from typing import Any
import re

try:
    from patterns import UNWANTED_PATTERNS
except ImportError:
    UNWANTED_PATTERNS = []

def remove_back_matter(text: str) -> str:
    # terms that are not relevant for the main text
    stop_signals = {
        "acknowledgments",
        "acknowledgements",
        "financial disclosure",
        "conflict of interest",
        "conflicts of interest",
        "supplementary material",
        "supplementary figure",
        "disclosure",
        "study funding"
    }

    lines = text.split("\n")
    clean_lines = []

    for line in lines:
        stripped_line = line.strip().lower()
        # check if the line is exactly one of the stop signals
        if any(stripped_line.startswith(signal) for signal in stop_signals):
            # if the line is a heading in the middle of the text, stop processing
            if len(stripped_line.split()) <= 4:
                break

        clean_lines.append(line)

    return "\n".join(clean_lines)

def clean_text(text: str) -> str:
    for pattern in UNWANTED_PATTERNS:
        if isinstance(pattern, re.Pattern):
            text = pattern.sub("", text)
        else:
            text = text.replace(pattern, "")
    return text

def is_heading(line: str) -> bool:
    line = line.strip()
    if not line:
        return False

    words = line.split()
    # only consider headings with 1-5 words
    if not (1 <= len(words) <= 5):
        return False

    # common short section labels
    if line.lower() in {
        "abstract", "introduction", "methods", "results", "discussion",
        "conclusion", "conclusions", "case report", "appendix"
    }:
        return True

    # Tables and figures
    if re.match(r"^(Table|Table\s\d+|Fig|Figure|FIGURE)\b", line, re.IGNORECASE):
        return True

    # no "/" in headings or headings ending with a digit
    if "/" in line or re.search(r"\d$", line):
        return False

    # ALL CAPS short headings (min. 3 characters and not ending with a period)
    if line.isupper() and len(line) > 4 and not line.endswith("."):
        return True

    # Section numbering like "1", "1.2", "2 Methods"
    #if re.match(r"^\d+(\.\d+)*\.?$", words[0]):
    #    return True

    # Title Case / label-like lines
    #if all(w[:1].isupper() or w.isdigit() for w in words if w):
    #    return True

    return False

def merge_broken_lines(text: str) -> str:
    # briefly clean the text
    text = clean_text(text)

    lines = text.split("\n")
    merged = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # if the line is a heading, do not merge it with the previous line
        if is_heading(line): #or (merged and is_heading(merged[-1])):
            merged.append(line)
            continue

        # normal line merging
        if merged and merged[-1] and not merged[-1].endswith((".", ":", ";", "!")):
            # prevent merging with heading
            merged[-1] += " " + line
        else:
            merged.append(line)

    # uses a special delimiter for paragraphs/headers
    return "\n\n".join(merged)


def split_into_chunks(text: str, max_words: int = 150) -> list[str]:
    # splitting at the double line breaks created by merge_broken_lines
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks = []
    current_chunk = []

    def flush_chunk():
        nonlocal current_chunk
        if current_chunk:
            chunks.append(" ".join(current_chunk).strip())
            current_chunk = []

    for paragraph in paragraphs:
        # check if the paragraph is a heading
        if is_heading(paragraph):
            flush_chunk()
            current_chunk.append(paragraph)
            # if it is a heading, skip the rest of the loop
            #flush_chunk()
            continue

        # count words for limiting the chunk size
        para_words = len(paragraph.split())
        current_words = len(" ".join(current_chunk).split())

        if current_chunk and (current_words + para_words > max_words):
            if len(current_chunk) == 1 and is_heading(current_chunk[0]):
                pass
            else:
                flush_chunk()

        if para_words > max_words:
            # if the paragraph is too long, split it into sentences
            sentences = re.split(r'(?<=[.!?])\s+', paragraph)
            for sentence in sentences:
                sentence = sentence.strip()
                sentence_words = len(sentence.split())
                current_words = len(" ".join(current_chunk).split())

                if current_chunk and (current_words + sentence_words > max_words):
                    flush_chunk()
                current_chunk.append(sentence)
        else:
            current_chunk.append(paragraph)

    flush_chunk()
    return chunks

def add_chunks_to_document(document: dict[str, Any]) -> dict[str, Any]:
    # remove back matter
    text_without_refs = remove_back_matter(document["text"])
    # clean and structure the text
    refined_text = merge_broken_lines(text_without_refs)
    # build chunk based on this structure
    document["chunks"] = split_into_chunks(refined_text)
    return document