# PDF Ingestion Pipeline

## Flow

```
POST /api/v1/papers/upload
  1. Save file  →  data/uploads/{paper_id}_{filename}
  2. Extract text  →  PyMuPDF (fallback: pdfplumber → pypdf)
  3. Extract metadata  →  title, authors, abstract, DOI, keywords
  4. Clean text  →  normalize whitespace, remove headers/footers, fix hyphenation
  5. Detect sections  →  Abstract, Introduction, Methods, Results, Conclusion
  6. Chunk  →  sentence-aware, 512 chars, 50 overlap, section-labeled
  7. Embed  →  sentence-transformers all-MiniLM-L6-v2, 384-dim, batch=32
  8. Index  →  Qdrant Cloud, upsert in batches of 100
```

## Components

**`PDFExtractor`** — tries PyMuPDF first (fastest), falls back to pdfplumber, then pypdf. Extracts per-page text map for page number tracking.

**`TextPreprocessor`** — removes null bytes, normalizes whitespace, strips headers/footers/page numbers, fixes line-break hyphenation, normalizes quotes/dashes.

**`TextChunker`** — splits by section first, then by sentence within each section. Never breaks mid-sentence. Configurable size/overlap.

**`EmbeddingService`** — lazy singleton, loads `all-MiniLM-L6-v2` on first use. Batch encodes with L2 normalization.

**`QdrantVectorStore`** — async Qdrant client. Creates collection + payload indexes on first run.

## Configuration

```env
MAX_UPLOAD_SIZE_MB=50
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MIN_CHUNK_LENGTH=100
EMBEDDING_BATCH_SIZE=32
```

## Typical timing (15-page paper, CPU)

| Step | Time |
|------|------|
| PDF extraction | 0.5–1s |
| Preprocessing | 0.1–0.3s |
| Chunking | 0.1–0.2s |
| Embedding (60 chunks) | 2–4s |
| Qdrant indexing | 0.3–0.5s |
| **Total** | **~3–6s** |
