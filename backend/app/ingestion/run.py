"""CLI entry point for Elexon BMRS wind actuals and forecast ingestion.

Usage:
    python -m app.ingestion.run --start 2026-01-01 --end 2026-01-31
    python -m app.ingestion.run --start 2026-01-01 --end 2026-01-07 --concurrency 4
"""

import argparse
import asyncio
from datetime import date, datetime
import logging
from pathlib import Path
import sys

from app.config import settings
from app.ingestion.elexon_client import ElexonClient
from app.ingestion.pipeline import ingest_dataset_range


def parse_iso_date(date_str: str) -> date:
    """Parse YYYY-MM-DD date string."""
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid date format: '{date_str}'. Expected YYYY-MM-DD.")


def setup_structured_logging(level: str = "INFO") -> None:
    """Configure structured console logging."""
    log_format = "%(asctime)s [%(levelname)-5s] [%(name)s] %(message)s"
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    # Silence noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)


def build_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser."""
    parser = argparse.ArgumentParser(
        prog="python -m app.ingestion.run",
        description="Ingest UK wind generation actuals (FUELHH) and forecasts (WINDFOR) from Elexon BMRS.",
    )
    parser.add_argument(
        "--start",
        type=parse_iso_date,
        default=date(2026, 1, 1),
        help="Start delivery date YYYY-MM-DD (default: 2026-01-01)",
    )
    parser.add_argument(
        "--end",
        type=parse_iso_date,
        default=date(2026, 1, 31),
        help="End delivery date YYYY-MM-DD (default: 2026-01-31)",
    )
    parser.add_argument(
        "--cache-dir",
        "--output",
        dest="cache_dir",
        type=Path,
        default=None,
        help="Target output directory for Parquet files (default: from settings or data/cache)",
    )
    parser.add_argument(
        "--concurrency",
        type=int,
        default=3,
        help="Maximum concurrent HTTP requests to Elexon BMRS (default: 3)",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="HTTP request timeout in seconds (default: 30.0)",
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Console logging level (default: INFO)",
    )
    return parser


async def main_async(args: argparse.Namespace) -> int:
    """Asynchronous main runner."""
    logger = logging.getLogger("app.ingestion.cli")

    if args.start > args.end:
        logger.error("Error: --start date (%s) must be on or before --end date (%s).", args.start, args.end)
        return 1

    target_dir = args.cache_dir or settings.cache_dir

    logger.info("Initializing Elexon client (timeout=%.1fs, concurrency=%d)...", args.timeout, args.concurrency)
    client = ElexonClient(
        timeout=args.timeout,
        max_concurrency=args.concurrency,
    )

    try:
        metadata = await ingest_dataset_range(
            start_date=args.start,
            end_date=args.end,
            cache_dir=target_dir,
            client=client,
            concurrency_limit=args.concurrency,
        )

        fuelhh_meta = metadata.get("fuelhh", {})
        windfor_meta = metadata.get("windfor", {})

        print("\n" + "=" * 65)
        print(" ELEXON BMRS INGESTION COMPLETE")
        print("=" * 65)
        print(f" Target Date Range:     {args.start} to {args.end}")
        print(f" Output Directory:      {target_dir.resolve()}")
        print(f" Total Ingestion Time:  {metadata.get('total_elapsed_seconds', 0.0):.2f} seconds")
        print("-" * 65)
        print(f" FUELHH Actuals Rows:   {fuelhh_meta.get('record_count', 0):,}")
        print(f" FUELHH File:           {fuelhh_meta.get('file')}")
        print(f" WINDFOR Forecast Rows: {windfor_meta.get('record_count', 0):,}")
        print(f" WINDFOR Delivery Slots:{windfor_meta.get('unique_delivery_slots', 0):,}")
        print(f" WINDFOR File:          {windfor_meta.get('file')}")
        print("=" * 65 + "\n")
        return 0

    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        return 1


def main() -> None:
    """CLI synchronous entry point."""
    parser = build_parser()
    args = parser.parse_args()
    setup_structured_logging(args.log_level)
    exit_code = asyncio.run(main_async(args))
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
