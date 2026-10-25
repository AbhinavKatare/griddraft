"""Comprehensive API tests for versioned API v1, parameter validation, leakage guards, and middleware."""

from datetime import date
from fastapi.testclient import TestClient
import httpx
import pytest

from app.analytics.cache import clear_analytics_cache
from app.main import app
from app.models.schemas import (
    ErrorByHorizonResponse,
    ErrorByHourResponse,
    ForecastSnapshotResponse,
    HealthResponse,
    MetaResponse,
    MonthlyKPIs,
    TimeseriesResponse,
)
from app.analytics.risk import SafeWindSummary

client = TestClient(app)


# ==============================================================================
# 1. System, Diagnostics & Health Endpoints
# ==============================================================================

def test_health_endpoint() -> None:
    """Test /health endpoint returns 200, valid HealthResponse schema and cache status."""
    resp = client.get("/health")
    assert resp.status_code == 200
    model = HealthResponse(**resp.json())
    assert model.status == "healthy"
    assert model.cache_loaded is True


def test_root_endpoint() -> None:
    """Test root endpoint provides service metadata and navigation links."""
    resp = client.get("/")
    assert resp.status_code == 200
    data = resp.json()
    assert "UK Wind Forecast Monitoring" in data["service"]
    assert data["api_v1"] == "/api/v1"
    assert data["health"] == "/health"
    assert data["metrics"] == "/metrics"


def test_timing_metrics_endpoint() -> None:
    """Test /metrics endpoint returns request counter and latency telemetry."""
    # Trigger a request first
    client.get("/health")
    resp = client.get("/metrics")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_requests" in data
    assert data["total_requests"] >= 1
    assert "endpoints" in data


# ==============================================================================
# 2. V1 Metadata & Schema Conformance
# ==============================================================================

def test_meta_endpoint_schema_conformance() -> None:
    """Test /api/v1/meta conforms strictly to MetaResponse schema."""
    resp = client.get("/api/v1/meta")
    assert resp.status_code == 200
    model = MetaResponse(**resp.json())
    assert model.available_start_date == "2026-01-01"
    assert model.available_end_date == "2026-01-31"
    assert model.fuelhh_rows == 1488
    assert model.windfor_rows == 18104


# ==============================================================================
# 3. Timeseries & Downsampling
# ==============================================================================

def test_timeseries_happy_path_30m() -> None:
    """Test /api/v1/timeseries native 30-minute interval response."""
    resp = client.get("/api/v1/timeseries?start_date=2026-01-01&end_date=2026-01-02&decision_time=09:00")
    assert resp.status_code == 200
    model = TimeseriesResponse(**resp.json())
    assert model.total_points == 96  # 2 days * 48 half-hours
    assert len(model.data) == 96
    first_pt = model.data[0]
    assert first_pt.settlement_date == "2026-01-01"
    assert first_pt.settlement_period == 1
    assert first_pt.actual_mw is not None
    assert first_pt.decision_forecast_mw is not None
    assert first_pt.latest_forecast_mw is not None


def test_timeseries_downsampling_1h_and_3h() -> None:
    """Test /api/v1/timeseries downsampling with ?resolution=1h and ?resolution=3h."""
    # 1h downsampling: 2 days * 24 hours = 48 points
    resp_1h = client.get("/api/v1/timeseries?start_date=2026-01-01&end_date=2026-01-02&resolution=1h")
    assert resp_1h.status_code == 200
    data_1h = resp_1h.json()
    assert data_1h["total_points"] == 48

    # 3h downsampling: 2 days * 8 intervals = 16 points
    resp_3h = client.get("/api/v1/timeseries?start_date=2026-01-01&end_date=2026-01-02&resolution=3h")
    assert resp_3h.status_code == 200
    data_3h = resp_3h.json()
    assert data_3h["total_points"] == 16


def test_timeseries_invalid_resolution_rejection() -> None:
    """Test /api/v1/timeseries rejects unsupported resolution values."""
    resp = client.get("/api/v1/timeseries?start_date=2026-01-01&end_date=2026-01-02&resolution=4h")
    assert resp.status_code == 400
    assert resp.headers["content-type"] == "application/problem+json"


# ==============================================================================
# 4. Forecast Snapshot & Leakage Guard
# ==============================================================================

def test_forecast_snapshot_happy_path() -> None:
    """Test /api/v1/forecast-snapshot conforms to ForecastSnapshotResponse."""
    resp = client.get("/api/v1/forecast-snapshot?delivery_date=2026-01-15&decision_time=09:00")
    assert resp.status_code == 200
    model = ForecastSnapshotResponse(**resp.json())
    assert model.delivery_date == "2026-01-15"
    assert model.total_periods == 48
    assert len(model.periods) == 48


def test_information_leakage_guard_strictly_enforced() -> None:
    """
    LEAKAGE GUARD TEST:
    Ensures that for a decision cutoff at 09:00 on D-1, no forecast published at 09:01
    or later is ever returned in snapshot or timeseries endpoints.
    """
    delivery_date = "2026-01-15"
    cutoff = "09:00"  # D-1 09:00 UTC

    resp = client.get(f"/api/v1/forecast-snapshot?delivery_date={delivery_date}&decision_time={cutoff}")
    assert resp.status_code == 200
    data = resp.json()

    cutoff_limit = data["cutoff_time"]  # "2026-01-14T09:00:00+00:00"

    for period in data["periods"]:
        if period["latest_publish_time"] is not None:
            # Publish time MUST be <= cutoff_limit
            assert period["latest_publish_time"] <= cutoff_limit, (
                f"LEAKAGE DETECTED: Forecast published at {period['latest_publish_time']} "
                f"was selected despite cutoff at {cutoff_limit}!"
            )


# ==============================================================================
# 5. Metrics & Stratified Profiles
# ==============================================================================

def test_metrics_happy_path() -> None:
    """Test /api/v1/metrics conforms to MonthlyKPIs schema and returns clean numbers."""
    resp = client.get("/api/v1/metrics?decision_time=09:00")
    assert resp.status_code == 200
    model = MonthlyKPIs(**resp.json())
    assert model.month == "2026-01"
    assert model.matched_half_hours == 1488
    assert model.mae_mw == pytest.approx(2145.2, 0.1)
    assert model.mae_pct_of_mean_gen == 18.52
    assert model.mae_pct_of_max_gen == 12.05


def test_error_by_horizon_both_sources() -> None:
    """Test /api/v1/error-by-horizon for both 'all' and 'decision' sources."""
    # All pre-delivery revisions
    resp_all = client.get("/api/v1/error-by-horizon?source=all")
    assert resp_all.status_code == 200
    model_all = ErrorByHorizonResponse(**resp_all.json())
    assert model_all.source == "all_pre_delivery_revisions"
    assert model_all.total_observations > 25000

    # Decision time snapshot
    resp_dec = client.get("/api/v1/error-by-horizon?source=decision&decision_time=09:00")
    assert resp_dec.status_code == 200
    model_dec = ErrorByHorizonResponse(**resp_dec.json())
    assert "decision_time_snapshot" in model_dec.source
    assert model_dec.total_observations == 1488


def test_error_by_hour_happy_path() -> None:
    """Test /api/v1/error-by-hour conforms to ErrorByHourResponse with all 24 clock hours."""
    resp = client.get("/api/v1/error-by-hour?decision_time=09:00")
    assert resp.status_code == 200
    model = ErrorByHourResponse(**resp.json())
    assert len(model.hours) == 24
    hours = [h["hour_of_day"] for h in model.hours]
    assert hours == list(range(24))


# ==============================================================================
# 6. Risk Analytics & Safe Wind Endpoint
# ==============================================================================

def test_safe_wind_endpoint_in_sample_and_prior_days() -> None:
    """Test /api/v1/risk/safe-wind returns SafeWindSummary with decomposition and backtest."""
    # In-sample mode
    resp_in = client.get("/api/v1/risk/safe-wind?delivery_date=2026-01-15&decision_time=09:00&quantile=0.90&mode=in_sample")
    assert resp_in.status_code == 200
    model_in = SafeWindSummary(**resp_in.json())
    assert model_in.quantile == 0.90
    assert model_in.mode == "in_sample"
    assert model_in.decomposition.total_buffer_mw > 0.0
    assert model_in.backtest is not None
    assert model_in.backtest.empirical_coverage_pct > 80.0
    assert len(model_in.periods) == 48

    # Prior-days mode
    resp_prior = client.get("/api/v1/risk/safe-wind?delivery_date=2026-01-15&decision_time=09:00&quantile=0.90&mode=prior_days")
    assert resp_prior.status_code == 200
    model_prior = SafeWindSummary(**resp_prior.json())
    assert model_prior.mode == "prior_days"


# ==============================================================================
# 7. Validation Errors & RFC 7807 Responses
# ==============================================================================

def test_validation_errors_rfc7807() -> None:
    """Test RFC 7807 format for bad dates, out-of-range dates, bad cutoff, and bad parameters."""
    # 1. Out of range date (outside Jan 2026)
    r1 = client.get("/api/v1/forecast-snapshot?delivery_date=2026-02-15")
    assert r1.status_code == 400
    assert r1.headers["content-type"] == "application/problem+json"
    p1 = r1.json()
    assert "January 2026" in p1["detail"]

    # 2. Malformed date
    r2 = client.get("/api/v1/forecast-snapshot?delivery_date=bad-date")
    assert r2.status_code == 400
    assert r2.headers["content-type"] == "application/problem+json"

    # 3. Start after end date
    r3 = client.get("/api/v1/timeseries?start_date=2026-01-15&end_date=2026-01-10")
    assert r3.status_code == 400
    assert "cannot be after" in r3.json()["detail"]

    # 4. Malformed cutoff time
    r4 = client.get("/api/v1/forecast-snapshot?delivery_date=2026-01-15&decision_time=25:99")
    assert r4.status_code == 400
    assert "HH:MM" in r4.json()["detail"]

    # 5. Invalid risk mode
    r5 = client.get("/api/v1/risk/safe-wind?delivery_date=2026-01-15&mode=unsupported_mode")
    assert r5.status_code == 400
    assert r5.headers["content-type"] == "application/problem+json"


# ==============================================================================
# 8. Middleware, ETag & Caching Behaviour
# ==============================================================================

def test_middleware_request_id_and_etag_caching() -> None:
    """Test that Request ID, latency header, and ETag 304 caching operate correctly."""
    # Initial request
    resp = client.get("/api/v1/meta", headers={"X-Request-ID": "test-req-12345"})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == "test-req-12345"
    assert "X-Process-Time-Ms" in resp.headers
    assert "Cache-Control" in resp.headers
    assert "ETag" in resp.headers

    etag = resp.headers["ETag"]

    # Subsequent request with matching If-None-Match header -> 304 Not Modified
    resp_304 = client.get("/api/v1/meta", headers={"If-None-Match": etag})
    assert resp_304.status_code == 304


# ==============================================================================
# 9. AsyncClient Test (httpx AsyncClient conformance)
# ==============================================================================

@pytest.mark.asyncio
async def test_async_client_happy_path() -> None:
    """Test endpoints using httpx.AsyncClient with ASGI Transport."""
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        resp = await ac.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "healthy"

        resp_meta = await ac.get("/api/v1/meta")
        assert resp_meta.status_code == 200
        assert resp_meta.json()["fuelhh_rows"] == 1488
