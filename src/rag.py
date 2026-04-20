"""This module implements the retrieval function for the RAG system."""
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

model = SentenceTransformer("BAAI/bge-m3")

def retrieve(query, embeddings, chunks, top_k=5):
    """Retrieves the most relevant chunks for a 
    given query based on cosine similarity."""
    # --- Prepare query ---
    query = "query: " + query

    query_embedding = model.encode(
        [query],
        normalize_embeddings=True
    )

    # --- Cosine similarity ---
    scores = cosine_similarity(query_embedding, embeddings)[0]

    # --- Score + Chunk  ---
    scored_chunks = []
    for i, chunk in enumerate(chunks):
        score = scores[i]

<<<<<<< HEAD
        # minimal bonus for newer papers
=======
        # minimal bonus for newer papers 
>>>>>>> 9a6eb1da4c9f474d55d81e4acad66315bb08d239
        year = chunk.get("metadata", {}).get("year")
        try:
            year = int(year)
            score += (year - 2000) * 0.001
        except (TypeError, ValueError):
            pass
        scored_chunks.append((score, chunk))

    # --- sort ---
    scored_chunks.sort(key=lambda x: x[0], reverse=True)

    # --- remove duplicates ---
    seen_texts = set()
    unique_chunks = []

    for score, chunk in scored_chunks:
        text = chunk.get("text", "")

        if text not in seen_texts:
            seen_texts.add(text)
            unique_chunks.append((score, chunk))

    # --- one chunk per reference ---
    seen_refs = set()
    final_chunks = []

    for score, chunk in unique_chunks:
        ref = chunk.get("metadata", {}).get("reference")

        if ref not in seen_refs:
            seen_refs.add(ref)
            final_chunks.append(chunk)

        if len(final_chunks) >= top_k:
            break

    return final_chunks
