"""Point-in-time forecast selection engine for Day-Ahead energy trading.

Provides pure, vectorised functions to select the appropriate forecast for each delivery
target startTime without lookahead bias or information leakage.
"""

from datetime import date, datetime, time, timedelta, timezone
from enum import Enum
import logging
from typing import Any, Optional, Sequence, Tuple, Union
import numpy as np
import pandas as pd

from app.config import settings

logger = logging.getLogger(__name__)


class ForecastSelectionMode(str, Enum):
    """Forecast selection operational modes."""

    DECISION_CUTOFF = "decision_cutoff"
    LATEST_AVAILABLE = "latest_available"
    FIXED_HORIZON = "fixed_horizon"


def _parse_cutoff_time(cutoff: Union[str, int, float, time]) -> tuple[int, int, int]:
    """
    Parse a cutoff hour or time representation into (hour, minute, second).

    Accepts:
    - str: "09:00", "09:00:00", "11:30"
    - int / float: 9 (meaning 09:00), 9.5 (meaning 09:30), 11
    - datetime.time: time(9, 0)
    """
    if isinstance(cutoff, time):
        if not (0 <= cutoff.hour <= 23 and 0 <= cutoff.minute <= 59 and 0 <= cutoff.second <= 59):
            raise ValueError(f"Time-of-day out of valid range [00:00:00, 23:59:59]: {cutoff!r}")
        return cutoff.hour, cutoff.minute, cutoff.second

    if isinstance(cutoff, (int, float)):
        val = float(cutoff)
        if not (0.0 <= val < 24.0):
            raise ValueError(f"Cutoff hour must be in range [0, 24), got: {cutoff!r}")
        total_minutes = int(round(val * 60))
        hour = (total_minutes // 60) % 24
        minute = total_minutes % 60
        return hour, minute, 0

    if isinstance(cutoff, str):
        parts = cutoff.strip().split(":")
        try:
            hour = int(parts[0])
            minute = int(parts[1]) if len(parts) > 1 else 0
            second = int(parts[2]) if len(parts) > 2 else 0
            if 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59:
                return hour, minute, second
        except ValueError:
            pass

    raise ValueError(
        f"Invalid cutoff time format: {cutoff!r}. Expected 'HH:MM' (00:00 - 23:59), integer hour [0-23], or datetime.time."
    )


def parse_decision_time(time_str: str) -> Tuple[int, int]:
    """
    Parse HH:MM string into (hour, minute).
    Fallback to default 09:00 on unparseable inputs.
    """
    try:
        h, m, _ = _parse_cutoff_time(time_str)
        return h, m
    except Exception:
        return 9, 0


def calculate_cutoff_timestamp(
    delivery_date: date,
    decision_time_str: str = "09:00",
    cutoff_day_offset: int = 1,
) -> pd.Timestamp:
    """Calculate the strict decision cutoff timestamp in UTC."""
    if cutoff_day_offset < 0:
        raise ValueError(f"cutoff_day_offset must be >= 0, got {cutoff_day_offset}")
    h, m, s = _parse_cutoff_time(decision_time_str)
    decision_date = delivery_date - timedelta(days=cutoff_day_offset)
    dt = datetime(decision_date.year, decision_date.month, decision_date.day, h, m, s, tzinfo=timezone.utc)
    return pd.Timestamp(dt)


def select_decision_forecast(
    forecasts_df: pd.DataFrame,
    cutoff_time_of_day: Union[str, int, float, time] = "09:00",
    cutoff_day_offset: int = 1,
    mode: Union[ForecastSelectionMode, str] = ForecastSelectionMode.DECISION_CUTOFF,
    fixed_horizon_hours: float = 24.0,
    tz: str = "UTC",
    target_start_times: Optional[Union[Sequence[Any], pd.Series, pd.DatetimeIndex]] = None,
) -> pd.DataFrame:
    """
    Pure, fully-vectorised function to select the appropriate forecast revision for each target delivery startTime.

    IMPORTANT: Delivery targets in forecasts_df must be hourly (on the hour :00).
    In Great Britain, WINDFOR forecasts are published as hourly generation flow rates (MW).
    Use `expand_to_half_hours()` after selection to map each hourly forecast to both constituent
    half-hourly Settlement Periods.

    Modes:
    1. 'decision_cutoff' (default):
       Selects the latest forecast published on or before the auction decision cutoff on D - cutoff_day_offset.
       E.g., for delivery on 2026-01-02, with cutoff 09:00 and day_offset=1 (D-1),
       the cutoff timestamp is 2026-01-01 09:00:00 UTC.
    2. 'latest_available':
       Selects the latest forecast published strictly prior to delivery start (publishTime < startTime).
       Captures intraday forecast updates up to gate closure without ex-post leakage.
    3. 'fixed_horizon':
       Selects the latest forecast published on or before a fixed lead time ahead of delivery
       (publishTime <= startTime - fixed_horizon_hours). E.g. 24h ahead of delivery.

    Guarantees:
    - Pure function: does NOT mutate `forecasts_df`.
    - Fully vectorised: ZERO row loops (`iterrows`, `itertuples`, row-wise `apply`).
    - Row-wise selection: stable sort + `drop_duplicates(keep='last')` ensures that if the latest
      revision contains NaN generation, that NaN is preserved rather than falling back to an older revision.
    - Invariant clamping: Clamps cutoff so selected `publishTime <= cutoff <= startTime`.
    - Explicit missing target handling: targets with no forecast before the cutoff are
      retained in the output with `forecast_mw = NaN`, `publishTime = NaT`, and `has_forecast = False`.

    Parameters:
    -----------
    forecasts_df : pd.DataFrame
        DataFrame containing at least 'startTime', 'publishTime', and 'generation'.
    cutoff_time_of_day : str, int, float, or time, default "09:00"
        Time of day for the decision cutoff (e.g. "09:00", 9, time(9, 0)).
    cutoff_day_offset : int, default 1
        Days before delivery date when decision is made (1 = D-1, 0 = D intraday, 2 = D-2). Must be >= 0.
    mode : ForecastSelectionMode or str, default "decision_cutoff"
        Selection operational mode: 'decision_cutoff', 'latest_available', or 'fixed_horizon'.
    fixed_horizon_hours : float, default 24.0
        Lead time in hours for 'fixed_horizon' mode.
    tz : str, default "UTC"
        Timezone to interpret cutoff_time_of_day (e.g. "UTC" or "Europe/London").
    target_start_times : sequence of datetimes, optional
        Explicit delivery targets to evaluate. If None, uses all unique startTimes in forecasts_df.

    Returns:
    --------
    pd.DataFrame:
        Table indexed or sorted by 'startTime' containing:
        - startTime: UTC delivery start timestamp (datetime64[ns, UTC])
        - forecast_mw: Selected forecast in MW (float64, NaN if no valid forecast or latest was NaN)
        - publishTime: Publication timestamp of selected forecast (datetime64[ns, UTC], NaT if missing)
        - horizon_hours: Lead time hours = (startTime - publishTime) (float64, NaN if missing)
        - cutoff_time: Applicable cutoff threshold for target (datetime64[ns, UTC])
        - has_forecast: bool, True if valid forecast exists <= cutoff, False otherwise
        - selection_mode: str, mode identifier

    Worked Example:
    ---------------
    >>> import pandas as pd
    >>> from app.analytics.forecast_selection import select_decision_forecast
    >>>
    >>> df = pd.DataFrame([
    ...     # Target: Jan 2 12:00 UTC (D = Jan 2, Cutoff D-1 09:00 = Jan 1 09:00 UTC)
    ...     {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-01 07:30:00Z", "generation": 14500.0},
    ...     {"startTime": "2026-01-02 12:00:00Z", "publishTime": "2026-01-01 11:30:00Z", "generation": 15200.0}, # after cutoff!
    ...     # Target: Jan 2 14:00 UTC (Only published AFTER cutoff)
    ...     {"startTime": "2026-01-02 14:00:00Z", "publishTime": "2026-01-01 11:30:00Z", "generation": 13800.0},
    ... ])
    >>>
    >>> res = select_decision_forecast(df, cutoff_time_of_day="09:00", cutoff_day_offset=1)
    >>> print(res[["startTime", "publishTime", "forecast_mw", "horizon_hours", "has_forecast"]])
                       startTime               publishTime  forecast_mw  horizon_hours  has_forecast
    0  2026-01-02 12:00:00+00:00 2026-01-01 07:30:00+00:00      14500.0           28.5          True
    1  2026-01-02 14:00:00+00:00                       NaT          NaN            NaN         False
    """
    if cutoff_day_offset < 0:
        raise ValueError(f"cutoff_day_offset must be >= 0, got {cutoff_day_offset}")

    mode_str = mode.value if isinstance(mode, ForecastSelectionMode) else str(mode).lower()

    if forecasts_df.empty:
        cols = ["startTime", "forecast_mw", "publishTime", "horizon_hours", "cutoff_time", "has_forecast", "selection_mode"]
        return pd.DataFrame(columns=cols)

    # Coerce timestamps to UTC datetime64[ns, UTC]
    df = forecasts_df.copy()
    if not pd.api.types.is_datetime64_any_dtype(df["startTime"]):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    elif df["startTime"].dt.tz is None:
        df["startTime"] = df["startTime"].dt.tz_localize("UTC")
    else:
        df["startTime"] = df["startTime"].dt.tz_convert("UTC")

    if not pd.api.types.is_datetime64_any_dtype(df["publishTime"]):
        df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    elif df["publishTime"].dt.tz is None:
        df["publishTime"] = df["publishTime"].dt.tz_localize("UTC")
    else:
        df["publishTime"] = df["publishTime"].dt.tz_convert("UTC")

    df["generation"] = pd.to_numeric(df["generation"], errors="coerce")

    # Determine universe of target startTimes
    if target_start_times is not None:
        targets = pd.Series(target_start_times)
        if not pd.api.types.is_datetime64_any_dtype(targets):
            targets = pd.to_datetime(targets, utc=True)
        elif targets.dt.tz is None:
            targets = targets.dt.tz_localize("UTC")
        else:
            targets = targets.dt.tz_convert("UTC")
        all_targets = pd.DataFrame({"startTime": targets.drop_duplicates().sort_values()})
    else:
        all_targets = pd.DataFrame({"startTime": df["startTime"].drop_duplicates().sort_values()})

    # --------------------------------------------------------------------------
    # Vectorised Cutoff Timestamp Calculation & Invariant Clamping
    # --------------------------------------------------------------------------
    if mode_str == ForecastSelectionMode.DECISION_CUTOFF.value:
        hour, minute, second = _parse_cutoff_time(cutoff_time_of_day)
        cutoff_seconds = hour * 3600 + minute * 60 + second

        # Calculate cutoff vectorized across all delivery targets
        target_local = all_targets["startTime"].dt.tz_convert(tz)
        local_midnight = target_local.dt.floor("D")
        cutoff_local = (
            local_midnight
            - pd.to_timedelta(cutoff_day_offset, unit="D")
            + pd.to_timedelta(cutoff_seconds, unit="s")
        )
        calculated_cutoff = cutoff_local.dt.tz_convert("UTC")

        # Clamp invariant: cutoff_time <= startTime (never allow future cutoff after delivery)
        all_targets["cutoff_time"] = np.minimum(calculated_cutoff, all_targets["startTime"])

        # Map cutoff_time to candidate forecast rows via merge
        df = pd.merge(df, all_targets[["startTime", "cutoff_time"]], on="startTime", how="inner")
        valid_mask = df["publishTime"] <= df["cutoff_time"]

    elif mode_str == ForecastSelectionMode.LATEST_AVAILABLE.value:
        # Latest forecast published strictly before delivery startTime
        all_targets["cutoff_time"] = all_targets["startTime"]
        df = pd.merge(df, all_targets[["startTime", "cutoff_time"]], on="startTime", how="inner")
        valid_mask = df["publishTime"] < df["cutoff_time"]

    elif mode_str == ForecastSelectionMode.FIXED_HORIZON.value:
        # Latest forecast published at or before (startTime - fixed_horizon_hours)
        horizon_delta = pd.to_timedelta(fixed_horizon_hours, unit="h")
        all_targets["cutoff_time"] = all_targets["startTime"] - horizon_delta
        # Clamp invariant: cutoff_time <= startTime
        all_targets["cutoff_time"] = np.minimum(all_targets["cutoff_time"], all_targets["startTime"])
        df = pd.merge(df, all_targets[["startTime", "cutoff_time"]], on="startTime", how="inner")
        valid_mask = df["publishTime"] <= df["cutoff_time"]

    else:
        raise ValueError(
            f"Unknown mode: {mode!r}. Supported modes: "
            f"{[m.value for m in ForecastSelectionMode]}"
        )

    # --------------------------------------------------------------------------
    # Row-Wise Selection of Latest Forecast <= Cutoff (Sort Stable + Drop Duplicates)
    # --------------------------------------------------------------------------
    valid_candidates = df[valid_mask].copy()

    if not valid_candidates.empty:
        # Stable sort ensures deterministic ordering by publication time
        # drop_duplicates preserves the EXACT row of the latest revision even if generation is NaN
        sorted_candidates = valid_candidates.sort_values(
            by=["startTime", "publishTime"], kind="stable"
        )
        selected = sorted_candidates.drop_duplicates(subset=["startTime"], keep="last")
        selected = selected.rename(columns={"generation": "forecast_mw"})[
            ["startTime", "forecast_mw", "publishTime"]
        ]
    else:
        selected = pd.DataFrame(columns=["startTime", "forecast_mw", "publishTime"])

    # --------------------------------------------------------------------------
    # Full Alignment with All Target StartTimes (NaN + flag for missing)
    # --------------------------------------------------------------------------
    result = pd.merge(all_targets, selected, on="startTime", how="left")
    result["publishTime"] = pd.to_datetime(result["publishTime"], utc=True)

    # Flag: a forecast was selected if publishTime is present (even if generation was NaN)
    result["has_forecast"] = result["publishTime"].notna()
    result["horizon_hours"] = np.where(
        result["has_forecast"],
        (result["startTime"] - result["publishTime"]).dt.total_seconds() / 3600.0,
        np.nan,
    )
    result["selection_mode"] = mode_str

    # Order canonical columns
    ordered_cols = [
        "startTime",
        "forecast_mw",
        "publishTime",
        "horizon_hours",
        "cutoff_time",
        "has_forecast",
        "selection_mode",
    ]
    return result[ordered_cols].sort_values(by="startTime").reset_index(drop=True)


def expand_to_half_hours(
    hourly_forecasts_df: pd.DataFrame,
    actuals_df: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Expand hourly forecasts to half-hourly settlement periods by joining on `startTime.dt.floor('h')`.

    In Great Britain, WINDFOR forecasts represent hourly power flow rates (MW).
    Each hourly forecast for delivery hour H applies across both constituent half-hour
    Settlement Periods:
    - SP 2H-1 (H:00 to H:30)
    - SP 2H   (H:30 to H+1:00)

    NOTE: The target startTimes passed to `select_decision_forecast()` must be hourly (on the hour :00).
    Call `expand_to_half_hours()` to produce the final 48 half-hourly evaluation series.

    Parameters:
    -----------
    hourly_forecasts_df : pd.DataFrame
        DataFrame returned by `select_decision_forecast()`. Must contain 'startTime' and 'forecast_mw'.
    actuals_df : pd.DataFrame, optional
        Half-hourly FUELHH actuals DataFrame. If provided, merges actuals and forecasts on
        `delivery_hour = startTime.dt.floor('h')`. If None, generates :00 and :30 intervals.

    Returns:
    --------
    pd.DataFrame
        Half-hourly aligned DataFrame with settlement periods, error metrics, and canonical columns.
    """
    if hourly_forecasts_df.empty:
        return pd.DataFrame()

    hf = hourly_forecasts_df.copy()
    hf["delivery_hour"] = hf["startTime"].dt.floor("h")

    if actuals_df is not None and not actuals_df.empty:
        act = actuals_df.copy()
        act["delivery_hour"] = act["startTime"].dt.floor("h")

        # Merge half-hourly actuals with hourly forecast on delivery_hour
        merged = pd.merge(
            act,
            hf.rename(columns={
                "startTime": "forecast_hour",
                "publishTime": "latest_publish_time",
                "horizon_hours": "lead_time_hours",
            })[[
                "delivery_hour",
                "forecast_mw",
                "latest_publish_time",
                "lead_time_hours",
                "has_forecast",
            ]],
            on="delivery_hour",
            how="left",
        )

        # Standardise column names
        if "generation" in merged.columns and "actual_mw" not in merged.columns:
            merged = merged.rename(columns={"generation": "actual_mw"})

        # Assign Settlement Period & Settlement Date if missing
        if "settlementDate" not in merged.columns or merged["settlementDate"].isna().any():
            merged["settlementDate"] = merged["startTime"].dt.strftime("%Y-%m-%d")

        if "settlementPeriod" not in merged.columns or merged["settlementPeriod"].isna().any():
            periods = (merged["startTime"].dt.hour * 2) + (merged["startTime"].dt.minute // 30) + 1
            merged["settlementPeriod"] = periods
        merged["settlementPeriod"] = merged["settlementPeriod"].fillna(1).astype(int)

        # Compute point-by-point errors
        merged["horizon_hours"] = merged["lead_time_hours"]
        merged["error_mw"] = merged["forecast_mw"] - merged["actual_mw"]
        merged["abs_error_mw"] = merged["error_mw"].abs()
        merged["shortfall_mw"] = merged["error_mw"].apply(lambda x: max(0.0, x) if pd.notna(x) else np.nan)

        return merged.sort_values(by="startTime").reset_index(drop=True)

    else:
        # Generate two half-hours (:00 and :30) for each hourly forecast
        first_half = hf.copy()
        first_half["startTime"] = first_half["delivery_hour"]

        second_half = hf.copy()
        second_half["startTime"] = second_half["delivery_hour"] + pd.Timedelta(minutes=30)

        expanded = pd.concat([first_half, second_half], ignore_index=True)
        expanded["settlementDate"] = expanded["startTime"].dt.strftime("%Y-%m-%d")
        expanded["settlementPeriod"] = (
            (expanded["startTime"].dt.hour * 2) + (expanded["startTime"].dt.minute // 30) + 1
        )
        return expanded.sort_values(by="startTime").reset_index(drop=True)


def get_day_forecast_alignment(
    delivery_date: date,
    decision_time_str: str = settings.default_decision_time,
    df_fuelhh: Optional[pd.DataFrame] = None,
    df_windfor: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Align actuals and latest decision-time forecast for a single delivery date D.
    Ensures ZERO future leakage: only forecasts published on or before D-1 at decision_time_str are selected.
    """
    from app.services.data_store import data_store

    if df_fuelhh is None:
        df_fuelhh = data_store.get_fuelhh()
    if df_windfor is None:
        df_windfor = data_store.get_windfor()

    if df_fuelhh.empty or df_windfor.empty:
        return pd.DataFrame()

    start_of_day = pd.Timestamp(datetime(delivery_date.year, delivery_date.month, delivery_date.day, 0, 0, 0, tzinfo=timezone.utc))
    end_of_day = pd.Timestamp(datetime(delivery_date.year, delivery_date.month, delivery_date.day, 23, 30, 0, tzinfo=timezone.utc))

    actual_day = df_fuelhh[
        (df_fuelhh["startTime"] >= start_of_day) & (df_fuelhh["startTime"] <= end_of_day)
    ].copy()

    # Generate 24 hourly targets for day D
    hourly_targets = pd.date_range(
        start=start_of_day,
        periods=24,
        freq="1h",
        tz="UTC",
    )

    # Run vectorised forecast selection
    selected_hourly = select_decision_forecast(
        forecasts_df=df_windfor,
        cutoff_time_of_day=decision_time_str,
        cutoff_day_offset=1,
        target_start_times=hourly_targets,
    )

    # Expand to 48 half-hours with actuals
    aligned = expand_to_half_hours(selected_hourly, actuals_df=actual_day)

    cutoff_ts = calculate_cutoff_timestamp(delivery_date, decision_time_str, cutoff_day_offset=1)
    aligned["decision_cutoff"] = cutoff_ts
    aligned["decision_time_str"] = decision_time_str
    return aligned


def get_monthly_forecast_alignment(
    decision_time_str: str = settings.default_decision_time,
    df_fuelhh: Optional[pd.DataFrame] = None,
    df_windfor: Optional[pd.DataFrame] = None,
) -> pd.DataFrame:
    """
    Align entire January 2026 month with point-in-time cutoff on D-1.
    Returns combined DataFrame with all 31 days.
    """
    from app.services.data_store import data_store

    if df_fuelhh is None:
        df_fuelhh = data_store.get_fuelhh()
    if df_windfor is None:
        df_windfor = data_store.get_windfor()

    if df_fuelhh.empty or df_windfor.empty:
        return pd.DataFrame()

    days = [date(2026, 1, d) for d in range(1, 32)]
    day_frames = []
    for d in days:
        aligned_day = get_day_forecast_alignment(
            delivery_date=d,
            decision_time_str=decision_time_str,
            df_fuelhh=df_fuelhh,
            df_windfor=df_windfor,
        )
        if not aligned_day.empty:
            day_frames.append(aligned_day)

    if not day_frames:
        return pd.DataFrame()

    return pd.concat(day_frames, ignore_index=True)
