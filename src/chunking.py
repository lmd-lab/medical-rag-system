import re
from typing import Any

def split_into_chunks_markdown(text: str, reference: str, max_words: int = 250) -> list[dict[str, Any]]:
    # split text at every markdown header (#, ##, ###))
    parts = re.split(r'(^#+\s+.*$)', text, flags=re.MULTILINE)

    chunks = []
    current_header = "Intro/Header"  # Fallback für Text vor der ersten Überschrift

    for part in parts:
        part = part.strip()
        if not part: continue

        if part.startswith("#"):
            current_header = part.replace("#", "").strip()
            continue

        words = part.split()

        if len(words) > max_words:
            sentences = re.split(r'(?<=[.!?])\s+', part)
            current_sub_text = ""

            for sentence in sentences:
                if len(current_sub_text.split()) + len(sentence.split()) > max_words:
                    chunks.append({
                        "text": current_sub_text.strip(),
                        "metadata": {"header": current_header, "reference": reference}
                    })
                    current_sub_text = sentence
                else:
                    current_sub_text += " " + sentence

            if current_sub_text:
                chunks.append({
                    "text": current_sub_text.strip(),
                    "metadata": {"header": current_header, "reference": reference}
                })
        else:
            chunks.append({
                "text": part,
                "metadata": {"header": current_header, "reference": reference}
            })

    return chunks


def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:

    source_ref = document.get("reference", document.get("filename", "Unknown Source"))

    # clear back matter - aber was ist wenn es nicht am Ende steht?
    text = document["text"]
    for marker in ["## References", "## Bibliography"]:
        pos = text.find(marker)
        if pos > len(text) * 0.7:
            text = text[:pos]
            break

    document["chunks"] = split_into_chunks_markdown(text, source_ref)
    return document
