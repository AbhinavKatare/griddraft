"""Unit and integration tests for canonical schemas, normalisation, and ingestion pipeline."""

from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import pandas as pd
import pytest
from pydantic import ValidationError

from app.ingestion.pipeline import (
    atomic_write_parquet,
    normalise_actuals_dataframe,
    normalise_forecasts_dataframe,
)
from app.models.canonical import (
    ACTUALS_CANONICAL_COLUMNS,
    FORECASTS_CANONICAL_COLUMNS,
    CanonicalActualRow,
    CanonicalForecastRow,
)


class TestCanonicalSchemas:
    """Test canonical Pydantic model validation."""

    def test_valid_actual_row(self) -> None:
        row = CanonicalActualRow(
            dataset="FUELHH",
            publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
            startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
            generation=12500.5,
        )
        assert row.generation == 12500.5
        assert row.settlementPeriod == 1
        assert row.fuelType == "WIND"
        assert row.publishTime.tzinfo is not None

    def test_actual_row_naive_datetime_coerced_to_utc(self) -> None:
        row = CanonicalActualRow(
            publishTime=datetime(2026, 1, 1, 1, 0),
            startTime=datetime(2026, 1, 1, 0, 0),
            settlementDate="2026-01-01",
            settlementPeriod=1,
            fuelType="WIND",
            generation=1000.0,
        )
        assert row.startTime.tzinfo == timezone.utc
        assert row.publishTime.tzinfo == timezone.utc

    def test_actual_row_negative_generation_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalActualRow(
                publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                settlementDate="2026-01-01",
                settlementPeriod=1,
                fuelType="WIND",
                generation=-150.0,
            )

    def test_actual_row_invalid_fueltype_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalActualRow(
                publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                settlementDate="2026-01-01",
                settlementPeriod=1,
                fuelType="CCGT",
                generation=1500.0,
            )

    def test_actual_row_invalid_settlement_period_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalActualRow(
                publishTime=datetime(2026, 1, 1, 1, 0, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 0, 0, tzinfo=timezone.utc),
                settlementDate="2026-01-01",
                settlementPeriod=55,  # Max is 50
                fuelType="WIND",
                generation=1500.0,
            )

    def test_valid_forecast_row(self) -> None:
        row = CanonicalForecastRow(
            dataset="WINDFOR",
            publishTime=datetime(2025, 12, 31, 7, 30, tzinfo=timezone.utc),
            startTime=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
            generation=18450.0,
        )
        assert row.generation == 18450.0
        assert row.dataset == "WINDFOR"

    def test_forecast_negative_generation_rejected(self) -> None:
        with pytest.raises(ValidationError):
            CanonicalForecastRow(
                publishTime=datetime(2025, 12, 31, 7, 30, tzinfo=timezone.utc),
                startTime=datetime(2026, 1, 1, 10, 0, tzinfo=timezone.utc),
                generation=-10.0,
            )


class TestNormalisationAndDeduplication:
    """Test DataFrame normalisation, cleaning, and deduplication logic."""

    def test_normalise_actuals_filters_and_deduplicates(self) -> None:
        raw_data = pd.DataFrame([
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2026-01-01T00:45:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 10000.0,
            },
            # Earlier duplicate publish for same startTime -> should be dropped
            {
                "startTime": "2026-01-01T00:00:00Z",
                "publishTime": "2026-01-01T00:15:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 9800.0,
            },
            # Non-wind row -> should be filtered
            {
                "startTime": "2026-01-01T00:30:00Z",
                "publishTime": "2026-01-01T01:00:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 2,
                "fuelType": "NUCLEAR",
                "generation": 5000.0,
            },
            # Negative generation row -> should be dropped
            {
                "startTime": "2026-01-01T01:00:00Z",
                "publishTime": "2026-01-01T01:30:00Z",
                "settlementDate": "2026-01-01",
                "settlementPeriod": 3,
                "fuelType": "WIND",
                "generation": -50.0,
            },
        ])

        clean = normalise_actuals_dataframe(raw_data)

        # Only 1 valid wind row should survive
        assert len(clean) == 1
        assert list(clean.columns) == ACTUALS_CANONICAL_COLUMNS
        assert clean.iloc[0]["generation"] == 10000.0
        assert clean.iloc[0]["settlementPeriod"] == 1
        assert clean["startTime"].dt.tz is not None

    def test_normalise_forecasts_deduplicates_composite_key(self) -> None:
        raw_data = pd.DataFrame([
            {
                "startTime": "2026-01-01T12:00:00Z",
                "publishTime": "2025-12-31T07:30:00Z",
                "generation": 14000.0,
            },
            # Exact duplicate of (startTime, publishTime)
            {
                "startTime": "2026-01-01T12:00:00Z",
                "publishTime": "2025-12-31T07:30:00Z",
                "generation": 14000.0,
            },
            # Different publishTime for same target
            {
                "startTime": "2026-01-01T12:00:00Z",
                "publishTime": "2025-12-31T09:30:00Z",
                "generation": 14200.0,
            },
        ])

        clean = normalise_forecasts_dataframe(raw_data)
        assert len(clean) == 2
        assert list(clean.columns) == FORECASTS_CANONICAL_COLUMNS
        assert (clean["generation"] > 0).all()


class TestAtomicWriteAndIdempotence:
    """Test atomic parquet writing and idempotence."""

    def test_atomic_write_creates_readable_parquet(self) -> None:
        df = pd.DataFrame([
            {
                "dataset": "FUELHH",
                "publishTime": pd.Timestamp("2026-01-01 01:00:00", tz="UTC"),
                "startTime": pd.Timestamp("2026-01-01 00:00:00", tz="UTC"),
                "settlementDate": "2026-01-01",
                "settlementPeriod": 1,
                "fuelType": "WIND",
                "generation": 12000.0,
            }
        ])

        with tempfile.TemporaryDirectory() as tmpdir:
            dest_file = Path(tmpdir) / "test_actuals.parquet"
            atomic_write_parquet(df, dest_file)
            assert dest_file.exists()

            loaded = pd.read_parquet(dest_file)
            assert len(loaded) == 1
            assert loaded.iloc[0]["generation"] == 12000.0

            # Idempotent re-write with same data
            atomic_write_parquet(df, dest_file)
            loaded_again = pd.read_parquet(dest_file)
            assert len(loaded_again) == 1
            assert loaded_again.equals(loaded)
