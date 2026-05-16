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
| PDF Processing | PyMuPDF → pdfplumber → pypdf (fallback chain) |

## Features

- Upload and process academic PDFs (text extraction, section detection, semantic chunking)
- Semantic vector search via Qdrant Cloud
- RAG-based Q&A with source citations and hallucination prevention
- Paper summarization (brief / comprehensive / technical)
- Literature review generation
- LangChain agent with intent routing and conversation memory
- Built-in web UI at `http://localhost:8000`

## Quick Start

```bash
git clone https://github.com/vamsi-op/AUTOMATED-RESEARCH-ASSISTANT.git
cd AUTOMATED-RESEARCH-ASSISTANT

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Fill in GROQ_API_KEY, QDRANT_URL, QDRANT_API_KEY

# Run
python main.py
```

Open **http://localhost:8000** — the UI loads automatically.
API docs at **http://localhost:8000/docs**.

## Docker

```bash
cp .env.example .env   # fill in your keys
docker-compose up
```

## Environment Variables

See `.env.example` for all options. Required:

```env
GROQ_API_KEY=gsk_...
QDRANT_URL=https://your-cluster.cloud.qdrant.io
QDRANT_API_KEY=eyJ...
```

Get free keys:
- Groq: https://console.groq.com
- Qdrant Cloud: https://cloud.qdrant.io

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/papers/upload` | Upload a PDF |
| GET | `/api/v1/papers` | List indexed papers |
| GET | `/api/v1/papers/{id}` | Get paper info |
| DELETE | `/api/v1/papers/{id}` | Delete a paper |
| POST | `/api/v1/query` | Ask a question (RAG) |
| POST | `/api/v1/summarize` | Summarize a paper |
| POST | `/api/v1/literature-review` | Generate literature review |
| POST | `/api/v1/agent` | Agent query with tool routing |
| GET | `/api/v1/health` | Health check |

## Project Structure

```
app/
├── api/v1/          # FastAPI routers
├── core/            # Config, exceptions
├── services/        # Business logic (query, document, summarize, literature, agent)
├── agents/          # LangChain tools and ReAct agent
├── retrieval/       # Qdrant client, hybrid retriever
├── processing/      # PDF extraction, preprocessing, chunking
├── prompts/         # RAG prompt templates
└── utils/           # Logging

frontend/            # Single-page web UI
data/uploads/        # Uploaded PDFs
```

## Roadmap

- [ ] Multi-language support
- [ ] OCR for image-based PDFs
- [ ] Citation graph visualization
- [ ] Export to BibTeX
- [ ] Table and figure extraction
