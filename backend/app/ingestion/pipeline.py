"""Data ingestion pipeline to fetch, validate, deduplicate, and atomically write canonical Parquet datasets."""

import asyncio
from datetime import date, datetime, timedelta, timezone
import json
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Optional
import pandas as pd

from app.config import settings
from app.ingestion.elexon_client import ElexonClient
from app.models.canonical import (
    normalise_actuals_dataframe,
    normalise_forecasts_dataframe,
)


def clean_fuelhh_dataframe(
    raw_records: list[dict[str, Any]] | pd.DataFrame,
) -> pd.DataFrame:
    """Validate and clean raw FUELHH records."""
    return normalise_actuals_dataframe(raw_records)


def clean_windfor_dataframe(
    raw_records: list[dict[str, Any]] | pd.DataFrame,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> pd.DataFrame:
    """Validate, clean, and filter raw WINDFOR records to delivery date bounds."""
    df = normalise_forecasts_dataframe(raw_records)
    if df.empty:
        return df

    s_date = start_date or date(2026, 1, 1)
    e_date = end_date or date(2026, 1, 31)
    start_bound = pd.Timestamp(datetime(s_date.year, s_date.month, s_date.day, 0, 0, 0, tzinfo=timezone.utc))
    end_bound = pd.Timestamp(datetime(e_date.year, e_date.month, e_date.day, 23, 30, 0, tzinfo=timezone.utc))

    return (
        df[(df["startTime"] >= start_bound) & (df["startTime"] <= end_bound)]
        .sort_values(by=["startTime", "publishTime"])
        .reset_index(drop=True)
    )

logger = logging.getLogger("app.ingestion.pipeline")


def atomic_write_parquet(df: pd.DataFrame, dest_path: Path) -> None:
    """
    Atomically write a DataFrame to Parquet using a temporary file and atomic swap.
    Prevents corrupt files if the process is killed mid-write.
    """
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_name(f".{dest_path.name}.tmp_{int(time.time() * 1000)}")

    try:
        df.to_parquet(
            temp_path,
            engine="pyarrow",
            compression="snappy",
            index=False,
        )
        # Atomic rename/replace on POSIX & Windows (Python 3.3+)
        os.replace(temp_path, dest_path)
    except Exception as exc:
        if temp_path.exists():
            temp_path.unlink()
        logger.error("Failed to write Parquet atomically to %s: %s", dest_path, exc)
        raise exc


async def ingest_dataset_range(
    start_date: date,
    end_date: date,
    cache_dir: Optional[Path] = None,
    client: Optional[ElexonClient] = None,
    concurrency_limit: int = 3,
) -> Dict[str, Any]:
    """
    Fetch, normalize, validate, deduplicate, and write actuals and forecasts for a specified date range.

    Idempotent:
    - Multiple executions over the same date range produce identical output files.
    - Writes are atomic and cannot partially corrupt existing files.

    Forecast Horizon Buffer:
    - For delivery in [start_date, end_date], WINDFOR is ingested starting from
      (start_date - 4 days) at 00:00:00 UTC to capture forecasts published up to
      the maximum 66.5h horizon prior to Day-1 09:00 cutoff.
    """
    t0 = time.perf_counter()
    target_cache_dir = cache_dir or settings.cache_dir
    target_cache_dir.mkdir(parents=True, exist_ok=True)

    elexon = client or ElexonClient(max_concurrency=concurrency_limit)

    logger.info(
        "=== Starting Elexon BMRS Ingestion [%s to %s] (Output: %s) ===",
        start_date,
        end_date,
        target_cache_dir,
    )

    # --------------------------------------------------------------------------
    # 1. Fetch & Normalise FUELHH (Actuals)
    # --------------------------------------------------------------------------
    logger.info("[1/2] Ingesting FUELHH actual wind generation...")
    t_fuel_start = time.perf_counter()
    raw_fuelhh = await elexon.fetch_fuelhh_wind(
        settlement_date_from=start_date,
        settlement_date_to=end_date,
    )
    df_raw_fuelhh = pd.DataFrame(raw_fuelhh)
    df_clean_fuelhh = normalise_actuals_dataframe(df_raw_fuelhh)

    # Verify coverage bounds
    start_bound_dt = pd.Timestamp(datetime(start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc))
    end_bound_dt = pd.Timestamp(datetime(end_date.year, end_date.month, end_date.day, 23, 30, 0, tzinfo=timezone.utc))
    df_clean_fuelhh = df_clean_fuelhh[
        (df_clean_fuelhh["startTime"] >= start_bound_dt) & (df_clean_fuelhh["startTime"] <= end_bound_dt)
    ].reset_index(drop=True)

    fuelhh_filename = "fuelhh_wind_jan2026.parquet" if (start_date == date(2026, 1, 1) and end_date == date(2026, 1, 31)) else f"fuelhh_wind_{start_date}_{end_date}.parquet"
    fuelhh_dest = target_cache_dir / fuelhh_filename
    atomic_write_parquet(df_clean_fuelhh, fuelhh_dest)
    t_fuel_duration = time.perf_counter() - t_fuel_start

    logger.info(
        "[1/2] FUELHH complete: %d rows written to %s in %.2fs.",
        len(df_clean_fuelhh),
        fuelhh_dest.name,
        t_fuel_duration,
    )

    # --------------------------------------------------------------------------
    # 2. Fetch & Normalise WINDFOR (Forecasts)
    # --------------------------------------------------------------------------
    # For day-ahead decision cutoff evaluation, we need forecasts published up to
    # 66.5 hours (~3 days) prior to start_date.
    forecast_pub_start = datetime(
        start_date.year, start_date.month, start_date.day, 0, 0, 0, tzinfo=timezone.utc
    ) - timedelta(days=4)
    forecast_pub_end = datetime(
        end_date.year, end_date.month, end_date.day, 23, 59, 59, tzinfo=timezone.utc
    ) + timedelta(days=1)

    logger.info(
        "[2/2] Ingesting WINDFOR forecasts. Effective publish fetch window: %s to %s (includes 4-day lookback buffer for max 66.5h horizon)...",
        forecast_pub_start.strftime("%Y-%m-%dT%H:%M:%SZ"),
        forecast_pub_end.strftime("%Y-%m-%dT%H:%M:%SZ"),
    )
    t_wind_start = time.perf_counter()
    raw_windfor = await elexon.fetch_windfor(
        publish_datetime_from=forecast_pub_start,
        publish_datetime_to=forecast_pub_end,
    )
    df_raw_windfor = pd.DataFrame(raw_windfor)
    df_clean_windfor = normalise_forecasts_dataframe(df_raw_windfor)

    # Filter delivery startTime to requested date range
    df_clean_windfor = df_clean_windfor[
        (df_clean_windfor["startTime"] >= start_bound_dt) & (df_clean_windfor["startTime"] <= end_bound_dt)
    ].reset_index(drop=True)

    windfor_filename = "windfor_jan2026.parquet" if (start_date == date(2026, 1, 1) and end_date == date(2026, 1, 31)) else f"windfor_{start_date}_{end_date}.parquet"
    windfor_dest = target_cache_dir / windfor_filename
    atomic_write_parquet(df_clean_windfor, windfor_dest)
    t_wind_duration = time.perf_counter() - t_wind_start

    logger.info(
        "[2/2] WINDFOR complete: %d rows written to %s in %.2fs.",
        len(df_clean_windfor),
        windfor_dest.name,
        t_wind_duration,
    )

    # --------------------------------------------------------------------------
    # 3. Write Metadata
    # --------------------------------------------------------------------------
    total_elapsed = time.perf_counter() - t0
    metadata: Dict[str, Any] = {
        "dataset_scope": f"UK Wind Forecast and Generation ({start_date} to {end_date})",
        "start_date": str(start_date),
        "end_date": str(end_date),
        "last_updated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Elexon Insights Solution (BMRS)",
        "total_elapsed_seconds": round(total_elapsed, 2),
        "fuelhh": {
            "file": fuelhh_dest.name,
            "record_count": len(df_clean_fuelhh),
            "min_start_time": df_clean_fuelhh["startTime"].min().isoformat() if not df_clean_fuelhh.empty else None,
            "max_start_time": df_clean_fuelhh["startTime"].max().isoformat() if not df_clean_fuelhh.empty else None,
            "min_generation_mw": float(df_clean_fuelhh["generation"].min()) if not df_clean_fuelhh.empty else None,
            "max_generation_mw": float(df_clean_fuelhh["generation"].max()) if not df_clean_fuelhh.empty else None,
            "mean_generation_mw": float(df_clean_fuelhh["generation"].mean()) if not df_clean_fuelhh.empty else None,
        },
        "windfor": {
            "file": windfor_dest.name,
            "record_count": len(df_clean_windfor),
            "unique_delivery_slots": int(df_clean_windfor["startTime"].nunique()) if not df_clean_windfor.empty else 0,
            "min_publish_time": df_clean_windfor["publishTime"].min().isoformat() if not df_clean_windfor.empty else None,
            "max_publish_time": df_clean_windfor["publishTime"].max().isoformat() if not df_clean_windfor.empty else None,
            "min_start_time": df_clean_windfor["startTime"].min().isoformat() if not df_clean_windfor.empty else None,
            "max_start_time": df_clean_windfor["startTime"].max().isoformat() if not df_clean_windfor.empty else None,
        },
    }

    meta_path = target_cache_dir / "metadata.json"
    temp_meta = meta_path.with_name(f".metadata.json.tmp_{int(time.time() * 1000)}")
    with open(temp_meta, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2)
    os.replace(temp_meta, meta_path)

    logger.info("Metadata successfully updated at %s (Total time: %.2fs)", meta_path, total_elapsed)
    return metadata


async def run_january_2026_ingestion(client: Optional[ElexonClient] = None) -> Dict[str, Any]:
    """Backward-compatible entry point for January 2026 default scope."""
    return await ingest_dataset_range(
        start_date=date(2026, 1, 1),
        end_date=date(2026, 1, 31),
        client=client,
    )
