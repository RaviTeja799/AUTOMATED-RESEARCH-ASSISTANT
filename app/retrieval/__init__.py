"""Retrieval and search functionality."""
from app.retrieval.elasticsearch_client import ElasticsearchClient, es_client

__all__ = ["ElasticsearchClient", "es_client"]
