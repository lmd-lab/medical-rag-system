"""
Simplified PDF text cleaning pipeline:
1. Artifact cleaning
2. Content cleaning
3. Metadata removal
4. URL / email cleanup
"""

import html
import logging
import os
import re
import unicodedata
from datetime import datetime

import ftfy

from src.patterns import (SECTION_HEADERS, UNWANTED_PREFIXES,
                          EMAIL_REGEX, URL_REGEX, MEDICAL_TERMS,
                          FUNCTION_WORDS)

MEDICAL_TERMS_LOWER = {term.lower() for term in MEDICAL_TERMS}


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
    """Fix spaced uppercase headers like A R T I C L E I N F O."""


    lines = text.split("\n")
    fixed_lines = []

    pattern = r"(?:[A-Za-z]\s){2,}[A-Za-z]}"

    for line in lines:
        if line.startswith("#"):
            matches = re.findall(pattern, line)

            if matches:
                logger.debug(
                    "Found %d spaced caps in line: %s",
                    len(matches),
                    matches[:3]
                )

                parts = line.split(None, 1)

                if len(parts) > 1:
                    prefix = parts[0]
                    content = parts[1]

                    # fix the spaced caps in the content part
                    content = re.sub(
                        pattern,
                        lambda m: m.group(0).replace(" ", ""),
                        content
                    )

                    line = f"{prefix} {content}"

        fixed_lines.append(line)

    return "\n".join(fixed_lines)


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

# ---------------- Phase 2: Author cleaning ----------------

def is_author_block(text: str) -> bool:
    """Heuristic to identify lines that are likely author blocks,"""
    lower_text = text.lower().strip()
    words_in_line = re.findall(r"[a-z]+", lower_text)

    if any(word in FUNCTION_WORDS for word in words_in_line):
        return False

    if any(word in MEDICAL_TERMS_LOWER for word in words_in_line):
        return False

    raw_words = text.split()
    if len(raw_words) < 3:
        return False

    # ratio of capitalized words
    capitals = sum(1 for w in raw_words if w[:1].isupper())
    if capitals / len(raw_words) > 0.8:
        return True

    return False

def clean_content(text: str) -> str:
    """Removes lines that are likely author blocks 
    or other non-content artifacts."""
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        lower = line.lower().strip()

        # always keep section headers, tables and lists
        if not lower or line.startswith(("#", "|", "*", "-")):
            cleaned.append(line)
            continue

        # check for unwanted patterns
        if any(lower.startswith(p) for p in UNWANTED_PREFIXES):
            logger.debug("Removed Metadata: %s", line)
            continue
        # check long lines
        if len(line) > 500:
            cleaned.append(line)
            continue

        # maybe an author block
        if is_author_block(line):
            logger.debug("Removed Author Block: %s", line)
            continue

        cleaned.append(line)

    return "\n".join(cleaned)

# ---------------- Phase 3: Metadata ----------------

def remove_metadata(text: str) -> str:
    """Removes lines that start with common 
    metadata prefixes like 'corresponding author' etc."""
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        lower = line.lower().strip()

        if re.fullmatch(r"\.+", lower):
            logger.debug("Removed dot-only line: %s", line)
            continue

        if any(lower.startswith(prefix) for prefix in UNWANTED_PREFIXES):
            logger.debug("Removed metadata line: %s", line)
            continue

        cleaned.append(line)

    return "\n".join(cleaned)

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
    text = clean_content(text)

    # Phase 3
    text = remove_metadata(text)

    logger.debug("Finished cleaning pipeline for %s", filename)

    return text.strip()
