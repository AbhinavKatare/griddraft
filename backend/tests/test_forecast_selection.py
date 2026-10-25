"""Unit tests for the vectorised forecast selection engine and expansion."""

from datetime import date, datetime, time, timezone
from pathlib import Path
import time as time_module
import numpy as np
import pandas as pd
import pytest

from app.analytics.forecast_selection import (
    ForecastSelectionMode,
    expand_to_half_hours,
    select_decision_forecast,
)


@pytest.fixture
def sample_forecasts_df() -> pd.DataFrame:
    """Multi-revision sample forecasts for testing selection modes."""
    return pd.DataFrame([
        # Target: 2026-01-02 12:00 UTC (D = Jan 2, Cutoff D-1 09:00 = 2026-01-01 09:00 UTC)
        {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-01 02:30:00Z", "generation": 14000.0},
        {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-01 07:30:00Z", "generation": 14500.0}, # Latest before D-1 09:00
        {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-01 11:30:00Z", "generation": 15000.0}, # After D-1 09:00, before D-1 12:00
        {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-02 09:30:00Z", "generation": 15500.0}, # Intraday before delivery
        {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-02 15:30:00Z", "generation": 16000.0}, # Post-delivery ex-post

        # Target: 2026-01-02 14:00 UTC (Only published AFTER D-1 09:00 cutoff)
        {"startTime": "2026-01-02 14:00:00Z", "publishTime": "2026-01-01 11:30:00Z", "generation": 13800.0},
        {"startTime": "2026-01-02 14:00:00Z", "publishTime": "2026-01-02 10:00:00Z", "generation": 14100.0},

        # Target: 2026-01-02 16:00 UTC (Early forecast available)
        {"startTime": "2026-01-02 16:00:00Z", "publishTime": "2025-12-31 07:30:00Z", "generation": 12000.0},
        {"startTime": "2026-01-02 16:00:00Z", "publishTime": "2026-01-01 07:30:00Z", "generation": 12400.0},
    ])


class TestForecastSelectionDecisionCutoff:
    """Test standard Day-Ahead decision cutoff selection (e.g. D-1 09:00)."""

    def test_select_decision_forecast_d1_0900(self, sample_forecasts_df: pd.DataFrame) -> None:
        res = select_decision_forecast(
            sample_forecasts_df,
            cutoff_time_of_day="09:00",
            cutoff_day_offset=1,
            mode="decision_cutoff",
        )

        assert len(res) == 3  # All 3 unique target startTimes preserved
        assert list(res["startTime"].dt.strftime("%H:%M")) == ["12:00", "14:00", "16:00"]

        # 12:00 target: Should select 2026-01-01 07:30 publication (14,500 MW)
        row_12 = res[res["startTime"].dt.hour == 12].iloc[0]
        assert bool(row_12["has_forecast"]) is True
        assert row_12["forecast_mw"] == 14500.0
        assert row_12["publishTime"] == pd.Timestamp("2026-01-01 07:30:00", tz="UTC")
        assert row_12["horizon_hours"] == 28.5  # 12:00 Jan 2 - 07:30 Jan 1 = 28.5h

        # 14:00 target: Had no forecast published <= Jan 1 09:00!
        row_14 = res[res["startTime"].dt.hour == 14].iloc[0]
        assert row_14["has_forecast"] == False
        assert np.isnan(row_14["forecast_mw"])
        assert pd.isna(row_14["publishTime"])
        assert np.isnan(row_14["horizon_hours"])

        # 16:00 target: Should select 2026-01-01 07:30 publication (12,400 MW)
        row_16 = res[res["startTime"].dt.hour == 16].iloc[0]
        assert row_16["has_forecast"] == True
        assert row_16["forecast_mw"] == 12400.0

    def test_cutoff_time_formats(self, sample_forecasts_df: pd.DataFrame) -> None:
        """Test accepting string '11:00', integer 11, and datetime.time(11, 0)."""
        res_str = select_decision_forecast(sample_forecasts_df, cutoff_time_of_day="11:30")
        res_int = select_decision_forecast(sample_forecasts_df, cutoff_time_of_day=11.5)
        res_time = select_decision_forecast(sample_forecasts_df, cutoff_time_of_day=time(11, 30))

        # At 11:30 cutoff, target 14:00 now HAS a forecast (published at 11:30)
        assert res_str[res_str["startTime"].dt.hour == 14].iloc[0]["has_forecast"] == True
        assert res_str["forecast_mw"].equals(res_int["forecast_mw"])
        assert res_str["forecast_mw"].equals(res_time["forecast_mw"])

    def test_pure_function_non_mutation(self, sample_forecasts_df: pd.DataFrame) -> None:
        """Ensure input DataFrame is not mutated."""
        original_cols = list(sample_forecasts_df.columns)
        original_shape = sample_forecasts_df.shape
        _ = select_decision_forecast(sample_forecasts_df, cutoff_time_of_day="09:00")

        assert list(sample_forecasts_df.columns) == original_cols
        assert sample_forecasts_df.shape == original_shape


class TestRowWiseSelectionAndNaNHandling:
    """Test row-wise selection (sort stable, drop_duplicates keep=last) and NaN preservation."""

    def test_latest_revision_with_nan_generation_retained(self) -> None:
        """
        Protects against: groupby().last() silently dropping NaNs and falling back to older values.
        Row-wise selection MUST select the latest revision even if its generation is NaN.
        """
        target = "2026-01-02 12:00:00Z"
        df = pd.DataFrame([
            # Older revision has valid generation
            {"startTime": target, "publishTime": "2026-01-01 02:30:00Z", "generation": 10000.0},
            # Latest revision before cutoff has NaN generation!
            {"startTime": target, "publishTime": "2026-01-01 07:30:00Z", "generation": np.nan},
        ])

        res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)

        assert len(res) == 1
        row = res.iloc[0]
        # Must pick the 07:30 revision and preserve its NaN (NOT fall back to 10000.0)
        assert row["publishTime"] == pd.Timestamp("2026-01-01 07:30:00", tz="UTC")
        assert np.isnan(row["forecast_mw"])
        assert row["has_forecast"] == True  # Forecast revision exists, even though value was NaN


class TestInvariantsAndValidation:
    """Test validation of inputs and clamping invariants."""

    def test_invalid_day_offset_raises(self, sample_forecasts_df: pd.DataFrame) -> None:
        """cutoff_day_offset < 0 must raise ValueError."""
        with pytest.raises(ValueError, match="cutoff_day_offset must be >= 0"):
            select_decision_forecast(sample_forecasts_df, cutoff_day_offset=-1)

    def test_invalid_time_of_day_raises(self, sample_forecasts_df: pd.DataFrame) -> None:
        """Invalid time string or hours out of range must raise ValueError."""
        with pytest.raises(ValueError, match="Invalid cutoff time format"):
            select_decision_forecast(sample_forecasts_df, cutoff_time_of_day="25:00")
        with pytest.raises(ValueError, match="Cutoff hour must be in range"):
            select_decision_forecast(sample_forecasts_df, cutoff_time_of_day=24.5)

    def test_clamping_invariant_publish_le_cutoff_le_start(self, sample_forecasts_df: pd.DataFrame) -> None:
        """
        Verify the fundamental ordering invariant:
            publishTime <= cutoff_time <= startTime
        Even if cutoff_day_offset=0 and cutoff_time_of_day='23:00', cutoff is clamped to <= startTime.
        """
        res = select_decision_forecast(
            sample_forecasts_df,
            cutoff_time_of_day="23:00",
            cutoff_day_offset=0,  # Same day
        )

        # Invariant 1: cutoff_time <= startTime for all targets
        assert (res["cutoff_time"] <= res["startTime"]).all()

        # Invariant 2: publishTime <= cutoff_time for all matched targets
        matched = res[res["has_forecast"] == True]
        assert (matched["publishTime"] <= matched["cutoff_time"]).all()


class TestAlternativeSelectionModes:
    """Test 'latest_available' and 'fixed_horizon' modes."""

    def test_latest_available_mode(self, sample_forecasts_df: pd.DataFrame) -> None:
        """Latest available mode picks latest forecast strictly prior to delivery start."""
        res = select_decision_forecast(
            sample_forecasts_df,
            mode=ForecastSelectionMode.LATEST_AVAILABLE,
        )

        row_12 = res[res["startTime"].dt.hour == 12].iloc[0]
        assert row_12["forecast_mw"] == 15500.0
        assert row_12["publishTime"] == pd.Timestamp("2026-01-02 09:30:00", tz="UTC")
        assert row_12["horizon_hours"] == 2.5

        row_14 = res[res["startTime"].dt.hour == 14].iloc[0]
        assert row_14["has_forecast"] == True
        assert row_14["forecast_mw"] == 14100.0

    def test_fixed_horizon_mode(self, sample_forecasts_df: pd.DataFrame) -> None:
        """Fixed horizon mode selects forecast available at fixed lead time (e.g. 24h ahead)."""
        res = select_decision_forecast(
            sample_forecasts_df,
            mode=ForecastSelectionMode.FIXED_HORIZON,
            fixed_horizon_hours=24.0,
        )

        row_12 = res[res["startTime"].dt.hour == 12].iloc[0]
        assert row_12["forecast_mw"] == 15000.0
        assert row_12["publishTime"] == pd.Timestamp("2026-01-01 11:30:00", tz="UTC")

        row_14 = res[res["startTime"].dt.hour == 14].iloc[0]
        assert row_14["forecast_mw"] == 13800.0


class TestExpandToHalfHours:
    """Test expand_to_half_hours function."""

    def test_expand_without_actuals(self) -> None:
        """Expanding a 1-hour forecast generates two half-hourly periods (:00 and :30)."""
        hourly = pd.DataFrame([
            {
                "startTime": pd.Timestamp("2026-01-01 10:00:00", tz="UTC"),
                "forecast_mw": 12000.0,
                "publishTime": pd.Timestamp("2025-12-31 07:30:00", tz="UTC"),
                "horizon_hours": 26.5,
                "has_forecast": True,
            }
        ])

        expanded = expand_to_half_hours(hourly)
        assert len(expanded) == 2
        assert list(expanded["startTime"].dt.minute) == [0, 30]
        assert list(expanded["settlementPeriod"]) == [21, 22]  # Hour 10:00 = SP 21 & 22
        assert (expanded["forecast_mw"] == 12000.0).all()

    def test_expand_with_actuals(self) -> None:
        """Expanding with actuals merges on floor('h') and computes point-by-point errors."""
        hourly = pd.DataFrame([
            {
                "startTime": pd.Timestamp("2026-01-01 10:00:00", tz="UTC"),
                "forecast_mw": 12000.0,
                "publishTime": pd.Timestamp("2025-12-31 07:30:00", tz="UTC"),
                "horizon_hours": 26.5,
                "has_forecast": True,
            }
        ])

        actuals = pd.DataFrame([
            {
                "startTime": pd.Timestamp("2026-01-01 10:00:00", tz="UTC"),
                "settlementDate": "2026-01-01",
                "settlementPeriod": 21,
                "generation": 11000.0,
            },
            {
                "startTime": pd.Timestamp("2026-01-01 10:30:00", tz="UTC"),
                "settlementDate": "2026-01-01",
                "settlementPeriod": 22,
                "generation": 11500.0,
            },
        ])

        aligned = expand_to_half_hours(hourly, actuals_df=actuals)
        assert len(aligned) == 2
        # Forecast 12,000 applies to both SP 21 and 22
        assert list(aligned["forecast_mw"]) == [12000.0, 12000.0]
        assert list(aligned["actual_mw"]) == [11000.0, 11500.0]
        assert list(aligned["error_mw"]) == [1000.0, 500.0]
        assert list(aligned["shortfall_mw"]) == [1000.0, 500.0]


class TestEdgeCasesAndPerformance:
    """Test boundary conditions and vectorised execution."""

    def test_empty_dataframe(self) -> None:
        res = select_decision_forecast(pd.DataFrame())
        assert res.empty
        assert "has_forecast" in res.columns
        assert "forecast_mw" in res.columns

    def test_custom_target_start_times(self, sample_forecasts_df: pd.DataFrame) -> None:
        custom_targets = [
            pd.Timestamp("2026-01-02 12:00:00", tz="UTC"),
            pd.Timestamp("2026-01-05 00:00:00", tz="UTC"),
        ]
        res = select_decision_forecast(
            sample_forecasts_df,
            target_start_times=custom_targets,
        )

        assert len(res) == 2
        assert res.iloc[0]["has_forecast"] == True
        assert res.iloc[1]["has_forecast"] == False
        assert np.isnan(res.iloc[1]["forecast_mw"])
        assert pd.isna(res.iloc[1]["publishTime"])

    def test_performance_on_full_month_real_cache(self) -> None:
        """Verify vectorised execution speed on full January 2026 cache (18,104 rows)."""
        cache_file = Path("data/cache/windfor_jan2026.parquet")
        if not cache_file.exists():
            cache_file = Path("../data/cache/windfor_jan2026.parquet")
        if not cache_file.exists():
            pytest.skip("Cache parquet not found for performance test")

        df = pd.read_parquet(cache_file)
        t0 = time_module.perf_counter()
        res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)
        elapsed_ms = (time_module.perf_counter() - t0) * 1000

        assert len(res) == 744
        assert res["has_forecast"].all()
        assert res["horizon_hours"].min() == 16.5
        assert res["horizon_hours"].max() == 39.5
        # Relaxed performance assertion (< 500ms) to ensure resilience across all platforms
        assert elapsed_ms < 500.0, f"Vectorised execution took {elapsed_ms:.1f}ms (expected < 500ms)"


class TestForecastSelectionBoundariesAndEdgeCases:
    """Testing temporal boundaries, exact cutoff matches, and DST transitions."""

    def test_publish_exactly_at_cutoff_included(self) -> None:
        """
        Protects against: Strict inequality (<) dropping forecasts published exactly at cutoff.
        A forecast published EXACTLY at D-1 09:00:00 must be included (<= condition).
        """
        target = "2026-01-02 12:00:00Z"
        cutoff_exact = "2026-01-01 09:00:00Z"

        df = pd.DataFrame([
            {"startTime": target, "publishTime": "2026-01-01 07:30:00Z", "generation": 10000.0},
            {"startTime": target, "publishTime": cutoff_exact, "generation": 12000.0},
        ])

        res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)

        assert len(res) == 1
        row = res.iloc[0]
        assert row["publishTime"] == pd.Timestamp(cutoff_exact)
        assert row["forecast_mw"] == 12000.0
        assert row["has_forecast"] == True

    def test_forecast_published_after_cutoff_strictly_excluded(self) -> None:
        """
        Protects against: Lookahead bias and information leakage.
        A forecast published 1 second after cutoff MUST be excluded.
        """
        target = "2026-01-02 12:00:00Z"
        cutoff_plus_1s = "2026-01-01 09:00:01Z"

        df = pd.DataFrame([
            {"startTime": target, "publishTime": "2026-01-01 07:30:00Z", "generation": 10000.0},
            {"startTime": target, "publishTime": cutoff_plus_1s, "generation": 15000.0},
        ])

        res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)

        assert len(res) == 1
        row = res.iloc[0]
        assert row["publishTime"] == pd.Timestamp("2026-01-01 07:30:00Z")
        assert row["forecast_mw"] == 10000.0

    def test_duplicate_rows_in_forecasts_input(self) -> None:
        """
        Protects against: Duplicate input rows inflating row counts or causing join explosions.
        """
        target = "2026-01-02 12:00:00Z"
        df = pd.DataFrame([
            {"startTime": target, "publishTime": "2026-01-01 07:30:00Z", "generation": 10000.0},
            {"startTime": target, "publishTime": "2026-01-01 07:30:00Z", "generation": 10000.0},
        ])

        res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)
        assert len(res) == 1
        assert res.iloc[0]["forecast_mw"] == 10000.0

    def test_timezone_aware_boundaries_london(self) -> None:
        """
        Protects against: Daylight saving time errors between GMT (UTC+0) and BST (UTC+1).
        In January, London is GMT (UTC+0), so 09:00 London == 09:00 UTC.
        In July, London is BST (UTC+1), so 09:00 London == 08:00 UTC.
        """
        jan_target = "2026-01-15 12:00:00Z"
        df_jan = pd.DataFrame([{"startTime": jan_target, "publishTime": "2026-01-14 08:30:00Z", "generation": 8000.0}])
        res_jan = select_decision_forecast(df_jan, cutoff_time_of_day="09:00", cutoff_day_offset=1, tz="Europe/London")
        assert res_jan.iloc[0]["cutoff_time"] == pd.Timestamp("2026-01-14 09:00:00", tz="UTC")

        jul_target = "2026-07-15 12:00:00Z"
        df_jul = pd.DataFrame([{"startTime": jul_target, "publishTime": "2026-07-14 07:30:00Z", "generation": 6000.0}])
        res_jul = select_decision_forecast(df_jul, cutoff_time_of_day="09:00", cutoff_day_offset=1, tz="Europe/London")
        # In BST (UTC+1), 09:00 local is 08:00 UTC!
        assert res_jul.iloc[0]["cutoff_time"] == pd.Timestamp("2026-07-14 08:00:00", tz="UTC")

    def test_daylight_saving_transitions_march_and_october(self) -> None:
        """
        Protects against: Clock switch day anomalies (23-hour clock switch in March, 25-hour in October).
        Verifies cutoff calculation on the exact DST transition days:
        - March 29, 2026: Clocks change at 01:00 GMT -> 02:00 BST.
        - October 25, 2026: Clocks change at 02:00 BST -> 01:00 GMT.
        """
        # Delivery on March 29, 2026: Cutoff on D-1 March 28 is still in GMT (09:00 UTC)
        target_march = "2026-03-29 14:00:00Z"
        df_march = pd.DataFrame([
            {"startTime": target_march, "publishTime": "2026-03-28 08:00:00Z", "generation": 9000.0},
        ])
        res_march = select_decision_forecast(df_march, cutoff_time_of_day="09:00", cutoff_day_offset=1, tz="Europe/London")
        assert res_march.iloc[0]["cutoff_time"] == pd.Timestamp("2026-03-28 09:00:00", tz="UTC")

        # Delivery on October 26, 2026 (day after clock change): Cutoff on Oct 25 (DST end day).
        target_oct = "2026-10-26 12:00:00Z"
        df_oct = pd.DataFrame([
            {"startTime": target_oct, "publishTime": "2026-10-25 08:00:00Z", "generation": 7500.0},
        ])
        res_oct = select_decision_forecast(df_oct, cutoff_time_of_day="09:00", cutoff_day_offset=1, tz="Europe/London")
        # On October 25 at 09:00 London time, the clocks have fallen back to GMT (UTC+0)
        assert res_oct.iloc[0]["cutoff_time"] == pd.Timestamp("2026-10-25 09:00:00", tz="UTC")

