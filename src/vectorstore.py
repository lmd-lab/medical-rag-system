"""
This module is responsible for loading the vectorstore
"""
import json
import numpy as np


from config import VECTORSTORE_PATH

def load_vectorstore():
    """Loads the vectorstore including the 
    embeddings and the corresponding chunks."""
    embeddings_path = VECTORSTORE_PATH / "embeddings.npy"
    chunks_path = VECTORSTORE_PATH / "chunks.json"

    embeddings = np.load(embeddings_path)

    with open(chunks_path, encoding="utf-8") as f:
        chunks = json.load(f)

    # check that the number of chunks matches the number of embeddings
    assert len(chunks) == embeddings.shape[0], \
        f"Mismatch: {len(chunks)} chunks vs {embeddings.shape[0]} embeddings"

    return embeddings, chunks