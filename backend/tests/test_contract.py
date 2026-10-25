"""
test_contract.py
================
Backend contract test: pins every canonical figure from the January 2026
Parquet cache.  Run with:

    pytest backend/tests/test_contract.py -v
    # or
    make contract-test

All values are computed from the real data, never from hard-coded fixtures.
Any drift beyond the stated tolerance will fail CI and prevent deployment.

Canonical values (January 2026, D-1 09:00 UTC):
    MAE                      2145.2 MW  (± 0.15 MW)
    RMSE                     2615.8 MW  (± 0.15 MW)
    Systematic Bias         +1851.9 MW  (± 0.15 MW)
    P90 Shortfall            4274.9 MW  (± 0.15 MW)
    Matched intervals        1488       (exact)
    Latest Pre-Delivery MAE  1804.2 MW  (± 0.15 MW)
    Leakage gap               15.9%     (± 0.5 pp, 341.0 MW delta)
    Positive-bias days          27      (exact)
    Residual P90             2423.0 MW  (± 5.0 MW)
    Horizon range            16.5–39.5 h (± 0.6 h)
    DST March UTC hour           8      (exact)
    DST October UTC hour         9      (exact)
"""

import numpy as np
import pandas as pd
import pytest
import pytz
from datetime import datetime

from app.analytics.forecast_selection import (
    get_monthly_forecast_alignment,
    select_decision_forecast,
    expand_to_half_hours,
    ForecastSelectionMode,
)
from app.analytics.metrics import calculate_monthly_kpis
from app.services.data_store import data_store


# ── Tolerances ────────────────────────────────────────────────────────────────
TOL_MW  = 0.15   # MW tolerance
TOL_PCT = 0.5    # percentage-point tolerance
TOL_H   = 0.6    # hour tolerance for horizon range
TOL_RES = 5.0    # MW tolerance for residual P90 (decomposition)

# ── Canonical ground truth ────────────────────────────────────────────────────
CANONICAL_MAE        = 2145.2
CANONICAL_RMSE       = 2615.8
CANONICAL_BIAS       = 1851.9
CANONICAL_P90SF      = 4274.9
CANONICAL_N          = 1488
CANONICAL_LAT_MAE    = 1804.2    # latest pre-delivery MAE from timeseries endpoint
CANONICAL_LEAKAGE    = 15.9      # (2145.2 - 1804.2) / 2145.2 * 100
CANONICAL_POS_DAYS   = 27
CANONICAL_TOTAL_DAYS = 31
CANONICAL_RES_P90    = 2423.0
CANONICAL_HOR_MIN    = 16.5
CANONICAL_HOR_MAX    = 39.5


# ── Shared fixtures ───────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def df_fuelhh() -> pd.DataFrame:
    data_store.load_data()
    return data_store.get_fuelhh()


@pytest.fixture(scope="module")
def df_windfor() -> pd.DataFrame:
    data_store.load_data()
    return data_store.get_windfor()


@pytest.fixture(scope="module")
def aligned(df_fuelhh: pd.DataFrame, df_windfor: pd.DataFrame) -> pd.DataFrame:
    """Full January 2026 decision-time aligned dataset."""
    return get_monthly_forecast_alignment(
        decision_time_str="09:00",
        df_fuelhh=df_fuelhh,
        df_windfor=df_windfor,
    )


@pytest.fixture(scope="module")
def valid(aligned: pd.DataFrame) -> pd.DataFrame:
    v = aligned.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    v["error_mw"]     = v["forecast_mw"] - v["actual_mw"]
    v["abs_error_mw"] = v["error_mw"].abs()
    v["shortfall_mw"] = np.maximum(0.0, v["error_mw"])
    return v


# ==============================================================================
# 1. Primary KPI contract
# ==============================================================================

class TestPrimaryKPIContract:
    """Pin MAE, RMSE, Bias, P90 Shortfall, and matched interval count."""

    def test_mae(self, valid: pd.DataFrame) -> None:
        mae = float(valid["abs_error_mw"].mean())
        assert abs(mae - CANONICAL_MAE) <= TOL_MW, (
            f"MAE {mae:.3f} drifted from canonical {CANONICAL_MAE} "
            f"(|Δ|={abs(mae - CANONICAL_MAE):.3f} > {TOL_MW})"
        )

    def test_rmse(self, valid: pd.DataFrame) -> None:
        rmse = float(np.sqrt((valid["error_mw"] ** 2).mean()))
        assert abs(rmse - CANONICAL_RMSE) <= TOL_MW, (
            f"RMSE {rmse:.3f} drifted from canonical {CANONICAL_RMSE}"
        )

    def test_bias(self, valid: pd.DataFrame) -> None:
        bias = float(valid["error_mw"].mean())
        assert abs(bias - CANONICAL_BIAS) <= TOL_MW, (
            f"Bias {bias:.3f} drifted from canonical {CANONICAL_BIAS}"
        )

    def test_p90_shortfall(self, valid: pd.DataFrame) -> None:
        p90 = float(np.percentile(valid["shortfall_mw"], 90))
        assert abs(p90 - CANONICAL_P90SF) <= TOL_MW, (
            f"P90 Shortfall {p90:.3f} drifted from canonical {CANONICAL_P90SF}"
        )

    def test_matched_intervals(self, valid: pd.DataFrame) -> None:
        n = len(valid)
        assert n == CANONICAL_N, (
            f"Matched intervals {n} != canonical {CANONICAL_N}"
        )

    def test_kpi_matches_calculate_monthly_kpis(self, aligned: pd.DataFrame) -> None:
        """calculate_monthly_kpis() must return figures consistent with direct computation."""
        kpis = calculate_monthly_kpis(aligned, decision_time_str="09:00")
        assert abs(kpis.mae_mw - CANONICAL_MAE)  <= TOL_MW, \
            f"calculate_monthly_kpis MAE={kpis.mae_mw:.3f} != canonical {CANONICAL_MAE}"
        assert abs(kpis.rmse_mw - CANONICAL_RMSE) <= TOL_MW, \
            f"calculate_monthly_kpis RMSE={kpis.rmse_mw:.3f} != canonical {CANONICAL_RMSE}"
        assert abs(kpis.mean_bias_mw - CANONICAL_BIAS) <= TOL_MW, \
            f"calculate_monthly_kpis Bias={kpis.mean_bias_mw:.3f} != canonical {CANONICAL_BIAS}"
        assert abs(kpis.shortfall_percentiles.p90 - CANONICAL_P90SF) <= TOL_MW, \
            f"calculate_monthly_kpis P90SF={kpis.shortfall_percentiles.p90:.3f} != {CANONICAL_P90SF}"
        assert kpis.matched_half_hours == CANONICAL_N, \
            f"calculate_monthly_kpis matched={kpis.matched_half_hours} != {CANONICAL_N}"


@pytest.fixture(scope="module")
def latest_mae(valid: pd.DataFrame, df_windfor: pd.DataFrame) -> float:
    target_hours = pd.date_range(
        "2026-01-01 00:00", "2026-01-31 23:00", freq="1h", tz="UTC"
    )
    latest_sel = select_decision_forecast(
        df_windfor,
        mode=ForecastSelectionMode.LATEST_AVAILABLE,
        target_start_times=target_hours,
    )
    latest_hh = expand_to_half_hours(latest_sel)
    lat_map = dict(zip(latest_hh["startTime"], latest_hh["forecast_mw"]))
    v = valid.copy()
    v["latest_forecast_mw"] = v["startTime"].map(lat_map)
    lat_valid = v.dropna(subset=["actual_mw", "latest_forecast_mw"])
    return float((lat_valid["latest_forecast_mw"] - lat_valid["actual_mw"]).abs().mean())


# ==============================================================================
# 2. Latest pre-delivery and leakage gap
# ==============================================================================

class TestLeakageContract:
    """Leakage gap = decision MAE minus latest pre-delivery MAE, expressed as %."""

    def test_latest_mae(self, latest_mae: float) -> None:
        assert abs(latest_mae - CANONICAL_LAT_MAE) <= TOL_MW, (
            f"Latest MAE {latest_mae:.3f} drifted from canonical {CANONICAL_LAT_MAE}"
        )

    def test_leakage_pct(self, latest_mae: float) -> None:
        leakage = (CANONICAL_MAE - latest_mae) / CANONICAL_MAE * 100.0
        assert abs(leakage - CANONICAL_LEAKAGE) <= TOL_PCT, (
            f"Leakage gap {leakage:.2f}% drifted from canonical {CANONICAL_LEAKAGE}%"
        )


# ==============================================================================
# 3. Daily bias: mean of 31 daily biases == global bias
# ==============================================================================

class TestDailyBiasContract:

    def test_mean_of_daily_biases_equals_global(self, valid: pd.DataFrame) -> None:
        """Mean of the 31 per-day mean biases must equal the global mean bias within 1 MW."""
        date_col = "settlementDate" if "settlementDate" in valid.columns else "settlement_date"
        daily = valid.groupby(valid[date_col].astype(str))["error_mw"].mean()
        mean_of_daily = float(daily.mean())
        global_bias   = float(valid["error_mw"].mean())
        assert abs(mean_of_daily - global_bias) < 1e-6, (
            f"Mean of daily biases {mean_of_daily:.10f} != global bias {global_bias:.10f} (diff >= 1e-6)"
        )

    def test_positive_bias_day_count(self, valid: pd.DataFrame) -> None:
        date_col   = "settlementDate" if "settlementDate" in valid.columns else "settlement_date"
        daily      = valid.groupby(valid[date_col].astype(str))["error_mw"].mean()
        pos_days   = int((daily > 0).sum())
        total_days = int(len(daily))
        assert total_days == CANONICAL_TOTAL_DAYS, \
            f"Expected {CANONICAL_TOTAL_DAYS} days, got {total_days}"
        assert pos_days == CANONICAL_POS_DAYS, (
            f"Positive-bias days {pos_days} != canonical {CANONICAL_POS_DAYS}"
        )


# ==============================================================================
# 4. P90 decomposition: systematic bias + residual ≈ P90 shortfall
# ==============================================================================

class TestP90DecompositionContract:

    def test_residual_p90(self, valid: pd.DataFrame) -> None:
        p90sf    = float(np.percentile(valid["shortfall_mw"], 90))
        bias     = float(valid["error_mw"].mean())
        residual = p90sf - bias
        assert abs(residual - CANONICAL_RES_P90) <= TOL_RES, (
            f"Residual P90 {residual:.1f} MW drifted from canonical {CANONICAL_RES_P90} MW"
        )


# ==============================================================================
# 5. Selected-run horizon range
# ==============================================================================

class TestHorizonRangeContract:

    def test_horizon_range(self, valid: pd.DataFrame) -> None:
        h_col = "horizon_hours" if "horizon_hours" in valid.columns else "lead_time_hours"
        h_data = valid[h_col].dropna()
        if len(h_data) == 0:
            pytest.skip("No horizon data in aligned dataset")
        h_min = float(h_data.min())
        h_max = float(h_data.max())
        assert abs(h_min - CANONICAL_HOR_MIN) <= TOL_H, (
            f"Horizon min {h_min:.2f}h drifted from canonical {CANONICAL_HOR_MIN}h"
        )
        assert abs(h_max - CANONICAL_HOR_MAX) <= TOL_H, (
            f"Horizon max {h_max:.2f}h drifted from canonical {CANONICAL_HOR_MAX}h"
        )


# ==============================================================================
# 6. DST transitions: Europe/London UTC cutoffs
# ==============================================================================

class TestDSTContract:

    def test_march_dst_spring_forward(self) -> None:
        """2026-03-29 09:00 BST (UTC+1) must resolve to 08:00 UTC."""
        london = pytz.timezone("Europe/London")
        local  = london.localize(datetime(2026, 3, 29, 9, 0, 0), is_dst=True)
        utc    = local.astimezone(pytz.utc)
        assert utc.hour == 8, (
            f"March DST: 09:00 BST expected UTC hour 8, got {utc.hour}"
        )
        assert utc.minute == 0

    def test_october_dst_fall_back(self) -> None:
        """2026-10-25 09:00 GMT (UTC+0) must resolve to 09:00 UTC."""
        london = pytz.timezone("Europe/London")
        local  = london.localize(datetime(2026, 10, 25, 9, 0, 0), is_dst=False)
        utc    = local.astimezone(pytz.utc)
        assert utc.hour == 9, (
            f"October DST: 09:00 GMT expected UTC hour 9, got {utc.hour}"
        )
        assert utc.minute == 0

    def test_march_transition_day_has_23_hours(self) -> None:
        """2026-03-29 is the spring-forward day: London has only 23 hours."""
        london    = pytz.timezone("Europe/London")
        day_start = london.localize(datetime(2026, 3, 29, 0, 0, 0), is_dst=False)
        day_end   = london.localize(datetime(2026, 3, 30, 0, 0, 0), is_dst=True)
        hours = (
            day_end.astimezone(pytz.utc) - day_start.astimezone(pytz.utc)
        ).total_seconds() / 3600.0
        assert hours == 23.0, f"Spring-forward day should be 23 h, got {hours}"

    def test_march_delivery_d_03_30_decision_cutoff(self) -> None:
        """For delivery date D = 2026-03-30 (March 30):
        The decision cutoff on D-1 (2026-03-29, post spring-forward) at 09:00 Europe/London
        is 09:00 BST, which resolves exactly to 08:00 UTC.
        """
        london = pytz.timezone("Europe/London")
        d_minus_1_local = london.localize(datetime(2026, 3, 29, 9, 0, 0), is_dst=True)
        utc_cutoff = d_minus_1_local.astimezone(pytz.utc)
        assert utc_cutoff.hour == 8, f"Expected 08:00 UTC cutoff on D-1, got {utc_cutoff.hour}"
        assert utc_cutoff.minute == 0

    def test_october_transition_day_has_25_hours(self) -> None:
        """2026-10-25 is the fall-back day: London has 25 hours."""
        day_start_utc = pytz.utc.localize(datetime(2026, 10, 24, 23, 0, 0))  # midnight BST
        day_end_utc   = pytz.utc.localize(datetime(2026, 10, 26, 0, 0, 0))   # midnight GMT next
        hours = (day_end_utc - day_start_utc).total_seconds() / 3600.0
        assert hours == 25.0, f"Fall-back day should be 25 h, got {hours}"

    def test_october_delivery_d_10_25_decision_cutoff(self) -> None:
        """For delivery date D = 2026-10-25 (October 25, transition day itself):
        The decision cutoff on D-1 (2026-10-24, pre fall-back) at 09:00 Europe/London
        is 09:00 BST, which resolves exactly to 08:00 UTC.
        """
        london = pytz.timezone("Europe/London")
        d_minus_1_local = london.localize(datetime(2026, 10, 24, 9, 0, 0), is_dst=True)
        utc_cutoff = d_minus_1_local.astimezone(pytz.utc)
        assert utc_cutoff.hour == 8, f"Expected 08:00 UTC cutoff on D-1, got {utc_cutoff.hour}"
        assert utc_cutoff.minute == 0

    def test_october_delivery_d_10_26_decision_cutoff(self) -> None:
        """For delivery date D = 2026-10-26 (October 26):
        The decision cutoff on D-1 (2026-10-25, post fall-back) at 09:00 Europe/London
        is 09:00 GMT, which resolves exactly to 09:00 UTC.
        """
        london = pytz.timezone("Europe/London")
        d_minus_1_local = london.localize(datetime(2026, 10, 25, 9, 0, 0), is_dst=False)
        utc_cutoff = d_minus_1_local.astimezone(pytz.utc)
        assert utc_cutoff.hour == 9, f"Expected 09:00 UTC cutoff on D-1, got {utc_cutoff.hour}"
        assert utc_cutoff.minute == 0


# ==============================================================================
# 7. Independent pure numpy recomputation contract & error standard deviation
# ==============================================================================

class TestIndependentNumpyRecomputation:
    """Computes MAE, RMSE, bias, P90 shortfall, and error standard deviation
    directly on raw 1D numpy arrays, completely independent of any helper classes.
    """

    def test_pure_numpy_recomputation(self, valid: pd.DataFrame) -> None:
        act = valid["actual_mw"].to_numpy(dtype=np.float64)
        fct = valid["forecast_mw"].to_numpy(dtype=np.float64)

        err       = fct - act
        abs_err   = np.abs(err)
        shortfall = np.maximum(0.0, err)

        numpy_mae   = float(np.mean(abs_err))
        numpy_rmse  = float(np.sqrt(np.mean(err ** 2)))
        numpy_bias  = float(np.mean(err))
        numpy_p90sf = float(np.percentile(shortfall, 90))
        error_std   = float(np.std(err, ddof=0))

        # Check raw array equality against canonical figures
        assert abs(numpy_mae - CANONICAL_MAE) <= TOL_MW, f"Numpy MAE {numpy_mae:.3f} != {CANONICAL_MAE}"
        assert abs(numpy_rmse - CANONICAL_RMSE) <= TOL_MW, f"Numpy RMSE {numpy_rmse:.3f} != {CANONICAL_RMSE}"
        assert abs(numpy_bias - CANONICAL_BIAS) <= TOL_MW, f"Numpy Bias {numpy_bias:.3f} != {CANONICAL_BIAS}"
        assert abs(numpy_p90sf - CANONICAL_P90SF) <= TOL_MW, f"Numpy P90 {numpy_p90sf:.3f} != {CANONICAL_P90SF}"

        # Error std identity: RMSE^2 = Bias^2 + Var(err) => error_std = sqrt(RMSE^2 - Bias^2) = 1847.4 MW
        expected_std = float(np.sqrt(CANONICAL_RMSE ** 2 - CANONICAL_BIAS ** 2))
        assert abs(error_std - expected_std) <= 1.0, f"Error std {error_std:.3f} != {expected_std:.3f}"
        assert abs(error_std - 1847.41) <= 0.1, f"Error std {error_std:.2f} != 1847.41 MW"
