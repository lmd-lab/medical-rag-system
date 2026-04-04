# Medical RAG Prototype

A minimal local retrieval-augmented generation (RAG) prototype for processing and querying medical documents.

## Project Goal

The goal of this project is to build a simple but functional prototype that transforms unstructured medical PDF documents into semantically searchable text chunks.

The current implementation focuses on scientific PDF documents as a technical development basis, while the long-term target is the processing of clinical documents such as physician letters.

The project intentionally follows an MVP approach:

- stable end-to-end processing
- pragmatic heuristics
- iterative improvement over full complexity

The primary goal is to establish a reliable pipeline before expanding complexity.

## Core Pipeline

PDF → Extraction → Cleaning → Chunking → Embeddings → Vector Store → Retrieval → Answer Generation

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
│   ├── ingestion.py            # PDF → Text
|   ├── cleaning.py             # Text cleaning
|   ├── crossref_citations.py   # Metadata enrichment
│   ├── chunking.py             # Text → Chunks
│   ├── embedding.py            # Generate embeddings
│   ├── vectorstore.py          # FAISS / Chroma handling
│   ├── rag.py                  # Retrieval + prompting
│   └── utils.py                # Utility functions
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

## MVP Scope

Current MVP intentionally includes only:

- local PDF files
- no OCR
- local vector storage
- no automated updates
- lightweight Streamlit interface

## Installation & Setup

This project uses **Conda** to manage the Python environment and its dependencies (including specialized libraries for vector search and PDF processing).

### 1. Prerequisites
Ensure you have [Conda](https://docs.conda.io/en/latest/miniconda.html) or [Mamba](https://mamba.readthedocs.io/) installed on your system.

### 2. Create the Environment
The environment is defined in the `environment.yml` file. To create it, run:

```bash
conda env create -f environment.yml
```

### 3. Activate the Environment

Once the installation is complete, activate the environment using:
Bash
```bash
conda activate rag-project
```

### 4. Keeping the Environment Updated

If the environment.yml is updated, you can synchronize your local environment by running:
Bash

```bash
conda env update -f environment.yml --prune
```


### Current environment note

Separate environments currently exist because extraction and embedding require different package constraints:

- env_ingestion.yml
- env_embedding.yml

## Development Philosophy

This project is intentionally developed iteratively.

Main principle:

A working prototype is more valuable than an unfinished perfect architecture.

Priorities:

- stability before elegance
- simple heuristics before complex document logic
- selective refactoring only when necessary

# Next Steps
- stabilize extraction across multiple document types
- validate chunk quality
- improve metadata consistency
- test retrieval quality
- prepare transition toward clinical document use