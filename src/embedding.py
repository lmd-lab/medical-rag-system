"""
This script runs the embedding pipeline for the medical RAG system. 
It performs the following steps:
1. Loads processed documents from the data/processed directory.
2. Flattens the chunks from all documents into a single list.
3. Prepares the text for embedding by adding a "passage: " prefix.
4. Loads the BAAI/bge-m3 model from Hugging Face.
5. Generates normalized embeddings for all chunks.
6. Saves the embeddings as a NumPy array and the corresponding 
chunks as a JSON file in the data/vectorstore directory.
"""

# todo: implement id-tracking for chunks (chunk_id)

import os
import json
import logging

import numpy as np
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

from config import PROCESSED_DATA_PATH, VECTORSTORE_PATH

# ---------------- Logging -----------------------

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("Logs/embedding.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


# ---------------- Main Pipeline -----------------------

def run_embedding_pipeline():
    """Runs the embedding pipeline for the medical RAG system."""

    logger.info("Starting embedding pipeline...")

    load_dotenv()

    # Paths
    processed_path = PROCESSED_DATA_PATH
    output_path = VECTORSTORE_PATH

    output_path.mkdir(parents=True, exist_ok=True)

    # ---------------- Load Documents -----------------------

    logger.info("Loading documents from %s", processed_path)

    files = list(processed_path.glob("*.json"))
    documents = []

    for file in files:
        try:
            with open(file, "r", encoding="utf-8") as f:
                documents.append(json.load(f))
        except (OSError, json.JSONDecodeError) as e:
            logger.warning("Skipping %s: %s", file.name, e)

    logger.info("Loaded %d documents", len(documents))

    # ---------------- Flatten Chunks -----------------------

    all_chunks = []

    for doc in documents:
        for chunk in doc["chunks"]:
            all_chunks.append({
                **chunk,
                "filename": doc.get("filename", "unknown")
            })

    logger.info("Total chunks: %d", len(all_chunks))

    # ---------------- Prepare Texts -----------------------

    texts = ["passage: " + chunk["text"] for chunk in all_chunks]

    logger.info("Texts prepared for embedding")

    # ---------------- Load Model -----------------------

    logger.info("Loading embedding model (BAAI/bge-m3)...")

    model = SentenceTransformer(
        "BAAI/bge-m3",
        cache_folder=os.path.expanduser("~/.cache/huggingface/hub")
    )

    logger.info("Model loaded")

    # ---------------- Generate Embeddings -----------------------

    logger.info("Generating embeddings...")

    embeddings = model.encode(
        texts,
        batch_size=6,
        show_progress_bar=True,
        normalize_embeddings=True,
        device="cpu"
    )

    logger.info("Embeddings shape: %s", embeddings.shape)

    # ---------------- Save -----------------------

    logger.info("Saving embeddings...")

    np.save(output_path / "embeddings.npy", embeddings)

    logger.info("Saving chunks...")

    with open(output_path / "chunks.json", "w", encoding="utf-8") as f:
        json.dump(all_chunks, f, ensure_ascii=False)

    logger.info("Embedding pipeline finished successfully.")


# ---------------- Run -----------------------

if __name__ == "__main__":
    run_embedding_pipeline()
    