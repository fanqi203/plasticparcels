#!/usr/bin/env python3
"""
Create W (vertical velocity) files for Copernicus data.
Since this is surface data, W will be zero everywhere.
"""

import xarray as xr
import numpy as np
import os
from datetime import datetime, timedelta

def create_w_files():
    """Create W files based on U files structure"""
    
    copernicus_dir = "copernicus_schism_output"
    
    # Get list of U files to match
    u_files = [f for f in os.listdir(copernicus_dir) if f.startswith('U_') and f.endswith('.nc')]
    u_files.sort()
    
    print(f"Found {len(u_files)} U files to match")
    
    for u_file in u_files:
        # Extract date from filename
        date_str = u_file.replace('U_', '').replace('.nc', '')
        w_file = f"W_{date_str}.nc"
        w_path = os.path.join(copernicus_dir, w_file)
        
        if os.path.exists(w_path):
            print(f"✅ {w_file} already exists")
            continue
            
        # Load U file to get structure
        u_path = os.path.join(copernicus_dir, u_file)
        with xr.open_dataset(u_path) as u_ds:
            print(f"📁 Creating {w_file} based on {u_file}")
            
            # Create W dataset with same structure but zero values
            w_ds = u_ds.copy(deep=True)
            
            # Replace U variable with W (vertical velocity = 0)
            w_data = np.zeros_like(u_ds['vozocrtx'].values)
            
            # Create new dataset with W variable
            w_ds = w_ds.drop_vars(['vozocrtx'])  # Remove U variable
            w_ds['vovecrtz'] = (u_ds['vozocrtx'].dims, w_data)  # Add W variable
            
            # Update attributes
            w_ds['vovecrtz'].attrs = {
                'long_name': 'Vertical velocity',
                'standard_name': 'upward_sea_water_velocity', 
                'units': 'm s-1',
                'unit_long': 'Meters per second',
                '_FillValue': 9.96921e+36,
                'valid_min': -10.0,
                'valid_max': 10.0
            }
            
            # Update global attributes
            w_ds.attrs['title'] = 'Vertical velocity (W) - Zero for surface data'
            w_ds.attrs['comment'] = 'Created from Copernicus surface data - W=0 everywhere'
            
            # Save W file
            w_ds.to_netcdf(w_path)
            print(f"✅ Created {w_file}")

if __name__ == "__main__":
    create_w_files()
    print("\n🎉 All W files created successfully!")
