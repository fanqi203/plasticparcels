# PlasticParcels Data Download Guide

## Overview

PlasticParcels includes built-in download capabilities for some datasets, but for global simulations you need to download oceanographic data from external sources.

## Built-in Download Capabilities ✅

### PlasticParcels Release Data (Automatic)
The package automatically downloads plastic release data:

```python
import plasticparcels as pp
settings = pp.utils.download_plasticparcels_dataset('NEMO0083', settings, 'input_data')
```

**Downloads:**
- `coastal_population_MPW_NEMO0083.csv` - Coastal plastic emissions
- `river_emissions_NEMO0083.csv` - River plastic emissions  
- `agg_data_fisheries_info_NEMO0083.csv` - Fisheries plastic data
- `global_concentrations_NEMO0083.csv` - Global plastic concentrations
- `land_current_NEMO0083.nc` - Unbeaching current data

**Source:** https://plasticadrift.science.uu.nl/plasticparcels/NEMO0083/

## Required External Data (Manual Download) 📥

For global simulations, you need oceanographic data from **Copernicus Marine Service**:

### 1. Hydrodynamic Data (Essential)
**Dataset:** MOI GLO12 (psy4v3r1)
- **Variables:** U/V/W velocities, Temperature, Salinity
- **Resolution:** 1/12° (~8km)
- **URL:** https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_PHY_001_030

### 2. Biogeochemical Data (For biofouling)
**Dataset:** MOI BIO4 (biomer4v2r1)  
- **Variables:** Nutrients, Phytoplankton, Oxygen
- **Resolution:** 1/4° (~25km)
- **URL:** https://data.marine.copernicus.eu/product/GLOBAL_MULTIYEAR_BGC_001_029

### 3. Wave Data (For Stokes drift)
**Dataset:** ECMWF ERA5 Wave
- **Variables:** Stokes drift components, wave periods
- **Resolution:** 0.5° (~50km)
- **URL:** https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels

### 4. Wind Data (For wind drift)
**Dataset:** ECMWF ERA5 Wind
- **Variables:** 10m U/V wind components
- **Resolution:** 0.25° (~25km)  
- **URL:** https://cds.climate.copernicus.eu/cdsapp#!/dataset/reanalysis-era5-single-levels

## Current Test Data Coverage 🧪

The included test data covers:
- **Region:** Mediterranean Sea (33-37°N, 16-21°E)
- **Time:** 2020-01-01 to 2020-01-06
- **Variables:** U/V/W, T/S, bathymetry, mixing coefficients
- **Size:** ~2 MB total

## Data Requirements by Location

### Your Original Request: 33.5°N, 78.8°W (Atlantic Ocean)
**Status:** ❌ Not covered by test data
**Required:** Download Copernicus Marine Service data for Atlantic region
**Alternative:** Use test data in Mediterranean (35°N, 18°E)

### Mediterranean Sea: 33-37°N, 16-21°E  
**Status:** ✅ Covered by test data
**Required:** Nothing (already included)

### Global Simulations
**Status:** ❌ Requires external data download
**Required:** Full Copernicus Marine Service datasets

## Download Instructions

### Option 1: Use Test Data (Recommended for Learning)
```bash
# Already included - no download needed
python run_plastic_simulation.py \
    --start "2020-01-04 00:00:00" \
    --end "2020-01-05 12:00:00" \
    --lat 35.0 \
    --lon 18.0
```

### Option 2: Download Global Data (For Production)

1. **Register for Copernicus Marine Service**
   - Create account at: https://data.marine.copernicus.eu/
   - Install copernicusmarine client: `pip install copernicusmarine`

2. **Download Hydrodynamic Data**
   ```bash
   copernicusmarine subset \
     --dataset-id cmems_mod_glo_phy_my_0.083_P1D-m \
     --variable uo --variable vo --variable wo --variable thetao --variable so \
     --start-datetime 2024-05-01 --end-datetime 2024-05-02 \
     --minimum-longitude -80 --maximum-longitude -77 \
     --minimum-latitude 32 --maximum-latitude 35 \
     --output-filename atlantic_hydrodynamic.nc
   ```

3. **Update Settings File**
   ```json
   {
     "ocean": {
       "directory": "/path/to/downloaded/data/",
       "filename_style": "atlantic_hydrodynamic.nc"
     }
   }
   ```

### Option 3: Use CDS API for Wind/Wave Data

1. **Install CDS API**
   ```bash
   pip install cdsapi
   ```

2. **Download Wind Data**
   ```python
   import cdsapi
   c = cdsapi.Client()
   c.retrieve('reanalysis-era5-single-levels', {
       'product_type': 'reanalysis',
       'variable': ['10m_u_component_of_wind', '10m_v_component_of_wind'],
       'year': '2024',
       'month': '05',
       'day': ['01', '02'],
       'time': ['00:00', '06:00', '12:00', '18:00'],
       'area': [35, -80, 32, -77],  # North, West, South, East
       'format': 'netcdf',
   }, 'wind_data.nc')
   ```

## File Structure

```
plasticparcels/
├── tests/test_data/           # Test data (Mediterranean)
│   ├── test_U_2020-01-04.nc  # Zonal velocity
│   ├── test_V_2020-01-04.nc  # Meridional velocity  
│   ├── test_W_2020-01-04.nc  # Vertical velocity
│   ├── test_T_2020-01-04.nc  # Temperature
│   ├── test_S_2020-01-04.nc  # Salinity
│   └── ...
├── input_data/NEMO0083/       # Downloaded release data
│   ├── coastal_population_MPW_NEMO0083.csv
│   ├── river_emissions_NEMO0083.csv
│   └── ...
└── your_data/                 # Your downloaded data
    ├── hydrodynamic/
    ├── biogeochemical/
    ├── wave/
    └── wind/
```

## Quick Start Recommendations

1. **Learning/Testing:** Use included test data in Mediterranean
2. **Research:** Download specific regional data from Copernicus
3. **Global Studies:** Download full global datasets (large!)

## Data Sizes

- **Test data:** ~2 MB (included)
- **Regional data:** ~100 MB - 1 GB per month
- **Global data:** ~10-100 GB per month (depending on resolution)

## Support

- **PlasticParcels docs:** https://plastic.oceanparcels.org/
- **Copernicus Marine:** https://help.marine.copernicus.eu/
- **CDS API:** https://cds.climate.copernicus.eu/api-how-to
