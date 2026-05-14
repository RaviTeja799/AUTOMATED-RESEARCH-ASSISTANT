# Quick Start Guide

## Prerequisites

1. **Python 3.10+**
2. **Elasticsearch 8.x**
3. **Ollama** with a model installed

---

## Installation

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Start Elasticsearch

**Using Docker:**
```bash
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.12.0
```

**Verify Elasticsearch:**
```bash
curl http://localhost:9200
```

### 3. Install and Start Ollama

**Install Ollama:**
```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Windows: Download from https://ollama.com/download
```

**Pull a model:**
```bash
ollama pull llama3
```

**Verify Ollama:**
```bash
ollama list
```

### 4. Configure Environment

```bash
cp .env.example .env
```

Edit `.env` if needed (defaults work for local development):
```env
ELASTICSEARCH_URL=http://localhost:9200
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
CHUNK_SIZE=512
CHUNK_OVERLAP=50
```

### 5. Initialize Elasticsearch Indices

```bash
python scripts/setup_elasticsearch.py
```

---

## Running the Application

### Development Mode

```bash
python main.py
```

The API will be available at:
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### Production Mode

```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

---

## Testing the API

### 1. Health Check

```bash
curl http://localhost:8000/api/v1/health
```

**Expected Response:**
```json
{
  "status": "healthy",
  "version": "1.0.0",
  "elasticsearch_connected": true,
  "ollama_available": true,
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### 2. Upload a Paper

```bash
curl -X POST "http://localhost:8000/api/v1/papers/upload" \
  -F "file=@paper.pdf"
```

**Response:**
```json
{
  "paper_id": "3f7a1b2c-...",
  "filename": "paper.pdf",
  "status": "success",
  "message": "Successfully processed 45 chunks",
  "metadata": {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani", "Shazeer"],
    "abstract": "...",
    "num_pages": 15,
    "doi": "10.48550/arXiv.1706.03762"
  },
  "num_chunks": 45,
  "processing_time": 2.34
}
```

### 3. List Papers

```bash
curl "http://localhost:8000/api/v1/papers?skip=0&limit=10"
```

### 4. Query Papers

```bash
curl -X POST "http://localhost:8000/api/v1/query" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the main findings about transformer architectures?",
    "top_k": 5
  }'
```

**Response:**
```json
{
  "answer": "Based on the retrieved papers, transformer architectures...",
  "citations": [
    {
      "paper_id": "...",
      "paper_title": "Attention Is All You Need",
      "authors": ["Vaswani et al."],
      "chunk_id": "...",
      "page_number": 3,
      "relevance_score": 0.92,
      "text_snippet": "..."
    }
  ],
  "confidence": 0.87,
  "processing_time": 1.23,
  "retrieved_chunks": 5
}
```

### 5. Summarize a Paper

```bash
curl -X POST "http://localhost:8000/api/v1/summarize" \
  -H "Content-Type: application/json" \
  -d '{
    "paper_id": "3f7a1b2c-...",
    "summary_type": "comprehensive"
  }'
```

### 6. Generate Literature Review

```bash
curl -X POST "http://localhost:8000/api/v1/literature/review" \
  -H "Content-Type: application/json" \
  -d '{
    "topic": "transformer models in NLP",
    "max_papers": 10
  }'
```

### 7. Use the Agent

```bash
curl -X POST "http://localhost:8000/api/v1/agent" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "Compare the methodologies used in the uploaded papers and identify research gaps"
  }'
```

---

## Test the PDF Pipeline Directly

```bash
# Process a PDF with detailed output
python scripts/test_pdf_pipeline.py process path/to/paper.pdf

# List all indexed papers
python scripts/test_pdf_pipeline.py list

# Delete a paper
python scripts/test_pdf_pipeline.py delete PAPER_ID
```

---

## PDF Ingestion Pipeline

The pipeline processes PDFs through these stages:

```
PDF Upload → Text Extraction → Preprocessing → Section Detection
    → Semantic Chunking → Embedding Generation → Elasticsearch Indexing
```

**Extraction fallback chain**: PyMuPDF → pdfplumber → pypdf

**Sections detected automatically**:
- Abstract, Introduction, Background
- Methodology / Methods
- Results / Experiments
- Discussion / Analysis
- Conclusion

See [PDF_INGESTION_PIPELINE.md](PDF_INGESTION_PIPELINE.md) for full details.

---

## Project Structure

```
app/
├── api/v1/           # FastAPI routers (papers, query, summarize, literature, agent)
├── core/             # Config, exceptions, security
├── models/           # Pydantic schemas
├── services/         # Business logic
│   ├── document_service.py     # Full PDF pipeline orchestration
│   ├── query_service.py        # RAG with citation-aware answers
│   ├── embedding_service.py    # sentence-transformers embeddings
│   ├── llm_service.py          # Ollama LLM integration
│   ├── summarization_service.py
│   ├── literature_service.py
│   └── agent_service.py        # LangChain agent integration
├── agents/           # LangChain tools and ReAct agent
├── retrieval/        # Elasticsearch hybrid search
├── processing/       # PDF extraction, preprocessing, chunking
├── prompts/          # RAG and agent prompt templates
└── utils/            # Logging

data/
├── uploads/          # Uploaded PDFs (named {paper_id}_{filename})
└── processed/        # Processed documents

scripts/
├── setup_elasticsearch.py   # Initialize ES indices
└── test_pdf_pipeline.py     # Pipeline test script
```

---

## Common Issues

### Elasticsearch Connection Failed

**Problem:** `ServiceUnavailableError: Elasticsearch`

**Solution:**
```bash
# Check if running
curl http://localhost:9200

# Check Docker logs
docker logs elasticsearch

# Restart
docker restart elasticsearch
```

### Ollama Not Available

**Problem:** `ServiceUnavailableError: LLM Service`

**Solution:**
```bash
# Check if running
ollama list

# Ensure model is pulled
ollama pull llama3

# Test model
ollama run llama3 "Hello"
```

### PDF Processing Fails

- Ensure PDF is not password-protected
- Check file size (default max: 50MB)
- Check logs: `tail -f logs/app.log`
- Try the test script: `python scripts/test_pdf_pipeline.py process paper.pdf`

### Out of Memory During Embedding

Reduce batch size in `.env`:
```env
EMBEDDING_BATCH_SIZE=8
CHUNK_SIZE=256
```

### Port Already in Use

```bash
# Windows
netstat -ano | findstr :8000

# Kill process or use different port
uvicorn app.main:app --port 8001
```

---

## Development Workflow

### Run with Auto-Reload

```bash
python main.py
```

### Check Logs

```bash
# Windows
type logs\app.log

# Linux/Mac
tail -f logs/app.log
```

### Format Code

```bash
black app/
isort app/
```

### Type Check

```bash
mypy app/
```

---

## Resources

- **FastAPI Docs**: https://fastapi.tiangolo.com/
- **Elasticsearch Docs**: https://www.elastic.co/guide/
- **Ollama Docs**: https://ollama.com/docs
- **LangChain Docs**: https://python.langchain.com/
- **Architecture**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **PDF Pipeline**: [PDF_INGESTION_PIPELINE.md](PDF_INGESTION_PIPELINE.md)
- **RAG Pipeline**: [RAG_PIPELINE.md](RAG_PIPELINE.md)
- **Agent Workflow**: [AGENT_WORKFLOW.md](AGENT_WORKFLOW.md)
- **ES Mappings**: [ELASTICSEARCH_MAPPINGS.md](ELASTICSEARCH_MAPPINGS.md)
