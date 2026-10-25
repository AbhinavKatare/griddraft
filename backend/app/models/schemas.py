"""Pydantic models and schemas for request/response typing."""

from datetime import date, datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, Field


class HalfHourForecastPoint(BaseModel):
    """Single half-hourly forecast and actual comparison point."""

    settlement_date: str = Field(..., description="Settlement date (YYYY-MM-DD)")
    settlement_period: int = Field(..., ge=1, le=50, description="Settlement period (1-48/50)")
    start_time: str = Field(..., description="Half-hour start timestamp ISO-8601 UTC")
    actual_mw: Optional[float] = Field(None, description="Actual wind generation from FUELHH (MW)")
    forecast_mw: Optional[float] = Field(None, description="Latest forecast available at decision time (MW)")
    latest_publish_time: Optional[str] = Field(None, description="Publish time of the selected forecast")
    lead_time_hours: Optional[float] = Field(None, description="Hours between publish time and delivery start")
    error_mw: Optional[float] = Field(None, description="Signed error = Forecast - Actual (MW)")
    abs_error_mw: Optional[float] = Field(None, description="Absolute error |Forecast - Actual| (MW)")
    shortfall_mw: Optional[float] = Field(
        None, description="Shortfall when forecast > actual, causing long day-ahead risk (MW)"
    )
    has_forecast: bool = Field(True, description="Whether a forecast was available prior to cutoff")


class DayForecastResponse(BaseModel):
    """Full day half-hourly delivery comparison for day D at D-1 decision time."""

    delivery_date: str = Field(..., description="Target delivery date (YYYY-MM-DD)")
    decision_time_cutoff: str = Field(..., description="Cutoff timestamp ISO-8601 on D-1")
    decision_time_str: str = Field(..., description="Cutoff time of day (HH:MM GMT)")
    total_periods: int
    matched_periods: int
    day_mae_mw: Optional[float] = None
    day_rmse_mw: Optional[float] = None
    day_bias_mw: Optional[float] = None
    periods: List[HalfHourForecastPoint]


class Percentiles(BaseModel):
    """Percentile distribution metrics."""

    p50: float = Field(..., description="50th percentile (Median)")
    p90: float = Field(..., description="90th percentile")
    p99: float = Field(..., description="99th percentile")


class MonthlyKPIs(BaseModel):
    """High-level summary metrics for the target scope."""

    month: str = Field(..., description="Scope month (YYYY-MM)")
    decision_time_str: str = Field(..., description="Decision time on D-1 (HH:MM GMT)")
    total_possible_half_hours: int
    matched_half_hours: int
    data_coverage_pct: float
    mae_mw: float
    rmse_mw: float
    mean_bias_mw: float
    bias_direction: str = Field(..., description="'OVER_FORECAST' (long risk) or 'UNDER_FORECAST' (short risk)")
    mae_pct_of_mean_gen: float
    mae_pct_of_max_gen: float
    mae_pct_of_capacity: Optional[float] = None
    mean_actual_mw: float
    mean_forecast_mw: float
    max_actual_mw: float
    max_forecast_mw: float
    abs_error_percentiles: Percentiles
    shortfall_percentiles: Percentiles


class DailyMetricPoint(BaseModel):
    """Daily aggregated accuracy metric point."""

    delivery_date: str
    mae_mw: float
    rmse_mw: float
    mean_bias_mw: float
    mean_actual_mw: float
    mean_forecast_mw: float
    matched_points: int


class HourlyProfilePoint(BaseModel):
    """Half-hourly settlement period average profile (1-48)."""

    settlement_period: int
    period_start_time: str
    mean_actual_mw: float
    mean_forecast_mw: float
    mean_bias_mw: float
    mae_mw: float
    sample_count: int


class HorizonPoint(BaseModel):
    """Error metrics at varying forecast horizons / lead times."""

    horizon_hours: float = Field(..., description="Hours before delivery start (lead time)")
    mae_mw: float
    rmse_mw: float
    mean_bias_mw: float
    sample_count: int


class ErrorDistributionBucket(BaseModel):
    """Histogram bucket for signed error distribution."""

    bin_start: float
    bin_end: float
    count: int
    percentage: float


class SystemStatus(BaseModel):
    """Backend status, data source and cache metadata."""

    status: str
    data_source: str
    cache_loaded: bool
    fuelhh_records: int
    windfor_records: int
    fuelhh_min_date: Optional[str]
    fuelhh_max_date: Optional[str]
    windfor_min_publish: Optional[str]
    windfor_max_publish: Optional[str]
    cache_last_updated: Optional[str]
    default_decision_time: str


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str = Field("healthy", description="Application status", examples=["healthy"])
    version: str = Field(..., description="Application version", examples=["1.0.0"])
    cache_loaded: bool = Field(..., description="Whether Parquet data cache is loaded in memory")


class MetaResponse(BaseModel):
    """Metadata detailing available dataset scope, dates, and cache timestamps."""

    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    available_start_date: str = Field(..., description="Earliest available settlement date (YYYY-MM-DD)")
    available_end_date: str = Field(..., description="Latest available settlement date (YYYY-MM-DD)")
    last_ingestion_time: Optional[str] = Field(None, description="ISO timestamp of last cache update")
    fuelhh_rows: int = Field(..., description="Number of metered actual half-hour rows in cache")
    windfor_rows: int = Field(..., description="Number of forecast revision rows in cache")
    decision_time_default: str = Field(..., description="Default trading decision cutoff on D-1")


class TimeseriesPoint(BaseModel):
    """A single half-hourly aligned observation containing actuals and forecasts."""

    start_time: str = Field(..., description="Interval start timestamp in UTC (ISO 8601)")
    settlement_date: str = Field(..., description="GB settlement date (YYYY-MM-DD)")
    settlement_period: int = Field(..., ge=1, le=50, description="Settlement period (1-48)")
    actual_mw: Optional[float] = Field(None, description="Outturn metered wind generation (FUELHH) in MW")
    decision_forecast_mw: Optional[float] = Field(None, description="Latest forecast published prior to cutoff in MW")
    latest_forecast_mw: Optional[float] = Field(None, description="Latest forecast published prior to delivery start in MW")
    error_mw: Optional[float] = Field(None, description="Decision error = forecast - actual in MW")
    abs_error_mw: Optional[float] = Field(None, description="Absolute error in MW")
    shortfall_mw: Optional[float] = Field(None, description="Downside shortfall = max(0, forecast - actual) in MW")


class TimeseriesResponse(BaseModel):
    """Time-series query response with aligned actuals and forecasts."""

    start_date: str
    end_date: str
    decision_time: str
    total_points: int
    data: List[TimeseriesPoint]


class ForecastSnapshotResponse(BaseModel):
    """Point-in-time forecast snapshot for a given delivery day and decision cutoff."""

    delivery_date: str
    decision_time_str: str
    cutoff_time: str
    total_periods: int
    matched_periods: int
    periods: List[HalfHourForecastPoint]


class ErrorByHorizonResponse(BaseModel):
    """Stratified forecast accuracy across lead time horizon buckets."""

    source: str = Field(..., description="Revisions source: 'all_pre_delivery_revisions' or 'decision_time_snapshot'")
    total_observations: int
    buckets: List[dict]


class ErrorByHourResponse(BaseModel):
    """Diurnal error profile across hours of the day (0-23)."""

    hours: List[dict]
