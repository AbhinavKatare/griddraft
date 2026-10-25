# Elexon BMRS API Technical Notes & Verification

This document records direct empirical observations from live Elexon BMRS REST API requests (`https://data.elexon.co.uk/bmrs/api/v1`), including endpoint behaviors, date range limits, and response schemas.

---

## 1. Date Range Constraint Verification (7 Days Inclusive, Observed HTTP 400)

The Elexon Insights Solution (BMRS) REST API enforces a maximum query window of **7 days inclusive**. Requests exceeding 7 days receive an observed HTTP 400 status.

### Empirical Test Request
- **Endpoint**: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/FUELHH`
- **Query Parameters**:
  - `settlementDateFrom`: `2026-01-01`
  - `settlementDateTo`: `2026-01-09` (8 full settlement days)
- **Execution**: Live HTTP GET via `httpx` (outside test suites).

### Live Response
- **HTTP Status**: `400 Bad Request`
- **Content-Type**: `application/problem+json; charset=utf-8`
- **Response Headers**:
  ```http
  HTTP/1.1 400 Bad Request
  Content-Type: application/problem+json; charset=utf-8
  Cache-Control: no-store, must-revalidate, no-cache
  Strict-Transport-Security: max-age=31536000
  ```
- **Response Body**:
  ```json
  {
    "type": "https://tools.ietf.org/html/rfc9110#section-15.5.1",
    "title": "One or more validation errors occurred.",
    "status": 400,
    "errors": {
      "": [
        "The date range between SettlementDateFrom and SettlementDateTo inclusive must not exceed 7 days"
      ]
    },
    "traceId": "00-05248628619cd151c85364cb96f790b2-486d7bcb8d9f405f-00"
  }
  ```

### WINDFOR 8-Day Request
- **Endpoint**: `GET https://data.elexon.co.uk/bmrs/api/v1/datasets/WINDFOR`
- **Query Parameters**:
  - `publishDateTimeFrom`: `2026-01-01T00:00:00Z`
  - `publishDateTimeTo`: `2026-01-09T00:00:00Z` (8 days)
- **Observed Response**:
  - **HTTP Status**: `400 Bad Request`
  - Validation error message: `"The date range between PublishDateTimeFrom and PublishDateTimeTo inclusive must not exceed 7 days"`

### Architectural Mitigation in Client
Because Elexon enforces 7 days inclusive, observed HTTP 400 whenever a query range exceeds 7 days, `backend/app/ingestion/elexon_client.py` breaks any requested date range into safe **6-day chunks** (`CHUNK_DAYS = 6`). Each chunk is fetched independently with semaphore-bounded concurrency and exponential backoff retry.
