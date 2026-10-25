"""Unit tests for quantitative trading metrics and risk calculations."""

import numpy as np
import pandas as pd
import pytest

from app.analytics.metrics import (
    calculate_daily_metrics,
    calculate_error_distribution,
    calculate_hourly_profile,
    calculate_monthly_kpis,
)


@pytest.fixture
def sample_aligned_dataframe() -> pd.DataFrame:
    """Fixture with known errors to verify exact analytical calculations."""
    data = [
        # actual, forecast -> error = forecast - actual, abs_error, shortfall
        # row 1: 1000, 1200 -> err = +200, abs = 200, shortfall = 200
        {"startTime": pd.Timestamp("2026-01-01 00:00:00", tz="UTC"), "settlementDate": "2026-01-01", "settlementPeriod": 1, "actual_mw": 1000.0, "forecast_mw": 1200.0, "error_mw": 200.0, "abs_error_mw": 200.0, "shortfall_mw": 200.0},
        # row 2: 2000, 1800 -> err = -200, abs = 200, shortfall = 0
        {"startTime": pd.Timestamp("2026-01-01 00:30:00", tz="UTC"), "settlementDate": "2026-01-01", "settlementPeriod": 2, "actual_mw": 2000.0, "forecast_mw": 1800.0, "error_mw": -200.0, "abs_error_mw": 200.0, "shortfall_mw": 0.0},
        # row 3: 3000, 3600 -> err = +600, abs = 600, shortfall = 600
        {"startTime": pd.Timestamp("2026-01-02 00:00:00", tz="UTC"), "settlementDate": "2026-01-02", "settlementPeriod": 1, "actual_mw": 3000.0, "forecast_mw": 3600.0, "error_mw": 600.0, "abs_error_mw": 600.0, "shortfall_mw": 600.0},
        # row 4: 4000, 3400 -> err = -600, abs = 600, shortfall = 0
        {"startTime": pd.Timestamp("2026-01-02 00:30:00", tz="UTC"), "settlementDate": "2026-01-02", "settlementPeriod": 2, "actual_mw": 4000.0, "forecast_mw": 3400.0, "error_mw": -600.0, "abs_error_mw": 600.0, "shortfall_mw": 0.0},
    ]
    return pd.DataFrame(data)


def test_calculate_monthly_kpis(sample_aligned_dataframe: pd.DataFrame) -> None:
    """Test monthly KPIs against exact known values."""
    kpis = calculate_monthly_kpis(sample_aligned_dataframe, decision_time_str="09:00")

    # Errors: [200, -200, 600, -600]
    # Abs errors: [200, 200, 600, 600] -> Mean = 400.0 MW
    assert kpis.mae_mw == 400.0

    # Squared errors: [40000, 40000, 360000, 360000] -> Mean = 200000 -> RMSE = sqrt(200000) = 447.2 MW
    assert kpis.rmse_mw == pytest.approx(447.2, 0.1)

    # Bias: (200 - 200 + 600 - 600) / 4 = 0.0 MW
    assert kpis.mean_bias_mw == 0.0

    # Mean actual = (1000 + 2000 + 3000 + 4000) / 4 = 2500 MW
    assert kpis.mean_actual_mw == 2500.0
    # MAE % of mean gen = 400 / 2500 * 100 = 16.0%
    assert kpis.mae_pct_of_mean_gen == 16.0

    # Max actual = 4000 MW -> MAE % of max gen = 400 / 4000 * 100 = 10.0%
    assert kpis.mae_pct_of_max_gen == 10.0

    # Percentiles of abs errors: [200, 200, 600, 600] -> median is 400
    assert kpis.abs_error_percentiles.p50 == 400.0
    assert kpis.abs_error_percentiles.p90 > 400.0


def test_calculate_daily_metrics(sample_aligned_dataframe: pd.DataFrame) -> None:
    """Test daily aggregation for Jan 1 and Jan 2."""
    daily = calculate_daily_metrics(sample_aligned_dataframe)
    assert len(daily) == 2

    jan1 = daily[0]
    assert jan1.delivery_date == "2026-01-01"
    # Abs errors on Jan 1: [200, 200] -> MAE = 200
    assert jan1.mae_mw == 200.0
    assert jan1.rmse_mw == 200.0
    assert jan1.mean_bias_mw == 0.0

    jan2 = daily[1]
    assert jan2.delivery_date == "2026-01-02"
    # Abs errors on Jan 2: [600, 600] -> MAE = 600
    assert jan2.mae_mw == 600.0


def test_calculate_hourly_profile(sample_aligned_dataframe: pd.DataFrame) -> None:
    """Test settlement period profile across periods 1 and 2."""
    profile = calculate_hourly_profile(sample_aligned_dataframe)
    assert len(profile) == 2

    p1 = profile[0]
    assert p1.settlement_period == 1
    assert p1.period_start_time == "00:00"
    # Actuals for p1: 1000 and 3000 -> Mean = 2000
    assert p1.mean_actual_mw == 2000.0
    # Forecasts for p1: 1200 and 3600 -> Mean = 2400
    assert p1.mean_forecast_mw == 2400.0
    assert p1.mean_bias_mw == 400.0

    p2 = profile[1]
    assert p2.settlement_period == 2
    assert p2.period_start_time == "00:30"
    assert p2.mean_bias_mw == -400.0


def test_calculate_error_distribution(sample_aligned_dataframe: pd.DataFrame) -> None:
    """Test error distribution binning."""
    buckets = calculate_error_distribution(sample_aligned_dataframe, bin_size_mw=500.0)
    assert len(buckets) > 0
    total_pct = sum(b.percentage for b in buckets)
    assert total_pct == pytest.approx(100.0, 0.5)
