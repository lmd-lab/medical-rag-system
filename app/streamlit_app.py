"""This is the Streamlit app for the Medical RAG Prototype."""

import sys
from pathlib import Path

# Put project root on sys.path first so `from src...` works reliably.
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Third-party imports
from dotenv import load_dotenv
import streamlit as st

# Load .env before importing src.rag (the model is initialized at import time there).
load_dotenv()

# Project imports
from src.vectorstore import load_vectorstore
from src.rag import retrieve

st.title("Medical RAG Prototype")

# Load once
@st.cache_resource
def load_data():
    return load_vectorstore()

embeddings, chunks = load_data()

query = st.text_input("Ask a question:")

if query:
    results = retrieve(query, embeddings, chunks)

    st.subheader("Top Results")

    for i, r in enumerate(results):
        st.markdown(f"### Result {i+1}")

        st.write(r["text"][:500] + "...")

        if "metadata" in r:
            st.write(r["metadata"])

        st.markdown("---")