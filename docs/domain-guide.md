# UK Power Trading Domain & Market Mechanics Guide

This document explains the foundational domain concepts and analytical rules implemented across the forecast monitoring platform.

---

## 1. Settlement Periods & Delivery Timestamps

* **Settlement Period (SP):** The Great Britain (GB) electricity market operates on a half-hourly (HH) basis governed by Elexon under the Balancing and Settlement Code (BSC). A standard 24-hour day contains **48 Settlement Periods**:
  * **SP 1:** 00:00 – 00:30 local/clock time
  * **SP 2:** 00:30 – 01:00 local/clock time
  * ...
  * **SP 48:** 23:30 – 24:00 local/clock time
* **`startTime`:** In Elexon BMRS APIs, timestamps are reported in ISO-8601 UTC and represent the beginning of the delivery interval.
  $$\text{SP} = 2 \times \text{Hour} + \lfloor \text{Minute} / 30 \rfloor + 1$$
* **UTC vs UK Local Time:** In January, UK Local Time is strictly Greenwich Mean Time (**GMT = UTC+0**). UTC and UK local time are identical ($\Delta = 0\text{ hours}$).

---

## 2. Elexon Datasets: `FUELHH` and `WINDFOR`

1. **`FUELHH` (Half-Hourly Generation by Fuel Type):**
   * Filter: `fuelType == 'WIND'`
   * Outturn generation in Megawatts (MW) for each half-hour.
2. **`WINDFOR` (Wind Generation Forecast):**
   * Fields: `startTime` (delivery time), `publishTime` (when the forecast was released), `generation` (MW).
   * **Forecast Horizon (Lead Time):**
     $$\text{Horizon} = \text{startTime} - \text{publishTime}$$

---

## 3. Day-Ahead Auction Mechanics & Information Leakage

* **Auction Timelines:** On Day D-1, orders in the EPEX SPOT GB Day-Ahead Auction close at **11:00 GMT**. Internal trading desks establish valuation cutoffs (typically **09:00 GMT**) to freeze models and submit bids.
* **Why "Latest" vs "Latest Before Cutoff" Matters:** A naive $\max(\text{publishTime})$ across the dataset selects forecasts issued during Day D (intraday), just hours before delivery. This causes severe **look-ahead bias / information leakage**, artificially suppressing forecast error by 20% to 40% and masking true overnight physical risk.
* **Point-in-Time Rule:**
  $$\text{Selected Forecast} = \arg\max_{\text{publishTime} \le \text{Cutoff}_{(D-1)}} (\text{publishTime})$$

---

## 4. Assumptions & Ambiguities Table

| # | Assumption | Why We Assumed It | How It's Configurable | Risk / Trade-Off |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Decision Cutoff Default: 09:00 GMT on D-1** | Traders submit bids before 11:00 GMT auction gate closure, requiring inputs to freeze by ~09:00 GMT. | Configurable via UI selector (presets: `07:00`, `09:00`, `11:00`, `12:00` or custom `HH:MM`). | If a trader submits bids at 10:55, a 09:00 cutoff misses 10:00 weather runs. Resolved by interactive selector. |
| **2** | **Hourly WINDFOR Mapped to Half-Hourly FUELHH** | In BMRS, `WINDFOR` is published for hourly slots (`:00`), whereas `FUELHH` actuals are half-hourly (`:00` and `:30`). In power markets, MW is an instantaneous flow rate; an hourly rate of $X\text{ MW}$ applies across both half-hours. | Handled automatically via `startTime.dt.floor('h')`. | Real generation ramps intra-hour. Step-mapping introduces slight ramp error, but preserves 100% data coverage without synthetic curves. |
| **3** | **NMAE Normalised by Mean and Max Observed Actual** | No installed-capacity assumption is needed. Percentage error is expressed as `MAE / mean(actual)` and `MAE / max(actual)`, both computed from the same January 2026 dataset. | Automatically derived from the aligned dataset; no external config. | Mean-normalised NMAE rises when the fleet runs below rated output (e.g. calm periods). Max-normalised NMAE is more stable across wind regimes. |
| **4** | **BM-Reported Wind vs Embedded / Micro Wind** | BMRS datasets (`FUELHH`, `WINDFOR`) cover transmission-metered wind BM units. Distributed wind is treated as negative demand. | Fixed by Elexon dataset scope. | Reflects the exact volume cleared and settled under BSC rules. |
| **5** | **Over-Forecasting = Shortfall (Long Risk)** | $\text{Error} = \text{Forecast} - \text{Actual}$. If $\text{Forecast} > \text{Actual}$, the desk sold power day-ahead thinking wind would generate, but physical outturn was short, incurring System Buy Price imbalance settlement charges. | Hardcoded formula: $\text{Forecast} - \text{Actual}$; shortfall is $\max(0, \text{Forecast} - \text{Actual})$. | Some meteorological papers define error as $\text{Actual} - \text{Forecast}$. In our trading app, positive error is explicitly documented as **Over-Forecast / Shortfall**. |
| **6** | **Calendar Scope: January 2026** | Explicit user requirement. Real Elexon BMRS January 2026 data is ingested and cached. | Date picker navigates Jan 1 to Jan 31, 2026. | Extending to other months requires running the ingestion pipeline chunker for the requested date window. |
