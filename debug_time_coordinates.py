#!/usr/bin/env python3
"""
Debug script to check time coordinates in diagnostic datasets
"""

import json
import numpy as np
from datetime import datetime, timedelta
import xarray as xr

def check_time_coordinates():
    """Check the actual time coordinates in both datasets."""
    
    print("🔍 DEBUGGING TIME COORDINATES")
    print("=" * 35)
    
    datasets = [
        ('mobile_6hour_full', 'Full Hourly'),
        ('mobile_6hour_single', 'Single Time')
    ]
    
    for data_dir, name in datasets:
        print(f"\n📊 {name} Dataset ({data_dir}):")
        
        try:
            # Check U file time coordinates
            u_file = f'{data_dir}/U_2024-01-01.nc'
            ds = xr.open_dataset(u_file)
            
            print(f"   Time coordinate name: {list(ds.coords.keys())}")
            print(f"   Time values: {ds.time_counter.values}")
            print(f"   Time shape: {ds.time_counter.shape}")
            print(f"   Time range: {ds.time_counter.min().values} to {ds.time_counter.max().values}")
            print(f"   Data shape: {ds.vozocrtx.shape}")
            
            ds.close()
            
            # Check settings
            settings_file = f'{data_dir}/settings.json'
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            
            print(f"   Allow extrapolation: {settings.get('allow_time_extrapolation', 'Not set')}")
            
        except Exception as e:
            print(f"   ❌ Error: {e}")
    
    print(f"\n🧪 TESTING FIELDSET CREATION:")
    
    for data_dir, name in datasets:
        print(f"\n--- {name} ---")
        
        try:
            settings_file = f'{data_dir}/settings.json'
            with open(settings_file, 'r') as f:
                settings = json.load(f)
            
            # Add minimal simulation settings
            settings['simulation'] = {
                'startdate': datetime(2024, 1, 1, 0, 0, 0),
                'runtime': timedelta(minutes=30),  # Very short: 30 minutes
                'outputdt': timedelta(minutes=30),
                'dt': timedelta(minutes=10),
            }
            
            from plasticparcels.constructors import create_hydrodynamic_fieldset
            
            fieldset = create_hydrodynamic_fieldset(settings)
            
            print(f"   ✓ Fieldset created successfully")
            print(f"   Available time steps: {len(fieldset.U.grid.time)}")
            print(f"   Time range: {fieldset.U.grid.time[0]:.3f} to {fieldset.U.grid.time[-1]:.3f}")
            print(f"   Time values: {fieldset.U.grid.time}")
            
        except Exception as e:
            print(f"   ❌ Fieldset creation failed: {e}")

if __name__ == "__main__":
    check_time_coordinates()
