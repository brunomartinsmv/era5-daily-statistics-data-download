# Documentation

This directory contains comprehensive documentation for the ERA5 Daily Statistics Data Download repository.

## Contents

### [era5_variable_checklist.md](era5_variable_checklist.md)

Operational checklist for ERA5 downloads:
- one row per variable
- ERA5 product and category
- temporal and spatial resolution
- download status
- processing status
- expected output file pattern
- short notes for water, soil, profile, and model-level variables

### [EVAPOTRANSPIRATION_GUIDE.md](EVAPOTRANSPIRATION_GUIDE.md)

Complete guide for evapotranspiration (ET) analysis using ERA5 data:
- What is evapotranspiration and why it matters
- Required variables for ET calculations
- FAO-56 Penman-Monteith equation implementation
- Case study: Cuiaba, Brazil
- Python code examples for processing ET data
- Seasonal analysis techniques
- Applications: irrigation scheduling, drought assessment, water balance
- References and additional resources

Perfect for:
- Agricultural water management
- Hydrological studies
- Climate impact assessments
- Ecosystem water use analysis

### [variables_documentation/](variables_documentation/)

PhD-level scientific documentation for each ERA5 variable:
- **28 variables** documented in detail
- Temperature and humidity variables
- Wind components (10m and 100m height)
- Pressure variables (surface and mean sea level)
- Precipitation types (total, convective, snowfall)
- Evaporation and water vapor
- Radiation variables (solar, thermal, net)
- Cloud cover (total, low, medium, high)
- Ocean variables (SST, sea ice)

Each variable includes:
- **Scientific Description**: Physical and mathematical basis
- **Units**: Standard units and typical value ranges
- **Applications**: Research and operational uses
- **Mathematical Relationships**: Key equations and formulas
- **Related Variables**: Connections to other parameters
- **Quality Considerations**: Limitations and caveats
- **References**: Key scientific publications

See [variables_documentation/README.md](variables_documentation/README.md) for the complete index.

## Quick Start

1. **New to ERA5 data?** Start with the main [README.md](../README.md) for installation and basic usage
2. **Planning downloads?** Use [era5_variable_checklist.md](era5_variable_checklist.md)
3. **Need ET analysis?** Go to [EVAPOTRANSPIRATION_GUIDE.md](EVAPOTRANSPIRATION_GUIDE.md)
4. **Want to understand a specific variable?** Browse [variables_documentation/](variables_documentation/)
5. **Looking for examples?** Check out [../examples.py](../examples.py) in the root directory

## Using the Documentation

### For Researchers
- Understand the scientific basis of each variable
- Learn appropriate applications and limitations
- Find relevant citations for your publications
- Discover relationships between variables

### For Students
- Learn about climate reanalysis data
- Understand meteorological variables
- See practical applications of climate science
- Study calculation methods (e.g., ET, wind speed)

### For Developers
- Implement data processing pipelines
- Validate your calculations against ERA5
- Understand data formats and units
- Build climate applications

### For Operational Users
- Quick reference for variable characteristics
- Typical value ranges for validation
- Best practices for using ERA5 data
- Decision support for specific applications

## Dataset Information

- **Products**: ERA5 daily statistics, hourly single levels, ERA5-Land, pressure levels, and model levels
- **Primary daily-statistics dataset ID**: `derived-era5-single-levels-daily-statistics`
- **Provider**: Copernicus Climate Data Store (CDS)
- **Temporal Coverage**: 1940 to present
- **Spatial Resolution**: ~0.25° × 0.25° (approximately 25-30 km)
- **Temporal Resolution**: Daily statistics (mean, minimum, maximum, spread)
- **URL**: https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics

## Additional Resources

- **CDS Dataset Page**: https://cds.climate.copernicus.eu/datasets/derived-era5-single-levels-daily-statistics
- **ERA5 Documentation**: https://confluence.ecmwf.int/display/CKB/ERA5
- **CDS API Guide**: https://cds.climate.copernicus.eu/how-to-api
- **FAO Irrigation Paper 56**: http://www.fao.org/3/x0490e/x0490e00.htm
- **PyETo Package**: https://pyeto.readthedocs.io/

## Citation

When using ERA5 data in publications, please cite:

> Hersbach, H., Bell, B., Berrisford, P., Hirahara, S., Horányi, A., Muñoz‐Sabater, J., ... & Thépaut, J. N. (2020). The ERA5 global reanalysis. *Quarterly Journal of the Royal Meteorological Society*, 146(730), 1999-2049. https://doi.org/10.1002/qj.3803

## Contributing

Found an error or have suggestions for improving the documentation? Please open an issue or submit a pull request on the [GitHub repository](https://github.com/brunomartinsmv/ear5-daily-statistics-data-download).

---

*Last Updated: 2026-04-25*
