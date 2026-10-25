"""FastAPI application factory and production server configuration."""

from contextlib import asynccontextmanager
import logging
from typing import AsyncGenerator, Optional
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware

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


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Lifespan event handler for startup cache loading and shutdown."""
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
    yield
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

    # Health, Root, and Metrics Endpoints
    @app.get(
        "/health",
        response_model=HealthResponse,
        tags=["System"],
        summary="Service health check",
    )
    async def health() -> HealthResponse:
        """Health check returning system status and memory cache readiness."""
        return HealthResponse(
            status="healthy",
            version=cfg.app_version,
            cache_loaded=data_store.is_cached(),
        )

    @app.get(
        "/",
        tags=["System"],
        summary="Service root endpoint",
    )
    async def root() -> dict:
        """Service root providing entrypoint links and metadata."""
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

    return app


# Default application instance for ASGI servers (uvicorn app.main:app)
app = create_app()
