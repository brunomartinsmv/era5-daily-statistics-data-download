#!/usr/bin/env bash

set -euo pipefail

PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON_BIN="${PYTHON_BIN:-}"
WITH_LATEX=0
SYSTEM_PACKAGES_INSTALLED=0
PACKAGE_MANAGER=""

usage() {
  cat <<'EOF'
Usage: scripts/setup_linux.sh [--with-latex] [--python-bin <python-binary>]

Installs the Linux dependencies needed by this repository:
- Python 3.11 virtual environment
- ecCodes system library for cfgrib/eccodes
- Python packages from requirements.txt
- Extra notebook packages used in the repo but missing from requirements.txt

Options:
  --with-latex            Also install LaTeX tools used to rebuild PDFs
  --python-bin <binary>   Python executable to use (default: auto-detect 3.11+)
  -h, --help              Show this help
EOF
}

log() {
  printf '[setup] %s\n' "$*"
}

need_cmd() {
  command -v "$1" >/dev/null 2>&1
}

run_as_root() {
  if [[ "${EUID}" -eq 0 ]]; then
    "$@"
  else
    sudo "$@"
  fi
}

detect_package_manager() {
  if need_cmd apt; then
    echo apt
    return
  fi
  if need_cmd apt-get; then
    echo apt
    return
  fi
  if need_cmd dnf; then
    echo dnf
    return
  fi
  if need_cmd pacman; then
    echo pacman
    return
  fi
  echo unsupported
}

install_system_packages() {
  local package_manager="$1"
  local -a packages=()
  local -a latex_packages=()

  if [[ "${SYSTEM_PACKAGES_INSTALLED}" -eq 1 ]]; then
    return
  fi

  case "${package_manager}" in
    apt)
      packages=(
        python3
        python3-venv
        python3-pip
        build-essential
        pkg-config
        libeccodes-dev
        libeccodes-tools
      )
      latex_packages=(
        texlive-latex-extra
        texlive-fonts-recommended
        texlive-bibtex-extra
        latexmk
      )
      if need_cmd apt-get; then
        run_as_root apt-get update
        run_as_root apt-get install -y "${packages[@]}"
      else
        run_as_root apt update
        run_as_root apt install -y "${packages[@]}"
      fi
      if [[ "${WITH_LATEX}" -eq 1 ]]; then
        if need_cmd apt-get; then
          run_as_root apt-get install -y "${latex_packages[@]}"
        else
          run_as_root apt install -y "${latex_packages[@]}"
        fi
      fi
      ;;
    dnf)
      packages=(
        python3
        python3-pip
        gcc
        gcc-c++
        make
        pkgconf-pkg-config
        eccodes
        eccodes-devel
      )
      latex_packages=(
        texlive-scheme-basic
        latexmk
      )
      run_as_root dnf install -y "${packages[@]}"
      if [[ "${WITH_LATEX}" -eq 1 ]]; then
        run_as_root dnf install -y "${latex_packages[@]}"
      fi
      ;;
    pacman)
      packages=(
        python
        python-pip
        base-devel
        pkgconf
        eccodes
      )
      latex_packages=(
        texlive-basic
        texlive-binextra
        texlive-latexextra
      )
      run_as_root pacman -Sy --noconfirm "${packages[@]}"
      if [[ "${WITH_LATEX}" -eq 1 ]]; then
        run_as_root pacman -Sy --noconfirm "${latex_packages[@]}"
      fi
      ;;
    *)
      log "No supported package manager detected. Skipping system package installation."
      return 0
      ;;
  esac

  SYSTEM_PACKAGES_INSTALLED=1
}

resolve_python_bin() {
  local candidate

  if [[ -n "${PYTHON_BIN}" ]] && need_cmd "${PYTHON_BIN}"; then
    echo "${PYTHON_BIN}"
    return
  fi

  for candidate in python3.11 python3 python; do
    if need_cmd "${candidate}"; then
      echo "${candidate}"
      return
    fi
  done

  echo ""
}

require_python_version() {
  local python_bin="$1"
  local version

  version="$("${python_bin}" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  if ! "${python_bin}" -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 11) else 1)'; then
    log "Python ${version} found at ${python_bin}, but this repo expects Python 3.11+."
    exit 1
  fi
}

ensure_python() {
  local resolved_python

  resolved_python="$(resolve_python_bin)"
  if [[ -n "${resolved_python}" ]]; then
    PYTHON_BIN="${resolved_python}"
    require_python_version "${PYTHON_BIN}"
    return
  fi

  log "Python 3.11+ not found. Installing system packages."
  install_system_packages "${PACKAGE_MANAGER}"

  resolved_python="$(resolve_python_bin)"
  if [[ -z "${resolved_python}" ]]; then
    log "A usable Python executable is still unavailable."
    exit 1
  fi

  PYTHON_BIN="${resolved_python}"
  require_python_version "${PYTHON_BIN}"
}

ensure_eccodes() {
  if need_cmd grib_ls || need_cmd codes_info; then
    return
  fi

  if [[ "${PACKAGE_MANAGER}" == "unsupported" ]]; then
    log "ecCodes tools are not available and no supported package manager was detected. Continuing with pip-based install only."
    return
  fi

  log "ecCodes tools not found. Installing system packages."
  install_system_packages "${PACKAGE_MANAGER}"
}

ensure_latex_tools() {
  if [[ "${WITH_LATEX}" -ne 1 ]]; then
    return
  fi

  if need_cmd pdflatex && need_cmd latexmk && need_cmd bibtex; then
    return
  fi

  if [[ "${PACKAGE_MANAGER}" == "unsupported" ]]; then
    log "LaTeX tools are not available and no supported package manager was detected."
    return
  fi

  log "LaTeX tools not found. Installing system packages."
  install_system_packages "${PACKAGE_MANAGER}"
}

create_venv() {
  if [[ ! -d "${VENV_DIR}" ]]; then
    log "Creating virtual environment at ${VENV_DIR}"
    if ! "${PYTHON_BIN}" -m venv "${VENV_DIR}"; then
      log "Failed to create the virtual environment."
      log "Your Python installation is missing venv/ensurepip support."
      log "On supported distros, install the system venv package and rerun the script."
      exit 1
    fi
  fi

  if [[ ! -x "${VENV_DIR}/bin/python" ]]; then
    log "Virtual environment exists but ${VENV_DIR}/bin/python is missing."
    exit 1
  fi
}

install_python_packages() {
  local python="${VENV_DIR}/bin/python"

  log "Upgrading pip tooling"
  "${python}" -m pip install --upgrade pip setuptools wheel

  log "Installing repository requirements"
  "${python}" -m pip install -r "${PROJECT_ROOT}/requirements.txt"

  log "Installing notebook and GRIB extras missing from requirements.txt"
  "${python}" -m pip install scipy statsmodels shap eccodes
}

print_next_steps() {
  cat <<EOF

Setup finished.

Activate the environment:
  source "${VENV_DIR}/bin/activate"

Optional but likely needed for ERA5 downloads:
  Create ~/.cdsapirc with your CDS API credentials.

Recommended smoke tests:
  "${VENV_DIR}/bin/python" -c "import xarray, cfgrib, eccodes, cdsapi"
  "${VENV_DIR}/bin/python" -m unittest discover tests
EOF
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --with-latex)
      WITH_LATEX=1
      shift
      ;;
    --python-bin)
      if [[ $# -lt 2 ]]; then
        usage
        exit 1
      fi
      PYTHON_BIN="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      printf 'Unknown option: %s\n\n' "$1" >&2
      usage
      exit 1
      ;;
  esac
done

log "Project root: ${PROJECT_ROOT}"
PACKAGE_MANAGER="$(detect_package_manager)"
ensure_python
ensure_eccodes
ensure_latex_tools
create_venv
install_python_packages
print_next_steps
