#!/opt/homebrew/opt/python@3.11/bin/python3.11
from __future__ import annotations

from pathlib import Path
import zipfile

import cdsapi
import numpy as np
import pandas as pd
from eccodes import codes_get, codes_get_array, codes_grib_new_from_file, codes_release


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "era5_redownload_audit"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

AREA_CUIABA = [-15.0, -56.5, -16.5, -55.5]
VARIABLES = [
    "10m_u_component_of_wind",
    "10m_v_component_of_wind",
    "2m_dewpoint_temperature",
    "2m_temperature",
    "surface_pressure",
    "total_precipitation",
    "convective_available_potential_energy",
    "convective_inhibition",
    "total_column_water_vapour",
]
CRITICAL_PERIODS = [
    (2008, "07"),
    (2010, "08"),
    (2017, "07"),
    (2020, "08"),
    (2021, "07"),
]
TIMES = [f"{hour:02d}:00" for hour in range(24)]
DAYS = [f"{day:02d}" for day in range(1, 32)]


def download_period(client: cdsapi.Client, year: int, month: str) -> Path:
    zip_path = OUTPUT_DIR / f"era5_cuiaba_{year}_{month}_audit.zip"
    client.retrieve(
        "reanalysis-era5-single-levels",
        {
            "product_type": "reanalysis",
            "variable": VARIABLES,
            "year": str(year),
            "month": month,
            "day": DAYS,
            "time": TIMES,
            "area": AREA_CUIABA,
            "data_format": "grib",
            "download_format": "zip",
        },
        str(zip_path),
    )
    return zip_path


def extract_grib(zip_path: Path) -> Path:
    grib_path = zip_path.with_suffix(".grib")
    with zipfile.ZipFile(zip_path, "r") as archive:
        members = [name for name in archive.namelist() if name.endswith(".grib")]
        if not members:
            raise RuntimeError(f"Nenhum arquivo GRIB encontrado em {zip_path}")
        with archive.open(members[0]) as source, grib_path.open("wb") as target:
            target.write(source.read())
    return grib_path


def audit_cin_vs_supporting_fields(grib_path: Path) -> pd.DataFrame:
    rows: list[dict[str, object]] = []
    with grib_path.open("rb") as handle:
        while True:
            gid = codes_grib_new_from_file(handle)
            if gid is None:
                break
            try:
                short_name = codes_get(gid, "shortName")
                if short_name not in {"cin", "cape", "sp", "tcwv"}:
                    continue

                date = pd.to_datetime(str(codes_get(gid, "dataDate")), format="%Y%m%d")
                hour = int(codes_get(gid, "hour"))
                values = np.asarray(codes_get_array(gid, "values"), dtype=float)
                missing_value = float(codes_get(gid, "missingValue"))
                valid = np.isfinite(values) & (values != missing_value)

                rows.append(
                    {
                        "shortName": short_name,
                        "date": date.date().isoformat(),
                        "hour": hour,
                        "valid_points": int(valid.sum()),
                        "total_points": int(values.size),
                    }
                )
            finally:
                codes_release(gid)

    return pd.DataFrame(rows)


def summarize_audit(df: pd.DataFrame) -> None:
    print("\nResumo por variavel:")
    print(df.groupby("shortName")["valid_points"].agg(["count", "min", "max"]).to_string())

    cin = df[df["shortName"] == "cin"].copy()
    daily = cin.groupby("date")["valid_points"].sum().reset_index()
    fully_missing = daily[daily["valid_points"] == 0]

    print("\nCIN por dia:")
    print(daily.head(15).to_string(index=False))
    print(f"\nDias com CIN totalmente ausente: {len(fully_missing)}")
    if not fully_missing.empty:
        print(fully_missing.head(20).to_string(index=False))


def main() -> None:
    client = cdsapi.Client()

    for year, month in CRITICAL_PERIODS:
        print(f"\n=== Auditando {year}-{month} ===")
        zip_path = download_period(client, year, month)
        grib_path = extract_grib(zip_path)
        audit = audit_cin_vs_supporting_fields(grib_path)

        csv_path = OUTPUT_DIR / f"audit_{year}_{month}.csv"
        audit.to_csv(csv_path, index=False)

        print(f"ZIP:  {zip_path}")
        print(f"GRIB: {grib_path}")
        print(f"CSV:  {csv_path}")
        summarize_audit(audit)


if __name__ == "__main__":
    main()
