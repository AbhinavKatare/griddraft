"""Parquet data store and cache manager."""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class DataStore:
    """Manages cached Parquet datasets and metadata."""

    def __init__(self, cache_dir: Optional[Path] = None) -> None:
        self.cache_dir = cache_dir or settings.cache_dir
        self._fuelhh_df: Optional[pd.DataFrame] = None
        self._windfor_df: Optional[pd.DataFrame] = None
        self._metadata: Optional[Dict[str, Any]] = None

    @property
    def fuelhh_path(self) -> Path:
        return self.cache_dir / "fuelhh_wind_jan2026.parquet"

    @property
    def windfor_path(self) -> Path:
        return self.cache_dir / "windfor_jan2026.parquet"

    @property
    def metadata_path(self) -> Path:
        return self.cache_dir / "metadata.json"

    def is_cached(self) -> bool:
        """Check if both Parquet cache files exist."""
        return self.fuelhh_path.exists() and self.windfor_path.exists()

    def load_data(self, force_reload: bool = False) -> None:
        """Load Parquet files into memory."""
        if not force_reload and self._fuelhh_df is not None and self._windfor_df is not None:
            return

        if not self.is_cached():
            logger.warning("Parquet cache files not found in %s", self.cache_dir)
            return

        logger.info("Loading Parquet cache from %s", self.cache_dir)
        self._fuelhh_df = pd.read_parquet(self.fuelhh_path, engine="pyarrow")
        self._windfor_df = pd.read_parquet(self.windfor_path, engine="pyarrow")

        # Ensure UTC datetime types
        if not pd.api.types.is_datetime64_any_dtype(self._fuelhh_df["startTime"]):
            self._fuelhh_df["startTime"] = pd.to_datetime(self._fuelhh_df["startTime"], utc=True)
        if not pd.api.types.is_datetime64_any_dtype(self._windfor_df["startTime"]):
            self._windfor_df["startTime"] = pd.to_datetime(self._windfor_df["startTime"], utc=True)
        if not pd.api.types.is_datetime64_any_dtype(self._windfor_df["publishTime"]):
            self._windfor_df["publishTime"] = pd.to_datetime(self._windfor_df["publishTime"], utc=True)

        if self.metadata_path.exists():
            try:
                with open(self.metadata_path, "r", encoding="utf-8") as f:
                    self._metadata = json.load(f)
            except Exception as exc:
                logger.error("Failed to load metadata.json: %s", exc)

        logger.info(
            "Parquet cache loaded: %d FUELHH rows, %d WINDFOR rows",
            len(self._fuelhh_df),
            len(self._windfor_df),
        )

    def get_fuelhh(self) -> pd.DataFrame:
        if self._fuelhh_df is None:
            self.load_data()
        if self._fuelhh_df is None:
            return pd.DataFrame()
        return self._fuelhh_df

    def get_windfor(self) -> pd.DataFrame:
        if self._windfor_df is None:
            self.load_data()
        if self._windfor_df is None:
            return pd.DataFrame()
        return self._windfor_df

    def get_metadata(self) -> Dict[str, Any]:
        if self._metadata is None and self.metadata_path.exists():
            with open(self.metadata_path, "r", encoding="utf-8") as f:
                self._metadata = json.load(f)
        return self._metadata or {}


# Global instance
data_store = DataStore()
