#!/usr/bin/env python3
"""Standalone ERA5 model-level downloader for the Ehrensperger et al. setup."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from download_era5_daily import (  # noqa: E402
    DATASET_MODEL_LEVELS,
    DEFAULT_AREA_CUIABA,
    DEFAULT_GRID,
    DEFAULT_MODEL_LEVELS,
    MODEL_LEVEL_PARAMS,
    PRESET_VARIABLES,
    _validate_area,
    _validate_months,
    _validate_years,
    build_model_level_targets,
    run_download,
)

YEAR_START = 2005
YEAR_END = 2023
DEFAULT_OUTPUT_DIR = ROOT / "data" / "raw" / "era5" / "model_levels_ehrensperger"
DEFAULT_PREFIX = "era5_cuiaba_model_levels_ehrensperger"
DEFAULT_PARAM_SHORT_NAMES = PRESET_VARIABLES["model-levels"]


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download ERA5 model-level fields used in the Ehrensperger et al. setup, "
            "with monthly chunking by default."
        )
    )
    parser.add_argument("--start-year", type=int, default=YEAR_START)
    parser.add_argument("--end-year", type=int, default=YEAR_END)
    parser.add_argument("--start-month", type=int, default=1)
    parser.add_argument("--end-month", type=int, default=12)
    parser.add_argument(
        "--chunk",
        choices=["month", "day"],
        default="month",
        help="Request chunking. Use 'day' if monthly requests exceed CDS limits or cost.",
    )
    parser.add_argument(
        "--variables",
        nargs="+",
        choices=sorted(MODEL_LEVEL_PARAMS),
        default=DEFAULT_PARAM_SHORT_NAMES,
        help="ERA5 model-level short names to download.",
    )
    parser.add_argument(
        "--levelist",
        default=DEFAULT_MODEL_LEVELS,
        help="Model levels in MARS syntax, for example '64/to/137'.",
    )
    parser.add_argument(
        "--area",
        nargs=4,
        type=float,
        default=DEFAULT_AREA_CUIABA,
        metavar=("N", "W", "S", "E"),
        help="Area in MARS/CDS order: North West South East.",
    )
    parser.add_argument("--grid", default=DEFAULT_GRID, help="Requested regular grid, e.g. '0.25/0.25'.")
    parser.add_argument(
        "--format",
        choices=["grib", "netcdf"],
        default="grib",
        help="Output format requested from CDS/MARS.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX, help="Filename prefix for generated files.")
    parser.add_argument("--dry-run", action="store_true", help="List requests without downloading.")
    parser.add_argument("--overwrite", action="store_true", help="Download again even if the file exists.")
    parser.add_argument("--sleep-seconds", type=int, default=10, help="Pause between requests.")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    _validate_years(args.start_year, args.end_year)
    _validate_months(args.start_month, args.end_month, args.start_year, args.end_year)
    _validate_area(args.area)
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds cannot be negative")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_args(args)

    download_args = argparse.Namespace(
        start_year=args.start_year,
        end_year=args.end_year,
        start_month=args.start_month,
        end_month=args.end_month,
        variables=args.variables,
        area=args.area,
        output_dir=str(args.output_dir),
        output_prefix=args.prefix,
        chunk=args.chunk,
        levelist=args.levelist,
        grid=args.grid,
        format=args.format,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        sleep_seconds=args.sleep_seconds,
    )

    targets = build_model_level_targets(download_args)
    if not targets:
        raise SystemExit("No download targets were generated.")

    print("=" * 72)
    print("ERA5 model-level download for Cuiaba (Ehrensperger setup)")
    print("=" * 72)
    print(f"Dataset CDS/MARS: {DATASET_MODEL_LEVELS}")
    print(f"Target period: {targets[0].label} to {targets[-1].label}")
    print(f"Expected files: {len(targets)}")
    print(f"Overwrite: {'yes' if args.overwrite else 'no'}")
    print(f"Area N/W/S/E: {args.area}")
    print(f"Requested grid: {args.grid}")
    print(f"Model levels: {args.levelist}")
    print(f"Format: {args.format}")
    print("Requested variables:")
    for short_name in args.variables:
        print(f"  - {short_name}: paramId {MODEL_LEVEL_PARAMS[short_name]}")

    exit_code = run_download(download_args, DATASET_MODEL_LEVELS, targets)

    print("\nFinal summary:")
    print(f"  Target files: {len(targets)}")
    print(f"  Mode: {'dry-run' if args.dry_run else 'download'}")
    print("\nSuggested next steps:")
    print("  1. Verify the temporal order of downloaded GRIB files.")
    print("  2. Extract daily and monthly means/maxima for each variable and level.")
    print("  3. Derive mixed-phase, shear, moisture, and ice diagnostics.")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
