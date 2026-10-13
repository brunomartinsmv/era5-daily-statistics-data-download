#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from download_era5_daily import DownloadTarget, retrieve_targets  # noqa: E402

YEAR_START = 2005
YEAR_END = 2023
AREA_CUIABA = [-15.0, -56.5, -16.5, -55.5]  # N, W, S, E
MONTHS = [f"{month:02d}" for month in range(1, 13)]
DAYS = [f"{day:02d}" for day in range(1, 32)]
TIMES = [f"{hour:02d}:00" for hour in range(24)]

DATASETS = {
    "single-levels": {
        "dataset": "reanalysis-era5-single-levels",
        "default_chunk": "year",
        "request": {
            "product_type": "reanalysis",
            "variable": [
                "skin_temperature",
                "boundary_layer_height",
                "surface_latent_heat_flux",
                "surface_sensible_heat_flux",
                "convective_precipitation",
                "large_scale_precipitation",
            ],
            "area": AREA_CUIABA,
            "month": MONTHS,
            "day": DAYS,
            "time": TIMES,
            "data_format": "grib",
            "download_format": "zip",
        },
        "output_dir": PROJECT_ROOT / "data" / "raw" / "era5" / "temperature_regime_single_levels",
        "prefix": "era5_cuiaba_temperature_regime_single_levels",
    },
    "land": {
        "dataset": "reanalysis-era5-land",
        "default_chunk": "month",
        "request": {
            "variable": [
                "skin_temperature",
                "soil_temperature_level_1",
                "soil_temperature_level_2",
                "volumetric_soil_water_layer_1",
                "volumetric_soil_water_layer_2",
            ],
            "area": AREA_CUIABA,
            "month": MONTHS,
            "day": DAYS,
            "time": TIMES,
            "data_format": "grib",
            "download_format": "zip",
        },
        "output_dir": PROJECT_ROOT / "data" / "raw" / "era5_land" / "temperature_regime_land",
        "prefix": "era5_land_cuiaba_temperature_regime",
    },
    "pressure-levels": {
        "dataset": "reanalysis-era5-pressure-levels",
        "default_chunk": "month",
        "request": {
            "product_type": "reanalysis",
            "variable": [
                "temperature",
                "specific_humidity",
                "geopotential",
                "vertical_velocity",
            ],
            "pressure_level": ["850", "700", "500"],
            "area": AREA_CUIABA,
            "month": MONTHS,
            "day": DAYS,
            "time": TIMES,
            "data_format": "grib",
            "download_format": "zip",
        },
        "output_dir": PROJECT_ROOT / "data" / "raw" / "era5" / "temperature_regime_pressure_levels",
        "prefix": "era5_cuiaba_temperature_regime_pressure_levels",
    },
}


def _month_label(months: list[str]) -> str:
    if len(months) == 1:
        return months[0]
    return f"{months[0]}-{months[-1]}"


def build_targets(
    kind: str,
    year_start: int,
    year_end: int,
    month_start: int,
    month_end: int,
    chunk_mode: str,
) -> list[tuple[int, list[str], Path]]:
    cfg = DATASETS[kind]
    output_dir = cfg["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)
    prefix = cfg["prefix"]
    targets: list[tuple[int, list[str], Path]] = []

    for year in range(year_start, year_end + 1):
        if chunk_mode == "year":
            start_month = month_start if year == year_start else 1
            end_month = month_end if year == year_end else 12
            months = [f"{month:02d}" for month in range(start_month, end_month + 1)]
            targets.append((year, months, output_dir / f"{prefix}_{year}.zip"))
            continue

        if chunk_mode == "month":
            start_month = month_start if year == year_start else 1
            end_month = month_end if year == year_end else 12
            for month in range(start_month, end_month + 1):
                month_str = f"{month:02d}"
                targets.append((year, [month_str], output_dir / f"{prefix}_{year}_{month_str}.zip"))
            continue

        raise ValueError(f"Invalid chunk_mode: {chunk_mode}")

    return targets


def build_request(kind: str, year: int, months: list[str]) -> dict[str, object]:
    cfg = DATASETS[kind]
    request = dict(cfg["request"])
    request["year"] = [str(year)]
    request["month"] = months
    return request


def summarize_target_state(
    targets: list[tuple[int, list[str], Path]],
    overwrite: bool,
) -> tuple[list[tuple[int, list[str], Path]], list[tuple[int, list[str], Path]]]:
    if overwrite:
        return [], targets
    existing = []
    missing = []
    for item in targets:
        if item[2].exists():
            existing.append(item)
        else:
            missing.append(item)
    return existing, missing


def download_kind(
    kind: str,
    year_start: int,
    year_end: int,
    month_start: int,
    month_end: int,
    chunk_mode: str,
    dry_run: bool,
    sleep_seconds: int,
    overwrite: bool,
) -> tuple[list[Path], list[str]]:
    cfg = DATASETS[kind]
    targets = build_targets(kind, year_start, year_end, month_start, month_end, chunk_mode)
    existing_targets, missing_targets = summarize_target_state(targets, overwrite)

    print("=" * 72)
    print(f"Preset: {kind}")
    print(f"CDS dataset: {cfg['dataset']}")
    print(f"Output: {cfg['output_dir']}")
    print(f"Chunking: {chunk_mode}")
    print(f"Already present: {len(existing_targets)}")
    print(f"Missing: {len(missing_targets)}")
    print("Variables:")
    for variable in cfg["request"]["variable"]:
        print(f"  - {variable}")
    if "pressure_level" in cfg["request"]:
        print("Pressure levels:")
        for level in cfg["request"]["pressure_level"]:
            print(f"  - {level} hPa")

    if dry_run:
        print("Dry-run: missing files that would be generated:")
        for year, months, target in missing_targets:
            print(f"  [{year}][{_month_label(months)}] {target}")
        return [target for _, _, target in missing_targets], []

    if not missing_targets:
        print(f"[{kind}] Nothing to download. All expected files already exist.")
        return [target for _, _, target in existing_targets], []

    download_targets = [
        DownloadTarget(
            label=f"{kind}:{year}:{_month_label(months)}",
            request=build_request(kind, year, months),
            output=target,
        )
        for year, months, target in missing_targets
    ]

    succeeded_targets: list[DownloadTarget] = []
    failures: list[str] = []
    retrieve_targets(
        cfg["dataset"],
        download_targets,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
        successful_targets=succeeded_targets,
        failure_messages=failures,
    )
    generated = [t.output for t in succeeded_targets]
    return generated, failures


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download additional ERA5/ERA5-Land variables to reassess lightning-regime "
            "sensitivity to temperature around Cuiaba."
        )
    )
    parser.add_argument(
        "--preset",
        choices=["single-levels", "land", "pressure-levels", "all"],
        default="all",
        help=(
            "Variable group to download. "
            "'single-levels' covers skt/blh/fluxes/cp/lsp; "
            "'land' covers soil temperature and moisture; "
            "'pressure-levels' covers 850/700/500 hPa profiles for derived indices."
        ),
    )
    parser.add_argument("--start-year", type=int, default=YEAR_START)
    parser.add_argument("--end-year", type=int, default=YEAR_END)
    parser.add_argument(
        "--start-month",
        type=int,
        default=1,
        help="Start month for presets that use monthly chunking.",
    )
    parser.add_argument(
        "--end-month",
        type=int,
        default=12,
        help="End month for presets that use monthly chunking.",
    )
    parser.add_argument(
        "--chunk",
        choices=["auto", "year", "month"],
        default="auto",
        help=(
            "Request chunking strategy. "
            "'auto' uses year for single-levels and month for land/pressure-levels."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="List target files without downloading.")
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Download even when the target file already exists.",
    )
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=5,
        help="Pause between downloads to reduce CDS rate-limit errors.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.start_year > args.end_year:
        raise SystemExit("--start-year cannot be greater than --end-year")
    if not 1 <= args.start_month <= 12:
        raise SystemExit("--start-month must be between 1 and 12")
    if not 1 <= args.end_month <= 12:
        raise SystemExit("--end-month must be between 1 and 12")
    if args.start_year == args.end_year and args.start_month > args.end_month:
        raise SystemExit("Within the same year, --start-month cannot be greater than --end-month")
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds cannot be negative")

    presets = ["single-levels", "land", "pressure-levels"] if args.preset == "all" else [args.preset]

    print("=" * 72)
    print("ERA5 variable download for temperature vs lightning-regime analysis")
    print("=" * 72)
    print(f"Period: {args.start_year}-{args.end_year}")
    print(f"Month range: {args.start_month:02d}-{args.end_month:02d}")
    print(f"Cuiaba area: {AREA_CUIABA}")
    print("Prerequisites:")
    print("  - ~/.cdsapirc configured")
    print("  - pip install cdsapi")

    all_paths: list[Path] = []
    all_failures: list[str] = []
    for preset in presets:
        chunk_mode = DATASETS[preset]["default_chunk"] if args.chunk == "auto" else args.chunk
        paths, failures = download_kind(
            kind=preset,
            year_start=args.start_year,
            year_end=args.end_year,
            month_start=args.start_month,
            month_end=args.end_month,
            chunk_mode=chunk_mode,
            dry_run=args.dry_run,
            sleep_seconds=args.sleep_seconds,
            overwrite=args.overwrite,
        )
        all_paths.extend(paths)
        all_failures.extend(failures)

    print("\nFinal summary:")
    print(f"  Presets run: {', '.join(presets)}")
    print(f"  Target files: {len(all_paths)}")
    if args.dry_run:
        print("  Mode: dry-run")
    elif all_failures:
        print("  Download finished with failures")
    else:
        print("  Download finished")

    print("\nSuggested next steps:")
    print("  1. Extract GRIB/ZIP contents.")
    print("  2. Aggregate to daily/monthly values as needed per variable.")
    print("  3. Re-run the analysis with skt/soil/cp/blh and, separately, derived indices.")

    if all_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
