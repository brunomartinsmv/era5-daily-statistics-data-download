# ERA5 Data Download

[![DOI](https://zenodo.org/badge/1154868167.svg)](https://doi.org/10.5281/zenodo.18674894)

Tools to download ERA5 data from the Copernicus Climate Data Store (CDS) API.
The main entrypoint supports daily statistics, hourly single levels, ERA5-Land,
pressure levels, and ERA5 model levels. The operational variable inventory lives
in [docs/era5_variable_checklist.md](docs/era5_variable_checklist.md).

## Datasets

This repository supports requests for:

- `derived-era5-single-levels-daily-statistics`
- `reanalysis-era5-single-levels`
- `reanalysis-era5-land`
- `reanalysis-era5-pressure-levels`
- `reanalysis-era5-complete` for model levels through MARS-style requests

## Prerequisites

- Python 3.6 or higher
- `pip`
- A CDS account with accepted terms for each ERA5 product you plan to download
- A configured `~/.cdsapirc` credentials file

Create `~/.cdsapirc` from the repository template:

```bash
cp config/cdsapirc.example ~/.cdsapirc
```

Then edit `~/.cdsapirc` with your CDS UID and API key:

```text
url: https://cds.climate.copernicus.eu/api
key: UID:API-KEY
```

## Installation

```bash
git clone https://github.com/brunomartinsmv/era5-daily-statistics-data-download.git
cd era5-daily-statistics-data-download
pip install -r requirements.txt
```

## Usage

The main script is [download_era5_daily.py](download_era5_daily.py):

```bash
python3 download_era5_daily.py <preset> --start-year YEAR --end-year YEAR [OPTIONS]
```

Available presets:

- `daily-statistics`: daily statistics from `derived-era5-single-levels-daily-statistics`
- `single-levels`: hourly ERA5 single-level fields
- `land`: hourly ERA5-Land fields
- `pressure-levels`: hourly pressure-level fields
- `model-levels`: ERA5 model levels from `reanalysis-era5-complete`

Use `--dry-run` before real downloads. It prints target files and the first CDS
request without contacting CDS:

```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 2020 \
    --end-year 2020 \
    --dry-run
```

Common options:

- `--variables`: override the preset variable list
- `--area`: bounding box as `N W S E`
- `--output-dir`: output directory for generated files
- `--overwrite`: download even when the target file already exists
- `--sleep-seconds`: pause between requests

## Examples

Download 2 m temperature for recent years:

```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 2020 \
    --end-year 2023 \
    --output temp_2020_2023.nc
```

Download multiple variables:

```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature total_precipitation 10m_u_component_of_wind \
    --start-year 2022 \
    --end-year 2022
```

Download maximum temperature for selected months:

```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 2020 \
    --end-year 2023 \
    --months 06 07 08 \
    --statistic daily_maximum
```

Dry-run hourly single-level data:

```bash
python3 download_era5_daily.py single-levels \
    --start-year 2020 \
    --end-year 2020 \
    --area -15.0 -56.5 -16.5 -55.5 \
    --dry-run
```

Dry-run model levels:

```bash
python3 download_era5_daily.py model-levels \
    --start-year 2020 \
    --end-year 2020 \
    --start-month 1 \
    --end-month 1 \
    --dry-run
```

Additional runnable examples live in [examples/](examples/).

## Python API

```python
from download_era5_daily import download_era5_daily_stats

download_era5_daily_stats(
    variables=["2m_temperature"],
    year_start=2020,
    year_end=2023,
    daily_statistic="daily_mean",
    output_file="temperature_data.nc",
)
```

See [examples/daily_statistics_examples.py](examples/daily_statistics_examples.py)
for legacy daily-statistics API examples.

## Auxiliary Scripts

The [scripts/](scripts/) directory contains specialized ERA5 utilities that are
kept separate from the main public entrypoint:

```bash
python3 scripts/download_era5_model_levels.py --start-year 2020 --end-year 2020 --start-month 1 --end-month 1 --dry-run
python3 scripts/download_era5_temperature_regime_vars.py --start-year 2020 --end-year 2020 --start-month 1 --end-month 1 --dry-run
```

## Documentation

- [docs/era5_variable_checklist.md](docs/era5_variable_checklist.md): operational variable checklist
- [docs/EVAPOTRANSPIRATION_GUIDE.md](docs/EVAPOTRANSPIRATION_GUIDE.md): evapotranspiration guide
- [docs/variables_documentation/](docs/variables_documentation/): scientific notes for ERA5 variables
- [config/](config/): configuration templates

## Output Format

Daily-statistics downloads are saved as NetCDF (`.nc`) by default. Hourly ERA5
product downloads are saved as ZIP files containing GRIB by default. These
formats can be read with:

- Python: `xarray`, `netCDF4`, `pandas`
- R: `ncdf4`, `raster`
- MATLAB: built-in `ncread`
- Other tools: CDO, NCO, Panoply

## Notes and Best Practices

1. Start with small requests, such as one year and one variable.
2. The CDS API may queue large requests for a long time.
3. Avoid many simultaneous requests because CDS applies rate limits.
4. Check local disk space before downloading large ERA5 products.
5. Cite ERA5 data in publications:
   Hersbach, H., et al. (2020). ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS).

## Troubleshooting

### Authentication Error

- Verify that `~/.cdsapirc` is correctly formatted.
- Check that you accepted the dataset terms and conditions.
- Confirm that your API key is valid.

### Connection Timeout

- Check your internet connection.
- CDS servers may be under high load; try again later.

### Invalid Parameter Error

- Verify variable names against the dataset documentation.
- Ensure the year range is valid.
- Check month formatting for `01` through `12`.

## Repository Structure

```text
.
├── config/                       # Local configuration templates
│   ├── README.md
│   └── cdsapirc.example
├── docs/                         # Project and scientific documentation
│   ├── README.md
│   ├── EVAPOTRANSPIRATION_GUIDE.md
│   ├── era5_variable_checklist.md
│   └── variables_documentation/
├── examples/                     # Runnable usage examples
│   ├── README.md
│   └── daily_statistics_examples.py
├── scripts/                      # Auxiliary ERA5 download utilities
│   ├── README.md
│   ├── download_era5_model_levels.py
│   └── download_era5_temperature_regime_vars.py
├── download_era5_daily.py         # Main public entrypoint
├── requirements.txt
└── README.md
```

## License

This repository contains scripts for downloading ERA5 data. The scripts are
provided as-is for use with the Copernicus Climate Data Store. See the
[Copernicus License](https://cds.climate.copernicus.eu/disclaimer-privacy) for
terms regarding ERA5 data.

## Resources

- [CDS API Documentation](https://cds.climate.copernicus.eu/how-to-api)
- [ERA5 Daily Statistics Dataset](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics)
- [ERA5 Documentation](https://confluence.ecmwf.int/display/CKB/ERA5)
- [cdsapi Python Package](https://pypi.org/project/cdsapi/)
