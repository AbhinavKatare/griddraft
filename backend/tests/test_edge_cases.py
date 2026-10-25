"""Unit tests for edge cases, data sanitization and boundary conditions."""

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.ingestion.pipeline import (
    clean_fuelhh_dataframe,
    clean_windfor_dataframe,
)
from app.main import app
from app.analytics.metrics import (
    calculate_monthly_kpis,
    calculate_daily_metrics,
)


def test_clean_fuelhh_filters_non_wind() -> None:
    """Ensure FUELHH ingestion discards non-wind fuel types like CCGT, NUCLEAR, BIOMASS."""
    raw = [
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:30:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "CCGT", "generation": 15000},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:30:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "WIND", "generation": 8500},
        {"startTime": "2026-01-01T00:00:00Z", "publishTime": "2026-01-01T00:30:00Z", "settlementDate": "2026-01-01", "settlementPeriod": 1, "fuelType": "NUCLEAR", "generation": 5000},
    ]
    df = clean_fuelhh_dataframe(raw)
    assert len(df) == 1
    assert df.iloc[0]["fuelType"] == "WIND"
    assert df.iloc[0]["generation"] == 8500.0


def test_clean_windfor_filters_out_of_january_delivery() -> None:
    """Ensure WINDFOR records with delivery outside January 2026 are excluded."""
    raw = [
        # In range
        {"startTime": "2026-01-15T12:00:00Z", "publishTime": "2026-01-14T08:00:00Z", "generation": 12000},
        # February delivery (out of scope)
        {"startTime": "2026-02-01T00:00:00Z", "publishTime": "2026-01-31T08:00:00Z", "generation": 11000},
        # December delivery (out of scope)
        {"startTime": "2025-12-31T23:30:00Z", "publishTime": "2025-12-30T08:00:00Z", "generation": 9000},
    ]
    df = clean_windfor_dataframe(raw)
    assert len(df) == 1
    assert df.iloc[0]["startTime"] == pd.Timestamp("2026-01-15 12:00:00", tz="UTC")


def test_empty_dataframe_metrics() -> None:
    """Ensure metric calculations on empty dataframes return zero/graceful structures rather than throwing exceptions."""
    empty_df = pd.DataFrame()
    kpis = calculate_monthly_kpis(empty_df)
    assert kpis.matched_half_hours == 0
    assert kpis.data_coverage_pct == 0.0
    assert kpis.mae_mw == 0.0

    daily = calculate_daily_metrics(empty_df)
    assert daily == []


def test_api_root_endpoint() -> None:
    """Test API root status response."""
    with TestClient(app) as client:
        resp = client.get("/")
        assert resp.status_code == 200
        data = resp.json()
        assert "UK Wind Forecast Monitoring" in data["service"]
        assert data["target_scope"] == "January 2026 UK Wind (FUELHH & WINDFOR)"


def test_invalid_date_rejection() -> None:
    """Test API rejects dates outside January 2026."""
    with TestClient(app) as client:
        resp = client.get("/api/v1/forecast-snapshot?delivery_date=2026-02-15")
        assert resp.status_code == 400
        assert "January 2026" in resp.json()["detail"]
