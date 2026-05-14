# Production-Ready RAG Pipeline Documentation

## Overview

This document describes the complete RAG (Retrieval-Augmented Generation) pipeline implementation with citation-awareness and hallucination prevention.

---

## Architecture

```
User Question
     ↓
┌────────────────────────────────────────────────────────────┐
│ 1. QUERY PROCESSING                                        │
│    - Question analysis                                     │
│    - Query embedding generation                            │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ 2. HYBRID RETRIEVAL                                        │
│    ┌──────────────────┬──────────────────┐               │
│    │ Semantic Search  │ Keyword Search   │               │
│    │ (Dense Vector)   │ (BM25)           │               │
│    └──────────────────┴──────────────────┘               │
│              ↓                                             │
│    ┌─────────────────────────────┐                       │
│    │ RRF (Rank Fusion)           │                       │
│    └─────────────────────────────┘                       │
│              ↓                                             │
│    Top-K Relevant Chunks                                  │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ 3. CONTEXT BUILDING                                        │
│    - Format chunks with citations                          │
│    - Add paper metadata                                    │
│    - Include section information                           │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ 4. PROMPT CONSTRUCTION                                     │
│    - Citation-aware instructions                           │
│    - Hallucination prevention rules                        │
│    - Formatted context                                     │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ 5. LLM GENERATION                                          │
│    - Generate answer with Ollama                           │
│    - Low temperature (0.3) for factual accuracy           │
│    - Citation enforcement                                  │
└────────────────────────────────────────────────────────────┘
     ↓
┌────────────────────────────────────────────────────────────┐
│ 6. POST-PROCESSING                                         │
│    - Extract citations                                     │
│    - Assess confidence                                     │
│    - Validate against sources                              │
└────────────────────────────────────────────────────────────┘
     ↓
Answer + Citations + Confidence
```

---

## Components

### 1. Query Service (`app/services/query_service.py`)

**Main orchestrator for the RAG pipeline.**

**Key Methods:**
- `query()` - Main entry point
- `_retrieve_chunks()` - Hybrid retrieval
- `_generate_answer()` - LLM generation
- `_extract_citations()` - Citation extraction
- `_assess_confidence()` - Confidence scoring

**Features:**
- ✅ Hybrid retrieval (semantic + keyword)
- ✅ Citation-aware prompting
- ✅ Hallucination prevention
- ✅ Confidence assessment
- ✅ Error handling

### 2. Hybrid Retriever (`app/retrieval/hybrid_retriever.py`)

**Combines semantic and keyword search.**

**Key Methods:**
- `retrieve()` - Main retrieval method
- `retrieve_with_reranking()` - With reranking
- `retrieve_by_paper()` - Get all chunks for a paper
- `retrieve_by_section()` - Filter by section
- `retrieve_by_date_range()` - Filter by date
- `retrieve_similar_chunks()` - Find similar chunks

**Features:**
- ✅ Semantic search (dense vectors)
- ✅ Keyword search (BM25)
- ✅ RRF (Reciprocal Rank Fusion)
- ✅ Configurable weights
- ✅ Filtering support
- ✅ Section boosting

### 3. RAG Prompts (`app/prompts/rag_prompts.py`)

**Citation-aware prompt templates.**

**Key Classes:**
- `RAGPrompts` - Main prompt builder
- `HallucinationPrevention` - Anti-hallucination strategies

**Features:**
- ✅ Citation-aware instructions
- ✅ Grounding rules
- ✅ Uncertainty expressions
- ✅ Fact-checking prompts
- ✅ Multi-hop reasoning
- ✅ Comparative analysis

---

## RAG Pipeline Flow

### Step 1: Query Processing

```python
# User submits question
request = QueryRequest(
    question="What are the main findings about transformer architectures?",
    top_k=5,
    include_citations=True
)
```

### Step 2: Embedding Generation

```python
# Generate query embedding
query_embedding = await embedding_service.embed_text(request.question)
# Returns: [0.1, 0.2, ..., 0.9] (384-dim vector)
```

### Step 3: Hybrid Retrieval

```python
# Retrieve relevant chunks
chunks = await retriever.retrieve(
    query=request.question,
    top_k=5,
    boost_key_sections=True,
    min_score=0.5
)
```

**Retrieval combines:**
- **Semantic search**: kNN with cosine similarity
- **Keyword search**: BM25 with field boosting
- **RRF**: Reciprocal Rank Fusion for combining results

**Retrieved chunks include:**
```json
{
  "chunk_id": "chunk-abc123",
  "paper_id": "paper-123",
  "text": "Transformers use self-attention mechanisms...",
  "section": "introduction",
  "page_number": 2,
  "score": 0.85,
  "paper_metadata": {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani", "Shazeer", "Parmar"],
    "publication_year": 2017
  }
}
```

### Step 4: Context Building

```python
# Build citation-aware context
prompt = RAGPrompts.build_rag_prompt(
    question=request.question,
    context_chunks=chunks,
    include_confidence=True
)
```

**Prompt structure:**
```
INSTRUCTIONS:
- Use ONLY information from sources
- Cite every claim: [Title, Authors, Year]
- If information missing, say so explicitly
- Never make assumptions

SOURCES:
[Source 1] Attention Is All You Need, Vaswani et al., 2017
Section: INTRODUCTION | Page: 2 | Relevance: 0.85
Content: Transformers use self-attention mechanisms...

[Source 2] BERT: Pre-training of Deep Bidirectional Transformers, Devlin et al., 2019
Section: METHODOLOGY | Page: 3 | Relevance: 0.82
Content: BERT builds on the transformer architecture...

QUESTION: What are the main findings about transformer architectures?

YOUR ANSWER (with citations):
```

### Step 5: LLM Generation

```python
# Generate answer with citation enforcement
answer = await llm_service.generate(
    prompt=prompt,
    system_prompt=RAGPrompts.SYSTEM_PROMPT,
    temperature=0.3,  # Low for factual accuracy
    max_tokens=2048
)
```

**System prompt enforces:**
- Citation after every claim
- No external knowledge
- Explicit uncertainty when needed
- Grounding in sources

### Step 6: Citation Extraction

```python
# Extract citations from answer
citations = _extract_citations(answer, chunks)
```

**Citation format:**
```python
Citation(
    paper_id="paper-123",
    paper_title="Attention Is All You Need",
    authors=["Vaswani", "Shazeer", "Parmar"],
    chunk_id="chunk-abc123",
    page_number=2,
    relevance_score=0.85,
    text_snippet="Transformers use self-attention mechanisms..."
)
```

### Step 7: Confidence Assessment

```python
# Assess answer confidence
confidence = _assess_confidence(answer, chunks)
```

**Confidence factors:**
- Presence of citations (40%)
- Lack of uncertainty phrases (30%)
- Average chunk relevance (30%)

**Confidence levels:**
- **High (0.7-1.0)**: Well-supported, multiple citations
- **Medium (0.4-0.7)**: Partially supported, some uncertainty
- **Low (0.0-0.4)**: Insufficient information, high uncertainty

### Step 8: Response

```python
QueryResponse(
    answer="Transformers introduced self-attention mechanisms [Attention Is All You Need, Vaswani et al., 2017]...",
    citations=[...],
    confidence=0.85,
    processing_time=1.23,
    retrieved_chunks=5
)
```

---

## Hallucination Prevention

### Strategy 1: Citation Enforcement

**Every claim must be cited:**
```
✓ GOOD: "Transformers use self-attention [Vaswani et al., 2017]."
✗ BAD:  "Transformers use self-attention."
```

### Strategy 2: Explicit Grounding

**Instructions in prompt:**
```
- Use ONLY information from provided sources
- Do NOT use external knowledge
- Do NOT make assumptions
- Do NOT infer beyond what is stated
```

### Strategy 3: Uncertainty Expression

**When information is partial:**
```
"Based on the provided sources..."
"The sources suggest..."
"Limited information is available about..."
```

### Strategy 4: Missing Information Handling

**When answer not in sources:**
```
"I don't have information about this in the provided papers."
```

### Strategy 5: Low Temperature

**LLM generation with temperature=0.3:**
- More deterministic
- Less creative/inventive
- More factual

### Strategy 6: Confidence Scoring

**Assess answer quality:**
- Citation count
- Uncertainty phrases
- Source relevance
- Completeness

---

## Citation-Aware Answering

### Example 1: Simple Question

**Question:** "What is a transformer?"

**Answer:**
```
A transformer is a neural network architecture that relies entirely on 
self-attention mechanisms to compute representations [Attention Is All You Need, 
Vaswani et al., 2017]. Unlike recurrent neural networks, transformers process 
all positions simultaneously, enabling parallelization [Attention Is All You Need, 
Vaswani et al., 2017].
```

### Example 2: Comparative Question

**Question:** "How do BERT and GPT differ?"

**Answer:**
```
BERT uses bidirectional transformers and is trained with masked language modeling 
[BERT, Devlin et al., 2019], while GPT uses unidirectional transformers and is 
trained with autoregressive language modeling [GPT, Radford et al., 2018]. 
BERT is designed for understanding tasks [BERT, Devlin et al., 2019], whereas 
GPT excels at generation tasks [GPT, Radford et al., 2018].
```

### Example 3: Missing Information

**Question:** "What is the training cost of GPT-4?"

**Answer:**
```
I don't have information about the training cost of GPT-4 in the provided papers. 
The indexed papers do not discuss GPT-4's training costs or computational requirements.
```

### Example 4: Contradictory Information

**Question:** "Is attention all you need?"

**Answer:**
```
The original transformer paper argues that attention mechanisms alone are sufficient 
for sequence transduction [Attention Is All You Need, Vaswani et al., 2017]. However, 
later work suggests that combining attention with other mechanisms can improve 
performance [Paper X, Authors, 2020]. The effectiveness depends on the specific task 
and dataset.
```

---

## Usage Examples

### Basic Query

```python
from app.services.query_service import QueryService

# Initialize service
query_service = QueryService(es_client, embedding_service, llm_service)

# Query
request = QueryRequest(
    question="What are transformers?",
    top_k=5,
    include_citations=True
)

response = await query_service.query(request)

print(response.answer)
print(f"Confidence: {response.confidence}")
print(f"Citations: {len(response.citations)}")
```

### Query with Filters

```python
# Filter by year
request = QueryRequest(
    question="What are recent advances in NLP?",
    top_k=10,
    filters={
        "paper_metadata.publication_year": {
            "range": {"gte": 2020}
        }
    }
)

response = await query_service.query(request)
```

### Query Specific Sections

```python
# Only search in abstracts and conclusions
chunks = await retriever.retrieve_by_section(
    query="What are the main contributions?",
    sections=["abstract", "conclusion"],
    top_k=5
)
```

### Find Similar Content

```python
# Find chunks similar to a given chunk
similar = await retriever.retrieve_similar_chunks(
    chunk_id="chunk-abc123",
    top_k=5,
    exclude_same_paper=True
)
```

---

## Configuration

### Retrieval Settings

```python
# In app/core/config.py
DEFAULT_TOP_K = 5                    # Number of chunks to retrieve
HYBRID_SEARCH_WEIGHT = 0.5           # Semantic vs keyword weight
MIN_SIMILARITY_SCORE = 0.5           # Minimum relevance threshold
```

### LLM Settings

```python
OLLAMA_MODEL = "llama3"              # Model name
OLLAMA_TEMPERATURE = 0.3             # Low for factual answers
OLLAMA_MAX_TOKENS = 2048             # Max response length
```

### Embedding Settings

```python
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
EMBEDDING_BATCH_SIZE = 32
```

---

## Performance Optimization

### 1. Retrieval Optimization

- **Hybrid search**: Combines best of semantic and keyword
- **RRF**: Effective result fusion
- **HNSW**: Fast approximate nearest neighbor search
- **Filtering**: Reduce search space

### 2. LLM Optimization

- **Low temperature**: Faster, more deterministic
- **Prompt caching**: Reuse system prompts
- **Streaming**: For real-time responses (future)

### 3. Caching

- **Embedding cache**: Cache query embeddings
- **Result cache**: Cache frequent queries
- **Chunk cache**: Cache retrieved chunks

---

## Monitoring and Metrics

### Key Metrics

```python
{
    "retrieval_time": 0.15,          # Seconds
    "llm_generation_time": 1.08,     # Seconds
    "total_processing_time": 1.23,   # Seconds
    "retrieved_chunks": 5,
    "num_citations": 3,
    "confidence": 0.85,
    "avg_chunk_relevance": 0.82
}
```

### Logging

```python
app_logger.info(
    "Query processed successfully",
    extra={
        "retrieved_chunks": 5,
        "num_citations": 3,
        "confidence": 0.85,
        "processing_time": 1.23
    }
)
```

---

## Testing

### Unit Tests

```python
# Test retrieval
async def test_retrieve_chunks():
    chunks = await retriever.retrieve("test query", top_k=5)
    assert len(chunks) <= 5
    assert all('score' in chunk for chunk in chunks)

# Test citation extraction
def test_extract_citations():
    answer = "Transformers use attention [Paper, Authors, 2017]."
    citations = _extract_citations(answer, chunks)
    assert len(citations) > 0
```

### Integration Tests

```python
# Test full pipeline
async def test_rag_pipeline():
    request = QueryRequest(question="What are transformers?", top_k=5)
    response = await query_service.query(request)
    
    assert response.answer
    assert response.retrieved_chunks > 0
    assert 0 <= response.confidence <= 1
```

---

## Best Practices

1. **Always use citations** - Every factual claim should be cited
2. **Low temperature** - Use 0.3 for factual answers
3. **Validate sources** - Check that citations match sources
4. **Express uncertainty** - When information is incomplete
5. **Filter appropriately** - Use filters to narrow search
6. **Monitor confidence** - Track confidence scores
7. **Log everything** - Comprehensive logging for debugging
8. **Handle errors gracefully** - Provide helpful error messages

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| No results retrieved | Check if papers are indexed, try broader query |
| Low confidence scores | Increase top_k, check source relevance |
| Missing citations | Verify citation extraction logic |
| Slow retrieval | Optimize Elasticsearch, add filters |
| Hallucinations | Lower temperature, strengthen prompts |
| Poor relevance | Adjust hybrid search weights |

---

## Summary

The RAG pipeline provides:

✅ **Hybrid retrieval** (semantic + keyword)
✅ **Citation-aware** answering
✅ **Hallucination prevention** through grounding
✅ **Confidence assessment** for answer quality
✅ **Flexible filtering** by date, section, paper
✅ **Production-ready** error handling and logging
✅ **Scalable architecture** with async operations
✅ **Comprehensive monitoring** and metrics

The system is designed to provide accurate, well-cited answers while explicitly handling uncertainty and preventing hallucinations.
