# Mobile Bay SCHISM to PlasticParcels Integration

## Overview

This document describes the integration of SCHISM hydrodynamic model output with PlasticParcels for plastic pollution modeling in Mobile Bay, Alabama. The workflow converts SCHISM's unstructured grid output to PlasticParcels-compatible NEMO format while preserving full temporal resolution.

## Key Findings

### Temporal Resolution Impact Study

A comprehensive diagnostic comparison revealed that **hourly temporal resolution is critical** for accurate particle tracking in Mobile Bay:

- **Position differences**: Up to 17+ km between hourly vs. daily resolution
- **Transport accuracy**: Hourly data captures essential tidal and diurnal effects
- **Scientific impact**: Single time step predictions can be completely wrong for pollution management

**Conclusion**: Full hourly SCHISM data is essential for realistic Mobile Bay plastic pollution modeling.

## Production Converter

### Features

- **Scalable processing**: Handle hours to months of SCHISM data
- **Preserves temporal resolution**: Maintains hourly hydrodynamic variations
- **PlasticParcels compatible**: Creates proper NEMO format files
- **Robust error handling**: Comprehensive logging and validation
- **Command-line interface**: Easy integration into workflows

### Installation Requirements

```bash
conda activate plasticparcels
pip install scipy xarray netcdf4
```

### Basic Usage

```bash
# Convert SCHISM data to PlasticParcels format
python mobile_bay_schism_converter.py \
    /path/to/schism/outputs \
    /path/to/output/directory

# Test with limited files
python mobile_bay_schism_converter.py \
    /anvil/projects/x-ees240085/sbao/mobile/outputs \
    mobile_bay_production \
    --max-files 48 \
    --hours-per-day 24
```

### Advanced Options

```bash
python mobile_bay_schism_converter.py \
    /path/to/schism/outputs \
    /path/to/output/directory \
    --resolution 0.005 \
    --hours-per-day 24 \
    --max-files 168 \
    --log-level DEBUG
```

## File Structure

### Input (SCHISM)
```
/anvil/projects/x-ees240085/sbao/mobile/outputs/
├── out2d_1.nc      # Hour 1
├── out2d_2.nc      # Hour 2
├── ...
└── out2d_249.nc    # Hour 249
```

### Output (PlasticParcels)
```
mobile_bay_production/
├── U_2024-01-01.nc              # Day 1 velocities (24 time steps)
├── V_2024-01-01.nc              # Day 1 velocities (24 time steps)
├── W_2024-01-01.nc              # Day 1 velocities (zero for 2D)
├── T_2024-01-01.nc              # Day 1 temperature (elevation proxy)
├── S_2024-01-01.nc              # Day 1 salinity (constant)
├── U_2024-01-02.nc              # Day 2 velocities (24 time steps)
├── ...
├── ocean_mesh_hgr.nc            # Grid coordinates
├── bathymetry_mesh_zgr.nc       # Bathymetry data
├── settings.json                # PlasticParcels configuration
└── mobile_bay_converter.log     # Conversion log
```

## PlasticParcels Integration

### Loading Converted Data

```python
import json
from datetime import datetime, timedelta
from plasticparcels.constructors import create_hydrodynamic_fieldset

# Load settings
with open('mobile_bay_production/settings.json', 'r') as f:
    settings = json.load(f)

# Add simulation parameters
settings['simulation'] = {
    'startdate': datetime(2024, 1, 1, 0, 0, 0),
    'runtime': timedelta(days=7),        # 7-day simulation
    'outputdt': timedelta(hours=6),      # Output every 6 hours
    'dt': timedelta(minutes=20),         # 20-minute time step
}

# Create fieldset
fieldset = create_hydrodynamic_fieldset(settings)
```

### Running Simulations

```python
from plasticparcels.constructors import create_particleset
import parcels

# Define particle release locations
release_locations = {
    'lons': [-88.0, -88.1, -88.2],      # Mobile Bay coordinates
    'lats': [30.3, 30.4, 30.5],        # Mobile Bay coordinates
    'plastic_amount': [1.0, 1.0, 1.0]   # kg of plastic per particle
}

# Create particle set
pset = create_particleset(fieldset, settings, release_locations)

# Run simulation
pset.execute(
    parcels.AdvectionRK4,
    runtime=settings['simulation']['runtime'],
    dt=settings['simulation']['dt'],
    output_file=pset.ParticleFile(
        name='mobile_bay_trajectories.zarr',
        outputdt=settings['simulation']['outputdt']
    )
)
```

## Technical Details

### Grid Conversion

- **Source**: SCHISM unstructured triangular grid (~112,762 nodes)
- **Target**: Regular lat/lon grid (0.01° resolution ≈ 1.1 km)
- **Method**: Linear interpolation using scipy.interpolate.griddata
- **Domain**: Mobile Bay (-89.124°E to -87.964°E, 30.017°N to 30.617°N)

### Critical Technical Fixes

Based on diagnostic testing, the following issues were identified and fixed:

1. **Time Units**: PlasticParcels expects time in **seconds**, not hours
   - Fixed: Convert time coordinates to seconds since reference date
   - Added: Proper CF-compliant time attributes

2. **Matplotlib Backend**: Headless servers need non-interactive backend
   - Fixed: Set `matplotlib.use('Agg')` before importing pyplot
   - Enables: Plot generation on remote servers without display

3. **Time Extrapolation**: Different requirements for different data types
   - Varying fields: `allow_time_extrapolation=false` (strict boundaries)
   - Constant fields: `allow_time_extrapolation=true` (handle edge cases)

### Temporal Structure

- **Input**: Individual hourly files (out2d_1.nc, out2d_2.nc, ...)
- **Output**: Daily files with multiple time steps (U_2024-01-01.nc with 24 hours)
- **Time coordinates**: Continuous across files (0, 1, 2, ..., 23, 24, 25, ...)
- **Compatibility**: PlasticParcels select_files() function

### Variable Mapping

| SCHISM Variable | NEMO Variable | Description |
|----------------|---------------|-------------|
| depthAverageVelX | vozocrtx | U velocity (m/s) |
| depthAverageVelY | vomecrty | V velocity (m/s) |
| elevation | votemper | Sea surface elevation (m) |
| - | vovecrtz | W velocity (0 for 2D) |
| - | vosaline | Salinity (constant 35 PSU) |

## Performance Considerations

### Processing Time

- **~1 minute per SCHISM file** on standard hardware
- **~4 hours for 249 files** (full Mobile Bay dataset)
- **Memory usage**: ~2-4 GB peak for regridding

### Scaling Recommendations

- **Testing**: Use `--max-files 48` (2 days)
- **Production**: Process full dataset (249 files ≈ 10 days)
- **Long-term**: Extend to weeks/months for seasonal studies

## Quality Assurance

### Validation Tests

1. **Grid conversion accuracy**: Verified interpolation preserves spatial patterns
2. **Temporal continuity**: Confirmed smooth time transitions between files
3. **PlasticParcels compatibility**: Tested fieldset creation and particle tracking
4. **Resolution impact**: Demonstrated 17+ km differences with/without hourly data

### Diagnostic Tools

```bash
# Test conversion with limited files
python mobile_bay_schism_converter.py \
    /anvil/projects/x-ees240085/sbao/mobile/outputs \
    test_output \
    --max-files 12 \
    --hours-per-day 6

# Verify PlasticParcels integration
python -c "
from plasticparcels.constructors import create_hydrodynamic_fieldset
import json
with open('test_output/settings.json') as f:
    settings = json.load(f)
fieldset = create_hydrodynamic_fieldset(settings)
print(f'Success! Time steps: {len(fieldset.U.grid.time)}')
"
```

## Applications

### Pollution Source Tracking

- **Oil spills**: Track spill trajectories for response planning
- **Plastic pollution**: Model microplastic transport and accumulation
- **Nutrient loading**: Study pollutant dispersion from rivers/ports

### Environmental Management

- **Cleanup optimization**: Predict where debris will accumulate
- **Protected area assessment**: Evaluate pollution risks to sensitive habitats
- **Policy support**: Provide scientific basis for regulations

### Research Applications

- **Tidal transport**: Study how tidal cycles affect particle movement
- **Seasonal patterns**: Analyze long-term transport variations
- **Climate impacts**: Assess how changing conditions affect pollution

## Troubleshooting

### Common Issues

1. **File not found errors**: Check SCHISM directory path and file permissions
2. **Memory errors**: Reduce `--hours-per-day` or process fewer files
3. **PlasticParcels errors**: Verify conda environment and dependencies
4. **Time extrapolation warnings**: Normal for edge cases, set `allow_time_extrapolation: true`

### Support

- **Log files**: Check `mobile_bay_converter.log` for detailed error messages
- **Validation**: Use diagnostic comparison tools to verify results
- **Documentation**: Refer to PlasticParcels documentation for simulation setup

## References

- **SCHISM Model**: [SCHISM Documentation](http://ccrm.vims.edu/schismweb/)
- **PlasticParcels**: [PlasticParcels Documentation](https://plastic.oceanparcels.org/)
- **Mobile Bay**: [NOAA Mobile Bay Information](https://www.noaa.gov/education/resource-collections/marine/mobile-bay)

## Production Workflow

### Quick Start

```bash
# 1. Convert SCHISM data (test with 48 files = 2 days)
python mobile_bay_schism_converter.py \
    /anvil/projects/x-ees240085/sbao/mobile/outputs \
    mobile_bay_production \
    --max-files 48

# 2. Test the conversion
python test_mobile_bay_production.py mobile_bay_production

# 3. Run your PlasticParcels simulation
python your_simulation_script.py
```

### Production Scale

```bash
# Convert full dataset (249 files ≈ 10 days)
python mobile_bay_schism_converter.py \
    /anvil/projects/x-ees240085/sbao/mobile/outputs \
    mobile_bay_full \
    --hours-per-day 24

# This creates ~10 daily files with 24 hourly time steps each
```

## Repository Files

- `mobile_bay_schism_converter.py` - Production converter script
- `test_mobile_bay_production.py` - Validation test script
- `MOBILE_BAY_SCHISM_INTEGRATION.md` - Complete documentation
- `mobile_schism_diagnostic_comparison.py` - Temporal resolution diagnostic
- `test_diagnostic_comparison.py` - Diagnostic test script

## Citation

If using this workflow in research, please cite:

```
Mobile Bay SCHISM to PlasticParcels Integration (2024)
Developed for plastic pollution modeling in Mobile Bay, Alabama
Demonstrates critical importance of hourly temporal resolution
```

---

**Version**: 1.0
**Last Updated**: 2024
**Key Finding**: Hourly resolution prevents 17+ km errors in particle tracking
