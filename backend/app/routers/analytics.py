"""Analytics router providing KPIs, daily breakdowns, hourly profiles and horizons."""

from typing import List
from fastapi import APIRouter, Query

from app.config import settings
from app.models.schemas import (
    DailyMetricPoint,
    ErrorDistributionBucket,
    HorizonPoint,
    HourlyProfilePoint,
    MonthlyKPIs,
)
from app.analytics.metrics import (
    calculate_daily_metrics,
    calculate_error_distribution,
    calculate_forecast_horizons,
    calculate_hourly_profile,
    calculate_monthly_kpis,
)
from app.analytics.forecast_selection import get_monthly_forecast_alignment

router = APIRouter(prefix="/api/analytics", tags=["Analytics"])


@router.get("/kpis", response_model=MonthlyKPIs)
async def get_kpis(
    decision_time: str = Query(
        settings.default_decision_time,
        description="Decision cutoff time on D-1 (HH:MM GMT)",
    ),
) -> MonthlyKPIs:
    """Get high-level trading KPIs, MAE, RMSE, bias and risk percentiles."""
    monthly_df = get_monthly_forecast_alignment(decision_time_str=decision_time)
    return calculate_monthly_kpis(monthly_df, decision_time_str=decision_time)


@router.get("/daily", response_model=List[DailyMetricPoint])
async def get_daily_metrics(
    decision_time: str = Query(
        settings.default_decision_time,
        description="Decision cutoff time on D-1 (HH:MM GMT)",
    ),
) -> List[DailyMetricPoint]:
    """Get day-by-day accuracy metrics across January 2026."""
    monthly_df = get_monthly_forecast_alignment(decision_time_str=decision_time)
    return calculate_daily_metrics(monthly_df)


@router.get("/hourly-profile", response_model=List[HourlyProfilePoint])
async def get_hourly_profile(
    decision_time: str = Query(
        settings.default_decision_time,
        description="Decision cutoff time on D-1 (HH:MM GMT)",
    ),
) -> List[HourlyProfilePoint]:
    """Get average profile across half-hourly settlement periods 1-48."""
    monthly_df = get_monthly_forecast_alignment(decision_time_str=decision_time)
    return calculate_hourly_profile(monthly_df)


@router.get("/horizons", response_model=List[HorizonPoint])
async def get_forecast_horizons() -> List[HorizonPoint]:
    """Get accuracy decay curves across different forecast lead times (48h down to 3h)."""
    return calculate_forecast_horizons()


@router.get("/distribution", response_model=List[ErrorDistributionBucket])
async def get_error_distribution(
    decision_time: str = Query(
        settings.default_decision_time,
        description="Decision cutoff time on D-1 (HH:MM GMT)",
    ),
    bin_size_mw: float = Query(500.0, description="Bin width in MW"),
) -> List[ErrorDistributionBucket]:
    """Get histogram distribution of signed forecast error (Forecast - Actual)."""
    monthly_df = get_monthly_forecast_alignment(decision_time_str=decision_time)
    return calculate_error_distribution(monthly_df, bin_size_mw=bin_size_mw)
