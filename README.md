# Automated Research Assistant

A production-grade research assistant system that processes academic PDFs, performs intelligent retrieval, and provides AI-powered research capabilities using RAG (Retrieval-Augmented Generation).

## Features

- **Document Processing**: Upload and process academic PDFs with intelligent text extraction, cleaning, and section detection
- **Hybrid Search**: Semantic + keyword search using Elasticsearch with dense vectors
- **RAG-based Q&A**: Answer research questions with source citations and hallucination prevention
- **Paper Summarization**: Generate concise summaries of academic papers
- **Literature Reviews**: Automated literature review generation across multiple papers
- **Agent Orchestration**: Intelligent routing using LangChain with ReAct pattern
- **Robust PDF Pipeline**: Multi-library fallback, malformed PDF handling, semantic chunking

## Architecture

```
research-assistant/
├── app/
│   ├── api/              # FastAPI routes and endpoints
│   ├── core/             # Core configuration and settings
│   ├── services/         # Business logic layer
│   ├── agents/           # LangChain/CrewAI agent definitions
│   ├── models/           # Pydantic models and schemas
│   ├── retrieval/        # Retrieval and search logic
│   ├── processing/       # Document processing pipeline
│   ├── prompts/          # LLM prompt templates
│   └── utils/            # Utility functions
├── data/                 # Local data storage
├── logs/                 # Application logs
├── tests/                # Unit and integration tests
├── frontend/             # Optional Streamlit UI
├── requirements.txt
├── .env.example
└── main.py
```

## Tech Stack

- **Backend**: FastAPI
- **LLM**: Ollama (local inference)
- **Vector Store**: Elasticsearch (dense vectors)
- **Embeddings**: sentence-transformers
- **Agent Framework**: LangChain
- **PDF Processing**: PyMuPDF, pdfplumber
- **Language**: Python 3.10+

## Prerequisites

1. **Python 3.10+**
2. **Elasticsearch 8.x** running locally or remotely
3. **Ollama** installed with a model (e.g., `llama3`, `mistral`)

### Install Ollama

```bash
# Linux/Mac
curl -fsSL https://ollama.com/install.sh | sh

# Pull a model
ollama pull llama3
```

### Install Elasticsearch

```bash
# Using Docker
docker run -d \
  --name elasticsearch \
  -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.12.0
```

## Installation

1. **Clone the repository**

```bash
git clone <repository-url>
cd research-assistant
```

2. **Create virtual environment**

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**

```bash
pip install -r requirements.txt
```

4. **Configure environment**

```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run the application**

```bash
python main.py
```

The API will be available at `http://localhost:8000`

## API Endpoints

### Upload Paper
```bash
POST /api/v1/papers/upload
Content-Type: multipart/form-data

# Upload a PDF file
curl -X POST "http://localhost:8000/api/v1/papers/upload" \
  -F "file=@paper.pdf"

# Response includes:
# - paper_id: Unique identifier
# - metadata: Extracted title, authors, abstract, DOI
# - num_chunks: Number of chunks created
# - processing_time: Time taken to process
```

### List Papers
```bash
GET /api/v1/papers?skip=0&limit=10

# Get all uploaded papers with pagination
curl "http://localhost:8000/api/v1/papers?skip=0&limit=10"
```

### Get Paper Info
```bash
GET /api/v1/papers/{paper_id}

# Get detailed information about a specific paper
curl "http://localhost:8000/api/v1/papers/{paper_id}"
```

### Delete Paper
```bash
DELETE /api/v1/papers/{paper_id}

# Delete a paper and all its chunks
curl -X DELETE "http://localhost:8000/api/v1/papers/{paper_id}"
```

### Query Papers
```bash
POST /api/v1/query
Content-Type: application/json

{
  "question": "What are the main findings about transformer architectures?",
  "top_k": 5
}
```

### Summarize Paper
```bash
POST /api/v1/papers/summarize
Content-Type: application/json

{
  "paper_id": "paper-uuid-here"
}
```

### Generate Literature Review
```bash
POST /api/v1/literature-review
Content-Type: application/json

{
  "topic": "transformer models in NLP",
  "max_papers": 10
}
```

### Agent Query
```bash
POST /api/v1/agent
Content-Type: application/json

{
  "query": "Compare the methodologies used in papers about attention mechanisms"
}
```

## Configuration

Key environment variables in `.env`:

- `ELASTICSEARCH_URL`: Elasticsearch connection URL
- `OLLAMA_BASE_URL`: Ollama API endpoint
- `OLLAMA_MODEL`: Model name (e.g., llama3)
- `EMBEDDING_MODEL`: Sentence transformer model
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Development

### Test PDF Pipeline
```bash
# Process a PDF file
python scripts/test_pdf_pipeline.py process path/to/paper.pdf

# List all papers
python scripts/test_pdf_pipeline.py list

# Delete a paper
python scripts/test_pdf_pipeline.py delete PAPER_ID
```

### Run tests
```bash
pytest tests/
```

### Run with auto-reload
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Format code
```bash
black app/
isort app/
```

### Setup Elasticsearch indices
```bash
python scripts/setup_elasticsearch.py
```

## Frontend (Optional)

A simple Streamlit interface is provided:

```bash
streamlit run frontend/app.py
```

## Project Structure Details

- **api/**: FastAPI routers and endpoint definitions
- **services/**: Core business logic (document service, query service, etc.)
- **agents/**: LangChain agent definitions and tools
- **models/**: Pydantic schemas for request/response validation
- **retrieval/**: Elasticsearch integration and hybrid search
- **processing/**: PDF parsing, text extraction, chunking
- **prompts/**: Centralized prompt templates
- **utils/**: Logging, helpers, decorators

## Features in Detail

### PDF Ingestion Pipeline
Complete pipeline for processing academic papers:
1. **Text Extraction**: Multi-library fallback (PyMuPDF → pdfplumber → pypdf)
2. **Preprocessing**: Whitespace normalization, header/footer removal, hyphenation fixing
3. **Section Detection**: Automatic detection of Abstract, Introduction, Methods, Results, etc.
4. **Semantic Chunking**: Sentence-aware chunking that respects section boundaries
5. **Embedding Generation**: 384-dim vectors using sentence-transformers
6. **Elasticsearch Indexing**: Hybrid search with dense vectors and BM25

See [PDF_INGESTION_PIPELINE.md](PDF_INGESTION_PIPELINE.md) for detailed documentation.

### Intelligent Chunking
Documents are chunked by sections (Abstract, Introduction, Methods, etc.) to preserve semantic coherence. Chunks never break mid-sentence and include configurable overlap.

### Hybrid Retrieval
Combines semantic similarity (dense vectors) with keyword matching (BM25) using Reciprocal Rank Fusion (RRF) for optimal retrieval.

### Source-Aware Answers
All answers include citations with paper titles, authors, page numbers, and relevance scores. Implements 6 hallucination prevention strategies.

### Agent Orchestration
The system intelligently routes queries to appropriate tools using LangChain ReAct pattern:
- Simple questions → Direct RAG
- Summarization requests → Summarization pipeline
- Comparative analysis → Multi-document retrieval
- Literature reviews → Structured generation

### Malformed PDF Handling
Robust error handling with multiple extraction strategies ensures maximum compatibility with various PDF formats.

## Performance Considerations

- Async processing for I/O operations
- Batch embedding generation
- Connection pooling for Elasticsearch
- Configurable chunk sizes and overlap
- Caching for frequently accessed papers

## Security

- Input validation using Pydantic
- File type verification for uploads
- Size limits on uploaded files
- Environment-based secrets management
- No hardcoded credentials

## Troubleshooting

### Elasticsearch connection issues
```bash
# Check if Elasticsearch is running
curl http://localhost:9200

# Check logs
docker logs elasticsearch
```

### Ollama issues
```bash
# Check if Ollama is running
ollama list

# Test model
ollama run llama3 "Hello"
```

### Memory issues
- Reduce batch sizes in config
- Use smaller embedding models
- Limit concurrent requests

## License

MIT License

## Contributing

Contributions welcome! Please read CONTRIBUTING.md for guidelines.

## Roadmap

- [x] PDF ingestion pipeline with section detection
- [x] Hybrid search with Elasticsearch
- [x] RAG with citation-aware answers
- [x] LangChain agent orchestration
- [x] Hallucination prevention strategies
- [ ] Multi-language support
- [ ] Advanced citation extraction and linking
- [ ] Graph-based paper relationships
- [ ] Collaborative filtering
- [ ] Export to BibTeX
- [ ] Integration with reference managers
- [ ] OCR support for image-based PDFs
- [ ] Table and figure extraction

## Contact

For issues and questions, please open a GitHub issue.
