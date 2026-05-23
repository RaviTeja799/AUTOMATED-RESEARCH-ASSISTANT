---
title: Automated Research Assistant
emoji: 🔬
colorFrom: indigo
colorTo: purple
sdk: docker
pinned: false
license: mit
short_description: RAG-powered Q&A on academic papers using Groq + Qdrant
---

# Automated Research Assistant

A production-grade RAG system that processes academic PDFs and provides AI-powered research capabilities.

## Stack

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (async) |
| LLM | Groq (`llama-3.1-8b-instant`) |
| Vector Store | Qdrant Cloud |
| Embeddings | sentence-transformers (`all-MiniLM-L6-v2`, 384-dim) |
| Agent | LangChain ReAct |
| PDF Processing | PyMuPDF → pdfplumber → pypdf |

## Features

- Upload and process academic PDFs
- Semantic vector search via Qdrant Cloud
- RAG-based Q&A with source citations and hallucination prevention
- Paper summarization (brief / comprehensive / technical)
- Literature review generation
- LangChain agent with intent routing
- Built-in web UI

## Quick Start

```bash
git clone https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT.git
cd AUTOMATED-RESEARCH-ASSISTANT
cp .env.example .env
# Fill in GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY
pip install -r requirements.txt
python main.py
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `GROQ_API_KEY` | Groq API key (console.groq.com) |
| `QDRANT_URL` | Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | Qdrant Cloud API key |

## GitHub

https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT
