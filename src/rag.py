"""This module implements the retrieval function for the RAG system."""
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")


def retrieve(query, embeddings, chunks, top_k=5):
    """Retrieves the top_k most relevant chunks for 
    the given query based on cosine similarity."""
    query = "query: " + query

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    scores = cosine_similarity(query_embedding, embeddings)[0]

    top_idx = scores.argsort()[-top_k:][::-1]

    return [chunks[i] for i in top_idx]