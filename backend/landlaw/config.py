from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    llm_provider: Literal['gemini', 'cloudflare', 'groq', 'nvidia'] = 'gemini'
    nvidia_api_key: SecretStr = SecretStr('')
    nvidia_model: Literal['nvidia/nemotron-3-super-120b-a12b','nvidia/nemotron-3-ultra-550b-a55b'] = 'nvidia/nemotron-3-super-120b-a12b'
    groq_api_key: SecretStr = SecretStr('')
    groq_model: Literal['openai/gpt-oss-120b','openai/gpt-oss-20b','qwen/qwen3.8-27b'] = 'openai/gpt-oss-120b'
    cloudflare_llm_model: Literal['@cf/qwen/qwen3-30b-a3b-fp8'] = '@cf/qwen/qwen3-30b-a3b-fp8'
    embedding_model: str = "gemini-embedding-2"
    embedding_provider: Literal['gemini','cloudflare','local_onnx'] = 'gemini'
    embedding_dimensions: int = 768
    embedding_concurrency: int = Field(default=2, ge=1, le=8)
    local_embedding_model_dir: Path = Path('models/e5')
    cloudflare_account_id: str = ''
    cloudflare_ai_api_token: SecretStr = SecretStr('')
    database_url: SecretStr = SecretStr("")
    admin_database_url: SecretStr = SecretStr("")
    backup_encryption_key: SecretStr = SecretStr("")
    sqlite_path: str = "data/local.db"
    supabase_url: str = ""
    supabase_service_role_key: SecretStr = SecretStr("")
    supabase_bucket: str = "legal-corpus"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    ip_hash_secret: SecretStr = SecretStr("")
    trust_proxy_headers: bool = False
    max_concurrent_requests: int = Field(default=2, ge=1, le=2)
    turn_timeout_seconds: int = Field(default=90, ge=1, le=90)
    session_retention_days: int = Field(default=7, ge=1, le=7)
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")

    @model_validator(mode="after")
    def production_requirements(self):
        if self.embedding_provider=='local_onnx':
            from .local_embedding import MODEL
            if self.embedding_model != MODEL['name'] or self.embedding_dimensions != MODEL['dimensions']:
                raise ValueError('Local embedding contract requires pinned E5 ONNX Q8 with 384 dimensions')
        elif self.embedding_provider=='cloudflare':
            if self.embedding_model!='@cf/baai/bge-m3' or self.embedding_dimensions!=1024:
                raise ValueError('Cloudflare embedding contract requires BGE-M3 with 1024 dimensions')
        elif self.embedding_dimensions != 768 or self.embedding_model not in {'gemini-embedding-2','gemini-embedding-001'}:
            raise ValueError('Gemini embedding contract requires an allowed model with 768 dimensions')
        if self.app_env == "production":
            if not self.database_url.get_secret_value():
                raise ValueError("Production requires PostgreSQL DATABASE_URL")
            if "sslmode=require" not in self.database_url.get_secret_value():
                raise ValueError("Production DATABASE_URL must require TLS")
            if len(self.ip_hash_secret.get_secret_value()) < 32:
                raise ValueError("Production requires a stable IP_HASH_SECRET of at least 32 characters")
            if any("localhost" in x or "*" in x for x in self.origins):
                raise ValueError("Production CORS_ORIGINS must name deployed frontend origins")
        return self

    @property
    def generation_model(self):
        if self.llm_provider == 'nvidia':
            return self.nvidia_model
        if self.llm_provider == 'groq':
            return self.groq_model
        return self.cloudflare_llm_model if self.llm_provider == 'cloudflare' else self.gemini_model

    @property
    def origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]

    def for_operator(self):
        return self.model_copy(update={"database_url": self.admin_database_url}) if self.admin_database_url.get_secret_value() else self


@lru_cache
def get_settings() -> Settings:
    return Settings()
