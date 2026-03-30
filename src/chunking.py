import re
from typing import Any


def normalize_text(text: str) -> str:
    # Handle multi-character replacements first
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks
    text = re.sub(r"-\n(?=\w)", "", text)

    # Use translate for single characters only
    translation_table = str.maketrans({
        "\xa0": " ", "\u2002": " ", "\u2003": " ", "\u2009": " ",
        "\u200b": "", "\u00ad": "", "\u0000": "", "\u0001": "",
        "\x02": "", "\x03": "", "\x04": "", "\u000f": ""
    })
    text = text.translate(translation_table)

    # inline citation markers
    text = re.sub(r"\[\d+\]", "", text)

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
    # Fix Year Fallback
    if not year or str(year).lower() in ["none", "null", "0"]:
        match = re.search(r"\b(19|20)\d{2}\b", reference)
        year = match.group(0) if match else year

    # Split by Markdown headers
    parts = re.split(r'(^#+\s+.*$)', text, flags=re.MULTILINE)
    chunks = []
    current_header = "Intro/Header"

    for part in parts:
        part = part.strip()
        if not part: continue

        if part.startswith("#"):
            current_header = normalize_text(part.replace("#", "").strip())
            continue

        # 3. Normalize content and split into sentences
        cleaned_part = normalize_text(part)
        sentences = re.split(r'(?<=[.!?])\s+', cleaned_part)

        current_chunk_text = ""

        for sentence in sentences:
            # Check if adding the next sentence exceeds max_words
            if len((current_chunk_text + " " + sentence).split()) > max_words and current_chunk_text:
                chunk_text = re.sub(r"\s+", " ", current_chunk_text).strip()
                if len(re.findall(r"[A-Za-z]", chunk_text)) >= 10:
                    chunks.append({
                        "text": chunk_text,
                        "metadata": {"header": current_header, "reference": reference, "year": year, "journal": journal}
                    })
                current_chunk_text = sentence
            else:
                current_chunk_text = (current_chunk_text + " " + sentence).strip()

        # Add the remaining text as the last chunk of this section
        if current_chunk_text:
            chunk_text = re.sub(r"\s+", " ", current_chunk_text).strip()
            if len(re.findall(r"[A-Za-z]", chunk_text)) >= 10:
                chunks.append({
                    "text": chunk_text,
                    "metadata": {"header": current_header, "reference": reference, "year": year, "journal": journal}
                })

    return chunks

def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:

    source_ref = document.get("reference", document.get("filename", "Unknown Source"))
    source_year = document.get("year")
    source_journal = document.get("journal")

    # clear back matter - aber was ist, wenn es nicht am Ende steht?
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
