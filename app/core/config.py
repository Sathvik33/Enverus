from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost/ragdb"

    OLLAMA_BASE_URL: str = "http://localhost:11434"
    LLM_MODEL: str = "qwen2.5:7b"
    LLM_PROVIDER: str = "ollama"  # "ollama" or "groq"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "openai/gpt-oss-120b"

    TEXT_EMBEDDING_MODEL: str = "sentence-transformers/all-mpnet-base-v2"
    TEXT_EMBEDDING_DIM: int = 768

    CLIP_MODEL: str = "google/siglip-base-patch16-224"
    IMAGE_EMBEDDING_MODEL: str = "google/siglip-base-patch16-224"
    IMAGE_EMBEDDING_DIM: int = 768

    RERANKER_MODEL: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"

    TOP_K: int = 10
    FINAL_TOP_K: int = 5
    RRF_K: int = 60

    CHUNK_SIZE: int = 600
    CHUNK_OVERLAP: int = 80

    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    LOG_LEVEL: str = "INFO"
    UPLOAD_DIR: str = "data/documents"
    IMAGE_DIR: str = "data/images"

    PII_DETECTION_ENABLED: bool = True
    OUTPUT_GROUNDING_ENABLED: bool = True

    BACKEND_URL: str = "http://localhost:8000"

    JWT_SECRET_KEY: str = "enverus-rag-super-secret-jwt-key-change-in-prod-2024"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


@lru_cache()
def get_settings() -> Settings:
    return Settings()
