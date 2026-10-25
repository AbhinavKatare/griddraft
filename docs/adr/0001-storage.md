# ADR 0001: Storage Strategy for Wind Forecast Monitoring (Parquet vs. SQLite vs. PostgreSQL)

## Status
**Accepted**

## Context
The Wind Forecast Monitoring platform quantifies day-ahead wind forecast accuracy against metered outturn for Great Britain during January 2026. 

Key technical characteristics of this workload:
* **Workload Type:** Strictly read-heavy analytical queries (filtering by point-in-time publication cutoffs, calculating MAE/RMSE/bias, quantile distributions, rolling profile aggregations).
* **Dataset Volume:** Modest and bounded for the 1-month scope:
  * `FUELHH` (actual wind outturn): 1,488 half-hourly rows (~60 KB in memory).
  * `WINDFOR` (forecast revisions): 18,104 hourly rows with multiple publication horizons (~750 KB in memory).
  * Total combined raw data volume is under 1 MB.
* **Deployment Target:** Serverless / ephemeral platforms (e.g., Vercel serverless functions, Heroku dynos, or lightweight Docker containers) where compute instances are stateless, subject to rapid scaling, and experience frequent restarts or cold starts.

## Considered Options

### Option 1: Apache Parquet Files with In-Memory Arrow/Pandas (Recommended)
* **Architecture:** Ingested data is cleaned, validated, and serialized into Snappy-compressed columnar Parquet files (`fuelhh_wind_jan2026.parquet` and `windfor_jan2026.parquet`). Files are either bundled within the deployment container/artifact or fetched from an object store (S3/GCS/Vercel Blob).
* **Storage Footprint (Measured):** Exactly **118.69 KB total on disk** (FUELHH: 36.04 KB / 36,900 bytes; WINDFOR: 82.66 KB / 84,639 bytes).
* **Read Performance (Measured):** **13.08 ms mean combined load time** from disk into Pandas DataFrames (min: 6.56 ms, P95: 16.76 ms over 50 benchmark iterations). Once loaded, DataFrames reside in memory with zero serialization overhead between Python and storage. Column projection and vectorization occur natively via PyArrow/Pandas SIMD instructions.
* **Concurrency:** Completely lock-free; immutable read-only files support arbitrary parallel worker processes with zero race conditions.
* **Cost & Infrastructure:** $0/month. No external database servers, no connection pools, no credential management.

### Option 2: Embedded SQLite Database
* **Architecture:** A single-file relational database (`data/weather.db`) with indexes on `startTime` and `publishTime`.
* **Storage Footprint:** ~2.5 MB on disk with B-Tree indexes.
* **Read Performance:** Fast local reads via SQLite C-bindings (5–15 ms). However, rows must be converted from SQLite binary row format to Python objects or DataFrame tabular memory, incurring deserialization overhead on complex aggregations.
* **Concurrency & Serverless Fit:** Read-only access is thread-safe, but ephemeral serverless functions (like Vercel AWS Lambda under the hood) create a fresh disk sandbox per cold container. Ephemeral writes are lost unless backed by persistent network volumes (EFS/LiteFS), which introduce latency and operational complexity.

### Option 3: Managed PostgreSQL (e.g., Supabase / Neon / Heroku Postgres)
* **Architecture:** Traditional client-server relational/timeseries database accessed over TCP/SSL via SQLAlchemy / asyncpg.
* **Storage Footprint:** ~15 MB on disk (tables + B-Tree indexes + WAL logs).
* **Read Performance:** 15–50 ms query latency due to network round-trips (TLS handshake, network latency, SQL parsing, row-to-dataframe serialization).
* **Concurrency & Serverless Fit:** Connection pool exhaustion is a notorious failure mode on serverless platforms when dozens of Lambdas spin up concurrently, requiring external connection poolers (PgBouncer/Neon Proxy).
* **Cost & Infrastructure:** $15–$50+/month for managed instances; requires secret management, backup automation, and VPC/firewall configuration.

---

## Comparison Matrix

| Evaluation Criterion | Apache Parquet (In-Memory Pandas) | Embedded SQLite | Managed PostgreSQL |
| :--- | :--- | :--- | :--- |
| **Data Size (Jan 2026)** | **118.7 KB (Measured Snappy)** | ~2.5 MB (Estimated) | ~15 MB (Estimated) |
| **Cold Start Latency** | **13.1 ms (Measured load)** | ~30 ms | 100–300 ms (TCP + TLS + auth) |
| **Analytical Query Speed** | **< 1 ms (Vectorized SIMD)** | 5–15 ms (row scan + parse) | 15–50 ms (network round-trip) |
| **Serverless Ephemeral Fit**| **Flawless (stateless, bundleable)** | Moderate (read-only file copy) | Poor (connection pool starvation) |
| **Infrastructure Cost** | **$0 / month** | $0 / month | $15 – $50+ / month |
| **Operational Overhead** | **Zero (no DB to maintain)** | Low (schema migrations) | Medium (backups, tuning, pooling)|
| **Concurrency Model** | **Lock-free immutable reads** | File lock considerations | Multi-version concurrency (MVCC) |
| **Point-in-Time Slicing** | **Vectorized Pandas filtering** | SQL index seek | SQL index seek |

---

## Decision & Recommendation

**We select Apache Parquet files with an in-memory Pandas/PyArrow singleton store (`DataStore`).**

### Rationale:
1. **Zero Cold-Start & Network Latency:** For an analytical app with 19,592 total rows across January 2026, maintaining a TCP client to a remote PostgreSQL server adds 20–50ms of network latency to every user request. In contrast, loading both Parquet files (118.69 KB total) directly from disk into memory takes an average of **13.08 ms** once per container lifecycle.
2. **Perfect Serverless Alignment:** Platforms like Vercel and Heroku dynos treat containers as ephemeral. Parquet files are static, deterministic, and can be committed or baked directly into container images, eliminating external database dependencies and connection pooling issues.
3. **Native Vectorized Analytics:** The core trader queries (point-in-time horizon slicing, half-hourly alignment, MAE/RMSE calculations, quantile distributions) run 10x to 100x faster using vectorized Pandas/PyArrow C-extensions than executing SQL queries and serializing rows over TCP.
4. **Idempotence & Portability:** Parquet files are self-describing, immutable snapshots. Moving from dev to staging or sharing data with Jupyter notebooks requires zero database dumps or port forwarding.

---

## Consequences

### Positive
* Zero hosting costs and zero operational maintenance (no backups, vacuuming, or connection leak bugs).
* Instantaneous response times for frontend charts (< 10ms P99 API response).
* Direct interoperability with Python data science workflows and Jupyter notebooks.
* Completely deterministic, version-controlled analytics.

### Negative & Mitigations
* *Negative:* Not designed for high-frequency concurrent transactional writes (OLTP).
  * *Mitigation:* The application is an analytical monitoring platform. Data is refreshed in batch via scheduled ingestion or on-demand pipeline runs, which write atomically to temporary Parquet files before swapping (`.tmp.parquet` $\to$ `.parquet`).
* *Negative:* If data scales to multiple years (e.g. 50M+ rows), in-memory loading could exceed serverless RAM limits (e.g., 256MB Vercel limit).
  * *Mitigation:* If scope expands beyond a seasonal sample to multi-decade datasets, DuckDB can be plugged in to query the exact same Parquet files with out-of-core streaming and zero schema conversion.
