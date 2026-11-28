from __future__ import annotations

import os
from pathlib import Path
from typing import List, Tuple

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parent.parent
PROJECT_ROOT = BACKEND_DIR.parent
ML_DIR = PROJECT_ROOT / "ml"

load_dotenv(PROJECT_ROOT / ".env")
load_dotenv(BACKEND_DIR / ".env")

DEFAULT_DEV_JWT_SECRET = "vyrox-dev-secret-change-in-production"


def normalize_database_url(raw_url: str, default_sqlite: str) -> str:
    url = raw_url.strip()
    if not url:
        return default_sqlite
    if url.startswith("postgres://"):
        return "postgresql+psycopg2://" + url[len("postgres://"):]
    if url.startswith("postgresql://") and "+psycopg2" not in url and "+asyncpg" not in url:
        return "postgresql+psycopg2://" + url[len("postgresql://"):]
    if url.startswith("sqlite:///./"):
        rel_path = url.replace("sqlite:///./", "", 1)
        return f"sqlite:///{(BACKEND_DIR / rel_path).as_posix()}"
    return url


class Settings:
    """Environment-driven configuration for VYRO-X with strict production safety guards."""

    def __init__(self) -> None:
        self.environment = os.getenv("ENVIRONMENT", "development").strip().lower()
        default_sqlite = f"sqlite:///{(BACKEND_DIR / 'vyrox.db').as_posix()}"
        raw_db_url = os.getenv("DATABASE_URL", "").strip()
        self.raw_database_url = raw_db_url
        self.database_url = normalize_database_url(raw_db_url, default_sqlite)

        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", DEFAULT_DEV_JWT_SECRET)
        self.jwt_algorithm = "HS256"
        self.access_token_expire_minutes = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "10080"))

        cors_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
        self.cors_origins: List[str] = [o.strip() for o in cors_raw.split(",") if o.strip()]

        self.auth_rate_limit_per_min = int(os.getenv("AUTH_RATE_LIMIT_PER_MIN", "60"))
        self.ml_retrain_rate_limit_per_min = int(os.getenv("ML_RETRAIN_RATE_LIMIT_PER_MIN", "6"))

        self.openai_api_key = os.getenv("OPENAI_API_KEY", "").strip()
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini").strip()
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1").strip().rstrip("/")

        self.gemini_api_key = os.getenv("GEMINI_API_KEY", "").strip()
        self.gemini_model = os.getenv("GEMINI_MODEL", "gemini-2.0-flash").strip()

        self.demo_step_stage_delay_sec = float(os.getenv("DEMO_STEP_STAGE_DELAY_SEC", "0.75"))
        self.llm_timeout_sec = float(os.getenv("LLM_TIMEOUT_SEC", "45.0"))

        # Research engine (OFF by default; per-task flag can enable it).
        self.research_enabled = os.getenv("RESEARCH_ENABLED", "false").strip().lower() in ("1", "true", "yes")
        self.research_providers = [
            p.strip().lower()
            for p in os.getenv("RESEARCH_PROVIDERS", "openalex,crossref,arxiv").split(",")
            if p.strip()
        ]
        self.research_max_sources = int(os.getenv("RESEARCH_MAX_SOURCES", "5"))
        self.research_timeout_sec = float(os.getenv("RESEARCH_TIMEOUT_SEC", "8.0"))
        self.research_max_bytes = int(os.getenv("RESEARCH_MAX_BYTES", "2000000"))
        self.research_per_provider_limit = int(os.getenv("RESEARCH_PER_PROVIDER_LIMIT", "5"))

    def validate_production_config(self) -> None:
        """
        Enforces strict production invariants:
        - Never silently fall back to SQLite in production.
        - Never allow default/short JWT secrets in production.
        """
        if self.environment != "production":
            return
        if not self.raw_database_url or self.database_url.startswith("sqlite"):
            raise RuntimeError(
                "ENVIRONMENT=production requires a PostgreSQL DATABASE_URL. "
                "Silent fallback to SQLite is disabled in production."
            )
        if not self.jwt_secret_key or self.jwt_secret_key == DEFAULT_DEV_JWT_SECRET or len(self.jwt_secret_key) < 32:
            raise RuntimeError(
                "ENVIRONMENT=production requires a strong JWT_SECRET_KEY (minimum 32 characters, not the dev default)."
            )

    @property
    def active_provider_info(self) -> Tuple[str, str]:
        """Returns (mode, provider_label). Never disguises demo mode as live AI."""
        if self.openai_api_key:
            return ("live", f"openai:{self.openai_model}")
        if self.gemini_api_key:
            return ("live", f"gemini:{self.gemini_model}")
        return ("demo", "vyrox-deterministic-v1")


settings = Settings()
