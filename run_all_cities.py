#!/usr/bin/env python3
"""Fail-fast guard for the multi-city pipeline entrypoint."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = ROOT_DIR / "cities_config.yaml"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Valida a presença da implementação/configuração do pipeline "
            "multi-cidades antes da execução."
        )
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Caminho para o arquivo de configuração YAML das cidades.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    problems: list[str] = [
        (
            "scripts/run_all_cities.py estava vazio no repositório atual; "
            "executá-lo como no-op silencioso tornava o fluxo multi-cidades "
            "não confiável."
        )
    ]

    config_path = args.config.resolve()
    if not config_path.exists():
        problems.append(f"Arquivo de configuração ausente: {config_path}")
    elif config_path.stat().st_size == 0:
        problems.append(f"Arquivo de configuração vazio: {config_path}")

    details = "\n".join(f"- {problem}" for problem in problems)
    parser.exit(
        1,
        "Falha de confiabilidade detectada no entrypoint multi-cidades.\n"
        f"{details}\n",
    )


if __name__ == "__main__":
    sys.exit(main())
