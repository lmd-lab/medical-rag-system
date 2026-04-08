"""
This module provides functions to query the Crossref API
for bibliographic information based on DOI, filename, or title.
It constructs a standardized reference string and extracts metadata.
"""
import os
import re
import html
import logging
from datetime import datetime

import requests
from dotenv import load_dotenv

load_dotenv()

CONTACT_EMAIL = os.getenv("CONTACT_EMAIL", "default@example.com")

# ---------------- Logging -----------------------

os.makedirs("Logs", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename: str = f"Logs/reference_{timestamp}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

if not logger.handlers:
    fh = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
    fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
    logger.addHandler(fh)

# ---------------- Helper Functions ----------------

def clean_filename_reference(filename: str) -> str:
    """Cleans a filename to create a more readable reference string."""
    return (
        filename.replace("_", " ")
        .replace("-", " ")
        .replace(".pdf", "")
        .replace(".txt", "")
        .strip()
    )

def validate_reference_match(reference: dict, text: str) -> bool:
    """Validates whether the reference title matches the extracted text,
    using a combination of exact and fuzzy matching heuristics."""
    title = reference.get("title", "")
    if isinstance(title, list):
        title = title[0] if title else ""

    if not title or not text:
        return False

    # clean text and title of everything but letters and numbers
    def normalize(s: str) -> str:
        return re.sub(r"[^a-z0-9]", "", s.lower())

    full_text_norm = normalize(text)

    # check if the normalized title is in the normalized text
    short_title = " ".join(title.split()[:6])
    short_title_norm = normalize(short_title)

    if short_title_norm in full_text_norm:
        return True

    # if the title is not found, check for significant words (longer than 5 characters)
    title_words = [
        normalize(w)
        for w in title.split()
        if len(normalize(w)) > 5
    ]
    if not title_words:
        return False

    matches = sum(
        1 for w in title_words
        if w in full_text_norm
    )

    # If 60% of the long words appear, it's likely a match'
    return (matches / len(title_words)) >= 0.6

def validate_candidate(candidate: dict, text: str, source: str, filename: str = None):
    """Validates a candidate reference against the extracted text and logs the result."""
    if candidate:
        if not text or validate_reference_match(candidate, text):
            logger.debug(
                'File "%s" → accepted %s: "%s"',
                filename,
                source,
                candidate.get("reference")
            )
            return candidate

        logger.debug(
            'File "%s" → rejected %s: validation failed for "%s"',
            filename,
            source,
            candidate.get("reference")
        )

    return None

# ---------------- NLM ----------------

def extract_nlm_info(text) -> dict:
    """Extract citation information from NLM Citation format."""

    match = re.search(
        r"NLM Citation:\s*(.*?)(?=\s*Bookshelf URL|Created:|$)",
        text,
        re.DOTALL,
    )
    if not match:
        return None

    full_citation = " ".join(match.group(1).split())

    # robust author/title extraction
    parts_match = re.search(
        r"^(.*?)\.\s+(.*?)\.\s+.*?\b((?:19|20)\d{2})\b",
        full_citation,
    )

    if parts_match:
        author, title, year = parts_match.groups()
    else:
        parts = [p.strip() for p in full_citation.split('. ')]
        author = parts[0] if len(parts) > 0 else "Unknown Author"
        title = parts[1] if len(parts) > 1 else "Unknown Title"

        year_match = re.search(r"\b((?:19|20)\d{2})\b", full_citation)
        year = year_match.group(0) if year_match else "Unknown Year"

    return {
        "reference": full_citation,
        "title": title,
        "author": author,
        "year": year,
        "journal": "GeneReviews® [Internet]",
        "publisher": "University of Washington, Seattle",
        "doi": None,
        "type": "book_chapter"
    }

# ---------------- CROSSREF ----------------

def build_reference(item: dict):
    """Builds a standardized reference string 
    and extracts metadata from a Crossref item."""
    authors = item.get("author", [])

    first_author = "Unknown"

    if authors:
        family = authors[0].get("family", "")
        given = authors[0].get("given", "")
        initials = f"{given[0]}." if given else ""
        first_author = f"{family}, {initials}"

        if len(authors) > 1:
            first_author += " et al."

    if not authors or not authors[0].get("family"):
        return None

    year = (
        item.get("published-print", {}).get("date-parts", [[None]])[0][0]
        or item.get("published-online", {}).get("date-parts", [[None]])[0][0]
        or item.get("created", {}).get("date-parts", [[None]])[0][0]
    )

    title = html.unescape(item.get("title", [""])[0])
    title = re.sub(r"<[^>]+>", "", title)
    title = re.sub(r"\s+", " ", title).strip()

    journal = item.get("container-title", [""])
    journal = journal[0] if journal else ""

    volume = item.get("volume", "")
    issue = item.get("issue", "")

    doi = item.get("DOI", "")
    publisher = item.get("publisher", "")

    reference = (
        f"{first_author} ({year}). {title}. "
        f"{journal}"
    )

    if volume:
        reference += f", {volume}"

    if issue:
        reference += f"({issue})"

    if doi:
        reference += f". https://doi.org/{doi}"

    return {
        "reference": reference,
        "title": title,
        "author": first_author,
        "year": year,
        "journal": journal,
        "publisher": publisher,
        "doi": doi,
        "type": item.get("type", "journal-article"),
    }

def query_crossref_by_text(query: str, base_url: str) -> dict:
    """Queries Crossref API using a text string (e.g., filename or title)"""
    try:
        headers = {"User-Agent": f"Medical RAG (mailto:{CONTACT_EMAIL})"}
        params = {"query.bibliographic": query, "rows": 1}

        r = requests.get(
            f"{base_url}/works",
            headers=headers,
            params=params,
            timeout=5,
        )

        if r.status_code == 200:
            data = r.json()["message"]
            items = data.get("items", [])

            if items:
                best_match = items[0]
                if best_match.get("score", 0) < 25:
                    return None

                return build_reference(best_match)
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"Crossref query error for '{query}': {e}")
    return None

# ---------------- Main pipeline ----------------------------

def get_reference(
    doi: str = None,
    filename: str = None,
    query_title: str = None,
    text: str = None,
) -> dict:
    """Main function to get citation information 
    from Crossref using DOI, filename, or title."""

    base_url = "https://api.crossref.org"

    result = None

    # 1. one special case NLM citation
    if text and "NLM Citation:" in text[:2000]:
        candidate = extract_nlm_info(text[:2000])
        validated = validate_candidate(candidate, text, "NLM", filename)
        if validated:
            validated["source"] = "nlm"
            return validated

    # 2. DOI lookup
    if doi and not result:
        try:
            headers = {"User-Agent": f"Medical RAG (mailto:{CONTACT_EMAIL})"}

            r = requests.get(
                f"{base_url}/works/{doi}",
                headers=headers,
                timeout=5,
            )

            if r.status_code == 200:
                candidate = build_reference(r.json()["message"])
                validated = validate_candidate(candidate, text, "DOI", filename)
                if validated:
                    validated["source"] = "doi"
                    return validated

        except (requests.exceptions.RequestException, ValueError) as e:
            logger.debug('File "%s" → DOI lookup error: %s', filename, e)

    # 3. Filename query
    if filename:
        candidate = query_crossref_by_text(clean_filename_reference(filename), base_url)
        validated = validate_candidate(candidate, text, "filename", filename)
        if validated:
            validated["source"] = "filename"
            return validated

    # 4. Title query
    if query_title:
        candidate = query_crossref_by_text(query_title, base_url)
        validated = validate_candidate(candidate, text, "title", filename)
        if validated:
            validated["source"] = "title"
            return validated

    # 5. Fallback
    fallback = {
        "reference": clean_filename_reference(filename) if filename else "Unknown Source",
        "title": query_title or "",
        "author": None,
        "year": None,
        "journal": None,
        "publisher": None,
        "doi": doi,
        "type": "fallback",
        "source": "fallback",
    }

    logger.debug(
        'File "%s" → fallback used: "%s"',
        filename,
        fallback["reference"]
    )
    return fallback
