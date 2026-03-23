# Medical RAG System

A minimal retrieval-augmented generation (RAG) system for querying local PDF documents.

## Goal

Build a simple local pipeline that:

- extracts text from PDF files
- splits text into chunks
- creates embeddings
- stores embeddings in a vector database
- retrieves relevant context for user queries
- generates answers with source references


## Project Structure
```text
.
│
├── data/
│   ├── raw/                 # Original PDFs
│   ├── processed/           # Extracted text / prepared files
│   └── vectorstore/         # Stored embeddings / FAISS index
│
├── src/
│   ├── ingestion.py         # PDF → Text
│   ├── chunking.py          # Text → Chunks
│   ├── embedding.py         # Generate embeddings
│   ├── vectorstore.py       # FAISS / Chroma handling
│   ├── rag.py               # Retrieval + prompting
│   └── utils.py             # Small utility functions
│
├── app/
│   └── streamlit_app.py     # UI
│
├── tests/                   # Simple tests
│
├── config.py                # Central configuration parameters
├── LICENSE                  # MIT License
├── .gitignore
└── README.md                # Project documentation

```

## Goal

Build a simple local pipeline that:

- extracts text from PDF files
- splits text into chunks
- creates embeddings
- stores embeddings in a vector database
- retrieves relevant context for user queries
- generates answers with source references

## MVP Scope

Current MVP includes:

local PDF files only
no OCR
no database
no automatic updates
simple Streamlit interface

## Planned Pipeline

PDFs → Text Extraction → Chunking → Embeddings → Vector Store → Retrieval → Answer Generation

First Steps
 Implement PDF loading
 Extract text
 Chunk text
 Create embeddings
 Test retrieval
 Build simple UI

## Notes

This project is intentionally developed iteratively.
The first goal is a working prototype, not a perfect architecture.