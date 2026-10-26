"""In-memory thread-safe LRU caching for expensive point-in-time alignments and metrics."""

from functools import lru_cache
import pandas as pd

from app.analytics.forecast_selection import (
    get_day_forecast_alignment as _get_day_forecast_alignment,
    get_monthly_forecast_alignment as _get_monthly_forecast_alignment,
)
from app.analytics.metrics import (
    align_all_pre_delivery_revisions as _align_all_pre_delivery_revisions,
    calculate_monthly_kpis as _calculate_monthly_kpis,
)
from app.models.schemas import MonthlyKPIs
from app.services.data_store import data_store


@lru_cache(maxsize=64)
def get_cached_monthly_alignment(decision_time_str: str) -> pd.DataFrame:
    """Cached monthly point-in-time alignment dataframe for a given decision cutoff."""
    return _get_monthly_forecast_alignment(
        decision_time_str=decision_time_str,
        df_fuelhh=data_store.get_fuelhh(),
        df_windfor=data_store.get_windfor(),
    )


@lru_cache(maxsize=128)
def get_cached_day_alignment(delivery_date_str: str, decision_time_str: str) -> pd.DataFrame:
    """Cached daily point-in-time alignment dataframe for a delivery date and decision cutoff."""
    delivery_date = pd.Timestamp(delivery_date_str).date()
    return _get_day_forecast_alignment(
        delivery_date=delivery_date,
        decision_time_str=decision_time_str,
        df_fuelhh=data_store.get_fuelhh(),
        df_windfor=data_store.get_windfor(),
    )


@lru_cache(maxsize=64)
def get_cached_all_pre_delivery_revisions() -> pd.DataFrame:
    """Cached complete pre-delivery revisions joined to actuals."""
    return _align_all_pre_delivery_revisions(
        df_windfor=data_store.get_windfor(),
        df_fuelhh=data_store.get_fuelhh(),
    )


@lru_cache(maxsize=64)
def get_cached_monthly_kpis(decision_time_str: str) -> MonthlyKPIs:
    """Cached monthly summary KPIs for a decision cutoff."""
    df = get_cached_monthly_alignment(decision_time_str)
    return _calculate_monthly_kpis(df, decision_time_str=decision_time_str)


def clear_analytics_cache() -> None:
    """Clear all LRU caches (useful during data ingestion reload or tests)."""
    get_cached_monthly_alignment.cache_clear()
    get_cached_day_alignment.cache_clear()
    get_cached_all_pre_delivery_revisions.cache_clear()
    get_cached_monthly_kpis.cache_clear()
