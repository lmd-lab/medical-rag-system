from pathlib import Path
from typing import Any
import json
import pymupdf

# TODO: add per-file error handling and logging for PDF ingestion
# TODO: add OCR extraction for PDFs with low text quality - metadata may be false too
# TODO: table handling

def clean_text(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = text.replace("\u00ad", "")
    return text

def classify_text_quality(text: str) -> str:
    if not text.strip():
        return "empty"

    if "Firefox" in text and "http" in text:
        return "artifact"

    words = text.split()

    if len(set(words)) < 30:
        return "artifact"

    return "good"

def extract_text_with_ocr(pdf_path: Path) -> str:
    return "OCR placeholder"

def extract_text_from_pdf(pdf_path: Path) -> dict[str, Any]:
    with pymupdf.open(pdf_path) as doc:
        raw_text = "".join(page.get_text() for page in doc)
        metadata = doc.metadata

    cleaned_text = clean_text(raw_text)

    quality = classify_text_quality(cleaned_text)

    if quality in {"empty", "artifact"}:
        cleaned_text = extract_text_with_ocr(pdf_path)
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

def load_all_pdfs(folder_path: Path) -> list[dict[str, Any]] | None:
    try:
        pdf_documents: list[dict[str, Any]] = []

        for pdf_file in folder_path.glob("*.pdf"):
            print(f"Processing: {pdf_file.name}")
            pdf_documents.append(extract_text_from_pdf(pdf_file))

        return pdf_documents
    except Exception as e:
        print(f"Failed: {pdf_file.name} -> {e}")

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
    saved_files = save_documents_to_processed(documents, processed_folder)

    for doc in documents:
        save_text(doc, processed_folder)

    print(f"\nLoaded {len(documents)} documents")
    print(documents[0]["filename"])
    print(documents[0]["text"][:1000])

    print(f"\nLoaded {len(documents)} documents")
    print(f"Saved {len(saved_files)} processed files")