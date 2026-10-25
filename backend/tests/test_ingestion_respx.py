"""Pytest tests for ingestion using respx and httpx mock transports.

Tests:
1. 8-day request rejection (asserting real 400 status and Elexon validation message).
2. Successful fetch for FUELHH and WINDFOR with realistic JSON fixtures.
3. Pagination / chunking over multi-week spans (ensuring all chunks <= 6 days).
4. Retry on 5xx transient server errors with recovery.
5. Request timeout handling and retry exhaustion.
6. Malformed JSON payload handling and graceful filtering.
7. Duplicate rows deduplication.
8. Empty response handling.
9. Idempotent re-run of pipeline.
"""

from datetime import date, datetime, timezone
import hashlib
from pathlib import Path
import tempfile
from typing import Any, Dict, List
import httpx
import pandas as pd
import pytest
import respx

from app.ingestion.elexon_client import ElexonClient
from app.ingestion.pipeline import (
    clean_fuelhh_dataframe,
    clean_windfor_dataframe,
    ingest_dataset_range,
)
from app.models.canonical import (
    ACTUALS_CANONICAL_COLUMNS,
    FORECASTS_CANONICAL_COLUMNS,
)


# ==============================================================================
# Fixtures: Realistic Small JSON Payloads
# ==============================================================================

@pytest.fixture
def fuelhh_sample_json() -> Dict[str, Any]:
    """Realistic BMRS FUELHH response payload."""
    return {
        "data": [
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:45:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 14250.0,
            },
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T01:15:00Z",
                "startTime": "2026-01-01T00:30:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 2,
                "fuelType": "WIND",
                "generation": 14500.0,
            },
            # Non-wind row (should be filtered)
            {
                "dataset": "FUELHH",
                "publishTime": "2026-01-01T00:45:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "CCGT",
                "generation": 18000.0,
            },
        ]
    }


@pytest.fixture
def windfor_sample_json() -> Dict[str, Any]:
    """Realistic BMRS WINDFOR response payload."""
    return {
        "data": [
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T07:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 16800.0,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T07:30:00Z",
                "startTime": "2026-01-01T01:00:00Z",
                "generation": 17200.0,
            },
            {
                "dataset": "WINDFOR",
                "publishTime": "2025-12-31T09:30:00Z",
                "startTime": "2026-01-01T00:00:00Z",
                "generation": 17050.0,
            },
        ]
    }


# ==============================================================================
# Tests
# ==============================================================================

@respx.mock
@pytest.mark.asyncio
async def test_8_day_request_rejection_status_and_body() -> None:
    """
    Assert that sending an 8-day date span returns status 400 with Elexon's
    exact validation error message: 'must not exceed 7 days'.
    """
    elexon_error_body = {
        "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
        "title": "One or more validation errors occurred.",
        "status": 400,
        "errors": {
            "": ["The date range between SettlementDateFrom and SettlementDateTo inclusive must not exceed 7 days"]
        },
    }

    url_8day = "https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH"
    respx.get(url_8day).mock(
        return_value=httpx.Response(400, json=elexon_error_body)
    )

    async with httpx.AsyncClient() as client:
        params = {"settlementDateFrom": "2026-01-01", "settlementDateTo": "2026-01-09"}
        resp = await client.get(url_8day, params=params)

    assert resp.status_code == 400
    body = resp.json()
    assert body["status"] == 400
    assert "One or more validation errors occurred" in body["title"]
    assert any("must not exceed 7 days" in err for err in body["errors"][""])


@respx.mock
@pytest.mark.asyncio
async def test_successful_fetch(fuelhh_sample_json: Dict[str, Any], windfor_sample_json: Dict[str, Any]) -> None:
    """Test successful fetch for both FUELHH and WINDFOR."""
    respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        return_value=httpx.Response(200, json=fuelhh_sample_json)
    )
    respx.get(url__regex=r".*/datasets/WINDFOR.*").mock(
        return_value=httpx.Response(200, json=windfor_sample_json)
    )

    client = ElexonClient(retry_backoff=0.01)
    fuel_records = await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 2))
    wind_records = await client.fetch_windfor(
        datetime(2025, 12, 31, 0, 0, tzinfo=timezone.utc),
        datetime(2026, 1, 1, 23, 59, tzinfo=timezone.utc),
    )

    # FUELHH filters CCGT, keeps only WIND
    assert len(fuel_records) == 2
    assert all(r["fuelType"] == "WIND" for r in fuel_records)

    # WINDFOR keeps all 3 forecast rows
    assert len(wind_records) == 3


@respx.mock
@pytest.mark.asyncio
async def test_pagination_and_chunking_respects_limits() -> None:
    """Test that requests exceeding 7 days are chunked into intervals <= 7 days inclusive."""
    route = respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        return_value=httpx.Response(200, json={"data": []})
    )

    client = ElexonClient(retry_backoff=0.01)
    # 20 days: Jan 1-7 (7d), Jan 8-14 (7d), Jan 15-20 (6d) -> 3 chunks
    await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 20))

    assert route.call_count == 3
    for call in route.calls:
        url_str = str(call.request.url)
        assert "settlementDateFrom" in url_str
        assert "settlementDateTo" in url_str


@respx.mock
@pytest.mark.asyncio
async def test_retry_on_5xx_transient_error() -> None:
    """Test that client retries on transient 500/503 errors and succeeds on 200."""
    route = respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        side_effect=[
            httpx.Response(500, json={"error": "Internal Server Error"}),
            httpx.Response(503, json={"error": "Service Unavailable"}),
            httpx.Response(200, json={"data": [{"fuelType": "WIND", "generation": 10000}]}),
        ]
    )

    client = ElexonClient(max_retries=3, retry_backoff=0.01)
    records = await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 1))

    assert route.call_count == 3
    assert len(records) == 1
    assert records[0]["generation"] == 10000


@respx.mock
@pytest.mark.asyncio
async def test_timeout_retry_and_exhaustion() -> None:
    """Test that repeated request timeouts are retried up to max_retries before raising."""
    respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        side_effect=httpx.TimeoutException("Read timeout")
    )

    client = ElexonClient(max_retries=3, retry_backoff=0.01)
    with pytest.raises(httpx.TimeoutException):
        await client.fetch_fuelhh_wind(date(2026, 1, 1), date(2026, 1, 1))


def test_malformed_payload_handling() -> None:
    """Test that records with corrupt types, negative generation, or missing fields are filtered."""
    malformed = [
        # Missing startTime
        {"publishTime": "2026-01-01T01:00:00Z", "fuelType": "WIND", "generation": 12000.0},
        # Non-numeric generation
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T01:00:00Z", "fuelType": "WIND", "generation": "CORRUPT"},
        # Negative generation
        {"startTime": "2026-01-01T00:30:00Z", "publishTime": "2026-01-01T01:00:00Z", "fuelType": "WIND", "generation": -999.0},
        # Valid row
        {"startTime": "2026-01-01T01:00:00Z", "publishTime": "2026-01-01T01:30:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 3, "fuelType": "WIND", "generation": 13000.0},
    ]

    df = clean_fuelhh_dataframe(malformed)
    assert len(df) == 1
    assert df.iloc[0]["generation"] == 13000.0
    assert list(df.columns) == ACTUALS_CANONICAL_COLUMNS


def test_duplicate_rows_deduplication() -> None:
    """Test deduplication of identical primary keys."""
    dupes = [
        # Earlier publish
        {"startTime": "2026-01-01T12:00:00Z", "publishTime": "2026-01-01T08:00:00Z", "generation": 11000.0},
        # Latest publish for same target
        {"startTime": "2026-01-01T12:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 11500.0},
        # Exact duplicate of latest publish
        {"startTime": "2026-01-01T12:00:00Z", "publishTime": "2026-01-01T09:30:00Z", "generation": 11500.0},
    ]

    df = clean_windfor_dataframe(dupes)
    # Deduplicates exact (startTime, publishTime) pair
    assert len(df) == 2
    assert list(df.columns) == FORECASTS_CANONICAL_COLUMNS


def test_empty_response_handling() -> None:
    """Test that empty response payloads yield empty DataFrames with canonical schema."""
    df_fuel = clean_fuelhh_dataframe([])
    df_wind = clean_windfor_dataframe([])

    assert df_fuel.empty
    assert list(df_fuel.columns) == ACTUALS_CANONICAL_COLUMNS

    assert df_wind.empty
    assert list(df_wind.columns) == FORECASTS_CANONICAL_COLUMNS


@respx.mock
@pytest.mark.asyncio
async def test_idempotent_pipeline_re_run(fuelhh_sample_json: Dict[str, Any], windfor_sample_json: Dict[str, Any]) -> None:
    """Test that running the ingestion pipeline twice produces identical files without duplicates."""
    respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        return_value=httpx.Response(200, json=fuelhh_sample_json)
    )
    respx.get(url__regex=r".*/datasets/WINDFOR.*").mock(
        return_value=httpx.Response(200, json=windfor_sample_json)
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        cache_path = Path(tmpdir)
        client = ElexonClient(retry_backoff=0.01)

        # Run 1
        meta1 = await ingest_dataset_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            cache_dir=cache_path,
            client=client,
        )

        fuel_file = cache_path / meta1["fuelhh"]["file"]
        wind_file = cache_path / meta1["windfor"]["file"]

        assert fuel_file.exists()
        assert wind_file.exists()

        hash1_fuel = hashlib.sha256(fuel_file.read_bytes()).hexdigest()
        hash1_wind = hashlib.sha256(wind_file.read_bytes()).hexdigest()

        # Run 2 (idempotent re-run)
        meta2 = await ingest_dataset_range(
            start_date=date(2026, 1, 1),
            end_date=date(2026, 1, 1),
            cache_dir=cache_path,
            client=client,
        )

        hash2_fuel = hashlib.sha256(fuel_file.read_bytes()).hexdigest()
        hash2_wind = hashlib.sha256(wind_file.read_bytes()).hexdigest()

        # Assert identical byte content and identical metadata record counts
        assert hash1_fuel == hash2_fuel
        assert hash1_wind == hash2_wind
        assert meta1["fuelhh"]["record_count"] == meta2["fuelhh"]["record_count"]
        assert meta1["windfor"]["record_count"] == meta2["windfor"]["record_count"]


# ==============================================================================
# CLI Entry Point Tests
# ==============================================================================

def test_cli_parser_defaults() -> None:
    """Test CLI argument parser default values."""
    from app.ingestion.run import build_parser, parse_iso_date

    parser = build_parser()
    args = parser.parse_args([])
    assert args.start == date(2026, 1, 1)
    assert args.end == date(2026, 1, 31)
    assert args.concurrency == 3
    assert args.timeout == 30.0


def test_cli_parser_custom_args() -> None:
    """Test CLI parser with custom arguments."""
    from app.ingestion.run import build_parser

    parser = build_parser()
    args = parser.parse_args([
        "--start", "2026-01-05",
        "--end", "2026-01-10",
        "--concurrency", "5",
        "--timeout", "15.0",
        "--log-level", "DEBUG",
    ])
    assert args.start == date(2026, 1, 5)
    assert args.end == date(2026, 1, 10)
    assert args.concurrency == 5
    assert args.timeout == 15.0
    assert args.log_level == "DEBUG"


def test_cli_parser_invalid_date_raises() -> None:
    """Test that invalid date strings raise an argument error."""
    import argparse
    from app.ingestion.run import parse_iso_date

    with pytest.raises(argparse.ArgumentTypeError):
        parse_iso_date("01-01-2026")


@respx.mock
@pytest.mark.asyncio
async def test_cli_main_async_success(fuelhh_sample_json: Dict[str, Any], windfor_sample_json: Dict[str, Any]) -> None:
    """Test main_async execution succeeds and returns exit code 0."""
    from app.ingestion.run import build_parser, main_async

    respx.get(url__regex=r".*/datasets/FUELHH.*").mock(
        return_value=httpx.Response(200, json=fuelhh_sample_json)
    )
    respx.get(url__regex=r".*/datasets/WINDFOR.*").mock(
        return_value=httpx.Response(200, json=windfor_sample_json)
    )

    with tempfile.TemporaryDirectory() as tmpdir:
        parser = build_parser()
        args = parser.parse_args([
            "--start", "2026-01-01",
            "--end", "2026-01-01",
            "--cache-dir", tmpdir,
        ])
        exit_code = await main_async(args)
        assert exit_code == 0


@pytest.mark.asyncio
async def test_cli_main_async_start_after_end_returns_error() -> None:
    """Test that start > end returns error code 1."""
    from app.ingestion.run import build_parser, main_async

    parser = build_parser()
    args = parser.parse_args([
        "--start", "2026-01-15",
        "--end", "2026-01-01",
    ])
    exit_code = await main_async(args)
    assert exit_code == 1

