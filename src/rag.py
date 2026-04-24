"""This module implements the retrieval function for the RAG system."""
import os
from dotenv import load_dotenv
from pathlib import Path
from groq import Groq

from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer

load_dotenv(dotenv_path=Path(__file__).parent.parent / ".env")

RAG_PROMPT = os.getenv("RAG_PROMPT", "Answer the question based on the following context:\n\n{context}\n\nQuestion: {query}\nAnswer:")

model = SentenceTransformer("BAAI/bge-m3")

def get_client():
    api_key = os.getenv("GROQ_API_KEY")

    if not api_key:
        raise ValueError("GROQ_API_KEY not found. Check your .env file.")

    return Groq(api_key=api_key)

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

        # minimal bonus for newer papers
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


def generate_answer(query, embeddings, chunks, top_k=5) -> str:
    """Generates an answer for the given query using retrieved chunks and Groq LLM."""
    client = get_client()

    # --- 1. Retrieval ---
    retrieved_chunks = retrieve(query, embeddings, chunks, top_k=top_k)

    # --- 2. Context build ---
    context_blocks = []
    sources = []

    for i, chunk in enumerate(retrieved_chunks):
        text = chunk.get("text", "")
        meta = chunk.get("metadata", {})

        ref = meta.get("reference") or "Unknown source"

        context_blocks.append(f"[{i+1}] {text}")
        sources.append(f"[{i+1}] {ref}")

    context = "\n\n".join(context_blocks)

    # --- 3. Prompt ---
    prompt = RAG_PROMPT.format(
            context=context,
            query=query
        )

    # --- 4. LLM Call (Groq) ---
    response = client.chat.completions.create(
        model="llama-3.1-8b-instant", 
        messages=[
            {"role": "user", "content": prompt}
        ],
        temperature=0.2  # less hallucinations, more focused on the context
    )

    answer = response.choices[0].message.content

    # --- 5. Sources append ---
    sources_text = "\n".join(sources)

    final_answer = f"{answer}\n\nSources:\n{sources_text}"

    return final_answer
