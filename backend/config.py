"""
Backend Configuration
=====================
Central settings loaded from environment variables or .env file.
Uses pydantic-settings for validation.
"""

from functools import lru_cache
from pathlib import Path
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings — override any value via environment variable."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # ── Application ──────────────────────────────────────────────────────────
    app_name: str = "QA Platform API"
    app_version: str = "2.0.0"
    debug: bool = False

    # ── Paths ─────────────────────────────────────────────────────────────────
    project_root: Path = Path(__file__).resolve().parents[1]
    data_dir: Path = Path(__file__).resolve().parents[1] / "data"
    output_dir: Path = Path(__file__).resolve().parents[1] / "output"
    database_url: str = "sqlite:///./database/qa_platform.db"

    # ── Auth (optional — set API_ACCESS_KEY to enable) ───────────────────────
    api_access_key: str = ""          # empty → auth disabled
    secret_key: str = "change-me-in-production"
    access_token_expire_minutes: int = 60 * 8  # 8 hours

    # ── CORS ──────────────────────────────────────────────────────────────────
    allowed_origins: List[str] = [
        "http://localhost",
        "http://localhost:8050",   # Dash dev server
        "http://localhost:8000",   # FastAPI dev server
        "http://127.0.0.1:8050",
        "http://127.0.0.1:8000",
    ]

    # ── Data sources ─────────────────────────────────────────────────────────
    @property
    def csv_paths(self) -> dict:
        return {
            "BAYSA": self.data_dir / "contratistas" / "BAYSA" / "ctrl_dosieres_BAYSA_normalizado.csv",
            "JAMAR": self.data_dir / "contratistas" / "JAMAR" / "ctrl_dosieres_JAMAR_normalizado.csv",
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
