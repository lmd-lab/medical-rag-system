import re
from typing import Any


def normalize_text(text: str) -> str:
    # Handle multi-character replacements first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks
    text = re.sub(r"-\n(?=\w)", "", text)

    # Use translation_table for single characters only
    translation_table = str.maketrans({
        "\xa0": " ", "\u2002": " ", "\u2003": " ", "\u2009": " ",
        "\u200b": "", "\u00ad": "", "\u0000": "", "\u0001": "",
        "\x02": "", "\x03": "", "\x04": "", "\u000f": ""
    })
    text: str = text.translate(translation_table)

    # inline citation markers
    text = re.sub(r"\[\d+]", "", text)

    # Process lines: Trim whitespace and collapse multiple empty lines
    cleaned_lines = []
    for line in text.split("\n"):
        # Reduce multiple spaces/tabs within a line to a single space
        line = re.sub(r"[ \t]+", " ", line).strip()

        # Only add the line if it's not a redundant empty line
        if line != "" or (cleaned_lines and cleaned_lines[-1] != ""):
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()

def split_into_chunks_markdown(
        text: str, reference: str, year: Any, journal: str | None, max_words: int = 250
) -> list[dict[str, Any]]:
    year_fallback_pattern = r"\b(19|20)\d{2}\b"
    header_split_pattern = r"(^#+\s+.*$)"
    sentence_split_pattern = r"(?<=[.!?])\s+"
    min_letter_count = 10

    def append_chunk(chunks: list[dict[str, Any]], chunk_text: str, metadata: dict[str, Any]) -> None:
        normalized_text = re.sub(r"\s+", " ", chunk_text).strip()
        if len(re.findall(r"[A-Za-z]", normalized_text)) >= min_letter_count:
            chunks.append({"text": normalized_text, "metadata": metadata})

    if not year or str(year).lower() in {"none", "null", "0"}:
        match = re.search(year_fallback_pattern, reference)
        year = match.group(0) if match else year

    metadata = {
        "reference": reference,
        "year": year,
        "journal": journal,
    }

    chunks: list[dict[str, Any]] = []
    current_header = "Intro/Header"

    for part in re.split(header_split_pattern, text, flags=re.MULTILINE):
        part = part.strip()
        if not part:
            continue

        if part.startswith("#"):
            current_header = normalize_text(part.replace("#", "").strip())
            continue

        sentences = re.split(sentence_split_pattern, normalize_text(part))
        current_chunk_text = ""

        for sentence in sentences:
            candidate_text = f"{current_chunk_text} {sentence}".strip()
            if current_chunk_text and len(candidate_text.split()) > max_words:
                append_chunk(
                    chunks,
                    current_chunk_text,
                    {"header": current_header, **metadata},
                )
                current_chunk_text = sentence
            else:
                current_chunk_text = candidate_text

        if current_chunk_text:
            append_chunk(
                chunks,
                current_chunk_text,
                {"header": current_header, **metadata},
            )

    return chunks

def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:

    source_ref = document.get("reference", document.get("filename", "Unknown Source"))
    source_year = document.get("year")
    source_journal = document.get("journal")

    # clear back matter
    text = document["text"]
    for marker in ["## References", "## Bibliography"]:
        pos = text.find(marker)
        if pos > len(text) * 0.7:
            text = text[:pos]
            break

    document["chunks"] = split_into_chunks_markdown(
        text,
        source_ref,
        source_year,
        source_journal
    )
    return document
