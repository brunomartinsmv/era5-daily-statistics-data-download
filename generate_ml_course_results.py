#!/usr/bin/env python3
"""Gera os artefatos reproduziveis do antigo trabalho de ML."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.modeling import generate_coursework_results, list_coursework_outputs
from src.modeling.coursework import DEFAULT_EVENT_DATA, DEFAULT_MONTHLY_DATA, DEFAULT_CITY


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Regenera figuras, tabelas e TXT do antigo trabalho de Machine Learning."
    )
    parser.add_argument("--city", default=DEFAULT_CITY, help="Nome curto da cidade usado no prefixo dos arquivos.")
    parser.add_argument("--monthly-data", default=DEFAULT_MONTHLY_DATA, type=Path, help="CSV mensal processado.")
    parser.add_argument("--event-data", default=DEFAULT_EVENT_DATA, type=Path, help="CSV de eventos de raios.")
    parser.add_argument(
        "--figures-dir",
        default=PROJECT_ROOT / "results" / "figures",
        type=Path,
        help="Diretorio de saida das figuras.",
    )
    parser.add_argument(
        "--tables-dir",
        default=PROJECT_ROOT / "results" / "tables",
        type=Path,
        help="Diretorio de saida das tabelas e arquivos TXT.",
    )
    parser.add_argument("--dry-run", action="store_true", help="Lista saidas sem executar modelos.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.dry_run:
        outputs = list_coursework_outputs(args.city)
        print("Figuras planejadas:")
        for path in outputs["figures"]:
            print(f"- {path}")
        print("Tabelas/TXT planejados:")
        for path in outputs["tables"]:
            print(f"- {path}")
        return

    metadata = generate_coursework_results(
        city=args.city,
        monthly_data=args.monthly_data,
        event_data=args.event_data,
        figures_dir=args.figures_dir,
        tables_dir=args.tables_dir,
    )
    print("Artefatos de ML gerados com sucesso.")
    print(f"Dados mensais: {metadata['monthly_data']}")
    print(f"Eventos de raios: {metadata['event_data']}")
    print(f"Figuras: {metadata['figures_dir']}")
    print(f"Tabelas/TXT: {metadata['tables_dir']}")


if __name__ == "__main__":
    main()
