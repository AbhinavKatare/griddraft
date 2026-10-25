"""FastAPI dependency injection and query parameter validators."""

from datetime import date, datetime
from typing import Tuple
from fastapi import Query

from app.models.problem import ProblemException
from app.services.data_store import DataStore, data_store


def get_data_store() -> DataStore:
    """Dependency provider for DataStore service."""
    return data_store


def validate_delivery_date(
    delivery_date: str = Query(
        "2026-01-15",
        description="Target delivery date in ISO format (YYYY-MM-DD) inside January 2026",
        examples=["2026-01-15"],
    ),
) -> date:
    """Validate that target delivery date is valid and strictly within January 2026."""
    try:
        dt = datetime.strptime(delivery_date, "%Y-%m-%d").date()
    except ValueError:
        raise ProblemException(
            status_code=400,
            title="Invalid Date Format",
            detail=f"Date '{delivery_date}' must be formatted as YYYY-MM-DD.",
        )

    if dt.year != 2026 or dt.month != 1:
        raise ProblemException(
            status_code=400,
            title="Date Out of Evaluation Window",
            detail=f"Delivery date {delivery_date} is outside January 2026.",
        )
    return dt


def validate_decision_time(
    decision_time: str = Query(
        "09:00",
        description="Day-ahead auction decision cutoff time on D-1 in HH:MM format",
        examples=["09:00", "08:30", "11:00"],
    ),
) -> str:
    """Validate decision time format (HH:MM)."""
    try:
        parts = decision_time.split(":")
        if len(parts) != 2:
            raise ValueError
        h = int(parts[0])
        m = int(parts[1])
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError
    except Exception:
        raise ProblemException(
            status_code=400,
            title="Invalid Cutoff Format",
            detail=f"Decision time '{decision_time}' must be in HH:MM format between 00:00 and 23:59.",
        )
    return decision_time


def validate_date_range(
    start_date: str = Query(
        "2026-01-01",
        description="Start delivery date (YYYY-MM-DD) within January 2026",
        examples=["2026-01-01"],
    ),
    end_date: str = Query(
        "2026-01-31",
        description="End delivery date (YYYY-MM-DD) within January 2026",
        examples=["2026-01-31"],
    ),
) -> Tuple[date, date]:
    """Validate a closed date range [start_date, end_date] within January 2026."""
    try:
        start_dt = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise ProblemException(
            status_code=400,
            title="Invalid Start Date",
            detail=f"Start date '{start_date}' must be formatted as YYYY-MM-DD.",
        )

    try:
        end_dt = datetime.strptime(end_date, "%Y-%m-%d").date()
    except ValueError:
        raise ProblemException(
            status_code=400,
            title="Invalid End Date",
            detail=f"End date '{end_date}' must be formatted as YYYY-MM-DD.",
        )

    if start_dt > end_dt:
        raise ProblemException(
            status_code=400,
            title="Invalid Date Ordering",
            detail=f"Start date ({start_date}) cannot be after end date ({end_date}).",
        )

    if start_dt.year != 2026 or start_dt.month != 1:
        raise ProblemException(
            status_code=400,
            title="Date Out of Scope",
            detail=f"Start date {start_date} is outside January 2026.",
        )

    if end_dt.year != 2026 or end_dt.month != 1:
        raise ProblemException(
            status_code=400,
            title="Date Out of Scope",
            detail=f"End date {end_date} is outside January 2026.",
        )

    return start_dt, end_dt
