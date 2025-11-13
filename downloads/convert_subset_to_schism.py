#!/usr/bin/env python3
"""
Convert Copernicus Marine subset.nc to SCHISM format for PlasticParcels
"""

import xarray as xr
import numpy as np
import os
from datetime import datetime
import pandas as pd

def convert_subset_to_schism(input_file, output_dir):
    """
    Convert subset.nc to SCHISM format with separate files per variable and day
    """
    print(f"Loading {input_file}...")
    ds = xr.open_dataset(input_file)
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Variable mapping: Copernicus -> SCHISM
    var_mapping = {
        'uo': 'vozocrtx',      # Eastward velocity
        'vo': 'vomecrty',      # Northward velocity  
        'thetao': 'votemper',  # Temperature
        'so': 'vosaline'       # Salinity
    }
    
    # Create coordinate mapping
    print("Converting coordinates...")
    
    # Convert longitude/latitude to nav_lon/nav_lat (2D arrays)
    lons_2d, lats_2d = np.meshgrid(ds.longitude.values, ds.latitude.values)
    
    # Group by day
    daily_groups = ds.groupby(ds.time.dt.date)
    
    print(f"Processing {len(daily_groups)} days...")
    
    for date, daily_data in daily_groups:
        date_str = date.strftime('%Y-%m-%d')
        print(f"  Processing {date_str}...")
        
        # Process each variable
        for copernicus_var, schism_var in var_mapping.items():
            if copernicus_var in daily_data.data_vars:
                print(f"    Converting {copernicus_var} -> {schism_var}")
                
                # Extract surface data (depth=0)
                var_data = daily_data[copernicus_var].isel(depth=0)
                
                # Create new dataset in SCHISM format
                ds_out = xr.Dataset()
                
                # Add the variable with SCHISM name
                ds_out[schism_var] = xr.DataArray(
                    var_data.values,
                    dims=['time_counter', 'y', 'x'],
                    coords={
                        'time_counter': ('time_counter', var_data.time.values),
                        'y': ('y', np.arange(len(ds.latitude))),
                        'x': ('x', np.arange(len(ds.longitude)))
                    }
                )
                
                # Add navigation coordinates
                ds_out['nav_lon'] = xr.DataArray(
                    lons_2d,
                    dims=['y', 'x'],
                    coords={'y': ds_out.y, 'x': ds_out.x}
                )
                
                ds_out['nav_lat'] = xr.DataArray(
                    lats_2d,
                    dims=['y', 'x'], 
                    coords={'y': ds_out.y, 'x': ds_out.x}
                )
                
                # Add attributes
                ds_out.attrs = {
                    'Conventions': 'CF-1.0',
                    'source': f'Copernicus Marine {date_str} converted to NEMO format',
                    'institution': 'PlasticParcels Converter',
                    'history': f'Created on {datetime.now().isoformat()}'
                }
                
                # Determine variable prefix
                if copernicus_var == 'uo':
                    prefix = 'U'
                elif copernicus_var == 'vo':
                    prefix = 'V'
                elif copernicus_var == 'thetao':
                    prefix = 'T'
                elif copernicus_var == 'so':
                    prefix = 'S'
                
                # Save file
                output_file = os.path.join(output_dir, f'{prefix}_{date_str}.nc')
                ds_out.to_netcdf(output_file)
                print(f"      Saved: {output_file}")
    
    # Only create settings.json if it doesn't exist (preserve existing configuration)
    settings_file = os.path.join(output_dir, 'settings.json')
    if not os.path.exists(settings_file):
        print("Creating new settings.json file...")
        settings = {
            "use_3D": False,
            "allow_time_extrapolation": False,
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
                "bathymetry_variables": "mbathy",
                "bathymetry_dimensions": {
                    "lon": "nav_lon",
                    "lat": "nav_lat"
                },
                "variables": {
                    "U": "vozocrtx",
                    "V": "vomecrty",
                    "conservative_temperature": "votemper",
                    "absolute_salinity": "vosaline"
                },
                "dimensions": {
                    "U": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "V": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "conservative_temperature": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "absolute_salinity": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"}
                },
                "indices": {}
            }
        }
        
        import json
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"✅ Created new settings file: {settings_file}")
    else:
        print(f"✅ Preserved existing settings file: {settings_file}")
    
    print(f"\nConversion complete!")
    print(f"Output directory: {output_dir}")
    print(f"Settings file: {settings_file}")
    print(f"Files created: {len(daily_groups) * len(var_mapping)} variable files")

if __name__ == "__main__":
    input_file = "/mnt/raid5/sbao/plastics/plasticparcels/downloads/subset.nc"
    output_dir = "/mnt/raid5/sbao/plastics/plasticparcels/copernicus_schism_output"
    
    convert_subset_to_schism(input_file, output_dir)
