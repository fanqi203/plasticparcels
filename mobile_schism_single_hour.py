#!/usr/bin/env python3
"""
Mobile Bay SCHISM to NEMO converter - Single hour per day (diagnostic)

Creates daily files with only ONE time step per day for comparison with hourly data.
This will help determine if hourly resolution actually affects particle trajectories.

Usage:
    conda activate plasticparcels
    python mobile_schism_single_hour.py
"""

import os
import glob
import re
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta

def convert_mobile_schism_single_hour():
    """Convert Mobile Bay SCHISM to single hour per day format (diagnostic)."""
    
    print("🌊 MOBILE BAY SCHISM TO SINGLE HOUR FORMAT (DIAGNOSTIC) 🌊")
    print("=" * 65)
    
    # Configuration
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    output_dir = 'mobile_single_hour'
    target_resolution = 0.01  # 1.1 km resolution
    
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Get SCHISM files - use only 2 files (one per "day")
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')
    
    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0
    
    all_files = sorted(all_files, key=extract_number)
    
    # Use only 2 files - one for each day (single time step per day)
    test_files = [all_files[0], all_files[6]]  # Hour 0 and hour 6
    
    print(f"Found {len(all_files)} total SCHISM files")
    print(f"Using only 2 files for single-hour diagnostic:")
    for i, f in enumerate(test_files):
        print(f"  Day {i+1}: {os.path.basename(f)} (single time step)")
    print()
    
    # Load first file to get grid structure
    print("📥 Loading SCHISM grid structure...")
    ds0 = xr.open_dataset(test_files[0])
    
    # Extract coordinates
    lons = ds0['SCHISM_hgrid_node_x'].values
    lats = ds0['SCHISM_hgrid_node_y'].values
    depths = ds0['depth'].values
    
    print(f"Grid info:")
    print(f"  Nodes: {len(lons):,}")
    print(f"  Longitude range: {lons.min():.3f} to {lons.max():.3f}")
    print(f"  Latitude range: {lats.min():.3f} to {lats.max():.3f}")
    print(f"  Depth range: {depths.min():.1f} to {depths.max():.1f} m")
    
    ds0.close()
    
    # Create target regular grid
    print(f"\n🎯 Creating target grid (resolution: {target_resolution}°)...")
    lon_min, lon_max = lons.min(), lons.max()
    lat_min, lat_max = lats.min(), lats.max()
    
    target_lons = np.arange(lon_min, lon_max + target_resolution, target_resolution)
    target_lats = np.arange(lat_min, lat_max + target_resolution, target_resolution)
    target_lon_2d, target_lat_2d = np.meshgrid(target_lons, target_lats)
    
    print(f"Target grid: {len(target_lats)} × {len(target_lons)} = {len(target_lats) * len(target_lons):,} points")
    
    # Create bathymetry (time-independent)
    print("🏔️  Creating bathymetry...")
    valid_mask = ~np.isnan(depths) & ~np.isnan(lons) & ~np.isnan(lats)
    if np.sum(valid_mask) == 0:
        print("    Warning: No valid bathymetry data, using zero depth")
        bathy_regridded = np.zeros(target_lon_2d.shape)
    else:
        bathy_regridded = griddata(
            points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
            values=depths[valid_mask],
            xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(target_lon_2d.shape)
    
    # Process each file as a single-time-step daily file
    print(f"\n🔄 Processing {len(test_files)} files (single time step each)...")
    
    base_date = datetime(2024, 1, 1)
    
    for day, file_path in enumerate(test_files):
        day_date = base_date + timedelta(days=day)
        date_str = day_date.strftime('%Y-%m-%d')
        
        print(f"\n  Day {day+1}: {date_str} from {os.path.basename(file_path)}")
        
        ds = xr.open_dataset(file_path)
        
        # Extract velocity and elevation data (single time step)
        try:
            if len(ds['depthAverageVelX'].shape) == 2:
                u_vals = ds['depthAverageVelX'][0, :].values
                v_vals = ds['depthAverageVelY'][0, :].values
                elev_vals = ds['elevation'][0, :].values
            else:
                u_vals = ds['depthAverageVelX'].values
                v_vals = ds['depthAverageVelY'].values
                elev_vals = ds['elevation'].values
        except Exception as e:
            print(f"    Error extracting data: {e}")
            u_vals = ds['depthAverageVelX'].values.flatten()
            v_vals = ds['depthAverageVelY'].values.flatten()
            elev_vals = ds['elevation'].values.flatten()
        
        ds.close()
        
        # Regrid each variable
        regridded_data = {}
        
        for var_name, vals in [('U', u_vals), ('V', v_vals), ('elevation', elev_vals)]:
            valid_mask = ~np.isnan(vals) & ~np.isnan(lons) & ~np.isnan(lats)
            if np.sum(valid_mask) == 0:
                print(f"    Warning: No valid data for {var_name}, using zeros")
                regridded = np.zeros(target_lon_2d.shape)
            else:
                regridded = griddata(
                    points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
                    values=vals[valid_mask],
                    xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
                    method='linear',
                    fill_value=0.0
                ).reshape(target_lon_2d.shape)
            
            regridded_data[var_name] = regridded
        
        # Create time coordinate (single time step, but continuous across days)
        time_hours = np.array([float(day * 24)])  # Day 0: hour 0, Day 1: hour 24
        
        # Create coordinate variables (no depth for 2D surface data)
        coords = {
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
            'time_counter': ('time_counter', time_hours),
            'x': ('x', np.arange(target_lon_2d.shape[1])),
            'y': ('y', np.arange(target_lon_2d.shape[0]))
        }
        
        # Save daily files for each variable (single time step)
        variables = {
            'U': ('vozocrtx', regridded_data['U']),
            'V': ('vomecrty', regridded_data['V']),
            'W': ('vovecrtz', np.zeros_like(regridded_data['U'])),
            'T': ('votemper', regridded_data['elevation']),
            'S': ('vosaline', np.full_like(regridded_data['U'], 35.0))
        }
        
        for var_letter, (nemo_var, data) in variables.items():
            # Create dataset with single time step
            # Shape: (time_counter, y, x) - single time step
            data_3d = data[np.newaxis, :, :]  # Add time dimension
            
            ds = xr.Dataset({
                nemo_var: (['time_counter', 'y', 'x'], data_3d)
            }, coords=coords)
            
            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': f'Mobile Bay SCHISM {date_str} single hour diagnostic',
                'institution': 'PlasticParcels Regridder'
            })
            
            # Save with PlasticParcels-compatible naming
            filename = f"{var_letter}_{date_str}.nc"
            filepath = os.path.join(output_dir, filename)
            ds.to_netcdf(filepath)
            
            ds.close()
        
        print(f"    ✓ Created single-hour files: {{U,V,W,T,S}}_{date_str}.nc")
    
    # Save mesh and bathymetry files
    print("\n🗺️  Saving mesh and bathymetry files...")
    
    # Mesh file
    mesh_ds = xr.Dataset({
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'x': ('x', np.arange(target_lon_2d.shape[1])),
        'y': ('y', np.arange(target_lon_2d.shape[0]))
    })
    mesh_file = os.path.join(output_dir, 'ocean_mesh_hgr.nc')
    mesh_ds.to_netcdf(mesh_file)
    print(f"   ✓ Saved {mesh_file}")
    
    # Bathymetry file
    mbathy = np.ones_like(bathy_regridded, dtype=int)
    mbathy[bathy_regridded <= 0] = 0
    
    bathy_ds = xr.Dataset({
        'mbathy': (['y', 'x'], mbathy),
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
    })
    bathy_file = os.path.join(output_dir, 'bathymetry_mesh_zgr.nc')
    bathy_ds.to_netcdf(bathy_file)
    print(f"   ✓ Saved {bathy_file}")
    
    # Create settings file
    print("⚙️  Creating PlasticParcels settings...")
    
    settings = {
        "use_3D": False,
        "allow_time_extrapolation": True,
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
    
    settings_file = os.path.join(output_dir, 'settings.json')
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"   ✓ Saved {settings_file}")
    
    print(f"\n🎉 SINGLE HOUR DIAGNOSTIC COMPLETED! 🎉")
    print("=" * 50)
    print(f"✅ Created 2 daily files with 1 time step each")
    print(f"✅ Time coordinates: [0.0, 24.0] hours (daily snapshots)")
    print(f"✅ Grid resolution: {target_resolution}° ({target_resolution * 111.32:.1f} km)")
    print()
    print("📁 OUTPUT FILES (SINGLE HOUR DIAGNOSTIC):")
    print(f"   • U_2024-01-01.nc (1 time step: hour 0)")
    print(f"   • U_2024-01-02.nc (1 time step: hour 24)")
    print(f"   • V, W, T, S files with same structure")
    print(f"   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
    print(f"   • settings.json")
    print()
    print("🧪 Test single-hour diagnostic:")
    print("   conda activate plasticparcels")
    print("   python test_single_hour_diagnostic.py")
    
    return output_dir, settings_file

if __name__ == "__main__":
    convert_mobile_schism_single_hour()
