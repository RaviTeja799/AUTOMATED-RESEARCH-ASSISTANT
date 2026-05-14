# Elasticsearch Index Mappings Documentation

## Overview

This document describes the Elasticsearch index mappings designed for the Research Assistant system. The mappings support **hybrid retrieval** (semantic + keyword search), **citation tracking**, **section-aware chunking**, and **rich metadata filtering**.

---

## Index Architecture

### 1. Main Papers Index (`research_papers`)
Stores document chunks with embeddings and metadata for hybrid search.

### 2. Papers Summary Index (`research_papers_summaries`)
Stores paper-level summaries and aggregated information.

### 3. Citation Graph Index (`research_papers_citations`)
Stores citation relationships for graph analysis.

---

## Main Papers Index Mapping

### Core Fields

#### **Chunk Identification**
```json
{
  "chunk_id": "keyword",        // Unique chunk identifier
  "paper_id": "keyword",         // Paper identifier
  "chunk_index": "integer"       // Position in document
}
```

#### **Text Content** (Keyword Search)
```json
{
  "text": {
    "type": "text",
    "analyzer": "scientific_analyzer",
    "fields": {
      "keyword": "keyword",      // Exact matching
      "exact": "text",           // Case-sensitive search
      "standard": "text"         // Standard analyzer
    }
  }
}
```

**Analyzers:**
- `scientific_analyzer`: Custom analyzer with stemming and stopwords for scientific text
- `standard_analyzer`: Standard Elasticsearch analyzer
- `exact_analyzer`: Keyword-based for exact matching

#### **Dense Vector Embedding** (Semantic Search)
```json
{
  "embedding": {
    "type": "dense_vector",
    "dims": 384,                 // Configurable via settings
    "index": true,
    "similarity": "cosine",
    "index_options": {
      "type": "hnsw",            // Hierarchical Navigable Small World
      "m": 16,                   // Number of connections
      "ef_construction": 100     // Construction time parameter
    }
  }
}
```

**HNSW Parameters:**
- `m=16`: Good balance between speed and accuracy
- `ef_construction=100`: Higher = better accuracy, slower indexing

---

### Section Information

```json
{
  "section": "keyword",              // Section type (abstract, intro, methods, etc.)
  "section_title": "text",           // Section heading
  "section_hierarchy": "keyword"     // Nested section path
}
```

**Common Section Types:**
- `abstract`
- `introduction`
- `related_work`
- `methodology`
- `experiments`
- `results`
- `discussion`
- `conclusion`
- `references`

---

### Position Information

```json
{
  "page_number": "integer",
  "start_char": "integer",
  "end_char": "integer"
}
```

---

### Paper Metadata (Nested Object)

```json
{
  "paper_metadata": {
    "title": {
      "type": "text",
      "boost": 2.0,                // Higher relevance for title matches
      "fields": {
        "keyword": "keyword",
        "exact": "text"
      }
    },
    "authors": "keyword[]",        // Array of author names
    "author_affiliations": "keyword[]",
    "abstract": {
      "type": "text",
      "boost": 1.5                 // Higher relevance for abstract matches
    },
    "publication_date": "date",
    "publication_year": "integer",
    "venue": "keyword",            // Conference/journal name
    "doi": "keyword",
    "arxiv_id": "keyword",
    "pmid": "keyword",             // PubMed ID
    "keywords": "keyword[]",
    "num_pages": "integer",
    "language": "keyword",
    "field_of_study": "keyword[]"
  }
}
```

**Date Formats Supported:**
- `yyyy-MM-dd` (2024-01-15)
- `yyyy-MM` (2024-01)
- `yyyy` (2024)
- `epoch_millis` (Unix timestamp)

---

### Citation Information (Nested)

```json
{
  "citations": [
    {
      "citation_id": "keyword",
      "cited_paper_id": "keyword",
      "cited_title": "text",
      "cited_authors": "keyword[]",
      "citation_context": "text",      // Surrounding text
      "citation_type": "keyword",      // direct, indirect, self
      "citation_intent": "keyword"     // background, method, result
    }
  ]
}
```

**Citation Types:**
- `direct`: Direct citation with specific claim
- `indirect`: General reference
- `self`: Self-citation

**Citation Intents:**
- `background`: Background/related work
- `method`: Methodology reference
- `result`: Result comparison
- `extension`: Building upon work

---

### References

```json
{
  "references": "keyword[]",         // List of referenced paper IDs
  "num_references": "integer"
}
```

---

### Figures and Tables

```json
{
  "has_figures": "boolean",
  "has_tables": "boolean",
  "figure_captions": "text",
  "table_captions": "text"
}
```

---

### Chunk Metadata

```json
{
  "chunk_metadata": {
    "word_count": "integer",
    "char_count": "integer",
    "sentence_count": "integer",
    "has_equations": "boolean",
    "has_code": "boolean",
    "language_detected": "keyword",
    "quality_score": "float"         // 0.0 - 1.0
  }
}
```

---

### Semantic Metadata (Nested)

```json
{
  "entities": [
    {
      "text": "keyword",
      "type": "keyword",               // PERSON, ORG, METHOD, etc.
      "confidence": "float"
    }
  ],
  "topics": "keyword[]",
  "concepts": "keyword[]"
}
```

**Entity Types:**
- `PERSON`: Person names
- `ORG`: Organizations
- `METHOD`: Methodologies
- `DATASET`: Dataset names
- `METRIC`: Evaluation metrics

---

### File Information

```json
{
  "file_metadata": {
    "filename": "keyword",
    "file_path": "keyword",
    "file_size_bytes": "long",
    "file_hash": "keyword",            // SHA-256 hash
    "mime_type": "keyword"
  }
}
```

---

### Timestamps

```json
{
  "created_at": "date",
  "updated_at": "date",
  "indexed_at": "date"
}
```

---

### Processing Information

```json
{
  "processing_metadata": {
    "extraction_method": "keyword",    // pymupdf, pdfplumber, etc.
    "chunking_method": "keyword",      // section-aware, fixed-size, etc.
    "embedding_model": "keyword",      // Model name
    "processing_version": "keyword"    // Version for reprocessing
  }
}
```

---

### Search Optimization

```json
{
  "search_boost": "float",             // Custom boost factor
  "is_key_section": "boolean"          // Abstract, conclusion, etc.
}
```

---

### User Annotations (Nested)

```json
{
  "annotations": [
    {
      "user_id": "keyword",
      "annotation_type": "keyword",    // highlight, note, tag
      "annotation_text": "text",
      "created_at": "date"
    }
  ]
}
```

---

### Access Control

```json
{
  "access_control": {
    "owner_id": "keyword",
    "visibility": "keyword",           // public, private, shared
    "shared_with": "keyword[]"
  }
}
```

---

## Hybrid Search Query

### Query Structure

The hybrid search combines:
1. **Semantic Search** (kNN with dense vectors)
2. **Keyword Search** (BM25 with text fields)
3. **RRF** (Reciprocal Rank Fusion) for combining results

### Example Query

```json
{
  "size": 10,
  "query": {
    "bool": {
      "should": [
        {
          "multi_match": {
            "query": "transformer architecture",
            "fields": [
              "text^1.0",
              "paper_metadata.title^2.0",
              "paper_metadata.abstract^1.5",
              "section_title^1.2"
            ],
            "type": "best_fields",
            "tie_breaker": 0.3
          }
        },
        {
          "term": {
            "is_key_section": {
              "value": true,
              "boost": 1.5
            }
          }
        }
      ],
      "filter": [
        {
          "range": {
            "paper_metadata.publication_year": {
              "gte": 2017
            }
          }
        }
      ]
    }
  },
  "knn": {
    "field": "embedding",
    "query_vector": [0.1, 0.2, ...],
    "k": 20,
    "num_candidates": 100
  },
  "rank": {
    "rrf": {
      "window_size": 20,
      "rank_constant": 60
    }
  },
  "_source": {
    "excludes": ["embedding"]
  },
  "highlight": {
    "fields": {
      "text": {
        "fragment_size": 150,
        "number_of_fragments": 3
      }
    }
  }
}
```

### Field Boosts

- `paper_metadata.title`: **2.0x** (highest priority)
- `paper_metadata.abstract`: **1.5x**
- `section_title`: **1.2x**
- `text`: **1.0x** (baseline)
- `is_key_section`: **1.5x** (multiplicative)

---

## Index Settings

### Sharding and Replication

```json
{
  "number_of_shards": 2,
  "number_of_replicas": 1,
  "refresh_interval": "1s",
  "max_result_window": 10000
}
```

**Recommendations:**
- **Development**: 1 shard, 0 replicas
- **Production**: 2-5 shards, 1-2 replicas
- **Large datasets**: More shards for parallelism

---

## Papers Summary Index

Stores one document per paper with aggregated information.

### Key Fields

```json
{
  "paper_id": "keyword",
  "title": "text",
  "authors": "keyword[]",
  "abstract": "text",
  "summary": "text",              // Generated summary
  "key_findings": "text",
  "methodology": "text",
  "limitations": "text",
  "num_chunks": "integer",
  "num_citations": "integer",
  "num_references": "integer"
}
```

---

## Citation Graph Index

Stores paper-to-paper citation relationships.

### Key Fields

```json
{
  "source_paper_id": "keyword",
  "target_paper_id": "keyword",
  "citation_type": "keyword",
  "citation_context": "text",
  "citation_count": "integer"
}
```

---

## Usage Examples

### 1. Setup Indices

```bash
python scripts/setup_elasticsearch.py setup
```

### 2. Verify Indices

```bash
python scripts/setup_elasticsearch.py verify
```

### 3. Delete Indices

```bash
python scripts/setup_elasticsearch.py delete
```

### 4. Index a Document

```python
from app.retrieval.elasticsearch_client import ElasticsearchClient
from app.models.schemas import DocumentChunk

chunk = DocumentChunk(
    paper_id="paper-123",
    text="Transformers use self-attention mechanisms...",
    section="introduction",
    page_number=1,
    chunk_index=0,
    embedding=[0.1, 0.2, ...],
    metadata={}
)

await es_client.index_chunks([chunk], paper_metadata={
    "title": "Attention Is All You Need",
    "authors": ["Vaswani et al."],
    "publication_year": 2017
})
```

### 5. Hybrid Search

```python
from app.retrieval.index_manager import IndexManager

query = IndexManager.get_hybrid_search_query(
    query_text="transformer architecture",
    query_embedding=[0.1, 0.2, ...],
    top_k=10,
    filters={"paper_metadata.publication_year": {"range": {"gte": 2017}}},
    semantic_weight=0.5
)

results = await es_client.search(index="research_papers", body=query)
```

### 6. Aggregations

```python
# Get top authors
query = IndexManager.get_aggregation_query(
    field="paper_metadata.authors",
    size=10
)

results = await es_client.search(index="research_papers", body=query)
```

---

## Performance Considerations

### Indexing Performance

- **Bulk indexing**: Use batch size of 100-500 documents
- **Refresh interval**: Set to `-1` during bulk indexing, restore to `1s` after
- **Replicas**: Set to `0` during initial indexing, increase after

### Search Performance

- **kNN parameters**: 
  - `k`: Number of nearest neighbors (10-50)
  - `num_candidates`: 5-10x the value of `k`
- **HNSW parameters**:
  - `m`: 16 (default, good balance)
  - `ef_construction`: 100-200 (higher = better accuracy)

### Storage Optimization

- **Exclude embeddings** from `_source` in search results
- **Use `doc_values: false`** for fields not used in aggregations/sorting
- **Compress text fields** with `best_compression` codec

---

## Monitoring

### Index Stats

```bash
curl http://localhost:9200/research_papers/_stats?pretty
```

### Mapping

```bash
curl http://localhost:9200/research_papers/_mapping?pretty
```

### Search Performance

```bash
curl -X GET "http://localhost:9200/research_papers/_search?pretty" \
  -H 'Content-Type: application/json' \
  -d '{"profile": true, "query": {...}}'
```

---

## Migration and Versioning

### Reindexing

When mappings change, use reindex API:

```bash
POST _reindex
{
  "source": {
    "index": "research_papers_old"
  },
  "dest": {
    "index": "research_papers_new"
  }
}
```

### Index Aliases

Use aliases for zero-downtime updates:

```bash
POST _aliases
{
  "actions": [
    {"remove": {"index": "research_papers_v1", "alias": "research_papers"}},
    {"add": {"index": "research_papers_v2", "alias": "research_papers"}}
  ]
}
```

---

## Best Practices

1. **Use index templates** for automatic mapping application
2. **Version your mappings** in the `processing_metadata.processing_version` field
3. **Monitor index size** and shard distribution
4. **Use filters** instead of queries when possible (cached)
5. **Exclude embeddings** from search results to reduce network overhead
6. **Boost key sections** (abstract, conclusion) for better relevance
7. **Use RRF** for combining semantic and keyword search
8. **Set appropriate `num_candidates`** for kNN search (5-10x k)
9. **Use bulk API** for indexing multiple documents
10. **Monitor query performance** with the profile API

---

## Troubleshooting

### Issue: Slow kNN search

**Solution:**
- Increase `num_candidates`
- Reduce `k`
- Add filters to reduce search space
- Check HNSW parameters

### Issue: Poor search relevance

**Solution:**
- Adjust field boosts
- Tune semantic vs keyword weight
- Use query-time boosting
- Add more training data for embeddings

### Issue: Index too large

**Solution:**
- Exclude embeddings from `_source`
- Use `best_compression` codec
- Reduce number of replicas
- Archive old documents

---

## Summary

The Elasticsearch mappings provide:

✅ **Hybrid retrieval** (semantic + keyword)
✅ **Dense vector search** with HNSW
✅ **Rich metadata** for filtering
✅ **Citation tracking** with nested objects
✅ **Section-aware** chunking support
✅ **Multi-field analysis** for different search types
✅ **Boosting** for key sections
✅ **RRF** for result fusion
✅ **Scalable** architecture
✅ **Production-ready** configuration

The mappings are designed to support all features of the Research Assistant system while maintaining high performance and scalability.
