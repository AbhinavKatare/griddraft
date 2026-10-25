"""System router for health check, cache metadata and status reporting."""

from fastapi import APIRouter, BackgroundTasks
import pandas as pd

from app.config import settings
from app.models.schemas import SystemStatus
from app.services.data_store import data_store
from app.ingestion.pipeline import run_january_2026_ingestion

router = APIRouter(prefix="/api/system", tags=["System"])


@router.get("/status", response_model=SystemStatus)
async def get_system_status() -> SystemStatus:
    """Return backend status, cache presence and Elexon dataset information."""
    is_cached = data_store.is_cached()
    fuelhh = data_store.get_fuelhh()
    windfor = data_store.get_windfor()
    metadata = data_store.get_metadata()

    f_min = fuelhh["startTime"].min().isoformat() if not fuelhh.empty else None
    f_max = fuelhh["startTime"].max().isoformat() if not fuelhh.empty else None
    w_min = windfor["publishTime"].min().isoformat() if not windfor.empty else None
    w_max = windfor["publishTime"].max().isoformat() if not windfor.empty else None

    return SystemStatus(
        status="ONLINE" if is_cached else "NO_CACHE",
        data_source="Elexon Insights Solution (BMRS) via Local Parquet Cache",
        cache_loaded=not fuelhh.empty and not windfor.empty,
        fuelhh_records=len(fuelhh),
        windfor_records=len(windfor),
        fuelhh_min_date=f_min,
        fuelhh_max_date=f_max,
        windfor_min_publish=w_min,
        windfor_max_publish=w_max,
        cache_last_updated=metadata.get("last_updated_utc"),
        default_decision_time=settings.default_decision_time,
    )


@router.post("/refresh-cache")
async def trigger_cache_refresh(background_tasks: BackgroundTasks) -> dict:
    """Trigger background refresh of January 2026 Elexon data."""
    async def _refresh() -> None:
        await run_january_2026_ingestion()
        data_store.load_data(force_reload=True)

    background_tasks.add_task(_refresh)
    return {"message": "Cache refresh initiated in background."}
