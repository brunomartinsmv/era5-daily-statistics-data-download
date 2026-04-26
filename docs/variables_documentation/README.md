# ERA5 Daily Statistics Variables Documentation

This directory contains comprehensive PhD-level documentation for each variable available in the ERA5 post-processed daily statistics dataset on single levels.

## Overview

Each variable is documented in a separate markdown file with detailed scientific descriptions, applications, units, and references. The documentation is designed to provide researchers with the context needed to properly understand and use these climate variables.

## Variable Categories

### Atmospheric Variables - Temperature and Humidity
- **[2m_temperature.md](2m_temperature.md)** - Air temperature at 2 metres above surface
- **[2m_dewpoint_temperature.md](2m_dewpoint_temperature.md)** - Dewpoint temperature at 2 metres
- **[2m_relative_humidity.md](2m_relative_humidity.md)** - Relative humidity at 2 metres
- **[total_column_water_vapor.md](total_column_water_vapor.md)** - Integrated atmospheric moisture (precipitable water)

### Atmospheric Variables - Wind
- **[10m_u_component_of_wind.md](10m_u_component_of_wind.md)** - Zonal (east-west) wind at 10 metres
- **[10m_v_component_of_wind.md](10m_v_component_of_wind.md)** - Meridional (north-south) wind at 10 metres
- **[10m_wind_speed.md](10m_wind_speed.md)** - Wind speed magnitude at 10 metres
- **[100m_u_component_of_wind.md](100m_u_component_of_wind.md)** - Zonal wind at 100 metres (hub height)
- **[100m_v_component_of_wind.md](100m_v_component_of_wind.md)** - Meridional wind at 100 metres

### Atmospheric Variables - Pressure
- **[surface_pressure.md](surface_pressure.md)** - Atmospheric pressure at surface elevation
- **[mean_sea_level_pressure.md](mean_sea_level_pressure.md)** - Pressure reduced to sea level

### Precipitation and Moisture
- **[total_precipitation.md](total_precipitation.md)** - Total liquid and frozen precipitation
- **[convective_precipitation.md](convective_precipitation.md)** - Precipitation from parameterized convection
- **[snowfall.md](snowfall.md)** - Solid precipitation (water equivalent)
- **[total_evaporation.md](total_evaporation.md)** - Surface to atmosphere moisture flux

### Ocean and Cryosphere
- **[sea_surface_temperature.md](sea_surface_temperature.md)** - Ocean surface temperature
- **[sea_ice_area_fraction.md](sea_ice_area_fraction.md)** - Sea ice concentration (0-1)
- **[sea_ice_thickness.md](sea_ice_thickness.md)** - Mean sea ice thickness

### Radiation - Solar/Shortwave
- **[surface_net_solar_radiation.md](surface_net_solar_radiation.md)** - Net shortwave radiation at surface
- **[surface_solar_radiation_downwards.md](surface_solar_radiation_downwards.md)** - Incoming solar radiation
- **[mean_surface_downward_short_wave_radiation_flux.md](mean_surface_downward_short_wave_radiation_flux.md)** - Downward solar flux (alternative name)

### Radiation - Thermal/Longwave
- **[surface_net_thermal_radiation.md](surface_net_thermal_radiation.md)** - Net longwave radiation at surface
- **[mean_surface_downward_long_wave_radiation_flux.md](mean_surface_downward_long_wave_radiation_flux.md)** - Downward thermal radiation from atmosphere

### Cloud Cover
- **[total_cloud_cover.md](total_cloud_cover.md)** - Total cloud fraction (all levels)
- **[low_cloud_cover.md](low_cloud_cover.md)** - Low-level cloud fraction (< 2 km)
- **[medium_cloud_cover.md](medium_cloud_cover.md)** - Mid-level cloud fraction (2-6 km)
- **[high_cloud_cover.md](high_cloud_cover.md)** - High-level cloud fraction (> 6 km)

## Documentation Structure

Each variable documentation file includes:

1. **Overview**: Brief description of the variable
2. **Scientific Description**: Detailed physical and mathematical description
3. **Units**: Standard and alternative units with typical value ranges
4. **Applications in Climate Research**: Key uses and applications
5. **Related Variables**: Connections to other variables
6. **Mathematical Relationships**: Relevant equations and formulas
7. **Data Characteristics**: Temporal/spatial resolution, availability
8. **Quality Considerations**: Known limitations and caveats
9. **Physical Context**: Underlying physics and processes
10. **Practical Interpretation**: Guidelines for using the data
11. **References**: Key scientific publications

## Dataset Information

- **Dataset**: ERA5 post-processed daily statistics on single levels
- **Dataset ID**: `derived-era5-single-levels-daily-statistics`
- **Provider**: Copernicus Climate Data Store (CDS)
- **Temporal Coverage**: 1940 to present
- **Spatial Resolution**: ~0.25° × 0.25° (approximately 25-30 km)
- **Temporal Resolution**: Daily statistics (mean, minimum, maximum, spread)

## Using This Documentation

This documentation is designed for:
- **Researchers**: Understanding variable characteristics and appropriate usage
- **Students**: Learning about climate variables and reanalysis data
- **Developers**: Implementing applications using ERA5 data
- **Operational Users**: Accessing reference information for specific variables

## Accessing ERA5 Data

To download these variables, use the scripts in the main repository:

```bash
python3 download_era5_daily.py daily-statistics --variables VARIABLE_NAME --start-year YYYY --end-year YYYY
```

See the main [README.md](../../README.md) for complete usage instructions.

## Additional Resources

- **CDS Dataset Page**: https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics
- **ERA5 Documentation**: https://confluence.ecmwf.int/display/CKB/ERA5
- **CDS API Guide**: https://cds.climate.copernicus.eu/how-to-api

## Contributing

If you find errors or have suggestions for improving the documentation, please open an issue or submit a pull request.

## Citation

When using ERA5 data in publications, please cite:

> Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz‐Sabater, J., ... & Thépaut, J. N. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049. https://doi.org/10.1002/qj.3803

## License

This documentation is provided for educational and research purposes. The ERA5 data itself is subject to the Copernicus License. See https://cds.climate.copernicus.eu/disclaimer-privacy for details.

---

*Last Updated: 2026-02-10*
