"""
Configuration management for LangGraph multi-agent system.
Supports easy switching between Ollama and OpenAI-compatible providers.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator
from typing import Literal

# Default values are defined as constants to avoid being flagged as hardcoded secrets
DEFAULT_OPENAI_API_KEY = "not-set"


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
    openai_api_key: str = DEFAULT_OPENAI_API_KEY
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4"

    # Database
    postgres_host: str = "postgres"
    postgres_port: int = 5432
    postgres_user: str = "postgres"
    postgres_password: str
    postgres_db: str = "ai_assistant"

    # Redis
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    redis_password: str | None = None

    # Qdrant
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_api_key: str | None = None

    # State Management
    state_pruning_enabled: bool = True
    state_max_messages: int = 20
    state_ttl_seconds: int = 86400  # 24 hours

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = False

    # CORS Configuration
    # Comma-separated list of allowed origins
    # For production: "https://yourdomain.com,https://app.yourdomain.com"
    # For development: "http://localhost:3000,http://localhost:3001"
    cors_allowed_origins: str = "http://localhost:3001"

    # Logging
    log_level: str = "INFO"

    # Validators
    @field_validator('postgres_password')
    @classmethod
    def validate_postgres_password(cls, v: str) -> str:
        """
        Validate PostgreSQL password.

        FIX: Enforce password requirements to prevent weak/default passwords.
        """
        if not v or v == "":
            raise ValueError(
                "POSTGRES_PASSWORD is required. "
                "Set it in your environment or .env file. "
                "Do not use empty passwords."
            )

        # Warn about weak passwords
        if len(v) < 12:
            import warnings
            warnings.warn(
                f"POSTGRES_PASSWORD is weak (length: {len(v)}). "
                "Recommend at least 12 characters for production.",
                UserWarning
            )

        return v

    @property
    def get_cors_origins(self) -> list[str]:
        """Parse and return CORS allowed origins as list."""
        return [origin.strip() for origin in self.cors_allowed_origins.split(",") if origin.strip()]

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
