"""Application configuration module with environment overrides."""

import os
from pathlib import Path
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings for UK Wind Forecast Monitoring service."""

    app_name: str = "UK Wind Forecast Monitoring"
    app_version: str = "1.0.0"
    debug: bool = False

    # Elexon BMRS API
    elexon_base_url: str = "https://data.elexon.co.uk/bmrs/api/v1"
    elexon_request_timeout: float = 30.0
    elexon_max_retries: int = 3
    elexon_retry_backoff: float = 1.0

    # Cache & Storage
    base_dir: Path = Path(__file__).resolve().parent.parent
    cache_dir: Path = (
        Path(os.environ["WIND_APP_CACHE_DIR"])
        if "WIND_APP_CACHE_DIR" in os.environ
        else (
            Path(os.environ["CACHE_DIR"])
            if "CACHE_DIR" in os.environ
            else (
                Path(__file__).resolve().parent.parent.parent / "data" / "cache"
                if (Path(__file__).resolve().parent.parent.parent / "data" / "cache").exists()
                else Path(__file__).resolve().parent.parent / "data" / "cache"
            )
        )
    )

    # CORS Settings
    cors_origins: list[str] = ["*"]

    # Render Anti-Sleep Keep-Alive
    enable_keep_alive: bool = True
    keep_alive_interval_minutes: int = 14
    keep_alive_url: Optional[str] = "https://griddraft.onrender.com"

    # Default Day-Ahead Trading Parameters
    default_decision_time: str = "09:00"  # UK time (= GMT in January) on D-1
    target_year: int = 2026
    target_month: int = 1

    model_config = SettingsConfigDict(
        env_prefix="WIND_APP_",
        env_file=".env",
        extra="ignore",
    )


settings = Settings()
try:
    settings.cache_dir.mkdir(parents=True, exist_ok=True)
except OSError:
    # Read-only filesystem in serverless environments (e.g. Vercel)
    pass
