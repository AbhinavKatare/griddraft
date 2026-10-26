"""API v1 Versioned Router for UK Wind Forecast Monitoring & Quantitative Analytics.

Provides production REST endpoints for:
- /meta: Dataset temporal coverage, row counts, and ingestion metadata
- /timeseries: Aligned time-series with downsampling options (30m, 1h, 3h)
- /forecast-snapshot: Point-in-time forecast snapshot for a specific delivery date and decision cutoff
- /metrics: Comprehensive summary accuracy and risk KPIs
- /error-by-horizon: Stratified accuracy breakdown across forecast lead time horizon buckets
- /error-by-hour: Diurnal accuracy breakdown across settlement hours (0-23)
- /risk/safe-wind: Safe wind commitment and backup procurement with decomposition and backtest
- /diagnostics/metrics: Server request latency and timing telemetry
"""

from datetime import date
import logging
from typing import Any, Dict, List, Optional
import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, Query

from app.analytics.cache import (
    get_cached_all_pre_delivery_revisions,
    get_cached_day_alignment,
    get_cached_monthly_alignment,
    get_cached_monthly_kpis,
)
from app.analytics.forecast_selection import (
    calculate_cutoff_timestamp,
    expand_to_half_hours,
    select_decision_forecast,
    ForecastSelectionMode,
)
from app.analytics.metrics import (
    calculate_error_by_horizon_bucket,
    calculate_error_by_hour_of_day,
    calculate_monthly_kpis,
)
from app.analytics.risk import (
    calculate_safe_wind_profile,
    SafeWindSummary,
)
from app.config import settings
from app.dependencies import (
    get_data_store,
    validate_decision_time,
    validate_delivery_date,
    validate_date_range,
)
from app.middleware import metrics_tracker
from app.models.schemas import (
    ErrorByHorizonResponse,
    ErrorByHourResponse,
    ForecastSnapshotResponse,
    HalfHourForecastPoint,
    MetaResponse,
    MonthlyKPIs,
    TimeseriesPoint,
    TimeseriesResponse,
)
from app.services.data_store import DataStore

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["V1 Analytics & Monitoring"])


# ==============================================================================
# 1. Metadata Endpoint
# ==============================================================================

@router.get(
    "/meta",
    response_model=MetaResponse,
    summary="Get dataset coverage and ingestion metadata",
    description="Returns available date boundaries, cache status, and raw row counts for actuals and forecasts.",
)
async def get_metadata(
    store: DataStore = Depends(get_data_store),
) -> MetaResponse:
    """Retrieve metadata about the cached January 2026 dataset."""
    df_fuelhh = store.get_fuelhh()
    df_windfor = store.get_windfor()
    meta = store.get_metadata()

    fuelhh_min = (
        df_fuelhh["startTime"].min().strftime("%Y-%m-%d")
        if not df_fuelhh.empty
        else "2026-01-01"
    )
    fuelhh_max = (
        df_fuelhh["startTime"].max().strftime("%Y-%m-%d")
        if not df_fuelhh.empty
        else "2026-01-31"
    )
    last_update = meta.get("created_at") or meta.get("last_ingestion_time")

    return MetaResponse(
        service=settings.app_name,
        version=settings.app_version,
        available_start_date=fuelhh_min,
        available_end_date=fuelhh_max,
        last_ingestion_time=last_update,
        fuelhh_rows=len(df_fuelhh),
        windfor_rows=len(df_windfor),
        decision_time_default=settings.default_decision_time,
    )


# ==============================================================================
# 2. Timeseries Endpoint with Downsampling
# ==============================================================================

@router.get(
    "/timeseries",
    response_model=TimeseriesResponse,
    summary="Query aligned actual and forecast time-series with downsampling",
    description=(
        "Returns actual wind generation alongside decision-time forecast and latest forecast. "
        "Supports downsampling aggregation via ?resolution=30m|1h|3h."
    ),
)
async def get_timeseries(
    date_range: tuple[date, date] = Depends(validate_date_range),
    decision_time: str = Depends(validate_decision_time),
    resolution: str = Query(
        "30m",
        pattern="^(30m|1h|3h)$",
        description="Temporal resolution: '30m' (native), '1h' (hourly average), or '3h' (3-hour average)",
        examples=["30m", "1h", "3h"],
    ),
    store: DataStore = Depends(get_data_store),
) -> TimeseriesResponse:
    """Retrieve point-in-time aligned time-series with optional downsampling."""
    start_dt, end_dt = date_range
    start_bound = pd.Timestamp(f"{start_dt.strftime('%Y-%m-%d')} 00:00:00", tz="UTC")
    end_bound = pd.Timestamp(f"{end_dt.strftime('%Y-%m-%d')} 23:30:00", tz="UTC")

    # Use cached monthly alignment as basis
    monthly_aligned = get_cached_monthly_alignment(decision_time)

    # Filter date range
    sub = monthly_aligned[
        (monthly_aligned["startTime"] >= start_bound) & (monthly_aligned["startTime"] <= end_bound)
    ].copy()

    # Pre-fetch latest available forecasts for this window
    df_windfor = store.get_windfor()
    target_hours = pd.date_range(
        start=start_bound,
        end=pd.Timestamp(f"{end_dt.strftime('%Y-%m-%d')} 23:00:00", tz="UTC"),
        freq="1h",
    )
    latest_fc = select_decision_forecast(
        df_windfor,
        mode=ForecastSelectionMode.LATEST_AVAILABLE,
        target_start_times=target_hours,
    )
    latest_aligned = expand_to_half_hours(latest_fc)
    latest_map = dict(zip(latest_aligned["startTime"], latest_aligned["forecast_mw"]))
    sub["latest_forecast_mw"] = sub["startTime"].map(latest_map)

    # Handle Downsampling
    if resolution == "1h":
        sub["group_time"] = sub["startTime"].dt.floor("1h")
        agg = sub.groupby("group_time", as_index=False).agg({
            "actual_mw": "mean",
            "forecast_mw": "mean",
            "latest_forecast_mw": "mean",
            "settlementDate": "first",
        })
        agg = agg.rename(columns={"group_time": "startTime"})
        agg["settlementPeriod"] = (agg["startTime"].dt.hour * 2) + 1
        agg["error_mw"] = agg["forecast_mw"] - agg["actual_mw"]
        agg["abs_error_mw"] = agg["error_mw"].abs()
        agg["shortfall_mw"] = agg["error_mw"].apply(lambda x: max(0.0, x) if pd.notna(x) else np.nan)
        df_points = agg
    elif resolution == "3h":
        sub["group_time"] = sub["startTime"].dt.floor("3h")
        agg = sub.groupby("group_time", as_index=False).agg({
            "actual_mw": "mean",
            "forecast_mw": "mean",
            "latest_forecast_mw": "mean",
            "settlementDate": "first",
        })
        agg = agg.rename(columns={"group_time": "startTime"})
        agg["settlementPeriod"] = (agg["startTime"].dt.hour * 2) + 1
        agg["error_mw"] = agg["forecast_mw"] - agg["actual_mw"]
        agg["abs_error_mw"] = agg["error_mw"].abs()
        agg["shortfall_mw"] = agg["error_mw"].apply(lambda x: max(0.0, x) if pd.notna(x) else np.nan)
        df_points = agg
    else:
        df_points = sub

    points: List[TimeseriesPoint] = []
    for _, row in df_points.iterrows():
        st = row["startTime"]
        act = float(round(row["actual_mw"], 1)) if pd.notna(row.get("actual_mw")) else None
        dec_fc = float(round(row["forecast_mw"], 1)) if pd.notna(row.get("forecast_mw")) else None
        lat_fc = float(round(row.get("latest_forecast_mw"), 1)) if pd.notna(row.get("latest_forecast_mw")) else None
        err = float(round(row["error_mw"], 1)) if pd.notna(row.get("error_mw")) else None
        abs_err = float(round(row["abs_error_mw"], 1)) if pd.notna(row.get("abs_error_mw")) else None
        shortfall = float(round(row["shortfall_mw"], 1)) if pd.notna(row.get("shortfall_mw")) else None

        points.append(
            TimeseriesPoint(
                start_time=st.isoformat(),
                settlement_date=str(row["settlementDate"]),
                settlement_period=int(row["settlementPeriod"]),
                actual_mw=act,
                decision_forecast_mw=dec_fc,
                latest_forecast_mw=lat_fc,
                error_mw=err,
                abs_error_mw=abs_err,
                shortfall_mw=shortfall,
            )
        )

    return TimeseriesResponse(
        start_date=start_dt.strftime("%Y-%m-%d"),
        end_date=end_dt.strftime("%Y-%m-%d"),
        decision_time=decision_time,
        total_points=len(points),
        data=points,
    )


# ==============================================================================
# 3. Forecast Snapshot Endpoint
# ==============================================================================

@router.get(
    "/forecast-snapshot",
    response_model=ForecastSnapshotResponse,
    summary="Get day-ahead forecast snapshot for a specific delivery date",
    description="Returns the exact 48 settlement half-hours for a target day as known at the decision cutoff.",
)
@router.get(
    "/forecast/snapshot",
    response_model=ForecastSnapshotResponse,
    include_in_schema=False,
)
async def get_forecast_snapshot(
    delivery_date: date = Depends(validate_delivery_date),
    decision_time: str = Depends(validate_decision_time),
) -> ForecastSnapshotResponse:
    """Retrieve point-in-time day-ahead snapshot for a single delivery day."""
    date_str = delivery_date.strftime("%Y-%m-%d")
    aligned_df = get_cached_day_alignment(date_str, decision_time)
    cutoff_ts = calculate_cutoff_timestamp(delivery_date, decision_time)

    periods: List[HalfHourForecastPoint] = []
    for _, row in aligned_df.iterrows():
        periods.append(
            HalfHourForecastPoint(
                start_time=row["startTime"].isoformat(),
                settlement_date=str(row["settlementDate"]),
                settlement_period=int(row["settlementPeriod"]),
                actual_mw=float(round(row["actual_mw"], 1)) if pd.notna(row.get("actual_mw")) else None,
                forecast_mw=float(round(row["forecast_mw"], 1)) if pd.notna(row.get("forecast_mw")) else None,
                error_mw=float(round(row["error_mw"], 1)) if pd.notna(row.get("error_mw")) else None,
                abs_error_mw=float(round(row["abs_error_mw"], 1)) if pd.notna(row.get("abs_error_mw")) else None,
                shortfall_mw=float(round(row["shortfall_mw"], 1)) if pd.notna(row.get("shortfall_mw")) else None,
                latest_publish_time=(
                    row["latest_publish_time"].isoformat()
                    if pd.notna(row.get("latest_publish_time"))
                    else None
                ),
                lead_time_hours=float(round(row["lead_time_hours"], 1)) if pd.notna(row.get("lead_time_hours")) else None,
                has_forecast=bool(row.get("has_forecast", False)),
            )
        )

    matched = sum(1 for p in periods if p.has_forecast and p.actual_mw is not None)

    return ForecastSnapshotResponse(
        delivery_date=date_str,
        decision_time_str=decision_time,
        cutoff_time=cutoff_ts.isoformat(),
        total_periods=len(periods),
        matched_periods=matched,
        periods=periods,
    )


# ==============================================================================
# 4. Metrics Endpoint
# ==============================================================================

@router.get(
    "/metrics",
    response_model=MonthlyKPIs,
    summary="Calculate trading summary KPIs and risk percentiles",
    description="Computes MAE, RMSE, bias, shortfall percentiles, and safe percentage metrics.",
)
async def get_metrics(
    decision_time: str = Depends(validate_decision_time),
    start_date: Optional[str] = Query(None, description="Optional start filter (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="Optional end filter (YYYY-MM-DD)"),
) -> MonthlyKPIs:
    """Calculate aggregate forecast accuracy KPIs."""
    if not start_date and not end_date:
        return get_cached_monthly_kpis(decision_time)

    monthly_df = get_cached_monthly_alignment(decision_time)
    if start_date and end_date:
        start_ts = pd.Timestamp(f"{start_date} 00:00:00", tz="UTC")
        end_ts = pd.Timestamp(f"{end_date} 23:30:00", tz="UTC")
        monthly_df = monthly_df[
            (monthly_df["startTime"] >= start_ts) & (monthly_df["startTime"] <= end_ts)
        ].copy()

    return calculate_monthly_kpis(monthly_df, decision_time_str=decision_time)


# ==============================================================================
# 5. Error by Horizon Endpoint
# ==============================================================================

@router.get(
    "/error-by-horizon",
    response_model=ErrorByHorizonResponse,
    summary="Get forecast error stratified across lead-time horizon buckets",
    description=(
        "Evaluates error metrics across lead time windows (0-6h, 6-12h, ..., 60-66.5h). "
        "Operates on ALL pre-delivery revisions by default, or on the D-1 decision snapshot."
    ),
)
@router.get(
    "/metrics/error-by-horizon",
    response_model=ErrorByHorizonResponse,
    include_in_schema=False,
)
async def get_error_by_horizon(
    source: str = Query(
        "all",
        description="Data source: 'all' (all pre-delivery revisions) or 'decision' (D-1 decision snapshot)",
        examples=["all", "decision"],
    ),
    decision_time: str = Depends(validate_decision_time),
) -> ErrorByHorizonResponse:
    """Stratified forecast accuracy across horizon buckets."""
    if source.lower() == "decision":
        df = get_cached_monthly_alignment(decision_time)
        source_label = f"decision_time_snapshot_{decision_time}"
    else:
        df = get_cached_all_pre_delivery_revisions()
        source_label = "all_pre_delivery_revisions"

    buckets = calculate_error_by_horizon_bucket(df)
    total_obs = sum(b.sample_count for b in buckets)

    return ErrorByHorizonResponse(
        source=source_label,
        total_observations=total_obs,
        buckets=[b.model_dump() for b in buckets],
    )


# ==============================================================================
# 6. Error by Hour Endpoint
# ==============================================================================

@router.get(
    "/error-by-hour",
    response_model=ErrorByHourResponse,
    summary="Get diurnal forecast error profile across hours of day (0-23)",
    description="Evaluates mean actual, mean forecast, bias, MAE, and RMSE for each clock hour 0 to 23.",
)
@router.get(
    "/metrics/error-by-hour",
    response_model=ErrorByHourResponse,
    include_in_schema=False,
)
async def get_error_by_hour(
    decision_time: str = Depends(validate_decision_time),
) -> ErrorByHourResponse:
    """Diurnal forecast error profile across hours 0-23."""
    df = get_cached_monthly_alignment(decision_time)
    hours = calculate_error_by_hour_of_day(df)

    return ErrorByHourResponse(
        hours=[h.model_dump() for h in hours],
    )


# ==============================================================================
# 7. Safe Wind & Risk Procurement Endpoint
# ==============================================================================

@router.get(
    "/risk/safe-wind",
    response_model=SafeWindSummary,
    summary="Calculate 'Safe Wind to Count On' and backup thermal procurement",
    description=(
        "Derates day-ahead wind commitments by a historical shortfall quantile (default P90). "
        "Provides buffer decomposition (systematic bias vs residual quantile), prior-days vs in-sample toggle, "
        "and empirical backtest coverage."
    ),
)
async def get_safe_wind(
    delivery_date: date = Depends(validate_delivery_date),
    decision_time: str = Depends(validate_decision_time),
    quantile: float = Query(
        0.90,
        ge=0.50,
        le=0.999,
        description="Target reliability quantile (e.g. 0.90 for P90)",
        examples=[0.90, 0.95, 0.99],
    ),
    mode: str = Query(
        "in_sample",
        pattern="^(in_sample|prior_days)$",
        description="Shortfall history mode: 'in_sample' (full month) or 'prior_days' (only days prior to target)",
        examples=["in_sample", "prior_days"],
    ),
) -> SafeWindSummary:
    """Compute period-by-period safe wind generation and backup thermal procurement."""
    date_str = delivery_date.strftime("%Y-%m-%d")
    target_day_df = get_cached_day_alignment(date_str, decision_time)
    monthly_df = get_cached_monthly_alignment(decision_time)

    return calculate_safe_wind_profile(
        target_forecasts_df=target_day_df,
        quantile=quantile,
        mode=mode,
        full_history_df=monthly_df,
    )


# ==============================================================================
# 8. Diagnostics & Timing Metrics Endpoint
# ==============================================================================

@router.get(
    "/diagnostics/metrics",
    summary="Get server request latency and timing telemetry",
    description="Returns request counts, mean, P50, and P95 latency per endpoint tracked in memory.",
)
async def get_diagnostics_metrics() -> Dict[str, Any]:
    """Retrieve in-memory latency and timing telemetry."""
    return metrics_tracker.get_summary()
