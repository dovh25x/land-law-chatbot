from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    llm_provider: Literal['groq'] = 'groq'
    groq_api_key: SecretStr = SecretStr('')
    groq_model: Literal['openai/gpt-oss-120b','openai/gpt-oss-20b'] = 'openai/gpt-oss-120b'
    embedding_model: str = "multilingual-e5-small-onnx-q8-window-v1"
    embedding_provider: Literal['local_onnx'] = 'local_onnx'
    embedding_dimensions: int = 384
    embedding_concurrency: int = Field(default=2, ge=1, le=8)
    local_embedding_model_dir: Path = Path('models/e5')
    database_url: SecretStr = SecretStr("")
    admin_database_url: SecretStr = SecretStr("")
    backup_encryption_key: SecretStr = SecretStr("")
    sqlite_path: str = "data/local.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ip_hash_secret: SecretStr = SecretStr("")
    trust_proxy_headers: bool = False
    max_concurrent_requests: int = Field(default=2, ge=1, le=2)
    turn_timeout_seconds: int = Field(default=90, ge=1, le=90)
    session_retention_days: int = Field(default=7, ge=1, le=7)
    ingress_secret: SecretStr = SecretStr('')
    turnstile_secret_key: SecretStr = SecretStr('')
    session_challenge_mode: Literal['turnstile', 'disabled'] = 'turnstile'
    public_hostname: str = 'hanoi-land-law.pages.dev'
    public_daily_llm_limit: int = Field(default=100, ge=1)
    public_daily_token_limit: int = Field(default=100000, ge=1)
    public_daily_ip_chat_limit: int = Field(default=30, ge=1, le=1000)
    generation_enabled: bool = True
    execution_mode: Literal['agentic', 'simple_rag', 'agentic_rag'] = 'agentic'
    source_lookup_only: bool = False
    allow_stale_generation: bool = False
    db_statement_timeout_ms: int = Field(default=8000, ge=100, le=15000)
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")

    @model_validator(mode="after")
    def production_requirements(self):
        from .local_embedding import MODEL
        if self.source_lookup_only and self.generation_enabled:
            raise ValueError('SOURCE_LOOKUP_ONLY requires GENERATION_ENABLED=false')
        if self.embedding_model != MODEL['name'] or self.embedding_dimensions != MODEL['dimensions']:
            raise ValueError('Local embedding contract requires pinned E5 ONNX Q8 with 384 dimensions')
        if self.app_env == "production":
            if not self.database_url.get_secret_value():
                raise ValueError("Production requires PostgreSQL DATABASE_URL")
            if "sslmode=require" not in self.database_url.get_secret_value():
                raise ValueError("Production DATABASE_URL must require TLS")
            if len(self.ip_hash_secret.get_secret_value()) < 32:
                raise ValueError("Production requires a stable IP_HASH_SECRET of at least 32 characters")
            if (self.session_challenge_mode == "turnstile"
                    and not self.turnstile_secret_key.get_secret_value()):
                raise ValueError("Production challenge mode requires TURNSTILE_SECRET_KEY")
            if any("localhost" in x or "*" in x for x in self.origins):
                raise ValueError("Production CORS_ORIGINS must name deployed frontend origins")
        return self

    @property
    def generation_model(self):
        return self.groq_model

    @property
    def origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]

    def for_operator(self):
        return self.model_copy(update={"database_url": self.admin_database_url}) if self.admin_database_url.get_secret_value() else self


@lru_cache
def get_settings() -> Settings:
    return Settings()
