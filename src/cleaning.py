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
from urlextract import URLExtract

import ftfy

from src.patterns import (SECTION_HEADERS, UNWANTED_PREFIXES,
                          EMAIL_REGEX, ALL_COUNTRIES,
                          FUNCTION_WORDS, AFFILIATION_MARKERS,
                          DATE_LINE_PATTERN, INLINE_FOOTERS)


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

    text = ftfy.fix_text(text)

    while "&" in text:
        new_text = html.unescape(text)
        if new_text == text:
            break
        text = new_text

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


def remove_markdown_links(text: str) -> str:
    """Removes Markdown links, keeping only the link text."""
    pattern = r"\[([^\]]+)\]\(([^)]+)\)"
    links = [
        {"text": match.group(1), "url": match.group(2)}
        for match in re.finditer(pattern, text)
    ]

    if links:
        logger.debug("Found Markdown links: %s", links)

    text = re.sub(pattern, r"\1", text)
    return text


def remove_image_placeholders(text: str) -> str:
    """Removes placeholders like <!-- Image Placeholder -->"""
    text, count = re.subn(r'<!-+.*?-+>', '', text, flags=re.DOTALL)
    logger.debug("Removed %d image placeholders", count)
    return text


def fix_spaced_caps(text: str) -> str:
    """Fix spaced uppercase headers like A R T I C L E I N F O."""

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
    """Removes URLs and email addresses from the text, 
    and also removes empty parentheses or brackets left behind."""
    extractor = URLExtract()
    emails = EMAIL_REGEX.findall(text)
    urls = extractor.find_urls(text)

    unique_emails = list(dict.fromkeys(e.strip() for e in emails if e.strip()))
    unique_urls = list(dict.fromkeys(u.strip() for u in urls if u.strip()))

    email_count = len(unique_emails)
    url_count = len(unique_urls)

    text = EMAIL_REGEX.sub('', text)

    for url in unique_urls:
        text = text.replace(url, "")

    # replace empty parentheses or brackets with a single space to avoid leftover artifacts
    #text, paren_count = re.compile(r'\s*(\(\s*\)|\[\s*\])\.?\s*').subn(' ', text)
    text, paren_count = re.compile(r'[ \t]*(\(\s*\)|\[\s*\])\.?[ \t]*').subn('', text)
    text = re.sub(r' +', ' ', text).strip()

    if unique_emails:
        logger.debug("Removed %d emails:\n%s", email_count, "\n".join(unique_emails))
    else:
        logger.debug("Removed %d emails", email_count)

    if unique_urls:
        logger.debug("Removed %d URLs:\n%s", url_count, "\n".join(unique_urls))
    else:
        logger.debug("Removed %d URLs", url_count)

    logger.debug("Removed %d empty parentheses/brackets", paren_count)

    return text

# ---------------- Phase 2: Author cleaning ----------------

def normalize_part(text: str) -> str:
    """Removes accents and special characters."""
    if not text:
        return ""

    text = "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    text = "".join(c for c in unicodedata.normalize('NFKD', text) if not unicodedata.combining(c))
    text = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2212]", "-", text)

    return text.lower().replace("-", " ").strip()


def extract_author_surname(author: str) -> str | None:
    """Extract surname of first author, skipping surname particles."""

    if not author:
        return None

    surname = author.split(",")[0].strip().lower()

    particles = {"van", "von", "de", "del", "der", "den", "da", "di", "la", "le"}

    parts = surname.split()

    # use last meaningful surname part if particle exists
    if len(parts) > 1 and parts[0] in particles:
        return parts[-1]

    return surname


def is_affiliation_block(block: str) -> bool:
    """Heuristic to identify blocks that are likely affiliations."""
    # skip numbers
    #if re.fullmatch(r"\s*\d+\s*", block.strip()):
    #    return True

    #if re.fullmatch(r"\s*[a-zA-Z]\s*", block.strip()):
    #    return True

    lower = block.lower()

    country_match = any(
            re.search(rf"\b{re.escape(c.lower())}\b", lower)
            for c in ALL_COUNTRIES
        )

    marker_set = {
        w for w in AFFILIATION_MARKERS
        if re.search(rf"\b{re.escape(w)}\b", lower)
    }
    marker_hits = len(marker_set)

    if country_match and marker_hits >= 1:
        return True

    if marker_hits >= 2:
        return True

    #logger.debug(
    #    "AFFILIATION CHECK | block=%s | country=%s | markers=%s",
    #    block,
    #    country_match,
    #    marker_hits
    #)

    return False


def remove_author_and_affiliation_block(text: str, author: str = None) -> str:
    """Removes the author block and likely affiliation lines from the text."""
    if not author:
        return text

    raw_surname = extract_author_surname(author)
    # remove accents and special characters for
    # better matching (e.g., 'Alfonso-Reis' -> 'alfonso reis')
    raw_surname = re.split(r'\s+', raw_surname)[0]
    surname = normalize_part(raw_surname)

    if not surname:
        return text

    paragraphs = text.split("\n\n")
    cleaned = []
    removed_author_blocks = []
    removed_affiliation_blocks = []

    for i, block in enumerate(paragraphs):
        block_words = re.findall(r"[a-z]+", block.lower())
        function_word_hits = len({w for w in block_words if w in FUNCTION_WORDS})

        norm_block = normalize_part(block)

        # 1. search author block based on surname in the first 20 paragraphs
        if i < 20 and re.search(rf'\b{re.escape(surname)}\b', norm_block):
            # if surname is followed by et al., it's likely an inline citation
            if re.search(rf"{re.escape(surname)}\s+et\s+al", norm_block) and function_word_hits > 3:
                cleaned.append(block)
                continue

            if function_word_hits > 3:
                cleaned.append(block)
                continue

            removed_author_blocks.append(block)
            continue

        # 2. remove blocks that are likely affiliations based on heuristics
        elif i < 50 and is_affiliation_block(block):

            if function_word_hits > 3:
                cleaned.append(block)
                continue

            removed_affiliation_blocks.append(block)
            continue

        cleaned.append(block)

    if removed_author_blocks:
        logger.debug(
            "Removed author-related blocks for surname '%s':\n\n%s",
            surname,
            "\n\n--- REMOVED AUTHOR BLOCK: ".join(removed_author_blocks)
        )

    if removed_affiliation_blocks:
        logger.debug(
            "Removed affiliation-related blocks:\n\n%s",
            "\n\n--- REMOVED AFFILIATION BLOCK: ".join(removed_affiliation_blocks)
        )

    return "\n\n".join(cleaned)


def remove_journal_lines(text: str, journal: str = None) -> str:
    """
    Removes lines that start with or exactly match the journal name.
    Useful for recurring headers/footers inserted by PDF extraction tools.
    """

    if not journal:
        return text

    # normalize journal name once
    journal_norm = normalize_part(journal)

    lines = text.split("\n")
    cleaned = []
    removed = []

    for line in lines:
        norm_line = normalize_part(line)

        # skip empty lines
        if not norm_line:
            cleaned.append(line)
            continue

        # match: line starts with journal OR equals journal
        if norm_line.startswith(journal_norm) or norm_line == journal_norm:
            removed.append(line)
            continue

        cleaned.append(line)

    if removed:
        logger.debug(
            "Removed journal lines for '%s':\n\n%s",
            journal,
            "\n".join(removed)  
        )

    return "\n".join(cleaned)

# ---------------- Phase 3: Metadata ----------------

def is_date_metadata_line(line: str) -> bool:
    """Heuristic to identify lines that likely contain date metadata,
    such as 'March 2021' or 'Received January 15, 2020', and not regular text."""
    stripped = line.strip()

    # Line must be short (date lines are rarely longer than ~60 characters)
    if len(stripped) > 60:
        return False

    return bool(DATE_LINE_PATTERN.match(stripped))

def remove_inline_footer_terms(line: str) -> tuple[str, list[str]]:
    """Removes exact inline footer terms from a line and returns removed terms."""
    cleaned = line
    removed_terms: list[str] = []

    for term in INLINE_FOOTERS:
        pattern = re.compile(rf"(?<!\\w){re.escape(term)}(?!\\w)", flags=re.IGNORECASE)
        cleaned, count = pattern.subn("", cleaned)
        if count > 0:
            removed_terms.append(term)

    # Clean up only spacing artifacts introduced by removals.
    cleaned = re.sub(r"[ \t]{2,}", " ", cleaned)
    cleaned = re.sub(r"^\s+", "", cleaned)

    return cleaned, removed_terms

def remove_metadata(text: str) -> str:
    """Removes lines that start with common 
    metadata prefixes like 'corresponding author' etc."""
    lines = text.split("\n")
    cleaned = []

    for line in lines:
        stripped = line.strip()
        lower = stripped.lower()

        if not stripped:
            cleaned.append(line)
            continue

        # remove lines that are just dots or similar
        if re.fullmatch(r"[\s.]+", lower):
            logger.debug("Removed dot-only line: %s", line)
            continue

        # check for unwanted patterns like additional information, corresponding author, etc.
        lower = unicodedata.normalize('NFKC', stripped).lower()
        lower = lower.replace('✩', '*').replace('∗', '*')

        if any(lower.startswith(prefix) for prefix in UNWANTED_PREFIXES):
            logger.debug("Removed metadata line: %s", line)
            continue

        if is_date_metadata_line(stripped):
            logger.debug("Removed date metadata line: %s", line)
            continue

        cleaned_line, removed_footer_terms = remove_inline_footer_terms(line)
        if removed_footer_terms:
            logger.debug(
                "Removed inline footer terms %s from line: %s",
                removed_footer_terms,
                line
            )
            if not cleaned_line.strip():
                continue
            cleaned.append(cleaned_line)
            continue

        cleaned.append(line)

    return "\n".join(cleaned)

# ---------------- Main pipeline ----------------------------

def clean_markdown_text(text: str,
                        filename: str = "unknown",
                        author: str | str = None,
                        journal: str | str = None) -> str:
    """Runs the full cleaning pipeline on the extracted Markdown text."""
    logger.debug("Starting cleaning pipeline for %s", filename)

    # Phase 1
    text = super_clean(text)
    text = remove_markdown_links(text)
    text = remove_image_placeholders(text)
    text = fix_spaced_caps(text)
    text = add_markdown_headers(text)
    text = remove_citation_markers(text)

    # Phase 2
    text = remove_author_and_affiliation_block(text, author=author)
    text = remove_journal_lines(text, journal=journal)

    # Phase 3
    text = remove_metadata(text)
    text = clean_urls_and_emails(text)

    # cleanup multiple newlines and trim
    text = re.sub(r'\n{3,}', '\n\n', text).strip()

    logger.debug("Finished cleaning pipeline for %s\n\n", filename)

    return text.strip()
