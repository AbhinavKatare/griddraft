"""Routers package init."""

from app.routers.forecast import router as forecast_router
from app.routers.analytics import router as analytics_router
from app.routers.system import router as system_router
from app.routers.v1 import router as v1_router

__all__ = ["forecast_router", "analytics_router", "system_router", "v1_router"]
