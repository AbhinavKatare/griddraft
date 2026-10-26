"""Async Elexon BMRS API client for FUELHH and WINDFOR datasets.

Features:
- Full async HTTP via httpx.AsyncClient
- Configurable request timeouts
- Exponential backoff with jitter on 429 rate-limits, 5xx server errors, and network disconnects
- Chunked date ranges respecting Elexon's maximum 7-day API limit (using 6-day intervals)
- Semaphore-bounded concurrency limit to prevent overwhelming upstream servers
- Structured logging of all network interactions and retry attempts
"""

import asyncio
from datetime import date, datetime, timedelta
import logging
import random
from typing import Any, Dict, List, Optional, Tuple
import httpx

from app.config import settings

logger = logging.getLogger("app.ingestion.elexon_client")


class ElexonClient:
    """Production async client for Elexon Insights Solution (BMRS) REST API."""

    def __init__(
        self,
        base_url: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
        retry_backoff: Optional[float] = None,
        max_concurrency: int = 3,
    ) -> None:
        self.base_url = (base_url or settings.elexon_base_url).rstrip("/")
        self.timeout = timeout or settings.elexon_request_timeout
        self.max_retries = max_retries or settings.elexon_max_retries
        self.retry_backoff = retry_backoff or settings.elexon_retry_backoff
        self.semaphore = asyncio.Semaphore(max(1, max_concurrency))
        self.headers = {
            "User-Agent": f"UKWindForecastApp/{settings.app_version}",
            "Accept": "application/json",
        }

    async def _fetch_with_retry(
        self,
        client: httpx.AsyncClient,
        url: str,
        params: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Fetch URL with bounded concurrency, exponential backoff, and jitter."""
        async with self.semaphore:
            backoff = self.retry_backoff
            for attempt in range(1, self.max_retries + 1):
                try:
                    logger.debug("HTTP GET %s (attempt %d/%d)", url, attempt, self.max_retries)
                    response = await client.get(url, params=params, timeout=self.timeout)

                    if response.status_code == 200:
                        return response.json()

                    if response.status_code in (429, 500, 502, 503, 504):
                        # Rate limit or transient gateway error -> exponential backoff with jitter
                        jitter = random.uniform(0.1, 0.5)
                        sleep_time = backoff + jitter
                        logger.warning(
                            "Elexon API returned status %d on attempt %d/%d for %s. Backing off %.2fs.",
                            response.status_code,
                            attempt,
                            self.max_retries,
                            url,
                            sleep_time,
                        )
                        if attempt == self.max_retries:
                            response.raise_for_status()
                        await asyncio.sleep(sleep_time)
                        backoff *= 2.0
                        continue

                    # Unrecoverable HTTP error (e.g., 400 Bad Request, 404 Not Found)
                    response.raise_for_status()

                except (httpx.RequestError, httpx.TimeoutException) as exc:
                    jitter = random.uniform(0.1, 0.5)
                    sleep_time = backoff + jitter
                    logger.warning(
                        "Network error on attempt %d/%d for %s: %r. Backing off %.2fs.",
                        attempt,
                        self.max_retries,
                        url,
                        exc,
                        sleep_time,
                    )
                    if attempt == self.max_retries:
                        raise
                    await asyncio.sleep(sleep_time)
                    backoff *= 2.0

            raise RuntimeError(f"Failed to fetch {url} after {self.max_retries} attempts.")

    async def _fetch_fuelhh_chunk(
        self,
        client: httpx.AsyncClient,
        start_date: date,
        end_date: date,
        chunk_idx: int,
        total_chunks: int,
    ) -> List[Dict[str, Any]]:
        """Fetch a single 6-day chunk of FUELHH actual wind generation."""
        url = f"{self.base_url}/datasets/FUELHH"
        params = {
            "settlementDateFrom": start_date.strftime("%Y-%m-%d"),
            "settlementDateTo": end_date.strftime("%Y-%m-%d"),
        }
        logger.info(
            "[FUELHH Chunk %d/%d] Fetching settlement dates %s to %s...",
            chunk_idx,
            total_chunks,
            start_date,
            end_date,
        )
        data = await self._fetch_with_retry(client, url, params=params)
        raw_list = data.get("data", []) if isinstance(data, dict) else data

        # Filter strictly for WIND fuelType
        wind_records = [
            item for item in raw_list
            if str(item.get("fuelType", "")).strip().upper() == "WIND"
        ]
        logger.info(
            "[FUELHH Chunk %d/%d] Received %d total records (%d WIND records).",
            chunk_idx,
            total_chunks,
            len(raw_list),
            len(wind_records),
        )
        return wind_records

    async def fetch_fuelhh_wind(
        self,
        settlement_date_from: date,
        settlement_date_to: date,
    ) -> List[Dict[str, Any]]:
        """
        Fetch FUELHH actual generation for WIND fuel type.
        Elexon enforces maximum 7-day span between settlementDateFrom and settlementDateTo.
        Chunks date range into 6-day intervals and runs with bounded concurrency.
        """
        chunks: List[Tuple[date, date]] = []
        curr = settlement_date_from
        while curr <= settlement_date_to:
            chunk_end = min(curr + timedelta(days=6), settlement_date_to)
            chunks.append((curr, chunk_end))
            curr = chunk_end + timedelta(days=1)

        total_chunks = len(chunks)
        logger.info(
            "Fetching FUELHH (WIND) from %s to %s across %d chunk(s) (concurrency limit: %d)...",
            settlement_date_from,
            settlement_date_to,
            total_chunks,
            self.semaphore._value,
        )

        async with httpx.AsyncClient(headers=self.headers) as client:
            tasks = [
                self._fetch_fuelhh_chunk(client, start, end, idx + 1, total_chunks)
                for idx, (start, end) in enumerate(chunks)
            ]
            chunk_results = await asyncio.gather(*tasks)

        all_records = [rec for sublist in chunk_results for rec in sublist]
        logger.info("Successfully fetched %d total raw FUELHH WIND records.", len(all_records))
        return all_records

    async def _fetch_windfor_chunk(
        self,
        client: httpx.AsyncClient,
        start_dt: datetime,
        end_dt: datetime,
        chunk_idx: int,
        total_chunks: int,
    ) -> List[Dict[str, Any]]:
        """Fetch a single 6-day chunk of WINDFOR generation forecasts."""
        url = f"{self.base_url}/datasets/WINDFOR"
        params = {
            "publishDateTimeFrom": start_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "publishDateTimeTo": end_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        logger.info(
            "[WINDFOR Chunk %d/%d] Fetching publish datetimes %s to %s...",
            chunk_idx,
            total_chunks,
            params["publishDateTimeFrom"],
            params["publishDateTimeTo"],
        )
        data = await self._fetch_with_retry(client, url, params=params)
        raw_list = data.get("data", []) if isinstance(data, dict) else data

        logger.info(
            "[WINDFOR Chunk %d/%d] Received %d forecast records.",
            chunk_idx,
            total_chunks,
            len(raw_list),
        )
        return raw_list

    async def fetch_windfor(
        self,
        publish_datetime_from: datetime,
        publish_datetime_to: datetime,
    ) -> List[Dict[str, Any]]:
        """
        Fetch WINDFOR wind generation forecasts.
        Elexon enforces maximum 7-day span between publishDateTimeFrom and publishDateTimeTo.
        Chunks date range into 6-day intervals and runs with bounded concurrency.
        """
        chunks: List[Tuple[datetime, datetime]] = []
        curr = publish_datetime_from
        while curr < publish_datetime_to:
            chunk_end = min(curr + timedelta(days=6), publish_datetime_to)
            chunks.append((curr, chunk_end))
            curr = chunk_end

        total_chunks = len(chunks)
        logger.info(
            "Fetching WINDFOR from %s to %s across %d chunk(s) (concurrency limit: %d)...",
            publish_datetime_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            publish_datetime_to.strftime("%Y-%m-%dT%H:%M:%SZ"),
            total_chunks,
            self.semaphore._value,
        )

        async with httpx.AsyncClient(headers=self.headers) as client:
            tasks = [
                self._fetch_windfor_chunk(client, start, end, idx + 1, total_chunks)
                for idx, (start, end) in enumerate(chunks)
            ]
            chunk_results = await asyncio.gather(*tasks)

        all_records = [rec for sublist in chunk_results for rec in sublist]
        logger.info("Successfully fetched %d total raw WINDFOR forecast records.", len(all_records))
        return all_records
