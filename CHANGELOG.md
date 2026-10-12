# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

This file is the single source of truth for release notes. GitHub Releases should
include a short summary and link here rather than duplicating the full changelog.

## [Unreleased]

## [2.1.0] - 2026-10-12

### Added

- Standard Python packaging via `pyproject.toml` with console script entrypoint `era5-download`
- GitHub Actions CI workflow in `.github/workflows/ci.yml` running unit tests on Python 3.9 through 3.13, packaging verification, and installed CLI smoke tests
- Atomic downloads using `<target>.<pid>_<uuid>.part` staging files, renamed into place only after the CDS transfer finishes
- Exclusive `<target>.lock` files so two runs cannot write the same destination at the same time
- Comprehensive unit tests covering atomic downloads, request-specific output filenames, destination locking, and month validation

### Changed

- Made `daily-statistics` default output filenames deterministic from the CDS request: years, statistic, variables, the explicit month list, frequency, time zone, area, and a short hash of the full request
- Included the month span in year-chunk hourly filenames when that year is not complete (for example `era5_single-levels_2020_11-12.zip`)
- Refactored `scripts/download_era5_temperature_regime_vars.py` to reuse `DownloadTarget` and `retrieve_targets` from the core module
- Allowed multi-year queries across seasonal month boundaries (e.g., `--start-month 11 --end-month 2`) in `_validate_months`
- Pinned `actions/checkout@v4` in `.github/workflows/pullfrog.yml` for stability and broad runner compatibility

### Fixed

- Default daily-statistics paths no longer collide when month lists differ only by which months are selected, or when frequency, time zone, or any other request field changes. An existing NetCDF is reused only for the same canonical request
- Concurrent downloads of one destination wait on a lock and, unless `--overwrite` is set, leave a file that appeared in the meantime untouched
- Cancelling a download removes the partial `.part` file and releases the destination lock
- Added `*.part` staging files and `*.lock` files to `.gitignore`
- Accurately track generated files in `scripts/download_era5_temperature_regime_vars.py` so failed downloads with `--overwrite` do not report pre-existing files as generated

## [2.0.0] - 2026-07-12

### Added

- Unified CLI with presets: `daily-statistics`, `single-levels`, `land`, `pressure-levels`, and `model-levels`
- `docs/era5_variable_checklist.md` as the operational variable inventory
- `AGENTS.md` with Cursor Cloud development instructions
- MIT LICENSE
- Unittest suite in `tests/` (9 tests, no CDS credentials required)
- `--dry-run` support across the main script and auxiliary utilities in `scripts/`
- `--overwrite` flag and validation for negative `--sleep-seconds`
- Configurable `--output-prefix` for model-level downloads
- `config/cdsapirc.example` credentials template (moved from repository root)
- DOI badge in README
- Auxiliary download scripts in `scripts/` for model levels and temperature-regime variables

### Changed

- Refactored `download_era5_daily.py` as the single entrypoint for all ERA5 download presets
- Refactored the model-levels script to reuse shared download logic from the main module
- Moved examples to `examples/` and credentials template to `config/`
- Rewrote README in English with updated usage for the unified CLI
- Updated Python requirement to 3.9+ (matches source typing)
- Translated variable checklist and auxiliary scripts to English
- Documented CDS vapor/vapour naming convention in README and checklist

### Fixed

- Omit `area` from hourly CDS requests when not set (avoids null values in API calls)
- Expose `overwrite` and `sleep_seconds` in `download_era5_daily_stats()` API
- Return exit code 1 from the temperature-regime script on download failures
- Respect `--start-month`/`--end-month` in year-chunk mode
- Fix `month_label` in the download loop to match dry-run output
- Normalize `product_type` to string format for CDS consistency

### Removed

- Standalone download scripts replaced by the unified CLI (`download_convective_precipitation.py`, `era5_pipeline.py`, and others)
- Local automation scripts unrelated to ERA5 downloads
- Portuguese content from repository documentation
- `setup_linux.sh` and `setup_linux.md`

## [1.0.0] - 2026-02-10

### Added

- ERA5 daily statistics download from the Copernicus Climate Data Store (1940–present)
- Command-line interface with support for multiple variables, temporal filtering, and spatial filtering
- Comprehensive variable documentation for 27+ meteorological variables in `docs/variables_documentation/`
- Example scripts and evapotranspiration analysis guide
- Documentation organized under `docs/` with navigation README

[Unreleased]: https://github.com/brunomartinsmv/era5-daily-statistics-data-download/compare/v2.1.0...HEAD
[2.1.0]: https://github.com/brunomartinsmv/era5-daily-statistics-data-download/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/brunomartinsmv/era5-daily-statistics-data-download/compare/v1.0.0...v2.0.0
[1.0.0]: https://github.com/brunomartinsmv/era5-daily-statistics-data-download/releases/tag/v1.0.0
