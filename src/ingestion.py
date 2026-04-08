"""
This module handles the ingestion of PDF documents
"""

import json
import logging
import os
import re
from pathlib import Path
from typing import Any
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from dotenv import load_dotenv

from config import RAW_DATA_PATH, PROCESSED_DATA_PATH

from src.patterns import DOI_REGEX, PMID_REGEX
from src.cleaning import clean_markdown_text
from src.reference_resolver import get_reference

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["PYTORCH_ENABLE_MPS_FALLBACK"] = "1"

# ---------------- Logging -----------------------

logging.basicConfig(
    level=logging.DEBUG, #INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("Logs/pipeline_debug.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()

# ---------------- Helper Functions ----------------

def extract_doi(text: str) -> str | None:
    """Extracts the DOI from the text using a regex pattern"""
    first_part = text[:6000] # only the first 1-2 pages

    match = DOI_REGEX.search(first_part)
    if match:
        return match.group(1).rstrip(".")

    return None

def extract_pmid(text: str) -> str | None:
    """Extracts the PMID from the text using a regex pattern"""
    first_part = text[:6000]

    match = PMID_REGEX.search(first_part)
    if match:
        return match.group(1)
    return None

def classify_basic_text_quality(text: str) -> tuple[str, str]:
    """Basic heuristic to classify text quality as good or empty."""

    if not text.strip():
        return "empty", "text is empty"

    words = text.split()

    if len(words) < 30:
        return "empty", "too short"

    if not re.search(r"[A-Za-z]{4,}", text):
        return "artifact", "no readable text"

    return "good", ""

def get_first_heading(md_text: str):
    """Extracts the first Markdown heading from the text, 
    which often corresponds to the title or main section."""
    for line in md_text.splitlines():
        if line.startswith("#"):
            return line.replace("#", "").strip()
    return None

# ---------------- Extract text and metadata from PDF -------------------------------------------

def extract_text(pdf_path: Path) -> dict[str, Any]:
    """Extracts text and metadata from a PDF file using docling"""
    # ignore pictures but use ocr for bad PDFs
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = True
    pipeline_options.generate_page_images = False
    pipeline_options.generate_table_images = False  # no pictures of tables?
    pipeline_options.do_table_structure = True # skips tables
    pipeline_options.table_structure_options.do_cell_matching = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    try:
        result = converter.convert(str(pdf_path))

        # Markdown without images
        markdown_text = result.document.export_to_markdown()

        # check quality and get doi
        quality, quality_reason = classify_basic_text_quality(markdown_text)

        # get doi and pmid
        doi = extract_doi(markdown_text)
        pmid = extract_pmid(markdown_text)

        # get first heading
        first_heading = get_first_heading(markdown_text)

        # build reference for chunking
        reference = get_reference(
            doi=doi,
            filename=pdf_path.name,
            query_title=first_heading,
            text=markdown_text,
        )

        # MOVE TO CLEANING: Remove journal name from text to reduce noise for chunking and embedding
        # remove journal if present in reference from text to reduce noise
        # cleaned_markdown = remove_journal_from_text(cleaned_markdown,
        #                                            reference,
        #                                        filename=pdf_path.name)
        # TO-DO: use the reference to also remove author names, affiliations, etc. from the text to reduce noise for chunking and embedding

        # clean Markdown from artifacts
        cleaned_markdown = clean_markdown_text(markdown_text, filename=pdf_path.name, author=reference.get("author"))


        return {
            "filename": pdf_path.name,
            "path": str(pdf_path),
            "first_heading": first_heading,
            "author": reference.get("author"),
            "title": reference.get("title"),
            "year": reference.get("year"),
            "journal": reference.get("journal"),
            "publisher": reference.get("publisher"),
            "type": reference.get("type"),
            "doi": doi,
            "pmid": pmid,
            "reference": reference.get("reference"),
            "reference_source": reference.get("source"),
            "quality": quality,
            "quality_reason": quality_reason,
            "processing_method": "docling_v2_optimized",
            "text": cleaned_markdown.strip(),
        }
    except (FileNotFoundError, ValueError, IOError) as e:
        print(f"Error processing {pdf_path}: {e}")
        return {"filename": pdf_path.name, "error": str(e)}
    except Exception as e:
        print(f"Unexpected error processing {pdf_path}: {e}")
        raise

# ---------------- Load and save results ----------------------------

def load_all_pdfs(folder_path: Path) -> list[dict[str, Any]]:
    """Loads and processes all PDF files in the specified folder, 
    returning a list of document dictionaries."""
    pdf_documents: list[dict[str, Any]] = []

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
            pdf_documents.append(extract_text(pdf_file))
        except (FileNotFoundError, IOError) as e:
            print(f"Failed: {pdf_file.name} -> {e}")
            continue  # Oder andere Fehlerbehandlung
        except Exception as e:
            print(f"Unexpected error: {pdf_file.name} -> {e}")
            raise

    return pdf_documents

def save_documents_to_processed(
    docs: list[dict[str, Any]],
    output_folder: Path,
) -> list[Path]:
    """Saves the processed document dictionaries to 
    JSON /md files in the specified output folder."""
    output_folder.mkdir(parents=True, exist_ok=True)

    saved_files: list[Path] = []

    for document in docs:
        output_path = output_folder / f"{Path(document['filename']).stem}.json"

        with output_path.open("w", encoding="utf-8") as f:
            json.dump(document, f, ensure_ascii=False, indent=2, default=str)

        saved_files.append(output_path)

    for document in docs:
        output_path = output_folder / f"{Path(document['filename']).stem}.md"

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(document["text"])

    return saved_files

# ---------------- Main execution ---------------------------------------

if __name__ == "__main__":
    # Procsessing
    documents = load_all_pdfs(RAW_DATA_PATH)
    #documents = [add_chunks_to_document(doc) for doc in documents if "text" in doc]
    processed_files = save_documents_to_processed(documents, PROCESSED_DATA_PATH)

    # Stats & Validation Setup
    quality_counts = {"good": 0, "empty": 0, "artifact": 0}

    # Lists for reference validation
    reference_stats = {
            "doi": 0,
            "filename": 0,
            "title": 0,
            "nlm": 0,
            "fallback": 0,
        }
    
    for doc in documents:
        # A. Quality Check
        q = doc.get("quality")
        if q in quality_counts:
            quality_counts[q] += 1

        # B. Reference source stats
        source = doc.get("reference_source")
        if source in reference_stats:
            reference_stats[source] += 1

        if q in {"empty", "artifact"}:
            print(f"QUALITY ALERT: {doc['filename']} -> {doc.get('quality_reason')}")

    logger.info("Reference stats: %s", reference_stats)
    logger.info("Quality stats: %s", quality_counts)