#!/usr/bin/env python3
"""
Mobile SCHISM to NEMO converter
Simplified converter for the mobile bay SCHISM data
"""

import os
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta
import glob

def convert_mobile_schism_to_nemo():
    """Convert mobile bay SCHISM data to NEMO format."""

    print("🌊 MOBILE BAY SCHISM TO NEMO CONVERTER 🌊")
    print("=" * 50)

    # Configuration
    schism_dir = "/anvil/projects/x-ees240085/sbao/mobile/outputs"
    output_dir = "mobile"
    target_resolution = 0.01  # 1.1 km resolution

    # Create output directory
    os.makedirs(output_dir, exist_ok=True)

    # Get first few files for testing (sequential order)
    pattern = os.path.join(schism_dir, "out2d_*.nc")
    all_files = glob.glob(pattern)

    # Sort files by the numeric part to get sequential order (1, 2, 3, 4, 5...)
    def extract_number(filename):
        import re
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0

    all_files = sorted(all_files, key=extract_number)

    print(f"Found {len(all_files)} SCHISM files")

    # Use first 5 files for testing
    test_files = all_files[:5]
    print(f"Processing first {len(test_files)} files for testing:")
    for f in test_files:
        print(f"  - {os.path.basename(f)}")

    # Load first file to get grid structure
    print("\n📥 Loading SCHISM grid structure...")
    ds0 = xr.open_dataset(test_files[0])

    print("Variables in SCHISM file:")
    for var in ds0.variables:
        print(f"  - {var}: {ds0[var].shape}")

    # Extract coordinates
    lons = ds0['SCHISM_hgrid_node_x'].values
    lats = ds0['SCHISM_hgrid_node_y'].values
    depths = ds0['depth'].values

    print(f"\nGrid info:")
    print(f"  Nodes: {len(lons):,}")
    print(f"  Longitude range: {lons.min():.3f} to {lons.max():.3f}")
    print(f"  Latitude range: {lats.min():.3f} to {lats.max():.3f}")
    print(f"  Depth range: {depths.min():.1f} to {depths.max():.1f} m")

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

        # Extract velocity and elevation data (remove time dimension)
        u_vals = ds['depthAverageVelX'].values[0, :]  # Remove time dimension
        v_vals = ds['depthAverageVelY'].values[0, :]  # Remove time dimension
        elev_vals = ds['elevation'].values[0, :]      # Remove time dimension

        # Regrid to regular grid
        for var_name, vals, output_array in [
            ('U', u_vals, u_data),
            ('V', v_vals, v_data),
            ('elevation', elev_vals, elev_data)
        ]:
            regridded = griddata(
                points=np.column_stack([lons, lats]),
                values=vals,
                xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
                method='linear',
                fill_value=0.0
            ).reshape(target_lon_2d.shape)

            output_array[t, :, :] = regridded

        ds.close()

    # Create bathymetry
    print("  Creating bathymetry...")
    bathy_regridded = griddata(
        points=np.column_stack([lons, lats]),
        values=depths,
        xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
        method='linear',
        fill_value=0.0
    ).reshape(target_lon_2d.shape)

    ds0.close()

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

    # Save mesh file with correct variable names
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
            "filename_style": "mobile",
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

    settings_file = os.path.join(output_dir, 'mobile_settings.json')
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
    print(f"   • mobile_settings.json")

    return output_dir, settings_file

def test_plasticparcels_simulation(output_dir, settings_file):
    """Test PlasticParcels simulation with converted data."""
    print(f"\n🧪 TESTING PLASTICPARCELS SIMULATION 🧪")
    print("=" * 50)

    try:
        import plasticparcels
        from plasticparcels.constructors import create_hydrodynamic_fieldset, create_particleset
        import parcels

        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        print("✓ Loaded settings file")

        # Add required simulation settings
        from datetime import datetime, timedelta
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=2),
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=20),
        }

        # Add plastic type settings
        settings['plastictype'] = {
            'wind_coefficient': 0.0,
            'plastic_diameter': 0.001,  # 1mm
            'plastic_density': 1028.0,  # kg/m³
        }

        # Create fieldset
        print("📊 Creating fieldset...")
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✓ Fieldset created successfully")

        # Set up particle release locations
        lon_min = fieldset.U.grid.lon.min()
        lon_max = fieldset.U.grid.lon.max()
        lat_min = fieldset.U.grid.lat.min()
        lat_max = fieldset.U.grid.lat.max()

        # Release particles in center of domain
        lon_center = (lon_min + lon_max) / 2
        lat_center = (lat_min + lat_max) / 2

        release_locations = {
            'lons': [lon_center - 0.01, lon_center + 0.01, lon_center - 0.01, lon_center + 0.01],
            'lats': [lat_center - 0.01, lat_center - 0.01, lat_center + 0.01, lat_center + 0.01],
            'plastic_amount': [1.0, 1.0, 1.0, 1.0]
        }

        print(f"🎯 Particle release:")
        print(f"   Location: {lon_center:.3f}°E, {lat_center:.3f}°N")
        print(f"   Particles: 4")
        print(f"   Duration: 2 hours")

        # Create particle set
        print("� Creating particle set...")
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")

        # Run simulation
        print("🚀 Running simulation...")
        output_file = os.path.join(output_dir, 'mobile_test_trajectories.zarr')
        pset.execute(parcels.AdvectionRK4,
                    runtime=settings['simulation']['runtime'],
                    dt=settings['simulation']['dt'],
                    output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt']))

        print("✓ Simulation completed successfully")
        print(f"✓ Output saved to: {output_file}")

        # Create simple plot
        print("📈 Creating trajectory plot...")
        fig, ax = plt.subplots(figsize=(10, 8))

        # Plot trajectories
        for i in range(num_particles):
            particle_data = simulation.output_file.variables
            lons = particle_data['lon'][i, :]
            lats = particle_data['lat'][i, :]

            # Remove NaN values
            valid_mask = ~np.isnan(lons) & ~np.isnan(lats)
            if np.any(valid_mask):
                ax.plot(lons[valid_mask], lats[valid_mask], 'o-',
                       label=f'Particle {i+1}', linewidth=2, markersize=4)

        ax.set_xlabel('Longitude (°E)')
        ax.set_ylabel('Latitude (°N)')
        ax.set_title('Mobile Bay Plastic Particle Trajectories\n(SCHISM → NEMO → PlasticParcels)')
        ax.legend()
        ax.grid(True, alpha=0.3)

        plot_file = os.path.join(output_dir, 'mobile_trajectories.png')
        plt.savefig(plot_file, dpi=150, bbox_inches='tight')
        plt.close()
        print(f"   ✓ Saved {plot_file}")

        print(f"\n🎉 SIMULATION TEST SUCCESSFUL! 🎉")
        print("=" * 45)
        print("✅ SCHISM data successfully converted to NEMO format")
        print("✅ PlasticParcels simulation ran without errors")
        print("✅ Trajectory plot created")
        print()
        print("🌊 Ready for full-scale Mobile Bay plastic pollution modeling!")

        return True

    except Exception as e:
        print(f"❌ Simulation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    # Convert SCHISM data
    output_dir, settings_file = convert_mobile_schism_to_nemo()

    print(f"\n🎯 CONVERSION COMPLETED!")
    print(f"Next step: Test with PlasticParcels")
    print(f"Run: conda activate plasticparcels && python -c \"from mobile_schism_converter import test_plasticparcels_simulation; test_plasticparcels_simulation('{output_dir}', '{settings_file}')\"")

    # Uncomment to run simulation test automatically:
    # test_plasticparcels_simulation(output_dir, settings_file)
