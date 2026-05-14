# PDF Ingestion Pipeline

## Overview

The PDF ingestion pipeline processes academic papers through a multi-stage workflow that extracts, cleans, chunks, embeds, and indexes documents for retrieval.

## Pipeline Architecture

```
PDF Upload
    ↓
1. File Storage
    ↓
2. Text Extraction (PDFExtractor)
    ↓
3. Text Preprocessing (TextPreprocessor)
    ↓
4. Section Detection
    ↓
5. Semantic Chunking (TextChunker)
    ↓
6. Embedding Generation (EmbeddingService)
    ↓
7. Elasticsearch Indexing
    ↓
Success Response
```

## Components

### 1. DocumentService
**Location**: `app/services/document_service.py`

Main orchestrator that coordinates the entire pipeline.

**Key Methods**:
- `process_document()`: Main pipeline entry point
- `get_paper_info()`: Retrieve paper metadata
- `list_papers()`: List all indexed papers
- `delete_paper()`: Remove paper from index and disk
- `get_paper_text()`: Reconstruct full paper text
- `get_paper_sections()`: Get text organized by sections

### 2. PDFExtractor
**Location**: `app/processing/pdf_extractor.py`

Extracts text and metadata from PDF files with multiple fallback strategies.

**Features**:
- **Multi-library fallback**: PyMuPDF → pdfplumber → pypdf
- **Page-level extraction**: Maintains page number mapping
- **Metadata extraction**: Title, authors, abstract, DOI, keywords
- **Section identification**: Detects major paper sections
- **Robust error handling**: Gracefully handles malformed PDFs

**Extraction Strategy**:
1. Try PyMuPDF (fastest, most reliable)
2. Fallback to pdfplumber if PyMuPDF fails
3. Fallback to pypdf as last resort

**Metadata Extraction**:
- From PDF metadata fields
- From text content using regex patterns
- Heuristic-based title detection
- Author name pattern matching
- Abstract section extraction
- DOI pattern matching
- Keyword extraction

### 3. TextPreprocessor
**Location**: `app/processing/preprocessor.py`

Cleans and normalizes extracted text for optimal retrieval.

**Cleaning Operations**:
- **Whitespace normalization**: Remove excessive spaces/newlines
- **Header/footer removal**: Strip page headers, footers, URLs
- **Hyphenation fixing**: Rejoin words split across lines
- **Page number removal**: Remove standalone page numbers
- **Special character cleaning**: Normalize quotes, dashes, unicode
- **Reference removal**: Strip bibliography section

**Section Detection**:
- Pattern-based section header recognition
- Supports numbered sections (1., 1.1, etc.)
- Recognizes standard academic sections:
  - Abstract
  - Introduction
  - Background/Related Work
  - Methodology/Methods
  - Results/Experiments
  - Discussion/Analysis
  - Conclusion
  - References

**Heading Extraction**:
- Numbered headings (1.1, 2.3, etc.)
- All-caps headings
- Title case headings
- Position tracking for context

### 4. TextChunker
**Location**: `app/processing/text_chunker.py`

Creates semantically coherent chunks for embedding and retrieval.

**Chunking Strategy**:
- **Section-aware**: Chunks within section boundaries
- **Sentence-based**: Never breaks mid-sentence
- **Overlap**: Configurable overlap between chunks
- **Size control**: Respects min/max chunk sizes
- **Page tracking**: Maintains page number references

**Configuration** (from `config.py`):
- `chunk_size`: 512 characters (default)
- `chunk_overlap`: 50 characters (default)
- `min_chunk_length`: 100 characters (default)

**Chunk Metadata**:
- `chunk_id`: Unique identifier
- `paper_id`: Parent paper reference
- `section`: Section name (if detected)
- `page_number`: Source page
- `chunk_index`: Sequential position
- `metadata`: Length, sentence count, etc.

### 5. EmbeddingService
**Location**: `app/services/embedding_service.py`

Generates dense vector embeddings using sentence-transformers.

**Features**:
- **Model**: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions)
- **Batch processing**: Efficient batch embedding generation
- **GPU support**: Automatic CUDA detection
- **Normalization**: L2-normalized for cosine similarity
- **Singleton pattern**: Single model instance across app

**Methods**:
- `embed_text()`: Embed single text or batch
- `embed_query()`: Embed search query
- `embed_documents()`: Embed multiple documents
- `similarity()`: Calculate cosine similarity

### 6. ElasticsearchClient
**Location**: `app/retrieval/elasticsearch_client.py`

Indexes chunks with embeddings for hybrid retrieval.

**Index Schema**:
```json
{
  "chunk_id": "keyword",
  "paper_id": "keyword",
  "text": "text with keyword field",
  "section": "keyword",
  "page_number": "integer",
  "chunk_index": "integer",
  "embedding": "dense_vector (384-dim, cosine)",
  "metadata": "object",
  "paper_metadata": {
    "title": "text",
    "authors": "keyword",
    "abstract": "text",
    "publication_date": "date",
    "doi": "keyword",
    "keywords": "keyword"
  },
  "created_at": "date"
}
```

**Indexing Features**:
- Bulk indexing for efficiency
- Automatic timestamp generation
- Paper metadata attached to each chunk
- Error handling and retry logic

## Pipeline Flow

### Step 1: File Storage
```python
file_path = upload_dir / f"{paper_id}_{filename}"
file_path.write_bytes(file_content)
```

### Step 2: Text Extraction
```python
raw_text, page_map = pdf_extractor.extract_text(file_path)
metadata = pdf_extractor.extract_metadata(file_path, raw_text)
```

**Output**:
- `raw_text`: Full extracted text
- `page_map`: Dict mapping page numbers to text
- `metadata`: PaperMetadata object

### Step 3: Text Preprocessing
```python
cleaned_text = preprocessor.clean_text(raw_text)
cleaned_text = preprocessor.remove_references_section(cleaned_text)
```

**Transformations**:
- Normalize whitespace
- Remove headers/footers
- Fix hyphenation
- Clean special characters

### Step 4: Section Detection
```python
sections = preprocessor.detect_sections(cleaned_text)
```

**Output**: Dict mapping section names to content
```python
{
  "abstract": "...",
  "introduction": "...",
  "methodology": "...",
  "results": "...",
  "conclusion": "..."
}
```

### Step 5: Semantic Chunking
```python
chunks = chunker.chunk_by_sections(
    text=cleaned_text,
    paper_id=paper_id,
    sections=sections,
    page_map=page_map
)
```

**Output**: List of DocumentChunk objects with:
- Unique chunk IDs
- Section labels
- Page numbers
- Sequential indices

### Step 6: Embedding Generation
```python
chunk_texts = [chunk.text for chunk in chunks]
embeddings = embedding_service.embed_documents(chunk_texts)

for chunk, embedding in zip(chunks, embeddings):
    chunk.embedding = embedding
```

**Output**: 384-dimensional normalized vectors

### Step 7: Elasticsearch Indexing
```python
indexed_count = await es_client.index_chunks(
    chunks=chunks,
    paper_metadata=metadata.model_dump()
)
```

**Result**: Chunks indexed and ready for retrieval

## Error Handling

### PDF Extraction Failures
- **Cause**: Corrupted PDF, unsupported format, encrypted file
- **Handling**: Try multiple extraction libraries in sequence
- **Response**: Return error with specific failure reason

### Embedding Generation Failures
- **Cause**: Model not loaded, GPU memory issues, text too long
- **Handling**: Log error, return failure response
- **Response**: Include error details for debugging

### Elasticsearch Indexing Failures
- **Cause**: Connection issues, mapping conflicts, disk space
- **Handling**: Retry logic, detailed error logging
- **Response**: Partial success reporting (X of Y chunks indexed)

### Malformed PDFs
- **Detection**: Empty text extraction, very short content
- **Handling**: Attempt all extraction methods
- **Fallback**: Return error if all methods fail

## Configuration

### Environment Variables
```bash
# Document Processing
MAX_UPLOAD_SIZE_MB=50
CHUNK_SIZE=512
CHUNK_OVERLAP=50
MIN_CHUNK_LENGTH=100

# Embeddings
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_DIMENSION=384
EMBEDDING_BATCH_SIZE=32

# Storage
UPLOAD_DIR=data/uploads
PROCESSED_DIR=data/processed
```

### Tuning Parameters

**Chunk Size**:
- Smaller (256-512): Better precision, more chunks
- Larger (1024-2048): Better context, fewer chunks
- Recommended: 512 for academic papers

**Chunk Overlap**:
- Prevents information loss at boundaries
- Recommended: 10-20% of chunk size

**Min Chunk Length**:
- Filters out artifacts and noise
- Recommended: 100 characters minimum

## Performance Considerations

### Processing Time
Typical processing time for a 10-page paper:
- PDF extraction: 0.5-1s
- Text preprocessing: 0.1-0.3s
- Chunking: 0.1-0.2s
- Embedding generation: 1-3s (CPU), 0.3-0.5s (GPU)
- Elasticsearch indexing: 0.2-0.5s
- **Total**: 2-5s (CPU), 1-2.5s (GPU)

### Optimization Tips
1. **Use GPU**: 5-10x faster embedding generation
2. **Batch processing**: Process multiple papers in parallel
3. **Async operations**: All I/O operations are async
4. **Connection pooling**: Reuse Elasticsearch connections
5. **Model caching**: Singleton pattern for embedding model

## Usage Example

### Upload and Process Paper
```python
from app.services.document_service import DocumentService
from app.retrieval.elasticsearch_client import es_client
from app.services.embedding_service import embedding_service

# Initialize service
doc_service = DocumentService(
    es_client=es_client,
    embedding_service=embedding_service
)

# Process PDF
with open("paper.pdf", "rb") as f:
    file_content = f.read()

response = await doc_service.process_document(
    file_content=file_content,
    filename="paper.pdf"
)

print(f"Status: {response.status}")
print(f"Paper ID: {response.paper_id}")
print(f"Chunks: {response.num_chunks}")
print(f"Time: {response.processing_time:.2f}s")
```

### Retrieve Paper Information
```python
paper_info = await doc_service.get_paper_info(paper_id)
print(f"Title: {paper_info.metadata.title}")
print(f"Authors: {', '.join(paper_info.metadata.authors)}")
print(f"Sections: {paper_info.sections}")
```

### Get Paper Text by Section
```python
sections = await doc_service.get_paper_sections(paper_id)
for section_name, section_text in sections.items():
    print(f"\n=== {section_name.upper()} ===")
    print(section_text[:200] + "...")
```

## API Integration

### Upload Endpoint
```http
POST /api/v1/papers/upload
Content-Type: multipart/form-data

file: <PDF file>
```

**Response**:
```json
{
  "paper_id": "uuid",
  "filename": "paper.pdf",
  "status": "success",
  "message": "Successfully processed 45 chunks",
  "metadata": {
    "title": "Paper Title",
    "authors": ["Author 1", "Author 2"],
    "abstract": "...",
    "num_pages": 10
  },
  "num_chunks": 45,
  "processing_time": 2.34
}
```

### List Papers Endpoint
```http
GET /api/v1/papers?skip=0&limit=10
```

### Get Paper Info Endpoint
```http
GET /api/v1/papers/{paper_id}
```

### Delete Paper Endpoint
```http
DELETE /api/v1/papers/{paper_id}
```

## Testing

### Test with Sample PDF
```bash
curl -X POST http://localhost:8000/api/v1/papers/upload \
  -F "file=@sample_paper.pdf"
```

### Verify Indexing
```bash
curl http://localhost:9200/research_papers/_count
```

### Check Paper Chunks
```bash
curl http://localhost:9200/research_papers/_search?q=paper_id:YOUR_PAPER_ID
```

## Troubleshooting

### Issue: Empty text extraction
**Solution**: Check PDF is not image-based (requires OCR)

### Issue: Slow embedding generation
**Solution**: Enable GPU or reduce batch size

### Issue: Elasticsearch connection failed
**Solution**: Verify Elasticsearch is running and accessible

### Issue: Out of memory
**Solution**: Reduce embedding batch size or chunk size

### Issue: No sections detected
**Solution**: Pipeline falls back to full text chunking automatically

## Future Enhancements

1. **OCR Support**: Extract text from image-based PDFs
2. **Table Extraction**: Preserve table structure
3. **Figure Extraction**: Extract and index figures
4. **Citation Parsing**: Extract and link citations
5. **Multi-format Support**: Support DOCX, HTML, etc.
6. **Incremental Updates**: Update existing papers
7. **Duplicate Detection**: Identify duplicate papers
8. **Quality Scoring**: Assess extraction quality
