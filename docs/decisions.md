# Architectural Decision Records (ADR Log)

This log records key quantitative, architectural, and structural decisions made in the **UK Wind Forecast Decision Tool**.

---

## ADR 001: Local Columnar Parquet Storage vs Database Engine
- **Status**: Accepted
- **Context**: The application ingests and analyzes January 2026 Elexon BMRS settlement data (1,488 actuals, 18,104 forecast revisions).
- **Decision**: Store canonical datasets as snappy-compressed Parquet files in `backend/data/cache/` (122 KB total) and preload into memory using PyArrow and Pandas.
- **Consequences**:
  - Zero external database dependencies (no Postgres, SQLite, or Redis to configure or maintain).
  - Microsecond in-memory query performance (<5ms per query).
  - Instantaneous deployment and reproduction on any developer machine or container.

---

## ADR 002: Strict Point-in-Time Causal Selection (Information Leakage Guard)
- **Status**: Accepted
- **Context**: In day-ahead power trading, bids are finalized before auction clearing on D-1. Forecasts published after the decision cutoff represent information leakage and produce deceptively optimistic accuracy stats if used to backtest trading decisions.
- **Decision**: Filter forecast revisions by invariant:
  $$\text{publishTime} \le \text{cutoff\_time} \le \text{startTime}$$
  Default cutoff: 09:00 UTC on D-1. All intraday revisions after this cutoff are strictly segregated and labeled as "Latest Pre-Delivery".
- **Consequences**:
  - Backtests reflect real trading operational conditions.
  - Traders can toggle between "Decision-Time Forecast" and "Latest Pre-Delivery Forecast" to quantify the information leakage penalty (341.0 MW / 15.9% MAE leakage delta).

---

## ADR 003: Signed Error and Shortfall Asymmetry Formulation
- **Status**: Accepted
- **Context**: Meteorological literature often defines error as $\text{Actual} - \text{Forecast}$. Power trading desks, however, sell generation commitments in advance. When $\text{Forecast} > \text{Actual}$, the trader is short physical power and must buy replacement energy at high system buy prices.
- **Decision**:
  - Signed Error: $\text{Error} = \text{Forecast} - \text{Actual}$.
  - Positive Error represents **Over-Forecasting / Generation Shortfall**.
  - Shortfall: $\text{Shortfall} = \max(0, \text{Forecast} - \text{Actual})$.
- **Consequences**:
  - Direct correspondence with trading exposure.
  - Shortfall buffer quantile (P90) defines the required replacement reserve capacity.

---

## ADR 004: Buffer Decomposition into Systematic Bias and Residual Quantile
- **Status**: Accepted
- **Context**: UK National Grid ESO WINDFOR forecasts exhibit a persistent positive bias of +1,851.9 MW across January 2026. A flat risk buffer lumps predictable bias together with stochastic uncertainty.
- **Decision**: Decompose the total shortfall buffer:
  $$\text{Total Buffer} = \text{Systematic Bias} + \text{Residual Quantile}$$
  $$\text{Systematic Bias} = \mathbb{E}[\text{Shortfall}], \quad \text{Residual Quantile} = \max(0, Q_\alpha(\text{Shortfall}) - \text{Systematic Bias})$$
- **Consequences**:
  - Traders see clearly how much reserve capacity is wasted compensating for persistent mean offset vs managing tail weather volatility.

---

## ADR 005: Decoupled Multi-Stage vs Single-Origin Docker Deployment
- **Status**: Accepted
- **Context**: Production deployment requires hosting both FastAPI backend and React Vite SPA.
- **Decision**: Support both:
  1. Primary: Single-origin Dockerfile (FastAPI serving pre-compiled React SPA from `/app/static` and `/api/v1/*` from the same origin).
  2. Alternative: Decoupled Vercel Edge frontend with API rewrites to Heroku/Render container.
- **Consequences**:
  - Single-origin eliminates CORS headers and preflight roundtrips entirely.
  - Zero deployment drift between backend schema and frontend types.
