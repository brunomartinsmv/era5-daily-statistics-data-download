# Scripts

Auxiliary ERA5 download utilities that complement the main entrypoint in the
repository root.

## Files

- `download_era5_model_levels.py`: standalone MARS-style downloader for ERA5
  model-level fields used in profile-based analyses.
- `download_era5_temperature_regime_vars.py`: standalone downloader for
  temperature-regime variables from ERA5 single levels, ERA5-Land, and pressure
  levels.

## Usage

Run scripts from the repository root so generated relative paths stay inside
the project:

```bash
python3 scripts/download_era5_model_levels.py --start-year 2020 --end-year 2020 --start-month 1 --end-month 1 --dry-run
python3 scripts/download_era5_temperature_regime_vars.py --start-year 2020 --end-year 2020 --start-month 1 --end-month 1 --dry-run
```

Use `--dry-run` before real downloads to inspect target files and CDS request
parameters.
