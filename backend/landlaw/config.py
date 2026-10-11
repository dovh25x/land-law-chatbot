from functools import lru_cache
from pathlib import Path

from pydantic import Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    app_env: str = "development"
    gemini_api_key: SecretStr = SecretStr("")
    gemini_model: str = "gemini-3.5-flash-lite"
    embedding_model: str = "gemini-embedding-2"
    embedding_dimensions: int = 768
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
    global_daily_llm_limit: int = Field(default=100, ge=1)
    global_daily_embedding_limit: int = Field(default=500, ge=1)
    max_concurrent_requests: int = Field(default=2, ge=1, le=2)
    turn_timeout_seconds: int = Field(default=90, ge=1, le=90)
    session_retention_days: int = Field(default=7, ge=1, le=7)
    data_dir: Path = Path("data")
    reports_dir: Path = Path("reports")

    @model_validator(mode="after")
    def production_requirements(self):
        if self.embedding_dimensions != 768:
            raise ValueError("This schema uses 768 dimensions; migrate/reindex before changing it")
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
    def origins(self) -> list[str]:
        return [x.strip().rstrip("/") for x in self.cors_origins.split(",") if x.strip()]

    def for_operator(self):
        return self.model_copy(update={"database_url": self.admin_database_url}) if self.admin_database_url.get_secret_value() else self


@lru_cache
def get_settings() -> Settings:
    return Settings()
