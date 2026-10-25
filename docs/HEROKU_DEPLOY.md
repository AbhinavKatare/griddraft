# Heroku Container Deployment Guide

This guide details how to build, deploy, and verify the **UK Wind Forecast Decision Tool** on Heroku using the Docker Container Registry.

The application is packaged as a **single-origin container**:
- **Multi-stage build**: Compiles the React + Vite frontend bundle (`frontend/dist`), builds Python 3.11-slim dependencies, and bundles pre-cached January 2026 Elexon Parquet datasets (`/app/data/cache`).
- **Single web process**: FastAPI serves both the REST API endpoints under `/api/v1/*` and the static SPA distribution at the root (`/`, `/assets/*`, and client routes `/decision`, `/accuracy`, `/methodology`).
- **Zero-downtime healthcheck**: Integrates a container healthcheck against `/health` and dynamic `$PORT` binding as required by the Heroku dyno runtime.

---

## 1. Prerequisites

1. **Heroku CLI**: Installed and authenticated ([Heroku CLI documentation](https://devcenter.heroku.com/articles/heroku-cli)).
2. **Docker Engine**: Installed and running locally.
3. **Git**: Workspace initialized.

Authenticate with Heroku and the Container Registry:
```bash
heroku login
heroku container:login
```

---

## 2. Heroku Dyno Sizing & Memory Considerations

- **Recommended Dyno**: `eco`, `basic`, or `standard-1x` (512 MB RAM).
- **Parquet In-Memory Footprint**:
  - `fuelhh_wind_jan2026.parquet`: 1,488 rows (~42 KB compressed, ~1.2 MB in-memory).
  - `windfor_jan2026.parquet`: 18,104 rows (~80 KB compressed, ~4.5 MB in-memory).
  - Total resident memory of FastAPI process with preloaded cache: **~85 MB - 110 MB RAM**, well within the 512 MB limit of Standard-1x/Eco dynos with zero swapping.

---

## 3. Deployment Steps

### Step 1: Create Heroku Application
```bash
# Create a new app (replace <app-name> with your preferred unique name)
heroku create uk-wind-forecast-monitor

# Set environment variables (optional overrides)
heroku config:set ENVIRONMENT=production LOG_LEVEL=INFO --app uk-wind-forecast-monitor
```

> [!NOTE]
> Heroku dynamically assigns a random port and injects it into the `$PORT` environment variable. The production [`Dockerfile`](file:///Dockerfile) CMD automatically binds Uvicorn to `${PORT:-8000}`:
> `CMD sh -c "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --workers 1"`

### Step 2: Build and Push Docker Image
Run from the root of the repository:
```bash
heroku container:push web --app uk-wind-forecast-monitor
```
This executes the multi-stage build:
1. Stage 1 (`frontend-builder`): Installs dependencies with `npm ci --legacy-peer-deps` and outputs optimized assets to `/app/frontend/dist`.
2. Stage 2 (`backend-builder`): Compiles backend wheels for Python 3.11-slim into `/install`.
3. Stage 3 (`runner`): Creates non-root user `appuser` (UID 10001), copies backend code, static assets, and cached Parquet data (`backend/data/cache`).

### Step 3: Release the Container
```bash
heroku container:release web --app uk-wind-forecast-monitor
```
Heroku provisions the dyno and routes traffic once the container starts and passes internal checks.

### Step 4: Monitor Dyno Startup Logs
```bash
heroku logs --tail --app uk-wind-forecast-monitor
```
Look for the startup log indicating cache loading:
```
app.services.data_store: Loading Parquet cache from /app/data/cache
app.services.data_store: Parquet cache loaded: 1488 FUELHH rows, 18104 WINDFOR rows
Uvicorn running on http://0.0.0.0:<PORT> (Press CTRL+C to quit)
```

---

## 4. Post-Deploy Smoke Testing

Verify the deployment using the automated smoke test script [`scripts/smoke_test.py`](file:///scripts/smoke_test.py):

```bash
python scripts/smoke_test.py --url https://uk-wind-forecast-monitor.herokuapp.com
```

### Verification Checks Performed:
1. **`/health`**: Validates `status: "healthy"` and `cache_loaded: true`.
2. **`/api/v1/meta`**: Validates January 2026 data range (1,488 FUELHH actuals, 18,104 WINDFOR revisions).
3. **`/api/v1/metrics`**: Verifies analytical calculation at D-1 09:00 decision cutoff.
4. **Single-Origin Root (`/`)**: Asserts HTTP 200 and validates that `index.html` with SPA bundle links is returned when requested with `Accept: text/html`.

### Sample Smoke Test Output:
```
========================================================
 UK Wind Forecast Monitor - Post-Deploy Smoke Test
 Target Service: https://uk-wind-forecast-monitor.herokuapp.com
 Timeout:        20.0s
========================================================

[1/4] Testing /health ... PASS (248.3ms)
      Status: healthy | Cache Loaded: True | Version: 1.0.0
[2/4] Testing /api/v1/meta ... PASS (5.2ms)
      Coverage: 2026-01-01 to 2026-01-31 (1488 FUELHH, 18104 WINDFOR)
[3/4] Testing /api/v1/metrics (D-1 09:00) ... PASS (212.1ms)
      MAE: 2145.2 MW | Bias: +1851.9 MW | Intervals: 1488
[4/4] Testing Single-Origin SPA Root (/ with Accept: text/html) ... PASS (42.0ms)
      SPA HTML successfully served from single origin (1274 bytes)

--------------------------------------------------------
 Results: 4/4 tests passed
--------------------------------------------------------
```

---

## 5. Troubleshooting & Maintenance

- **Dyno Scaling**:
  ```bash
  heroku ps:scale web=1 --app uk-wind-forecast-monitor
  ```
- **Inspect Container Shell**:
  ```bash
  heroku run bash --app uk-wind-forecast-monitor
  ```
- **Cold Start Behavior**:
  FastAPI loads the 122 KB bundled Parquet data into memory during application lifespan startup. The complete cold start to first request takes **< 2.0 seconds** on standard dynos.
