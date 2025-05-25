#!/usr/bin/env python3
"""
Mobile Bay SCHISM to NEMO converter - Proper PlasticParcels format

Converts SCHISM files to the exact format used by PlasticParcels test data:
- Individual files per time step: mobile_U_2024-01-01-01.nc, mobile_U_2024-01-01-02.nc, etc.
- Single time step per file
- Proper NEMO variable names and structure

Usage:
    conda activate plasticparcels
    python mobile_schism_to_nemo_proper.py
"""

import os
import glob
import re
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta

def convert_mobile_schism_proper():
    """Convert Mobile Bay SCHISM to proper PlasticParcels format."""

    print("🌊 MOBILE BAY SCHISM TO NEMO (PROPER FORMAT) 🌊")
    print("=" * 60)

    # Configuration
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    output_dir = 'mobile_nemo_proper'
    target_resolution = 0.01  # 1.1 km resolution

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get first 5 sequential files
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')

    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0

    all_files = sorted(all_files, key=extract_number)
    test_files = all_files[:5]  # Process first 5 files

    print(f"Found {len(all_files)} total SCHISM files")
    print(f"Processing first {len(test_files)} sequential files:")
    for i, f in enumerate(test_files):
        print(f"  {i+1}. {os.path.basename(f)} → Hour {i+1}")
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

    # Process each time step as separate files
    print(f"\n🔄 Processing {len(test_files)} time steps...")

    # Base date for file naming
    base_date = datetime(2024, 1, 1)

    for t, file_path in enumerate(test_files):
        # Calculate date for this time step (hourly, since SCHISM files are hourly)
        current_datetime = base_date + timedelta(hours=t)
        date_str = current_datetime.strftime('%Y-%m-%d-%H')

        print(f"  Processing {os.path.basename(file_path)} → {date_str}")

        ds = xr.open_dataset(file_path)

        # Extract velocity and elevation data
        try:
            if len(ds['depthAverageVelX'].shape) == 2:
                # Shape: (time, nodes) - take first time step
                u_vals = ds['depthAverageVelX'][0, :].values
                v_vals = ds['depthAverageVelY'][0, :].values
                elev_vals = ds['elevation'][0, :].values
            else:
                # Shape: (nodes,) - single time step
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
            # Remove NaN values before regridding
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

        # Create depth levels (following test data format)
        # For 2D SCHISM data, we'll create a single surface layer
        depth_levels = np.array([0.5])  # Single surface layer at 0.5m depth
        n_depths = len(depth_levels)

        # Create coordinate variables (following test data format)
        coords = {
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
            'deptht': ('deptht', depth_levels),
            'time_counter': ('time_counter', [0.0]),  # Single time step
            'x': ('x', np.arange(target_lon_2d.shape[1])),
            'y': ('y', np.arange(target_lon_2d.shape[0]))
        }

        # Save individual files for each variable (following test data format)
        variables = {
            'U': ('vozocrtx', regridded_data['U']),
            'V': ('vomecrty', regridded_data['V']),
            'W': ('vovecrtz', np.zeros_like(regridded_data['U'])),  # Zero for 2D
            'T': ('votemper', regridded_data['elevation']),  # Use elevation as temperature proxy
            'S': ('vosaline', np.full_like(regridded_data['U'], 35.0))  # Constant salinity
        }

        for var_letter, (nemo_var, data) in variables.items():
            # Create dataset with depth dimension (following test data format)
            # Shape: (deptht, y, x) for 3D variables
            data_3d = data[np.newaxis, :, :]  # Add depth dimension: (1, y, x)

            ds = xr.Dataset({
                nemo_var: (['deptht', 'y', 'x'], data_3d)
            }, coords=coords)

            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': f'Mobile Bay SCHISM {os.path.basename(file_path)} regridded to NEMO format',
                'institution': 'PlasticParcels Regridder'
            })

            # Save with PlasticParcels naming convention (no prefix)
            filename = f"{var_letter}_{date_str}.nc"
            filepath = os.path.join(output_dir, filename)
            ds.to_netcdf(filepath)

            ds.close()

        print(f"    ✓ Created files: mobile_{{U,V,W,T,S}}_{date_str}.nc")

    # Save mesh and bathymetry files (time-independent)
    print("\n🗺️  Saving mesh and bathymetry files...")

    # Mesh file (following test data format)
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

    # Create settings file (following test data format)
    print("⚙️  Creating PlasticParcels settings...")

    settings = {
        "use_3D": False,
        "allow_time_extrapolation": True,  # Allow extrapolation for edge cases
        "verbose_delete": False,
        "use_mixing": False,
        "use_biofouling": False,
        "use_stokes": False,
        "use_wind": False,
        "ocean": {
            "modelname": "NEMO0083",
            "directory": f"{output_dir}/",
            "filename_style": "",  # No prefix
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
                "U": {"lon": "nav_lon", "lat": "nav_lat", "depth": "deptht", "time": "time_counter"},
                "V": {"lon": "nav_lon", "lat": "nav_lat", "depth": "deptht", "time": "time_counter"},
                "W": {"lon": "nav_lon", "lat": "nav_lat", "depth": "deptht", "time": "time_counter"},
                "conservative_temperature": {"lon": "nav_lon", "lat": "nav_lat", "depth": "deptht", "time": "time_counter"},
                "absolute_salinity": {"lon": "nav_lon", "lat": "nav_lat", "depth": "deptht", "time": "time_counter"}
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

    print(f"\n🎉 CONVERSION COMPLETED! 🎉")
    print("=" * 40)
    print(f"✅ Processed {len(test_files)} time steps")
    print(f"✅ Created individual NEMO files per time step (hourly)")
    print(f"✅ Grid resolution: {target_resolution}° ({target_resolution * 111.32:.1f} km)")
    print()
    print("📁 OUTPUT FILES:")
    print(f"   • U_2024-01-01-00.nc, U_2024-01-01-01.nc, U_2024-01-01-02.nc, etc.")
    print(f"   • V_2024-01-01-00.nc, V_2024-01-01-01.nc, V_2024-01-01-02.nc, etc.")
    print(f"   • W_2024-01-01-00.nc, W_2024-01-01-01.nc, W_2024-01-01-02.nc, etc.")
    print(f"   • T_2024-01-01-00.nc, T_2024-01-01-01.nc, T_2024-01-01-02.nc, etc.")
    print(f"   • S_2024-01-01-00.nc, S_2024-01-01-01.nc, S_2024-01-01-02.nc, etc.")
    print(f"   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
    print(f"   • settings.json")
    print()
    print("🧪 Test PlasticParcels integration:")
    print("   conda activate plasticparcels")
    print("   python test_mobile_nemo_proper.py")

    return output_dir, settings_file

if __name__ == "__main__":
    convert_mobile_schism_proper()
