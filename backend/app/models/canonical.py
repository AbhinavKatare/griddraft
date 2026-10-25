"""Canonical schemas, Pydantic models, and pandas/pyarrow dtype maps for actuals and forecasts.

All timestamps are strictly UTC-aware.
All generation values are floats in Megawatts (MW), strictly non-negative.
"""

from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field, field_validator
import pyarrow as pa


# ==============================================================================
# Canonical Column Names
# ==============================================================================

ACTUALS_CANONICAL_COLUMNS = [
    "dataset",
    "publishTime",
    "startTime",
    "settlementDate",
    "settlementPeriod",
    "fuelType",
    "generation",
]

FORECASTS_CANONICAL_COLUMNS = [
    "dataset",
    "publishTime",
    "startTime",
    "generation",
]


# ==============================================================================
# Pandas / NumPy Dtype Maps
# ==============================================================================

ACTUALS_PANDAS_DTYPES: Dict[str, str] = {
    "dataset": "string",
    "settlementDate": "string",
    "settlementPeriod": "int64",
    "fuelType": "string",
    "generation": "float64",
}

FORECASTS_PANDAS_DTYPES: Dict[str, str] = {
    "dataset": "string",
    "generation": "float64",
}

# Timestamp columns that MUST be stored as UTC datetime64[ns, UTC]
DATETIME_UTC_COLUMNS = ["startTime", "publishTime"]


# ==============================================================================
# PyArrow Table Schemas for Zero-Copy Parquet Serialization
# ==============================================================================

ACTUALS_PYARROW_SCHEMA = pa.schema([
    ("dataset", pa.string()),
    ("publishTime", pa.timestamp("us", tz="UTC")),
    ("startTime", pa.timestamp("us", tz="UTC")),
    ("settlementDate", pa.string()),
    ("settlementPeriod", pa.int64()),
    ("fuelType", pa.string()),
    ("generation", pa.float64()),
])

FORECASTS_PYARROW_SCHEMA = pa.schema([
    ("dataset", pa.string()),
    ("publishTime", pa.timestamp("us", tz="UTC")),
    ("startTime", pa.timestamp("us", tz="UTC")),
    ("generation", pa.float64()),
])


# ==============================================================================
# Pydantic Canonical Models
# ==============================================================================

class CanonicalActualRow(BaseModel):
    """Canonical representation of a single FUELHH wind actuals record."""

    dataset: str = Field(default="FUELHH", description="Dataset identifier")
    publishTime: datetime = Field(..., description="Timestamp when record was published (UTC)")
    startTime: datetime = Field(..., description="Delivery start timestamp for half-hour (UTC)")
    settlementDate: str = Field(..., description="Settlement date (YYYY-MM-DD)")
    settlementPeriod: int = Field(..., ge=1, le=50, description="Settlement period (1 to 48/50)")
    fuelType: str = Field(default="WIND", description="Generation fuel type (must be WIND)")
    generation: float = Field(..., ge=0.0, description="Actual metered generation in MW (non-negative)")

    @field_validator("publishTime", "startTime")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Enforce UTC timezone awareness."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)

    @field_validator("fuelType")
    @classmethod
    def validate_wind(cls, v: str) -> str:
        """Ensure fuelType is WIND."""
        if v.strip().upper() != "WIND":
            raise ValueError(f"fuelType must be 'WIND', got: {v}")
        return "WIND"

    @field_validator("settlementDate")
    @classmethod
    def validate_date_format(cls, v: str) -> str:
        """Validate settlementDate follows YYYY-MM-DD format."""
        try:
            datetime.strptime(v.strip(), "%Y-%m-%d")
        except ValueError:
            raise ValueError(f"settlementDate must be 'YYYY-MM-DD', got: {v}")
        return v.strip()


class CanonicalForecastRow(BaseModel):
    """Canonical representation of a single WINDFOR forecast record."""

    dataset: str = Field(default="WINDFOR", description="Dataset identifier")
    publishTime: datetime = Field(..., description="Timestamp when forecast was published (UTC)")
    startTime: datetime = Field(..., description="Target delivery start timestamp (UTC)")
    generation: float = Field(..., ge=0.0, description="Forecast wind generation in MW (non-negative)")

    @field_validator("publishTime", "startTime")
    @classmethod
    def ensure_utc(cls, v: datetime) -> datetime:
        """Enforce UTC timezone awareness."""
        if v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)
        return v.astimezone(timezone.utc)


# ==============================================================================
# Normalisation & Vectorized Validation Helpers
# ==============================================================================

def normalise_actuals_dataframe(df: pd.DataFrame | List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalise and strictly validate an actuals DataFrame against canonical schema:
    1. Filter strictly for WIND fuelType.
    2. Convert timestamps to UTC datetime64[ns, UTC].
    3. Coerce generation to float64 and drop any negative values (< 0 MW).
    4. Ensure settlementPeriod is integer in [1, 50].
    5. Deduplicate by startTime keeping the latest publishTime.
    6. Select and order canonical columns.
    """
    if isinstance(df, list):
        df = pd.DataFrame(df)

    if df.empty:
        return pd.DataFrame(columns=ACTUALS_CANONICAL_COLUMNS)

    clean_df = df.copy()

    # Normalize column names if PascalCase / camelCase
    col_map = {
        "start_time": "startTime",
        "publish_time": "publishTime",
        "settlement_date": "settlementDate",
        "settlement_period": "settlementPeriod",
        "fuel_type": "fuelType",
    }
    clean_df = clean_df.rename(columns=col_map)

    if "fuelType" in clean_df.columns:
        clean_df = clean_df[clean_df["fuelType"].astype(str).str.upper() == "WIND"].copy()
    else:
        clean_df["fuelType"] = "WIND"

    clean_df["dataset"] = "FUELHH"

    # Datetime conversions to UTC
    clean_df["startTime"] = pd.to_datetime(clean_df["startTime"], utc=True)
    clean_df["publishTime"] = pd.to_datetime(clean_df["publishTime"], utc=True)

    # Generation numeric conversion (MW)
    clean_df["generation"] = pd.to_numeric(clean_df["generation"], errors="coerce")
    clean_df = clean_df.dropna(subset=["startTime", "publishTime", "generation"])

    # Non-negative validation (MW >= 0)
    clean_df = clean_df[clean_df["generation"] >= 0.0]

    # Settlement period validation
    clean_df["settlementPeriod"] = pd.to_numeric(clean_df["settlementPeriod"], errors="coerce").fillna(1).astype(int)
    clean_df = clean_df[(clean_df["settlementPeriod"] >= 1) & (clean_df["settlementPeriod"] <= 50)]

    # Settlement date formatting
    clean_df["settlementDate"] = pd.to_datetime(clean_df["settlementDate"]).dt.strftime("%Y-%m-%d")

    # Deduplicate: Unique primary key is startTime; retain latest publishTime
    clean_df = clean_df.sort_values(by=["startTime", "publishTime"]).drop_duplicates(
        subset=["startTime"], keep="last"
    )

    clean_df = clean_df.sort_values(by="startTime").reset_index(drop=True)
    return clean_df[ACTUALS_CANONICAL_COLUMNS]


def normalise_forecasts_dataframe(df: pd.DataFrame | List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Normalise and strictly validate a forecasts DataFrame against canonical schema:
    1. Convert timestamps to UTC datetime64[ns, UTC].
    2. Coerce generation to float64 and drop any negative values (< 0 MW).
    3. Deduplicate composite key (startTime, publishTime), keeping the latest.
    4. Select and order canonical columns.
    """
    if isinstance(df, list):
        df = pd.DataFrame(df)

    if df.empty:
        return pd.DataFrame(columns=FORECASTS_CANONICAL_COLUMNS)

    clean_df = df.copy()

    col_map = {
        "start_time": "startTime",
        "publish_time": "publishTime",
    }
    clean_df = clean_df.rename(columns=col_map)
    clean_df["dataset"] = "WINDFOR"

    clean_df["startTime"] = pd.to_datetime(clean_df["startTime"], utc=True)
    clean_df["publishTime"] = pd.to_datetime(clean_df["publishTime"], utc=True)

    clean_df["generation"] = pd.to_numeric(clean_df["generation"], errors="coerce")
    clean_df = clean_df.dropna(subset=["startTime", "publishTime", "generation"])

    # Non-negative validation
    clean_df = clean_df[clean_df["generation"] >= 0.0]

    # Deduplicate: Unique composite key is (startTime, publishTime)
    clean_df = clean_df.drop_duplicates(subset=["startTime", "publishTime"], keep="last")

    clean_df = clean_df.sort_values(by=["startTime", "publishTime"]).reset_index(drop=True)
    return clean_df[FORECASTS_CANONICAL_COLUMNS]
