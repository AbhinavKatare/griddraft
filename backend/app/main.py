"""FastAPI application factory and production server configuration."""

import asyncio
from contextlib import asynccontextmanager
import logging
import os
from pathlib import Path
from typing import AsyncGenerator, Optional
import httpx
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.gzip import GZipMiddleware
from starlette.requests import Request

from app.config import Settings, settings
from app.ingestion.pipeline import run_january_2026_ingestion
from app.middleware import (
    ETagAndCacheControlMiddleware,
    RequestIDAndLoggingMiddleware,
    metrics_tracker,
)
from app.models.problem import (
    ProblemException,
    http_exception_handler,
    problem_exception_handler,
    validation_exception_handler,
)
from app.models.schemas import HealthResponse
from app.routers import v1_router
from app.services.data_store import data_store

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("wind_forecast_app")


async def keep_alive_worker(app_url: str, interval_seconds: int = 840) -> None:
    """Periodically ping public URL every 14 minutes (840s) to prevent container sleep on free hosts (Render)."""
    logger.info("Starting keep-alive background worker targeting %s every %ds...", app_url, interval_seconds)
    client = httpx.AsyncClient(timeout=15.0)
    try:
        while True:
            await asyncio.sleep(interval_seconds)
            try:
                target = f"{app_url.rstrip('/')}/health"
                resp = await client.get(target)
                logger.info("Keep-alive ping to %s returned %s", target, resp.status_code)
            except Exception as err:
                logger.warning("Keep-alive ping to %s failed: %s", app_url, err)
    except asyncio.CancelledError:
        logger.info("Keep-alive background worker cancelled cleanly.")
    finally:
        await client.aclose()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup cache loading, keep-alive worker, and shutdown."""
    logger.info("Initializing %s v%s...", settings.app_name, settings.app_version)

    # Check if Parquet cache exists; if not, fetch once from Elexon BMRS
    if not data_store.is_cached():
        logger.warning("Parquet cache not found. Triggering automated Elexon BMRS ingestion for January 2026...")
        try:
            await run_january_2026_ingestion()
        except Exception as exc:
            logger.error("Failed to run Elexon ingestion on startup: %s", exc)

    # Load cache into memory once
    data_store.load_data()
    logger.info("Application ready to serve requests. Cache loaded: %s", data_store.is_cached())

    # Start 14-minute keep-alive worker if configured or running on Render
    keep_alive_task = None
    target_url = (
        settings.keep_alive_url
        or os.environ.get("RENDER_EXTERNAL_URL")
        or os.environ.get("KEEP_ALIVE_URL")
    )
    if settings.enable_keep_alive and target_url:
        interval_secs = max(60, settings.keep_alive_interval_minutes * 60)
        keep_alive_task = asyncio.create_task(keep_alive_worker(target_url, interval_secs))
    else:
        logger.info("Keep-alive worker inactive (no RENDER_EXTERNAL_URL or KEEP_ALIVE_URL provided).")

    yield

    if keep_alive_task:
        keep_alive_task.cancel()
        try:
            await keep_alive_task
        except asyncio.CancelledError:
            pass

    logger.info("Shutting down application.")


def create_app(app_settings: Optional[Settings] = None) -> FastAPI:
    """Application factory creating FastAPI instance with versioned routing, CORS, and RFC 7807 handlers."""
    cfg = app_settings or settings

    app = FastAPI(
        title=cfg.app_name,
        version=cfg.app_version,
        description=(
            "### UK Wind Forecast Monitoring & Day-Ahead Trading Analytics\n\n"
            "Production REST API for power traders, quantitatively evaluating National Grid ESO / Elexon BMRS "
            "WINDFOR generation forecasts against FUELHH metered outturn.\n\n"
            "**Key Capabilities:**\n"
            "- Point-in-time forecast selection at configurable decision cutoffs (e.g. D-1 09:00)\n"
            "- Causal information leakage prevention (publishTime <= cutoff <= startTime)\n"
            "- Outturn-normalised accuracy metrics (NMAE by mean actual and max observed actual, sMAPE)\n"
            "- Downside shortfall risk analysis and implied backup thermal procurement\n"
            "- Lead-time horizon and diurnal hour-of-day error profiles\n"
        ),
        lifespan=lifespan,
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

    # 1. Custom Request ID & Structured Logging Middleware
    app.add_middleware(RequestIDAndLoggingMiddleware)

    # 2. ETag & Cache-Control Middleware
    app.add_middleware(ETagAndCacheControlMiddleware)

    # 3. GZip Response Compression (minimum size 500 bytes)
    app.add_middleware(GZipMiddleware, minimum_size=500)

    # 4. CORS Middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cfg.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register RFC 7807 Exception Handlers
    app.add_exception_handler(ProblemException, problem_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    app.add_exception_handler(HTTPException, http_exception_handler)

    # Include Versioned API v1 Router (All legacy routes removed)
    app.include_router(v1_router)

    # 5. Frontend Single-Origin Serving (if frontend/dist or STATIC_DIR exists)
    static_env = os.environ.get("STATIC_DIR")
    if static_env:
        static_dir = Path(static_env)
    else:
        static_dir = Path(__file__).resolve().parent.parent / "static"
        if not static_dir.exists():
            static_dir = Path(__file__).resolve().parent.parent.parent / "frontend" / "dist"

    has_frontend = static_dir.exists() and (static_dir / "index.html").exists()

    if has_frontend:
        assets_dir = static_dir / "assets"
        if assets_dir.exists():
            app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")

    # Health, Root, and Metrics Endpoints
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Service health check",
    )
    async def health() -> HealthResponse:
        """Health check returning system status and memory cache readiness."""
        # Ensure lazy load if lifespan did not fire in serverless environments
        if not data_store.is_cached():
            data_store.load_data()
        return HealthResponse(
            status="healthy",
            version=cfg.app_version,
            cache_loaded=data_store.is_cached(),
        )

    @app.get(
        "/",
        tags=["System"],
        summary="Service root endpoint or frontend SPA",
    )
    async def root(request: Request):
        """Service root returning SPA index.html for browsers or JSON metadata for API clients."""
        accept = request.headers.get("accept", "")
        if "text/html" in accept and has_frontend:
            return FileResponse(static_dir / "index.html")
        return {
            "service": cfg.app_name,
            "version": cfg.app_version,
            "target_scope": "January 2026 UK Wind (FUELHH & WINDFOR)",
            "api_v1": "/api/v1",
            "health": "/health",
            "metrics": "/metrics",
            "docs": "/docs",
        }

    @app.get(
        "/metrics",
        tags=["System"],
        summary="Server timing metrics and telemetry",
    )
    async def timing_metrics() -> dict:
        """Endpoint providing request counts and latency statistics."""
        return metrics_tracker.get_summary()

    # SPA Catch-All fallback for client-side routing (e.g. /decision, /accuracy, /methodology)
    if has_frontend:
        @app.get("/{full_path:path}", include_in_schema=False)
        async def spa_catch_all(full_path: str):
            target_file = static_dir / full_path
            if target_file.is_file():
                return FileResponse(target_file)
            return FileResponse(static_dir / "index.html")

    return app


# Default application instance for ASGI servers (uvicorn app.main:app)
app = create_app()
