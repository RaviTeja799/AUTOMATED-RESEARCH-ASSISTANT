# Architecture

## Stack

```
Browser / API Client
        │
        ▼
   FastAPI (uvicorn)
        │
   ┌────┴────────────────────────────────┐
   │                                     │
   ▼                                     ▼
Groq API                          Qdrant Cloud
(llama-3.1-8b-instant)         (vector store, 384-dim)
                                         │
                                         ▼
                               sentence-transformers
                               (all-MiniLM-L6-v2, local)
```

## Folder Structure

```
app/
├── api/
│   ├── deps.py              # Dependency injection (singletons)
│   └── v1/
│       ├── router.py
│       ├── papers.py        # Upload, list, delete
│       ├── query.py         # RAG Q&A
│       ├── summarize.py     # Paper summarization
│       ├── literature.py    # Literature review
│       ├── agent.py         # LangChain agent
│       └── health.py
│
├── core/
│   ├── config.py            # Pydantic settings (env vars)
│   └── exceptions.py        # Custom exception hierarchy
│
├── services/
│   ├── document_service.py  # PDF ingestion pipeline
│   ├── query_service.py     # RAG pipeline + TTL cache
│   ├── summarization_service.py
│   ├── literature_service.py
│   ├── embedding_service.py # sentence-transformers (lazy singleton)
│   ├── llm_service.py       # Groq async client
│   └── agent_service.py     # LangChain orchestration
│
├── agents/
│   ├── research_agent.py    # ReAct agent + memory
│   └── tools.py             # 5 LangChain tools
│
├── retrieval/
│   ├── qdrant_client.py     # Async Qdrant Cloud client
│   └── hybrid_retriever.py  # Semantic search via Qdrant
│
├── processing/
│   ├── pdf_extractor.py     # PyMuPDF → pdfplumber → pypdf
│   ├── preprocessor.py      # Text cleaning, section detection
│   └── text_chunker.py      # Sentence-aware chunking
│
├── prompts/
│   └── rag_prompts.py       # Citation-aware RAG prompts
│
├── models/
│   └── schemas.py           # Pydantic request/response models
│
└── utils/
    └── logger.py            # Loguru structured logging

frontend/
└── index.html               # Single-page UI (vanilla JS + Tailwind)
```

## Data Flow

### PDF Upload
```
POST /api/v1/papers/upload
  → DocumentService.process_document()
    → PDFExtractor.extract_text()        # PyMuPDF fallback chain
    → TextPreprocessor.clean_text()      # Normalize, remove headers
    → TextPreprocessor.detect_sections() # Abstract, Intro, Methods...
    → TextChunker.chunk_by_sections()    # Sentence-aware, 512 chars
    → EmbeddingService.embed_documents() # Batch encode, 384-dim
    → QdrantVectorStore.index_chunks()   # Upsert to Qdrant Cloud
```

### Query (RAG)
```
POST /api/v1/query
  → QueryService.query()
    → Check TTL cache (120s)
    → HybridRetriever.retrieve()
        → EmbeddingService.embed_query()  # Sync, CPU-bound
        → QdrantVectorStore.search()      # Async, cosine similarity
    → RAGPrompts.build_rag_prompt()       # Citation-aware context
    → LLMService.generate()              # Groq async API
    → _extract_citations()               # Match answer to sources
    → _assess_confidence()               # Single-pass scoring
    → Cache result
```

### Agent
```
POST /api/v1/agent
  → AgentService.process_query()
    → IntentClassifier.classify()        # Keyword-based routing
    → ResearchAgent.process_query()
        → AgentExecutor.invoke()         # LangChain ReAct (thread pool)
            → Tools: search_papers, answer_question,
                     summarize_paper, compare_papers,
                     generate_literature_review
```

## Key Design Decisions

**Groq instead of local Ollama** — No 4GB model download, ~10x faster inference, free tier sufficient for development.

**Qdrant Cloud instead of local Elasticsearch** — No Docker dependency, free persistent storage, purpose-built for vector search.

**Lazy singleton for embedding model** — `sentence-transformers` loads once on first request, not at import time. Prevents cold-start crashes.

**TTL cache on queries** — Identical questions within 120s skip Qdrant + Groq entirely.

**Sync embedding in async context** — `SentenceTransformer.encode()` is CPU-bound and runs in a dedicated `ThreadPoolExecutor` via `run_in_executor`, so it never blocks the event loop.

## Qdrant Collection Schema

```
Collection: research_papers
Vector: 384-dim cosine

Payload fields:
  chunk_id      keyword (indexed)
  paper_id      keyword (indexed)
  section       keyword (indexed)
  text          string
  page_number   integer
  chunk_index   integer
  paper_metadata {title, authors, abstract, doi, keywords, num_pages}
  metadata      {length, sentence_count}
```
