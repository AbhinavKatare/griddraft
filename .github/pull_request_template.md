## Pull Request Description

### Overview
<!-- Provide a high-level summary of the changes introduced in this PR. -->

### Changes Categorization
- [ ] **Analytics / Core**: Point-in-time forecast selection, metrics computation, or risk estimation logic.
- [ ] **Backend / API**: FastAPI routers, schemas, services, or middleware.
- [ ] **Frontend / UI**: React components, Recharts visualizations, controls, or styling.
- [ ] **Infrastructure / CI**: Dockerfiles, docker-compose, GitHub Actions, or deployment scripts.
- [ ] **Documentation / Testing**: Test additions, methodology documentation, or architectural decision logs.

---

### Verification & Testing
- [ ] Backend tests passing: `cd backend && python -m pytest tests/ -v` (assert 92+ tests pass).
- [ ] Backend linting clean: `ruff check backend/app` and `mypy backend/app`.
- [ ] Frontend test suite passing: `cd frontend && npm test` (all 7 suites pass).
- [ ] Frontend build succeeds without errors: `cd frontend && npm run build`.
- [ ] Playwright E2E smoke test green: `cd frontend && npx playwright test`.
- [ ] Local container builds cleanly: `docker compose build`.

---

### Quantitative Trading Checklist (CODEOWNERS Standards)
- [ ] **Point-in-Time Invariant**: Publish time $\le$ Decision cutoff $\le$ Delivery start time. No future information leakage.
- [ ] **Error Direction**: Error is explicitly defined as $\text{Forecast} - \text{Actual}$. Positive error represents Over-Forecasting / Shortfall risk.
- [ ] **Shortfall Formulation**: Shortfall buffer strictly defined as $\max(0, \text{Forecast} - \text{Actual})$.
- [ ] **No Hardcoded Stats**: Every number displayed in the UI is derived directly from `/api/v1/*` endpoints.
- [ ] **Zero Speculative Text**: No speculative domain explanations ("frontal propagation", "solar ramps", "firm backup", "cashout").
- [ ] **Timezone Integrity**: All backend timestamps are strictly ISO 8601 UTC. London local time is handled with explicit conversion.

---

### Reviewer Sign-Off
- [ ] Approved by Quant Lead / Backend Reviewer
- [ ] Approved by Frontend / UI Reviewer
