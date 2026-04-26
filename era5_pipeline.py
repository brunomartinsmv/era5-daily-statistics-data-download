#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.era5.config import (
    DATA_RAW_ERA5,
    DEFAULT_CITY,
    DEFAULT_EFFICIENCY_FILE,
    DEFAULT_LIGHTNING_FILE,
    DEFAULT_YEAR_END,
    DEFAULT_YEAR_START,
)
from src.era5.download import download_era5_cuiaba
from src.era5.extract import extract_era5_archives
from src.era5.pipeline import run_full_pipeline
from src.era5.process import ProcessRunConfig, run_process_step


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="ERA5 ETL pipeline for Cuiaba.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download ERA5 annual zip files.")
    download.add_argument("--start-year", type=int, default=DEFAULT_YEAR_START)
    download.add_argument("--end-year", type=int, default=DEFAULT_YEAR_END)
    download.add_argument("--output-dir", type=Path, default=DATA_RAW_ERA5)
    download.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate params and list target files without network download.",
    )

    extract = subparsers.add_parser("extract", help="Extract downloaded ERA5 zip archives.")
    extract.add_argument("--input-dir", type=Path, default=DATA_RAW_ERA5)
    extract.add_argument("--pattern", type=str, default="era5_cuiaba_*.zip")

    process = subparsers.add_parser("process", help="Process GRIB files and generate merged datasets.")
    process.add_argument("--input-dir", type=Path, default=DATA_RAW_ERA5)
    process.add_argument("--city", type=str, default=DEFAULT_CITY)
    process.add_argument("--lightning-file", type=Path, default=DEFAULT_LIGHTNING_FILE)
    process.add_argument("--efficiency-file", type=Path, default=DEFAULT_EFFICIENCY_FILE)

    all_cmd = subparsers.add_parser("all", help="Run complete pipeline.")
    all_cmd.add_argument("--start-year", type=int, default=DEFAULT_YEAR_START)
    all_cmd.add_argument("--end-year", type=int, default=DEFAULT_YEAR_END)
    all_cmd.add_argument("--input-dir", type=Path, default=DATA_RAW_ERA5)
    all_cmd.add_argument("--city", type=str, default=DEFAULT_CITY)
    all_cmd.add_argument(
        "--skip-download",
        action="store_true",
        help="Skip download step and use existing ZIP files.",
    )
    all_cmd.add_argument(
        "--skip-extract",
        action="store_true",
        help="Skip extraction step and use existing GRIB files.",
    )
    all_cmd.add_argument(
        "--dry-run-download",
        action="store_true",
        help="Only affects 'all' when download is enabled.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "download":
        files = download_era5_cuiaba(
            year_start=args.start_year,
            year_end=args.end_year,
            output_dir=args.output_dir,
            dry_run=args.dry_run,
        )
        print(f"Download step completed for {len(files)} file(s).")
        return 0

    if args.command == "extract":
        files = extract_era5_archives(args.input_dir, pattern=args.pattern)
        print(f"Extract step completed for {len(files)} GRIB file(s).")
        return 0

    if args.command == "process":
        config = ProcessRunConfig(
            input_dir=args.input_dir,
            city=args.city,
            lightning_file=args.lightning_file,
            efficiency_file=args.efficiency_file,
        )
        outputs = run_process_step(config)
        print(f"Process step completed. Final dataset: {outputs.merged_monthly_corrected}")
        return 0

    if args.command == "all":
        outputs = run_full_pipeline(
            year_start=args.start_year,
            year_end=args.end_year,
            input_dir=args.input_dir,
            city=args.city,
            run_download=not args.skip_download,
            run_extract=not args.skip_extract,
            dry_run_download=args.dry_run_download,
        )
        print(f"Pipeline completed. Final dataset: {outputs.merged_monthly_corrected}")
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
