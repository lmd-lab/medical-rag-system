"""This is the Streamlit app for the Medical RAG Prototype."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import streamlit as st

# Setup project root before local imports to avoid ModuleNotFoundError
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load environment variables before importing modules that might depend on them
load_dotenv()

# tLocal imports
from src.vectorstore import load_vectorstore
from src.rag import generate_answer

# Configuration from environment variables
RAG_TITLE = os.getenv("RAG_TITLE", "Medical RAG System")
RAG_CAPTION = os.getenv("RAG_CAPTION", "Ask a question about the medical literature.")

# UI Components
st.title(RAG_TITLE)
st.caption(RAG_CAPTION)

@st.cache_resource
def load_data():
    """Initializes the vectorstore once and caches the result."""
    return load_vectorstore()

# Initialize data
embeddings, chunks = load_data()

# User Interaction
query = st.text_input("Ask a question:")

if query:
    with st.spinner("Searching and generating answer..."):
        # Process query using the RAG pipeline
        answer = generate_answer(query, embeddings, chunks)

    st.markdown("### Answer")
    st.markdown(answer)
    