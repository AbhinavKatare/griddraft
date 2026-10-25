"""Computes exact metrics and answers for preliminary questions 1 to 4."""

from datetime import date, datetime, timedelta, timezone
import numpy as np
import pandas as pd

wf = pd.read_parquet("data/cache/windfor_jan2026.parquet")
wf["startTime"] = pd.to_datetime(wf["startTime"], utc=True)
wf["publishTime"] = pd.to_datetime(wf["publishTime"], utc=True)

fh = pd.read_parquet("data/cache/fuelhh_wind_jan2026.parquet")
fh["startTime"] = pd.to_datetime(fh["startTime"], utc=True)
fh["delivery_hour"] = fh["startTime"].dt.floor("h")

# 1. Distinct publishTime clock times (HH:MM) and their counts
wf["pub_clock"] = wf["publishTime"].dt.strftime("%H:%M")
clock_counts = wf["pub_clock"].value_counts().sort_index()
print("=== 1. DISTINCT PUBLISHTIME CLOCK TIMES (HH:MM) & COUNTS ===")
for clock, cnt in clock_counts.items():
    print(f"  {clock}: {cnt:,} records")

# 2. Earliest publishTime per target for 2026-01-01..03
wf_jan_targets = wf[(wf["startTime"] >= "2026-01-01 00:00:00+00:00") & (wf["startTime"] <= "2026-01-03 23:00:00+00:00")]
earliest_per_target = wf_jan_targets.groupby("startTime")["publishTime"].min()
print("\n=== 2. EARLIEST PUBLISHTIME PER TARGET (2026-01-01 to 2026-01-03) ===")
print("Earliest publishTime for Jan 1 00:00 to 03:00:")
for t, pub in earliest_per_target.head(4).items():
    print(f"  Target {t} -> Earliest Publish: {pub} (Horizon: {(t - pub).total_seconds()/3600:.1f}h)")

# 3A. For 2026-01-01 00:00:
actual_00 = fh[fh["startTime"] == "2026-01-01 00:00:00+00:00"]["generation"].values[0]

cutoff_0101 = pd.Timestamp("2025-12-31 09:00:00", tz="UTC")
fc_dec_00_rows = wf[(wf["startTime"] == "2026-01-01 00:00:00+00:00") & (wf["publishTime"] <= cutoff_0101)].sort_values("publishTime")
fc_dec_00 = fc_dec_00_rows.iloc[-1]["generation"]
fc_dec_00_pub = fc_dec_00_rows.iloc[-1]["publishTime"]

post_rows = wf[(wf["startTime"] == "2026-01-01 00:00:00+00:00") & (wf["publishTime"] > "2026-01-01 00:00:00+00:00")].sort_values("publishTime")
post_flat_val = post_rows.iloc[-1]["generation"]
post_flat_pubs = post_rows["generation"].unique()

print("\n=== 3A. TARGET 2026-01-01 00:00:00 ===")
print(f"Actual Outturn (FUELHH):            {actual_00:,.1f} MW")
print(f"Decision-Time Forecast (D-1 09:00): {fc_dec_00:,.1f} MW (published {fc_dec_00_pub})")
print(f"Post-Delivery Flat Value:          {post_flat_val:,.1f} MW (unique post-delivery values: {post_flat_pubs})")

# 3B. Compute full month:
days = [date(2026, 1, d) for d in range(1, 32)]
aligned_dec = []
aligned_latest = []

for d in days:
    cutoff = pd.Timestamp(datetime(d.year, d.month, d.day, 9, 0, 0, tzinfo=timezone.utc) - timedelta(days=1))
    day_start = pd.Timestamp(datetime(d.year, d.month, d.day, 0, 0, 0, tzinfo=timezone.utc))
    day_end = pd.Timestamp(datetime(d.year, d.month, d.day, 23, 30, 0, tzinfo=timezone.utc))

    sub_fh = fh[(fh["startTime"] >= day_start) & (fh["startTime"] <= day_end)].copy()
    sub_wf_dec = wf[(wf["startTime"] >= day_start) & (wf["startTime"] <= day_end) & (wf["publishTime"] <= cutoff)]
    sub_wf_all = wf[(wf["startTime"] >= day_start) & (wf["startTime"] <= day_end)]

    latest_dec = sub_wf_dec.sort_values(["startTime", "publishTime"]).groupby("startTime").last().reset_index()
    latest_dec = latest_dec.rename(columns={"generation": "fc_dec", "publishTime": "pub_dec"})[["startTime", "fc_dec", "pub_dec"]]
    latest_dec["delivery_hour"] = latest_dec["startTime"]

    latest_overall = sub_wf_all.sort_values(["startTime", "publishTime"]).groupby("startTime").last().reset_index()
    latest_overall = latest_overall.rename(columns={"generation": "fc_latest", "publishTime": "pub_latest"})[["startTime", "fc_latest", "pub_latest"]]
    latest_overall["delivery_hour"] = latest_overall["startTime"]

    m_dec = pd.merge(sub_fh, latest_dec[["delivery_hour", "fc_dec", "pub_dec"]], on="delivery_hour", how="inner")
    m_all = pd.merge(sub_fh, latest_overall[["delivery_hour", "fc_latest", "pub_latest"]], on="delivery_hour", how="inner")

    aligned_dec.append(m_dec)
    aligned_latest.append(m_all)

df_dec = pd.concat(aligned_dec, ignore_index=True)
df_latest = pd.concat(aligned_latest, ignore_index=True)

err_dec = df_dec["fc_dec"] - df_dec["generation"]
mean_err_dec = err_dec.mean()
mae_dec = err_dec.abs().mean()
rmse_dec = np.sqrt((err_dec**2).mean())

err_latest = df_latest["fc_latest"] - df_latest["generation"]
mean_err_latest = err_latest.mean()
mae_latest = err_latest.abs().mean()
rmse_latest = np.sqrt((err_latest**2).mean())

print("\n=== 3B. FULL MONTH METRICS (1,488 HALF-HOURS) ===")
print("--- Decision-Time Forecast (D-1 09:00 Cutoff) ---")
print(f"Mean Error (Bias): {mean_err_dec:+,.1f} MW")
print(f"MAE:               {mae_dec:,.1f} MW")
print(f"RMSE:              {rmse_dec:,.1f} MW")

print("\n--- Using Absolute Latest Forecast (Includes Post-Delivery / Ex-Post) ---")
print(f"Mean Error (Bias): {mean_err_latest:+,.1f} MW")
print(f"MAE:               {mae_latest:,.1f} MW")
print(f"RMSE:              {rmse_latest:,.1f} MW")

# 4. Distribution of horizon of selected forecast
df_dec["selected_horizon_h"] = (df_dec["startTime"] - df_dec["pub_dec"]).dt.total_seconds() / 3600.0
print("\n=== 4. DISTRIBUTION OF HORIZON OF SELECTED FORECAST (D-1 09:00 CUTOFF) ===")
print(f"Min horizon:    {df_dec['selected_horizon_h'].min():.1f} hours")
print(f"Median horizon: {df_dec['selected_horizon_h'].median():.1f} hours")
print(f"Mean horizon:   {df_dec['selected_horizon_h'].mean():.1f} hours")
print(f"Max horizon:    {df_dec['selected_horizon_h'].max():.1f} hours")
print("Quantiles:")
for q in [0.0, 0.25, 0.5, 0.75, 1.0]:
    print(f"  {int(q*100)}%: {df_dec['selected_horizon_h'].quantile(q):.1f} hours")
