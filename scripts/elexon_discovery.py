"""Standalone discovery script to verify Elexon BMRS API endpoints, parameters, and schemas."""

from datetime import datetime, timezone
import json
import httpx
import pandas as pd

# ==============================================================================
# OFFICIAL ELEXON BMRS API SPECIFICATION CONSTANTS
# ==============================================================================
BASE_URL = "https://data.elexon.co.uk/bmrs/api/v1"

# Stream Endpoints (Return raw JSON array without {"data": ...} wrapper)
ENDPOINT_FUELHH_STREAM = f"{BASE_URL}/datasets/FUELHH/stream"
ENDPOINT_WINDFOR_STREAM = f"{BASE_URL}/datasets/WINDFOR/stream"

# Official Query Parameter Names
PARAM_SETTLEMENT_DATE_FROM = "settlementDateFrom"      # Format: YYYY-MM-DD
PARAM_SETTLEMENT_DATE_TO = "settlementDateTo"          # Format: YYYY-MM-DD
PARAM_PUBLISH_DATETIME_FROM = "publishDateTimeFrom"    # Format: ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)
PARAM_PUBLISH_DATETIME_TO = "publishDateTimeTo"        # Format: ISO-8601 UTC (YYYY-MM-DDTHH:MM:SSZ)
PARAM_FUEL_TYPE = "fuelType"                           # e.g., "WIND"

# Enforced API Boundaries (RFC 9110 / HTTP 400 if exceeded)
MAX_DATE_RANGE_DAYS = 7  # Maximum inclusive span between From and To dates

# 2-Day Verification Sample Bounds
SAMPLE_SETTLEMENT_DATE_FROM = "2026-01-01"
SAMPLE_SETTLEMENT_DATE_TO = "2026-01-02"
SAMPLE_PUBLISH_DATETIME_FROM = "2026-01-01T00:00:00Z"
SAMPLE_PUBLISH_DATETIME_TO = "2026-01-03T00:00:00Z"
REQUEST_TIMEOUT_SECONDS = 30.0


def fetch_fuelhh_sample() -> pd.DataFrame:
    """Fetch 2-day sample of FUELHH actual wind generation using the stream endpoint."""
    params = {
        PARAM_SETTLEMENT_DATE_FROM: SAMPLE_SETTLEMENT_DATE_FROM,
        PARAM_SETTLEMENT_DATE_TO: SAMPLE_SETTLEMENT_DATE_TO,
        PARAM_FUEL_TYPE: "WIND",
    }
    headers = {"User-Agent": "ElexonDiscoveryScript/1.0"}

    print(f"\n[1/2] Calling FUELHH stream endpoint: {ENDPOINT_FUELHH_STREAM}")
    print(f"      Parameters: {params}")

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
        response = client.get(ENDPOINT_FUELHH_STREAM, params=params)
        response.raise_for_status()

        raw_data = response.json()
        print(f"      HTTP Status: {response.status_code}")
        print(f"      Response Format: Top-level {type(raw_data).__name__} (length: {len(raw_data)})")

        df = pd.DataFrame(raw_data)
        return df


def fetch_windfor_sample() -> pd.DataFrame:
    """Fetch 2-day sample of WINDFOR wind forecasts using the stream endpoint."""
    params = {
        PARAM_PUBLISH_DATETIME_FROM: SAMPLE_PUBLISH_DATETIME_FROM,
        PARAM_PUBLISH_DATETIME_TO: SAMPLE_PUBLISH_DATETIME_TO,
    }
    headers = {"User-Agent": "ElexonDiscoveryScript/1.0"}

    print(f"\n[2/2] Calling WINDFOR stream endpoint: {ENDPOINT_WINDFOR_STREAM}")
    print(f"      Parameters: {params}")

    with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, headers=headers) as client:
        response = client.get(ENDPOINT_WINDFOR_STREAM, params=params)
        response.raise_for_status()

        raw_data = response.json()
        print(f"      HTTP Status: {response.status_code}")
        print(f"      Response Format: Top-level {type(raw_data).__name__} (length: {len(raw_data)})")

        df = pd.DataFrame(raw_data)
        return df


def main() -> None:
    # --------------------------------------------------------------------------
    # 1. FUELHH Actuals Verification
    # --------------------------------------------------------------------------
    df_fuel = fetch_fuelhh_sample()
    print("\n" + "=" * 80)
    print("DATASET: FUELHH (Actual Wind Outturn - Stream Endpoint)")
    print("=" * 80)
    print(f"Shape: {df_fuel.shape}")
    print("\nColumns and Data Types:")
    for col, dtype in df_fuel.dtypes.items():
        print(f"  - {col:<20} {dtype}")
    print("\nFirst 5 Sample Rows:")
    print(df_fuel.head(5).to_string(index=False))

    # --------------------------------------------------------------------------
    # 2. WINDFOR Forecasts Verification
    # --------------------------------------------------------------------------
    df_wind = fetch_windfor_sample()
    print("\n" + "=" * 80)
    print("DATASET: WINDFOR (Wind Generation Forecast - Stream Endpoint)")
    print("=" * 80)
    print(f"Shape: {df_wind.shape}")
    print("\nColumns and Data Types:")
    for col, dtype in df_wind.dtypes.items():
        print(f"  - {col:<20} {dtype}")
    print("\nFirst 5 Sample Rows:")
    print(df_wind.head(5).to_string(index=False))

    # --------------------------------------------------------------------------
    # 3. Domain Questions Analysis
    # --------------------------------------------------------------------------
    df_wind["startTime_dt"] = pd.to_datetime(df_wind["startTime"], utc=True)
    df_wind["publishTime_dt"] = pd.to_datetime(df_wind["publishTime"], utc=True)

    print("\n" + "=" * 80)
    print("DOMAIN VERIFICATION QUESTIONS & FINDINGS")
    print("=" * 80)

    # Q1: Timestamp Granularity
    minutes_dist = df_wind["startTime_dt"].dt.minute.value_counts().to_dict()
    print(f"1. Timestamp Granularity (Minute values in startTime): {minutes_dist}")
    if set(minutes_dist.keys()) == {0}:
        print("   -> CONCLUSION: WINDFOR timestamps are strictly HOURLY (every record has minute == 00).")
    else:
        print("   -> CONCLUSION: WINDFOR contains sub-hourly timestamps.")

    # Q2: Distinct publishTimes per startTime
    pubs_per_start = df_wind.groupby("startTime_dt")["publishTime_dt"].nunique()
    print(f"\n2. Revisions per Delivery Slot (Distinct publishTimes per startTime):")
    print(f"   - Minimum: {pubs_per_start.min()}")
    print(f"   - Median:  {pubs_per_start.median():.1f}")
    print(f"   - Mean:    {pubs_per_start.mean():.2f}")
    print(f"   - Maximum: {pubs_per_start.max()}")
    print(f"   -> CONCLUSION: In full publication windows, National Grid publishes up to {pubs_per_start.max()} revisions per delivery hour.")

    # Q3: Horizon Range
    df_wind["horizon_hours"] = (df_wind["startTime_dt"] - df_wind["publishTime_dt"]).dt.total_seconds() / 3600.0
    forward_horizons = df_wind[df_wind["horizon_hours"] >= 0]["horizon_hours"]
    print(f"\n3. Forecast Horizon Range (startTime - publishTime):")
    print(f"   - Overall Range: {df_wind['horizon_hours'].min():.1f}h to {df_wind['horizon_hours'].max():.1f}h")
    print(f"   - Forward Looking Range (startTime >= publishTime): {forward_horizons.min():.1f}h to {forward_horizons.max():.1f}h")
    print(f"   -> CONCLUSION: Forward forecasts extend from {forward_horizons.min():.1f}h (intraday) up to ~{forward_horizons.max():.1f}h (~2.75 days ahead).")
    print("=" * 80)


if __name__ == "__main__":
    main()
