#!/usr/bin/env python3
"""
Unified ERA5 download entrypoint.

The script keeps the download logic in one place and leaves the operational
variable inventory in docs/era5_variable_checklist.md.
"""

from __future__ import annotations

import argparse
import calendar
import errno
import hashlib
import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


DATASET_DAILY = "derived-era5-single-levels-daily-statistics"
DATASET_SINGLE_LEVELS = "reanalysis-era5-single-levels"
DATASET_LAND = "reanalysis-era5-land"
DATASET_PRESSURE_LEVELS = "reanalysis-era5-pressure-levels"
DATASET_MODEL_LEVELS = "reanalysis-era5-complete"

DEFAULT_MONTHS = [f"{month:02d}" for month in range(1, 13)]
DEFAULT_DAYS = [f"{day:02d}" for day in range(1, 32)]
DEFAULT_TIMES = [f"{hour:02d}:00" for hour in range(24)]
DEFAULT_AREA_CUIABA = [-15.0, -56.5, -16.5, -55.5]
DEFAULT_GRID = "0.25/0.25"
DEFAULT_MODEL_LEVELS = "64/to/137"

MODEL_LEVEL_PARAMS = {
    "t": "130",
    "q": "133",
    "u": "131",
    "v": "132",
    "w": "135",
    "ciwc": "247",
    "cswc": "76",
    "clwc": "246",
    "crwc": "75",
}

PRESET_VARIABLES = {
    "daily-statistics": [
        "2m_temperature",
        "2m_dewpoint_temperature",
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "surface_pressure",
        "total_precipitation",
        "total_evaporation",
        "total_column_water_vapor",
    ],
    "single-levels": [
        "10m_u_component_of_wind",
        "10m_v_component_of_wind",
        "2m_dewpoint_temperature",
        "2m_temperature",
        "surface_pressure",
        "total_precipitation",
        "convective_precipitation",
        "large_scale_precipitation",
        "convective_available_potential_energy",
        "convective_inhibition",
        "total_column_water_vapour",
    ],
    "land": [
        "skin_temperature",
        "soil_temperature_level_1",
        "soil_temperature_level_2",
        "volumetric_soil_water_layer_1",
        "volumetric_soil_water_layer_2",
    ],
    "pressure-levels": [
        "temperature",
        "specific_humidity",
        "geopotential",
        "vertical_velocity",
    ],
    "model-levels": ["t", "q", "u", "v", "w", "ciwc", "cswc", "clwc", "crwc"],
}


@dataclass(frozen=True)
class DownloadTarget:
    label: str
    request: dict[str, Any]
    output: Path


def _months_from_args(months: list[str] | None) -> list[str]:
    if months is None:
        return DEFAULT_MONTHS
    return [f"{int(month):02d}" for month in months]


def _validate_years(start_year: int, end_year: int, minimum_year: int = 1940) -> None:
    if start_year < minimum_year:
        raise SystemExit(f"--start-year must be {minimum_year} or later")
    if start_year > end_year:
        raise SystemExit("--start-year must be less than or equal to --end-year")


def _validate_months(
    start_month: int,
    end_month: int,
    start_year: int | None = None,
    end_year: int | None = None,
) -> None:
    if not 1 <= start_month <= 12:
        raise SystemExit("--start-month must be between 1 and 12")
    if not 1 <= end_month <= 12:
        raise SystemExit("--end-month must be between 1 and 12")
    if (start_year is None or end_year is None or start_year == end_year) and start_month > end_month:
        raise SystemExit("--start-month must be less than or equal to --end-month")


def _validate_area(area: list[float] | None) -> None:
    if area is None:
        return
    if len(area) != 4:
        raise SystemExit("--area must have four values: N W S E")
    if area[0] < area[2]:
        raise SystemExit("--area is invalid: north must be greater than or equal to south")
    if area[1] > area[3]:
        raise SystemExit("--area is invalid: west must be less than or equal to east")


def _area_to_mars(area: list[float]) -> str:
    return "/".join(f"{value:g}" for value in area)


def _model_param_ids(short_names: list[str]) -> str:
    unknown = [name for name in short_names if name not in MODEL_LEVEL_PARAMS]
    if unknown:
        raise SystemExit(f"Unknown model-level short name(s): {', '.join(unknown)}")
    return "/".join(MODEL_LEVEL_PARAMS[name] for name in short_names)


def _default_output(prefix: str, suffix: str, extension: str, output_dir: Path) -> Path:
    return output_dir / f"{prefix}_{suffix}.{extension}"


_REQUEST_FINGERPRINT_HEX_CHARS = 10


def _daily_statistics_request(args: argparse.Namespace) -> dict[str, Any]:
    """Canonical daily-statistics request. The default filename hashes this mapping."""
    variables = getattr(args, "variables", None) or PRESET_VARIABLES["daily-statistics"]
    request: dict[str, Any] = {
        "product_type": "reanalysis",
        "variable": sorted(variables),
        "year": [str(year) for year in range(args.start_year, args.end_year + 1)],
        "month": _months_from_args(getattr(args, "months", None)),
        "daily_statistic": getattr(args, "statistic", None) or "daily_mean",
        "time_zone": getattr(args, "time_zone", None) or "utc+00:00",
        "frequency": getattr(args, "frequency", None) or "1_hourly",
    }
    area = getattr(args, "area", None)
    if area:
        request["area"] = [float(value) for value in area]
    return request


def _request_fingerprint(request: dict[str, Any]) -> str:
    payload = json.dumps(request, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:_REQUEST_FINGERPRINT_HEX_CHARS]


def _filename_token(value: str) -> str:
    return "".join(char if char.isalnum() or char in "+-_" else "-" for char in value)


def _variable_name_part(variables: list[str]) -> str:
    if not variables:
        return ""
    if len(variables) <= 2:
        return "_" + "_".join(_filename_token(variable) for variable in variables)
    digest = hashlib.sha256(",".join(sorted(variables)).encode("utf-8")).hexdigest()[:8]
    return f"_{len(variables)}vars_{digest}"


def _month_name_part(months: list[str]) -> str:
    if months == DEFAULT_MONTHS:
        return ""
    return "_m" + "-".join(months)


def _area_name_part(area: list[float] | None) -> str:
    if not area:
        return ""
    return "_area_" + "_".join(f"{value:g}" for value in area)


def _single_output_path(args: argparse.Namespace, prefix: str, extension: str) -> Path:
    if getattr(args, "output", None):
        return Path(args.output)
    request = _daily_statistics_request(args)
    years = request["year"]
    year_part = years[0] if len(years) == 1 else f"{years[0]}_{years[-1]}"
    statistic = str(request["daily_statistic"])
    stat_part = f"_{statistic}" if statistic != "daily_mean" else ""
    suffix = (
        f"{year_part}{stat_part}"
        f"{_variable_name_part(list(request['variable']))}"
        f"{_month_name_part(list(request['month']))}"
        f"_{_filename_token(str(request['frequency']))}"
        f"_{_filename_token(str(request['time_zone']))}"
        f"{_area_name_part(request.get('area'))}"
        f"_{_request_fingerprint(request)}"
    )
    return _default_output(prefix, suffix, extension, Path(args.output_dir))


def build_daily_statistics_target(args: argparse.Namespace) -> list[DownloadTarget]:
    _validate_years(args.start_year, args.end_year)
    _validate_area(args.area)
    request = _daily_statistics_request(args)
    output = _single_output_path(args, "era5_daily_statistics", "nc")
    return [DownloadTarget("daily-statistics", request, output)]


def download_era5_daily_stats(
    variables: list[str],
    year_start: int,
    year_end: int,
    months: list[str] | None = None,
    daily_statistic: str = "daily_mean",
    time_zone: str = "utc+00:00",
    frequency: str = "1_hourly",
    output_file: str | None = None,
    area: list[float] | None = None,
    overwrite: bool = True,
    sleep_seconds: int = 0,
) -> bool:
    """Backward-compatible Python API for the daily-statistics product."""
    args = argparse.Namespace(
        variables=variables,
        start_year=year_start,
        end_year=year_end,
        months=months,
        statistic=daily_statistic,
        time_zone=time_zone,
        frequency=frequency,
        output=output_file,
        output_dir="downloads",
        area=area,
        dry_run=False,
        overwrite=overwrite,
        sleep_seconds=sleep_seconds,
    )
    targets = build_daily_statistics_target(args)
    return retrieve_targets(DATASET_DAILY, targets, overwrite=overwrite, sleep_seconds=sleep_seconds) == 0


def _target_months_for_year(year: int, start_year: int, end_year: int, start_month: int, end_month: int) -> range:
    first = start_month if year == start_year else 1
    last = end_month if year == end_year else 12
    return range(first, last + 1)


def _hourly_output_extension(format_name: str, download_format: str) -> str:
    if download_format == "zip":
        return "zip"
    return "nc" if format_name == "netcdf" else "grib"


def build_hourly_targets(args: argparse.Namespace, preset: str, dataset: str) -> list[DownloadTarget]:
    _validate_years(args.start_year, args.end_year)
    _validate_months(args.start_month, args.end_month, args.start_year, args.end_year)
    _validate_area(args.area)
    variables = args.variables or PRESET_VARIABLES[preset]
    extension = _hourly_output_extension(args.format, args.download_format)
    targets: list[DownloadTarget] = []

    for year in range(args.start_year, args.end_year + 1):
        months = list(_target_months_for_year(year, args.start_year, args.end_year, args.start_month, args.end_month))
        if args.chunk == "year":
            month_values = [f"{month:02d}" for month in months]
            is_full_year = len(month_values) == 12
            month_suffix = "" if is_full_year else f"_{month_values[0]}-{month_values[-1]}"
            label = f"{year}" if is_full_year else f"{year}_{month_values[0]}-{month_values[-1]}"
            request = _build_hourly_request(args, dataset, variables, str(year), month_values)
            suffix = f"{preset}_{year}{month_suffix}_{_request_fingerprint(request)}"
            targets.append(
                DownloadTarget(
                    label=label,
                    request=request,
                    output=_default_output("era5", suffix, extension, Path(args.output_dir)),
                )
            )
            continue

        for month in months:
            month_value = f"{month:02d}"
            label = f"{year}-{month_value}"
            request = _build_hourly_request(args, dataset, variables, str(year), [month_value])
            suffix = f"{preset}_{year}_{month_value}_{_request_fingerprint(request)}"
            targets.append(
                DownloadTarget(
                    label=label,
                    request=request,
                    output=_default_output("era5", suffix, extension, Path(args.output_dir)),
                )
            )

    return targets


def _canonical_pressure_levels(levels: list[str]) -> list[str]:
    """Numeric order so the same levels share one request hash and filename.

    ``json.dumps`` keeps list order, and the default path embeds that hash.
    ``1000`` sorts before ``850`` as text, so the key is the integer value.
    """

    def sort_key(level: str) -> tuple[int, int | str, str]:
        try:
            return (0, int(level), level)
        except ValueError:
            return (1, level, level)

    return sorted(levels, key=sort_key)


def _build_hourly_request(
    args: argparse.Namespace,
    dataset: str,
    variables: list[str],
    year: str,
    months: list[str],
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "variable": sorted(variables),
        "year": year,
        "month": months,
        "day": DEFAULT_DAYS,
        "time": DEFAULT_TIMES,
        "data_format": args.format,
        "download_format": args.download_format,
    }
    if args.area is not None:
        request["area"] = args.area
    if dataset != DATASET_LAND:
        request["product_type"] = "reanalysis"
    if dataset == DATASET_PRESSURE_LEVELS:
        request["pressure_level"] = _canonical_pressure_levels(list(args.pressure_levels))
    return request


def build_model_level_targets(args: argparse.Namespace) -> list[DownloadTarget]:
    _validate_years(args.start_year, args.end_year)
    _validate_months(args.start_month, args.end_month, args.start_year, args.end_year)
    _validate_area(args.area)
    variables = args.variables or PRESET_VARIABLES["model-levels"]
    extension = "nc" if args.format == "netcdf" else "grib"
    output_dir = Path(args.output_dir)
    output_prefix = getattr(args, "output_prefix", "era5_model_levels")
    targets: list[DownloadTarget] = []

    for year in range(args.start_year, args.end_year + 1):
        months = _target_months_for_year(year, args.start_year, args.end_year, args.start_month, args.end_month)
        for month in months:
            if args.chunk == "month":
                last_day = calendar.monthrange(year, month)[1]
                label = f"{year}-{month:02d}"
                date_range = f"{year}-{month:02d}-01/to/{year}-{month:02d}-{last_day:02d}"
                output = _default_output(output_prefix, f"{year}_{month:02d}", extension, output_dir)
                targets.append(
                    DownloadTarget(label, _build_model_level_request(args, variables, date_range), output)
                )
                continue

            for day in range(1, calendar.monthrange(year, month)[1] + 1):
                label = f"{year}-{month:02d}-{day:02d}"
                date_range = label
                output = _default_output(output_prefix, f"{year}_{month:02d}_{day:02d}", extension, output_dir)
                targets.append(
                    DownloadTarget(label, _build_model_level_request(args, variables, date_range), output)
                )

    return targets


def _build_model_level_request(args: argparse.Namespace, variables: list[str], date_range: str) -> dict[str, Any]:
    return {
        "class": "ea",
        "expver": "1",
        "stream": "oper",
        "type": "an",
        "levtype": "ml",
        "levelist": args.levelist,
        "param": _model_param_ids(variables),
        "date": date_range,
        "time": "00:00:00/to/23:00:00/by/1",
        "area": _area_to_mars(args.area),
        "grid": args.grid,
        "format": args.format,
    }


def print_dry_run(dataset: str, targets: list[DownloadTarget], overwrite: bool) -> None:
    print(f"Dataset: {dataset}")
    print(f"Targets: {len(targets)}")
    print(f"Overwrite: {'yes' if overwrite else 'no'}")
    for target in targets:
        exists = "exists" if target.output.exists() else "missing"
        print(f"- [{target.label}] {target.output} ({exists})")
    if targets:
        print("\nFirst request:")
        print(json.dumps(targets[0].request, indent=2, ensure_ascii=False))


def _output_lock_path(output: Path) -> Path:
    """Stable short lock name in the destination directory.

    The basename is a hash of the target name so a destination already near
    NAME_MAX does not grow a ``.lock`` suffix past the filesystem limit.
    """
    digest = hashlib.sha256(output.name.encode("utf-8")).hexdigest()[:16]
    return output.with_name(f"era5-{digest}.lock")


def _staging_path(output: Path) -> Path:
    """Same-directory staging name that stays well under NAME_MAX."""
    return output.with_name(f"part-{uuid.uuid4().hex}.part")


_WINDOWS_LOCK_POLL_SECONDS = 0.2
# ``msvcrt.LK_NBLCK`` raises these when another process still holds the region.
_WINDOWS_LOCK_BUSY = {errno.EACCES, errno.EDEADLK, getattr(errno, "EDEADLOCK", errno.EDEADLK)}


def _acquire_file_lock(fd: int) -> None:
    """Block on a kernel lock released automatically when the holder exits.

    Unix uses ``flock``, which waits with no timeout. Windows ``msvcrt.LK_LOCK``
    retries for about ten seconds and then raises, so a second run would record
    a long CDS transfer as a download failure. ``LK_NBLCK`` is polled until the
    other holder releases the region. ``os.kill(pid, 0)`` is not a liveness
    probe on Windows because signal 0 terminates the process.
    """
    if sys.platform == "win32":
        import msvcrt

        os.lseek(fd, 0, os.SEEK_SET)
        if os.fstat(fd).st_size == 0:
            os.write(fd, b"\0")
            os.lseek(fd, 0, os.SEEK_SET)
        while True:
            try:
                msvcrt.locking(fd, msvcrt.LK_NBLCK, 1)
                return
            except OSError as exc:
                if exc.errno not in _WINDOWS_LOCK_BUSY:
                    raise
                time.sleep(_WINDOWS_LOCK_POLL_SECONDS)
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_EX)


def _release_file_lock(fd: int) -> None:
    if sys.platform == "win32":
        import msvcrt

        try:
            os.lseek(fd, 0, os.SEEK_SET)
            msvcrt.locking(fd, msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        return
    import fcntl

    fcntl.flock(fd, fcntl.LOCK_UN)


@contextmanager
def _exclusive_output_lock(output: Path) -> Iterator[None]:
    """Block until this process holds the kernel lock for ``output``.

    The lock file is never unlinked. Deleting it after a stale check can
    remove a replacement lock created by another live download. The kernel
    drops the lock when every holder fd closes, including on crash, so a
    leftover file does not stay owned by a reused PID.
    """
    lock_path = _output_lock_path(output)
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
    acquired = False
    try:
        _acquire_file_lock(fd)
        acquired = True
        yield
    finally:
        if acquired:
            _release_file_lock(fd)
        os.close(fd)


def _discard_part_file(part_output: Path) -> None:
    if not part_output.exists():
        return
    try:
        part_output.unlink()
    except OSError:
        pass


def retrieve_targets(
    dataset: str,
    targets: list[DownloadTarget],
    overwrite: bool,
    sleep_seconds: int,
    successful_targets: list[DownloadTarget] | None = None,
    failure_messages: list[str] | None = None,
) -> int:
    try:
        import cdsapi
    except Exception as exc:
        raise RuntimeError("cdsapi is required for downloads. Install requirements and configure ~/.cdsapirc.") from exc

    client = cdsapi.Client()
    failures = failure_messages if failure_messages is not None else []
    targets_to_download = [target for target in targets if overwrite or not target.output.exists()]

    if not targets_to_download:
        print("Nothing to download. All target files already exist.")
        return 0

    for index, target in enumerate(targets_to_download):
        target.output.parent.mkdir(parents=True, exist_ok=True)
        part_output = _staging_path(target.output)
        attempted_download = False
        try:
            with _exclusive_output_lock(target.output):
                if not overwrite and target.output.exists():
                    print(f"[{target.label}] already exists, skipping {target.output}")
                else:
                    attempted_download = True
                    print(f"[{target.label}] downloading -> {target.output}")
                    try:
                        _discard_part_file(part_output)
                        client.retrieve(dataset, target.request).download(str(part_output))
                        if not overwrite and target.output.exists():
                            print(f"[{target.label}] already exists, skipping {target.output}")
                        else:
                            part_output.replace(target.output)
                            if successful_targets is not None:
                                successful_targets.append(target)
                            print(f"[{target.label}] ok")
                    finally:
                        _discard_part_file(part_output)
        except Exception as exc:  # pragma: no cover - depends on CDS/network
            failures.append(f"{target.label}: {exc}")
            print(f"[{target.label}] error: {exc}", file=sys.stderr)

        if attempted_download and index < len(targets_to_download) - 1 and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if failures:
        print("\nFailures:", file=sys.stderr)
        for failure in failures:
            print(f"- {failure}", file=sys.stderr)
        return 1
    return 0


def run_download(args: argparse.Namespace, dataset: str, targets: list[DownloadTarget]) -> int:
    if args.dry_run:
        print_dry_run(dataset, targets, args.overwrite)
        return 0
    return retrieve_targets(dataset, targets, args.overwrite, args.sleep_seconds)


def add_common_args(parser: argparse.ArgumentParser, *, hourly: bool = False) -> None:
    parser.add_argument("--start-year", type=int, required=True)
    parser.add_argument("--end-year", type=int, required=True)
    parser.add_argument("--variables", nargs="+", default=None, help="Override preset variables.")
    parser.add_argument("--area", nargs=4, type=float, default=None, metavar=("N", "W", "S", "E"))
    parser.add_argument("--output-dir", default="downloads", help="Directory for generated output files.")
    parser.add_argument("--dry-run", action="store_true", help="Print target files and first CDS request without downloading.")
    parser.add_argument("--overwrite", action="store_true", help="Download even when the target file already exists.")
    parser.add_argument("--sleep-seconds", type=int, default=5, help="Pause between CDS requests.")
    if hourly:
        parser.add_argument("--start-month", type=int, default=1)
        parser.add_argument("--end-month", type=int, default=12)
        parser.add_argument("--format", choices=["grib", "netcdf"], default="grib")
        parser.add_argument("--download-format", choices=["zip", "unarchived"], default="zip")
        parser.add_argument("--chunk", choices=["year", "month"], default="year")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download ERA5 products from the Copernicus Climate Data Store.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "Examples:\n"
            "  python3 download_era5_daily.py daily-statistics --variables 2m_temperature --start-year 2020 --end-year 2020 --dry-run\n"
            "  python3 download_era5_daily.py single-levels --start-year 2020 --end-year 2020 --area -15 -56.5 -16.5 -55.5 --dry-run\n"
            "  python3 download_era5_daily.py model-levels --start-year 2020 --end-year 2020 --start-month 1 --end-month 1 --dry-run\n"
        ),
    )
    subparsers = parser.add_subparsers(dest="preset", required=True)

    daily = subparsers.add_parser("daily-statistics", help=f"Download {DATASET_DAILY}.")
    add_common_args(daily)
    daily.add_argument("--months", nargs="+", default=None, help="Months to download. Default: all months.")
    daily.add_argument(
        "--statistic",
        default="daily_mean",
        choices=["daily_mean", "daily_minimum", "daily_maximum", "daily_spread"],
    )
    daily.add_argument("--time-zone", default="utc+00:00")
    daily.add_argument("--frequency", default="1_hourly", choices=["1_hourly", "3_hourly", "6_hourly"])
    daily.add_argument("--output", default=None, help="Single output file path for this request.")

    single = subparsers.add_parser("single-levels", help=f"Download {DATASET_SINGLE_LEVELS}.")
    add_common_args(single, hourly=True)
    single.set_defaults(area=DEFAULT_AREA_CUIABA)

    land = subparsers.add_parser("land", help=f"Download {DATASET_LAND}.")
    add_common_args(land, hourly=True)
    land.set_defaults(area=DEFAULT_AREA_CUIABA, chunk="month")

    pressure = subparsers.add_parser("pressure-levels", help=f"Download {DATASET_PRESSURE_LEVELS}.")
    add_common_args(pressure, hourly=True)
    pressure.set_defaults(area=DEFAULT_AREA_CUIABA, chunk="month")
    pressure.add_argument("--pressure-levels", nargs="+", default=["850", "700", "500"])

    model = subparsers.add_parser("model-levels", help=f"Download {DATASET_MODEL_LEVELS} model levels.")
    add_common_args(model)
    model.set_defaults(area=DEFAULT_AREA_CUIABA, output_dir="downloads/model_levels")
    model.add_argument("--start-month", type=int, default=1)
    model.add_argument("--end-month", type=int, default=12)
    model.add_argument("--chunk", choices=["month", "day"], default="month")
    model.add_argument("--levelist", default=DEFAULT_MODEL_LEVELS)
    model.add_argument("--grid", default=DEFAULT_GRID)
    model.add_argument("--output-prefix", default="era5_model_levels", help="Filename prefix for generated model-level files.")
    model.add_argument("--format", choices=["grib", "netcdf"], default="grib")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds cannot be negative")

    if args.preset == "daily-statistics":
        return run_download(args, DATASET_DAILY, build_daily_statistics_target(args))
    if args.preset == "single-levels":
        return run_download(args, DATASET_SINGLE_LEVELS, build_hourly_targets(args, args.preset, DATASET_SINGLE_LEVELS))
    if args.preset == "land":
        return run_download(args, DATASET_LAND, build_hourly_targets(args, args.preset, DATASET_LAND))
    if args.preset == "pressure-levels":
        return run_download(args, DATASET_PRESSURE_LEVELS, build_hourly_targets(args, args.preset, DATASET_PRESSURE_LEVELS))
    if args.preset == "model-levels":
        return run_download(args, DATASET_MODEL_LEVELS, build_model_level_targets(args))

    parser.error(f"Unknown preset: {args.preset}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
