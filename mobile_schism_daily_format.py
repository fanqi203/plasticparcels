#!/usr/bin/env python3
"""
Mobile Bay SCHISM to NEMO converter - Daily files with multiple time steps

Creates daily files compatible with PlasticParcels default date extraction:
- U_2024-01-01.nc (contains multiple hourly time steps)
- U_2024-01-02.nc (contains next day's hourly time steps)
- etc.

This approach works with PlasticParcels' default select_files function.

Usage:
    conda activate plasticparcels
    python mobile_schism_daily_format.py
"""

import os
import glob
import re
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta

def convert_mobile_schism_daily():
    """Convert Mobile Bay SCHISM to daily NEMO format files."""

    print("🌊 MOBILE BAY SCHISM TO DAILY NEMO FORMAT 🌊")
    print("=" * 55)

    # Configuration
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    output_dir = 'mobile_daily_format'
    target_resolution = 0.01  # 1.1 km resolution
    hours_per_day = 6  # Use 6 hours per day for testing (much faster)

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get SCHISM files
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')

    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0

    all_files = sorted(all_files, key=extract_number)

    # Process first 12 files (2 "days" worth, 6 hours each for testing)
    test_files = all_files[:12]

    print(f"Found {len(all_files)} total SCHISM files")
    print(f"Processing first {len(test_files)} files (2 test days worth)")
    print(f"Creating daily files with {hours_per_day} time steps each (for testing)")
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

    # Process files in daily chunks
    print(f"\n🔄 Processing files in daily chunks...")

    base_date = datetime(2024, 1, 1)
    n_days = len(test_files) // hours_per_day

    for day in range(n_days):
        day_date = base_date + timedelta(days=day)
        date_str = day_date.strftime('%Y-%m-%d')

        print(f"\n  Day {day+1}: {date_str} (hours {day*hours_per_day} to {(day+1)*hours_per_day-1})")

        # Get files for this day
        day_files = test_files[day*hours_per_day:(day+1)*hours_per_day]

        # Initialize arrays for this day
        n_hours = len(day_files)
        grid_shape = (n_hours, len(target_lats), len(target_lons))

        u_data = np.zeros(grid_shape)
        v_data = np.zeros(grid_shape)
        w_data = np.zeros(grid_shape)  # Always zero for 2D
        elev_data = np.zeros(grid_shape)

        # Process each hour of this day
        for h, file_path in enumerate(day_files):
            print(f"    Hour {h:02d}: {os.path.basename(file_path)}")

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
                print(f"      Error extracting data: {e}")
                u_vals = ds['depthAverageVelX'].values.flatten()
                v_vals = ds['depthAverageVelY'].values.flatten()
                elev_vals = ds['elevation'].values.flatten()

            ds.close()

            # Regrid each variable for this hour
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

        # Create time coordinate for this day (hours since simulation start)
        # Make time continuous across all files
        time_hours = np.arange(day * hours_per_day, (day + 1) * hours_per_day, dtype=float)

        # Create coordinate variables (no depth for 2D surface data)
        coords = {
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
            'time_counter': ('time_counter', time_hours),
            'x': ('x', np.arange(target_lon_2d.shape[1])),
            'y': ('y', np.arange(target_lon_2d.shape[0]))
        }

        # Save daily files for each variable
        variables = {
            'U': ('vozocrtx', u_data),
            'V': ('vomecrty', v_data),
            'W': ('vovecrtz', w_data),
            'T': ('votemper', elev_data),
            'S': ('vosaline', np.full_like(u_data, 35.0))
        }

        for var_letter, (nemo_var, data) in variables.items():
            # Create dataset with multiple time steps for this day
            # Shape: (time_counter, y, x) - no depth dimension for 2D surface data

            ds = xr.Dataset({
                nemo_var: (['time_counter', 'y', 'x'], data)
            }, coords=coords)

            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': f'Mobile Bay SCHISM {date_str} regridded to NEMO format',
                'institution': 'PlasticParcels Regridder'
            })

            # Save with PlasticParcels-compatible naming
            filename = f"{var_letter}_{date_str}.nc"
            filepath = os.path.join(output_dir, filename)
            ds.to_netcdf(filepath)

            ds.close()

        print(f"    ✓ Created daily files: {{U,V,W,T,S}}_{date_str}.nc")

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

    print(f"\n🎉 CONVERSION COMPLETED! 🎉")
    print("=" * 40)
    print(f"✅ Processed {len(test_files)} hourly files (TESTING)")
    print(f"✅ Created {n_days} daily files with {hours_per_day} time steps each")
    print(f"✅ Grid resolution: {target_resolution}° ({target_resolution * 111.32:.1f} km)")
    print()
    print("📁 OUTPUT FILES (TESTING FORMAT):")
    print(f"   • U_2024-01-01.nc, U_2024-01-02.nc (each with {hours_per_day} time steps)")
    print(f"   • V_2024-01-01.nc, V_2024-01-02.nc (each with {hours_per_day} time steps)")
    print(f"   • W_2024-01-01.nc, W_2024-01-02.nc (each with {hours_per_day} time steps)")
    print(f"   • T_2024-01-01.nc, T_2024-01-02.nc (each with {hours_per_day} time steps)")
    print(f"   • S_2024-01-01.nc, S_2024-01-02.nc (each with {hours_per_day} time steps)")
    print(f"   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
    print(f"   • settings.json")
    print()
    print("🧪 Test PlasticParcels integration:")
    print("   conda activate plasticparcels")
    print("   python test_mobile_daily_format.py")

    return output_dir, settings_file

if __name__ == "__main__":
    convert_mobile_schism_daily()
