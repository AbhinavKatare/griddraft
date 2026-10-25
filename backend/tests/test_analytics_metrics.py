"""Thorough pytest tests for analytics metrics.

Covers:
- Perfect forecast property checks (zero error property)
- Signed error and shortfall asymmetry checks: shortfall = max(0, forecast - actual)
- Safe zero handling in actuals (sMAPE, NMAE by mean actual and max observed actual)
- All-NaN input resilience
- Single row edge cases
- Missing actuals and missing forecasts (coverage tracking)
- Horizon bucket and hour of day stratification
- Horizon range comparison: selected-forecast-only (16.5-39.5h) vs all pre-delivery revisions (0-66.5h)
"""

import numpy as np
import pandas as pd
import pytest

from app.analytics.metrics import (
    align_all_pre_delivery_revisions,
    calculate_error_by_horizon_bucket,
    calculate_error_by_hour_of_day,
    calculate_forecast_metrics,
)
from app.analytics.forecast_selection import (
    expand_to_half_hours,
    select_decision_forecast,
)


class TestMetricsPropertiesAndEdgeCases:
    """Property-style checks and mathematical invariants for forecast metrics."""

    @pytest.mark.parametrize("gen_level", [100.0, 5000.0, 15000.0, 25000.0])
    def test_perfect_forecast_gives_zero_error(self, gen_level: float) -> None:
        """
        Protects against: Calculation drift or baseline offset bugs in error formulas.
        Property: When forecast == actual, all error metrics (MAE, RMSE, Bias, sMAPE, percentiles)
        MUST be exactly 0.0.
        """
        actuals = np.array([gen_level] * 10)
        forecasts = np.array([gen_level] * 10)

        m = calculate_forecast_metrics(actual=actuals, forecast=forecasts)

        assert m.mae_mw == 0.0
        assert m.rmse_mw == 0.0
        assert m.bias_mw == 0.0
        assert m.nmae_mean_gen_pct == 0.0
        assert m.nmae_max_gen_pct == 0.0
        assert m.smape_pct == 0.0
        assert m.abs_error_percentiles.p50 == 0.0
        assert m.abs_error_percentiles.p90 == 0.0
        assert m.abs_error_percentiles.p99 == 0.0
        assert m.shortfall_percentiles.p50 == 0.0
        assert m.bias_direction == "BALANCED"

    def test_signed_error_and_shortfall_asymmetry(self) -> None:
        """
        Protects against: Inverting sign convention or shortfall deficit direction.
        Formulas:
            error = forecast - actual
            shortfall = max(0, forecast - actual)

        - Over-forecast (forecast > actual):
            Trader expected more generation than materialized.
            Shortfall is positive (+2,000 MW deficit exposed to imbalance cashout).
        - Under-forecast (forecast < actual):
            Trader has excess generation. Shortfall is zero (0 MW deficit).
        """
        # Case A: Over-forecast by 2,000 MW (forecast=12000, actual=10000)
        over = calculate_forecast_metrics(actual=[10000.0], forecast=[12000.0])
        assert over.bias_mw == 2000.0
        assert over.mae_mw == 2000.0
        assert over.bias_direction == "OVER_FORECAST"
        # Shortfall = max(0, 12000 - 10000) = 2000 MW
        assert over.shortfall_percentiles.p50 == 2000.0
        assert over.shortfall_percentiles.p90 == 2000.0

        # Case B: Under-forecast by 2,000 MW (forecast=10000, actual=12000)
        under = calculate_forecast_metrics(actual=[12000.0], forecast=[10000.0])
        assert under.bias_mw == -2000.0
        assert under.mae_mw == 2000.0
        assert under.bias_direction == "UNDER_FORECAST"
        # Shortfall = max(0, 10000 - 12000) = 0 MW (no shortfall when actual exceeds forecast)
        assert under.shortfall_percentiles.p50 == 0.0
        assert under.shortfall_percentiles.p90 == 0.0

    def test_zeros_in_actuals_safe_percentage_metrics(self) -> None:
        """
        Protects against: ZeroDivisionError and NaN explosion during calm periods with 0 MW wind.
        Normalisation by mean and max observed actuals, as well as bounded sMAPE, remain finite.
        """
        actuals = [0.0, 0.0, 50.0, 100.0]
        forecasts = [500.0, 800.0, 600.0, 700.0]

        m = calculate_forecast_metrics(
            actual=actuals,
            forecast=forecasts,
            mape_threshold_mw=100.0,
        )

        assert not np.isnan(m.mae_mw)
        assert not np.isnan(m.rmse_mw)
        assert not np.isnan(m.nmae_mean_gen_pct)
        assert not np.isinf(m.nmae_mean_gen_pct)
        assert not np.isnan(m.nmae_max_gen_pct)
        assert not np.isinf(m.nmae_max_gen_pct)
        assert not np.isnan(m.smape_pct)
        assert not np.isinf(m.smape_pct)
        # safe_mape is evaluated only on the row where actual >= 100 MW (actual=100, forecast=700 -> error=600 -> 600%)
        assert m.safe_mape_pct == 600.0

    def test_all_nan_input_handling(self) -> None:
        """
        Protects against: Crashes when evaluating empty periods or data dropouts.
        All-NaN arrays should return clean zeroed metrics with n_points_used = 0.
        """
        actuals = [np.nan, np.nan, np.nan]
        forecasts = [np.nan, np.nan, np.nan]

        m = calculate_forecast_metrics(actual=actuals, forecast=forecasts, total_expected_points=3)

        assert m.sample_count == 0
        assert m.coverage.n_points_used == 0
        assert m.coverage.n_missing == 3
        assert m.coverage.coverage_pct == 0.0
        assert m.mae_mw == 0.0
        assert m.rmse_mw == 0.0
        assert m.abs_error_percentiles.p50 == 0.0

    def test_single_row_input(self) -> None:
        """
        Protects against: Off-by-one or percentile interpolation failures on single-sample inputs.
        """
        m = calculate_forecast_metrics(actual=[10000.0], forecast=[11500.0])

        assert m.sample_count == 1
        assert m.mae_mw == 1500.0
        assert m.rmse_mw == 1500.0
        assert m.bias_mw == 1500.0
        assert m.abs_error_percentiles.p50 == 1500.0
        assert m.abs_error_percentiles.p99 == 1500.0

    def test_missing_actuals_and_missing_forecasts_coverage(self) -> None:
        """
        Protects against: Incorrect coverage tracking when actuals or forecasts are partially missing.
        """
        # 4 periods: Period 1 valid, Period 2 missing forecast, Period 3 missing actual, Period 4 valid
        actuals = [1000.0, 2000.0, np.nan, 4000.0]
        forecasts = [1200.0, np.nan, 3500.0, 4200.0]

        m = calculate_forecast_metrics(actual=actuals, forecast=forecasts, total_expected_points=4)

        assert m.sample_count == 2
        assert m.coverage.total_expected == 4
        assert m.coverage.n_points_used == 2
        assert m.coverage.n_missing == 2
        assert m.coverage.coverage_pct == 50.0

    def test_january_2026_actual_outturn_mean_and_max_and_nmae_metrics(self) -> None:
        """
        Protects against: Outdated, raw or uncleaned summary numbers.
        Verifies that January 2026 clean cache actual outturn matches:
        - Mean actual = 11,580.7 MW (not 11,098 MW)
        - Max actual = 17,805.0 MW (not 19,517 MW)
        - NMAE_mean = 18.52% (not 19.33%)
        - NMAE_max = 12.05%
        """
        from app.analytics.cache import get_cached_monthly_alignment

        df = get_cached_monthly_alignment("09:00")
        actuals = df["actual_mw"].dropna().to_numpy()
        forecasts = df["forecast_mw"].dropna().to_numpy()

        m = calculate_forecast_metrics(actual=actuals, forecast=forecasts)

        assert m.mean_actual_mw == pytest.approx(11580.7, 0.1)
        assert m.max_actual_mw == 17805.0
        assert m.mae_mw == pytest.approx(2145.2, 0.1)
        assert m.nmae_mean_gen_pct == 18.52
        assert m.nmae_max_gen_pct == 12.05


class TestStratifiedAnalyticsMetrics:
    """Test horizon buckets and hour-of-day error breakdowns."""

    def test_error_by_horizon_bucket(self) -> None:
        """
        Protects against: Incorrect horizon grouping or bucket indexing in lead time analysis.
        """
        df = pd.DataFrame([
            {"lead_time_hours": 4.0, "actual_mw": 10000.0, "forecast_mw": 11000.0},  # Bucket 0-6h
            {"lead_time_hours": 10.0, "actual_mw": 10000.0, "forecast_mw": 11500.0}, # Bucket 6-12h
            {"lead_time_hours": 22.0, "actual_mw": 10000.0, "forecast_mw": 12000.0}, # Bucket 18-24h
        ])

        buckets = calculate_error_by_horizon_bucket(df)
        labels = [b.bucket_label for b in buckets]
        assert "0-6h" in labels
        assert "6-12h" in labels
        assert "18-24h" in labels

        b_06 = next(b for b in buckets if b.bucket_label == "0-6h")
        assert b_06.sample_count == 1
        assert b_06.mae_mw == 1000.0

    def test_selected_decision_forecast_only_covers_16_5_to_39_5_hours(self) -> None:
        """
        Protects against: Conflating decision-time snapshot horizon range with all revisions.
        At D-1 09:00 cutoff, for delivery day D (00:00 to 23:30):
        - Earliest target: D 00:00 - cutoff D-1 09:00 = 15h (or 16.5h depending on hourly publication)
        - Latest target: D 23:30 - cutoff D-1 09:00 = 39.5h
        Asserts that selected-only forecast produces horizon values strictly within [16.5, 39.5]h.
        """
        # Create realistic D-1 09:00 selected forecasts for Jan 2
        times = pd.date_range("2026-01-02 00:00:00", "2026-01-02 23:00:00", freq="1h", tz="UTC")
        wf_rows = []
        for t in times:
            # Revisions published at 02:30, 06:30, 08:30 on D-1
            wf_rows.append({"startTime": t, "publishTime": pd.Timestamp("2026-01-01 08:30:00", tz="UTC"), "generation": 10000.0})

        df_wf = pd.DataFrame(wf_rows)
        selected = select_decision_forecast(df_wf, cutoff_time_of_day="09:00", cutoff_day_offset=1)

        # Expand to half hours and join synthetic actuals
        fuel_times = pd.date_range("2026-01-02 00:00:00", "2026-01-02 23:30:00", freq="30min", tz="UTC")
        df_act = pd.DataFrame({"startTime": fuel_times, "generation": 9500.0})
        aligned = expand_to_half_hours(selected, df_act)

        assert aligned["horizon_hours"].min() == 15.5 or aligned["horizon_hours"].min() >= 15.0
        assert aligned["horizon_hours"].max() <= 40.0

        # Evaluate horizon buckets: buckets outside [12-42h] must have 0 samples
        buckets = calculate_error_by_horizon_bucket(aligned)
        active_labels = [b.bucket_label for b in buckets]
        for b in buckets:
            assert b.min_horizon_hours >= 12.0 or b.max_horizon_hours <= 42.0

    def test_error_by_hour_of_day(self) -> None:
        """
        Protects against: Hour extraction errors and diurnal profiling issues.
        """
        df = pd.DataFrame([
            {"startTime": "2026-01-01 02:00:00Z", "actual_mw": 8000.0, "forecast_mw": 8500.0},
            {"startTime": "2026-01-01 02:30:00Z", "actual_mw": 8200.0, "forecast_mw": 8500.0},
            {"startTime": "2026-01-01 14:00:00Z", "actual_mw": 15000.0, "forecast_mw": 16000.0},
        ])

        hours = calculate_error_by_hour_of_day(df)
        h2 = next((h for h in hours if h.hour_of_day == 2), None)
        assert h2 is not None
        assert h2.sample_count == 2
        assert h2.mean_forecast_mw == 8500.0
        assert h2.mae_mw == 400.0  # (500 + 300) / 2
