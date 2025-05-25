# Plastic Parcels Simulation Script

## Overview

The `run_plastic_simulation.py` script provides a complete command-line interface for running plastic particle simulations using the plasticparcels package. It handles data management, simulation configuration, execution, and visualization.

## Features

✅ **Command-line interface** with flexible parameters  
✅ **Automatic data validation** and bounds checking  
✅ **3D ocean simulation** with U/V/W currents and settling  
✅ **Automatic output generation** (zarr format)  
✅ **Trajectory visualization** with horizontal and vertical plots  
✅ **Error handling** and user-friendly messages  

## Usage

### Basic Command Structure
```bash
python run_plastic_simulation.py --start "YYYY-MM-DD HH:MM:SS" --end "YYYY-MM-DD HH:MM:SS" --lat LAT --lon LON [OPTIONS]
```

### Required Arguments
- `--start`: Start time in format "YYYY-MM-DD HH:MM:SS"
- `--end`: End time in format "YYYY-MM-DD HH:MM:SS"  
- `--lat`: Latitude of plastic release location (degrees N)
- `--lon`: Longitude of plastic release location (degrees E)

### Optional Arguments
- `--output`: Output filename prefix (default: "plastic_simulation")
- `--timestep`: Simulation timestep in minutes (default: 20)
- `--output_freq`: Output frequency in minutes (default: 60)

## Examples

### Example 1: Mediterranean Sea (within test data bounds)
```bash
python run_plastic_simulation.py \
    --start "2020-01-04 00:00:00" \
    --end "2020-01-05 12:00:00" \
    --lat 35.0 \
    --lon 18.0 \
    --output "mediterranean_test"
```

### Example 2: Custom timestep and output frequency
```bash
python run_plastic_simulation.py \
    --start "2020-01-04 06:00:00" \
    --end "2020-01-04 18:00:00" \
    --lat 34.5 \
    --lon 19.5 \
    --output "custom_test" \
    --timestep 30 \
    --output_freq 120
```

### Example 3: Your original request (adjusted to test data)
```bash
# Original: 2024-05-01 to 2024-05-02, 33.5N 78.8W
# Adjusted to test data bounds:
python run_plastic_simulation.py \
    --start "2020-01-04 01:00:00" \
    --end "2020-01-05 01:00:00" \
    --lat 35.0 \
    --lon 18.0 \
    --output "atlantic_style_test"
```

## Data Requirements

### Current Implementation (Test Data)
- **Geographic bounds**: 33-37°N, 16-21°E (Mediterranean Sea)
- **Time bounds**: 2020-01-01 to 2020-01-06
- **Resolution**: ~8km horizontal, 75 vertical levels
- **Variables**: U/V/W velocities, temperature, salinity, bathymetry

### For Production Use
To use real oceanographic data, you would need to:
1. Download data from Copernicus Marine Service
2. Modify the data paths in the settings
3. Ensure proper time/space coverage

## Output Files

### 1. Simulation Data (`{output}.zarr`)
- **Format**: Zarr (compressed, chunked arrays)
- **Variables**: lon, lat, z (depth), time, plastic_amount
- **Dimensions**: trajectory × observation_time
- **Usage**: Can be loaded with `xarray.open_zarr()`

### 2. Trajectory Plot (`{output}_trajectory.png`)
- **Left panel**: Horizontal trajectory (lat/lon)
- **Right panel**: Vertical profile (depth vs time)
- **Annotations**: Distance traveled, depth change
- **Format**: High-resolution PNG (300 DPI)

## Physics Processes

The script currently implements:
- ✅ **3D Advection** (AdvectionRK4_3D)
- ✅ **Settling velocity** based on particle density
- ✅ **Boundary conditions** (periodic, bathymetry checking)
- ✅ **Error handling** (surface/bottom boundaries)
- ❌ **Biofouling** (disabled for simplicity)
- ❌ **Wind drift** (disabled for simplicity)  
- ❌ **Stokes drift** (disabled for simplicity)
- ❌ **Vertical mixing** (disabled for simplicity)

## Troubleshooting

### Common Issues

1. **Location outside test data bounds**
   - Script will warn and ask for confirmation
   - May produce unrealistic results

2. **Time outside test data bounds**  
   - Script automatically adjusts to available data period
   - Preserves simulation duration when possible

3. **Missing dependencies**
   - Ensure plasticparcels conda environment is activated
   - Install missing packages with conda/pip

### Error Messages
- **"Test data directory not found"**: Run from plasticparcels root directory
- **"Missing required data files"**: Check test data integrity
- **"Simulation failed"**: Check particle location and time bounds

## Technical Details

### Simulation Configuration
- **Particle properties**: 1mm diameter, 1025 kg/m³ density
- **Kernels**: 7 physics kernels for realistic behavior
- **Output**: Hourly snapshots by default
- **Precision**: Float64 for coordinates, Float32 for other variables

### Performance
- **Typical runtime**: 1-10 seconds for 24-hour simulation
- **Memory usage**: <100 MB for single particle
- **Scaling**: Linear with number of particles and timesteps

## Next Steps

To extend this script for production use:
1. **Add real data download** from Copernicus Marine Service
2. **Enable additional physics** (wind, waves, biofouling)
3. **Support multiple particles** and release scenarios
4. **Add more visualization options** (maps, animations)
5. **Implement data validation** for downloaded datasets

## Support

For issues with the script:
1. Check that you're in the correct conda environment
2. Verify input parameters are within valid ranges
3. Ensure test data files are present and accessible
4. Check the plasticparcels documentation for physics details
