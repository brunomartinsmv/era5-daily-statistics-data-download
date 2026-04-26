# ERA5 Variable Download Checklist

This checklist is the human-facing inventory for the repository. The Python
script downloads ERA5 products; this file tracks what should be downloaded,
where it comes from, and whether the raw files still need processing.

Status values:

- Download: `baixado`, `pendente`, `parcial`, `nao necessario`
- Processing: `processado`, `precisa processar`, `somente bruto`, `nao se aplica`

## Daily Statistics

Dataset: `derived-era5-single-levels-daily-statistics`

| Variable | Product | Category | Temporal resolution | Spatial resolution | Download status | Processing status | Expected file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2m_temperature` | daily-statistics | temperature | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Common near-surface temperature variable. |
| `2m_dewpoint_temperature` | daily-statistics | water / humidity | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Water-vapor proxy for VPD and humidity. |
| `2m_relative_humidity` | daily-statistics | water / humidity | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Diagnostic humidity variable documented in this repo. |
| `total_column_water_vapor` | daily-statistics | water / humidity | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Spelling used by the daily-statistics product documentation. |
| `total_precipitation` | daily-statistics | water / precipitation | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Basic water-balance input. |
| `convective_precipitation` | daily-statistics | water / precipitation | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Already documented; hourly single-levels can also download it. |
| `snowfall` | daily-statistics | water / precipitation | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Liquid-water equivalent snowfall. |
| `total_evaporation` | daily-statistics | water / evaporation | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Surface moisture flux; useful for ET work. |
| `10m_u_component_of_wind` | daily-statistics | wind | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | U component at 10 m. |
| `10m_v_component_of_wind` | daily-statistics | wind | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | V component at 10 m. |
| `surface_pressure` | daily-statistics | pressure | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Needed for humidity and ET calculations. |
| `mean_sea_level_pressure` | daily-statistics | pressure | daily statistic from hourly data | ERA5 native grid | pendente | nao se aplica | `downloads/era5_daily_statistics_*.nc` | Synoptic pressure field. |

## Single Levels

Dataset: `reanalysis-era5-single-levels`

| Variable | Product | Category | Temporal resolution | Spatial resolution | Download status | Processing status | Expected file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `2m_temperature` | single-levels | temperature | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Hourly source for custom daily aggregation. |
| `2m_dewpoint_temperature` | single-levels | water / humidity | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Water-vapor input for VPD/RH. |
| `total_column_water_vapour` | single-levels | water / humidity | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | British spelling used by hourly ERA5. |
| `total_precipitation` | single-levels | water / precipitation | hourly accumulation | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Convert accumulated metres to mm when processing. |
| `convective_precipitation` | single-levels | water / precipitation | hourly accumulation | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Useful split from total precipitation. |
| `large_scale_precipitation` | single-levels | water / precipitation | hourly accumulation | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Complements convective precipitation. |
| `10m_u_component_of_wind` | single-levels | wind | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Can derive wind speed. |
| `10m_v_component_of_wind` | single-levels | wind | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Can derive wind speed. |
| `surface_pressure` | single-levels | pressure | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | Surface pressure at model orography. |
| `convective_available_potential_energy` | single-levels | convection | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | CAPE diagnostic. |
| `convective_inhibition` | single-levels | convection | hourly | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_single-levels_*.zip` | CIN diagnostic. |

## ERA5-Land

Dataset: `reanalysis-era5-land`

| Variable | Product | Category | Temporal resolution | Spatial resolution | Download status | Processing status | Expected file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `skin_temperature` | land | land temperature | hourly | ERA5-Land grid | pendente | precisa processar | `downloads/era5_land_*.zip` | Surface skin temperature. |
| `soil_temperature_level_1` | land | soil temperature | hourly | ERA5-Land grid | pendente | precisa processar | `downloads/era5_land_*.zip` | Upper soil layer. |
| `soil_temperature_level_2` | land | soil temperature | hourly | ERA5-Land grid | pendente | precisa processar | `downloads/era5_land_*.zip` | Second soil layer. |
| `volumetric_soil_water_layer_1` | land | water / soil moisture | hourly | ERA5-Land grid | pendente | precisa processar | `downloads/era5_land_*.zip` | Main missing water-soil block to expand later. |
| `volumetric_soil_water_layer_2` | land | water / soil moisture | hourly | ERA5-Land grid | pendente | precisa processar | `downloads/era5_land_*.zip` | Add deeper layers later if needed. |

## Pressure Levels

Dataset: `reanalysis-era5-pressure-levels`

| Variable | Product | Category | Temporal resolution | Spatial resolution | Download status | Processing status | Expected file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `temperature` | pressure-levels | temperature profile | hourly at selected pressure levels | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_pressure-levels_*.zip` | Defaults to 850, 700, and 500 hPa. |
| `specific_humidity` | pressure-levels | water / humidity profile | hourly at selected pressure levels | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_pressure-levels_*.zip` | Vertical moisture profile. |
| `geopotential` | pressure-levels | dynamic profile | hourly at selected pressure levels | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_pressure-levels_*.zip` | Can derive height fields. |
| `vertical_velocity` | pressure-levels | dynamic profile | hourly at selected pressure levels | 0.25 x 0.25 degrees by default area request | pendente | precisa processar | `downloads/era5_pressure-levels_*.zip` | Omega profile. |

## Model Levels

Dataset: `reanalysis-era5-complete`

| Variable | Product | Category | Temporal resolution | Spatial resolution | Download status | Processing status | Expected file | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `t` | model-levels | temperature profile | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 130. |
| `q` | model-levels | water / humidity profile | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 133. |
| `u` | model-levels | wind profile | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 131. |
| `v` | model-levels | wind profile | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 132. |
| `w` | model-levels | vertical motion profile | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 135. |
| `ciwc` | model-levels | water / cloud ice | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 247. |
| `cswc` | model-levels | water / snow | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 76. |
| `clwc` | model-levels | water / cloud liquid | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 246. |
| `crwc` | model-levels | water / rain | hourly analysis | requested grid, default 0.25/0.25 | pendente | somente bruto | `downloads/model_levels/era5_model_levels_*.grib` | MARS paramId 75. |

## Water Variable Coverage

Water/moisture variables already covered here include precipitation,
convective precipitation, large-scale precipitation, snowfall, evaporation,
dewpoint temperature, relative humidity, total-column water vapour/vapor,
specific humidity, volumetric soil water, and model-level cloud/rain/snow
water contents.

The least complete block is still soil water. If more prepared ERA5-Land water
variables become available, add them to the ERA5-Land section with one row per
variable.
