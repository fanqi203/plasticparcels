#!/usr/bin/env python3
"""
Aggregate Mobile Bay individual file results into complete time series

Takes the individual mobile_file_*_work directories and combines them
into a single time series dataset for continuous PlasticParcels simulations.

Usage:
    conda activate plasticparcels
    python aggregate_mobile_timeseries.py
"""

import os
import glob
import numpy as np
import xarray as xr
import json
from datetime import datetime, timedelta
import re

def aggregate_mobile_timeseries():
    """Aggregate individual Mobile Bay results into complete time series."""
    
    print("🔄 AGGREGATING MOBILE BAY TIME SERIES 🔄")
    print("=" * 50)
    
    # Find all mobile_file_*_work directories
    work_dirs = glob.glob('mobile_file_*_work')
    
    # Sort by file number
    def extract_file_number(dirname):
        match = re.search(r'mobile_file_(\d+)_work', dirname)
        return int(match.group(1)) if match else 0
    
    work_dirs = sorted(work_dirs, key=extract_file_number)
    
    if not work_dirs:
        print("❌ No mobile_file_*_work directories found!")
        print("   Please run run_mobile_example_work.py first")
        return False
    
    print(f"Found {len(work_dirs)} individual result directories:")
    for i, dir_name in enumerate(work_dirs):
        print(f"  {i+1}. {dir_name}")
    
    output_dir = 'mobile_complete_timeseries'
    os.makedirs(output_dir, exist_ok=True)
    
    print(f"\n📥 Loading individual datasets...")
    
    # Load all datasets
    datasets = {}
    variables = ['U', 'V', 'W', 'T', 'S']
    
    for var in variables:
        var_datasets = []
        
        for i, work_dir in enumerate(work_dirs):
            var_file = os.path.join(work_dir, f'{var}_nemo.nc')
            
            if os.path.exists(var_file):
                print(f"   Loading {var} from {work_dir}")
                ds = xr.open_dataset(var_file)
                
                # Add time coordinate if missing or fix it
                if 'time_counter' not in ds.dims:
                    # Add time dimension
                    ds = ds.expand_dims('time_counter')
                
                # Set correct time value (hour i)
                ds = ds.assign_coords(time_counter=[float(i)])
                
                var_datasets.append(ds)
            else:
                print(f"   ⚠️  Missing {var_file}")
        
        if var_datasets:
            # Concatenate along time dimension
            print(f"   Concatenating {len(var_datasets)} {var} datasets...")
            combined_ds = xr.concat(var_datasets, dim='time_counter')
            datasets[var] = combined_ds
        else:
            print(f"   ❌ No {var} datasets found")
    
    if not datasets:
        print("❌ No datasets could be loaded!")
        return False
    
    print(f"\n💾 Saving aggregated time series...")
    
    # Get grid coordinates from first dataset
    first_ds = list(datasets.values())[0]
    
    # Create proper time coordinate
    n_times = len(work_dirs)
    time_hours = np.arange(n_times, dtype=float)
    
    # Update coordinates for all datasets
    for var, ds in datasets.items():
        # Ensure proper time coordinate
        ds = ds.assign_coords(time_counter=time_hours)
        
        # Save with date-based naming for PlasticParcels compatibility
        filename = f"{var}_2024-01-01.nc"
        filepath = os.path.join(output_dir, filename)
        ds.to_netcdf(filepath)
        print(f"   ✓ Saved {filepath}")
        
        # Close dataset
        ds.close()
    
    # Copy mesh and bathymetry files from first directory
    print("   Copying mesh and bathymetry files...")
    
    for filename in ['ocean_mesh_hgr.nc', 'bathymetry_mesh_zgr.nc']:
        src_file = os.path.join(work_dirs[0], filename)
        dst_file = os.path.join(output_dir, filename)
        
        if os.path.exists(src_file):
            # Copy using xarray to ensure consistency
            ds = xr.open_dataset(src_file)
            ds.to_netcdf(dst_file)
            ds.close()
            print(f"   ✓ Copied {filename}")
        else:
            print(f"   ⚠️  Missing {src_file}")
    
    # Create aggregated settings file
    print("⚙️  Creating aggregated settings...")
    
    settings = {
        "use_3D": False,
        "allow_time_extrapolation": False,  # Now we have proper time series!
        "verbose_delete": False,
        "use_mixing": False,
        "use_biofouling": False,
        "use_stokes": False,
        "use_wind": False,
        "ocean": {
            "modelname": "NEMO0083",
            "directory": f"{output_dir}/",
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
                "U": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                "V": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                "W": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                "conservative_temperature": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                "absolute_salinity": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"}
            },
            "indices": {},
            "bathymetry_variables": {"bathymetry": "mbathy"},
            "bathymetry_dimensions": {"lon": "nav_lon", "lat": "nav_lat"}
        }
    }
    
    settings_file = os.path.join(output_dir, 'complete_timeseries_settings.json')
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"   ✓ Saved {settings_file}")
    
    print(f"\n🎉 AGGREGATION COMPLETED! 🎉")
    print("=" * 40)
    print(f"✅ Combined {len(work_dirs)} time steps")
    print(f"✅ Created complete time series in '{output_dir}/'")
    print(f"✅ Time range: 0 to {len(work_dirs)-1} hours")
    print()
    print("📁 OUTPUT FILES:")
    print(f"   • U_2024-01-01.nc, V_2024-01-01.nc, W_2024-01-01.nc")
    print(f"   • T_2024-01-01.nc, S_2024-01-01.nc")
    print(f"   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
    print(f"   • complete_timeseries_settings.json")
    print()
    print("🧪 Test the complete time series:")
    print("   conda activate plasticparcels")
    print("   python test_complete_timeseries.py")
    
    return output_dir, settings_file

def check_timeseries_info(output_dir='mobile_complete_timeseries'):
    """Check information about the aggregated time series."""
    
    print(f"\n🔍 CHECKING TIME SERIES INFO 🔍")
    print("=" * 40)
    
    if not os.path.exists(output_dir):
        print(f"❌ Directory {output_dir} not found")
        return
    
    # Check each variable file
    variables = ['U', 'V', 'W', 'T', 'S']
    
    for var in variables:
        var_file = os.path.join(output_dir, f'{var}_2024-01-01.nc')
        
        if os.path.exists(var_file):
            ds = xr.open_dataset(var_file)
            
            print(f"\n{var} variable:")
            print(f"   Shape: {ds[list(ds.data_vars.keys())[0]].shape}")
            print(f"   Time steps: {len(ds.time_counter)}")
            print(f"   Time range: {ds.time_counter.values[0]} to {ds.time_counter.values[-1]} hours")
            print(f"   Grid size: {ds.dims}")
            
            ds.close()
        else:
            print(f"\n❌ {var} file not found: {var_file}")

if __name__ == "__main__":
    # Aggregate the time series
    result = aggregate_mobile_timeseries()
    
    if result:
        output_dir, settings_file = result
        
        # Check the results
        check_timeseries_info(output_dir)
        
        print(f"\n🌊 READY FOR CONTINUOUS SIMULATIONS! 🌊")
        print("You can now run multi-hour simulations with time-varying currents!")
    else:
        print("❌ Aggregation failed. Check error messages above.")
