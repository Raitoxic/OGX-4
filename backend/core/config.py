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


class Settings:
    """Environment-driven configuration for VYRO-X."""

    def __init__(self) -> None:
        default_sqlite = f"sqlite:///{(BACKEND_DIR / 'vyrox.db').as_posix()}"
        raw_db_url = os.getenv("DATABASE_URL", "").strip()
        if not raw_db_url:
            self.database_url = default_sqlite
        elif raw_db_url.startswith("sqlite:///./"):
            rel_path = raw_db_url.replace("sqlite:///./", "", 1)
            self.database_url = f"sqlite:///{(BACKEND_DIR / rel_path).as_posix()}"
        else:
            self.database_url = raw_db_url

        self.jwt_secret_key = os.getenv("JWT_SECRET_KEY", "vyrox-dev-secret-change-in-production")
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

    @property
    def active_provider_info(self) -> Tuple[str, str]:
        """Returns (mode, provider_label). Never disguises demo mode as live AI."""
        if self.openai_api_key:
            return ("live", f"openai:{self.openai_model}")
        if self.gemini_api_key:
            return ("live", f"gemini:{self.gemini_model}")
        return ("demo", "vyrox-deterministic-v1")


settings = Settings()
