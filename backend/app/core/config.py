"""Application configuration using Pydantic Settings"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables"""

    # App
    app_name: str = "Halo"
    app_version: str = "1.0.0"
    debug: bool = False

    # OpenAI GPT-5 via GitHub Models (Azure AI Inference)
    github_token: str = ""
    openai_model: str = "gpt-4o"
    openai_endpoint: str = "https://models.github.ai/inference"

    # Embeddings (sentence-transformers, local)
    embedding_model: str = "all-MiniLM-L6-v2"

    # RAG (ChromaDB)
    chroma_persist_dir: str = "./knowledge/chroma_db"
    rag_top_k: int = 5

    # Stellar
    stellar_network: str = "testnet"
    stellar_horizon_url: str = "https://horizon-testnet.stellar.org"
    stellar_soroban_rpc_url: str = "https://soroban-testnet.stellar.org"
    stellar_hot_wallet_secret: str = ""

    # Database
    database_url: str = "postgresql://halo:halo@localhost:5432/halo"

    # Docker
    docker_timeout_seconds: int = 60
    soroban_builder_image: str = "halo-soroban-builder:latest"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


settings = get_settings()
