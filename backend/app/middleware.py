"""Production ASGI middleware for Request ID, structured JSON logging, ETag/Cache-Control, and latency metrics."""

import hashlib
import json
import logging
import time
from typing import Callable, Dict, Optional
import uuid

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response as StarletteResponse

logger = logging.getLogger("app.access")


class MetricsTracker:
    """In-memory request counter and latency tracker."""

    def __init__(self) -> None:
        self.total_requests: int = 0
        self.endpoint_counts: Dict[str, int] = {}
        self.endpoint_latencies: Dict[str, list[float]] = {}

    def record(self, path: str, latency_ms: float, status_code: int) -> None:
        self.total_requests += 1
        key = f"{path} [{status_code}]"
        self.endpoint_counts[key] = self.endpoint_counts.get(key, 0) + 1
        if path not in self.endpoint_latencies:
            self.endpoint_latencies[path] = []
        # Keep last 500 samples per path
        if len(self.endpoint_latencies[path]) >= 500:
            self.endpoint_latencies[path].pop(0)
        self.endpoint_latencies[path].append(latency_ms)

    def get_summary(self) -> Dict[str, object]:
        summary: Dict[str, object] = {
            "total_requests": self.total_requests,
            "endpoints": {},
        }
        endpoints_dict = {}
        for path, latencies in self.endpoint_latencies.items():
            if latencies:
                endpoints_dict[path] = {
                    "count": len(latencies),
                    "mean_latency_ms": round(sum(latencies) / len(latencies), 2),
                    "p50_latency_ms": round(sorted(latencies)[len(latencies) // 2], 2),
                    "p95_latency_ms": round(sorted(latencies)[int(len(latencies) * 0.95)], 2),
                }
        summary["endpoints"] = endpoints_dict
        return summary


metrics_tracker = MetricsTracker()


class RequestIDAndLoggingMiddleware(BaseHTTPMiddleware):
    """Assigns X-Request-ID, tracks latency, and outputs structured JSON access logs."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], StarletteResponse]) -> StarletteResponse:
        req_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        start_time = time.perf_counter()

        response = await call_next(request)

        latency_ms = round((time.perf_counter() - start_time) * 1000.0, 2)
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Process-Time-Ms"] = str(latency_ms)

        # Record metrics
        metrics_tracker.record(request.url.path, latency_ms, response.status_code)

        # Structured JSON access log
        log_entry = {
            "request_id": req_id,
            "method": request.method,
            "path": request.url.path,
            "status_code": response.status_code,
            "latency_ms": latency_ms,
            "client_ip": request.client.host if request.client else "unknown",
        }
        logger.info(json.dumps(log_entry))

        return response


class ETagAndCacheControlMiddleware(BaseHTTPMiddleware):
    """Generates standard ETag and Cache-Control headers, returning 304 Not Modified when matches."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], StarletteResponse]) -> StarletteResponse:
        response = await call_next(request)

        # Apply caching only to successful GET responses
        if request.method == "GET" and response.status_code == 200:
            cache_control = "public, max-age=3600, stale-while-revalidate=86400"

            # Consume response body
            body_chunks = []
            async for chunk in response.body_iterator:
                body_chunks.append(chunk if isinstance(chunk, bytes) else chunk.encode("utf-8"))
            body = b"".join(body_chunks)

            etag = f'"{hashlib.md5(body).hexdigest()}"'

            # Check If-None-Match condition
            client_etag = request.headers.get("If-None-Match")
            if client_etag and client_etag.strip() == etag:
                return Response(
                    status_code=304,
                    headers={
                        "ETag": etag,
                        "Cache-Control": cache_control,
                        "X-Request-ID": response.headers.get("X-Request-ID", ""),
                    },
                )

            headers = dict(response.headers)
            headers["ETag"] = etag
            headers["Cache-Control"] = cache_control
            return Response(
                content=body,
                status_code=response.status_code,
                headers=headers,
                media_type=response.media_type,
            )

        return response
