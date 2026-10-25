# Backend Service (`/backend`)

The Python FastAPI backend service provides high-performance point-in-time Day-Ahead forecast alignment and quantitative trading analytics.

## Subsystem Architecture

```text
backend/
├── app/
│   ├── config.py           # Pydantic Settings & configuration
│   ├── main.py             # FastAPI entrypoint, lifespan loader, CORS
│   ├── models/
│   │   ├── canonical.py    # Strict canonical schemas, Pydantic models & dtype maps
│   │   └── schemas.py      # Request/response API typing
│   ├── ingestion/
│   │   ├── elexon_client.py # Async httpx client with chunking, retries & concurrency semaphore
│   │   ├── pipeline.py     # Data fetch, normalisation, validation & atomic Parquet writes
│   │   └── run.py          # CLI entry point (python -m app.ingestion.run --start ... --end ...)
│   ├── services/
│   │   ├── data_store.py   # Parquet cache manager (PyArrow engine)
│   │   ├── point_in_time.py# D-1 decision cutoff engine (ZERO future leakage)
│   │   └── metrics.py      # MAE, RMSE, Bias, Percentiles, Horizons, Profiles
│   └── routers/
│       ├── forecast.py     # GET /api/forecast/day
│       ├── analytics.py    # GET /api/analytics/{kpis,daily,hourly-profile,horizons,distribution}
│       └── system.py       # GET /api/system/status, POST /api/system/refresh-cache
├── tests/                  # 24 unit, canonical validation, and edge case tests
├── requirements.txt        # Pinned production dependencies
└── Dockerfile              # Multi-stage production container
```

## Running Data Ingestion CLI

```bash
# Ingest full January 2026 data
python -m app.ingestion.run --start 2026-01-01 --end 2026-01-31

# Custom date range with custom concurrency
python -m app.ingestion.run --start 2026-01-01 --end 2026-01-07 --concurrency 4
```

## Running Locally

```bash
# Install dependencies
python -m pip install -r requirements.txt

# Run test suite
python -m pytest tests -v

# Start FastAPI server
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
API docs available at: `http://127.0.0.1:8000/docs`
