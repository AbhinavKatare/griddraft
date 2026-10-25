# 10-Minute Video Presentation Plan & Rehearsal Script

This document details the exact structure, click-by-click flow, timestamps, real benchmark numbers, and rehearsal checklist for the 10-minute presentation.

---

## Timing Structure Overview
| Segment | Duration | Audience | Core Focus |
| :--- | :--- | :--- | :--- |
| **Part 1: Customer Pitch** | **4:15** (max 4:30) | Trading Desk Head, Portfolio Manager | The over-forecasting hazard, live demo with exact clicks, 3 headline numbers, procurement savings |
| **Part 2: Tech Lead Walkthrough** | **4:45** (max 5:00) | Head of Engineering, Quantitative Lead | Architecture, point-in-time invariant code, test suite, CI/CD pipeline, trade-offs & limitations |
| **Buffer / Wrap-Up** | **1:00** | Both | Summary & Call-to-Action |
| **Total Duration** | **10:00** | | |

---

## Part 1: Customer Pitch (Day-Ahead Power Trading Desk)
**Target Duration:** 0:00 – 4:15 (4 min 15 sec)

### [0:00 – 0:45] The Hook: The +1,852 MW Systematic Over-Forecasting Trap
- **Visual:** Full-screen web app in dark theme on January 15, 2026.
- **Script:**
  > *"If you trade UK Day-Ahead power, your nominations are locked in before the 11:00 auction on D-1. If National Grid's wind forecast says you will produce 14,000 MW, but physical outturn is only 11,000 MW, your desk is caught 3,000 MW short. That deficit isn't a rounding error—it is settled at cash-draining system imbalance prices.*
  > *Worse: when desks backtest their models, they inadvertently test against forecasts published hours after the D-1 decision cutoff. That is information leakage—and it masks the true risk. Today I'm demonstrating the UK Wind Forecast Decision Tool: built strictly with real Elexon BMRS January 2026 settlement data to eliminate leakage and give your desk a provable, conservative volume to count on."*

### [0:45 – 2:30] Live Demo Flow (Exact Clicks)
1. **Click 1 [0:50]**: Open `http://localhost:5173` (Decision View).
   - Point to the **Global Controls Bar**: Date `2026-01-15`, Cutoff `09:00 UTC`, Mode `Decision-Time`.
   - *"Notice the Run Lineage Banner: our bids for January 15 were committed at 09:00 UTC on January 14. We are looking at the exact forecast available when the trader clicked 'Submit'—not a single revision leaked."*
2. **Click 2 [1:20]**: Point to **Summary Strip**:
   - Forecast: `331,100 MWh` | Safe Wind: `228,500 MWh` | Peak Procurement: `2,200 MW`.
   - *"Instead of selling 331 GWh and risking catastrophic imbalance, our P90 Safe Wind model derates nominations to 228 GWh, with an implied 2,200 MW thermal backup contract."*
3. **Click 3 [1:45]**: Toggle `Leaky Baseline` in Control Bar.
   - Show the dashed grey line appearing on the Hero Chart.
   - *"This dashed line is the latest pre-delivery forecast. Notice how it shifted intraday. Relying on this line gives you false confidence; our solid amber line is your real decision baseline."*
4. **Click 4 [2:10]**: Click **"Accuracy"** in Header Navigation Tab.
   - View URL updates to `/view=accuracy` instantly with preserved state.

### [2:30 – 3:45] 3 Headline Findings (Real Data from January 2026)
- **Finding 1: Systematic +1,852 MW Over-Forecast Bias**
  - Point to **Bias Alert Banner** and Card 3:
  - *"Across all 1,488 settlement intervals in January 2026, WINDFOR systematically over-forecasts generation with a mean bias of **+1,851.9 MW**. This isn't random noise: WINDFOR was over-forecast in **27 out of 31 days** (87.1% of the month). A desk that sells nominal forecast is structurally short 87% of the time."*
- **Finding 2: The 341 MW Information Leakage Penalty**
  - Point to Card 1 and the Baseline comparison toggle:
  - *"At D-1 09:00, our true MAE is **2,145.2 MW** (18.5% of mean generation). If you look at latest pre-delivery forecasts, MAE drops to **1,804.2 MW**. That **341 MW gap** (15.9% leakage) is pure information leakage. Trading decisions made D-1 face the 2,145.2 MW reality."*
- **Finding 3: The 4,275 MW P90 Shortfall Buffer**
  - Point to Card 4:
  - *"To achieve 90% volumetric reliability, the desk must hold a **4,275 MW** shortfall buffer. And because our backend decomposes this into +1,852 MW systematic bias and 2,423 MW residual volatility, you immediately see where the risk originates."*

### [3:45 – 4:15] Customer Procurement Value & Closing
- **Script:**
  > *"What is the value? By knowing that +1,852 MW is systematic bias rather than random weather uncertainty, your desk can recalibrate bidding curves and size thermal replacement reserve contracts precisely. Instead of paying peak imbalance penalties, you lock in predictable hedges. That transforms wind uncertainty from an operational risk into an edge."*

---

## Part 2: Tech Lead Walkthrough (Architecture & Code)
**Target Duration:** 4:15 – 9:00 (4 min 45 sec)

### [4:15 – 5:15] Architecture & Storage Decision (Mermaid on screen)
- **Visual:** Display `docs/ARCHITECTURE.md` Mermaid diagram.
- **Script:**
  > *"Let's look under the hood. The core architectural challenge was evaluating 18,104 forecast revisions against 1,488 actual settlement periods with sub-5ms query times. Rather than deploying an operational database like Postgres or Redis, we store canonical datasets as Snappy-compressed Parquet files in `backend/data/cache/`.*
  > *The entire January 2026 cache is just **122 KB** on disk. On application startup, PyArrow loads both tables directly into memory in under 15 milliseconds. Zero external DB latency, zero maintenance, and hermetic deployments."*

### [5:15 – 6:15] Decision-Time Logic & Key Code Files
- **Visual:** Code editor displaying `backend/app/analytics/forecast_selection.py`.
- **Script:**
  > *"Here is the point-in-time engine in `forecast_selection.py`. The pure function `select_decision_forecast` takes the raw forecasts DataFrame and applies a strict vectorised invariant:*
  > `publishTime <= cutoff_time <= startTime`
  > *We avoid slow row-by-row iteration. We sort by `[delivery_hour, publishTime]`, filter out any publish timestamps after the D-1 cutoff, and deduplicate with `keep='last'`. Then `expand_to_half_hours` maps hourly WINDFOR forecasts into half-hourly settlement periods using `dt.floor('h')`.*
  > *This guarantees mathematical causality: no forecast revision published after the decision cutoff can ever enter the backtest."*

### [6:15 – 7:15] Quantitative Risk & Buffer Decomposition
- **Visual:** Code editor displaying `backend/app/analytics/risk.py`.
- **Script:**
  > *"In `risk.py`, we implement the Safe Wind formula:*
  > `safe_wind = max(0, forecast - buffer)`
  > *where shortfall is strictly $\max(0, \text{forecast} - \text{actual})$. Notice `decompose_shortfall_buffer`: we split the total P90 buffer into systematic bias (`mean(shortfall)`) and residual quantile. We support two distinct evaluation modes: `in_sample` across the month, and a causal `prior_days` rolling backtest that only uses days strictly before the target date."*

### [7:15 – 8:15] Verification Suite, Testing & CI/CD
- **Visual:** Terminal running tests + GitHub Actions workflow YAML.
- **Script:**
  > *"Reliability is enforced across the stack:*
  > 1. **Backend**: 92 Pytest tests covering boundary conditions, daylight saving transitions across London time (23-hour March and 25-hour October clock switches), and verifying that lag-0 MAE and RMSE match primary KPIs identically.
  > 2. **Frontend**: 37 Vitest unit & integration tests using MSW to mock `/api/v1/*`, plus axe-core WCAG 2.1 AA accessibility audits and Playwright E2E browser flows.
  > 3. **CI/CD**: GitHub Actions runs Ruff, Mypy, Pytest with coverage, Oxlint, Vitest, and builds our multi-stage Docker container on every pull request."*

### [8:15 – 9:00] Trade-offs, Limitations & Next Steps
- **Visual:** Slide or README section displaying Limitations.
- **Script:**
  > *"Let's talk trade-offs:*
  > - **Trade-off 1**: Hourly-to-half-hour step mapping. We assume an hourly forecast rate applies to both half-hours. Intra-hour wind ramps introduce minor noise, but this preserves 100% data coverage without fabricating synthetic profiles.
  > - **Limitation**: BMRS data is national aggregate. We don't see zonal transmission bottlenecks between Scotland and England.
  > - **Next Step**: Ingest System Buy Prices (SBP) to evaluate monetary imbalance (£) penalties alongside MW volumetric shortfalls."*

---

## [9:00 – 10:00] Summary & Final Wrap-Up
- **Visual:** Return to browser live tool.
- **Script:**
  > *"To summarize: the UK Wind Forecast Decision Tool provides power traders with causal, leakage-free accuracy metrics and a disciplined, mathematical approach to day-ahead wind risk management. Full source code, test suites, and documentation are available in the repository. Thank you."*

---

## Rehearsal & Delivery Checklist
- [ ] **Timing Check**: Part 1 completes before 4:30; Part 2 completes before 9:00; full video under 10:00.
- [ ] **Numbers Check**: MAE = 2,145.2 MW; RMSE = 2,615.8 MW; Bias = +1,851.9 MW; P90 = 4,274.9 MW; Latest Pre-Delivery MAE = 1,804.2 MW (341 MW / 15.9% leakage); 27 of 31 days.
- [ ] **Click Flow Check**: Date selection -> Control Bar toggle -> Leaky baseline toggle -> Accuracy tab navigation.
- [ ] **Code Flow Check**: `forecast_selection.py` (line 120 invariant) -> `risk.py` (decomposition) -> `metrics.py` (lag test).
- [ ] **Microphone & Resolution**: 1080p recording, 125% browser zoom for crisp table readability, dark mode active.
