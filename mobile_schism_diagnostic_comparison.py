#!/usr/bin/env python3
"""
Mobile Bay SCHISM diagnostic comparison

Creates two datasets from the SAME SCHISM files:
1. Full 6-hour dataset (hourly resolution)
2. Single time step dataset (first hour only)

This provides a fair comparison to see if hourly resolution matters.

Usage:
    conda activate plasticparcels
    python mobile_schism_diagnostic_comparison.py
"""

import os
import glob
import re
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta

def create_diagnostic_datasets():
    """Create both full hourly and single-time datasets for comparison."""

    print("🔬 MOBILE BAY DIAGNOSTIC COMPARISON CREATOR 🔬")
    print("=" * 60)

    # Configuration
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    target_resolution = 0.01  # 1.1 km resolution

    # Get first 6 SCHISM files
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')

    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0

    all_files = sorted(all_files, key=extract_number)
    test_files = all_files[:6]  # First 6 hours

    print(f"Using 6 SCHISM files for comparison:")
    for i, f in enumerate(test_files):
        print(f"  Hour {i}: {os.path.basename(f)}")
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

    ds0.close()

    # Create target regular grid
    print(f"\n🎯 Creating target grid (resolution: {target_resolution}°)...")
    lon_min, lon_max = lons.min(), lons.max()
    lat_min, lat_max = lats.min(), lats.max()

    target_lons = np.arange(lon_min, lon_max + target_resolution, target_resolution)
    target_lats = np.arange(lat_min, lat_max + target_resolution, target_resolution)
    target_lon_2d, target_lat_2d = np.meshgrid(target_lons, target_lats)

    print(f"Target grid: {len(target_lats)} × {len(target_lons)} = {len(target_lats) * len(target_lons):,} points")

    # Create bathymetry
    print("🏔️  Creating bathymetry...")
    valid_mask = ~np.isnan(depths) & ~np.isnan(lons) & ~np.isnan(lats)
    if np.sum(valid_mask) == 0:
        bathy_regridded = np.zeros(target_lon_2d.shape)
    else:
        bathy_regridded = griddata(
            points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
            values=depths[valid_mask],
            xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(target_lon_2d.shape)

    # Process all 6 hours of data
    print(f"\n🔄 Processing 6 hours of SCHISM data...")

    n_hours = len(test_files)
    grid_shape = (n_hours, len(target_lats), len(target_lons))

    u_data = np.zeros(grid_shape)
    v_data = np.zeros(grid_shape)
    elev_data = np.zeros(grid_shape)

    for h, file_path in enumerate(test_files):
        print(f"  Processing hour {h}: {os.path.basename(file_path)}")

        ds = xr.open_dataset(file_path)

        # Extract velocity and elevation data
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
        for var_name, vals, output_array in [
            ('U', u_vals, u_data),
            ('V', v_vals, v_data),
            ('elevation', elev_vals, elev_data)
        ]:
            valid_mask = ~np.isnan(vals) & ~np.isnan(lons) & ~np.isnan(lats)
            if np.sum(valid_mask) == 0:
                regridded = np.zeros(target_lon_2d.shape)
            else:
                regridded = griddata(
                    points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
                    values=vals[valid_mask],
                    xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
                    method='linear',
                    fill_value=0.0
                ).reshape(target_lon_2d.shape)

            output_array[h, :, :] = regridded

    # Create both datasets
    print(f"\n📊 Creating diagnostic datasets...")

    # Dataset 1: Full 6-hour hourly data (time in seconds)
    # Use only first 5 time steps, convert hours to seconds
    time_seconds_full = np.arange(5, dtype=float) * 3600.0  # [0, 3600, 7200, 10800, 14400] seconds
    create_dataset("mobile_6hour_full", u_data[:5], v_data[:5], elev_data[:5],
                  target_lon_2d, target_lat_2d, bathy_regridded,
                  time_seconds_full, "5-hour full hourly")

    # Dataset 2: Single time step (extend to match full dataset duration)
    # Use same time coordinates as full dataset but with constant velocities
    single_u = np.array([u_data[0]] * 5)    # Repeat first time step 5 times
    single_v = np.array([v_data[0]] * 5)    # Repeat first time step 5 times
    single_elev = np.array([elev_data[0]] * 5)  # Repeat first time step 5 times

    # Same time coordinates as full dataset to avoid boundary issues
    create_dataset("mobile_6hour_single", single_u, single_v, single_elev,
                  target_lon_2d, target_lat_2d, bathy_regridded,
                  time_seconds_full, "single time step (extended)")

    print(f"\n🎉 DIAGNOSTIC DATASETS CREATED! 🎉")
    print("=" * 45)
    print("✅ mobile_6hour_full/    - 5 hourly time steps (0-4 hours, varying velocities)")
    print("✅ mobile_6hour_single/  - 5 time steps (0-4 hours, constant velocities)")
    print()
    print("🧪 Run comparison tests:")
    print("   conda activate plasticparcels")
    print("   python test_diagnostic_comparison.py")

def create_dataset(output_dir, u_data, v_data, elev_data,
                  target_lon_2d, target_lat_2d, bathy_regridded,
                  time_hours, description):
    """Create a single dataset with given data."""

    print(f"  Creating {output_dir} ({description})...")

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Ensure time_hours is a proper numpy array with correct dtype
    time_hours = np.array(time_hours, dtype=np.float64)

    print(f"    Time coordinates: {time_hours}")
    print(f"    Data shape: {u_data.shape}")

    # Create coordinate variables
    coords = {
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'time_counter': ('time_counter', time_hours),
        'x': ('x', np.arange(target_lon_2d.shape[1])),
        'y': ('y', np.arange(target_lon_2d.shape[0]))
    }

    # Save variables
    variables = {
        'U': ('vozocrtx', u_data),
        'V': ('vomecrty', v_data),
        'W': ('vovecrtz', np.zeros_like(u_data)),
        'T': ('votemper', elev_data),
        'S': ('vosaline', np.full_like(u_data, 35.0))
    }

    for var_letter, (nemo_var, data) in variables.items():
        ds = xr.Dataset({
            nemo_var: (['time_counter', 'y', 'x'], data)
        }, coords=coords)

        # Add time coordinate attributes (time in seconds)
        ds.time_counter.attrs.update({
            'units': 'seconds since 2024-01-01 00:00:00',
            'calendar': 'gregorian',
            'long_name': 'time',
            'standard_name': 'time'
        })

        ds.attrs.update({
            'Conventions': 'CF-1.0',
            'source': f'Mobile Bay SCHISM diagnostic - {description}',
            'institution': 'PlasticParcels Regridder'
        })

        filename = f"{var_letter}_2024-01-01.nc"
        filepath = os.path.join(output_dir, filename)
        ds.to_netcdf(filepath)
        ds.close()

    # Save mesh and bathymetry files
    mesh_ds = xr.Dataset({
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'x': ('x', np.arange(target_lon_2d.shape[1])),
        'y': ('y', np.arange(target_lon_2d.shape[0]))
    })
    mesh_file = os.path.join(output_dir, 'ocean_mesh_hgr.nc')
    mesh_ds.to_netcdf(mesh_file)

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

    # Create settings file
    # Set allow_time_extrapolation based on dataset type
    if 'single' in output_dir.lower():
        allow_extrapolation = True  # Required for constant velocity fields
    else:
        allow_extrapolation = False  # Strict for varying fields

    settings = {
        "use_3D": False,
        "allow_time_extrapolation": allow_extrapolation,
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

    print(f"    ✓ {output_dir} created with {len(time_hours)} time steps")

if __name__ == "__main__":
    create_diagnostic_datasets()
