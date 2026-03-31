from pathlib import Path
from typing import Any
import re
import json
import html
from collections import Counter
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions

from config import RAW_DATA_PATH, PROCESSED_DATA_PATH
from src.chunking import add_chunks_to_document
from src.crossref_citations import get_citation_from_crossref, clean_filename_reference
from src.patterns import DOI_REGEX, PMID_REGEX, SECTION_HEADERS
try:
    from src.patterns import UNWANTED_PATTERNS
except ImportError:
    UNWANTED_PATTERNS = []

def extract_doi(text: str) -> str | None:
    first_part = text[:6000] # only the first 1-2 pages

    match = DOI_REGEX.search(first_part)
    if match:
        return match.group(1).rstrip(".")

    return None

def extract_pmid(text: str) -> str | None:
    first_part = text[:6000]

    match = PMID_REGEX.search(first_part)
    if match:
        return match.group(1)
    return None

def classify_basic_text_quality(text: str) -> tuple[str, str]:
    if not text.strip():
        return "empty", "text is empty or whitespace only"

    words = text.split()

    if len(words) <= 2:
        return "artifact", "too few words"

    unique_ratio = len(set(words)) / len(words)
    if unique_ratio < 0.2:
        return "artifact", "too few unique words"

    return "good", "enough unique words and no obvious artifact pattern"

def get_first_heading(md_text: str):
    for line in md_text.splitlines():
        if line.startswith("#"):
            return line.replace("#", "").strip()
    return None

def fix_spaced_caps(text: str) -> str:
    return re.sub(
        r"\b(?:[A-Z]\s){3,}[A-Z](?=\b|:)",
        lambda m: m.group(0).replace(" ", ""),
        text
    )

def add_markdown_headers(text: str) -> str:
    for header in SECTION_HEADERS:
        text = re.sub(
            rf"(?im)^\s*{header}\s*$",
            f"\n# {header}\n",
            text,
        )
    return text

def clean_markdown_text(text: str) -> str:
    text = html.unescape(text) # remove HTML entities

    text = text.replace("-\n", "") # remove line breaks after dashes
    text = text.replace("\n\n\n", "\n\n") # remove multiple line breaks
    text = re.sub(r" {2,}", " ", text) # remove multiple spaces
    text = text.replace("\xa0", " ") # NBSP = Non-Breaking Space
    text = text.replace("â€™", "'") # remove weird character
    text = text.replace("ﬁ", "fi").replace("ﬂ", "fl")

    text = fix_spaced_caps(text)

    for pattern in UNWANTED_PATTERNS:
        if isinstance(pattern, re.Pattern):
            text = pattern.sub("", text)
        else:
            text = re.sub(re.escape(pattern), "", text, flags=re.IGNORECASE)

    text = add_markdown_headers(text)

    return text.strip()

def remove_journal_from_text(text: str, reference: dict) -> str:
    journal = reference.get("journal")

    if journal:
        text = re.sub(
            re.escape(journal),
            "",
            text,
            flags=re.IGNORECASE
        )

    publisher = reference.get("publisher")

    if publisher:
        text = re.sub(
            re.escape(publisher),
            "",
            text,
            flags=re.IGNORECASE
        )

    return text

def validate_reference_match(reference: dict, text: str) -> bool:
    if not isinstance(reference, dict) or not reference.get("title"):
        return False

    # clean text and title of everything but letters and numbers
    def normalize(s: str) -> str:
        return re.sub(r"\W", "", s).lower()

    full_text_norm = normalize(text)

    # check if the normalized title is in the normalized text
    short_title = " ".join(reference["title"].split()[:6])
    short_title_norm = normalize(short_title)

    if short_title_norm in full_text_norm:
        return True

    # if the title is not found, check for significant words (longer than 5 characters)
    title_words = [
        normalize(w)
        for w in reference["title"].split()
        if len(normalize(w)) > 5
    ]
    if not title_words:
        return False

    matches = sum(
        1 for w in title_words
        if w in full_text_norm
    )

    # If 60% of the long words appear, it's likely a match'
    return (matches / len(title_words)) >= 0.6

def extract_text(pdf_path: Path) -> dict[str, Any]:
    # ignore pictures but use ocr for bad PDFs
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.generate_page_images = False
    pipeline_options.generate_table_images = False  # no pictures of tables?

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    try:
        result = converter.convert(str(pdf_path))

        # Markdown without images
        markdown_text = result.document.export_to_markdown()

        # Metadata extraction
        metadata = vars(result.document.origin) if result.document.origin else {}

        # check quality and get doi
        quality, quality_reason = classify_basic_text_quality(markdown_text)

        # get doi and pmid
        doi = extract_doi(markdown_text)
        pmid = extract_pmid(markdown_text)

        # clean Markdown from artifacts
        cleaned_markdown = clean_markdown_text(markdown_text)

        # get first heading
        first_heading = get_first_heading(cleaned_markdown)

        # build reference for chunking
        reference = get_citation_from_crossref(
            doi=doi,
            filename=pdf_path.name,
            query_title=first_heading,
        )

        # validate the reference match
        reference_valid = validate_reference_match(
            reference,
            cleaned_markdown,
        )
        if not reference_valid:
            reference = {
                "reference": clean_filename_reference(pdf_path.name),
                "journal": None,
                "publisher": None,
                "doi": doi,
            }

        # remove journal if present in reference from text to reduce noise
        cleaned_markdown = remove_journal_from_text(cleaned_markdown, reference)

        return {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "first_heading": first_heading,
            "title": reference.get("title"),
            "year": reference.get("year"),
            "reference": reference.get("reference"),
            "journal": reference.get("journal"),
            "publisher": reference.get("publisher"),
            "doi": doi,
            "pmid": pmid,
            "quality": quality,
            "quality_reason": quality_reason,
            "processing_method": "docling_v2_optimized",
            "metadata": metadata,
            "text": cleaned_markdown.strip(),
        }
    except Exception as e:
        print(f"Error processing {pdf_path}: {e}")
        return {"filename": pdf_path.name, "error": str(e)}

def load_all_pdfs(folder_path: Path) -> list[dict[str, Any]]:
    documents: list[dict[str, Any]] = []

    for pdf_file in folder_path.glob("*.pdf"):
        # generate expected json file name
        expected_json_name = f"{pdf_file.stem}.json"
        expected_json_path = PROCESSED_DATA_PATH / expected_json_name

        # check if file is already processed
        if expected_json_path.exists():
            print(f"Skipping: {pdf_file.name} (already processed)")
            continue

        try:
            print(f"Processing: {pdf_file.name}")
            documents.append(extract_text(pdf_file))
        except Exception as e:
            print(f"Failed: {pdf_file.name} -> {e}")

    return documents

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

def save_markdown(document: dict[str, Any], output_folder: Path) -> None:
    output_folder.mkdir(parents=True, exist_ok=True)

    output_file = output_folder / f"{Path(document['filename']).stem}.txt"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(document["text"])

if __name__ == "__main__":
    # Procsessing
    documents = load_all_pdfs(RAW_DATA_PATH)
    documents = [add_chunks_to_document(doc) for doc in documents if "text" in doc]
    processed_files = save_documents_to_processed(documents, PROCESSED_DATA_PATH)

    for doc in documents:
        save_markdown(doc, PROCESSED_DATA_PATH)

    # Stats & Validation Setup
    quality_counts = {"good": 0, "empty": 0, "artifact": 0}

    # Lists for reference validation
    valid_refs = []
    suspicious_refs = []
    fallback_refs = []

    print("\n--- Processing Details ---")
    for doc in documents:
        # A. Quality Check
        q = doc.get("quality")
        if q in quality_counts:
            quality_counts[q] += 1

        if q in {"empty", "artifact"}:
            print(f"QUALITY ALERT: {doc['filename']} -> {doc.get('quality_reason')}")

        title = doc.get("title")

        if not title:
            fallback_refs.append(doc["filename"])
        else:
            is_valid = validate_reference_match({"title": title}, doc.get("text", ""))
            if is_valid:
                valid_refs.append(doc["filename"])
            else:
                suspicious_refs.append(f"{doc['filename']} (Ref: {doc.get('reference')})")

    # Final summary output
    print("\n" + "=" * 30)
    print(f"TOTAL DOCUMENTS: {len(documents)}")
    print(f"SAVED FILES:     {len(processed_files)}")
    print("-" * 30)
    print(
        f"QUALITY:    Good: {quality_counts['good']} | Empty/Artifact: {quality_counts['empty'] + quality_counts['artifact']}")
    print(f"REFERENCES: Valid: {len(valid_refs)} | Suspicious: {len(suspicious_refs)} | Fallback: {len(fallback_refs)}")
    print("=" * 30)

    if suspicious_refs:
        print("\nSUSPICIOUS REFERENCES (Check these manually):")
        for item in suspicious_refs:
            print(f"  [!] {item}")

    if fallback_refs:
        print("\nFALLBACKS (No Crossref title found):")
        for item in fallback_refs:
            print(f"  [?] {item}")

    # Journal stats
    journals = [doc.get("journal") for doc in documents if doc.get("journal")]
    if journals:
        print("\nTOP JOURNALS:")
        for journal, count in Counter(journals).most_common(5):
            print(f"  {count}x {journal}")