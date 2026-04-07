"""
Simplified PDF text cleaning pipeline:
1. Artifact cleaning
2. Content cleaning
3. Metadata removal
4. URL / email cleanup
"""
import calendar
import html
import logging
import os
import re
import unicodedata
from datetime import datetime

import ftfy
import spacy

from src.patterns import (FUNCTION_WORDS, NOISE_WORDS,
                          SECTION_HEADERS, UNWANTED_PREFIXES,
                          EMAIL_REGEX, URL_REGEX,
                          ALL_COUNTRIES, MEDICAL_TERMS)


# ---------------- Logging ----------------

os.makedirs("Logs", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename: str = f"Logs/cleaning_{timestamp}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(log_filename, mode='w', encoding='utf-8')
fh.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))

if not logger.handlers:
    logger.addHandler(fh)


# ---------------- spaCy ------------------------------------

nlp = spacy.load("en_core_web_sm")


# ---------------- Phase 1: Artifact cleaning ----------------

def super_clean(text: str) -> str:
    """Performs basic cleaning of text, including fixing 
    encoding issues and removing control characters."""
    if not text:
        return ""

    text = html.unescape(text)
    text = ftfy.fix_text(text)
    text = unicodedata.normalize('NFKC', text)

    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)

    special_fixes = {
        "þ": "+",
        "â€™": "'",
        "95 C": "95 °C"
    }

    for search, replace in special_fixes.items():
        text = text.replace(search, replace)

    return text


def remove_image_placeholders(text: str) -> str:
    """Removes placeholders like <!-- Image Placeholder -->"""
    text, count = re.subn(r'<!-+.*?-+>', '', text, flags=re.DOTALL)
    logger.debug("Removed %d image placeholders", count)
    return text


def fix_spaced_caps(text: str) -> str:
    """Fixes A R T I C L E I N F O in headers with any number of # symbols."""

    pattern = r"^(#+\s*)?((?:[a-zA-Z]\s+){2,}[a-zA-Z])(?=\s|$)"

    matches = re.findall(pattern, text, re.MULTILINE)
    if matches:
        logger.debug("Found %d spaced caps: %s",
                     len(matches), [m[1] for m in matches[:3]])

    def remove_spaces(match):
        prefix = match.group(1) or ""
        content = re.sub(r"\s+", "", match.group(2))
        return f"{prefix}{content}"

    return re.sub(pattern, remove_spaces, text, flags=re.MULTILINE)


def add_markdown_headers(text: str) -> str:
    """Adds Markdown headers before section titles like ABSTRACT, INTRODUCTION, etc."""
    for header in SECTION_HEADERS:
        pattern = rf"(?im)^[ \t]*({re.escape(header)})[ \t]*$"
        text, count = re.subn(pattern, r"\n# \1\n", text)

        if count > 0:
            logger.debug("Fixed lonely header: '%s' (%d occurrences)", header, count)
    return text


def remove_citation_markers(text: str) -> str:
    """Removes citation markers like [1], [2,3], etc."""
    text, count = re.subn(r'\[[\d\s,.\-–]+\]', '', text)

    if count:
        logger.debug("Removed %d citation markers", count)

    return text


def clean_urls_and_emails(text: str) -> str:
    """Removes email addresses and URLs from the text."""
    email_count = len(EMAIL_REGEX.findall(text))
    url_count = len(URL_REGEX.findall(text))

    text = EMAIL_REGEX.sub('', text)
    text = URL_REGEX.sub('', text)

    logger.debug("Removed %d emails", email_count)
    logger.debug("Removed %d URLs", url_count)

    return text

# ---------------- Phase 2: Content cleaning ----------------

# ---------------- Main pipeline ----------------------------

def clean_markdown_text(text: str, filename: str = "unknown") -> str:
    """Runs the full cleaning pipeline on the extracted Markdown text."""
    logger.debug("Starting cleaning pipeline for %s", filename)

    # Phase 1
    text = super_clean(text)
    text = remove_image_placeholders(text)
    text = fix_spaced_caps(text)
    text = add_markdown_headers(text)
    text = remove_citation_markers(text)
    text = clean_urls_and_emails(text)

    # Phase 2
    #text = clean_content(text)

    # Phase 3
    #text = remove_metadata(text)
    

    logger.debug("Finished cleaning pipeline for %s", filename)

    return text.strip()
