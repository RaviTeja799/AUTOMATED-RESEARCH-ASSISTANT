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
<div align="center">

# ðŸ”¬ Automated Research Assistant

**RAG-powered Q&A on academic papers**

[![Live Demo](https://img.shields.io/badge/ðŸ¤—%20HuggingFace-Live%20Demo-orange)](https://vamsi-op-automated-research-assistant.hf.space)
[![GitHub](https://img.shields.io/badge/GitHub-Repository-black)](https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Upload academic PDFs â†’ Ask questions â†’ Get cited answers

</div>

---

## ðŸš€ Live Demo

**[https://vamsi-op-automated-research-assistant.hf.space](https://vamsi-op-automated-research-assistant.hf.space)**

---

## âœ¨ Features

| Feature | Description |
|---------|-------------|
| ðŸ“„ **PDF Upload** | Drag-and-drop with duplicate detection |
| ðŸ’¬ **RAG Q&A** | Answers with citations and confidence scores |
| ðŸ“ **Summarization** | Brief, comprehensive, or technical summaries |
| ðŸ“Š **Literature Review** | Themes, gaps, and future directions |
| ðŸ¤– **Agent** | LangChain ReAct with intent routing |
| ðŸ” **Semantic Search** | 384-dim vector search via Qdrant Cloud |
| ðŸ›¡ï¸ **Hallucination Prevention** | Citation enforcement + grounding rules |

---

## ðŸ—ï¸ Architecture

```
Browser / API Client
        â”‚
        â–¼
   FastAPI (uvicorn)
        â”‚
   â”Œâ”€â”€â”€â”€â”´â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
   â”‚                               â”‚
   â–¼                               â–¼
Groq API                    Qdrant Cloud
(llama-3.1-8b-instant)    (vector store, 384-dim)
                                   â”‚
                                   â–¼
                         sentence-transformers
                         (all-MiniLM-L6-v2, local)
```

**Stack:**

| Component | Technology |
|-----------|-----------|
| Backend | FastAPI (async) |
| LLM | Groq `llama-3.1-8b-instant` |
| Vector Store | Qdrant Cloud |
| Embeddings | sentence-transformers `all-MiniLM-L6-v2` (384-dim) |
| Agent | LangChain ReAct + 5 tools |
| PDF Processing | PyMuPDF â†’ pdfplumber â†’ pypdf (fallback chain) |
| Frontend | Vanilla JS + Tailwind CSS |

---

## ðŸš¦ Quick Start

### Prerequisites
- Python 3.11+
- Free [Groq API key](https://console.groq.com)
- Free [Qdrant Cloud cluster](https://cloud.qdrant.io)

### Run locally

```bash
git clone https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT.git
cd AUTOMATED-RESEARCH-ASSISTANT

pip install -r requirements.txt

cp .env.example .env
# Edit .env with your keys

python main.py
# Open http://localhost:8000
```

### Run with Docker

```bash
cp .env.example .env   # fill in your keys
docker-compose up
```

---

## âš™ï¸ Environment Variables

Copy `.env.example` to `.env` and fill in:

| Variable | Required | Description |
|----------|----------|-------------|
| `GROQ_API_KEY` | âœ… | Get free at [console.groq.com](https://console.groq.com) |
| `QDRANT_URL` | âœ… | Your Qdrant Cloud cluster URL |
| `QDRANT_API_KEY` | âœ… | Your Qdrant Cloud API key |
| `GROQ_MODEL` | optional | Default: `llama-3.1-8b-instant` |
| `EMBEDDING_MODEL` | optional | Default: `sentence-transformers/all-MiniLM-L6-v2` |
| `CHUNK_SIZE` | optional | Default: `512` |

---

## ðŸ“¡ API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/papers/upload` | Upload a PDF |
| `GET` | `/api/v1/papers` | List all papers |
| `GET` | `/api/v1/papers/{id}` | Get paper info |
| `DELETE` | `/api/v1/papers/{id}` | Delete a paper |
| `POST` | `/api/v1/query` | Ask a question (RAG) |
| `POST` | `/api/v1/summarize` | Summarize a paper |
| `POST` | `/api/v1/literature-review` | Generate literature review |
| `POST` | `/api/v1/agent` | Agent with tool routing |
| `GET` | `/api/v1/health` | Full health check |

Interactive docs at `/docs`.

---

## ðŸ“ Project Structure

```
app/
â”œâ”€â”€ api/v1/          # FastAPI routers
â”œâ”€â”€ core/            # Config, exceptions
â”œâ”€â”€ services/        # Business logic
â”‚   â”œâ”€â”€ document_service.py     # PDF ingestion pipeline
â”‚   â”œâ”€â”€ query_service.py        # RAG + TTL cache
â”‚   â”œâ”€â”€ embedding_service.py    # sentence-transformers (async)
â”‚   â”œâ”€â”€ llm_service.py          # Groq client
â”‚   â”œâ”€â”€ summarization_service.py
â”‚   â”œâ”€â”€ literature_service.py
â”‚   â””â”€â”€ agent_service.py
â”œâ”€â”€ agents/          # LangChain ReAct agent + tools
â”œâ”€â”€ retrieval/       # Qdrant client, hybrid retriever
â”œâ”€â”€ processing/      # PDF extraction, chunking, preprocessing
â”œâ”€â”€ prompts/         # RAG prompt templates
â”œâ”€â”€ models/          # Pydantic schemas
â””â”€â”€ utils/           # Logging

frontend/            # Single-page web UI
scripts/             # CLI utilities
```

---

## ðŸ”„ How RAG Works

```
Question
  â†’ Embed (384-dim vector)
  â†’ Search Qdrant (cosine similarity, top-5)
  â†’ Build citation-aware prompt
  â†’ Generate answer (Groq, temp=0.3)
  â†’ Extract citations
  â†’ Assess confidence
  â†’ Return answer + citations + confidence
```

**Hallucination prevention:** Every claim must be cited. The system prompt forbids external knowledge and enforces `[Title, Authors, Year]` citation format.

---

## ðŸ› ï¸ Scripts

```bash
# Run a quick demo against a running server
python scripts/demo.py

# Upload a PDF and test all endpoints
python scripts/upload_test.py path/to/paper.pdf

# Benchmark query performance (cache speedup)
python scripts/benchmark.py
```

---

## ðŸ“„ License

MIT â€” see [LICENSE](LICENSE)

---

## ðŸ‘¤ Author

<table>
  <tr>
    <td align="center">
      <a href="https://github.com/vamsi-op">
        <img src="https://github.com/vamsi-op.png" width="80px" alt="Vamsi Puttepu"/><br/>
        <sub><b>Vamsi Puttepu</b></sub>
      </a><br/>
      <a href="https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT/commits?author=vamsi-op">ðŸ’»</a>
    </td>
  </tr>
</table>

---

## ðŸ¤ Contributing

Contributions, issues and feature requests are welcome.

1. Fork the repo
2. Create a branch: `git checkout -b feature/your-feature`
3. Commit your changes: `git commit -m 'feat: add your feature'`
4. Push: `git push origin feature/your-feature`
5. Open a Pull Request

---

<div align="center">
  <sub>Built with â¤ï¸ using FastAPI Â· Groq Â· Qdrant Â· sentence-transformers</sub>
</div>
