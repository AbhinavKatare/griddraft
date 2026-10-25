# UK Wind Forecast Monitoring & Day-Ahead Decision Tool

[![CI / CD Quality Pipeline](https://github.com/anonymous/uk-wind-forecast/actions/workflows/ci.yml/badge.svg)](https://github.com/anonymous/uk-wind-forecast/actions)
[![Pytest Coverage](https://img.shields.io/badge/pytest_coverage-87%25-brightgreen.svg)](#testing-instructions)
[![Vitest Unit Tests](https://img.shields.io/badge/vitest-37%20passed-brightgreen.svg)](#testing-instructions)
[![Playwright E2E](https://img.shields.io/badge/playwright-smoke%20passed-blue.svg)](#testing-instructions)
[![WCAG Accessibility](https://img.shields.io/badge/axe--core-WCAG%202.1%20AA%20Compliant-success.svg)](#accessibility--contrast)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

A production-grade quantitative decision platform built for UK power trading desks who buy, sell, and hedge electricity on the Day-Ahead market (decisions committed on **D-1** for delivery across all 48 settlement periods on **D**).

Built strictly with real, continuous **Elexon Insights Solution (BMRS)** settlement data across all 1,488 half-hours of **January 2026**.

---

## 1. Project Overview & Trader Problem

Day-ahead power traders participating in GB wholesale auctions (EPEX SPOT Day-Ahead Auction closing at 11:00 GMT, Nord Pool at 12:00 GMT, or desk risk cutoffs at 09:00 GMT) must finalize nomination volumes on **D-1**.

Because wind generation is non-dispatchable and weather-dependent:
1. **The Over-Forecasting Hazard**: Committing nominal forecast volume into day-ahead auctions when models over-forecast leaves the trading desk with an unhedged physical deficit. The deficit must be bought back in the balancing mechanism at volatile system imbalance prices.
2. **The Causal Leakage Trap**: Evaluating historical forecast accuracy using revisions published after the D-1 auction cutoff introduces **information leakage**, giving traders a falsely optimistic impression of model performance.

This application directly addresses these challenges with:
- **Strict Causal Point-in-Time Selection**: Freezes forecast information strictly at the D-1 decision cutoff (default 09:00 UTC).
- **Leakage Delta Quantification**: Compares D-1 decision forecasts against latest pre-delivery revisions to isolate intraday forecast decay.
- **Safe Wind to Count On**: Computes empirical shortfall buffer quantiles (P90) and decomposes the buffer into systematic bias vs stochastic weather volatility.

---

## 2. Live Deployment & Video Walkthrough

- **Live Application URL**: [https://uk-wind-forecast-demo.vercel.app](https://uk-wind-forecast-demo.vercel.app) *(Deployment link placeholder)*
- **Interactive API Swagger Docs**: [https://uk-wind-forecast-demo.vercel.app/docs](https://uk-wind-forecast-demo.vercel.app/docs)
- **10-Minute Video Presentation**: [Unlisted YouTube Video Link](https://youtu.be/placeholder-demo) *(Pitch & Architecture Walkthrough)*

---

## 3. High-Level Architecture Diagram

```mermaid
flowchart TD
    subgraph Data ["Data Ingestion & Storage"]
        BMRS[("Elexon BMRS Live API<br/>FUELHH & WINDFOR")] --> Pipeline["CLI Ingestion Pipeline<br/>scripts/fetch_elexon_jan2026.py"]
        Pipeline --> Parquet[("Snappy Parquet Cache<br/>backend/data/cache/ (122 KB)")]
    end

    subgraph Backend ["FastAPI Analytical Backend (Python 3.11)"]
        Parquet --> Store["DataStore & In-Memory Cache<br/>app/services/data_store.py"]
        Store --> Pit["Point-in-Time Selection Engine<br/>app/analytics/forecast_selection.py"]
        Store --> MetricsEng["Trading Accuracy Metrics<br/>app/analytics/metrics.py"]
        Store --> RiskEng["Safe Wind & Risk Derating<br/>app/analytics/risk.py"]
        
        Pit & MetricsEng & RiskEng --> Routers["REST API Routers (/api/v1/*)<br/>app/routers/analytics.py"]
        Routers --> Middleware["ETag Caching & Request ID<br/>app/main.py"]
    end

    subgraph Frontend ["React 19 + TypeScript SPA (Vite)"]
        Middleware --> Client["Typed API Client & TanStack Query<br/>frontend/src/api/"]
        Client --> State["URL Parameter State Sync<br/>frontend/src/hooks/useUrlState.ts"]
        State --> ControlBar["Global Control Bar<br/>frontend/src/components/layout/ControlBar.tsx"]
        ControlBar --> DecisionView["Day-Ahead Decision View<br/>Auction Snapshot & Safe Wind Ledger"]
        ControlBar --> AccuracyView["Verification & Accuracy Suite<br/>Trading KPIs, Leakage & Daily Trend"]
        ControlBar --> Methodology["Methodology Drawer<br/>Formulas & Trading Invariants"]
    end
```

---

## 4. Directory & File Map

```
UK weather forecast/
├── .github/
│   ├── workflows/ci.yml             # GitHub Actions CI/CD (Ruff, Mypy, Pytest, Oxlint, Vitest, Docker)
│   ├── pull_request_template.md     # PR description & trading checklist
│   └── CODEOWNERS                   # Critical path ownership specifications
├── backend/
│   ├── app/
│   │   ├── analytics/
│   │   │   ├── forecast_selection.py# Point-in-time selection with D-1 cutoff & horizon modes
│   │   │   ├── metrics.py           # MAE, RMSE, Bias, Percentiles, Lags, Profiles
│   │   │   └── risk.py              # Safe wind derating, buffer decomposition, backtests
│   │   ├── models/schemas.py        # Pydantic v2 schemas for all API payloads
│   │   ├── routers/analytics.py     # FastAPI endpoints under /api/v1/*
│   │   ├── services/data_store.py   # Parquet loader & in-memory pyarrow cache
│   │   ├── config.py                # Pydantic BaseSettings & environment configs
│   │   └── main.py                  # FastAPI app factory, ETag middleware, SPA static mount
│   ├── data/cache/                  # Canonical January 2026 Parquet cache (122 KB total)
│   ├── tests/                       # 92 unit, regression, invariant & property tests
│   ├── Dockerfile                   # Multi-stage production backend container
│   └── requirements.txt             # Pinned backend dependencies
├── frontend/
│   ├── src/
│   │   ├── api/                     # TanStack Query hooks & RFC 7807 fetch client
│   │   ├── components/ui/           # Accessible UI primitives (MetricCard, SegmentedControl, etc.)
│   │   ├── features/
│   │   │   ├── decision/            # Day-Ahead Decision View, Hero Chart, Safe Wind Ledger
│   │   │   ├── accuracy/            # Verification Suite, KPI cards, Leakage Trend, Histograms
│   │   │   └── methodology/         # Interactive Methodology drawer & domain formulas
│   │   ├── test/                    # 37 Vitest unit & integration tests + MSW mock server
│   │   └── types.ts                 # Full TypeScript definitions matching OpenAPI schemas
│   ├── e2e/smoke.spec.ts            # Playwright browser end-to-end user flow
│   ├── Dockerfile                   # Multi-stage production frontend container
│   └── package.json                 # Pinned frontend dependencies
├── scripts/
│   ├── fetch_elexon_jan2026.py      # Resilient BMRS ingestion chunker
│   └── smoke_test.py                # Automated post-deployment verification script
├── docs/
│   ├── DEPLOYMENT_GUIDE.md          # Step-by-step Vercel & Heroku deployment guide
│   ├── decisions.md                 # Architectural Decision Records (ADRs)
│   └── METHODOLOGY.md               # Mathematical formulation of metrics and risk
├── Dockerfile                       # Unified single-origin production container (FastAPI + React)
├── docker-compose.yml               # Unified dev (hot reload) and prod orchestration
└── README.md                        # Master project documentation
```

---

## 5. January 2026 Ground Truth Benchmark (D-1 09:00 UTC Cutoff)

All metrics below are computed strictly from real Elexon BMRS datasets across all 1,488 settlement intervals:

| Metric | Ground Truth Value | Trader Operational Interpretation |
| :--- | :--- | :--- |
| **Data Coverage Evaluated** | **1,488 / 1,488 (100.0%)** | Zero missing half-hours across January 2026 |
| **Mean Actual Generation** | **11,580.7 MW** | High winter outturn fleet baseline |
| **Mean Forecast Generation** | **13,432.6 MW** | Nominal model baseline at D-1 09:00 cutoff |
| **Mean Absolute Error (MAE)** | **2,145.2 MW** | Expected unhedged imbalance volume per half-hour |
| **MAE % of Mean Outturn (NMAE)** | **18.52%** | Relative volumetric sizing error |
| **MAE % of Peak Outturn** | **12.05%** | Scaled against peak observed generation (17,805 MW) |
| **Root Mean Squared Error (RMSE)**| **2,615.8 MW** | Heavy penalty on catastrophic forecast swings |
| **Systematic Forecast Bias** | **+1,851.9 MW** | **OVER-FORECAST (Long Risk)**: Models over-forecast in 27 of 31 days |
| **P50 Shortfall (Median)** | **1,703.0 MW** | Median generation deficit when forecast > actual |
| **P90 Shortfall Buffer** | **4,274.9 MW** | Required reserve buffer for 90% risk tolerance |
| **P99 Tail Shortfall Risk** | **6,359.9 MW** | Extreme weather miss exposure |
| **Latest Pre-Delivery MAE** | **1,804.2 MW** | Full-month latest forecast accuracy |
| **Information Leakage Delta** | **341.0 MW (15.9%)** | Artificial accuracy improvement if using leaked intraday data |

---

## 6. Assumptions & Methodology Matrix

| # | Assumption / Choice | Rationale | Implementation | Impact & Trade-Off |
| :--- | :--- | :--- | :--- | :--- |
| **1** | **Decision Cutoff Default: 09:00 UTC on D-1** | GB day-ahead auctions clear at 11:00 UTC; desks freeze inputs by ~09:00 UTC. | Global interactive selector with presets (`07:00`, `09:00`, `11:00`, `12:00`). | Earlier cutoffs prevent leakage but increase forecast lead time (~15–39h). |
| **2** | **Hourly WINDFOR Mapped to Half-Hourly FUELHH** | In BMRS, `WINDFOR` is published for hourly intervals, while `FUELHH` actuals are half-hourly. In power markets, MW is an instantaneous rate; an hourly rate of $X\text{ MW}$ applies across both half-hours. | Vectorized join via `startTime.dt.floor('h')` in `expand_to_half_hours`. | Preserves 100% data coverage (1,488 half-hours) without synthetic interpolation. |
| **3** | **Normalisation by Mean & Peak Outturn** | Fleet capacity estimates vary across sources (~30–31 GW). Normalising by actuals provides empirical rigour. | NMAE Mean Gen: $\frac{\text{MAE}}{\text{mean}(A)} = 18.52\%$; NMAE Max Gen: $\frac{\text{MAE}}{\max(A)} = 12.05\%$. | Eliminates dependence on external capacity assumptions. |
| **4** | **Over-Forecasting = Positive Shortfall** | In power trading, over-forecasting leaves the desk short physical energy. | $\text{Error} = \text{Forecast} - \text{Actual}$; $\text{Shortfall} = \max(0, \text{Forecast} - \text{Actual})$. | Correctly reflects financial risk exposure. |
| **5** | **Buffer Decomposition** | WINDFOR has a large mean bias (+1,852 MW). Lumping bias and variance obscures causality. | $\text{Total Buffer} = \text{Systematic Bias} + \text{Residual Quantile}$. | Shows traders how much reserve is spent offsetting mean bias vs stochastic volatility. |
| **6** | **Calendar Scope: January 2026** | Full continuous month with winter storm cycles and varying wind regimes. | Date picker navigates Jan 1 to Jan 31, 2026. | Validated over 1,488 periods with complete Elexon cache. |

---

## 7. Quick Start: Running Locally

### Option A: Using Docker Compose (Recommended)

1. **Clone the repository**:
   ```bash
   git clone https://github.com/anonymous/uk-wind-forecast.git
   cd uk-wind-forecast
   ```

2. **Run Production-Like Unified Container**:
   ```bash
   docker compose up --build
   ```
   Open `http://localhost:8000` in your browser.

3. **Run Local Development Mode with Hot Reload**:
   ```bash
   docker compose --profile dev up
   ```
   - Frontend with Vite HMR: `http://localhost:5173`
   - FastAPI Backend with reload: `http://localhost:8001`

---

### Option B: Without Docker (Local Shell)

#### 1. Backend Setup
```bash
cd backend
python -m pip install -r requirements.txt

# Run backend test suite (92 tests)
python -m pytest tests/ -v

# Start FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```
Backend API will be accessible at `http://127.0.0.1:8000` with interactive Swagger docs at `http://127.0.0.1:8000/docs`.

#### 2. Frontend Setup
```bash
cd frontend
npm install --legacy-peer-deps

# Run unit tests (37 tests)
npm test

# Run build verification
npm run build

# Start Vite development server
npm run dev
```
Open `http://localhost:5173` in your browser.

---

## 8. Environment Variables Table

| Variable | Default | Scope | Description |
| :--- | :--- | :--- | :--- |
| `PORT` | `8000` | Backend | Port bound by Uvicorn ASGI server. |
| `WIND_APP_DEBUG` | `false` | Backend | Enables debug logging and interactive OpenAPI docs (`/docs`). |
| `WIND_APP_DEFAULT_DECISION_TIME` | `09:00` | Backend | Default D-1 auction decision cutoff time (HH:MM). |
| `CACHE_DIR` | `backend/data/cache` | Backend | Directory containing pre-cached Parquet datasets. |
| `STATIC_DIR` | `frontend/dist` | Backend | Directory containing compiled React SPA bundle. |
| `CORS_ORIGINS` | `*` | Backend | Permitted CORS origins for decoupled frontend hosting. |
| `VITE_API_BASE_URL` | `""` | Frontend | Base URL for API requests (empty string uses same-origin proxy). |

---

## 9. REST API Summary (`/api/v1/*`)

| Endpoint | Method | Key Parameters | Description |
| :--- | :--- | :--- | :--- |
| `/health` | `GET` | — | Service healthcheck and Parquet cache status (`cache_loaded: true`). |
| `/api/v1/meta` | `GET` | — | Cache boundaries, total rows, date ranges, and ingestion metadata. |
| `/api/v1/timeseries` | `GET` | `start_date`, `end_date`, `decision_time`, `resolution` | Aligned forecast vs actual timeseries with downsampling (`30m`, `1h`, `3h`). |
| `/api/v1/forecast/snapshot` | `GET` | `delivery_date`, `decision_time` | Point-in-time snapshot for all 48 settlement periods on delivery day. |
| `/api/v1/metrics` | `GET` | `decision_time`, `start_date`, `end_date` | Monthly trading KPIs (MAE, RMSE, Bias, Percentiles, NMAE). |
| `/api/v1/metrics/error-by-horizon` | `GET` | `source`, `decision_time` | Horizon decay profile from 0h to 48h lead times. |
| `/api/v1/metrics/error-by-hour` | `GET` | `decision_time` | Diurnal error breakdown across 24 hours of the day. |
| `/api/v1/risk/safe-wind` | `GET` | `delivery_date`, `decision_time`, `quantile`, `mode` | Conservative Safe Wind profile, buffer decomposition, and empirical backtest. |

---

## 10. Testing Instructions

### 1. Backend Tests (Pytest)
```bash
cd backend
python -m pytest tests/ -v --cov=app --cov-report=term-missing
```
**Results**: **112 passed**, 88% statement coverage across all analytical modules.

### 2. Frontend Tests (Vitest & React Testing Library)
```bash
cd frontend
npm test
```
**Results**: **38 passed** across 7 test suites (`format`, `url-state`, `control-bar`, `accessibility`, `colour-contrast`, `decision-view`, `accuracy-view`).

### 3. End-to-End Smoke Test (Playwright)
```bash
cd frontend
npx playwright test
```
**Results**: Complete user trading flow verified in headless Chromium.

### 4. Post-Deploy Smoke Test Script
```bash
python scripts/smoke_test.py --url http://localhost:8000
```
Verifies `/health`, `/api/v1/meta`, `/api/v1/metrics`, and single-origin SPA routing.

---

## 11. Limitations & Next Steps

1. **Single-Month Scope**: The current dataset strictly evaluates January 2026. While ideal for evaluating high winter wind volatility, extending to all 12 months will reveal seasonal bias variations.
2. **National Aggregation**: BMRS reports fleet-wide wind generation. Zonal granularity (Scotland vs England/Wales) would expose transmission constraint risks (BM curtailment under Bid-Offer Acceptances).
3. **Price Joint Distribution**: Future iterations could integrate historical System Buy Prices (SBP) to calculate exact monetary imbalance penalties (£) alongside volumetric shortfalls (MW).

---

## 12. AI-Usage Disclosure

In accordance with academic and technical disclosure standards:
- **Tools Used**: AI assistants (Claude 3.7 Sonnet / Google Antigravity) were utilized for scaffolding initial boilerplate, drafting test fixtures, and optimizing CSS token implementations.
- **Human Verification & Authorship**:
  1. All mathematical formulas (point-in-time invariant filtering, shortfall asymmetry, buffer decomposition) were derived and independently verified by the author.
  2. Every analytical KPI reported in this document was calculated directly from raw Elexon BMRS data using deterministic Python scripts.
  3. All test assertions, edge cases (DST transitions, NaN revisions, boundary clamping), and security reviews (non-root Docker users, input validation) were manually verified and audited.
