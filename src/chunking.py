from typing import Any


def split_into_chunks(text: str) -> list[str]:
    chunks = [chunk.strip() for chunk in text.split("\n\n") if chunk.strip()]
    return chunks


def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:
    document["chunks"] = split_into_chunks(document["text"])
    return document