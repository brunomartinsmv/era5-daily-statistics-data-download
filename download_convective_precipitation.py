#!/usr/bin/env python3
from __future__ import annotations

import argparse
import importlib.util
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

def _load_era5_config():
    config_path = PROJECT_ROOT / "src" / "era5" / "config.py"
    module_name = "era5_config_for_cp"
    spec = importlib.util.spec_from_file_location(module_name, config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load ERA5 config from {config_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


ERA5_CONFIG = _load_era5_config()

DATA_PROCESSED_DAILY = ERA5_CONFIG.DATA_PROCESSED_DAILY
DATA_RAW_ERA5 = ERA5_CONFIG.DATA_RAW_ERA5
DEFAULT_CITY = ERA5_CONFIG.DEFAULT_CITY
DEFAULT_ERA5_CP_DAILY_OUTPUT = ERA5_CONFIG.DEFAULT_ERA5_CP_DAILY_OUTPUT
DEFAULT_MERGED_DAILY_CORRECTED_OUTPUT = ERA5_CONFIG.DEFAULT_MERGED_DAILY_CORRECTED_OUTPUT
DEFAULT_MERGED_DAILY_OUTPUT = ERA5_CONFIG.DEFAULT_MERGED_DAILY_OUTPUT
DEFAULT_YEAR_END = ERA5_CONFIG.DEFAULT_YEAR_END
DEFAULT_YEAR_START = ERA5_CONFIG.DEFAULT_YEAR_START
ERA5_AREA_CUIABA = ERA5_CONFIG.ERA5_AREA_CUIABA
ERA5_DAYS = ERA5_CONFIG.ERA5_DAYS
ERA5_MONTHS = ERA5_CONFIG.ERA5_MONTHS
ERA5_TIMES = ERA5_CONFIG.ERA5_TIMES


DEFAULT_RAW_DIR = DATA_RAW_ERA5 / "cp"
DEFAULT_CP_OUTPUT = DEFAULT_ERA5_CP_DAILY_OUTPUT
DEFAULT_MERGE_TARGETS = [
    DEFAULT_MERGED_DAILY_CORRECTED_OUTPUT,
    DEFAULT_MERGED_DAILY_OUTPUT,
]
DEFAULT_COLUMN_NAME = "precip_conv"


def _require_pandas():
    try:
        import pandas as pd
    except Exception as exc:
        raise RuntimeError(
            "pandas is required for processing or merge steps. Install project dependencies first."
        ) from exc
    return pd


def _build_targets(year_start: int, year_end: int, output_dir: Path, city: str) -> list[tuple[int, Path]]:
    if year_end < year_start:
        raise ValueError("year_end must be >= year_start")

    output_dir.mkdir(parents=True, exist_ok=True)
    return [
        (year, output_dir / f"era5_{city}_cp_{year}.zip")
        for year in range(year_start, year_end + 1)
    ]


def _build_request(year: int) -> dict[str, object]:
    return {
        "product_type": ["reanalysis"],
        "variable": ["convective_precipitation"],
        "year": [str(year)],
        "month": ERA5_MONTHS,
        "day": ERA5_DAYS,
        "time": ERA5_TIMES,
        "data_format": "grib",
        "download_format": "zip",
        "area": ERA5_AREA_CUIABA,
    }


def download_yearly_cp_archives(
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    output_dir: Path = DEFAULT_RAW_DIR,
    city: str = DEFAULT_CITY,
    sleep_seconds: int = 5,
    dry_run: bool = False,
) -> list[Path]:
    targets = _build_targets(year_start, year_end, output_dir, city)

    if dry_run:
        return [target for _, target in targets]

    try:
        import cdsapi
    except Exception as exc:
        raise RuntimeError(
            "cdsapi is required for download step. Install it and configure ~/.cdsapirc."
        ) from exc

    client = cdsapi.Client()
    failures: list[str] = []
    last_index = len(targets) - 1

    for index, (year, target) in enumerate(targets):
        if target.exists():
            print(f"[{year}] archive already exists, skipping: {target}")
            continue

        request = _build_request(year)
        print(f"[{year}] downloading convective_precipitation...")
        try:
            client.retrieve("reanalysis-era5-single-levels", request).download(str(target))
            print(f"[{year}] ok -> {target}")
        except Exception as exc:  # pragma: no cover - network behavior
            failures.append(f"{year}: {exc}")
            print(f"[{year}] error: {exc}")

        if index < last_index and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if failures:
        joined = "\n".join(failures)
        raise RuntimeError(f"Failed to download one or more years:\n{joined}")

    return [target for _, target in targets]


def _daily_series_from_grib(grib_path: Path, year: int, column_name: str) -> pd.Series:
    pd = _require_pandas()
    try:
        import xarray as xr
    except Exception as exc:
        raise RuntimeError(
            "xarray and cfgrib are required for processing GRIB files."
        ) from exc

    ds = xr.open_dataset(
        grib_path,
        engine="cfgrib",
        backend_kwargs={"filter_by_keys": {"shortName": "cp"}},
    )

    try:
        data_var = list(ds.data_vars)[0]
        data = ds[data_var]

        spatial_dims = [dim for dim in data.dims if dim not in {"time", "step"} and data.sizes.get(dim, 1) > 1]
        if spatial_dims:
            data = data.mean(dim=spatial_dims)

        for dim in [dim for dim in data.dims if dim not in {"time", "step"}]:
            data = data.isel({dim: 0}, drop=True)

        if "valid_time" not in data.coords:
            raise ValueError(f"'valid_time' coordinate not found in {grib_path}")

        flat = data.stack(obs=("time", "step")).transpose("obs")
        valid_time = pd.to_datetime(flat["valid_time"].values)
        values = flat.values
        hourly = pd.Series(values, index=valid_time).sort_index()

        year_start = pd.Timestamp(f"{year}-01-01 00:00:00")
        year_end = pd.Timestamp(f"{year + 1}-01-01 00:00:00")
        hourly = hourly.loc[(hourly.index >= year_start) & (hourly.index < year_end)]

        daily = hourly.groupby(hourly.index.floor("D")).sum() * 1000.0
        series = daily.sort_index()
        series.name = column_name
        return series
    finally:
        ds.close()


def extract_daily_cp_from_archive(
    archive_path: Path,
    year: int,
    column_name: str = DEFAULT_COLUMN_NAME,
) -> pd.Series:
    import tempfile
    import zipfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        with zipfile.ZipFile(archive_path) as archive:
            archive.extractall(tmp_path)

        grib_files = sorted(tmp_path.glob("*.grib")) + sorted(tmp_path.glob("*.grib2"))
        if not grib_files:
            raise FileNotFoundError(f"No GRIB file found in {archive_path}")

        return _daily_series_from_grib(grib_files[0], year=year, column_name=column_name)


def process_cp_archives(
    input_dir: Path = DEFAULT_RAW_DIR,
    output_csv: Path = DEFAULT_CP_OUTPUT,
    year_start: int = DEFAULT_YEAR_START,
    year_end: int = DEFAULT_YEAR_END,
    city: str = DEFAULT_CITY,
    column_name: str = DEFAULT_COLUMN_NAME,
) -> pd.DataFrame:
    pd = _require_pandas()
    series_list: list[pd.Series] = []

    for year, archive_path in _build_targets(year_start, year_end, input_dir, city):
        if not archive_path.exists():
            raise FileNotFoundError(f"Missing archive for {year}: {archive_path}")

        print(f"[{year}] processing {archive_path.name}...")
        series = extract_daily_cp_from_archive(archive_path, year=year, column_name=column_name)
        series_list.append(series)

    if not series_list:
        raise RuntimeError("No cp archive was processed.")

    df = pd.concat(series_list).sort_index().to_frame()
    df.index = pd.to_datetime(df.index)
    df = df[~df.index.duplicated(keep="first")]
    df.index.name = "date"
    df = df.reset_index()
    df["date"] = pd.to_datetime(df["date"])

    output_csv.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    return df


def merge_cp_with_daily_datasets(
    cp_daily: pd.DataFrame,
    targets: list[Path] | None = None,
    column_name: str = DEFAULT_COLUMN_NAME,
    output_suffix: str = "_with_cp",
) -> list[Path]:
    pd = _require_pandas()
    merge_targets = targets or DEFAULT_MERGE_TARGETS
    written: list[Path] = []

    cp_df = cp_daily.copy()
    cp_df["date"] = pd.to_datetime(cp_df["date"])
    cp_df = cp_df[["date", column_name]].drop_duplicates(subset=["date"])

    for target in merge_targets:
        if not target.exists():
            print(f"merge target not found, skipping: {target}")
            continue

        df = pd.read_csv(target)
        if "date" not in df.columns:
            raise ValueError(f"Target dataset has no 'date' column: {target}")

        df["date"] = pd.to_datetime(df["date"])
        if column_name in df.columns:
            df = df.drop(columns=[column_name])

        merged = df.merge(cp_df, on="date", how="left", validate="one_to_one")
        output_path = target.with_name(f"{target.stem}{output_suffix}.csv")
        merged.to_csv(output_path, index=False)
        written.append(output_path)
        print(f"merged dataset written: {output_path}")

    return written


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Download and process ERA5 convective precipitation (cp) for Cuiaba."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    download = subparsers.add_parser("download", help="Download yearly cp ZIP archives from CDS.")
    download.add_argument("--start-year", type=int, default=DEFAULT_YEAR_START)
    download.add_argument("--end-year", type=int, default=DEFAULT_YEAR_END)
    download.add_argument("--output-dir", type=Path, default=DEFAULT_RAW_DIR)
    download.add_argument("--city", type=str, default=DEFAULT_CITY)
    download.add_argument("--sleep-seconds", type=int, default=5)
    download.add_argument("--dry-run", action="store_true")

    process = subparsers.add_parser("process", help="Process downloaded cp archives into a daily CSV.")
    process.add_argument("--start-year", type=int, default=DEFAULT_YEAR_START)
    process.add_argument("--end-year", type=int, default=DEFAULT_YEAR_END)
    process.add_argument("--input-dir", type=Path, default=DEFAULT_RAW_DIR)
    process.add_argument("--output-csv", type=Path, default=DEFAULT_CP_OUTPUT)
    process.add_argument("--city", type=str, default=DEFAULT_CITY)
    process.add_argument("--column-name", type=str, default=DEFAULT_COLUMN_NAME)

    merge = subparsers.add_parser("merge", help="Merge processed cp daily data into existing daily datasets.")
    merge.add_argument("--cp-csv", type=Path, default=DEFAULT_CP_OUTPUT)
    merge.add_argument("--column-name", type=str, default=DEFAULT_COLUMN_NAME)
    merge.add_argument(
        "--target",
        action="append",
        dest="targets",
        type=Path,
        help="Daily dataset to receive the cp column. Repeat the flag to merge into multiple files.",
    )
    merge.add_argument("--output-suffix", type=str, default="_with_cp")

    all_cmd = subparsers.add_parser("all", help="Run download, process and merge in sequence.")
    all_cmd.add_argument("--start-year", type=int, default=DEFAULT_YEAR_START)
    all_cmd.add_argument("--end-year", type=int, default=DEFAULT_YEAR_END)
    all_cmd.add_argument("--raw-dir", type=Path, default=DEFAULT_RAW_DIR)
    all_cmd.add_argument("--output-csv", type=Path, default=DEFAULT_CP_OUTPUT)
    all_cmd.add_argument("--city", type=str, default=DEFAULT_CITY)
    all_cmd.add_argument("--column-name", type=str, default=DEFAULT_COLUMN_NAME)
    all_cmd.add_argument("--sleep-seconds", type=int, default=5)
    all_cmd.add_argument("--dry-run-download", action="store_true")
    all_cmd.add_argument(
        "--target",
        action="append",
        dest="targets",
        type=Path,
        help="Daily dataset to receive the cp column. Repeat the flag to merge into multiple files.",
    )
    all_cmd.add_argument("--output-suffix", type=str, default="_with_cp")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "download":
        files = download_yearly_cp_archives(
            year_start=args.start_year,
            year_end=args.end_year,
            output_dir=args.output_dir,
            city=args.city,
            sleep_seconds=args.sleep_seconds,
            dry_run=args.dry_run,
        )
        print(f"Download step completed for {len(files)} file(s).")
        return 0

    if args.command == "process":
        df = process_cp_archives(
            input_dir=args.input_dir,
            output_csv=args.output_csv,
            year_start=args.start_year,
            year_end=args.end_year,
            city=args.city,
            column_name=args.column_name,
        )
        print(
            "Process step completed. "
            f"Rows: {len(df)}. Period: {df['date'].min().date()} to {df['date'].max().date()}."
        )
        return 0

    if args.command == "merge":
        pd = _require_pandas()
        cp_daily = pd.read_csv(args.cp_csv)
        outputs = merge_cp_with_daily_datasets(
            cp_daily=cp_daily,
            targets=args.targets,
            column_name=args.column_name,
            output_suffix=args.output_suffix,
        )
        print(f"Merge step completed for {len(outputs)} file(s).")
        return 0

    if args.command == "all":
        download_yearly_cp_archives(
            year_start=args.start_year,
            year_end=args.end_year,
            output_dir=args.raw_dir,
            city=args.city,
            sleep_seconds=args.sleep_seconds,
            dry_run=args.dry_run_download,
        )
        if args.dry_run_download:
            print("Dry-run download completed. No processing or merge was executed.")
            return 0

        cp_daily = process_cp_archives(
            input_dir=args.raw_dir,
            output_csv=args.output_csv,
            year_start=args.start_year,
            year_end=args.end_year,
            city=args.city,
            column_name=args.column_name,
        )
        outputs = merge_cp_with_daily_datasets(
            cp_daily=cp_daily,
            targets=args.targets,
            column_name=args.column_name,
            output_suffix=args.output_suffix,
        )
        print(
            "All steps completed. "
            f"Daily cp rows: {len(cp_daily)}. Merge outputs: {len(outputs)}."
        )
        return 0

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
