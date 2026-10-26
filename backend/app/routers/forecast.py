"""Forecast router providing point-in-time day-ahead forecast views."""

from datetime import datetime
import logging
from fastapi import APIRouter, HTTPException, Query
import numpy as np
import pandas as pd

from app.config import settings
from app.models.schemas import DayForecastResponse, HalfHourForecastPoint
from app.analytics.forecast_selection import (
    calculate_cutoff_timestamp,
    get_day_forecast_alignment,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/forecast", tags=["Forecast"])


@router.get("/day", response_model=DayForecastResponse)
async def get_day_forecast(
    delivery_date: str = Query("2026-01-15", description="Target delivery date (YYYY-MM-DD)"),
    decision_time: str = Query(
        settings.default_decision_time,
        description="Cutoff decision time on D-1 (HH:MM GMT)",
    ),
) -> DayForecastResponse:
    """
    Get half-hourly forecast and actual comparison for delivery day D,
    strictly restricted to forecasts published before decision_time on D-1.
    """
    try:
        parsed_date = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid date format. Expected YYYY-MM-DD.")

    if parsed_date.year != 2026 or parsed_date.month != 1:
        raise HTTPException(status_code=400, detail="Scope is restricted to January 2026.")

    aligned_df = get_day_forecast_alignment(
        delivery_date=parsed_date,
        decision_time_str=decision_time,
    )

    cutoff_ts = calculate_cutoff_timestamp(parsed_date, decision_time)

    if aligned_df.empty:
        return DayForecastResponse(
            delivery_date=delivery_date,
            decision_time_cutoff=cutoff_ts.isoformat(),
            decision_time_str=decision_time,
            total_periods=0,
            matched_periods=0,
            day_mae_mw=None,
            day_rmse_mw=None,
            day_bias_mw=None,
            periods=[],
        )

    # Calculate day-level summary
    valid = aligned_df.dropna(subset=["actual_mw", "forecast_mw"])
    mae = float(valid["abs_error_mw"].mean()) if not valid.empty else None
    rmse = float(np.sqrt((valid["error_mw"] ** 2).mean())) if not valid.empty else None
    bias = float(valid["error_mw"].mean()) if not valid.empty else None

    period_points = []
    for _, row in aligned_df.iterrows():
        p_pt = HalfHourForecastPoint(
            settlement_date=str(row["settlementDate"]),
            settlement_period=int(row["settlementPeriod"]) if pd.notna(row.get("settlementPeriod")) else 1,
            start_time=row["startTime"].isoformat() if pd.notna(row["startTime"]) else "",
            actual_mw=float(round(row["actual_mw"], 1)) if pd.notna(row.get("actual_mw")) else None,
            forecast_mw=float(round(row["forecast_mw"], 1)) if pd.notna(row.get("forecast_mw")) else None,
            latest_publish_time=row["latest_publish_time"].isoformat() if pd.notna(row.get("latest_publish_time")) else None,
            lead_time_hours=float(round(row["lead_time_hours"], 1)) if pd.notna(row.get("lead_time_hours")) else None,
            error_mw=float(round(row["error_mw"], 1)) if pd.notna(row.get("error_mw")) else None,
            abs_error_mw=float(round(row["abs_error_mw"], 1)) if pd.notna(row.get("abs_error_mw")) else None,
            shortfall_mw=float(round(row["shortfall_mw"], 1)) if pd.notna(row.get("shortfall_mw")) else None,
        )
        period_points.append(p_pt)

    return DayForecastResponse(
        delivery_date=delivery_date,
        decision_time_cutoff=cutoff_ts.isoformat(),
        decision_time_str=decision_time,
        total_periods=len(aligned_df),
        matched_periods=len(valid),
        day_mae_mw=round(mae, 1) if mae is not None else None,
        day_rmse_mw=round(rmse, 1) if rmse is not None else None,
        day_bias_mw=round(bias, 1) if bias is not None else None,
        periods=period_points,
    )
