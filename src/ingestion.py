from pathlib import Path
from typing import Any
import json
import pymupdf
import re

from cleaning import normalize_text
from chunking import add_chunks_to_document
from patterns import DOI_REGEX

# TODO: pagewise extraction, e.g.
# for page_number, page in enumerate(pdf_doc, start=1):
#    text = page.get_text()
# save to "pages": [...]
# TODO: add per-file error handling and logging for PDF ingestion
# TODO: add OCR extraction for PDFs with low text quality - metadata may be false too
# TODO: table handling
# TODO: Enhance meta-data handling: PDF -> extract DOI -> lookup metadata -> merge

def extract_doi(text: str, metadata: dict[str, Any] | None = None) -> str | None:
    # 1) Try metadata first
    if metadata:
        for value in metadata.values():
            if isinstance(value, str):
                match = DOI_REGEX.search(value)
                if match:
                    return match.group(1)

    # 2) Try full text
    match = DOI_REGEX.search(text)
    if match:
        return match.group(1)

    return None

def classify_text_quality(text: str) -> tuple[str, str]:
    if not text.strip():
        return "empty", "text is empty or whitespace only"

    words = text.split()

    if len(words) <= 2:
        return "artifact", "too few words"

    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.2:
        return "artifact", "too few unique words"

    return "good", "enough unique words and no obvious artifact pattern"

def extract_text_with_ocr() -> str:
    return "OCR placeholder"

def extract_text_from_pdf(pdf_path: Path) -> dict[str, Any]:
    with pymupdf.open(pdf_path) as pdf_doc:
        raw_text = "".join(page.get_text() for page in pdf_doc)
        metadata = pdf_doc.metadata

    cleaned_text = normalize_text(raw_text)
    quality, quality_reason  = classify_text_quality(cleaned_text)
    doi = extract_doi(cleaned_text, metadata)

    if quality in {"empty", "artifact"}:
        #cleaned_text = extract_text_with_ocr()
        processing_method = "ocr"
    else:
        processing_method = "text"

    return {
        "filename": pdf_path.name,
        "path": str(pdf_path),
        "text": cleaned_text,
        "doi": doi,
        "metadata": metadata,
        "quality": quality,
        "quality_reason": quality_reason,
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
    documents = [add_chunks_to_document(doc) for doc in documents]
    processed_files = save_documents_to_processed(documents, processed_folder)

    for doc in documents:
        save_text(doc, processed_folder)

    for doc in documents:
        quality = doc.get("quality")

    quality_counts = {"good": 0, "empty": 0, "artifact": 0}

    for doc in documents:
        quality = doc.get("quality")
        if quality in quality_counts:
            quality_counts[quality] += 1

        if quality in {"empty", "artifact"}:
            print(
                f"{doc.get('filename')}: quality={quality} | reason={doc.get('quality_reason')}"
            )

    print(f"\nLoaded {len(documents)} documents")
    print(f"Saved {len(processed_files)} processed files")
    print(
        f"Quality summary: good={quality_counts['good']}, empty={quality_counts['empty']}, artifact={quality_counts['artifact']}")
