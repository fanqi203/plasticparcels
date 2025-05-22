# SCHISM to NEMO Regridding Workflow

## Overview

This workflow converts SCHISM unstructured grid output to NEMO-compatible format, allowing you to use PlasticParcels without code modifications.

## 🔄 **Regridding Strategy Benefits**

✅ **No code changes** - Use PlasticParcels as-is  
✅ **Proven reliability** - NEMO format is well-tested  
✅ **Better performance** - Regular grids are faster  
✅ **Easier debugging** - Standard format, standard tools  
✅ **Future-proof** - Works with PlasticParcels updates  

## 📋 **Required Tools**

### Python Packages
```bash
pip install xarray netcdf4 scipy pandas numpy
# or
conda install xarray netcdf4 scipy pandas numpy
```

### Optional (for advanced regridding)
```bash
pip install pyresample  # For sophisticated regridding
pip install xesmf       # For conservative regridding
```

## 🔧 **Step-by-Step Workflow**

### **Step 1: Analyze Your SCHISM Output**

```python
import xarray as xr

# Load SCHISM output
schism_data = xr.open_dataset('schout_2024050100.nc')
print("SCHISM variables:", list(schism_data.variables))
print("SCHISM dimensions:", dict(schism_data.dims))

# Load grid
grid_data = xr.open_dataset('hgrid.gr3')  # or appropriate grid file
print("Grid coordinates:", list(grid_data.variables))
```

### **Step 2: Set Up Regridding Parameters**

```python
from schism_to_nemo_regridder import SCHISMToNEMORegridder

# Initialize regridder
regridder = SCHISMToNEMORegridder(
    target_resolution=0.1,  # 0.1° ≈ 11km (adjust as needed)
    target_levels=50        # Number of vertical levels
)

# Load SCHISM grid
regridder.load_schism_grid('hgrid.gr3')

# Create target regular grid
regridder.create_target_grid(
    lon_bounds=(-80, -75),  # Your Atlantic region
    lat_bounds=(32, 36)     # Your Atlantic region
)
```

### **Step 3: Process Time Series**

```python
import glob
from datetime import datetime, timedelta

# Get all SCHISM output files
schism_files = sorted(glob.glob('schout_*.nc'))

for i, schism_file in enumerate(schism_files):
    print(f"Processing {schism_file} ({i+1}/{len(schism_files)})")
    
    # Load SCHISM data
    schism_data = xr.open_dataset(schism_file)
    
    # Extract date from filename
    date_str = schism_file.split('_')[1][:8]  # Adjust based on your naming
    formatted_date = f"{date_str[:4]}-{date_str[4:6]}-{date_str[6:8]}"
    
    # Regrid all variables
    regridded_data = {}
    for schism_var in ['hvel_x', 'hvel_y', 'vertical_velocity', 'temp', 'salt']:
        if schism_var in schism_data.variables:
            regridded_data[schism_var] = regridder.regrid_variable(
                schism_data, schism_var, time_index=0
            )
    
    # Save in NEMO format
    regridder.save_nemo_format(regridded_data, 'nemo_output/', formatted_date)
    
    schism_data.close()
```

### **Step 4: Create PlasticParcels Settings**

```python
import json

# Create settings file for regridded data
nemo_settings = {
    "use_3D": True,
    "allow_time_extrapolation": True,
    "verbose_delete": False,
    "use_mixing": False,
    "use_biofouling": False,
    "use_stokes": False,
    "use_wind": False,
    "ocean": {
        "modelname": "NEMO0083",  # Use NEMO format
        "directory": "nemo_output/",
        "filename_style": "",
        "ocean_mesh": "ocean_mesh_hgr.nc",
        "bathymetry_mesh": "bathymetry_mesh_zgr.nc",
        "variables": {
            "U": "vozocrtx",
            "V": "vomecrty",
            "W": "vovecrtz",
            "conservative_temperature": "votemper",
            "absolute_salinity": "vosaline"
        },
        "dimensions": {
            "U": {"lon": "glamf", "lat": "gphif", "depth": "deptht", "time": "time_counter"},
            "V": {"lon": "glamf", "lat": "gphif", "depth": "deptht", "time": "time_counter"},
            "W": {"lon": "glamf", "lat": "gphif", "depth": "deptht", "time": "time_counter"},
            "conservative_temperature": {"lon": "glamf", "lat": "gphif", "depth": "deptht", "time": "time_counter"},
            "absolute_salinity": {"lon": "glamf", "lat": "gphif", "depth": "deptht", "time": "time_counter"}
        },
        "indices": {},
        "bathymetry_variables": {"bathymetry": "mbathy"},
        "bathymetry_dimensions": {"lon": "nav_lon", "lat": "nav_lat"}
    }
}

# Save settings
with open('schism_regridded_settings.json', 'w') as f:
    json.dump(nemo_settings, f, indent=2)
```

### **Step 5: Run PlasticParcels Simulation**

```python
import plasticparcels as pp
from datetime import datetime, timedelta

# Load regridded data settings
settings = pp.utils.load_settings('schism_regridded_settings.json')

# Set up simulation
settings['simulation'] = {
    'startdate': datetime(2024, 5, 1, 1, 0, 0),
    'runtime': timedelta(days=1),
    'outputdt': timedelta(hours=1),
    'dt': timedelta(minutes=20),
}

# Your Atlantic location now works!
release_locations = {
    'lons': [-78.8],
    'lats': [33.5],
    'plastic_amount': [1.0]
}

# Create fieldset (now using regridded SCHISM data in NEMO format)
fieldset = pp.constructors.create_fieldset(settings)

# Create particles
pset = pp.constructors.create_particleset(fieldset, settings, release_locations)

# Run simulation
kernels = pp.constructors.create_kernel(fieldset)
pset.execute(kernels, runtime=settings['simulation']['runtime'], 
             dt=settings['simulation']['dt'])

print("Success! SCHISM data working with PlasticParcels!")
```

## ⚙️ **Advanced Regridding Options**

### **Conservative Regridding (Recommended for Mass Conservation)**

```python
import xesmf as xe

# Create conservative regridder
regridder_conservative = xe.Regridder(
    schism_grid, target_grid, 
    method='conservative',
    periodic=False
)

# Apply conservative regridding
regridded_conservative = regridder_conservative(schism_data)
```

### **High-Quality Interpolation**

```python
from pyresample import geometry, kd_tree

# Define source and target grids
source_def = geometry.SwathDefinition(lons=schism_lons, lats=schism_lats)
target_def = geometry.AreaDefinition(...)

# High-quality interpolation
regridded_hq = kd_tree.resample_nearest(
    source_def, schism_data, target_def, 
    radius_of_influence=50000,  # 50km
    fill_value=np.nan
)
```

## 🎯 **Quality Control**

### **Validation Checks**

```python
# Check mass conservation
original_total = np.nansum(schism_data.hvel_x.values)
regridded_total = np.nansum(regridded_data['hvel_x'])
conservation_error = abs(regridded_total - original_total) / original_total
print(f"Mass conservation error: {conservation_error:.2%}")

# Check spatial patterns
import matplotlib.pyplot as plt
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))
ax1.contourf(schism_lons, schism_lats, schism_data.hvel_x[0, 0, :])
ax1.set_title('Original SCHISM')
ax2.contourf(target_lon_2d, target_lat_2d, regridded_data['hvel_x'][0, :, :])
ax2.set_title('Regridded to NEMO format')
plt.show()
```

## 📊 **Performance Considerations**

- **Resolution trade-off**: Higher resolution = better accuracy but slower processing
- **Memory usage**: Process time steps individually for large datasets
- **Parallel processing**: Use dask for large time series
- **Storage**: Regridded data may be larger than original SCHISM output

## 🚀 **Benefits of This Approach**

1. **Immediate compatibility** with PlasticParcels
2. **No software maintenance** burden
3. **Standard workflow** for ocean model intercomparison
4. **Quality control** through visualization and validation
5. **Flexibility** to adjust resolution and domain as needed

This regridding strategy is much more practical than code modification and will get you running plastic simulations with SCHISM data quickly and reliably!
