"""
Configuration settings for the RAG application.
Handles environment variables and application settings.
"""
import os
from functools import lru_cache
from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings from environment variables."""

    # Application
    app_name: str = "AI Knowledge Assistant API"
    debug: bool = False

    # Database
    database_url: str = Field(alias="DATABASE_URL")

    AZURE_OPENAI_API_KEY: str
    AZURE_OPENAI_ENDPOINT: str
    AZURE_OPENAI_DEPLOYMENT: str
    AZURE_OPENAI_API_VERSION: str

    # Supabase
    supabase_url: str = Field(alias="NEXT_PUBLIC_SUPABASE_URL")
    supabase_key: str = Field(alias="NEXT_PUBLIC_SUPABASE_ANON_KEY")
    supabase_service_key: Optional[str] = Field(default=None, alias="SUPABASE_SERVICE_KEY")

    # Redis (removed - no longer using Celery)
    # redis_url: str = "redis://localhost:6379/0"

    # AI Models
    embedding_model: str = "sentence-transformers/paraphrase-MiniLM-L3-v2"
    llm_model: str = "google/flan-t5-small"  # Can be changed to Llama/Mistral later
    max_tokens: int = 512

    # Vector Search
    similarity_threshold: float = 0.01  # Lowered for TF-IDF embeddings which have lower similarity scores
    max_chunks: int = 5

    # Document Processing
    max_file_size: int = 10 * 1024 * 1024  # 10MB
    chunk_size: int = 1000
    chunk_overlap: int = 100

    # Security
    secret_key: str = "your-super-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30

    model_config = {
        "env_file": ".env",
        "case_sensitive": False,
        "extra": "ignore",
        "populate_by_name": True
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached application settings."""
    return Settings()


# Global settings instance
settings = get_settings()