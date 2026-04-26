# Evapotranspiration Analysis Guide

This guide explains how to use ERA5 data for evapotranspiration (ET) analysis, with a specific example for Cuiaba, Brazil.

## What is Evapotranspiration?

Evapotranspiration (ET) is the combined process of:
- **Evaporation**: Water movement from soil and water bodies to the atmosphere
- **Transpiration**: Water movement from plants to the atmosphere through stomata

ET is a critical component of:
- Water balance and hydrology studies
- Agricultural water management
- Drought monitoring and assessment
- Climate change impact studies
- Ecosystem water use analysis

## Variables Required for ET Analysis

To calculate reference evapotranspiration (ET₀) using standard methods like Penman-Monteith or FAO-56, you need:

### 1. Temperature Variables
- **`2m_temperature`**: Air temperature at 2 meters height
  - Drives evaporative demand
  - Used in vapor pressure calculations
  - Affects psychrometric constant

- **`2m_dewpoint_temperature`**: Dewpoint temperature at 2 meters
  - Used to calculate actual vapor pressure
  - Determines vapor pressure deficit (VPD = es - ea)
  - Critical for atmospheric moisture demand

### 2. Radiation Variables
- **`surface_net_solar_radiation`**: Net solar (shortwave) radiation
  - Primary energy source for evapotranspiration
  - Shortwave component of net radiation (Rn) in the FAO-56 Penman–Monteith equation
- **`surface_net_thermal_radiation`**: Net thermal (longwave) radiation
  - Longwave component of net radiation (Rn) in the FAO-56 Penman–Monteith equation
- **`net_radiation (Rn)`**: Computed as `surface_net_solar_radiation + surface_net_thermal_radiation`
  - Total net radiation (shortwave + longwave); key input for energy balance methods such as FAO-56 Penman–Monteith

### 3. Wind Variables
- **`10m_u_component_of_wind`**: East-west wind component
- **`10m_v_component_of_wind`**: North-south wind component
  - Combined to calculate wind speed: √(u² + v²)
  - Wind enhances vapor transport away from surface
  - Important for aerodynamic term in Penman-Monteith

### 4. Pressure Variables
- **`surface_pressure`**: Atmospheric pressure at surface
  - Used in psychrometric constant calculation
  - Affects saturation vapor pressure
  - Altitude correction factor

### 5. Water Balance Variables
- **`total_precipitation`**: Total precipitation
  - Input side of water balance (P - ET = ΔS + R)
  - Needed for soil moisture and water availability assessment

- **`total_evaporation`**: ERA5 model evaporation output
  - Direct model output for comparison
  - Includes soil evaporation and transpiration
  - Can be used to validate calculated ET

## Calculating Reference Evapotranspiration (ET₀)

### FAO-56 Penman-Monteith Equation

The FAO-56 Penman-Monteith equation is the standard method for calculating reference evapotranspiration:

```
ET₀ = (0.408 × Δ × (Rn - G) + γ × (900/(T+273)) × u₂ × (es - ea)) / (Δ + γ × (1 + 0.34 × u₂))
```

Where:
- ET₀ = reference evapotranspiration [mm day⁻¹]
- Rn = net radiation at crop surface [MJ m⁻² day⁻¹]
- G = soil heat flux density [MJ m⁻² day⁻¹] (often ≈ 0 for daily calculations)
- T = mean daily air temperature at 2 m height [°C]
- u₂ = wind speed at 2 m height [m s⁻¹]
- es = saturation vapor pressure [kPa]
- ea = actual vapor pressure [kPa]
- es - ea = vapor pressure deficit [kPa]
- Δ = slope of vapor pressure curve [kPa °C⁻¹]
- γ = psychrometric constant [kPa °C⁻¹]

### Key Calculations

**Wind Speed at 2m from 10m components:**
```python
import numpy as np

u10 = era5_data['10m_u_component_of_wind']
v10 = era5_data['10m_v_component_of_wind']
wind_speed_10m = np.sqrt(u10**2 + v10**2)

# Convert from 10m to 2m height using logarithmic profile
wind_speed_2m = wind_speed_10m * 4.87 / np.log(67.8 * 10 - 5.42)
```

**Saturation Vapor Pressure (es):**
```python
def calc_es(T):
    """Calculate saturation vapor pressure from temperature (°C)"""
    return 0.6108 * np.exp((17.27 * T) / (T + 237.3))
```

**Actual Vapor Pressure (ea) from Dewpoint:**
```python
def calc_ea(Tdew):
    """Calculate actual vapor pressure from dewpoint temperature (°C)"""
    return 0.6108 * np.exp((17.27 * Tdew) / (Tdew + 237.3))
```

**Slope of Vapor Pressure Curve (Δ):**
```python
def calc_delta(T):
    """Calculate slope of saturation vapor pressure curve (kPa/°C)"""
    return 4098 * calc_es(T) / (T + 237.3)**2
```

**Psychrometric Constant (γ):**
```python
def calc_gamma(P):
    """Calculate psychrometric constant from pressure (kPa)"""
    return 0.000665 * P
```

## Example: Cuiaba, Brazil

Cuiaba is the capital of Mato Grosso state in Brazil, located in the tropics with coordinates approximately 15.6°S, 56.1°W.

### Climate Characteristics
- **Climate Type**: Tropical savanna (Aw in Köppen classification)
- **Temperature**: Hot year-round, 24-27°C mean annual
- **Rainfall**: Distinct wet (October-April) and dry (May-September) seasons
- **ET Demand**: High, especially during dry season
- **Agriculture**: Important region for soybean, corn, and cattle

### Why ET Analysis is Important for Cuiaba

1. **Agricultural Water Management**
   - Cuiaba region is a major agricultural producer
   - Irrigation scheduling requires accurate ET estimates
   - Crop water requirements vary by season

2. **Drought Monitoring**
   - Dry season can be severe
   - High ET combined with low precipitation leads to water stress
   - ET/P ratio indicates aridity levels

3. **Water Resources**
   - Understanding water balance (P - ET)
   - River flow and reservoir management
   - Groundwater recharge estimation

4. **Climate Change Impacts**
   - Projected temperature increases will enhance ET demand
   - Changing precipitation patterns affect water availability
   - Adaptation strategies for agriculture

### Downloading Data for Cuiaba

Using the Python API:
```python
from download_era5_daily import download_era5_daily_stats

# Cuiaba region bounding box: [North, West, South, East]
cuiaba_area = [-13.6, -58.1, -17.6, -54.1]

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
```

Or using the command line:
```bash
python3 download_era5_daily.py daily-statistics \
    --variables 2m_temperature 2m_dewpoint_temperature \
                10m_u_component_of_wind 10m_v_component_of_wind \
                surface_net_solar_radiation surface_pressure \
                total_precipitation total_evaporation \
    --start-year 2020 \
    --end-year 2023 \
    --area -13.6 -58.1 -17.6 -54.1 \
    --output era5_evapotranspiration_cuiaba_2020_2023.nc
```

Or run the example directly:
```bash
python3 examples/daily_statistics_examples.py
# Then uncomment: example_evapotranspiration_cuiaba()
```

## Processing the Downloaded Data

### Example Python Code

```python
import xarray as xr
import numpy as np

# Load the downloaded data
ds = xr.open_dataset('era5_evapotranspiration_cuiaba_2020_2023.nc')

# Extract variables (variable names may differ in the file)
T2m = ds['t2m'] - 273.15  # Convert K to °C
Tdew = ds['d2m'] - 273.15  # Convert K to °C
u10 = ds['u10']
v10 = ds['v10']
Rn = ds['ssr'] / 1e6  # Convert daily J/m² to MJ/m²/day
P = ds['sp'] / 1000  # Convert Pa to kPa
precip = ds['tp'] * 1000  # Convert m to mm
et_era5 = -ds['e'] * 1000  # Convert m to mm (negative to positive)

# Calculate wind speed at 2m
wind_10m = np.sqrt(u10**2 + v10**2)
wind_2m = wind_10m * 4.87 / np.log(67.8 * 10 - 5.42)

# Calculate vapor pressures
es = 0.6108 * np.exp((17.27 * T2m) / (T2m + 237.3))
ea = 0.6108 * np.exp((17.27 * Tdew) / (Tdew + 237.3))
vpd = es - ea

# Calculate psychrometric parameters
delta = 4098 * es / (T2m + 237.3)**2
gamma = 0.000665 * P

# Calculate ET0 using Penman-Monteith
# (simplified, assuming G ≈ 0 for daily data)
numerator = 0.408 * delta * Rn + gamma * (900/(T2m+273)) * wind_2m * vpd
denominator = delta + gamma * (1 + 0.34 * wind_2m)
ET0 = numerator / denominator

# Add ET0 to dataset
ds['ET0'] = ET0
ds['ET0'].attrs['units'] = 'mm/day'
ds['ET0'].attrs['long_name'] = 'Reference Evapotranspiration (FAO-56 Penman-Monteith)'

# Calculate water balance
water_deficit = precip - ET0
ds['water_deficit'] = water_deficit
ds['water_deficit'].attrs['units'] = 'mm/day'
ds['water_deficit'].attrs['long_name'] = 'Precipitation minus ET0'

# Save processed data
ds.to_netcdf('cuiaba_processed_et_2020_2023.nc')

print(f"Mean annual ET0: {ET0.mean(['time', 'latitude', 'longitude']).values:.2f} mm/day")
print(f"Mean annual Precipitation: {precip.mean(['time', 'latitude', 'longitude']).values:.2f} mm/day")
print(f"Mean annual ERA5 ET: {et_era5.mean(['time', 'latitude', 'longitude']).values:.2f} mm/day")
```

### Seasonal Analysis

```python
# Group by season
wet_season = ds.sel(time=ds.time.dt.month.isin([10,11,12,1,2,3,4]))
dry_season = ds.sel(time=ds.time.dt.month.isin([5,6,7,8,9]))

print("\nSeasonal Statistics:")
print(f"Wet Season ET0: {wet_season.ET0.mean().values:.2f} mm/day")
print(f"Dry Season ET0: {dry_season.ET0.mean().values:.2f} mm/day")
print(f"Wet Season P: {wet_season.tp.mean().values * 1000:.2f} mm/day")
print(f"Dry Season P: {dry_season.tp.mean().values * 1000:.2f} mm/day")
```

## Applications

### 1. Irrigation Scheduling
- Calculate crop water requirements: ETc = Kc × ET0
- Determine irrigation amounts: I = ETc - Pe (effective precipitation)
- Optimize irrigation timing to avoid water stress

### 2. Drought Assessment
- Calculate Aridity Index: AI = P / ET0
- Monitor water deficit accumulation
- Identify drought onset and duration

### 3. Water Balance
- Estimate runoff: R ≈ P - ET - ΔS
- Assess groundwater recharge potential
- Evaluate water availability for different uses

### 4. Climate Change Impact
- Trend analysis of ET0 over time
- Changes in P/ET0 ratio
- Shifts in seasonal patterns

## References

1. **Allen, R. G., Pereira, L. S., Raes, D., & Smith, M. (1998).** 
   Crop evapotranspiration: Guidelines for computing crop water requirements. 
   FAO Irrigation and drainage paper 56. Rome: FAO.

2. **Hersbach, H., et al. (2020).** 
   The ERA5 global reanalysis. 
   Quarterly Journal of the Royal Meteorological Society, 146(730), 1999-2049.

3. **Penman, H. L. (1948).** 
   Natural evaporation from open water, bare soil and grass. 
   Proceedings of the Royal Society of London. Series A, 193(1032), 120-145.

4. **Monteith, J. L. (1965).** 
   Evaporation and environment. 
   Symposia of the Society for Experimental Biology, 19, 205-234.

## Additional Resources

- **FAO Irrigation and Drainage Paper 56**: http://www.fao.org/3/x0490e/x0490e00.htm
- **ERA5 Documentation**: https://confluence.ecmwf.int/display/CKB/ERA5
- **PyETo Python Package**: https://pyeto.readthedocs.io/ (for ET calculations)
- **RefET Python Package**: https://github.com/DRI-WSWUP/RefET (FAO-56 implementation)

## Notes

- ET0 represents potential evapotranspiration for a reference grass surface
- Actual ET depends on crop type (crop coefficient Kc), soil moisture, and vegetation health
- For specific crops, multiply ET0 by appropriate crop coefficients
- ERA5's total_evaporation includes both evaporation and transpiration from the land surface model
- Consider local calibration with measured data when possible
