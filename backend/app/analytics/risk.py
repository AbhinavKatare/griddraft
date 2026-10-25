"""Quantitative risk management and 'Safe Wind to Count On' estimation.

Trader Problem:
A physical trader selling wind generation commits energy in the Day-Ahead auction.
Because wind is non-dispatchable and intermittent, committing nominal forecast volume
exposes the trading desk to energy shortfalls whenever outturn is lower than forecast.

To manage this risk, traders compute a conservative 'Safe Wind to Count On' volume:
    safe_wind = max(0.0, forecast - buffer)
where shortfall = max(0.0, forecast - actual).

The remaining volume represents the implied thermal backup procurement:
    thermal_procurement = forecast - safe_wind = min(forecast, buffer)

Statistical Assumptions & Limitations:
1. Stationarity:
   - Historical error and shortfall distributions are assumed stationary across evaluation periods.
   - Limitation: Meteorological regime shifts between persistent high pressure and cyclonic depressions
     change the error variance.
2. Homoskedasticity:
   - Applying a single flat buffer assumes shortfall uncertainty is independent of wind level.
3. Sample Size:
   - Estimating upper tail quantiles (e.g. P90, P95, P99) is subject to sampling variance.
"""

import logging
from typing import List, Optional, Sequence
import numpy as np
import pandas as pd
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


# ==============================================================================
# Typed Models
# ==============================================================================

class BufferDecomposition(BaseModel):
    """Decomposition of the total buffer into systematic bias and stochastic residual."""

    systematic_bias_mw: float = Field(..., description="Mean historical shortfall component in MW")
    residual_quantile_mw: float = Field(..., description="Residual quantile component above mean bias in MW")
    total_buffer_mw: float = Field(..., description="Total combined shortfall buffer in MW")


class BacktestResult(BaseModel):
    """Empirical backtest evaluating whether actual outturn covered safe wind commitments."""

    target_coverage_pct: float = Field(..., description="Nominal confidence quantile percentage (e.g. 90%)")
    empirical_coverage_pct: float = Field(..., description="Observed percentage of intervals where actual >= safe_wind")
    total_evaluated_periods: int = Field(..., description="Number of periods with actuals evaluated")
    breach_count: int = Field(..., description="Number of intervals where actual fell below safe_wind")
    max_breach_mw: float = Field(..., description="Maximum deficit observed: max(0, safe_wind - actual) in MW")
    mean_breach_mw: float = Field(..., description="Average deficit during breach intervals in MW")


class SafeWindPeriod(BaseModel):
    """Safe wind commitment and backup procurement for a single settlement period."""

    start_time: str = Field(..., description="Target delivery start time in UTC (ISO 8601)")
    settlement_period: Optional[int] = Field(None, ge=1, le=50, description="GB settlement period (1-48)")
    forecast_mw: float = Field(..., description="Nominal point forecast in MW")
    shortfall_buffer_mw: float = Field(..., description="Historical shortfall quantile buffer in MW")
    safe_wind_mw: float = Field(..., description="Floored safe wind volume: max(0, forecast - buffer) in MW")
    thermal_procurement_mw: float = Field(..., description="Backup capacity required: min(forecast, buffer) in MW")
    actual_mw: Optional[float] = Field(None, description="Actual outturn if available in MW")
    is_breached: Optional[bool] = Field(None, description="Whether actual < safe_wind (breach)")


class SafeWindSummary(BaseModel):
    """Aggregated safe wind profile, buffer decomposition, and backtest results."""

    quantile: float = Field(..., ge=0.5, le=0.999, description="Target reliability quantile (e.g. 0.90 for P90)")
    mode: str = Field(..., description="Evaluation mode: 'in_sample' or 'prior_days'")
    shortfall_quantile_mw: float = Field(..., description="Evaluated total shortfall buffer in MW")
    total_forecast_mwh: float = Field(..., description="Total forecasted energy across periods in MWh")
    total_safe_wind_mwh: float = Field(..., description="Total derated safe wind energy in MWh")
    total_thermal_procurement_mwh: float = Field(..., description="Total backup thermal energy required in MWh")
    hedge_ratio_pct: float = Field(..., description="Ratio of safe wind to nominal forecast (0 - 100%)")
    decomposition: BufferDecomposition
    backtest: Optional[BacktestResult] = None
    periods: List[SafeWindPeriod]


# ==============================================================================
# Pure Risk Calculation Functions
# ==============================================================================

def compute_safe_wind_quantity(forecast_mw: float, shortfall_quantile_mw: float) -> float:
    """
    Calculate safe wind volume floored at zero.

    safe_wind = max(0.0, forecast - shortfall_quantile)
    """
    return max(0.0, forecast_mw - shortfall_quantile_mw)


def compute_thermal_procurement_quantity(forecast_mw: float, shortfall_quantile_mw: float) -> float:
    """
    Calculate required thermal procurement to firm up nominal forecast commitment.

    thermal = forecast - safe_wind = min(forecast, shortfall_quantile)
    """
    return min(max(0.0, forecast_mw), max(0.0, shortfall_quantile_mw))


def decompose_shortfall_buffer(
    shortfalls: np.ndarray,
    quantile: float = 0.90,
) -> BufferDecomposition:
    """
    Decompose total shortfall buffer into systematic bias and stochastic residual quantile.

    total_buffer = Q_alpha(shortfall)
    systematic_bias = mean(shortfall)
    residual_quantile = max(0.0, total_buffer - systematic_bias)
    """
    if len(shortfalls) == 0:
        return BufferDecomposition(systematic_bias_mw=0.0, residual_quantile_mw=0.0, total_buffer_mw=0.0)

    total_buf = float(np.percentile(shortfalls, quantile * 100.0))
    bias = float(np.mean(shortfalls))
    residual = max(0.0, total_buf - bias)

    return BufferDecomposition(
        systematic_bias_mw=round(bias, 1),
        residual_quantile_mw=round(residual, 1),
        total_buffer_mw=round(total_buf, 1),
    )


def calculate_safe_wind_profile(
    target_forecasts_df: pd.DataFrame,
    quantile: float = 0.90,
    historical_shortfalls: Optional[Sequence[float] | pd.Series | np.ndarray] = None,
    mode: str = "in_sample",
    full_history_df: Optional[pd.DataFrame] = None,
    prior_cutoff_offset_days: int = 1,
) -> SafeWindSummary:
    """
    Compute period-by-period safe wind generation, buffer decomposition, and backtest.

    Parameters:
    - target_forecasts_df: DataFrame with 'startTime', 'forecast_mw', and optional 'settlementPeriod', 'actual_mw'
    - quantile: Probability quantile alpha in [0.50, 0.999], defaults to 0.90 (P90)
    - historical_shortfalls: Optional external sample of shortfall = max(0, forecast - actual).
    - mode: 'in_sample' (uses full sample distribution) or 'prior_days' (uses only days strictly prior to target date).
    - full_history_df: Optional complete historical aligned DataFrame containing actuals and forecasts for prior_days mode.
    - prior_cutoff_offset_days: Number of days prior to target date for training cutoff (1 for < D, 2 for <= D-2).
    """
    if target_forecasts_df.empty:
        empty_decomp = BufferDecomposition(systematic_bias_mw=0.0, residual_quantile_mw=0.0, total_buffer_mw=0.0)
        return SafeWindSummary(
            quantile=quantile,
            mode=mode,
            shortfall_quantile_mw=0.0,
            total_forecast_mwh=0.0,
            total_safe_wind_mwh=0.0,
            total_thermal_procurement_mwh=0.0,
            hedge_ratio_pct=0.0,
            decomposition=empty_decomp,
            backtest=None,
            periods=[],
        )

    # Resolve shortfalls based on mode
    if mode == "prior_days" and full_history_df is not None and not full_history_df.empty:
        target_date = str(target_forecasts_df.get("settlementDate", pd.Series([""])).iloc[0])
        cutoff_date = (pd.to_datetime(target_date) - pd.Timedelta(days=prior_cutoff_offset_days)).strftime("%Y-%m-%d")
        prior = full_history_df[full_history_df["settlementDate"] <= cutoff_date].dropna(
            subset=["actual_mw", "forecast_mw"]
        )
        if len(prior) >= 48:
            err = prior["forecast_mw"].to_numpy() - prior["actual_mw"].to_numpy()
            sf_clean = np.maximum(0.0, err)
        elif historical_shortfalls is not None and len(historical_shortfalls) > 0:
            sf_array = np.asarray(historical_shortfalls, dtype="float64")
            sf_clean = sf_array[~np.isnan(sf_array)]
        elif "actual_mw" in target_forecasts_df.columns and "forecast_mw" in target_forecasts_df.columns:
            # Fallback for D=1 or D=2 when <48 prior periods exist
            valid = target_forecasts_df.dropna(subset=["actual_mw", "forecast_mw"])
            err = valid["forecast_mw"].to_numpy() - valid["actual_mw"].to_numpy()
            sf_clean = np.maximum(0.0, err)
        else:
            sf_clean = np.array([0.0])
    elif historical_shortfalls is not None and len(historical_shortfalls) > 0:
        sf_array = np.asarray(historical_shortfalls, dtype="float64")
        sf_clean = sf_array[~np.isnan(sf_array)]
    elif "actual_mw" in target_forecasts_df.columns and "forecast_mw" in target_forecasts_df.columns:
        valid = target_forecasts_df.dropna(subset=["actual_mw", "forecast_mw"])
        err = valid["forecast_mw"].to_numpy() - valid["actual_mw"].to_numpy()
        sf_clean = np.maximum(0.0, err)
    else:
        sf_clean = np.array([0.0])

    if len(sf_clean) == 0:
        sf_clean = np.array([0.0])

    # Decompose buffer
    decomp = decompose_shortfall_buffer(sf_clean, quantile=quantile)
    q_val = decomp.total_buffer_mw

    df = target_forecasts_df.reset_index(drop=True)
    if "forecast_mw" not in df.columns:
        raise ValueError("target_forecasts_df must contain 'forecast_mw' column.")

    forecasts = df["forecast_mw"].fillna(0.0).to_numpy()
    safe_winds = np.maximum(0.0, forecasts - q_val)
    thermals = forecasts - safe_winds

    total_fc_mwh = round(float(np.sum(forecasts) * 0.5), 1)
    total_safe_mwh = round(float(np.sum(safe_winds) * 0.5), 1)
    total_thermal_mwh = round(float(np.sum(thermals) * 0.5), 1)

    hedge_ratio = round((total_safe_mwh / total_fc_mwh * 100.0), 2) if total_fc_mwh > 0 else 0.0

    periods: List[SafeWindPeriod] = []
    has_actuals = "actual_mw" in df.columns and df["actual_mw"].notna().any()

    breach_count = 0
    breach_deficits: List[float] = []
    evaluated_count = 0

    for i, row in df.iterrows():
        fc = float(row.get("forecast_mw", 0.0))
        sw = float(safe_winds[i])
        tp = float(thermals[i])
        st_val = str(row.get("startTime", ""))
        sp = int(row["settlementPeriod"]) if "settlementPeriod" in row and pd.notna(row["settlementPeriod"]) else None

        act_val: Optional[float] = None
        is_breach: Optional[bool] = None

        if has_actuals and pd.notna(row.get("actual_mw")):
            act_val = float(round(row["actual_mw"], 1))
            is_breach = act_val < sw
            evaluated_count += 1
            if is_breach:
                breach_count += 1
                breach_deficits.append(sw - act_val)

        periods.append(
            SafeWindPeriod(
                start_time=st_val,
                settlement_period=sp,
                forecast_mw=round(fc, 1),
                shortfall_buffer_mw=q_val,
                safe_wind_mw=round(sw, 1),
                thermal_procurement_mw=round(tp, 1),
                actual_mw=act_val,
                is_breached=is_breach,
            )
        )

    # Backtest summary if actuals available
    backtest: Optional[BacktestResult] = None
    if evaluated_count > 0:
        emp_coverage = round(((evaluated_count - breach_count) / evaluated_count) * 100.0, 2)
        max_b = round(max(breach_deficits), 1) if breach_deficits else 0.0
        mean_b = round(float(np.mean(breach_deficits)), 1) if breach_deficits else 0.0

        backtest = BacktestResult(
            target_coverage_pct=round(quantile * 100.0, 1),
            empirical_coverage_pct=emp_coverage,
            total_evaluated_periods=evaluated_count,
            breach_count=breach_count,
            max_breach_mw=max_b,
            mean_breach_mw=mean_b,
        )

    return SafeWindSummary(
        quantile=quantile,
        mode=mode,
        shortfall_quantile_mw=q_val,
        total_forecast_mwh=total_fc_mwh,
        total_safe_wind_mwh=total_safe_mwh,
        total_thermal_procurement_mwh=total_thermal_mwh,
        hedge_ratio_pct=hedge_ratio,
        decomposition=decomp,
        backtest=backtest,
        periods=periods,
    )
