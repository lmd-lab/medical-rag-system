from pathlib import Path
from typing import Any
import json
import pymupdf
import re

# TODO: add per-file error handling and logging for PDF ingestion
# TODO: add OCR extraction for PDFs with low text quality - metadata may be false too
# TODO: table handling

def normalize_text(text: str) -> str:
    # Normalize line endings
    text = text.replace("\r\n", "\n").replace("\r", "\n")

    # Fix hyphenated line breaks
    text = re.sub(r"-\n(?=\w)", "", text)

    # Replace common spacing artifacts with regular spaces
    text = text.replace("\xa0", " ")  # NBSP = Non-Breaking Space
    text = text.replace("\u2002", " ")  # ENSP = En Space
    text = text.replace("\u2003", " ")  # EMSP = Em Space
    text = text.replace("\u2009", " ")  # THSP = Thin Space

    # Remove invisible / soft formatting artifacts
    text = text.replace("\u200b", "")  # ZWSP = Zero Width Space
    text = text.replace("\u00ad", "")  # SHY = Soft Hyphen

    # Remove control characters that are usually extraction noise
    text = text.replace("\x01", "")  # SOH = Start Of Heading
    text = text.replace("\x02", "")  # STX = Start Of Text
    text = text.replace("\x03", "")  # ETX = End Of Text
    text = text.replace("\x04", "")  # EOT = End Of Transmission

    # Clean each line without destroying paragraph structure
    cleaned_lines = []
    blank_count = 0

    for line in text.split("\n"):
        # Normalize spaces/tabs within the line
        line = re.sub(r"[ \t]+", " ", line).strip()

        if line == "":
            blank_count += 1
            if blank_count <= 1:
                cleaned_lines.append("")
        else:
            blank_count = 0
            cleaned_lines.append(line)

    return "\n".join(cleaned_lines).strip()

def classify_text_quality(text: str) -> str:
    if not text.strip():
        return "empty"

    if "Firefox" in text and "http" in text:
        return "artifact"

    words = text.split()

    if len(set(words)) < 30:
        return "artifact"

    return "good"

def extract_text_with_ocr() -> str:
    return "OCR placeholder"

def extract_text_from_pdf(pdf_path: Path) -> dict[str, Any]:
    with pymupdf.open(pdf_path) as pdf_doc:
        raw_text = "".join(page.get_text() for page in pdf_doc)
        metadata = pdf_doc.metadata

    cleaned_text = normalize_text(raw_text)
    quality = classify_text_quality(cleaned_text)

    if quality in {"empty", "artifact"}:
        cleaned_text = extract_text_with_ocr()
        processing_method = "ocr"
    else:
        processing_method = "text"

    return {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "text": cleaned_text,
        "metadata": metadata,
        "quality": quality,
        "processing_method": processing_method,
    }

def load_all_pdfs(folder_path: Path) -> list[dict[str, Any]]:
    pdf_documents: list[dict[str, Any]] = []

    for pdf_file in folder_path.glob("*.pdf"):
        try:
            print(f"Processing: {pdf_file.name}")
            pdf_documents.append(extract_text_from_pdf(pdf_file))
        except Exception as e:
            print(f"Failed: {pdf_file.name} -> {e}")

    return pdf_documents

def save_documents_to_processed(
    documents: list[dict[str, Any]],
    output_folder: Path,
) -> list[Path]:
    output_folder.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []

    for document in documents:
        output_path = output_folder / f"{Path(document['filename']).stem}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False, indent=2, default=str)

        saved_files.append(output_path)

    return saved_files

def save_text(document: dict[str, Any], output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / f"{Path(document['filename']).stem}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(document["text"])

if __name__ == "__main__":
    pdf_folder = Path("data/raw")
    processed_folder = Path("data/processed")

    documents = load_all_pdfs(pdf_folder)
    processed_files = save_documents_to_processed(documents, processed_folder)

    for doc in documents:
        save_text(doc, processed_folder)

    print(f"\nLoaded {len(documents)} documents")
    print(documents[0]["filename"])
    print(documents[0]["text"][:1000])

    print(f"\nLoaded {len(documents)} documents")
    print(f"Saved {len(processed_files)} processed files")