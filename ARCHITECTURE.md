# **Automated Research Assistant - Complete Architecture Design**

## **1. System Overview**

The Automated Research Assistant is a production-grade RAG system that processes academic papers, performs intelligent retrieval, and provides AI-powered research capabilities through agent orchestration.

### **Core Capabilities**
- PDF upload and intelligent processing
- Hybrid semantic + keyword search
- RAG-based question answering with citations
- Paper summarization
- Literature review generation
- Agent-based task routing

---

## **2. Complete Folder Structure**

```
research-assistant/
├── app/
│   ├── __init__.py
│   ├── main.py                      # FastAPI application entry
│   │
│   ├── api/                         # API Layer
│   │   ├── __init__.py
│   │   ├── deps.py                  # Dependency injection
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── router.py            # Main router aggregator
│   │   │   ├── papers.py            # Paper upload/management endpoints
│   │   │   ├── query.py             # Query endpoints
│   │   │   ├── summarize.py         # Summarization endpoints
│   │   │   ├── literature.py        # Literature review endpoints
│   │   │   └── health.py            # Health check endpoints
│   │
│   ├── core/                        # Core Configuration
│   │   ├── __init__.py
│   │   ├── config.py                # Settings (Pydantic)
│   │   ├── security.py              # Security utilities
│   │   └── exceptions.py            # Custom exceptions
│   │
│   ├── models/                      # Data Models
│   │   ├── __init__.py
│   │   ├── schemas.py               # Pydantic request/response models
│   │   └── domain.py                # Domain models
│   │
│   ├── services/                    # Business Logic Layer
│   │   ├── __init__.py
│   │   ├── document_service.py      # Document processing orchestration
│   │   ├── query_service.py         # Query handling
│   │   ├── summarization_service.py # Summarization logic
│   │   ├── literature_service.py    # Literature review generation
│   │   ├── embedding_service.py     # Embedding generation
│   │   └── llm_service.py           # LLM interaction (Ollama)
│   │
│   ├── agents/                      # Agent Layer
│   │   ├── __init__.py
│   │   ├── research_agent.py        # Main research agent
│   │   ├── tools.py                 # LangChain tools
│   │   ├── orchestrator.py          # Agent orchestration logic
│   │   └── callbacks.py             # Agent callbacks
│   │
│   ├── retrieval/                   # Retrieval Layer
│   │   ├── __init__.py
│   │   ├── elasticsearch_client.py  # ES client wrapper
│   │   ├── hybrid_retriever.py      # Hybrid search implementation
│   │   ├── reranker.py              # Result reranking
│   │   └── index_manager.py         # Index creation/management
│   │
│   ├── processing/                  # Document Processing
│   │   ├── __init__.py
│   │   ├── pdf_extractor.py         # PDF text extraction
│   │   ├── text_chunker.py          # Intelligent chunking
│   │   ├── metadata_extractor.py    # Metadata extraction
│   │   └── preprocessor.py          # Text preprocessing
│   │
│   ├── prompts/                     # Prompt Templates
│   │   ├── __init__.py
│   │   ├── templates.py             # Prompt templates
│   │   ├── rag_prompts.py           # RAG-specific prompts
│   │   └── agent_prompts.py         # Agent prompts
│   │
│   └── utils/                       # Utilities
│       ├── __init__.py
│       ├── logger.py                # Logging configuration
│       ├── file_utils.py            # File handling utilities
│       ├── text_utils.py            # Text processing utilities
│       └── validators.py            # Input validators
│
├── data/                            # Data Storage
│   ├── uploads/                     # Uploaded PDFs
│   ├── processed/                   # Processed documents
│   └── cache/                       # Embedding cache
│
├── logs/                            # Application Logs
│   ├── app.log
│   └── error.log
│
├── tests/                           # Tests
│   ├── __init__.py
│   ├── conftest.py                  # Pytest fixtures
│   ├── unit/
│   │   ├── test_pdf_extractor.py
│   │   ├── test_chunker.py
│   │   └── test_services.py
│   ├── integration/
│   │   ├── test_api.py
│   │   └── test_retrieval.py
│   └── e2e/
│       └── test_workflows.py
│
├── frontend/                        # Optional Frontend
│   ├── app.py                       # Streamlit app
│   ├── components/
│   │   ├── upload.py
│   │   ├── query.py
│   │   └── results.py
│   └── utils.py
│
├── scripts/                         # Utility Scripts
│   ├── setup_elasticsearch.py       # ES index setup
│   ├── migrate_data.py              # Data migration
│   └── benchmark.py                 # Performance benchmarking
│
├── .env.example                     # Environment template
├── .gitignore
├── requirements.txt                 # Python dependencies
├── README.md                        # Project documentation
├── ARCHITECTURE.md                  # This file
├── main.py                          # Application entry point
└── pyproject.toml                   # Project metadata
```

---

## **3. Data Flow Architecture**

### **3.1 Document Ingestion Flow**

```
User Upload (PDF)
    ↓
[API Layer] papers.py endpoint
    ↓
[Service Layer] document_service.py
    ↓
┌─────────────────────────────────────┐
│ 1. Validate file (size, type)      │
│ 2. Save to uploads/                 │
│ 3. Extract text (pdf_extractor)    │
│ 4. Extract metadata                 │
│ 5. Identify sections                │
│ 6. Chunk text (text_chunker)       │
│ 7. Generate embeddings (batch)     │
│ 8. Store in Elasticsearch           │
│ 9. Return paper_id + metadata      │
└─────────────────────────────────────┘
    ↓
Response to User
```

### **3.2 Query Flow (RAG Pipeline)**

```
User Query
    ↓
[API Layer] query.py endpoint
    ↓
[Service Layer] query_service.py
    ↓
┌─────────────────────────────────────┐
│ 1. Validate query                   │
│ 2. Generate query embedding         │
│ 3. Hybrid retrieval (ES)            │
│    - Semantic search (dense vector) │
│    - Keyword search (BM25)          │
│    - Combine scores                 │
│ 4. Rerank results                   │
│ 5. Extract top-k chunks             │
│ 6. Build context                    │
│ 7. Generate answer (LLM)            │
│ 8. Extract citations                │
│ 9. Format response                  │
└─────────────────────────────────────┘
    ↓
Response with Answer + Citations
```

### **3.3 Agent Workflow**

```
User Request
    ↓
[API Layer] Endpoint
    ↓
[Agent Layer] research_agent.py
    ↓
┌─────────────────────────────────────┐
│ Agent Decision Tree:                │
│                                     │
│ IF "summarize" → Summarization Tool │
│ IF "compare" → Multi-doc Retrieval  │
│ IF "review" → Literature Review     │
│ IF "question" → RAG Tool            │
│ ELSE → General Query                │
└─────────────────────────────────────┘
    ↓
Tool Execution
    ↓
[Service Layer] Appropriate Service
    ↓
Response
```

---

## **4. RAG Pipeline Details**

### **4.1 Chunking Strategy**

```python
# Intelligent section-aware chunking
Document
    ↓
Identify Sections (Abstract, Intro, Methods, etc.)
    ↓
For each section:
    - Split by paragraphs
    - Maintain chunk_size (512 tokens)
    - Apply overlap (50 tokens)
    - Preserve section context
    ↓
Chunks with metadata:
    - chunk_id
    - paper_id
    - section_name
    - page_number
    - chunk_index
```

### **4.2 Embedding Generation**

```python
# Batch embedding with caching
Chunks (batch of 32)
    ↓
Check cache (optional)
    ↓
sentence-transformers model
    ↓
384-dimensional vectors
    ↓
Store in Elasticsearch dense_vector field
```

### **4.3 Hybrid Retrieval**

```python
# Combining semantic and keyword search
Query
    ↓
┌──────────────────┬──────────────────┐
│ Semantic Search  │ Keyword Search   │
│ (dense_vector)   │ (BM25)           │
│                  │                  │
│ - Generate       │ - Tokenize query │
│   embedding      │ - Match terms    │
│ - Cosine sim     │ - TF-IDF scoring │
│ - Top 10 results │ - Top 10 results │
└──────────────────┴──────────────────┘
    ↓
Combine scores (weighted):
    final_score = α * semantic_score + (1-α) * keyword_score
    ↓
Rerank (optional)
    ↓
Top-k results
```

---

## **5. Elasticsearch Schema**

### **5.1 Index Mapping**

```json
{
  "mappings": {
    "properties": {
      "chunk_id": {
        "type": "keyword"
      },
      "paper_id": {
        "type": "keyword"
      },
      "text": {
        "type": "text",
        "analyzer": "standard",
        "fields": {
          "keyword": {
            "type": "keyword",
            "ignore_above": 256
          }
        }
      },
      "embedding": {
        "type": "dense_vector",
        "dims": 384,
        "index": true,
        "similarity": "cosine"
      },
      "section": {
        "type": "keyword"
      },
      "page_number": {
        "type": "integer"
      },
      "chunk_index": {
        "type": "integer"
      },
      "paper_metadata": {
        "properties": {
          "title": {
            "type": "text"
          },
          "authors": {
            "type": "keyword"
          },
          "abstract": {
            "type": "text"
          },
          "publication_date": {
            "type": "date"
          },
          "doi": {
            "type": "keyword"
          },
          "keywords": {
            "type": "keyword"
          }
        }
      },
      "upload_date": {
        "type": "date"
      },
      "file_path": {
        "type": "keyword"
      }
    }
  },
  "settings": {
    "number_of_shards": 1,
    "number_of_replicas": 1,
    "analysis": {
      "analyzer": {
        "custom_analyzer": {
          "type": "standard",
          "stopwords": "_english_"
        }
      }
    }
  }
}
```

### **5.2 Query Examples**

**Hybrid Search Query:**
```json
{
  "query": {
    "script_score": {
      "query": {
        "bool": {
          "should": [
            {
              "match": {
                "text": {
                  "query": "transformer architecture",
                  "boost": 0.5
                }
              }
            }
          ]
        }
      },
      "script": {
        "source": "cosineSimilarity(params.query_vector, 'embedding') + 1.0",
        "params": {
          "query_vector": [0.1, 0.2, ...]
        }
      }
    }
  },
  "size": 10
}
```

---

## **6. API Interactions**

### **6.1 API Endpoints**

| Endpoint | Method | Description | Request | Response |
|----------|--------|-------------|---------|----------|
| `/api/v1/papers/upload` | POST | Upload PDF | multipart/form-data | PaperUploadResponse |
| `/api/v1/papers/{paper_id}` | GET | Get paper info | - | PaperInfo |
| `/api/v1/papers` | GET | List papers | query params | List[PaperInfo] |
| `/api/v1/query` | POST | Query papers | QueryRequest | QueryResponse |
| `/api/v1/papers/{paper_id}/summarize` | POST | Summarize paper | SummarizeRequest | PaperSummary |
| `/api/v1/literature-review` | POST | Generate review | LiteratureReviewRequest | LiteratureReview |
| `/api/v1/health` | GET | Health check | - | HealthResponse |

### **6.2 Sequence Diagrams**

**Upload Paper Sequence:**
```
Client          API           DocumentService    PDFExtractor    Chunker    EmbeddingService    Elasticsearch
  |              |                   |                |             |              |                  |
  |--Upload PDF->|                   |                |             |              |                  |
  |              |--process()------->|                |             |              |                  |
  |              |                   |--extract()---->|             |              |                  |
  |              |                   |<--text---------|             |              |                  |
  |              |                   |--chunk()------------------>|              |                  |
  |              |                   |<--chunks-------------------|              |                  |
  |              |                   |--embed()-------------------------------->|                  |
  |              |                   |<--embeddings-----------------------------|                  |
  |              |                   |--index()------------------------------------------------->|
  |              |                   |<--success--------------------------------------------------|
  |              |<--response--------|                |             |              |                  |
  |<--200 OK-----|                   |                |             |              |                  |
```

**Query Sequence:**
```
Client          API         QueryService    HybridRetriever    LLMService    Elasticsearch
  |              |                |                |                |              |
  |--Query------>|                |                |                |              |
  |              |--query()------>|                |                |              |
  |              |                |--retrieve()--->|                |              |
  |              |                |                |--search()----->|              |
  |              |                |                |<--chunks-------|              |
  |              |                |<--results------|                |              |
  |              |                |--generate()------------------>|              |
  |              |                |<--answer----------------------|              |
  |              |<--response-----|                |                |              |
  |<--200 OK-----|                |                |                |              |
```

---

## **7. Agent Architecture**

### **7.1 Agent Components**

```python
ResearchAgent
    ├── LLM (Ollama)
    ├── Tools:
    │   ├── RAGTool (query papers)
    │   ├── SummarizationTool (summarize paper)
    │   ├── ComparisonTool (compare papers)
    │   └── LiteratureReviewTool (generate review)
    ├── Memory (conversation history)
    └── Orchestrator (decision logic)
```

### **7.2 Agent Decision Flow**

```
User Input
    ↓
Parse Intent
    ↓
┌─────────────────────────────────────┐
│ Intent Classification:              │
│                                     │
│ "summarize paper X"                 │
│   → SummarizationTool               │
│                                     │
│ "compare X and Y"                   │
│   → ComparisonTool                  │
│                                     │
│ "what are findings on Z?"           │
│   → RAGTool                         │
│                                     │
│ "generate literature review on W"   │
│   → LiteratureReviewTool            │
│                                     │
│ Complex multi-step query            │
│   → Chain multiple tools            │
└─────────────────────────────────────┘
    ↓
Execute Tool(s)
    ↓
Format Response
    ↓
Return to User
```

### **7.3 Tool Definitions**

```python
# RAG Tool
class RAGTool(BaseTool):
    name = "query_papers"
    description = "Search papers and answer questions using retrieved context"
    
    def _run(self, question: str, top_k: int = 5) -> str:
        # Retrieve relevant chunks
        # Generate answer with citations
        # Return formatted response

# Summarization Tool
class SummarizationTool(BaseTool):
    name = "summarize_paper"
    description = "Generate a comprehensive summary of a paper"
    
    def _run(self, paper_id: str, summary_type: str = "comprehensive") -> str:
        # Retrieve paper chunks
        # Generate structured summary
        # Return summary

# Literature Review Tool
class LiteratureReviewTool(BaseTool):
    name = "generate_literature_review"
    description = "Generate a literature review on a topic"
    
    def _run(self, topic: str, max_papers: int = 10) -> str:
        # Search relevant papers
        # Extract key contributions
        # Identify themes and gaps
        # Generate structured review
```

---

## **8. Service Layer Architecture**

### **8.1 Service Dependencies**

```
DocumentService
    ├── PDFExtractor
    ├── TextChunker
    ├── EmbeddingService
    └── ElasticsearchClient

QueryService
    ├── HybridRetriever
    ├── LLMService
    └── EmbeddingService

SummarizationService
    ├── ElasticsearchClient
    └── LLMService

LiteratureService
    ├── HybridRetriever
    ├── LLMService
    └── QueryService
```

### **8.2 Dependency Injection Pattern**

```python
# api/deps.py
async def get_es_client() -> ElasticsearchClient:
    client = ElasticsearchClient(settings.elasticsearch_url)
    try:
        yield client
    finally:
        await client.close()

async def get_embedding_service() -> EmbeddingService:
    return EmbeddingService(settings.embedding_model)

async def get_query_service(
    es_client: ElasticsearchClient = Depends(get_es_client),
    embedding_service: EmbeddingService = Depends(get_embedding_service)
) -> QueryService:
    return QueryService(es_client, embedding_service)

# api/v1/query.py
@router.post("/query", response_model=QueryResponse)
async def query_papers(
    request: QueryRequest,
    query_service: QueryService = Depends(get_query_service)
):
    return await query_service.query(request)
```

---

## **9. Error Handling Strategy**

### **9.1 Exception Hierarchy**

```python
class ResearchAssistantException(Exception):
    """Base exception"""

class DocumentProcessingError(ResearchAssistantException):
    """Document processing failures"""

class RetrievalError(ResearchAssistantException):
    """Retrieval failures"""

class LLMError(ResearchAssistantException):
    """LLM interaction failures"""

class ValidationError(ResearchAssistantException):
    """Input validation failures"""
```

### **9.2 Error Handling Flow**

```python
# Global exception handler
@app.exception_handler(ResearchAssistantException)
async def handle_exception(request: Request, exc: ResearchAssistantException):
    logger.error(f"Error: {exc}", exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"error": str(exc), "detail": exc.detail}
    )

# Service-level error handling
async def process_document(file: UploadFile) -> PaperUploadResponse:
    try:
        # Processing logic
        pass
    except PDFExtractionError as e:
        logger.error(f"PDF extraction failed: {e}")
        raise DocumentProcessingError("Failed to extract text from PDF")
    except EmbeddingError as e:
        logger.error(f"Embedding generation failed: {e}")
        raise DocumentProcessingError("Failed to generate embeddings")
```

---

## **10. Performance Optimizations**

### **10.1 Async Operations**

- All I/O operations are async (FastAPI, Elasticsearch, file operations)
- Batch embedding generation (32 chunks at a time)
- Connection pooling for Elasticsearch
- Async LLM calls with streaming support

### **10.2 Caching Strategy**

```python
# Embedding cache
embedding_cache = {}

async def get_embedding(text: str) -> List[float]:
    cache_key = hashlib.md5(text.encode()).hexdigest()
    if cache_key in embedding_cache:
        return embedding_cache[cache_key]
    
    embedding = await generate_embedding(text)
    embedding_cache[cache_key] = embedding
    return embedding
```

### **10.3 Indexing Optimizations**

- Bulk indexing for chunks (batch of 100)
- Refresh interval tuning
- Proper shard configuration
- Index aliases for zero-downtime updates

---

## **11. Security Considerations**

### **11.1 Input Validation**

- File type validation (PDF only)
- File size limits (50MB default)
- Query length limits
- Pydantic schema validation

### **11.2 Rate Limiting**

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/query")
@limiter.limit("10/minute")
async def query_papers(request: QueryRequest):
    pass
```

### **11.3 Secrets Management**

- Environment variables for all secrets
- No hardcoded credentials
- .env file excluded from git
- Optional integration with secret managers (AWS Secrets Manager, etc.)

---

## **12. Monitoring and Logging**

### **12.1 Logging Strategy**

```python
# Structured logging with context
logger.info(
    "Document processed",
    extra={
        "paper_id": paper_id,
        "num_chunks": len(chunks),
        "processing_time": elapsed_time
    }
)
```

### **12.2 Metrics to Track**

- Request latency (p50, p95, p99)
- Embedding generation time
- Retrieval time
- LLM response time
- Error rates by endpoint
- Document processing success rate

---

## **13. Testing Strategy**

### **13.1 Test Pyramid**

```
        /\
       /E2E\         (Few) - Full workflow tests
      /------\
     /  INT   \      (Some) - API + Service integration
    /----------\
   /   UNIT     \    (Many) - Individual components
  /--------------\
```

### **13.2 Test Coverage**

- Unit tests: 80%+ coverage
- Integration tests: Critical paths
- E2E tests: Main user workflows
- Performance tests: Load testing

---

## **14. Deployment Architecture**

### **14.1 Production Setup**

```
                    ┌─────────────┐
                    │   Nginx     │
                    │  (Reverse   │
                    │   Proxy)    │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │   FastAPI   │
                    │  (Uvicorn)  │
                    │  Workers: 4 │
                    └──────┬──────┘
                           │
        ┌──────────────────┼──────────────────┐
        │                  │                  │
   ┌────▼────┐      ┌──────▼──────┐   ┌──────▼──────┐
   │ Ollama  │      │Elasticsearch│   │  File       │
   │  LLM    │      │   Cluster   │   │  Storage    │
   └─────────┘      └─────────────┘   └─────────────┘
```

### **14.2 Docker Compose**

```yaml
version: '3.8'

services:
  api:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ELASTICSEARCH_URL=http://elasticsearch:9200
      - OLLAMA_BASE_URL=http://ollama:11434
    depends_on:
      - elasticsearch
      - ollama
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs

  elasticsearch:
    image: elasticsearch:8.12.0
    environment:
      - discovery.type=single-node
      - xpack.security.enabled=false
    ports:
      - "9200:9200"
    volumes:
      - es_data:/usr/share/elasticsearch/data

  ollama:
    image: ollama/ollama:latest
    ports:
      - "11434:11434"
    volumes:
      - ollama_data:/root/.ollama

volumes:
  es_data:
  ollama_data:
```

---

## **15. Implementation Roadmap**

### **Phase 1: Core Infrastructure (Week 1)**
- ✅ Project structure setup
- ✅ Configuration management
- ✅ Logging setup
- ✅ Basic models and schemas
- ✅ PDF extraction
- ✅ Text chunking

### **Phase 2: Retrieval System (Week 2)**
- [ ] Elasticsearch client implementation
- [ ] Index manager
- [ ] Embedding service
- [ ] Hybrid retriever
- [ ] Reranking logic

### **Phase 3: API Layer (Week 3)**
- [ ] FastAPI application setup
- [ ] Dependency injection
- [ ] Paper upload endpoint
- [ ] Query endpoint
- [ ] Health check endpoint

### **Phase 4: Services (Week 4)**
- [ ] Document service
- [ ] Query service
- [ ] LLM service (Ollama integration)
- [ ] Summarization service

### **Phase 5: Agent System (Week 5)**
- [ ] LangChain agent setup
- [ ] Tool definitions
- [ ] Agent orchestrator
- [ ] Literature review service

### **Phase 6: Testing & Optimization (Week 6)**
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance optimization
- [ ] Documentation

### **Phase 7: Frontend & Deployment (Week 7)**
- [ ] Streamlit interface
- [ ] Docker setup
- [ ] Deployment configuration
- [ ] Production hardening

---

## **16. Key Design Decisions**

### **16.1 Why Elasticsearch?**
- Native support for both dense vectors and BM25
- Proven scalability
- Rich query DSL for hybrid search
- Production-ready with monitoring tools

### **16.2 Why Ollama?**
- Local inference (privacy, cost)
- Easy model switching
- Good performance on consumer hardware
- Compatible with LangChain

### **16.3 Why LangChain?**
- Rich ecosystem of tools and integrations
- Agent framework with memory
- Easy prompt management
- Active community

### **16.4 Why FastAPI?**
- Async support out of the box
- Automatic API documentation
- Pydantic integration
- High performance

---

## **17. Future Enhancements**

### **Short-term**
- [ ] Citation graph visualization
- [ ] Multi-language support
- [ ] Advanced filtering (date, author, venue)
- [ ] Export to BibTeX

### **Medium-term**
- [ ] Collaborative features (shared collections)
- [ ] Custom embedding models
- [ ] Graph-based paper relationships
- [ ] Integration with reference managers (Zotero, Mendeley)

### **Long-term**
- [ ] Multi-modal support (figures, tables)
- [ ] Automated hypothesis generation
- [ ] Research trend analysis
- [ ] Peer review assistance

---

This architecture provides a comprehensive blueprint for building a production-grade research assistant. Each component is designed to be modular, testable, and scalable, following industry best practices and clean architecture principles.
