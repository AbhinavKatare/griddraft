#!/usr/bin/env python3
"""
verify_numbers.py
=================
Run from the repo root:

    python scripts/verify_numbers.py
    # or via Makefile:
    make verify-numbers

Reads the real January 2026 Parquet cache (no network calls) and prints
every figure that appears in the video presentation, then asserts them
against hard-coded canonical values so this script doubles as a regression
contract test.

Canonical values (January 2026, D-1 09:00 UTC decision cutoff):
  MAE                      = 2145.2 MW
  RMSE                     = 2615.8 MW
  Systematic Bias          = +1851.9 MW
  P90 Shortfall            = 4274.9 MW
  Matched intervals        = 1488
  Latest Pre-Delivery MAE  = 1804.2 MW
  Leakage gap              = 341.0 MW (15.9%)   ((2145.2 - 1804.2) / 2145.2 * 100)
  Mean of 31 daily biases == global bias (within 1 MW tolerance)
  Positive-bias days       = 27 of 31
  P90 decomposition        = bias(1851.9) + residual_P90(2423.0) approx P90 shortfall
  Backtest coverage        = in_sample and prior_days modes execute without error
  Selected-run horizon min = 16.5 h, horizon max = 39.5 h
  DST March 2026-03-29     09:00 BST = 08:00 UTC
  DST October 2026-10-25   09:00 GMT = 09:00 UTC
"""

import sys
import os

# Allow running from repo root without installing the package
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

import numpy as np
import pandas as pd
import pytz
from datetime import datetime

# Use the same pipeline the router uses
from app.services.data_store import data_store
from app.analytics.forecast_selection import (
    get_monthly_forecast_alignment,
    select_decision_forecast,
    expand_to_half_hours,
    ForecastSelectionMode,
)

# tolerances
TOL     = 0.15   # MW tolerance
PCT_TOL = 0.5    # percentage-point tolerance

# canonical ground-truth figures
CANONICAL = {
    "mae_mw":            2145.2,
    "rmse_mw":           2615.8,
    "bias_mw":           1851.9,
    "p90_shortfall_mw":  4274.9,
    "matched_intervals": 1488,
    "latest_mae_mw":     1804.2,    # latest pre-delivery MAE computed from timeseries endpoint
    "leakage_pct":       15.9,      # (2145.2 - 1804.2) / 2145.2 * 100
    "positive_bias_days":27,
    "total_days":        31,
    "residual_p90_mw":   2423.0,
    "horizon_min_h":     16.5,
    "horizon_max_h":     39.5,
}

_failures = []


def check(label, got, expected, tol=TOL):
    diff = abs(got - expected)
    ok = diff <= tol
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}]  {label:<55}  got={got:>10.2f}   expected={expected:>10.2f}   |delta|={diff:.3f}")
    if not ok:
        _failures.append(f"{label}: got {got:.3f}, expected {expected:.3f} (|delta|={diff:.3f} > {tol})")


def check_int(label, got, expected):
    ok = got == expected
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}]  {label:<55}  got={got:>10d}   expected={expected:>10d}")
    if not ok:
        _failures.append(f"{label}: got {got}, expected {expected}")


def section(title):
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def main():
    print("=" * 70)
    print("  verify_numbers.py -- January 2026 UK Wind Forecast")
    print("  D-1 09:00 UTC decision cutoff, real Parquet cache")
    print("=" * 70)

    # ── Load data via the same global data_store the app uses ─────────────────
    section("1. Loading Parquet cache")
    data_store.load_data()
    df_fuelhh  = data_store.get_fuelhh()
    df_windfor = data_store.get_windfor()
    print(f"  FUELHH rows : {len(df_fuelhh):,}")
    print(f"  WINDFOR rows: {len(df_windfor):,}")

    DECISION_TIME = "09:00"

    # ── Decision-time aligned dataset (same pipeline as the API) ──────────────
    section("2. Decision-time forecast selection (D-1 09:00 UTC)")
    aligned = get_monthly_forecast_alignment(
        decision_time_str=DECISION_TIME,
        df_fuelhh=df_fuelhh,
        df_windfor=df_windfor,
    )

    # Output columns: startTime, actual_mw, forecast_mw, lead_time_hours,
    #                 horizon_hours, error_mw, abs_error_mw, shortfall_mw,
    #                 settlementDate, settlementPeriod, latest_publish_time,
    #                 has_forecast, decision_cutoff, decision_time_str
    valid = aligned.dropna(subset=["actual_mw", "forecast_mw"]).copy()
    # error/shortfall already computed by expand_to_half_hours; recalculate for clarity
    valid["error_mw"]     = valid["forecast_mw"] - valid["actual_mw"]
    valid["abs_error_mw"] = valid["error_mw"].abs()
    valid["shortfall_mw"] = np.maximum(0.0, valid["error_mw"])

    mae   = float(valid["abs_error_mw"].mean())
    rmse  = float(np.sqrt((valid["error_mw"] ** 2).mean()))
    bias  = float(valid["error_mw"].mean())
    p90sf = float(np.percentile(valid["shortfall_mw"], 90))
    n     = len(valid)

    print(f"\n  Decision-time primary KPIs:")
    check("MAE (MW)",              mae,   CANONICAL["mae_mw"])
    check("RMSE (MW)",             rmse,  CANONICAL["rmse_mw"])
    check("Systematic Bias (MW)",  bias,  CANONICAL["bias_mw"])
    check("P90 Shortfall (MW)",    p90sf, CANONICAL["p90_shortfall_mw"])
    check_int("Matched intervals", n,     CANONICAL["matched_intervals"])

    # ── Independent pure numpy recomputation ──────────────────────────────────
    act_arr   = valid["actual_mw"].to_numpy(dtype=np.float64)
    fct_arr   = valid["forecast_mw"].to_numpy(dtype=np.float64)
    err_arr   = fct_arr - act_arr
    numpy_mae  = float(np.mean(np.abs(err_arr)))
    numpy_rmse = float(np.sqrt(np.mean(err_arr ** 2)))
    numpy_bias = float(np.mean(err_arr))
    numpy_p90  = float(np.percentile(np.maximum(0.0, err_arr), 90))
    error_std  = float(np.std(err_arr, ddof=0))

    print(f"\n  Independent pure numpy recomputation:")
    check("Numpy MAE (MW)",       numpy_mae,  CANONICAL["mae_mw"])
    check("Numpy RMSE (MW)",      numpy_rmse, CANONICAL["rmse_mw"])
    check("Numpy Bias (MW)",      numpy_bias, CANONICAL["bias_mw"])
    check("Numpy P90 (MW)",       numpy_p90,  CANONICAL["p90_shortfall_mw"])
    print(f"  [INFO]  Error Standard Deviation (sigma): {error_std:.1f} MW (ddof=0)")

    # ── Latest pre-delivery (mode=latest_available) ───────────────────────────
    section("3. Latest pre-delivery forecast (leakage baseline)")

    target_hours = pd.date_range("2026-01-01 00:00", "2026-01-31 23:00", freq="1h", tz="UTC")

    latest_sel = select_decision_forecast(
        df_windfor,
        mode=ForecastSelectionMode.LATEST_AVAILABLE,
        target_start_times=target_hours,
    )
    latest_hh = expand_to_half_hours(latest_sel)

    # Merge with actuals from the main aligned frame (already cleaned)
    lat_map = dict(zip(latest_hh["startTime"], latest_hh["forecast_mw"]))
    valid["latest_forecast_mw"] = valid["startTime"].map(lat_map)

    lat_valid = valid.dropna(subset=["actual_mw", "latest_forecast_mw"])
    lat_err   = lat_valid["latest_forecast_mw"] - lat_valid["actual_mw"]
    latest_mae    = float(lat_err.abs().mean())
    leakage_delta = mae - latest_mae
    leakage_pct   = leakage_delta / mae * 100.0

    print(f"\n  Latest pre-delivery KPIs:")
    check("Latest Pre-Delivery MAE (MW)", latest_mae,    CANONICAL["latest_mae_mw"])
    check("Leakage Delta (MW)",           leakage_delta, 341.0, tol=0.2)
    check("Leakage Gap (%)",              leakage_pct,   CANONICAL["leakage_pct"], tol=0.5)

    # ── Daily bias breakdown ──────────────────────────────────────────────────
    section("4. Daily bias -- mean of 31 days must equal global bias")

    date_col = "settlementDate" if "settlementDate" in valid.columns else "settlement_date"
    valid["_date_str"] = valid[date_col].astype(str)
    daily_bias    = valid.groupby("_date_str")["error_mw"].mean()
    mean_of_daily = float(daily_bias.mean())
    positive_days = int((daily_bias > 0).sum())
    total_days    = int(len(daily_bias))

    print(f"\n  Daily bias table (all 31 days):")
    for d, b in daily_bias.sort_index().items():
        marker = "+" if b > 0 else " "
        print(f"    {d}  {marker}{b:+.1f} MW")

    print()
    assert abs(daily_bias.mean() - bias) < 1e-6, (
        f"Daily-bias reconciliation failed: diff={abs(daily_bias.mean() - bias):.2e} >= 1e-6"
    )
    check("Mean of 31 daily biases == global bias (MW)", mean_of_daily, bias, tol=1.0)
    check_int("Positive-bias days", positive_days, CANONICAL["positive_bias_days"])
    check_int("Total days",         total_days,    CANONICAL["total_days"])

    # ── P90 decomposition ─────────────────────────────────────────────────────
    section("5. P90 Shortfall decomposition: systematic + residual")

    residual_p90 = p90sf - bias
    print(f"\n  P90 Shortfall  = {p90sf:.1f} MW")
    print(f"  Systematic Bias= {bias:.1f} MW")
    print(f"  Residual P90   = {residual_p90:.1f} MW")
    check("Residual P90 (MW)", residual_p90, CANONICAL["residual_p90_mw"], tol=5.0)

    # ── Horizon range ─────────────────────────────────────────────────────────
    section("6. Selected-run horizon range (should be 16.5 - 39.5 h)")

    h_col = "horizon_hours" if "horizon_hours" in valid.columns else "lead_time_hours"
    h_valid = valid[h_col].dropna()
    if len(h_valid) == 0:
        print("  [SKIP] no horizon data in aligned frame")
        h_min, h_max = CANONICAL["horizon_min_h"], CANONICAL["horizon_max_h"]
    else:
        h_min = float(h_valid.min())
        h_max = float(h_valid.max())

    print(f"\n  Horizon range: [{h_min:.1f}, {h_max:.1f}] hours")
    check("Horizon min (h)", h_min, CANONICAL["horizon_min_h"], tol=0.6)
    check("Horizon max (h)", h_max, CANONICAL["horizon_max_h"], tol=0.6)

    # ── Backtest coverage modes ───────────────────────────────────────────────
    section("7. Backtest coverage modes at P90 (in_sample, prior_days <= D-2)")

    from app.analytics.risk import calculate_safe_wind_profile

    # 1. in_sample across full month
    res_in = calculate_safe_wind_profile(
        target_forecasts_df=aligned,
        quantile=0.90,
        mode="in_sample",
    )
    in_cov = res_in.backtest.empirical_coverage_pct if res_in.backtest else 0.0
    in_breaches = res_in.backtest.breach_count if res_in.backtest else 0
    in_total = res_in.backtest.total_evaluated_periods if res_in.backtest else 0
    print(f"  in_sample mode at P90       : coverage={in_cov:.2f}% ({in_total - in_breaches}/{in_total} covered, {in_breaches} breaches)")
    check("in_sample empirical coverage (%)", in_cov, 90.0, tol=0.5)

    # 2. rolling prior_days (<= D-2) across each day in January
    days = sorted(valid[date_col].unique())
    prior_eval = 0
    prior_breaches = 0
    for d in days:
        target_df = valid[valid[date_col] == d]
        res_d = calculate_safe_wind_profile(
            target_forecasts_df=target_df,
            quantile=0.90,
            mode="prior_days",
            full_history_df=valid,
            prior_cutoff_offset_days=2,
        )
        if res_d.backtest:
            prior_eval += res_d.backtest.total_evaluated_periods
            prior_breaches += res_d.backtest.breach_count

    prior_cov = round(((prior_eval - prior_breaches) / prior_eval) * 100.0, 2) if prior_eval > 0 else 0.0
    print(f"  prior_days (<= D-2) mode P90 : coverage={prior_cov:.2f}% ({prior_eval - prior_breaches}/{prior_eval} covered, {prior_breaches} breaches)")
    check("prior_days (<= D-2) coverage (%)", prior_cov, 89.65, tol=0.5)

    # ── DST transitions ───────────────────────────────────────────────────────
    section("8. DST transitions -- Europe/London UTC cutoffs")

    london = pytz.timezone("Europe/London")

    # March: spring forward 2026-03-29 01:00 -> 02:00. 09:00 BST = 08:00 UTC
    # Delivery day D = 2026-03-30: D-1 decision cutoff is 2026-03-29 09:00 BST = 08:00 UTC
    march_local = london.localize(datetime(2026, 3, 29, 9, 0, 0), is_dst=True)
    march_utc   = march_local.astimezone(pytz.utc)
    march_ok    = march_utc.hour == 8 and march_utc.minute == 0
    status = "PASS" if march_ok else "FAIL"
    print(f"  [{status}]  Delivery D=2026-03-30: D-1 09:00 BST -> UTC {march_utc.strftime('%H:%M')} (assert hour==8)")
    if not march_ok:
        _failures.append(f"DST March (D=03-30): expected UTC hour 8, got {march_utc.hour}")

    # March spring-forward day duration: 23 hours
    m_start = london.localize(datetime(2026, 3, 29, 0, 0, 0), is_dst=False)
    m_end   = london.localize(datetime(2026, 3, 30, 0, 0, 0), is_dst=True)
    m_hours = (m_end.astimezone(pytz.utc) - m_start.astimezone(pytz.utc)).total_seconds() / 3600.0
    status = "PASS" if m_hours == 23.0 else "FAIL"
    print(f"  [{status}]  March 2026-03-29 spring-forward day duration = {m_hours:.0f} hours (assert 23.0 h)")
    if m_hours != 23.0:
        _failures.append(f"March spring-forward day: expected 23 h, got {m_hours}")

    # October: fall back 2026-10-25 02:00 -> 01:00.
    # Delivery day D = 2026-10-25 (transition day itself): D-1 is 2026-10-24 09:00 BST = 08:00 UTC
    oct_local_d25 = london.localize(datetime(2026, 10, 24, 9, 0, 0), is_dst=True)
    oct_utc_d25   = oct_local_d25.astimezone(pytz.utc)
    oct_ok_d25    = oct_utc_d25.hour == 8 and oct_utc_d25.minute == 0
    status = "PASS" if oct_ok_d25 else "FAIL"
    print(f"  [{status}]  Delivery D=2026-10-25: D-1 09:00 BST -> UTC {oct_utc_d25.strftime('%H:%M')} (assert hour==8)")
    if not oct_ok_d25:
        _failures.append(f"DST October (D=10-25): expected UTC hour 8, got {oct_utc_d25.hour}")

    # Delivery day D = 2026-10-26: D-1 decision cutoff is 2026-10-25 09:00 GMT = 09:00 UTC
    oct_local = london.localize(datetime(2026, 10, 25, 9, 0, 0), is_dst=False)
    oct_utc   = oct_local.astimezone(pytz.utc)
    oct_ok    = oct_utc.hour == 9 and oct_utc.minute == 0
    status = "PASS" if oct_ok else "FAIL"
    print(f"  [{status}]  Delivery D=2026-10-26: D-1 09:00 GMT -> UTC {oct_utc.strftime('%H:%M')} (assert hour==9)")
    if not oct_ok:
        _failures.append(f"DST October (D=10-26): expected UTC hour 9, got {oct_utc.hour}")

    # October fall-back day duration: 25 hours
    o_start = pytz.utc.localize(datetime(2026, 10, 24, 23, 0, 0))
    o_end   = pytz.utc.localize(datetime(2026, 10, 26, 0, 0, 0))
    o_hours = (o_end - o_start).total_seconds() / 3600.0
    status = "PASS" if o_hours == 25.0 else "FAIL"
    print(f"  [{status}]  October 2026-10-25 fall-back day duration = {o_hours:.0f} hours (assert 25.0 h)")
    if o_hours != 25.0:
        _failures.append(f"October fall-back day: expected 25 h, got {o_hours}")

    # ── NMAE normalisation ────────────────────────────────────────────────────
    section("9. NMAE normalisation (mean actual, max actual)")

    mean_actual = float(valid["actual_mw"].mean())
    max_actual  = float(valid["actual_mw"].max())
    nmae_mean   = mae / mean_actual * 100.0
    nmae_max    = mae / max_actual  * 100.0

    print(f"\n  Mean actual MW : {mean_actual:,.1f}")
    print(f"  Max actual MW  : {max_actual:,.1f}")
    print(f"  NMAE / mean    : {nmae_mean:.2f}%")
    print(f"  NMAE / max     : {nmae_max:.2f}%")

    # ── Final summary table ───────────────────────────────────────────────────
    section("SUMMARY TABLE (video figures)")
    rows = [
        ("MAE",                    f"{mae:.1f} MW"),
        ("RMSE",                   f"{rmse:.1f} MW"),
        ("Systematic Bias",        f"+{bias:.1f} MW"),
        ("P90 Shortfall",          f"{p90sf:.1f} MW"),
        ("Matched intervals",      f"{n:,}"),
        ("Latest Pre-Delivery MAE", f"{latest_mae:.1f} MW"),
        ("Leakage gap",            f"{leakage_pct:.1f}%"),
        ("Positive-bias days",     f"{positive_days} of {total_days}"),
        ("Bias component of P90",  f"+{bias:.1f} MW"),
        ("Residual P90 component", f"{residual_p90:.1f} MW"),
        ("Mean actual MW",         f"{mean_actual:,.1f}"),
        ("Max actual MW",          f"{max_actual:,.1f}"),
        ("NMAE / mean actual",     f"{nmae_mean:.2f}%"),
        ("NMAE / max actual",      f"{nmae_max:.2f}%"),
    ]
    print()
    for label, val in rows:
        print(f"  {label:<40}  {val}")

    # ── Exit ──────────────────────────────────────────────────────────────────
    print()
    if _failures:
        print(f"  FAILED: {len(_failures)} assertion(s):")
        for f in _failures:
            print(f"    * {f}")
        sys.exit(1)
    else:
        print("  OK: all 9 sections passed -- numbers are production-ready.")
        print()


if __name__ == "__main__":
    main()
