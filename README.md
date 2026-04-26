# ERA5 Data Download
[![DOI](https://zenodo.org/badge/1154868167.svg)](https://doi.org/10.5281/zenodo.18674894)

Unified script to download several ERA5 products using the Copernicus Climate Data Store (CDS) API, with a Markdown checklist tracking variables, download status, and processing status.

## Dataset Information

This repository provides tools to download data from these ERA5 products:
- `derived-era5-single-levels-daily-statistics`
- `reanalysis-era5-single-levels`
- `reanalysis-era5-land`
- `reanalysis-era5-pressure-levels`
- `reanalysis-era5-complete` for model levels through MARS-style requests

The operational variable inventory lives in [docs/era5_variable_checklist.md](docs/era5_variable_checklist.md).

## Prerequisites

### 1. Python Environment
- Python 3.6 or higher
- pip package manager

### 2. CDS API Account
Before using these scripts, you need to:

1. **Register** for a free account at the [Copernicus Climate Data Store](https://cds.climate.copernicus.eu/)
2. **Accept the terms and conditions** for each ERA5 product you plan to download in the CDS portal.
3. **Get your API credentials**:
   - Login to CDS
   - Go to https://cds.climate.copernicus.eu/how-to-api
   - Copy your UID and API key

### 3. Configure API Credentials

Create a file `~/.cdsapirc` (in your home directory) with your credentials:

```
url: https://cds.climate.copernicus.eu/api
key: UID:API-KEY
```

Replace `UID` with your user ID and `API-KEY` with your actual API key.

Alternatively, copy the example file and edit it:
```bash
cp .cdsapirc.example ~/.cdsapirc
# Edit ~/.cdsapirc with your credentials
```

## Installation

1. Clone this repository:
```bash
git clone https://github.com/brunomartinsmv/ear5-data-download.git
cd ear5-data-download
```

2. Install required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Command-Line Usage

The main script `download_era5_daily.py` provides one entrypoint with subcommands:

```bash
python3 download_era5_daily.py <preset> --start-year YEAR --end-year YEAR [OPTIONS]
```

Available presets:

- `daily-statistics`: daily statistics from `derived-era5-single-levels-daily-statistics`
- `single-levels`: hourly ERA5 single-level fields
- `land`: hourly ERA5-Land fields
- `pressure-levels`: hourly pressure-level fields
- `model-levels`: ERA5 model levels from `reanalysis-era5-complete`

Use `--dry-run` before real downloads. It prints the target files and the first CDS request without contacting CDS:

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

### Examples

#### Example 1: Download 2m temperature for recent years
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 2020 \
    --end-year 2023 \
    --output temp_2020_2023.nc
```

#### Example 2: Download multiple variables
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature total_precipitation 10m_u_component_of_wind \
    --start-year 2022 \
    --end-year 2022
```

#### Example 3: Download maximum temperature for summer months
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 2020 \
    --end-year 2023 \
    --months 06 07 08 \
    --statistic daily_maximum
```

#### Example 4: Download data for a specific region (Europe)
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature total_precipitation \
    --start-year 2023 \
    --end-year 2023 \
    --area 71 -25 35 40
```

#### Example 5: Download historical data from 1940s
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature \
    --start-year 1940 \
    --end-year 1945
```

#### Example 6: Download variables for evapotranspiration analysis (Cuiaba, Brazil)
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature 2m_dewpoint_temperature 10m_u_component_of_wind 10m_v_component_of_wind surface_net_solar_radiation surface_pressure total_precipitation total_evaporation \
    --start-year 2020 \
    --end-year 2023 \
    --area -13.6 -58.1 -17.6 -54.1 \
    --output era5_evapotranspiration_cuiaba_2020_2023.nc
```

This downloads all variables needed for evapotranspiration analysis using methods like Penman-Monteith or FAO-56.

#### Example 7: Dry-run hourly single-level data
```bash
python3 download_era5_daily.py single-levels \
    --start-year 2020 \
    --end-year 2020 \
    --area -15.0 -56.5 -16.5 -55.5 \
    --dry-run
```

#### Example 8: Dry-run model levels
```bash
python3 download_era5_daily.py model-levels \
    --start-year 2020 \
    --end-year 2020 \
    --start-month 1 \
    --end-month 1 \
    --dry-run
```

### Using the Python API

You can also use the download function directly in your Python scripts:

```python
from download_era5_daily import download_era5_daily_stats

# Download 2m temperature for 2020-2023
download_era5_daily_stats(
    variables=['2m_temperature'],
    year_start=2020,
    year_end=2023,
    daily_statistic='daily_mean',
    output_file='temperature_data.nc'
)
```

See `examples.py` for legacy daily-statistics API examples.

## Available Variables

Common variables include:
- `2m_temperature` - 2 metre temperature
- `total_precipitation` - Total precipitation
- `10m_u_component_of_wind` - 10 metre U wind component
- `10m_v_component_of_wind` - 10 metre V wind component
- `surface_pressure` - Surface pressure
- `mean_sea_level_pressure` - Mean sea level pressure
- `2m_dewpoint_temperature` - 2 metre dewpoint temperature
- `sea_surface_temperature` - Sea surface temperature

For the repository's operational variable checklist, see [docs/era5_variable_checklist.md](docs/era5_variable_checklist.md). For the complete official variable lists, check the relevant CDS dataset page.

### Variable Documentation

For detailed scientific documentation on each ERA5 variable, including physical descriptions, applications, units, and references, see:
- **[docs/variables_documentation/](docs/variables_documentation/)** - Comprehensive PhD-level documentation for all variables

Each variable is documented with:
- Scientific description and physical context
- Units and typical value ranges
- Applications in climate research
- Mathematical relationships and equations
- Quality considerations and limitations
- Key scientific references

### Evapotranspiration Analysis

For a detailed guide on downloading and analyzing evapotranspiration data, including variable descriptions and calculation methods, see:
- **[docs/EVAPOTRANSPIRATION_GUIDE.md](docs/EVAPOTRANSPIRATION_GUIDE.md)** - Comprehensive guide for ET analysis with Cuiaba example

## Output Format

Daily-statistics downloads are saved as NetCDF (`.nc`) by default. Hourly ERA5 product downloads are saved as ZIP files containing GRIB by default. These formats can be read with:
- Python: `xarray`, `netCDF4`, `pandas`
- R: `ncdf4`, `raster`
- MATLAB: built-in `ncread` function
- Other tools: CDO, NCO, Panoply

### Reading Downloaded Data with Python

```python
import xarray as xr

# Open the downloaded file
ds = xr.open_dataset('era5_daily_stats_2020_2023.nc')

# Explore the data
print(ds)

# Access a specific variable
temperature = ds['t2m']  # or the variable name in the file

# Plot the data (requires matplotlib)
temperature.isel(time=0).plot()
```

## Notes and Best Practices

1. **Download Size**: ERA5 data files can be very large. Start with small requests (e.g., one year, one variable) to test your setup.

2. **Processing Time**: The CDS API may queue your request. Large downloads can take considerable time to process on the server side.

3. **Rate Limits**: The CDS API has rate limits. Avoid making too many simultaneous requests.

4. **Storage**: Ensure you have sufficient disk space for the downloaded data.

5. **Data Usage**: Please cite the ERA5 dataset in any publications:
   > Hersbach, H., et al. (2020): ERA5 hourly data on single levels from 1940 to present. Copernicus Climate Change Service (C3S) Climate Data Store (CDS).

## Troubleshooting

### Authentication Error
- Verify your `~/.cdsapirc` file is correctly formatted
- Check that you've accepted the dataset terms and conditions
- Ensure your API key is valid

### Connection Timeout
- Check your internet connection
- The CDS servers may be experiencing high load; try again later

### Invalid Parameter Error
- Verify variable names are correct (check the dataset documentation)
- Ensure year range is valid (1940 onwards)
- Check that month format is correct (01-12)

## License

This repository contains scripts for downloading ERA5 data. The scripts themselves are provided as-is for use with the Copernicus Climate Data Store. Please refer to the [Copernicus License](https://cds.climate.copernicus.eu/disclaimer-privacy) for terms regarding the ERA5 data itself.

## Repository Structure

```
.
├── download_era5_daily.py         # Unified download script with preset subcommands
├── examples.py                    # Example usage scripts
├── requirements.txt               # Python dependencies
├── .cdsapirc.example             # Example API configuration file
├── docs/                         # Documentation
│   ├── era5_variable_checklist.md     # Operational variable/download checklist
│   ├── EVAPOTRANSPIRATION_GUIDE.md    # Guide for ET analysis
│   └── variables_documentation/       # Detailed variable docs
│       ├── README.md                  # Variables documentation index
│       ├── 2m_temperature.md          # Temperature documentation
│       ├── total_precipitation.md     # Precipitation documentation
│       └── ...                        # Other variable docs
└── README.md                     # This file
```

## Contributing

Contributions are welcome! Please feel free to submit issues or pull requests.

## Resources

- [CDS API Documentation](https://cds.climate.copernicus.eu/how-to-api)
- [ERA5 Daily Statistics Dataset](https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics)
- [ERA5 Documentation](https://confluence.ecmwf.int/display/CKB/ERA5)
- [cdsapi Python Package](https://pypi.org/project/cdsapi/)
