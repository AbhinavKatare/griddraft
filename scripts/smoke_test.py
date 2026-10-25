#!/usr/bin/env python3
"""Post-Deployment Smoke Test Script for UK Wind Forecast Monitoring.

Validates that the deployed container is fully initialized, the Parquet cache is active,
and both the single-origin API and frontend routes are functioning.

Usage:
    python scripts/smoke_test.py --url https://your-app-name.herokuapp.com
    python scripts/smoke_test.py --url http://localhost:8000
"""

import argparse
import os
import sys
import time
import httpx


def test_endpoint(client: httpx.Client, method: str, path: str, headers: dict = None, expected_status: int = 200) -> tuple[bool, float, dict | str]:
    """Execute HTTP request and measure latency."""
    t0 = time.perf_counter()
    try:
        resp = client.request(method, path, headers=headers)
        latency_ms = (time.perf_counter() - t0) * 1000.0
        if resp.status_code != expected_status:
            return False, latency_ms, f"HTTP {resp.status_code}: {resp.text[:200]}"
        try:
            return True, latency_ms, resp.json()
        except Exception:
            return True, latency_ms, resp.text
    except Exception as exc:
        latency_ms = (time.perf_counter() - t0) * 1000.0
        return False, latency_ms, str(exc)


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deploy smoke test for UK Wind Forecast Monitor")
    parser.add_argument(
        "--url",
        default=os.environ.get("APP_URL", "http://localhost:8000"),
        help="Base URL of deployed service (e.g. https://app.herokuapp.com)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=20.0,
        help="Request timeout in seconds",
    )
    args = parser.parse_args()

    base_url = args.url.rstrip("/")
    print(f"\n========================================================")
    print(f" UK Wind Forecast Monitor - Post-Deploy Smoke Test")
    print(f" Target Service: {base_url}")
    print(f" Timeout:        {args.timeout}s")
    print(f"========================================================\n")

    passed_count = 0
    total_count = 4

    with httpx.Client(base_url=base_url, timeout=args.timeout) as client:
        # ----------------------------------------------------------------------
        # Test 1: Service Healthcheck (/health)
        # ----------------------------------------------------------------------
        print(f"[1/{total_count}] Testing /health ...", end=" ", flush=True)
        ok, lat, data = test_endpoint(client, "GET", "/health")
        if ok and isinstance(data, dict) and data.get("status") == "healthy" and data.get("cache_loaded") is True:
            print(f"PASS ({lat:.1f}ms)")
            print(f"      Status: {data.get('status')} | Cache Loaded: {data.get('cache_loaded')} | Version: {data.get('version')}")
            passed_count += 1
        else:
            print(f"FAIL ({lat:.1f}ms)")
            print(f"      Error: {data}")

        # ----------------------------------------------------------------------
        # Test 2: Ingestion & Cache Metadata (/api/v1/meta)
        # ----------------------------------------------------------------------
        print(f"[2/{total_count}] Testing /api/v1/meta ...", end=" ", flush=True)
        ok, lat, data = test_endpoint(client, "GET", "/api/v1/meta")
        if ok and isinstance(data, dict) and "fuelhh_rows" in data and data.get("fuelhh_rows", 0) > 0:
            print(f"PASS ({lat:.1f}ms)")
            print(f"      Coverage: {data.get('available_start_date')} to {data.get('available_end_date')} ({data.get('fuelhh_rows')} FUELHH, {data.get('windfor_rows')} WINDFOR)")
            passed_count += 1
        else:
            print(f"FAIL ({lat:.1f}ms)")
            print(f"      Error: {data}")

        # ----------------------------------------------------------------------
        # Test 3: Analytics Accuracy Metrics (/api/v1/metrics?decision_time=09:00)
        # ----------------------------------------------------------------------
        print(f"[3/{total_count}] Testing /api/v1/metrics (D-1 09:00) ...", end=" ", flush=True)
        ok, lat, data = test_endpoint(client, "GET", "/api/v1/metrics?decision_time=09:00")
        if ok and isinstance(data, dict) and "mae_mw" in data:
            print(f"PASS ({lat:.1f}ms)")
            print(f"      MAE: {data.get('mae_mw'):.1f} MW | Bias: +{data.get('mean_bias_mw'):.1f} MW | Intervals: {data.get('matched_half_hours')}")
            passed_count += 1
        else:
            print(f"FAIL ({lat:.1f}ms)")
            print(f"      Error: {data}")

        # ----------------------------------------------------------------------
        # Test 4: Single-Origin Frontend SPA Root (GET / with text/html)
        # ----------------------------------------------------------------------
        print(f"[4/{total_count}] Testing Single-Origin SPA Root (/ with Accept: text/html) ...", end=" ", flush=True)
        ok, lat, data = test_endpoint(client, "GET", "/", headers={"Accept": "text/html"})
        if ok and isinstance(data, str) and ("<div id=\"root\">" in data or "<title>" in data):
            print(f"PASS ({lat:.1f}ms)")
            print(f"      SPA HTML successfully served from single origin ({len(data)} bytes)")
            passed_count += 1
        else:
            print(f"FAIL ({lat:.1f}ms)")
            print(f"      Error: {data[:200] if isinstance(data, str) else data}")

    print(f"\n--------------------------------------------------------")
    print(f" Results: {passed_count}/{total_count} tests passed")
    print(f"--------------------------------------------------------\n")

    return 0 if passed_count == total_count else 1


if __name__ == "__main__":
    sys.exit(main())
