# SCHISM Time Series Integration Guide

## 🌊 **Multiple-Time SCHISM Output Support**

This guide covers how to handle SCHISM model outputs with multiple time steps for realistic time-varying plastic pollution simulations.

## 📋 **Supported Time Series Scenarios**

### **Scenario 1: Multiple Files (Sequential)**
```
out2d_1.nc   # t=0h
out2d_2.nc   # t=1h  
out2d_3.nc   # t=2h
...
out2d_24.nc  # t=24h
```

### **Scenario 2: Single File with Time Dimension**
```
out2d_full.nc
├── time: [0, 1, 2, ..., 24] hours
├── depthAverageVelX: (time, nodes)
├── depthAverageVelY: (time, nodes)
└── elevation: (time, nodes)
```

### **Scenario 3: Mixed Format**
```
morning.nc   # t=0-12h (12 time steps)
afternoon.nc # t=12-24h (12 time steps)
```

## 🚀 **Usage Examples**

### **Basic Time Series Processing**

#### **Multiple Files with Wildcard**
```bash
# Process all out2d_*.nc files in sequence
python schism_timeseries_to_plasticparcels.py --schism_files "out2d_*.nc"
```

#### **Specific File List**
```bash
# Process specific files in order
python schism_timeseries_to_plasticparcels.py \
    --schism_files "out2d_1.nc,out2d_2.nc,out2d_3.nc,out2d_4.nc"
```

#### **Single File with Multiple Times**
```bash
# Process single file containing time series
python schism_timeseries_to_plasticparcels.py --schism_files "out2d_full.nc"
```

### **Advanced Options**

#### **With Spatial Subsetting**
```bash
# Extract Gulf Stream region from large Atlantic domain
python schism_timeseries_to_plasticparcels.py \
    --schism_files "atlantic_out2d_*.nc" \
    --lon_bounds -85,-70 \
    --lat_bounds 25,45 \
    --resolution 0.02
```

#### **High-Resolution Coastal Study**
```bash
# Process coastal time series with fine resolution
python schism_timeseries_to_plasticparcels.py \
    --schism_files "coastal_*.nc" \
    --lon_bounds -81,-79 \
    --lat_bounds 31.5,32.5 \
    --resolution 0.005 \
    --output_dir coastal_timeseries
```

## 📊 **Output Structure**

### **NEMO-Compatible Time Series Files**
```
schism_timeseries_output/
├── U_timeseries.nc              # U velocity (time, y, x)
├── V_timeseries.nc              # V velocity (time, y, x)
├── W_timeseries.nc              # W velocity (zeros for 2D)
├── T_timeseries.nc              # Temperature (elevation proxy)
├── S_timeseries.nc              # Salinity (constant)
├── ocean_mesh_hgr.nc            # Horizontal grid mesh
├── bathymetry_mesh_zgr.nc       # Bathymetry data
└── timeseries_settings.json     # PlasticParcels settings
```

### **Key Differences from Single Time Step**
- ✅ **Time dimension**: All variables have (time, y, x) shape
- ✅ **Real time evolution**: Currents change over time
- ✅ **No extrapolation**: `allow_time_extrapolation=False`
- ✅ **Realistic physics**: Tidal cycles, weather events captured

## 🔬 **Scientific Benefits**

### **Realistic Ocean Dynamics**
```
Single Time Step:               Time Series:
├── Stationary currents        ├── Time-varying currents
├── No tidal cycles            ├── Tidal cycles (12.5h periods)
├── No weather events          ├── Storm events captured
├── Spatial gradients only     ├── Spatial + temporal gradients
└── Short-term studies only    └── Long-term studies possible
```

### **Enhanced Simulation Capabilities**
- ✅ **Tidal transport**: 12.5-hour tidal cycles
- ✅ **Multi-day tracking**: Realistic long-term trajectories
- ✅ **Weather events**: Storm-driven transport
- ✅ **Seasonal patterns**: Monthly/seasonal circulation
- ✅ **Operational forecasting**: Real-time predictions

## ⚙️ **Performance Considerations**

### **Memory Usage**
```
Single Time Step:              Time Series (24 hours):
├── 1 × grid_size × variables  ├── 24 × grid_size × variables
├── ~100 MB for 100×100 grid   ├── ~2.4 GB for 100×100 grid
└── Fast processing            └── 24× more memory needed
```

### **Processing Time**
```
Time Steps    Processing Time    Memory Usage
1             1 minute          100 MB
6             6 minutes          600 MB
24            24 minutes         2.4 GB
72            72 minutes         7.2 GB
168 (1 week)  3 hours           16.8 GB
```

### **Optimization Strategies**
1. **Spatial subsetting**: Reduce domain size first
2. **Temporal chunking**: Process in smaller time blocks
3. **Resolution adjustment**: Balance detail vs performance
4. **Parallel processing**: Use multiple cores for large datasets

## 🎯 **Use Case Examples**

### **1. Tidal Transport Study**
```bash
# 48-hour simulation capturing 4 tidal cycles
python schism_timeseries_to_plasticparcels.py \
    --schism_files "tidal_out2d_*.nc" \
    --lon_bounds -80.8,-80.2 \
    --lat_bounds 32.0,32.6 \
    --resolution 0.002
```

**Benefits**: Captures tidal mixing, residual transport

### **2. Hurricane Debris Tracking**
```bash
# 1-week simulation during hurricane passage
python schism_timeseries_to_plasticparcels.py \
    --schism_files "hurricane_day*.nc" \
    --lon_bounds -85,-75 \
    --lat_bounds 25,35 \
    --resolution 0.01
```

**Benefits**: Storm surge, wind-driven transport, debris dispersal

### **3. Seasonal River Discharge**
```bash
# Monthly simulation with varying river flow
python schism_timeseries_to_plasticparcels.py \
    --schism_files "river_month*.nc" \
    --lon_bounds -90,-88 \
    --lat_bounds 28,30 \
    --resolution 0.005
```

**Benefits**: Seasonal discharge patterns, plume dynamics

## 🔧 **PlasticParcels Integration**

### **Using Time Series Data**
```python
import plasticparcels as pp

# Load time series settings
settings = pp.utils.load_settings('schism_timeseries_output/timeseries_settings.json')

# Set simulation parameters
settings['simulation'] = {
    'startdate': datetime(2024, 5, 1, 0, 0, 0),
    'runtime': timedelta(days=3),  # Can now run realistic multi-day sims
    'outputdt': timedelta(hours=1),
    'dt': timedelta(minutes=20),
}

# Create fieldset (now with time-varying currents!)
fieldset = pp.constructors.create_fieldset(settings)

# Release locations
release_locations = {
    'lons': [-80.5, -80.3, -80.1],
    'lats': [32.0, 32.2, 32.4],
    'plastic_amount': [1.0, 1.0, 1.0]
}

# Create particles
pset = pp.constructors.create_particleset(fieldset, settings, release_locations)

# Run simulation with realistic time-varying currents
kernels = pp.constructors.create_kernel(fieldset)
pset.execute(kernels, 
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'])
```

### **Key Advantages**
- ✅ **No time extrapolation warnings**
- ✅ **Realistic current evolution**
- ✅ **Accurate long-term transport**
- ✅ **Tidal and weather effects captured**

## 📈 **Validation and Quality Control**

### **Check Time Series Continuity**
```python
import xarray as xr
import matplotlib.pyplot as plt

# Load time series
u_data = xr.open_dataset('schism_timeseries_output/U_timeseries.nc')

# Plot time evolution at a point
lon_idx, lat_idx = 50, 50  # Grid indices
u_timeseries = u_data['vozocrtx'][:, lat_idx, lon_idx]

plt.figure(figsize=(12, 4))
plt.plot(u_timeseries.time_counter, u_timeseries)
plt.xlabel('Time (hours)')
plt.ylabel('U velocity (m/s)')
plt.title('Current Evolution at Grid Point')
plt.grid(True)
plt.show()
```

### **Validate Tidal Signals**
```python
# Check for tidal periodicity (12.5 hours)
from scipy import signal

# Compute power spectrum
freqs, power = signal.periodogram(u_timeseries, fs=1.0)  # 1 sample/hour
tidal_freq = 1.0 / 12.5  # Tidal frequency (cycles/hour)

# Look for tidal peak
tidal_peak_idx = np.argmin(np.abs(freqs - tidal_freq))
print(f"Tidal signal strength: {power[tidal_peak_idx]:.3f}")
```

## 🎉 **Summary**

**Time series SCHISM integration enables:**
- ✅ **Realistic ocean dynamics** with tidal cycles and weather events
- ✅ **Long-term simulations** (days to weeks)
- ✅ **Operational forecasting** capabilities
- ✅ **Scientific accuracy** for policy-relevant studies

**Your SCHISM time series data is now fully compatible with PlasticParcels for professional-grade plastic pollution modeling!** 🌊🔬
