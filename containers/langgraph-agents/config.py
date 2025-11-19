"""
Configuration management for LangGraph multi-agent system.
Supports easy switching between Ollama and OpenAI-compatible providers.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal


class Settings(BaseSettings):
    """Application settings with environment variable support."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Configuration
    llm_provider: Literal["ollama", "openai"] = "ollama"

    # Ollama
    ollama_base_url: str = "http://ollama:11434"
    ollama_model: str = "llama3.2:3b"

    # OpenAI
    openai_api_key: str = "not-set"
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str = ""
    postgres_db: str = "ai_assistant"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str = ""

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str = ""

    # State Management
    state_pruning_enabled: bool = True
    state_max_messages: int = 20
    state_ttl_seconds: int = 86400  # 24 hours

    # n8n
    n8n_base_url: str = "http://n8n:5678"
    n8n_webhook_path: str = "/webhook"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # Logging
    log_level: str = "INFO"

    @property
    def postgres_url(self) -> str:
        """Get PostgreSQL connection URL."""
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def redis_url(self) -> str:
        """Get Redis connection URL."""
        if self.redis_password:
            return f"redis://:{self.redis_password}@{self.redis_host}:{self.redis_port}/{self.redis_db}"
        return f"redis://{self.redis_host}:{self.redis_port}/{self.redis_db}"

    @property
    def qdrant_url(self) -> str:
        """Get Qdrant URL."""
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


# Global settings instance
settings = Settings()
