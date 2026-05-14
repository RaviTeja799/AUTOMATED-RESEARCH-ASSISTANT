"""
Elasticsearch index management with mappings for hybrid retrieval.
"""
from typing import Dict, Any, Optional
from datetime import datetime

from app.core.config import settings
from app.utils.logger import app_logger


class IndexManager:
    """Manage Elasticsearch index creation and mappings."""
    
    @staticmethod
    def get_papers_index_mapping() -> Dict[str, Any]:
        """
        Get the complete index mapping for research papers.
        
        This mapping supports:
        - Dense vector embeddings for semantic search
        - Text fields for keyword search (BM25)
        - Nested metadata for filtering
        - Citation tracking
        - Section-aware chunking
        
        Returns:
            Complete index mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 2,
                "number_of_replicas": 1,
                "refresh_interval": "1s",
                "max_result_window": 10000,
                "analysis": {
                    "analyzer": {
                        "standard_analyzer": {
                            "type": "standard",
                            "stopwords": "_english_"
                        },
                        "scientific_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": [
                                "lowercase",
                                "asciifolding",
                                "scientific_stop",
                                "scientific_stemmer"
                            ]
                        },
                        "exact_analyzer": {
                            "type": "custom",
                            "tokenizer": "keyword",
                            "filter": ["lowercase"]
                        }
                    },
                    "filter": {
                        "scientific_stop": {
                            "type": "stop",
                            "stopwords": "_english_"
                        },
                        "scientific_stemmer": {
                            "type": "stemmer",
                            "language": "english"
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    # ============================================
                    # Chunk Identification
                    # ============================================
                    "chunk_id": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    "paper_id": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    "chunk_index": {
                        "type": "integer",
                        "doc_values": True
                    },
                    
                    # ============================================
                    # Text Content (for keyword search)
                    # ============================================
                    "text": {
                        "type": "text",
                        "analyzer": "scientific_analyzer",
                        "search_analyzer": "scientific_analyzer",
                        "term_vector": "with_positions_offsets",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 256
                            },
                            "exact": {
                                "type": "text",
                                "analyzer": "exact_analyzer"
                            },
                            "standard": {
                                "type": "text",
                                "analyzer": "standard_analyzer"
                            }
                        }
                    },
                    
                    # ============================================
                    # Dense Vector Embedding (for semantic search)
                    # ============================================
                    "embedding": {
                        "type": "dense_vector",
                        "dims": settings.embedding_dimension,
                        "index": True,
                        "similarity": "cosine",
                        "index_options": {
                            "type": "hnsw",
                            "m": 16,
                            "ef_construction": 100
                        }
                    },
                    
                    # ============================================
                    # Section Information
                    # ============================================
                    "section": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    "section_title": {
                        "type": "text",
                        "analyzer": "scientific_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword"
                            }
                        }
                    },
                    "section_hierarchy": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    
                    # ============================================
                    # Position Information
                    # ============================================
                    "page_number": {
                        "type": "integer",
                        "doc_values": True
                    },
                    "start_char": {
                        "type": "integer"
                    },
                    "end_char": {
                        "type": "integer"
                    },
                    
                    # ============================================
                    # Paper Metadata (nested for rich filtering)
                    # ============================================
                    "paper_metadata": {
                        "type": "object",
                        "properties": {
                            "title": {
                                "type": "text",
                                "analyzer": "scientific_analyzer",
                                "boost": 2.0,
                                "fields": {
                                    "keyword": {
                                        "type": "keyword",
                                        "ignore_above": 512
                                    },
                                    "exact": {
                                        "type": "text",
                                        "analyzer": "exact_analyzer"
                                    }
                                }
                            },
                            "authors": {
                                "type": "keyword",
                                "doc_values": True
                            },
                            "author_affiliations": {
                                "type": "keyword"
                            },
                            "abstract": {
                                "type": "text",
                                "analyzer": "scientific_analyzer",
                                "boost": 1.5
                            },
                            "publication_date": {
                                "type": "date",
                                "format": "yyyy-MM-dd||yyyy-MM||yyyy||epoch_millis"
                            },
                            "publication_year": {
                                "type": "integer",
                                "doc_values": True
                            },
                            "venue": {
                                "type": "keyword",
                                "fields": {
                                    "text": {
                                        "type": "text",
                                        "analyzer": "standard_analyzer"
                                    }
                                }
                            },
                            "doi": {
                                "type": "keyword"
                            },
                            "arxiv_id": {
                                "type": "keyword"
                            },
                            "pmid": {
                                "type": "keyword"
                            },
                            "keywords": {
                                "type": "keyword",
                                "doc_values": True
                            },
                            "num_pages": {
                                "type": "integer"
                            },
                            "language": {
                                "type": "keyword"
                            },
                            "field_of_study": {
                                "type": "keyword",
                                "doc_values": True
                            }
                        }
                    },
                    
                    # ============================================
                    # Citation Information
                    # ============================================
                    "citations": {
                        "type": "nested",
                        "properties": {
                            "citation_id": {
                                "type": "keyword"
                            },
                            "cited_paper_id": {
                                "type": "keyword"
                            },
                            "cited_title": {
                                "type": "text",
                                "analyzer": "scientific_analyzer"
                            },
                            "cited_authors": {
                                "type": "keyword"
                            },
                            "citation_context": {
                                "type": "text",
                                "analyzer": "scientific_analyzer"
                            },
                            "citation_type": {
                                "type": "keyword"
                            },
                            "citation_intent": {
                                "type": "keyword"
                            }
                        }
                    },
                    
                    # ============================================
                    # References (papers cited by this chunk)
                    # ============================================
                    "references": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    "num_references": {
                        "type": "integer"
                    },
                    
                    # ============================================
                    # Figures and Tables
                    # ============================================
                    "has_figures": {
                        "type": "boolean"
                    },
                    "has_tables": {
                        "type": "boolean"
                    },
                    "figure_captions": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "table_captions": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    
                    # ============================================
                    # Chunk Metadata
                    # ============================================
                    "chunk_metadata": {
                        "type": "object",
                        "properties": {
                            "word_count": {
                                "type": "integer"
                            },
                            "char_count": {
                                "type": "integer"
                            },
                            "sentence_count": {
                                "type": "integer"
                            },
                            "has_equations": {
                                "type": "boolean"
                            },
                            "has_code": {
                                "type": "boolean"
                            },
                            "language_detected": {
                                "type": "keyword"
                            },
                            "quality_score": {
                                "type": "float"
                            }
                        }
                    },
                    
                    # ============================================
                    # Semantic Metadata
                    # ============================================
                    "entities": {
                        "type": "nested",
                        "properties": {
                            "text": {
                                "type": "keyword"
                            },
                            "type": {
                                "type": "keyword"
                            },
                            "confidence": {
                                "type": "float"
                            }
                        }
                    },
                    "topics": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    "concepts": {
                        "type": "keyword",
                        "doc_values": True
                    },
                    
                    # ============================================
                    # File Information
                    # ============================================
                    "file_metadata": {
                        "type": "object",
                        "properties": {
                            "filename": {
                                "type": "keyword"
                            },
                            "file_path": {
                                "type": "keyword"
                            },
                            "file_size_bytes": {
                                "type": "long"
                            },
                            "file_hash": {
                                "type": "keyword"
                            },
                            "mime_type": {
                                "type": "keyword"
                            }
                        }
                    },
                    
                    # ============================================
                    # Timestamps
                    # ============================================
                    "created_at": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "updated_at": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    "indexed_at": {
                        "type": "date",
                        "format": "strict_date_optional_time||epoch_millis"
                    },
                    
                    # ============================================
                    # Processing Information
                    # ============================================
                    "processing_metadata": {
                        "type": "object",
                        "properties": {
                            "extraction_method": {
                                "type": "keyword"
                            },
                            "chunking_method": {
                                "type": "keyword"
                            },
                            "embedding_model": {
                                "type": "keyword"
                            },
                            "processing_version": {
                                "type": "keyword"
                            }
                        }
                    },
                    
                    # ============================================
                    # Search Optimization
                    # ============================================
                    "search_boost": {
                        "type": "float",
                        "doc_values": True
                    },
                    "is_key_section": {
                        "type": "boolean"
                    },
                    
                    # ============================================
                    # User Annotations (for future use)
                    # ============================================
                    "annotations": {
                        "type": "nested",
                        "properties": {
                            "user_id": {
                                "type": "keyword"
                            },
                            "annotation_type": {
                                "type": "keyword"
                            },
                            "annotation_text": {
                                "type": "text"
                            },
                            "created_at": {
                                "type": "date"
                            }
                        }
                    },
                    
                    # ============================================
                    # Access Control (for future use)
                    # ============================================
                    "access_control": {
                        "type": "object",
                        "properties": {
                            "owner_id": {
                                "type": "keyword"
                            },
                            "visibility": {
                                "type": "keyword"
                            },
                            "shared_with": {
                                "type": "keyword"
                            }
                        }
                    }
                }
            }
        }
    
    @staticmethod
    def get_papers_summary_index_mapping() -> Dict[str, Any]:
        """
        Get index mapping for paper-level summaries (separate from chunks).
        
        This index stores one document per paper with aggregated information.
        
        Returns:
            Summary index mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1,
                "analysis": {
                    "analyzer": {
                        "scientific_analyzer": {
                            "type": "custom",
                            "tokenizer": "standard",
                            "filter": ["lowercase", "asciifolding", "stop", "stemmer"]
                        }
                    }
                }
            },
            "mappings": {
                "properties": {
                    "paper_id": {
                        "type": "keyword"
                    },
                    "title": {
                        "type": "text",
                        "analyzer": "scientific_analyzer",
                        "fields": {
                            "keyword": {
                                "type": "keyword",
                                "ignore_above": 512
                            }
                        }
                    },
                    "authors": {
                        "type": "keyword"
                    },
                    "abstract": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "summary": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "key_findings": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "methodology": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "limitations": {
                        "type": "text",
                        "analyzer": "scientific_analyzer"
                    },
                    "publication_year": {
                        "type": "integer"
                    },
                    "venue": {
                        "type": "keyword"
                    },
                    "doi": {
                        "type": "keyword"
                    },
                    "keywords": {
                        "type": "keyword"
                    },
                    "field_of_study": {
                        "type": "keyword"
                    },
                    "num_chunks": {
                        "type": "integer"
                    },
                    "num_citations": {
                        "type": "integer"
                    },
                    "num_references": {
                        "type": "integer"
                    },
                    "created_at": {
                        "type": "date"
                    },
                    "updated_at": {
                        "type": "date"
                    }
                }
            }
        }
    
    @staticmethod
    def get_citation_graph_index_mapping() -> Dict[str, Any]:
        """
        Get index mapping for citation graph (paper-to-paper relationships).
        
        This index stores citation relationships for graph analysis.
        
        Returns:
            Citation graph index mapping configuration
        """
        return {
            "settings": {
                "number_of_shards": 1,
                "number_of_replicas": 1
            },
            "mappings": {
                "properties": {
                    "source_paper_id": {
                        "type": "keyword"
                    },
                    "target_paper_id": {
                        "type": "keyword"
                    },
                    "citation_type": {
                        "type": "keyword"
                    },
                    "citation_context": {
                        "type": "text"
                    },
                    "citation_count": {
                        "type": "integer"
                    },
                    "created_at": {
                        "type": "date"
                    }
                }
            }
        }
    
    @staticmethod
    def create_index_template() -> Dict[str, Any]:
        """
        Create an index template for automatic index creation.
        
        Returns:
            Index template configuration
        """
        return {
            "index_patterns": [f"{settings.elasticsearch_index}*"],
            "template": IndexManager.get_papers_index_mapping(),
            "priority": 100,
            "version": 1,
            "_meta": {
                "description": "Research papers index template with hybrid retrieval support",
                "created_by": "Research Assistant",
                "created_at": datetime.utcnow().isoformat()
            }
        }
    
    @staticmethod
    def get_hybrid_search_query(
        query_text: str,
        query_embedding: list,
        top_k: int = 10,
        filters: Optional[Dict[str, Any]] = None,
        semantic_weight: float = 0.5,
        boost_key_sections: bool = True
    ) -> Dict[str, Any]:
        """
        Build a hybrid search query combining semantic and keyword search.
        
        Args:
            query_text: Text query for keyword search
            query_embedding: Embedding vector for semantic search
            top_k: Number of results to return
            filters: Optional filters (e.g., paper_id, section, date range)
            semantic_weight: Weight for semantic vs keyword (0-1)
            boost_key_sections: Boost results from key sections
            
        Returns:
            Elasticsearch query DSL
        """
        # Build filter clauses
        filter_clauses = []
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {field: value}})
                elif isinstance(value, dict) and "range" in value:
                    filter_clauses.append({"range": {field: value["range"]}})
                else:
                    filter_clauses.append({"term": {field: value}})
        
        # Keyword search query (BM25)
        text_query = {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query_text,
                            "fields": [
                                "text^1.0",
                                "text.standard^0.8",
                                "paper_metadata.title^2.0",
                                "paper_metadata.abstract^1.5",
                                "section_title^1.2"
                            ],
                            "type": "best_fields",
                            "tie_breaker": 0.3
                        }
                    }
                ],
                "minimum_should_match": 1
            }
        }
        
        # Add boost for key sections
        if boost_key_sections:
            text_query["bool"]["should"].append({
                "term": {
                    "is_key_section": {
                        "value": True,
                        "boost": 1.5
                    }
                }
            })
        
        # Add filters
        if filter_clauses:
            text_query["bool"]["filter"] = filter_clauses
        
        # Semantic search using kNN
        knn_query = {
            "field": "embedding",
            "query_vector": query_embedding,
            "k": top_k * 2,
            "num_candidates": top_k * 10
        }
        
        if filter_clauses:
            knn_query["filter"] = filter_clauses
        
        # Combine with RRF (Reciprocal Rank Fusion)
        query = {
            "size": top_k,
            "query": text_query,
            "knn": knn_query,
            "rank": {
                "rrf": {
                    "window_size": top_k * 2,
                    "rank_constant": 60
                }
            },
            "_source": {
                "excludes": ["embedding"]  # Don't return embeddings in results
            },
            "highlight": {
                "fields": {
                    "text": {
                        "fragment_size": 150,
                        "number_of_fragments": 3,
                        "pre_tags": ["<mark>"],
                        "post_tags": ["</mark>"]
                    }
                }
            }
        }
        
        return query
    
    @staticmethod
    def get_aggregation_query(
        field: str,
        size: int = 10,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Build an aggregation query for faceted search.
        
        Args:
            field: Field to aggregate on
            size: Number of buckets to return
            filters: Optional filters
            
        Returns:
            Elasticsearch aggregation query
        """
        query = {
            "size": 0,
            "aggs": {
                f"{field}_agg": {
                    "terms": {
                        "field": field,
                        "size": size
                    }
                }
            }
        }
        
        if filters:
            filter_clauses = []
            for f, value in filters.items():
                if isinstance(value, list):
                    filter_clauses.append({"terms": {f: value}})
                else:
                    filter_clauses.append({"term": {f: value}})
            
            query["query"] = {
                "bool": {
                    "filter": filter_clauses
                }
            }
        
        return query


# Export for easy access
__all__ = ["IndexManager"]
