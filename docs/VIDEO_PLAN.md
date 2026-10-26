# UK Wind Forecast Decision Tool — 10-Minute Video Script & Presentation Guide

This document contains the exact, word-for-word rehearsal script, click-by-click UI actions, mouse positions, code walkthrough cues, and technical talking points.

---

## High-Level Video Blueprint

| Segment | Timing | Target Audience | Primary Goal |
| :--- | :--- | :--- | :--- |
| **Part 1: Customer Presentation** | **0:00 – 4:45** (max 5:00) | Power Trading Desk Head, Portfolio Manager, Risk Officer | **Impress them**: Show pilot findings, commercial savings, causal leakage trap, and live portal demo |
| **Part 2: Tech Lead Walkthrough** | **4:45 – 9:30** (max 5:00) | Engineering Lead, Quantitative Architect, Reviewer | **Make review easy**: Full knowledge transfer, architecture, storage design, causal invariants, 100% test coverage |
| **Wrap-Up & Submission** | **9:30 – 10:00** (30 sec) | Both | Quick recap and public deployment verification |

---

## Pre-Recording Checklist (Complete 2 Minutes Before Hitting Record)

1. **Wake Render Backend**:
   - Open [https://griddraft.onrender.com/health](https://griddraft.onrender.com/health) in a browser tab. Confirm JSON response: `{"status":"healthy","version":"1.0.0","cache_loaded":true}`.
2. **Open Production Portal**:
   - Open [https://griddraft-one.vercel.app](https://griddraft-one.vercel.app) in Google Chrome (full-screen `F11` or maximized).
   - Set zoom level to **110%** or **125%** so typography and charts look bold and legible on 1080p video.
   - Confirm dark theme is active.
3. **Open IDE / Code Editor**:
   - Split editor or tabs ready:
     - `backend/app/analytics/forecast_selection.py` (Line 115)
     - `backend/app/analytics/risk.py` (Line 45)
     - `README.md` (Mermaid diagram around line 42)
     - Terminal tab with `python scripts/verify_numbers.py` ready.
4. **Audio & Screen Settings**:
   - Record system audio off / microphone on.
   - Resolution: 1920x1080 at 30 or 60 fps.

---

# Part 1: Customer Presentation (Pilot Project Output)
**Audience:** Head of Day-Ahead Power Trading & Quantitative Portfolio Manager  
**Tone:** Confident Senior Energy Quant. Direct, commercial, numbers-first.  
**Target Duration:** Exactly 4 minutes 30 seconds (Hard stop at 4:50).

---

### [0:00 – 0:50] 1. The Hook: The Systematic Over-Forecasting Hazard
- **Screen:** Full-screen browser on `https://griddraft-one.vercel.app` (Decision View).
- **Mouse Action:** Hover briefly over the Hero Chart peak.
- **Word-for-Word Script:**
  > *"Good morning. Over the last four weeks, we conducted a quantitative pilot project for your UK power trading desk, evaluating National Grid ESO's Day-Ahead wind generation forecasts against actual metered outturn across all 1,488 settlement periods of January 2026.*
  > 
  > *If you trade Day-Ahead power, your physical nominations are locked in before the 11:00 auction on D-1. If the national wind forecast tells your desk you will generate 14,000 MW, but outturn drops to 11,000 MW, your book is caught 3,000 MW short. That deficit is settled at punishing system imbalance cashout prices.*
  > 
  > *Our pilot revealed two critical findings: first, National Grid's models over-forecast in **27 out of 31 days** in January, with an average bias of **+1,852 MW**. Second, desks backtesting their trading algorithms routinely use forecasts published after the D-1 auction cutoff. That is **information leakage**—and it severely understates your true volumetric risk.*
  > 
  > *Today, I'm presenting the portal we engineered to solve this: the **UK Wind Forecast Decision Tool**."*

---

### [0:50 – 2:30] 2. Live Interactive Portal Demo (Click-by-Click)

#### Action 1: Point Out the Global Control Room & Lineage [0:50 – 1:20]
- **Mouse Action / Click:**
  - Move mouse to the **Global Controls Bar** at the top.
  - Hover over **Delivery Date**: `2026-01-15`.
  - Click on **Decision Cutoff**: confirm `09:00 UTC` is selected.
  - Point to the **Run Lineage Alert Banner** directly above the chart.
- **Word-for-Word Script:**
  > *"Here is the production platform. Notice the Controls Bar at the top. We are viewing delivery for **January 15, 2026** at the standard desk risk cutoff of **09:00 UTC on D-1**.*
  > 
  > *Look at the Run Lineage banner below: it explicitly confirms that every forecast point displayed was published on or before **09:00 UTC on January 14**. We enforce mathematical causality: not a single intra-day revision published after your auction cutoff is allowed to leak into this view."*

#### Action 2: The Summary Strip & Safe Wind Derating [1:20 – 1:55]
- **Mouse Action / Click:**
  - Move mouse smoothly across the 3 top KPI summary cards in the **Summary Metric Strip**:
    - Card 1: **Nominal Forecast**: `331,100 MWh`
    - Card 2: **Safe Wind (P90)**: `228,500 MWh`
    - Card 3: **Peak Procurement**: `2,200 MW`
- **Word-for-Word Script:**
  > *"Notice what the decision engine does with this data in the Summary Strip.*
  > 
  > *If your trader sells nominal forecast volume, they would bid **331.1 GWh** into the Day-Ahead auction. But look at the amber line on our chart: our P90 Safe Wind model derates that volume to **228.5 GWh**.*
  > 
  > *That leaves an implied peak shortfall of **2,200 MW**. Instead of waiting for the balancing mechanism to fine your desk at volatile cashout prices, our tool immediately sizes your backup thermal replacement contracts in advance."*

#### Action 3: Exposing the Information Leakage Trap [1:55 – 2:30]
- **Mouse Action / Click:**
  - Click the **"Leaky Baseline"** toggle switch in the Control Bar.
  - Watch the dashed grey line appear on the Hero Chart.
  - Hover over Period 24 (12:00) where the dashed line is higher than the solid line.
- **Word-for-Word Script:**
  > *"Now watch what happens when I click this toggle: **Leaky Baseline**.*
  > 
  > *This dashed grey curve appears. That is the latest pre-delivery forecast published right before gate closure. Notice how dramatically it shifted from our solid decision baseline.*
  > 
  > *If a quant on your desk evaluates forecast quality using that dashed curve, they will conclude the forecast was accurate. But your trader had to commit at 09:00 on D-1! Relying on post-cutoff data gives you false confidence; our solid baseline represents the actual reality your capital faced."*

---

### [2:30 – 4:00] 3. The 3 Executive Findings (Real January 2026 Data)

#### Action 4: Navigate to Accuracy Suite [2:30 – 2:45]
- **Mouse Action / Click:**
  - Click the **"Accuracy"** tab in the main navigation bar.
  - Notice the URL changes instantaneously to `/?view=accuracy` with state preserved.
- **Word-for-Word Script:**
  > *"Let's switch to the **Accuracy Suite** to examine the full-month ground truth across all 1,488 settlement periods."*

#### Finding 1: The +1,852 MW Systematic Over-Forecast Bias [2:45 – 3:15]
- **Mouse Action:**
  - Point mouse to **Card 3 (Systematic Bias)** and the **Bias Advisory Banner** above it.
- **Word-for-Word Script:**
  > *"Finding Number 1: **Systematic Over-Forecasting**.*
  > 
  > *Across all 1,488 settlement intervals in January 2026, National Grid's models over-forecasted wind generation with a mean bias of **+1,851.9 MW**. As highlighted in this alert banner, the model was over-forecast in **27 out of 31 days** (87.1% of the month). A desk that sells nominal wind is structurally short 87% of the time."*

#### Finding 2: The 341 MW Information Leakage Penalty [3:15 – 3:45]
- **Mouse Action:**
  - Point mouse to **Card 1 (Mean Absolute Error - MAE)** and the small badge below it.
- **Word-for-Word Script:**
  > *"Finding Number 2: **The 341 MW Information Leakage Penalty**.*
  > 
  > *At your true D-1 09:00 decision cutoff, the monthly MAE is **2,145.2 MW**—which represents **18.52% of mean actual generation**. But if you evaluate against latest pre-delivery forecasts, MAE drops to **1,804.2 MW**.*
  > 
  > *That **341 MW gap**—a 15.9% difference—is pure information leakage. Desks that don't account for point-in-time cutoffs are underestimating their volumetric risk by nearly 16%."*

#### Finding 3: The 4,275 MW P90 Shortfall Buffer [3:45 – 4:10]
- **Mouse Action:**
  - Point mouse to **Card 4 (P90 Shortfall Buffer)** showing `4,274.9 MW`.
- **Word-for-Word Script:**
  > *"Finding Number 3: **The P90 Shortfall Buffer**.*
  > 
  > *To trade with 90% volumetric certainty, the desk needs a **4,275 MW buffer**. Crucially, our platform decomposes this: **+1,852 MW** is pure systematic bias, and **2,423 MW** is residual weather uncertainty."*

---

### [4:10 – 4:45] 4. Commercial Value & Customer Pitch Wrap-Up
- **Screen:** Hover over the Daily Bias chart at the bottom of the Accuracy page.
- **Word-for-Word Script:**
  > *"Why is this decomposition transformative for your desk?*
  > 
  > *Because systematic bias is predictable. You don't need to buy expensive, flexible tolling agreements to cover the entire 4,275 MW. You simply derate your Day-Ahead auction bids by 1,852 MW, and size your replacement hedges strictly for the true 2,423 MW weather variance.*
  > 
  > *In summary: this pilot turns wind forecast volatility from an uncontrolled balance sheet liability into a structured, quantitative trading edge. Thank you."*

---
*(Brief pause / transition marker — 4:45)*
---

# Part 2: Tech Lead Walkthrough (Architecture, Code & Practices)
**Audience:** Head of Engineering / Tech Lead / Systems Architect  
**Tone:** Senior Quantitative Systems Architect. Crisp, engineering-focused, zero fluff.  
**Target Duration:** Exactly 4 minutes 45 seconds (4:45 – 9:30).

---

### [4:45 – 5:45] 1. System Architecture & Split Production Deployment
- **Screen:** Switch to IDE showing `README.md` Mermaid Diagram (Line 41) or display the architecture block.
- **Mouse Action:** Trace from `Vercel (Frontend)` down to `Render (Backend)` and into `Snappy Parquet Cache`.
- **Word-for-Word Script:**
  > *"Now let's dive into the technical implementation for the engineering review.*
  > 
  > *First, **Deployment Architecture**: We run a decoupled split deployment. The React 19 single-page application is hosted globally on **Vercel** at `griddraft-one.vercel.app`. The backend is a multi-stage Dockerised **FastAPI** service running on **Render** at `griddraft.onrender.com`.*
  > 
  > *To eliminate cross-origin complexity and protect against CORS preflight latency, Vercel's edge rewrites all `/api/*` and `/health` requests directly to Render. The browser interacts with a single unified origin.*
  > 
  > *Second, **Storage Architecture**: Rather than deploying a relational database like Postgres or Redis, we store canonical Elexon BMRS datasets as Snappy-compressed Parquet files in `backend/data/cache/`.*
  > 
  > *The entire January 2026 dataset—18,104 forecast revisions and 1,488 actual intervals—takes only **122 KB on disk**. On container startup, PyArrow loads both tables directly into memory in under **15 milliseconds**. Queries execute in-memory with sub-5 millisecond response times and zero database network hops."*

---

### [5:45 – 6:45] 2. The Analytical Engine: Point-in-Time Invariant Code
- **Screen:** Switch editor to `backend/app/analytics/forecast_selection.py`.
- **Mouse Action:** Highlight lines 105 to 135 (the `select_decision_forecast` function).
- **Word-for-Word Script:**
  > *"Let's look at the core causal logic in `backend/app/analytics/forecast_selection.py`.*
  > 
  > *The primary function is `select_decision_forecast`. It enforces the fundamental point-in-time invariant:*
  > $$\text{publishTime} \le \text{cutoff\_time} \le \text{startTime}$$
  > 
  > *We achieve this without slow row-by-row loops. Using vectorised Pandas operations:*
  > 1. *We calculate the target delivery date's cutoff timestamp.*
  > 2. *We filter `publishTime <= cutoff_time`.*
  > 3. *We sort by `[delivery_hour, publishTime]` and take `keep='last'`, which selects the freshest forecast available to the trader when the auction order was submitted.*
  > 
  > *Then, in `expand_to_half_hours`, we map hourly WINDFOR forecasts to half-hourly settlement periods using `dt.floor('h')`. In electricity markets, power is an instantaneous rate in MW, so an hourly forecast applies equally across both 30-minute intervals. This preserves 100% data coverage without synthesizing fake interpolation."*

---

### [6:45 – 7:45] 3. Quantitative Risk & Buffer Decomposition Code
- **Screen:** Switch editor to `backend/app/analytics/risk.py`.
- **Mouse Action:** Highlight lines 40 to 80 (the `calculate_safe_wind` and `decompose_shortfall_buffer` functions).
- **Word-for-Word Script:**
  > *"Now let's examine `backend/app/analytics/risk.py`.*
  > 
  > *Here we implement the Safe Wind formula:*
  > $$\text{Safe Wind} = \max(0, \text{Forecast} - \text{Buffer})$$
  > *where shortfall is asymmetric:*
  > $$\text{Shortfall} = \max(0, \text{Forecast} - \text{Actual})$$
  > 
  > *Look at `decompose_shortfall_buffer`: we mathematically split the total quantile buffer into two independent components: the systematic mean bias, and the residual stochastic quantile.*
  > 
  > *Furthermore, we support two empirical backtest modes: `in_sample` across the month, and a causal rolling `prior_days` backtest that uses only historical days up to $D-2$. At P90, our empirical coverage achieves **89.99%** in-sample and **89.65%** in prior-days backtesting, proving that the risk model holds out-of-sample."*

---

### [7:45 – 8:40] 4. Reliability Engineering, Quality Gates & CI/CD
- **Screen:** Switch to Terminal and run: `python scripts/verify_numbers.py`.
- **Mouse Action:** Scroll through the 9 green `[PASS]` sections on screen.
- **Word-for-Word Script:**
  > *"Next, let's review our testing and software quality gates.*
  > 
  > *Notice this terminal execution: `python scripts/verify_numbers.py`. It runs across 9 rigorous sections: validating our primary KPIs against pure independent NumPy recalculations, verifying that the mean of the 31 daily biases equals the global monthly bias to within $10^{-6}$, and testing daylight saving time transitions across London time (including 23-hour spring-forward and 25-hour fall-back days).*
  > 
  > *In addition, our test suite includes:*
  > - **112 backend tests** in Pytest, including 20 contract tests in `test_contract.py` that strictly lock every metric shown on the UI.
  > - **38 frontend tests** in Vitest using Mock Service Worker (MSW), including automated `axe-core` accessibility audits guaranteeing WCAG 2.1 AA compliance.
  > - **Automated Keep-Alive**: To prevent Render free tier containers from sleeping after 15 minutes, FastAPI runs a background asyncio worker pinging its own health endpoint every 14 minutes, paired with a React frontend heartbeat hook.*
  > 
  > *All of this is enforced automatically on every commit via GitHub Actions in `.github/workflows/ci.yml`."*

---

### [8:40 – 9:30] 5. Architectural Trade-offs & Limitations
- **Screen:** Switch editor to `README.md` Section 11 (Limitations & Next Steps).
- **Word-for-Word Script:**
  > *"To ensure a thorough review, let's discuss our explicit design trade-offs and limitations:*
  > 
  > 1. **Hourly vs Half-Hourly Granularity**: BMRS WINDFOR is published hourly while FUELHH is half-hourly. Assuming a flat hourly block rate ignores intra-hour ramp rates, but avoids fabricating non-existent data.
  > 2. **National Fleet Aggregation**: Our pilot strictly uses national-level data. It does not model Scottish export transmission bottlenecks or BM curtailment under Bid-Offer Acceptances (BOAs).
  > 3. **Next Technical Evolution**: Extending the cache beyond January 2026 across full multi-year seasons, and integrating half-hourly System Buy Price (SBP) feeds to compute real-time cash imbalance penalties alongside volumetric MW shortfalls."*

---

### [9:30 – 10:00] Wrap-Up & Submission
- **Screen:** Return to browser showing `https://griddraft-one.vercel.app`.
- **Word-for-Word Script:**
  > *"In conclusion: the UK Wind Forecast Decision Tool is fully deployed, rigorously tested, and operational today. Both the Vercel frontend and Dockerised Render backend are live, open-source, and backed by a 100% green CI pipeline.*
  > 
  > *Thank you for your time, and I look forward to your questions."*

---

## Quick Reference Summary Cards for Presentation

| Metric Name | Canonical Value | Where to Point on Screen |
| :--- | :--- | :--- |
| **January Coverage** | **1,488 / 1,488 intervals (100%)** | Top Metadata Header |
| **Decision Cutoff MAE** | **2,145.2 MW (18.52% of mean)** | Accuracy Tab, Card 1 |
| **Decision Cutoff RMSE** | **2,615.8 MW (14.7% of peak)** | Accuracy Tab, Card 2 |
| **Systematic Bias** | **+1,851.9 MW (Over-forecast)** | Accuracy Tab, Card 3 |
| **Positive Bias Days** | **27 of 31 days (87.1%)** | Bias Banner & Daily Chart |
| **P90 Shortfall Buffer** | **4,274.9 MW** | Accuracy Tab, Card 4 |
| **Bias / Residual Split** | **1,851.9 MW bias + 2,423.0 MW residual** | Card 4 breakdown text |
| **Latest Pre-Delivery MAE** | **1,804.2 MW** | Accuracy Tab, Baseline toggle |
| **Leakage Gap** | **341.0 MW (15.9%)** | Card 1 Leakage delta badge |
| **Parquet Cache Size** | **122 KB total on disk** | Architecture Diagram / Terminal |
| **Backend Test Count** | **112 passed** | Terminal / CI badge |
| **Frontend Test Count** | **38 passed** | Terminal / CI badge |
