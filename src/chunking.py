from typing import Any
import re

try:
    from patterns import UNWANTED_PATTERNS
except ImportError:
    UNWANTED_PATTERNS = []

def merge_broken_lines(text: str) -> str:
    lines = text.split("\n")
    merged = []

    for line in lines:
        line = line.strip()

        if not line:
            merged.append("")
            continue

        if any(
            pattern in line if isinstance(pattern, str) else pattern.search(line)
            for pattern in UNWANTED_PATTERNS
        ):
            continue

        if line.startswith("http"):
            continue

        if merged and merged[-1] and not merged[-1].endswith((".", ":", ";")):
            merged[-1] += " " + line
        else:
            merged.append(line)

    return "\n".join(merged)

def split_into_chunks(text: str, max_words: int = 120) -> list[str]:
    text = merge_broken_lines(text)

    sentences = re.split(r'(?<=[.!?])\s+', text)

    chunks = []
    current_chunk = []

    for sentence in sentences:
        current_chunk.append(sentence)

        if len(" ".join(current_chunk).split()) >= max_words:
            chunks.append(" ".join(current_chunk))
            current_chunk = []

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:
    document["chunks"] = split_into_chunks(document["text"])
    return document