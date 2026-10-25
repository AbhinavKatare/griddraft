# Data Directory (`/data`)

This directory manages the storage, local caching, and metadata for raw and processed energy market datasets.

## Structure

```text
data/
└── cache/
    ├── .gitkeep
    ├── fuelhh_wind_jan2026.parquet  # Real Elexon FUELHH actuals (WIND, 1488 HH)
    ├── windfor_jan2026.parquet      # Real Elexon WINDFOR forecasts (18,104 rows)
    └── metadata.json                # Ingestion timestamps, row counts, data bounds
```

## Storage Guidelines

* **Parquet Format:** All tabular time-series data is serialized into Snappy-compressed Apache Parquet format via `pyarrow`. Parquet provides columnar compression (~90% size reduction compared to CSV) and sub-millisecond query filtering.
* **Git Ignored:** Data files (`*.parquet`, `*.json`) are excluded from version control via `.gitignore`. The directory structure is preserved using `.gitkeep`.
* **Zero Cold-Start:** When running the application locally or in containers, the backend loads data directly from `data/cache/` to ensure offline capability and immediate API response times without depending on live Elexon availability.
