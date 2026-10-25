"""Unit tests for quantitative risk analytics, buffer decomposition, and backtest coverage."""

import numpy as np
import pandas as pd
import pytest

from app.analytics.risk import (
    calculate_safe_wind_profile,
    compute_safe_wind_quantity,
    compute_thermal_procurement_quantity,
    decompose_shortfall_buffer,
)


def test_compute_safe_wind_quantity() -> None:
    """Test pure function calculating safe wind floored at zero."""
    # When forecast exceeds buffer: safe wind = forecast - buffer
    assert compute_safe_wind_quantity(forecast_mw=10000.0, shortfall_quantile_mw=4000.0) == 6000.0

    # When forecast is lower than buffer: floored at 0.0 MW
    assert compute_safe_wind_quantity(forecast_mw=3000.0, shortfall_quantile_mw=4000.0) == 0.0

    # When forecast is exactly equal to buffer
    assert compute_safe_wind_quantity(forecast_mw=4000.0, shortfall_quantile_mw=4000.0) == 0.0


def test_compute_thermal_procurement_quantity() -> None:
    """Test pure function calculating implied backup thermal capacity."""
    # When forecast exceeds buffer: thermal backup is capped at buffer
    assert compute_thermal_procurement_quantity(forecast_mw=10000.0, shortfall_quantile_mw=4000.0) == 4000.0

    # When forecast is lower than buffer: thermal procurement is exactly equal to forecast
    assert compute_thermal_procurement_quantity(forecast_mw=2500.0, shortfall_quantile_mw=4000.0) == 2500.0

    # Identity check: safe_wind + thermal_procurement MUST equal original forecast
    for fc in [1000.0, 4000.0, 7500.0, 15000.0]:
        sw = compute_safe_wind_quantity(fc, 4000.0)
        tp = compute_thermal_procurement_quantity(fc, 4000.0)
        assert sw + tp == fc


def test_buffer_decomposition() -> None:
    """Test mathematical decomposition of total buffer into systematic bias and stochastic residual."""
    shortfalls = np.array([1000.0, 2000.0, 3000.0, 4000.0, 5000.0])
    decomp = decompose_shortfall_buffer(shortfalls, quantile=0.90)

    # Mean = 3000.0 MW, P90 = 4600.0 MW
    assert decomp.systematic_bias_mw == 3000.0
    assert decomp.total_buffer_mw == 4600.0
    assert decomp.residual_quantile_mw == 1600.0
    assert decomp.total_buffer_mw == pytest.approx(decomp.systematic_bias_mw + decomp.residual_quantile_mw)


def test_calculate_safe_wind_profile_with_historical_shortfall() -> None:
    """Test profile calculation across periods with user-specified shortfall sample."""
    # Historical shortfalls: [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000]
    shortfalls = np.linspace(1000.0, 10000.0, 10)

    df_fc = pd.DataFrame([
        {"startTime": "2026-01-15T00:00:00Z", "settlementPeriod": 1, "forecast_mw": 12000.0},
        {"startTime": "2026-01-15T00:30:00Z", "settlementPeriod": 2, "forecast_mw": 5000.0},
    ])

    summary = calculate_safe_wind_profile(
        target_forecasts_df=df_fc,
        quantile=0.90,
        historical_shortfalls=shortfalls,
    )

    assert summary.quantile == 0.90
    assert summary.shortfall_quantile_mw == pytest.approx(9100.0, 1.0)
    assert len(summary.periods) == 2
    assert summary.decomposition.total_buffer_mw == pytest.approx(9100.0, 1.0)

    # Period 1: Forecast 12,000 MW, Buffer 9,100 MW -> Safe Wind = 2,900 MW, Thermal = 9,100 MW
    p1 = summary.periods[0]
    assert p1.forecast_mw == 12000.0
    assert p1.safe_wind_mw == pytest.approx(2900.0, 1.0)
    assert p1.thermal_procurement_mw == pytest.approx(9100.0, 1.0)

    # Period 2: Forecast 5,000 MW, Buffer 9,100 MW -> Floored Safe Wind = 0.0 MW, Thermal = 5,000 MW
    p2 = summary.periods[1]
    assert p2.forecast_mw == 5000.0
    assert p2.safe_wind_mw == 0.0
    assert p2.thermal_procurement_mw == 5000.0

    # Total energy: (12000 + 5000) * 0.5h = 8,500 MWh
    assert summary.total_forecast_mwh == 8500.0
    assert summary.total_safe_wind_mwh + summary.total_thermal_procurement_mwh == 8500.0


def test_safe_wind_backtest_coverage() -> None:
    """Test empirical backtest evaluation when actual generation is present."""
    # Forecasts: [10000, 10000], Actuals: [8000, 5000], Buffer: 3000 MW -> Safe wind: 7000 MW
    # Period 1: Actual 8000 >= Safe Wind 7000 -> Covered! (No breach)
    # Period 2: Actual 5000 < Safe Wind 7000 -> Breached by 2000 MW!
    df = pd.DataFrame([
        {"startTime": "2026-01-15T00:00:00Z", "settlementPeriod": 1, "forecast_mw": 10000.0, "actual_mw": 8000.0},
        {"startTime": "2026-01-15T00:30:00Z", "settlementPeriod": 2, "forecast_mw": 10000.0, "actual_mw": 5000.0},
    ])

    summary = calculate_safe_wind_profile(
        target_forecasts_df=df,
        quantile=0.90,
        historical_shortfalls=[3000.0],
    )

    assert summary.backtest is not None
    assert summary.backtest.total_evaluated_periods == 2
    assert summary.backtest.breach_count == 1
    assert summary.backtest.empirical_coverage_pct == 50.0
    assert summary.backtest.max_breach_mw == 2000.0


def test_prior_days_toggle() -> None:
    """Test prior_days mode evaluates only strictly earlier settlement dates."""
    # Historical days: Jan 1 and Jan 2
    history_df = pd.DataFrame([
        {"settlementDate": "2026-01-01", "forecast_mw": 10000.0, "actual_mw": 8000.0}] * 48 +
        [{"settlementDate": "2026-01-02", "forecast_mw": 10000.0, "actual_mw": 5000.0}] * 48
    )

    # Target day: Jan 2. Prior days should strictly use Jan 1 shortfalls (2000 MW)!
    target_df = pd.DataFrame([
        {"settlementDate": "2026-01-02", "startTime": "2026-01-02T12:00:00Z", "forecast_mw": 12000.0}
    ])

    summary = calculate_safe_wind_profile(
        target_forecasts_df=target_df,
        quantile=0.90,
        mode="prior_days",
        full_history_df=history_df,
    )

    # In Jan 1, shortfall is 10000 - 8000 = 2000 MW. Buffer must be 2000 MW!
    assert summary.shortfall_quantile_mw == 2000.0
    assert summary.periods[0].safe_wind_mw == 10000.0


def test_empty_dataframe_safe_wind() -> None:
    """Test resilience when empty forecast dataframe is supplied."""
    empty_df = pd.DataFrame(columns=["startTime", "forecast_mw"])
    summary = calculate_safe_wind_profile(empty_df)

    assert summary.total_forecast_mwh == 0.0
    assert summary.total_safe_wind_mwh == 0.0
    assert summary.periods == []
