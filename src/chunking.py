"""
Chunking module for medical RAG:
- Removes figure captions
- Extracts tables and merges captions
- Adds metadata + logging
- Handles cases where text starts without a heading
"""

import os
import re
import uuid
import logging
from typing import Any
from datetime import datetime

from src.patterns import SKIP_HEADERS


# ---------------- Logging ----------------

os.makedirs("Logs", exist_ok=True)

timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
log_filename: str = f"Logs/chunking_{timestamp}.log"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

fh = logging.FileHandler(log_filename, mode="w", encoding="utf-8")
fh.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))

if not logger.handlers:
    logger.addHandler(fh)

# ---------------- Helper Functions ----------------

def normalize_text(text: str) -> str:
    """Basic text normalization to clean up
    whitespace and hyphenation artifacts.
    """
    text = re.sub(r"-\n", "", text)
    text = re.sub(r"\n+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def is_skip_header(header: str) -> bool:
    """Determines if a header should be skipped based on patterns"""
    header_clean = header.lower().strip().rstrip(":.")

    degree_pattern = r"\b(md|phd|dds|rn|bsn|faan|faap|chtp|msc|mba)\b"

    # Case 1: exact skip headers
    if header_clean in SKIP_HEADERS:
        return True

    # Case 2: short header with degree → likely author line
    if (
        len(header_clean.split()) <= 6
        and re.search(degree_pattern, header_clean, re.IGNORECASE)
    ):
        return True

    return False


def is_figure_caption(line: str) -> bool:
    """Determines if a line is a figure caption"""
    return bool(re.match(r"^(Figure|Fig\.?)\s*\d+", line.strip(), re.IGNORECASE))


def is_table_caption(line: str) -> bool:
    """Determines if a line is a table caption"""
    return bool(re.match(r"^Table\s*\d+", line.strip(), re.IGNORECASE))


def is_table_line(line: str) -> bool:
    """Determines if a line is part of a table"""
    return line.strip().startswith("|")


def is_low_information(text: str) -> tuple[bool, str]:
    """Heuristic checks to identify low-information content"""
    words = text.split()

    if len(words) < 3:
        return True, "too_few_words"

    num_ratio = sum(c.isdigit() for c in text) / max(len(text), 1)
    if num_ratio > 0.85:
        return True, "mostly_numbers"

    if re.fullmatch(r"[\d\s\.,%-]+", text):
        return True, "numeric_line"

    if re.fullmatch(r"[\s\.,%\-\|/]+", text):
        return True, "junk_characters"

    return False, ""


# ---------------- Main chunking function ----------------


def split_into_chunks_markdown(
    text: str,
    base_metadata: dict[str, Any],
    max_words: int = 250
) -> list[dict[str, Any]]:
    """Splits markdown text into chunks 
    based on headers, captions, and tables."""
    header_pattern = r"(^#+\s+.*$)"
    chunks: list[dict[str, Any]] = []
    removal_stats: dict[str, dict[str, int]] = {}

    current_header = "Abstract/Preface"
    active_caption: str | None = None
    skip_section = False

    lines = text.split("\n")
    total_lines = max(len(lines), 1)

    table_buffer: list[str] = []
    current_text = ""
    chunk_counter = 0

    def ensure_section_stats(header: str) -> dict[str, int]:
        if header not in removal_stats:
            removal_stats[header] = {
                "skipped_section_lines": 0,
                "captions_attached": 0,
                "low_info_text_chunks": 0,
                "low_info_tables": 0,
            }
        return removal_stats[header]

    def flush_text(line_offset: int) -> None:
        nonlocal current_text, active_caption, chunk_counter
        if not current_text.strip():
            return

        clean = normalize_text(current_text)
        is_bad, reason = is_low_information(clean)

        if is_bad:
            section_stats = ensure_section_stats(current_header)
            section_stats["low_info_text_chunks"] += 1
            logger.info("Removed text chunk (%s) | %s: %r", reason, current_header, clean[:80])
        else:
            chunks.append({
                "chunk_id": uuid.uuid4().hex,
                "chunk_type": "text",
                "text": clean,
                "metadata": {
                    "header": current_header,
                    "context_caption": active_caption,
                    "chunk_index": chunk_counter,
                    "relative_pos": round(line_offset / total_lines, 3),
                    **base_metadata,
                },
            })
            chunk_counter += 1
            active_caption = None

        current_text = ""

    def flush_table(line_offset: int) -> None:
        nonlocal table_buffer, active_caption
        if not table_buffer:
            return

        clean_table = "\n".join(table_buffer).strip()
        is_bad, reason = is_low_information(clean_table)

        if is_bad:
            section_stats = ensure_section_stats(current_header)
            section_stats["low_info_tables"] += 1
            logger.info("Removed table (%s) | %s: %r", reason, current_header, clean_table[:80])
        else:
            chunks.append({
                "chunk_id": uuid.uuid4().hex,
                "chunk_type": "table",
                "text": clean_table,
                "metadata": {
                    "header": current_header,
                    "context_caption": active_caption,
                    "chunk_index": chunk_counter,
                    "relative_pos": round(line_offset / total_lines, 3),
                    **base_metadata,
                },
            })

        table_buffer = []
        active_caption = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # --- HEADER ---
        if re.match(header_pattern, line):
            flush_text(i)
            flush_table(i)
            current_header = normalize_text(line.replace("#", ""))
            skip_section = is_skip_header(current_header)
            if skip_section:
                logger.info("Skipping section: %s", current_header)
            continue

        if not stripped:
            continue

        if skip_section:
            section_stats = ensure_section_stats(current_header)
            section_stats["skipped_section_lines"] += 1
            continue

        # --- CAPTIONS (store as context for the next chunk) ---
        if is_figure_caption(stripped) or is_table_caption(stripped):
            flush_text(i)
            active_caption = stripped
            section_stats = ensure_section_stats(current_header)
            section_stats["captions_attached"] += 1
            logger.info("Found caption for context: %s", stripped[:100])
            continue

        # --- TABLE LINE ---
        if is_table_line(line):
            table_buffer.append(line)
            continue

        if table_buffer:
            flush_table(i)

        # --- NORMAL TEXT ---
        current_text += " " + stripped
        if len(current_text.split()) > max_words:
            flush_text(i)

    flush_text(total_lines - 1)
    flush_table(total_lines - 1)

    for section, stats in removal_stats.items():
        total_events = sum(stats.values())
        if total_events > 0:
            logger.info(
                "Section summary | section='%s' | skipped_lines=%d |" \
                "captions_attached=%d | low_info_text=%d | low_info_tables=%d",
                section,
                stats["skipped_section_lines"],
                stats["captions_attached"],
                stats["low_info_text_chunks"],
                stats["low_info_tables"],
            )

    return chunks

# ─── Main document processing function ─────────────────────────────────────

def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:
    """Main function to process one document."""

    filename = document.get("filename", "unknown")
    logger.info("Start chunking file: %s", filename)

    base_metadata = {
        "reference": document.get("reference", document.get("filename", "Unknown Source")),
        "first_author": document.get("first_author", "Unknown Author"),
        "authors": document.get("authors", []),
        "year": document.get("year", "Unknown Year"),
        "journal": document.get("journal", "Unknown Journal"),
    }

    document["chunks"] = split_into_chunks_markdown(
        document["text"],
        base_metadata
    )

    total_chunks = len(document["chunks"])
    text_chunks = sum(1 for c in document["chunks"] if c.get("chunk_type") == "text")
    table_chunks = sum(1 for c in document["chunks"] if c.get("chunk_type") == "table")

    logger.info(
        "Finished chunking file: %s | total_chunks=%d | text_chunks=%d | table_chunks=%d",
        filename,
        total_chunks,
        text_chunks,
        table_chunks,
    )

    return document
