#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

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
            "product_type": ["reanalysis"],
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
            "product_type": ["reanalysis"],
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
            targets.append((year, MONTHS, output_dir / f"{prefix}_{year}.zip"))
            continue

        if chunk_mode == "month":
            start_month = month_start if year == year_start else 1
            end_month = month_end if year == year_end else 12
            for month in range(start_month, end_month + 1):
                month_str = f"{month:02d}"
                targets.append((year, [month_str], output_dir / f"{prefix}_{year}_{month_str}.zip"))
            continue

        raise ValueError(f"chunk_mode invalido: {chunk_mode}")

    return targets


def build_request(kind: str, year: int, months: list[str]) -> dict[str, object]:
    cfg = DATASETS[kind]
    request = dict(cfg["request"])
    request["year"] = [str(year)]
    request["month"] = months
    return request


def summarize_target_state(targets: list[tuple[int, list[str], Path]]) -> tuple[list[tuple[int, list[str], Path]], list[tuple[int, list[str], Path]]]:
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
) -> list[Path]:
    cfg = DATASETS[kind]
    targets = build_targets(kind, year_start, year_end, month_start, month_end, chunk_mode)
    existing_targets, missing_targets = summarize_target_state(targets)

    print("=" * 72)
    print(f"Preset: {kind}")
    print(f"Dataset CDS: {cfg['dataset']}")
    print(f"Saida: {cfg['output_dir']}")
    print(f"Fatiamento: {chunk_mode}")
    print(f"Ja existentes: {len(existing_targets)}")
    print(f"Faltantes: {len(missing_targets)}")
    print("Variaveis:")
    for variable in cfg["request"]["variable"]:
        print(f"  - {variable}")
    if "pressure_level" in cfg["request"]:
        print("Niveis de pressao:")
        for level in cfg["request"]["pressure_level"]:
            print(f"  - {level} hPa")

    if dry_run:
        print("Dry-run: arquivos faltantes que seriam gerados:")
        for year, months, target in missing_targets:
            month_label = months[0] if len(months) == 1 else "01-12"
            print(f"  [{year}][{month_label}] {target}")
        return [target for _, _, target in missing_targets]

    import cdsapi

    client = cdsapi.Client()
    generated: list[Path] = []
    failures: list[str] = []

    if not missing_targets:
        print(f"[{kind}] Nada para baixar. Todos os arquivos esperados ja existem.")
        return [target for _, _, target in existing_targets]

    last_index = len(missing_targets) - 1

    for index, (year, months, target) in enumerate(missing_targets):
        request = build_request(kind, year, months)
        month_label = months[0] if len(months) == 1 else "01-12"
        print(f"[{kind}][{year}][{month_label}] Baixando...")
        try:
            client.retrieve(cfg["dataset"], request).download(str(target))
            print(f"[{kind}][{year}][{month_label}] OK -> {target}")
            generated.append(target)
        except Exception as exc:
            failures.append(f"{kind}:{year}:{month_label}: {exc}")
            print(f"[{kind}][{year}][{month_label}] ERRO: {exc}")

        if index < last_index and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if failures:
        print("\nFalhas encontradas:")
        for failure in failures:
            print(f"  - {failure}")

    return generated


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa variaveis adicionais do ERA5/ERA5-Land para reavaliar a "
            "sensibilidade do regime de raios a temperatura em Cuiaba."
        )
    )
    parser.add_argument(
        "--preset",
        choices=["single-levels", "land", "pressure-levels", "all"],
        default="all",
        help=(
            "Grupo de variaveis a baixar. "
            "'single-levels' cobre skt/blh/fluxos/cp/lsp; "
            "'land' cobre temperatura e umidade do solo; "
            "'pressure-levels' cobre perfis 850/700/500 hPa para derivar indices."
        ),
    )
    parser.add_argument("--start-year", type=int, default=YEAR_START)
    parser.add_argument("--end-year", type=int, default=YEAR_END)
    parser.add_argument(
        "--start-month",
        type=int,
        default=1,
        help="Mes inicial para presets em fatiamento mensal.",
    )
    parser.add_argument(
        "--end-month",
        type=int,
        default=12,
        help="Mes final para presets em fatiamento mensal.",
    )
    parser.add_argument(
        "--chunk",
        choices=["auto", "year", "month"],
        default="auto",
        help=(
            "Estrategia de fatiamento da requisição. "
            "'auto' usa ano para single-levels e mes para land/pressure-levels."
        ),
    )
    parser.add_argument("--dry-run", action="store_true", help="Lista os arquivos sem baixar nada.")
    parser.add_argument(
        "--sleep-seconds",
        type=int,
        default=5,
        help="Intervalo entre downloads anuais para reduzir chance de erro no CDS.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if args.start_year > args.end_year:
        raise SystemExit("--start-year nao pode ser maior que --end-year")
    if not 1 <= args.start_month <= 12:
        raise SystemExit("--start-month deve estar entre 1 e 12")
    if not 1 <= args.end_month <= 12:
        raise SystemExit("--end-month deve estar entre 1 e 12")
    if args.start_year == args.end_year and args.start_month > args.end_month:
        raise SystemExit("No mesmo ano, --start-month nao pode ser maior que --end-month")

    presets = ["single-levels", "land", "pressure-levels"] if args.preset == "all" else [args.preset]

    print("=" * 72)
    print("Download de variaveis ERA5 para analise temperatura x regime de raios")
    print("=" * 72)
    print(f"Periodo: {args.start_year}-{args.end_year}")
    print(f"Recorte mensal: {args.start_month:02d}-{args.end_month:02d}")
    print(f"Area Cuiaba: {AREA_CUIABA}")
    print("Pre-requisitos:")
    print("  - ~/.cdsapirc configurado")
    print("  - pip install cdsapi")

    all_paths: list[Path] = []
    for preset in presets:
        chunk_mode = DATASETS[preset]["default_chunk"] if args.chunk == "auto" else args.chunk
        all_paths.extend(
            download_kind(
                kind=preset,
                year_start=args.start_year,
                year_end=args.end_year,
                month_start=args.start_month,
                month_end=args.end_month,
                chunk_mode=chunk_mode,
                dry_run=args.dry_run,
                sleep_seconds=args.sleep_seconds,
            )
        )

    print("\nResumo final:")
    print(f"  Presets executados: {', '.join(presets)}")
    print(f"  Arquivos alvo: {len(all_paths)}")
    if args.dry_run:
        print("  Modo: dry-run")
    else:
        print("  Download concluido")

    print("\nProxima etapa sugerida:")
    print("  1. Extrair os GRIBs/ZIPs")
    print("  2. Agregar diario/mensal conforme a variavel")
    print("  3. Reexecutar a analise com skt/solo/cp/blh e, separadamente, com indices derivados")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
