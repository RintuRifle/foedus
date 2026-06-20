"""
Foedus — Application Configuration
Reads all settings from environment variables via Pydantic Settings.
"""

from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """
    Central configuration for the entire backend.
    All values come from .env file or environment variables.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── App ───────────────────────────────────────────────────
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_NAME: str = "Foedus"
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:3001"

    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    # ── Database ──────────────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://foedus:foedus_dev_2024@localhost:5432/foedus_db"
    DATABASE_URL_SYNC: str = "postgresql://foedus:foedus_dev_2024@localhost:5432/foedus_db"

    # ── Redis ─────────────────────────────────────────────────
    REDIS_URL: str = "redis://localhost:6379/0"

    # ── Qdrant ────────────────────────────────────────────────
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_COLLECTION: str = "foedus_tenders"

    # ── JWT Auth ──────────────────────────────────────────────
    JWT_SECRET: str = "change-this-to-a-random-64-char-string-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # ── LLM APIs ─────────────────────────────────────────────
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # ── Supabase ──────────────────────────────────────────────
    SUPABASE_URL: str = ""
    SUPABASE_KEY: str = ""
    SUPABASE_STORAGE_BUCKET: str = "foedus-docs"

    # ── Razorpay ──────────────────────────────────────────────
    RAZORPAY_KEY_ID: str = ""
    RAZORPAY_KEY_SECRET: str = ""
    RAZORPAY_WEBHOOK_SECRET: str = ""

    # ── Email ─────────────────────────────────────────────────
    RESEND_API_KEY: str = ""

    # ── LangSmith ─────────────────────────────────────────────
    LANGCHAIN_TRACING_V2: bool = False
    LANGCHAIN_API_KEY: str = ""
    LANGCHAIN_PROJECT: str = "foedus"

    # ── Sentry ────────────────────────────────────────────────
    SENTRY_DSN: str = ""

    # ── Scraper ───────────────────────────────────────────────
    SCRAPER_CRON_HOUR: int = 6
    SCRAPER_CRON_MINUTE: int = 0
    SCRAPER_MAX_PAGES: int = 5
    SCRAPER_PDF_DIR: str = "./data/pdfs"

# Singleton — import this everywhere
settings = Settings()
