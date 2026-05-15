"""
Core configuration module using Pydantic settings.
"""
from typing import List, Optional
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # Application
    app_name: str = Field(default="Research Assistant", alias="APP_NAME")
    app_version: str = Field(default="1.0.0", alias="APP_VERSION")
    debug: bool = Field(default=False, alias="DEBUG")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    # Server
    host: str = Field(default="0.0.0.0", alias="HOST")
    port: int = Field(default=8000, alias="PORT")

    # ── Groq LLM ──────────────────────────────────────────────────────────
    groq_api_key: str = Field(default="", alias="GROQ_API_KEY")
    groq_model: str = Field(default="llama3-8b-8192", alias="GROQ_MODEL")
    groq_temperature: float = Field(default=0.3, alias="GROQ_TEMPERATURE")
    groq_max_tokens: int = Field(default=2048, alias="GROQ_MAX_TOKENS")

    # ── Qdrant Cloud ──────────────────────────────────────────────────────
    qdrant_url: str = Field(default="", alias="QDRANT_URL")
    qdrant_api_key: str = Field(default="", alias="QDRANT_API_KEY")
    qdrant_collection: str = Field(default="research_papers", alias="QDRANT_COLLECTION")

    # ── Embeddings ────────────────────────────────────────────────────────
    embedding_model: str = Field(
        default="sentence-transformers/all-MiniLM-L6-v2",
        alias="EMBEDDING_MODEL"
    )
    embedding_dimension: int = Field(default=384, alias="EMBEDDING_DIMENSION")
    embedding_batch_size: int = Field(default=32, alias="EMBEDDING_BATCH_SIZE")

    # ── Document Processing ───────────────────────────────────────────────
    max_upload_size_mb: int = Field(default=50, alias="MAX_UPLOAD_SIZE_MB")
    chunk_size: int = Field(default=512, alias="CHUNK_SIZE")
    chunk_overlap: int = Field(default=50, alias="CHUNK_OVERLAP")
    min_chunk_length: int = Field(default=100, alias="MIN_CHUNK_LENGTH")

    # ── Retrieval ─────────────────────────────────────────────────────────
    default_top_k: int = Field(default=5, alias="DEFAULT_TOP_K")
    hybrid_search_weight: float = Field(default=0.5, alias="HYBRID_SEARCH_WEIGHT")
    min_similarity_score: float = Field(default=0.3, alias="MIN_SIMILARITY_SCORE")

    # ── Agent ─────────────────────────────────────────────────────────────
    agent_max_iterations: int = Field(default=5, alias="AGENT_MAX_ITERATIONS")
    agent_verbose: bool = Field(default=True, alias="AGENT_VERBOSE")

    # ── Storage ───────────────────────────────────────────────────────────
    upload_dir: Path = Field(default=Path("data/uploads"), alias="UPLOAD_DIR")
    processed_dir: Path = Field(default=Path("data/processed"), alias="PROCESSED_DIR")
    log_dir: Path = Field(default=Path("logs"), alias="LOG_DIR")

    # ── Rate Limiting ─────────────────────────────────────────────────────
    rate_limit_per_minute: int = Field(default=60, alias="RATE_LIMIT_PER_MINUTE")

    # ── CORS ──────────────────────────────────────────────────────────────
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8501"],
        alias="CORS_ORIGINS"
    )

    # ── Legacy Elasticsearch (kept for backward compat, unused) ───────────
    elasticsearch_url: str = Field(default="", alias="ELASTICSEARCH_URL")
    elasticsearch_index: str = Field(default="research_papers", alias="ELASTICSEARCH_INDEX")
    elasticsearch_username: Optional[str] = Field(default=None, alias="ELASTICSEARCH_USERNAME")
    elasticsearch_password: Optional[str] = Field(default=None, alias="ELASTICSEARCH_PASSWORD")

    # ── Legacy Ollama (kept for backward compat, unused) ─────────────────
    ollama_base_url: str = Field(default="http://localhost:11434", alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3", alias="OLLAMA_MODEL")
    ollama_temperature: float = Field(default=0.7, alias="OLLAMA_TEMPERATURE")
    ollama_max_tokens: int = Field(default=2048, alias="OLLAMA_MAX_TOKENS")

    @field_validator("upload_dir", "processed_dir", "log_dir")
    @classmethod
    def create_directories(cls, v: Path) -> Path:
        v.mkdir(parents=True, exist_ok=True)
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        valid_levels = ["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"]
        v = v.upper()
        if v not in valid_levels:
            raise ValueError(f"Log level must be one of {valid_levels}")
        return v

    @property
    def max_upload_size_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024


settings = Settings()
