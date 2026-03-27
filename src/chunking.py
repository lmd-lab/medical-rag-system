from typing import Any
import re

# TODO: handle scientific PDF artifacts (headers, footers, tables) before semantic chunking

UNWANTED_PATTERNS = [
    "Downloaded from",
    "by guest on",
    "©",
    re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
]

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

def split_into_chunks(text: str) -> list[str]:
    text = merge_broken_lines(text)
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks


def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:
    document["chunks"] = split_into_chunks(document["text"])
    return document