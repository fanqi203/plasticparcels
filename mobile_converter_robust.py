#!/usr/bin/env python3
"""
Robust Mobile Bay SCHISM to PlasticParcels converter

Specifically designed for Mobile Bay SCHISM data structure.
Handles the exact format of out2d_*.nc files.

Usage:
    conda activate plasticparcels
    python mobile_converter_robust.py
"""

import os
import glob
import re
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json

def convert_mobile_schism_robust():
    """Robust converter for Mobile Bay SCHISM data."""

    print("🌊 ROBUST MOBILE BAY SCHISM CONVERTER 🌊")
    print("=" * 50)

    # Configuration
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    output_dir = 'mobile_robust'
    target_resolution = 0.01  # 1.1 km resolution

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get first 5 sequential files
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')

    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0

    all_files = sorted(all_files, key=extract_number)
    test_files = all_files[:5]

    print(f"Found {len(all_files)} total SCHISM files")
    print(f"Processing first 5 sequential files:")
    for i, f in enumerate(test_files):
        print(f"  {i+1}. {os.path.basename(f)}")
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

    # Check data structure
    print(f"\nData structure check:")
    for var in ['depthAverageVelX', 'depthAverageVelY', 'elevation']:
        if var in ds0.variables:
            shape = ds0[var].shape
            dims = ds0[var].dims
            print(f"  {var}: {shape} {dims}")

    ds0.close()

    # Create target regular grid
    print(f"\n🎯 Creating target grid (resolution: {target_resolution}°)...")
    lon_min, lon_max = lons.min(), lons.max()
    lat_min, lat_max = lats.min(), lats.max()

    target_lons = np.arange(lon_min, lon_max + target_resolution, target_resolution)
    target_lats = np.arange(lat_min, lat_max + target_resolution, target_resolution)
    target_lon_2d, target_lat_2d = np.meshgrid(target_lons, target_lats)

    print(f"Target grid: {len(target_lats)} × {len(target_lons)} = {len(target_lats) * len(target_lons):,} points")

    # Process time series
    print(f"\n🔄 Processing {len(test_files)} time steps...")

    n_times = len(test_files)
    grid_shape = (n_times, len(target_lats), len(target_lons))

    # Initialize arrays
    u_data = np.zeros(grid_shape)
    v_data = np.zeros(grid_shape)
    w_data = np.zeros(grid_shape)  # Always zero for 2D
    elev_data = np.zeros(grid_shape)

    for t, file_path in enumerate(test_files):
        print(f"  Processing {os.path.basename(file_path)} ({t+1}/{n_times})")

        ds = xr.open_dataset(file_path)

        # Extract velocity and elevation data - handle different shapes
        try:
            # Try different indexing approaches
            if len(ds['depthAverageVelX'].shape) == 2:
                # Shape: (time, nodes)
                u_vals = ds['depthAverageVelX'][0, :].values  # First (and likely only) time step
                v_vals = ds['depthAverageVelY'][0, :].values
                elev_vals = ds['elevation'][0, :].values
            else:
                # Shape: (nodes,) - single time step
                u_vals = ds['depthAverageVelX'].values
                v_vals = ds['depthAverageVelY'].values
                elev_vals = ds['elevation'].values

            print(f"    Data shapes: U={u_vals.shape}, V={v_vals.shape}, elev={elev_vals.shape}")

        except Exception as e:
            print(f"    Error extracting data: {e}")
            print(f"    Trying alternative approach...")
            u_vals = ds['depthAverageVelX'].values.flatten()
            v_vals = ds['depthAverageVelY'].values.flatten()
            elev_vals = ds['elevation'].values.flatten()

        # Regrid to regular grid
        for var_name, vals, output_array in [
            ('U', u_vals, u_data),
            ('V', v_vals, v_data),
            ('elevation', elev_vals, elev_data)
        ]:
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

            output_array[t, :, :] = regridded

        ds.close()

    # Create bathymetry
    print("  Creating bathymetry...")
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

    # Save NEMO format files
    print(f"\n💾 Saving NEMO-compatible files...")

    # Time coordinate (hours)
    time_hours = np.arange(n_times, dtype=float)

    # Coordinate variables
    coords = {
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'time_counter': ('time_counter', time_hours)
    }

    # Save each variable
    variables = {
        'U': ('vozocrtx', u_data),
        'V': ('vomecrty', v_data),
        'W': ('vovecrtz', w_data),
        'T': ('votemper', elev_data),  # Use elevation as temperature proxy
        'S': ('vosaline', np.full_like(u_data, 35.0))  # Constant salinity
    }

    for var_letter, (nemo_var, data) in variables.items():
        ds = xr.Dataset({
            nemo_var: (['time_counter', 'y', 'x'], data)
        }, coords=coords)

        ds.attrs.update({
            'Conventions': 'CF-1.0',
            'source': 'Mobile Bay SCHISM regridded to NEMO format',
            'institution': 'PlasticParcels Regridder'
        })

        # Save with date-based naming for PlasticParcels compatibility
        filename = f"{var_letter}_2024-01-01.nc"
        filepath = os.path.join(output_dir, filename)
        ds.to_netcdf(filepath)
        print(f"   ✓ Saved {filepath}")

    # Save mesh file
    mesh_ds = xr.Dataset({
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'glamf': (['y', 'x'], target_lon_2d),  # Keep both for compatibility
        'gphif': (['y', 'x'], target_lat_2d),
    })
    mesh_file = os.path.join(output_dir, 'ocean_mesh_hgr.nc')
    mesh_ds.to_netcdf(mesh_file)
    print(f"   ✓ Saved {mesh_file}")

    # Save bathymetry file
    mbathy = np.ones_like(bathy_regridded, dtype=int)
    mbathy[bathy_regridded <= 0] = 0

    bathy_ds = xr.Dataset({
        'mbathy': (['time_counter', 'y', 'x'], mbathy[np.newaxis, :, :]),
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

    settings_file = os.path.join(output_dir, 'timeseries_settings.json')
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"   ✓ Saved {settings_file}")

    print(f"\n🎉 CONVERSION COMPLETED! 🎉")
    print("=" * 40)
    print(f"✅ Processed {n_times} time steps")
    print(f"✅ Created NEMO-compatible files in '{output_dir}/'")
    print(f"✅ Grid resolution: {target_resolution}° ({target_resolution * 111.32:.1f} km)")
    print()
    print("📁 OUTPUT FILES:")
    print(f"   • U_2024-01-01.nc, V_2024-01-01.nc, W_2024-01-01.nc")
    print(f"   • T_2024-01-01.nc, S_2024-01-01.nc")
    print(f"   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
    print(f"   • timeseries_settings.json")
    print()
    print("🧪 Test PlasticParcels integration:")
    print("   conda activate plasticparcels")
    print("   python test_mobile_plasticparcels_robust.py")

    return output_dir, settings_file

if __name__ == "__main__":
    convert_mobile_schism_robust()
