#!/usr/bin/env python3
from __future__ import annotations

import argparse
import calendar
import json
import sys
import time
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]

DATASET = "reanalysis-era5-complete"
YEAR_START = 2005
YEAR_END = 2023
AREA_CUIABA = [-15.0, -56.5, -16.5, -55.5]  # N, W, S, E
GRID_025 = "0.25/0.25"
DEFAULT_LEVELIST = "64/to/137"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "data" / "raw" / "era5" / "model_levels_ehrensperger"
DEFAULT_PREFIX = "era5_cuiaba_model_levels_ehrensperger"

# ERA5 Table 12 model-level parameter IDs used by the Ehrensperger et al. setup.
PARAMS_BY_SHORT_NAME = {
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
DEFAULT_PARAM_SHORT_NAMES = ["t", "q", "u", "v", "w", "ciwc", "cswc", "clwc", "crwc"]


@dataclass(frozen=True)
class RequestTarget:
    year: int
    month: int
    day: int | None
    date_range: str
    path: Path

    @property
    def label(self) -> str:
        if self.day is None:
            return f"{self.year}-{self.month:02d}"
        return f"{self.year}-{self.month:02d}-{self.day:02d}"


def _month_range_for_year(
    year: int,
    year_start: int,
    year_end: int,
    month_start: int,
    month_end: int,
) -> range:
    start = month_start if year == year_start else 1
    end = month_end if year == year_end else 12
    return range(start, end + 1)


def _month_date_range(year: int, month: int) -> str:
    last_day = calendar.monthrange(year, month)[1]
    return f"{year}-{month:02d}-01/to/{year}-{month:02d}-{last_day:02d}"


def _day_date_range(year: int, month: int, day: int) -> str:
    return f"{year}-{month:02d}-{day:02d}"


def _target_suffix(year: int, month: int, day: int | None, data_format: str) -> str:
    extension = "nc" if data_format == "netcdf" else "grib"
    if day is None:
        return f"{year}_{month:02d}.{extension}"
    return f"{year}_{month:02d}_{day:02d}.{extension}"


def build_targets(
    year_start: int,
    year_end: int,
    month_start: int,
    month_end: int,
    chunk_mode: str,
    output_dir: Path,
    prefix: str,
    data_format: str,
) -> list[RequestTarget]:
    targets: list[RequestTarget] = []

    for year in range(year_start, year_end + 1):
        for month in _month_range_for_year(year, year_start, year_end, month_start, month_end):
            if chunk_mode == "month":
                suffix = _target_suffix(year, month, day=None, data_format=data_format)
                targets.append(
                    RequestTarget(
                        year=year,
                        month=month,
                        day=None,
                        date_range=_month_date_range(year, month),
                        path=output_dir / f"{prefix}_{suffix}",
                    )
                )
                continue

            if chunk_mode == "day":
                last_day = calendar.monthrange(year, month)[1]
                for day in range(1, last_day + 1):
                    suffix = _target_suffix(year, month, day=day, data_format=data_format)
                    targets.append(
                        RequestTarget(
                            year=year,
                            month=month,
                            day=day,
                            date_range=_day_date_range(year, month, day),
                            path=output_dir / f"{prefix}_{suffix}",
                        )
                    )
                continue

            raise ValueError(f"chunk_mode invalido: {chunk_mode}")

    return targets


def summarize_target_state(targets: list[RequestTarget]) -> tuple[list[RequestTarget], list[RequestTarget]]:
    existing = []
    missing = []
    for target in targets:
        if target.path.exists():
            existing.append(target)
        else:
            missing.append(target)
    return existing, missing


def _area_to_mars_string(area: list[float]) -> str:
    return "/".join(f"{value:g}" for value in area)


def _param_ids(short_names: list[str]) -> str:
    unknown = [name for name in short_names if name not in PARAMS_BY_SHORT_NAME]
    if unknown:
        raise ValueError(f"Variaveis desconhecidas: {', '.join(unknown)}")
    return "/".join(PARAMS_BY_SHORT_NAME[name] for name in short_names)


def build_request(
    target: RequestTarget,
    param_short_names: list[str],
    levelist: str,
    area: list[float],
    grid: str,
    data_format: str,
) -> dict[str, object]:
    return {
        "class": "ea",
        "expver": "1",
        "stream": "oper",
        "type": "an",
        "levtype": "ml",
        "levelist": levelist,
        "param": _param_ids(param_short_names),
        "date": target.date_range,
        "time": "00:00:00/to/23:00:00/by/1",
        "area": _area_to_mars_string(area),
        "grid": grid,
        "format": data_format,
    }


def download_targets(
    targets: list[RequestTarget],
    param_short_names: list[str],
    levelist: str,
    area: list[float],
    grid: str,
    data_format: str,
    dry_run: bool,
    overwrite: bool,
    sleep_seconds: int,
) -> list[Path]:
    existing_targets, missing_targets = summarize_target_state(targets)
    targets_to_download = targets if overwrite else missing_targets

    print("=" * 72)
    print("Download ERA5 model levels para Cuiaba")
    print("=" * 72)
    print(f"Dataset CDS/MARS: {DATASET}")
    print(f"Periodo alvo: {targets[0].label} a {targets[-1].label}" if targets else "Periodo alvo: vazio")
    print(f"Arquivos esperados: {len(targets)}")
    print(f"Ja existentes: {len(existing_targets)}")
    print(f"Faltantes: {len(missing_targets)}")
    print(f"Modo sobrescrever: {'sim' if overwrite else 'nao'}")
    print(f"Area N/W/S/E: {_area_to_mars_string(area)}")
    print(f"Grade solicitada: {grid}")
    print(f"Niveis de modelo: {levelist}")
    print(f"Formato: {data_format}")
    print("Variaveis solicitadas:")
    for short_name in param_short_names:
        print(f"  - {short_name}: paramId {PARAMS_BY_SHORT_NAME[short_name]}")

    if dry_run:
        print("\nDry-run: nenhuma chamada ao CDS sera feita.")
        print("Arquivos que seriam baixados:")
        for target in targets_to_download:
            print(f"  [{target.label}] {target.path}")
        if targets_to_download:
            example = build_request(
                target=targets_to_download[0],
                param_short_names=param_short_names,
                levelist=levelist,
                area=area,
                grid=grid,
                data_format=data_format,
            )
            print("\nExemplo da primeira requisicao:")
            print(json.dumps(example, indent=2, ensure_ascii=False))
        return [target.path for target in targets_to_download]

    if not targets_to_download:
        print("\nNada para baixar. Todos os arquivos esperados ja existem.")
        return [target.path for target in existing_targets]

    try:
        import cdsapi
    except Exception as exc:
        raise RuntimeError(
            "cdsapi e necessario para baixar ERA5. Instale e configure ~/.cdsapirc."
        ) from exc

    targets[0].path.parent.mkdir(parents=True, exist_ok=True)
    client = cdsapi.Client()
    generated: list[Path] = []
    failures: list[str] = []
    last_index = len(targets_to_download) - 1

    for index, target in enumerate(targets_to_download):
        request = build_request(
            target=target,
            param_short_names=param_short_names,
            levelist=levelist,
            area=area,
            grid=grid,
            data_format=data_format,
        )
        print(f"[{target.label}] Baixando -> {target.path}")
        try:
            client.retrieve(DATASET, request).download(str(target.path))
            print(f"[{target.label}] OK")
            generated.append(target.path)
        except Exception as exc:  # pragma: no cover - depende do CDS/rede
            failures.append(f"{target.label}: {exc}")
            print(f"[{target.label}] ERRO: {exc}")

        if index < last_index and sleep_seconds > 0:
            time.sleep(sleep_seconds)

    if failures:
        print("\nFalhas encontradas:")
        for failure in failures:
            print(f"  - {failure}")
        raise RuntimeError("Um ou mais downloads falharam. Veja a lista acima.")

    return generated


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Baixa dados ERA5 em model levels para variaveis usadas no desenho "
            "de Ehrensperger et al., com fatiamento mensal por padrao."
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
        help="Fatiamento da requisicao. Use 'day' se o mensal exceder limite/custo do CDS.",
    )
    parser.add_argument(
        "--variables",
        nargs="+",
        choices=sorted(PARAMS_BY_SHORT_NAME),
        default=DEFAULT_PARAM_SHORT_NAMES,
        help="Short names ERA5 model-level a baixar.",
    )
    parser.add_argument(
        "--levelist",
        default=DEFAULT_LEVELIST,
        help="Niveis de modelo em sintaxe MARS, por exemplo '64/to/137'.",
    )
    parser.add_argument(
        "--area",
        nargs=4,
        type=float,
        default=AREA_CUIABA,
        metavar=("N", "W", "S", "E"),
        help="Area em ordem MARS/CDS: Norte Oeste Sul Leste.",
    )
    parser.add_argument("--grid", default=GRID_025, help="Grade regular solicitada, ex.: '0.25/0.25'.")
    parser.add_argument(
        "--format",
        choices=["grib", "netcdf"],
        default="grib",
        help="Formato de saida solicitado ao CDS/MARS.",
    )
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--prefix", default=DEFAULT_PREFIX)
    parser.add_argument("--dry-run", action="store_true", help="Lista requisicoes sem baixar nada.")
    parser.add_argument("--overwrite", action="store_true", help="Baixa novamente mesmo se o arquivo existir.")
    parser.add_argument("--sleep-seconds", type=int, default=10, help="Pausa entre requisicoes.")
    return parser.parse_args(argv)


def validate_args(args: argparse.Namespace) -> None:
    if args.start_year > args.end_year:
        raise SystemExit("--start-year nao pode ser maior que --end-year")
    if not 1 <= args.start_month <= 12:
        raise SystemExit("--start-month deve estar entre 1 e 12")
    if not 1 <= args.end_month <= 12:
        raise SystemExit("--end-month deve estar entre 1 e 12")
    if args.start_year == args.end_year and args.start_month > args.end_month:
        raise SystemExit("No mesmo ano, --start-month nao pode ser maior que --end-month")
    if len(args.area) != 4:
        raise SystemExit("--area deve ter quatro valores: N W S E")
    if args.area[0] < args.area[2]:
        raise SystemExit("--area invalida: Norte deve ser maior ou igual ao Sul")
    if args.area[1] > args.area[3]:
        raise SystemExit("--area invalida: Oeste deve ser menor ou igual ao Leste")
    if args.sleep_seconds < 0:
        raise SystemExit("--sleep-seconds nao pode ser negativo")


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    validate_args(args)

    targets = build_targets(
        year_start=args.start_year,
        year_end=args.end_year,
        month_start=args.start_month,
        month_end=args.end_month,
        chunk_mode=args.chunk,
        output_dir=args.output_dir,
        prefix=args.prefix,
        data_format=args.format,
    )
    if not targets:
        raise SystemExit("Nenhum alvo de download foi gerado.")

    paths = download_targets(
        targets=targets,
        param_short_names=args.variables,
        levelist=args.levelist,
        area=args.area,
        grid=args.grid,
        data_format=args.format,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
        sleep_seconds=args.sleep_seconds,
    )

    print("\nResumo final:")
    print(f"  Arquivos alvo: {len(paths)}")
    print(f"  Modo: {'dry-run' if args.dry_run else 'download'}")
    print("\nProxima etapa sugerida:")
    print("  1. Conferir a ordem temporal dos GRIBs baixados.")
    print("  2. Extrair medias/maximos por dia e por mes para cada variavel e nivel.")
    print("  3. Derivar diagnosticos de fase mista, cisalhamento, umidade e gelo.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
