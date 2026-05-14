# Elasticsearch Mappings - Quick Reference

## 📊 Index Overview

| Index | Purpose | Documents |
|-------|---------|-----------|
| `research_papers` | Main chunks index | Document chunks with embeddings |
| `research_papers_summaries` | Paper summaries | One doc per paper |
| `research_papers_citations` | Citation graph | Paper-to-paper relationships |

---

## 🔑 Key Fields Reference

### Chunk Identification
```
chunk_id          keyword    Unique chunk ID
paper_id          keyword    Paper ID
chunk_index       integer    Position in document
```

### Text & Embeddings
```
text              text       Main content (BM25 search)
  ├─ .keyword     keyword    Exact matching
  ├─ .exact       text       Case-sensitive
  └─ .standard    text       Standard analyzer

embedding         dense_vector (384 dims, cosine, HNSW)
```

### Section Info
```
section           keyword    Section type (abstract, intro, etc.)
section_title     text       Section heading
page_number       integer    Page location
```

### Paper Metadata
```
paper_metadata.title              text (boost: 2.0)
paper_metadata.authors            keyword[]
paper_metadata.abstract           text (boost: 1.5)
paper_metadata.publication_year   integer
paper_metadata.venue              keyword
paper_metadata.doi                keyword
paper_metadata.keywords           keyword[]
paper_metadata.field_of_study    keyword[]
```

### Citations (Nested)
```
citations[].citation_id       keyword
citations[].cited_paper_id    keyword
citations[].citation_type     keyword
citations[].citation_intent   keyword
citations[].citation_context  text
```

### Timestamps
```
created_at        date
updated_at        date
indexed_at        date
```

---

## 🔍 Search Patterns

### 1. Hybrid Search (Semantic + Keyword)

```python
from app.retrieval.index_manager import IndexManager

query = IndexManager.get_hybrid_search_query(
    query_text="transformer architecture",
    query_embedding=[0.1, 0.2, ...],  # 384-dim vector
    top_k=10,
    semantic_weight=0.5  # 0.5 = equal weight
)
```

### 2. Filter by Year

```python
filters = {
    "paper_metadata.publication_year": {
        "range": {"gte": 2017, "lte": 2024}
    }
}
```

### 3. Filter by Author

```python
filters = {
    "paper_metadata.authors": ["Vaswani", "Hinton"]
}
```

### 4. Filter by Section

```python
filters = {
    "section": ["abstract", "conclusion"]
}
```

### 5. Boost Key Sections

```python
query = IndexManager.get_hybrid_search_query(
    query_text="...",
    query_embedding=[...],
    boost_key_sections=True  # Boosts abstract, conclusion
)
```

---

## 📈 Field Boosts

| Field | Boost | Priority |
|-------|-------|----------|
| `paper_metadata.title` | 2.0x | Highest |
| `paper_metadata.abstract` | 1.5x | High |
| `section_title` | 1.2x | Medium |
| `text` | 1.0x | Baseline |
| `is_key_section` | 1.5x | Multiplicative |

---

## ⚙️ HNSW Parameters

```json
{
  "type": "hnsw",
  "m": 16,                    // Connections per node
  "ef_construction": 100      // Build-time accuracy
}
```

**Recommendations:**
- `m=16`: Good balance (default)
- `ef_construction=100-200`: Higher = better accuracy, slower indexing

---

## 🔧 Setup Commands

### Create Indices
```bash
python scripts/setup_elasticsearch.py setup
```

### Verify Indices
```bash
python scripts/setup_elasticsearch.py verify
```

### Delete Indices
```bash
python scripts/setup_elasticsearch.py delete
```

### Check Index Stats
```bash
curl http://localhost:9200/research_papers/_stats?pretty
```

### View Mapping
```bash
curl http://localhost:9200/research_papers/_mapping?pretty
```

---

## 📝 Common Queries

### Get All Papers
```bash
curl -X GET "http://localhost:9200/research_papers/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "unique_papers": {
        "terms": {"field": "paper_id", "size": 1000}
      }
    }
  }'
```

### Count Documents
```bash
curl http://localhost:9200/research_papers/_count?pretty
```

### Get Paper Chunks
```bash
curl -X GET "http://localhost:9200/research_papers/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {"paper_id": "paper-123"}
    },
    "sort": [{"chunk_index": "asc"}]
  }'
```

### Search by Author
```bash
curl -X GET "http://localhost:9200/research_papers/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "query": {
      "term": {"paper_metadata.authors": "Vaswani"}
    }
  }'
```

### Aggregation by Year
```bash
curl -X GET "http://localhost:9200/research_papers/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{
    "size": 0,
    "aggs": {
      "papers_by_year": {
        "terms": {
          "field": "paper_metadata.publication_year",
          "size": 20,
          "order": {"_key": "desc"}
        }
      }
    }
  }'
```

---

## 🎯 RRF (Reciprocal Rank Fusion)

Combines semantic and keyword search results:

```json
{
  "rank": {
    "rrf": {
      "window_size": 20,      // Consider top 20 from each
      "rank_constant": 60     // Smoothing parameter
    }
  }
}
```

**Formula:**
```
RRF_score = Σ (1 / (rank_constant + rank_i))
```

---

## 🚀 Performance Tips

### Indexing
- Use bulk API (100-500 docs per batch)
- Set `refresh_interval: -1` during bulk indexing
- Set `number_of_replicas: 0` during initial load
- Restore settings after indexing

### Searching
- Exclude embeddings from `_source`
- Use filters (cached) instead of queries when possible
- Set appropriate `num_candidates` (5-10x k)
- Use index aliases for zero-downtime updates

### Storage
- Use `best_compression` codec for large indices
- Archive old documents
- Monitor shard size (keep under 50GB per shard)

---

## 📊 Index Settings

### Development
```json
{
  "number_of_shards": 1,
  "number_of_replicas": 0,
  "refresh_interval": "1s"
}
```

### Production
```json
{
  "number_of_shards": 2,
  "number_of_replicas": 1,
  "refresh_interval": "1s",
  "codec": "best_compression"
}
```

---

## 🔍 Analyzers

### scientific_analyzer
- Tokenizer: `standard`
- Filters: `lowercase`, `asciifolding`, `stop`, `stemmer`
- Use: Scientific text, abstracts, papers

### standard_analyzer
- Tokenizer: `standard`
- Filters: `lowercase`
- Use: General text

### exact_analyzer
- Tokenizer: `keyword`
- Filters: `lowercase`
- Use: Exact matching, case-insensitive

---

## 📦 Document Structure Example

```json
{
  "chunk_id": "chunk-abc123",
  "paper_id": "paper-123",
  "chunk_index": 0,
  "text": "Transformers use self-attention mechanisms...",
  "embedding": [0.1, 0.2, ..., 0.9],
  "section": "introduction",
  "section_title": "Introduction",
  "page_number": 1,
  "paper_metadata": {
    "title": "Attention Is All You Need",
    "authors": ["Vaswani", "Shazeer", "Parmar"],
    "abstract": "The dominant sequence transduction models...",
    "publication_year": 2017,
    "venue": "NeurIPS",
    "doi": "10.5555/3295222.3295349",
    "keywords": ["attention", "transformer", "neural networks"]
  },
  "citations": [
    {
      "citation_id": "cite-1",
      "cited_paper_id": "paper-456",
      "cited_title": "Neural Machine Translation",
      "citation_type": "direct",
      "citation_intent": "background"
    }
  ],
  "chunk_metadata": {
    "word_count": 150,
    "has_equations": false,
    "quality_score": 0.95
  },
  "is_key_section": true,
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

## 🛠️ Troubleshooting

| Issue | Solution |
|-------|----------|
| Slow kNN search | Increase `num_candidates`, add filters |
| Poor relevance | Adjust field boosts, tune semantic weight |
| Index too large | Exclude embeddings from `_source`, use compression |
| Out of memory | Reduce `num_candidates`, increase heap size |
| Indexing slow | Use bulk API, disable refresh, remove replicas |

---

## 📚 Resources

- **Full Documentation**: `ELASTICSEARCH_MAPPINGS.md`
- **Architecture**: `ARCHITECTURE.md`
- **Setup Script**: `scripts/setup_elasticsearch.py`
- **Index Manager**: `app/retrieval/index_manager.py`
- **ES Client**: `app/retrieval/elasticsearch_client.py`

---

## ✅ Checklist

- [ ] Elasticsearch running on port 9200
- [ ] Run `python scripts/setup_elasticsearch.py setup`
- [ ] Verify with `python scripts/setup_elasticsearch.py verify`
- [ ] Check index exists: `curl http://localhost:9200/_cat/indices`
- [ ] Test search: Use `/docs` endpoint
- [ ] Monitor performance: Check `_stats` endpoint

---

**Quick Start:**
```bash
# 1. Start Elasticsearch
docker run -d --name elasticsearch -p 9200:9200 \
  -e "discovery.type=single-node" \
  -e "xpack.security.enabled=false" \
  elasticsearch:8.12.0

# 2. Setup indices
python scripts/setup_elasticsearch.py setup

# 3. Verify
python scripts/setup_elasticsearch.py verify

# 4. Start application
python main.py
```

🎉 **Ready to index and search!**
