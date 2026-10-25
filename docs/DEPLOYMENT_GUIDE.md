# Production Deployment Guide: Vercel Frontend & Containerized Backend

This document provides a comprehensive, production-grade guide to deploying the **UK Wind Forecast Decision Tool**.

---

## 1. Architecture & Deployment Options

You have two primary deployment architectures depending on operational preference:

### Architecture Comparison
| Attribute | Option A: Decoupled (Vercel + Heroku/Render) | Option B: Unified Single-Origin Container (Heroku/Fly.io) |
| :--- | :--- | :--- |
| **Frontend Host** | Vercel Edge Network (Global CDN) | FastAPI mounted static assets (`/app/static`) |
| **Backend Host** | Heroku Container Dyno or Render Web Service | Same Heroku Container Dyno |
| **CORS** | Requires CORS origin headers or Vercel API rewrite | **None** (100% same-origin `/api/v1/*`) |
| **Cold Start** | Frontend: 0ms (Edge); Backend: ~1.5s | ~1.5s total (single process) |
| **Parquet Cache** | Baked directly into Backend Docker container | Baked directly into Unified Docker container |
| **Operational Overhead** | Two platforms, two git branches / builds | **Single push**, zero CORS, zero drift |

---

## 2. Shipping the Parquet Cache: Best Practices

### Why We Commit the Parquet Cache Directly (~122 KB Total)
- **Dataset Sizes**:
  - `fuelhh_wind_jan2026.parquet`: 1,488 rows, **42 KB** (Snappy compressed).
  - `windfor_jan2026.parquet`: 18,104 rows, **80 KB** (Snappy compressed).
  - Total repository weight: **~122 KB** (smaller than a typical PNG logo).
- **Comparison: Committed vs Build-Time Ingestion**:
  1. **Build-Time Ingestion (Anti-Pattern)**: Calling Elexon BMRS API during container build or serverless deployment introduces third-party network flakiness, rate limiting (HTTP 429), Elexon 400 window errors, and increases build times by 45–90 seconds.
  2. **Committed Small Parquet (Recommended Pattern)**: Git handles 122 KB effortlessly. It guarantees **100% deterministic, hermetic builds**, zero deployment flakiness, and instantaneous startup.

---

## 3. Cold Start & In-Memory Footprint

- **Container Startup Latency**:
  - Loading Python 3.11 runtime: ~350ms
  - Reading 122 KB Parquet into memory via PyArrow: **~12ms**
  - Parsing UTC timestamps & indexing: **~35ms**
  - Total process readiness (`/health` responding): **< 1.8 seconds**
- **RAM Usage**:
  - FastAPI + PyArrow + Pandas resident memory: **~85 MB** (well under 512 MB Eco/Basic dyno limits).
- **Vercel Serverless Python Limitation**:
  - Vercel Serverless Python functions experience 3.5s–6s cold starts when loading heavy C-extension wheels (`pandas`, `pyarrow`, `numpy`). Running the backend in a long-lived container (Heroku or Render) provides instantaneous (<50ms) API responses once warmed.

---

## 4. Option A: Step-by-Step Vercel (Frontend) + Heroku (Backend)

### Step 1: Deploy Backend to Heroku Container
```bash
# 1. Login to Heroku and container registry
heroku login
heroku container:login

# 2. Create the backend application
heroku create uk-wind-backend-api

# 3. Push and release using backend Dockerfile
heroku container:push web --app uk-wind-backend-api --context-path ./backend
heroku container:release web --app uk-wind-backend-api

# 4. Verify backend health
curl -f https://uk-wind-backend-api.herokuapp.com/health
```

### Step 2: Configure CORS on Backend
Set environment variable in Heroku to permit the Vercel origin:
```bash
heroku config:set CORS_ORIGINS="https://your-frontend.vercel.app,http://localhost:5173" --app uk-wind-backend-api
```

### Step 3: Deploy Frontend to Vercel
1. Install Vercel CLI or link repo in Vercel Dashboard:
   ```bash
   npm i -g vercel
   cd frontend
   vercel
   ```
2. Set Environment Variables in Vercel:
   - `VITE_API_BASE_URL`: `https://uk-wind-backend-api.herokuapp.com`
3. Alternatively, use Vercel Rewrites (`frontend/vercel.json`):
   ```json
   {
     "rewrites": [
       {
         "source": "/api/:path*",
         "destination": "https://uk-wind-backend-api.herokuapp.com/api/:path*"
       },
       {
         "source": "/health",
         "destination": "https://uk-wind-backend-api.herokuapp.com/health"
       },
       {
         "source": "/(.*)",
         "destination": "/index.html"
       }
     ]
   }
   ```
   *Benefit of rewrites: Eliminates CORS completely by proxying `/api/*` through the Vercel domain!*

---

## 5. Option B: Step-by-Step Unified Single-Origin Container (Heroku)

This is the most robust setup: one container, zero CORS, zero domain mismatch.

```bash
# 1. Create app
heroku create uk-wind-forecast-decision

# 2. Push unified root Dockerfile (builds React + FastAPI in 1 image)
heroku container:push web --app uk-wind-forecast-decision

# 3. Release container
heroku container:release web --app uk-wind-forecast-decision

# 4. Run automated post-deploy smoke test
python scripts/smoke_test.py --url https://uk-wind-forecast-decision.herokuapp.com
```

---

## 6. Environment Variables Reference

| Variable | Default | Purpose |
| :--- | :--- | :--- |
| `PORT` | `8000` | Port injected dynamically by Heroku or container runtime. |
| `WIND_APP_DEBUG` | `false` | Enables debug logging and interactive OpenAPI docs (`/docs`). |
| `WIND_APP_DEFAULT_DECISION_TIME` | `09:00` | Default D-1 auction decision cutoff time (HH:MM). |
| `CACHE_DIR` | `/app/data/cache` | Path to pre-cached Parquet datasets. |
| `STATIC_DIR` | `/app/static` | Path to compiled React production bundle for SPA serving. |
| `CORS_ORIGINS` | `*` | Comma-separated list of permitted browser origins. |

---

## 7. Post-Deploy Smoke Test & Verification

Run the test suite against the live deployment:
```bash
python scripts/smoke_test.py --url https://your-deployed-url.com
```

### Checks Performed:
1. `GET /health` -> HTTP 200, `status: "healthy"`, `cache_loaded: true`.
2. `GET /api/v1/meta` -> HTTP 200, 1,488 actuals, 18,104 forecasts.
3. `GET /api/v1/metrics?decision_time=09:00` -> HTTP 200, MAE = 2,145.2 MW, RMSE = 2,615.8 MW.
4. `GET /` -> HTTP 200, returns HTML with SPA title and `<div id="root">`.

---

## 8. Troubleshooting Guide

### Issue 1: "Parquet cache files not found" on Startup
- **Symptom**: `/health` returns `cache_loaded: false`.
- **Root Cause**: `.dockerignore` or `.gitignore` inadvertently excluded `.parquet` files.
- **Fix**: Check that `backend/data/cache/*.parquet` is checked into git:
  ```bash
  git status backend/data/cache
  git add -f backend/data/cache/*.parquet
  ```

### Issue 2: CORS Preflight Failed (Status 403 / No Access-Control-Allow-Origin)
- **Symptom**: Browser console shows `CORS error` when calling `/api/v1/timeseries`.
- **Fix**:
  1. In `vercel.json`, use API rewrites to proxy `/api/:path*` directly to the backend URL.
  2. Or configure `CORS_ORIGINS` on the backend host to include `https://<your-vercel-domain>.vercel.app`.

### Issue 3: Container Crashes with `R10 (Boot timeout)` on Heroku
- **Symptom**: Heroku logs show `Web process failed to bind to $PORT within 60 seconds of launch`.
- **Root Cause**: Hardcoded port 8000 in Uvicorn command.
- **Fix**: Verify Dockerfile CMD binds to `${PORT:-8000}`:
  `CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]`
