#!/usr/bin/env python3
"""Examples that call download_era5_daily_stats."""

from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from download_era5_daily import download_era5_daily_stats


def example_temperature_recent_years():
    """Download 2m temperature daily mean for recent years (2020-2023)."""
    print("Example 1: Downloading 2m temperature for 2020-2023\n")
    
    download_era5_daily_stats(
        variables=['2m_temperature'],
        year_start=2020,
        year_end=2023,
        daily_statistic='daily_mean',
        output_file='era5_temp_2020_2023.nc'
    )


def example_multiple_variables():
    """Download multiple variables for a single year."""
    print("\nExample 2: Downloading multiple variables for 2022\n")
    
    download_era5_daily_stats(
        variables=[
            '2m_temperature',
            'total_precipitation',
            '10m_u_component_of_wind',
            '10m_v_component_of_wind'
        ],
        year_start=2022,
        year_end=2022,
        daily_statistic='daily_mean',
        output_file='era5_multi_vars_2022.nc'
    )


def example_summer_months_max_temp():
    """Download maximum temperature for summer months."""
    print("\nExample 3: Downloading maximum temperature for summer months 2020-2023\n")
    
    download_era5_daily_stats(
        variables=['2m_temperature'],
        year_start=2020,
        year_end=2023,
        months=['06', '07', '08'],
        daily_statistic='daily_maximum',
        output_file='era5_temp_max_summer_2020_2023.nc'
    )


def example_regional_data():
    """Download data for a specific region (Europe)."""
    print("\nExample 4: Downloading temperature for Europe (2023)\n")
    
    # CDS area order is N, W, S, E.
    europe_area = [71, -25, 35, 40]
    
    download_era5_daily_stats(
        variables=['2m_temperature', 'total_precipitation'],
        year_start=2023,
        year_end=2023,
        area=europe_area,
        output_file='era5_europe_2023.nc'
    )


def example_historical_data():
    """Download historical data from 1940s."""
    print("\nExample 5: Downloading historical temperature data (1940-1945)\n")
    
    download_era5_daily_stats(
        variables=['2m_temperature'],
        year_start=1940,
        year_end=1945,
        daily_statistic='daily_mean',
        output_file='era5_temp_1940_1945.nc'
    )


def example_evapotranspiration_cuiaba():
    """Daily-mean fields for Penman-Monteith ET around Cuiaba (15.6°S, 56.1°W)."""
    print("\nExample 6: Downloading evapotranspiration variables for Cuiaba, Brazil\n")

    # CDS area order is N, W, S, E. Box is about 2° around 15.6°S, 56.1°W.
    cuiaba_area = [-13.6, -58.1, -17.6, -54.1]
    
    print("Region: Cuiaba, Mato Grosso, Brazil")
    print(f"Bounding box: {cuiaba_area} (N, W, S, E)")
    print("Variables: Temperature, humidity, wind, radiation, precipitation, evaporation")
    print("\nThese variables can be used to:")
    print("  - Calculate reference evapotranspiration (ET0) using Penman-Monteith")
    print("  - Analyze water balance (P - ET)")
    print("  - Study agricultural water requirements")
    print("  - Assess drought conditions")
    print("  - Validate crop water use models\n")
    
    download_era5_daily_stats(
        variables=[
            '2m_temperature',
            '2m_dewpoint_temperature',
            '10m_u_component_of_wind',
            '10m_v_component_of_wind',
            'surface_net_solar_radiation',
            'surface_pressure',
            'total_precipitation',
            'total_evaporation'
        ],
        year_start=2020,
        year_end=2023,
        area=cuiaba_area,
        daily_statistic='daily_mean',
        output_file='era5_evapotranspiration_cuiaba_2020_2023.nc'
    )


def main():
    print("ERA5 Daily Statistics Download Examples")
    print("=" * 50)
    print("\nIMPORTANT: Make sure you have:")
    print("1. Installed cdsapi: pip install -r requirements.txt")
    print("2. Copied config/cdsapirc.example to ~/.cdsapirc and added your CDS credentials")
    print("3. Accepted the terms and conditions at:")
    print("   https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics")
    print("\n" + "=" * 50 + "\n")
    
    print("\nNo example ran. Call one of the example functions from main() to download.")


if __name__ == '__main__':
    main()
