"""Quantitative trading analytics and forecast accuracy metrics.

Features:
- Error definition: signed error = forecast - actual
- Shortfall error: shortfall = max(0, forecast - actual) (trader deficit when generation falls short of forecast)
- Primary metrics: MAE, RMSE, Bias (mean signed error)
- Safe percentage metrics:
  * NMAE Mean Gen: MAE / mean(actual)
  * NMAE Max Gen: MAE / max(actual)
  * sMAPE: Symmetric MAPE bounded in [0, 200%]
  * Safe MAPE: Masked MAPE evaluated strictly where actual >= threshold (e.g. 100 MW)
- Error percentiles: P50, P90, P95, P99 for absolute error and signed shortfall
- Coverage tracking: total expected, n used, n missing, coverage %
- Stratified breakdowns: error by forecast horizon bucket and error by hour of day (0-23)
- High-level aggregators: monthly KPIs, daily breakdown, hourly profiles, and error distributions
- Return values: typed Pydantic models
"""

from datetime import date
import logging
from typing import Any, Dict, List, Optional, Sequence
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

from app.config import settings
from app.models.schemas import (
    DailyMetricPoint,
    ErrorDistributionBucket,
    HorizonPoint,
    HourlyProfilePoint,
    MonthlyKPIs,
    Percentiles,
)

logger = logging.getLogger(__name__)


# ==============================================================================
# Typed Return Models
# ==============================================================================

class PercentilesResult(BaseModel):
    """P50, P90, P95, and P99 percentiles."""

    p50: float = Field(..., description="50th percentile (Median)")
    p90: float = Field(..., description="90th percentile")
    p95: float = Field(..., description="95th percentile")
    p99: float = Field(..., description="99th percentile")


class CoverageCount(BaseModel):
    """Data completeness and sample counts."""

    total_expected: int = Field(..., description="Total theoretical intervals in evaluation window")
    n_points_used: int = Field(..., description="Number of valid matched forecast-actual pairs")
    n_missing: int = Field(..., description="Number of intervals missing forecast or actual")
    coverage_pct: float = Field(..., description="Percentage of valid data coverage (0 - 100%)")


class ForecastMetricsSummary(BaseModel):
    """Comprehensive summary of forecast accuracy and risk metrics."""

    sample_count: int
    mean_actual_mw: float
    mean_forecast_mw: float
    max_actual_mw: float
    max_forecast_mw: float
    mae_mw: float
    rmse_mw: float
    bias_mw: float = Field(..., description="Signed mean error = forecast - actual")
    bias_direction: str = Field(..., description="'OVER_FORECAST' (long risk), 'UNDER_FORECAST' (short risk), or 'BALANCED'")
    nmae_mean_gen_pct: float = Field(..., description="MAE as percentage of mean actual generation")
    nmae_max_gen_pct: float = Field(..., description="MAE as percentage of max observed actual generation")
    smape_pct: float = Field(..., description="Symmetric Mean Absolute Percentage Error (0 - 200%)")
    safe_mape_pct: Optional[float] = Field(None, description="MAPE evaluated only on non-zero actuals (>= 100 MW)")
    abs_error_percentiles: PercentilesResult
    shortfall_percentiles: PercentilesResult
    coverage: CoverageCount


class HorizonBucketMetric(BaseModel):
    """Forecast error metrics aggregated by lead time horizon bucket."""

    bucket_label: str
    min_horizon_hours: float
    max_horizon_hours: float
    sample_count: int
    mae_mw: float
    rmse_mw: float
    bias_mw: float
    smape_pct: float


class HourOfDayMetric(BaseModel):
    """Forecast error metrics aggregated by hour of day (0-23)."""

    hour_of_day: int = Field(..., ge=0, le=23)
    sample_count: int
    mean_actual_mw: float
    mean_forecast_mw: float
    bias_mw: float
    mae_mw: float
    rmse_mw: float


# ==============================================================================
# Pure Vectorised Analytics Functions
# ==============================================================================

def calculate_forecast_metrics(
    actual: Sequence[float] | pd.Series | np.ndarray,
    forecast: Sequence[float] | pd.Series | np.ndarray,
    total_expected_points: Optional[int] = None,
    mape_threshold_mw: float = 100.0,
) -> ForecastMetricsSummary:
    """
    Pure function to calculate comprehensive forecast accuracy metrics.

    Error formula:
        error = forecast - actual
        shortfall = max(0, forecast - actual)

    Relative error metrics:
    - `nmae_mean_gen_pct`: MAE / mean(actual) * 100%
    - `nmae_max_gen_pct`: MAE / max(actual) * 100% (fleet peak normalized without external capacity assumption)
    - `smape_pct`: 200% * |f - a| / (|f| + |a| + epsilon). Numerically bounded in [0, 200%].
    - `safe_mape_pct`: Evaluated strictly for actual >= threshold (100 MW) to avoid division by zero.
    """
    act = pd.Series(actual, dtype="float64")
    fct = pd.Series(forecast, dtype="float64")

    # Align and drop missing values
    valid_mask = act.notna() & fct.notna()
    act_valid = act[valid_mask].to_numpy()
    fct_valid = fct[valid_mask].to_numpy()

    n_used = len(act_valid)
    total_expected = total_expected_points if total_expected_points is not None else len(act)
    total_expected = max(total_expected, n_used)
    n_missing = total_expected - n_used
    coverage_pct = round((n_used / total_expected) * 100.0, 2) if total_expected > 0 else 0.0

    coverage = CoverageCount(
        total_expected=total_expected,
        n_points_used=n_used,
        n_missing=n_missing,
        coverage_pct=coverage_pct,
    )

    empty_pct = PercentilesResult(p50=0.0, p90=0.0, p95=0.0, p99=0.0)

    if n_used == 0:
        return ForecastMetricsSummary(
            sample_count=0,
            mean_actual_mw=0.0,
            mean_forecast_mw=0.0,
            max_actual_mw=0.0,
            max_forecast_mw=0.0,
            mae_mw=0.0,
            rmse_mw=0.0,
            bias_mw=0.0,
            bias_direction="BALANCED",
            nmae_mean_gen_pct=0.0,
            nmae_max_gen_pct=0.0,
            smape_pct=0.0,
            safe_mape_pct=None,
            abs_error_percentiles=empty_pct,
            shortfall_percentiles=empty_pct,
            coverage=coverage,
        )

    # Core error series
    err = fct_valid - act_valid
    abs_err = np.abs(err)
    shortfall = np.maximum(0.0, err)

    mean_act = float(np.mean(act_valid))
    mean_fct = float(np.mean(fct_valid))
    max_act = float(np.max(act_valid))
    max_fct = float(np.max(fct_valid))

    mae = float(np.mean(abs_err))
    rmse = float(np.sqrt(np.mean(err ** 2)))
    bias = float(np.mean(err))

    if abs(bias) < 1e-4:
        direction = "BALANCED"
    elif bias > 0:
        direction = "OVER_FORECAST"
    else:
        direction = "UNDER_FORECAST"

    # Percentage Normalizations
    nmae_mean = round((mae / mean_act * 100.0), 2) if mean_act > 0 else 0.0
    nmae_max = round((mae / max_act * 100.0), 2) if max_act > 0 else 0.0

    # sMAPE: 200 * |f - a| / (|f| + |a| + eps)
    denom = np.abs(fct_valid) + np.abs(act_valid) + 1e-6
    smape = float(np.mean(2.0 * abs_err / denom) * 100.0)

    # Safe MAPE on non-zero actuals
    mape_mask = act_valid >= mape_threshold_mw
    if np.any(mape_mask):
        safe_mape = float(np.mean(abs_err[mape_mask] / act_valid[mape_mask]) * 100.0)
        safe_mape_val: Optional[float] = round(safe_mape, 2)
    else:
        safe_mape_val = None

    # Percentiles
    abs_pct = PercentilesResult(
        p50=round(float(np.percentile(abs_err, 50)), 1),
        p90=round(float(np.percentile(abs_err, 90)), 1),
        p95=round(float(np.percentile(abs_err, 95)), 1),
        p99=round(float(np.percentile(abs_err, 99)), 1),
    )

    shortfall_pct = PercentilesResult(
        p50=round(float(np.percentile(shortfall, 50)), 1),
        p90=round(float(np.percentile(shortfall, 90)), 1),
        p95=round(float(np.percentile(shortfall, 95)), 1),
        p99=round(float(np.percentile(shortfall, 99)), 1),
    )

    return ForecastMetricsSummary(
        sample_count=n_used,
        mean_actual_mw=round(mean_act, 1),
        mean_forecast_mw=round(mean_fct, 1),
        max_actual_mw=round(max_act, 1),
        max_forecast_mw=round(max_fct, 1),
        mae_mw=round(mae, 1),
        rmse_mw=round(rmse, 1),
        bias_mw=round(bias, 1),
        bias_direction=direction,
        nmae_mean_gen_pct=nmae_mean,
        nmae_max_gen_pct=nmae_max,
        smape_pct=round(smape, 2),
        safe_mape_pct=safe_mape_val,
        abs_error_percentiles=abs_pct,
        shortfall_percentiles=shortfall_pct,
        coverage=coverage,
    )


def calculate_error_by_horizon_bucket(
    df: pd.DataFrame,
    bins: Optional[Sequence[float]] = None,
    labels: Optional[Sequence[str]] = None,
) -> List[HorizonBucketMetric]:
    """
    Compute forecast error metrics stratified across lead time horizon windows.

    Operates on all pre-delivery revisions (horizon_hours >= 0) joined to actuals.
    If provided a selected-forecast-only DataFrame (e.g. at D-1 09:00), it will only
    contain samples within the 16.5-39.5h range.

    Requires columns:
    - 'lead_time_hours' or 'horizon_hours'
    - 'forecast_mw'
    - 'actual_mw'
    """
    if df.empty:
        return []

    data = df.copy()
    h_col = "lead_time_hours" if "lead_time_hours" in data.columns else "horizon_hours"
    if h_col not in data.columns or "forecast_mw" not in data.columns or "actual_mw" not in data.columns:
        return []

    data = data.dropna(subset=[h_col, "forecast_mw", "actual_mw"]).copy()
    data = data[data[h_col] >= 0].copy()
    if data.empty:
        return []

    if bins is None:
        bins = [0, 6, 12, 18, 24, 30, 36, 42, 48, 54, 60, 66.5]
    if labels is None:
        labels = [f"{int(bins[i])}-{int(bins[i+1])}h" for i in range(len(bins) - 1)]

    data["bucket"] = pd.cut(data[h_col], bins=bins, labels=labels, include_lowest=True)

    results: List[HorizonBucketMetric] = []
    for i, label in enumerate(labels):
        sub = data[data["bucket"] == label]
        if sub.empty:
            continue
        err = sub["forecast_mw"] - sub["actual_mw"]
        abs_err = err.abs()
        denom = sub["forecast_mw"].abs() + sub["actual_mw"].abs() + 1e-6
        smape = float((2.0 * abs_err / denom).mean() * 100.0)

        results.append(
            HorizonBucketMetric(
                bucket_label=label,
                min_horizon_hours=float(bins[i]),
                max_horizon_hours=float(bins[i + 1]),
                sample_count=len(sub),
                mae_mw=round(float(abs_err.mean()), 1),
                rmse_mw=round(float(np.sqrt((err ** 2).mean())), 1),
                bias_mw=round(float(err.mean()), 1),
                smape_pct=round(smape, 2),
            )
        )
    return results


def calculate_error_by_hour_of_day(df: pd.DataFrame) -> List[HourOfDayMetric]:
    """
    Compute forecast error metrics stratified across hour of day (0 to 23).

    Requires columns:
    - 'startTime'
    - 'forecast_mw'
    - 'actual_mw'
    """
    if df.empty:
        return []

    data = df.copy()
    if "startTime" not in data.columns or "forecast_mw" not in data.columns or "actual_mw" not in data.columns:
        return []

    data["startTime"] = pd.to_datetime(data["startTime"], utc=True)
    data = data.dropna(subset=["startTime", "forecast_mw", "actual_mw"]).copy()
    if data.empty:
        return []

    data["hour"] = data["startTime"].dt.hour

    results: List[HourOfDayMetric] = []
    for h in range(24):
        sub = data[data["hour"] == h]
        if sub.empty:
            continue
        err = sub["forecast_mw"] - sub["actual_mw"]
        results.append(
            HourOfDayMetric(
                hour_of_day=h,
                sample_count=len(sub),
                mean_actual_mw=round(float(sub["actual_mw"].mean()), 1),
                mean_forecast_mw=round(float(sub["forecast_mw"].mean()), 1),
                bias_mw=round(float(err.mean()), 1),
                mae_mw=round(float(err.abs().mean()), 1),
                rmse_mw=round(float(np.sqrt((err ** 2).mean())), 1),
            )
        )
    return results


def align_all_pre_delivery_revisions(
    df_windfor: pd.DataFrame,
    df_fuelhh: pd.DataFrame,
) -> pd.DataFrame:
    """
    Align ALL pre-delivery forecast revisions (horizon >= 0) with half-hourly actuals.

    Each hourly WINDFOR revision is expanded to cover its two half-hourly settlement
    periods, filtered for publishTime <= startTime, and joined with FUELHH actuals.
    """
    if df_windfor.empty or df_fuelhh.empty:
        return pd.DataFrame(
            columns=["startTime", "publishTime", "forecast_mw", "actual_mw", "horizon_hours", "error_mw"]
        )

    wf = df_windfor.copy()
    wf["startTime"] = pd.to_datetime(wf["startTime"], utc=True)
    wf["publishTime"] = pd.to_datetime(wf["publishTime"], utc=True)

    # Filter pre-delivery revisions only (horizon >= 0)
    wf = wf[wf["publishTime"] <= wf["startTime"]].copy()
    if wf.empty:
        return pd.DataFrame(
            columns=["startTime", "publishTime", "forecast_mw", "actual_mw", "horizon_hours", "error_mw"]
        )

    # Expand hourly forecasts to half-hours
    first_half = wf.copy()
    second_half = wf.copy()
    second_half["startTime"] = second_half["startTime"] + pd.Timedelta(minutes=30)
    expanded_wf = pd.concat([first_half, second_half], ignore_index=True)
    expanded_wf = expanded_wf.rename(columns={"generation": "forecast_mw"})

    # Prepare actuals
    act = df_fuelhh.copy()
    act["startTime"] = pd.to_datetime(act["startTime"], utc=True)
    act = act.rename(columns={"generation": "actual_mw"})[["startTime", "actual_mw"]]

    # Merge
    merged = pd.merge(expanded_wf, act, on="startTime", how="inner")
    merged["horizon_hours"] = (merged["startTime"] - merged["publishTime"]).dt.total_seconds() / 3600.0
    merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
    merged["abs_error_mw"] = merged["error_mw"].abs()
    merged["shortfall_mw"] = np.maximum(0.0, merged["error_mw"])

    return merged


# ==============================================================================
# Aggregated Service-Level Functions
# ==============================================================================

def calculate_monthly_kpis(
    df: pd.DataFrame,
    decision_time_str: str = settings.default_decision_time,
) -> MonthlyKPIs:
    """Compute overall summary KPIs and risk percentiles for the aligned dataset."""
    total_expected = 31 * 48  # 1,488 half hours in January

    if df.empty:
        empty_pct = Percentiles(p50=0.0, p90=0.0, p99=0.0)
        return MonthlyKPIs(
            month="2026-01",
            decision_time_str=decision_time_str,
            total_possible_half_hours=total_expected,
            matched_half_hours=0,
            data_coverage_pct=0.0,
            mae_mw=0.0,
            rmse_mw=0.0,
            mean_bias_mw=0.0,
            bias_direction="BALANCED",
            mae_pct_of_mean_gen=0.0,
            mae_pct_of_max_gen=0.0,
            mae_pct_of_capacity=0.0,
            mean_actual_mw=0.0,
            mean_forecast_mw=0.0,
            max_actual_mw=0.0,
            max_forecast_mw=0.0,
            abs_error_percentiles=empty_pct,
            shortfall_percentiles=empty_pct,
        )

    valid = df.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    matched = len(valid)
    coverage = round((matched / total_expected) * 100.0, 2)

    if matched == 0:
        empty_pct = Percentiles(p50=0.0, p90=0.0, p99=0.0)
        return MonthlyKPIs(
            month="2026-01",
            decision_time_str=decision_time_str,
            total_possible_half_hours=total_expected,
            matched_half_hours=0,
            data_coverage_pct=0.0,
            mae_mw=0.0,
            rmse_mw=0.0,
            mean_bias_mw=0.0,
            bias_direction="BALANCED",
            mae_pct_of_mean_gen=0.0,
            mae_pct_of_max_gen=0.0,
            mae_pct_of_capacity=0.0,
            mean_actual_mw=0.0,
            mean_forecast_mw=0.0,
            max_actual_mw=0.0,
            max_forecast_mw=0.0,
            abs_error_percentiles=empty_pct,
            shortfall_percentiles=empty_pct,
        )

    valid["error_mw"] = valid["forecast_mw"] - valid["actual_mw"]
    valid["abs_error_mw"] = valid["error_mw"].abs()
    valid["shortfall_mw"] = np.maximum(0.0, valid["error_mw"])

    mae = float(valid["abs_error_mw"].mean())
    mse = float((valid["error_mw"] ** 2).mean())
    rmse = float(np.sqrt(mse))
    bias = float(valid["error_mw"].mean())
    mean_actual = float(valid["actual_mw"].mean())
    mean_forecast = float(valid["forecast_mw"].mean())
    max_actual = float(valid["actual_mw"].max())
    max_forecast = float(valid["forecast_mw"].max())

    # Percentage Normalizations: mean actual & max observed actual
    pct_mean_gen = round((mae / mean_actual * 100.0), 2) if mean_actual > 0 else 0.0
    pct_max_gen = round((mae / max_actual * 100.0), 2) if max_actual > 0 else 0.0

    # Percentiles
    abs_p50 = float(np.percentile(valid["abs_error_mw"], 50))
    abs_p90 = float(np.percentile(valid["abs_error_mw"], 90))
    abs_p99 = float(np.percentile(valid["abs_error_mw"], 99))

    # Shortfall percentiles: max(0, forecast - actual)
    shortfalls = valid["shortfall_mw"].dropna()
    sf_p50 = float(np.percentile(shortfalls, 50)) if len(shortfalls) > 0 else 0.0
    sf_p90 = float(np.percentile(shortfalls, 90)) if len(shortfalls) > 0 else 0.0
    sf_p99 = float(np.percentile(shortfalls, 99)) if len(shortfalls) > 0 else 0.0

    direction = "OVER_FORECAST" if bias >= 0 else "UNDER_FORECAST"

    return MonthlyKPIs(
        month="2026-01",
        decision_time_str=decision_time_str,
        total_possible_half_hours=total_expected,
        matched_half_hours=matched,
        data_coverage_pct=coverage,
        mae_mw=round(mae, 1),
        rmse_mw=round(rmse, 1),
        mean_bias_mw=round(bias, 1),
        bias_direction=direction,
        mae_pct_of_mean_gen=pct_mean_gen,
        mae_pct_of_max_gen=pct_max_gen,
        mae_pct_of_capacity=pct_max_gen,
        mean_actual_mw=round(mean_actual, 1),
        mean_forecast_mw=round(mean_forecast, 1),
        max_actual_mw=round(max_actual, 1),
        max_forecast_mw=round(max_forecast, 1),
        abs_error_percentiles=Percentiles(
            p50=round(abs_p50, 1),
            p90=round(abs_p90, 1),
            p99=round(abs_p99, 1),
        ),
        shortfall_percentiles=Percentiles(
            p50=round(sf_p50, 1),
            p90=round(sf_p90, 1),
            p99=round(sf_p99, 1),
        ),
    )


def calculate_daily_metrics(df: pd.DataFrame) -> List[DailyMetricPoint]:
    """Aggregate accuracy metrics by delivery day across January 2026."""
    if df.empty:
        return []

    valid = df.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    if valid.empty:
        return []

    if "error_mw" not in valid.columns:
        valid["error_mw"] = valid["forecast_mw"] - valid["actual_mw"]
    if "abs_error_mw" not in valid.columns:
        valid["abs_error_mw"] = valid["error_mw"].abs()

    results: List[DailyMetricPoint] = []
    grouped = valid.groupby("settlementDate")

    for s_date, group in grouped:
        mae = float(group["abs_error_mw"].mean())
        rmse = float(np.sqrt((group["error_mw"] ** 2).mean()))
        bias = float(group["error_mw"].mean())
        mean_act = float(group["actual_mw"].mean())
        mean_fc = float(group["forecast_mw"].mean())

        results.append(
            DailyMetricPoint(
                delivery_date=str(s_date),
                mae_mw=round(mae, 1),
                rmse_mw=round(rmse, 1),
                mean_bias_mw=round(bias, 1),
                mean_actual_mw=round(mean_act, 1),
                mean_forecast_mw=round(mean_fc, 1),
                matched_points=len(group),
            )
        )

    return sorted(results, key=lambda x: x.delivery_date)


def calculate_hourly_profile(df: pd.DataFrame) -> List[HourlyProfilePoint]:
    """Calculate mean actual, forecast, error and MAE for each settlement period (1-48)."""
    if df.empty:
        return []

    valid = df.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    if valid.empty:
        return []

    if "error_mw" not in valid.columns:
        valid["error_mw"] = valid["forecast_mw"] - valid["actual_mw"]
    if "abs_error_mw" not in valid.columns:
        valid["abs_error_mw"] = valid["error_mw"].abs()

    results: List[HourlyProfilePoint] = []
    grouped = valid.groupby("settlementPeriod")

    for period, group in grouped:
        p_int = int(period)
        h = (p_int - 1) // 2
        m = 30 if (p_int % 2 == 0) else 0
        time_label = f"{h:02d}:{m:02d}"

        mean_act = float(group["actual_mw"].mean())
        mean_fc = float(group["forecast_mw"].mean())
        bias = float(group["error_mw"].mean())
        mae = float(group["abs_error_mw"].mean())

        results.append(
            HourlyProfilePoint(
                settlement_period=p_int,
                period_start_time=time_label,
                mean_actual_mw=round(mean_act, 1),
                mean_forecast_mw=round(mean_fc, 1),
                mean_bias_mw=round(bias, 1),
                mae_mw=round(mae, 1),
                sample_count=len(group),
            )
        )

    return sorted(results, key=lambda x: x.settlement_period)


def calculate_forecast_horizons(
    df_fuelhh: pd.DataFrame,
    df_windfor: pd.DataFrame,
    horizons_hours: Optional[List[float]] = None,
) -> List[HorizonPoint]:
    """
    Quantify how forecast accuracy changes as delivery approaches (from 48h down to 3h).
    Evaluates: 'What was the error if trader evaluated at T minus H hours?'
    """
    if df_fuelhh.empty or df_windfor.empty:
        return []

    if horizons_hours is None:
        horizons_hours = [48.0, 36.0, 24.0, 18.0, 15.0, 12.0, 6.0, 3.0]

    actuals = df_fuelhh.rename(columns={"generation": "actual_mw"})[["startTime", "actual_mw"]].copy()
    actuals["startTime"] = pd.to_datetime(actuals["startTime"], utc=True)
    actuals["delivery_hour"] = actuals["startTime"].dt.floor("h")

    wf = df_windfor.copy()
    wf["startTime"] = pd.to_datetime(wf["startTime"], utc=True)
    wf["publishTime"] = pd.to_datetime(wf["publishTime"], utc=True)

    results: List[HorizonPoint] = []

    for h in sorted(horizons_hours, reverse=True):
        cutoff_series = wf["startTime"] - pd.Timedelta(hours=h)
        valid_wf = wf[wf["publishTime"] <= cutoff_series].copy()

        if valid_wf.empty:
            continue

        valid_wf["delivery_hour"] = valid_wf["startTime"].dt.floor("h")
        latest_wf = (
            valid_wf.sort_values(by=["delivery_hour", "publishTime"])
            .drop_duplicates(subset=["delivery_hour"], keep="last")
            .rename(columns={"generation": "forecast_mw"})[["delivery_hour", "forecast_mw"]]
        )

        merged = pd.merge(actuals, latest_wf, on="delivery_hour", how="inner")
        if merged.empty:
            continue

        merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
        merged["abs_error_mw"] = merged["error_mw"].abs()

        mae = float(merged["abs_error_mw"].mean())
        rmse = float(np.sqrt((merged["error_mw"] ** 2).mean()))
        bias = float(merged["error_mw"].mean())

        results.append(
            HorizonPoint(
                horizon_hours=float(h),
                mae_mw=round(mae, 1),
                rmse_mw=round(rmse, 1),
                mean_bias_mw=round(bias, 1),
                sample_count=len(merged),
            )
        )

    return sorted(results, key=lambda x: x.horizon_hours, reverse=True)


def calculate_error_distribution(
    df: pd.DataFrame,
    bin_size_mw: float = 500.0,
) -> List[ErrorDistributionBucket]:
    """Calculate histogram distribution buckets for signed forecast error (Forecast - Actual)."""
    if df.empty:
        return []

    valid = df.dropna(subset=["error_mw"]).copy()
    if valid.empty:
        return []

    errors = valid["error_mw"].values
    min_val = np.floor(np.min(errors) / bin_size_mw) * bin_size_mw
    max_val = np.ceil(np.max(errors) / bin_size_mw) * bin_size_mw

    bins = np.arange(min_val, max_val + bin_size_mw, bin_size_mw)
    counts, edges = np.histogram(errors, bins=bins)
    total = len(errors)

    buckets: List[ErrorDistributionBucket] = []
    for count, b_start, b_end in zip(counts, edges[:-1], edges[1:]):
        pct = round((count / total) * 100.0, 2) if total > 0 else 0.0
        buckets.append(
            ErrorDistributionBucket(
                bin_start=float(b_start),
                bin_end=float(b_end),
                count=int(count),
                percentage=pct,
            )
        )

    return buckets
