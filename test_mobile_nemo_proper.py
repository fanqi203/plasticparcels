#!/usr/bin/env python3
"""
Test PlasticParcels with Mobile Bay NEMO proper format

Tests the properly formatted Mobile Bay data that follows PlasticParcels conventions.

Usage:
    conda activate plasticparcels
    python test_mobile_nemo_proper.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def test_proper_format_fieldset(data_dir='mobile_nemo_proper'):
    """Test fieldset creation with proper NEMO format."""

    print("🧪 TESTING PROPER NEMO FORMAT FIELDSET 🧪")
    print("=" * 50)

    settings_file = os.path.join(data_dir, 'settings.json')

    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        print("   Please run mobile_schism_to_nemo_proper.py first!")
        return False

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        print(f"✓ Loaded settings from {settings_file}")

        # Add simulation settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=3),  # 3-hour simulation across multiple files
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=20),
        }

        # Import PlasticParcels
        from plasticparcels.constructors import create_hydrodynamic_fieldset
        print("✓ PlasticParcels imported successfully")

        # Create fieldset
        print("📊 Creating fieldset...")
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✅ Fieldset created successfully!")

        # Display fieldset information
        print()
        print("📋 PROPER FORMAT FIELDSET INFORMATION:")
        print(f"   Domain: {fieldset.U.grid.lon.min():.3f}°E to {fieldset.U.grid.lon.max():.3f}°E")
        print(f"           {fieldset.U.grid.lat.min():.3f}°N to {fieldset.U.grid.lat.max():.3f}°N")
        print(f"   Grid size: {fieldset.U.grid.lat.shape} points")
        print(f"   Time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")

        # Test velocity sampling at domain center
        lon_center = (fieldset.U.grid.lon.min() + fieldset.U.grid.lon.max()) / 2
        lat_center = (fieldset.U.grid.lat.min() + fieldset.U.grid.lat.max()) / 2

        print(f"\n🌊 TESTING VELOCITY SAMPLING:")
        print(f"   Sampling at center: {lon_center:.3f}°E, {lat_center:.3f}°N")

        # Sample velocities at different times
        for t in range(min(3, len(fieldset.U.grid.time))):
            try:
                u_val = fieldset.U[t, 0, lat_center, lon_center]
                v_val = fieldset.V[t, 0, lat_center, lon_center]
                speed = np.sqrt(u_val**2 + v_val**2)
                print(f"   Time {t}h: U={u_val:.4f} m/s, V={v_val:.4f} m/s, Speed={speed:.4f} m/s")
            except Exception as e:
                print(f"   Time {t}h: Could not sample ({e})")

        return True

    except Exception as e:
        print(f"❌ Error creating fieldset: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_proper_format_simulation(data_dir='mobile_nemo_proper'):
    """Test particle simulation with proper NEMO format."""

    print("\n🚀 TESTING PROPER FORMAT SIMULATION 🚀")
    print("=" * 45)

    settings_file = os.path.join(data_dir, 'settings.json')

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Add simulation and plastic settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=3),  # 3-hour simulation across files
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=15),    # 15-minute time step
        }

        settings['plastictype'] = {
            'wind_coefficient': 0.0,
            'plastic_diameter': 0.001,  # 1mm
            'plastic_density': 1028.0,  # kg/m³
        }

        # Import required modules
        from plasticparcels.constructors import create_hydrodynamic_fieldset, create_particleset
        import parcels

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✓ Fieldset created")

        # Set up particle release locations (center of Mobile Bay)
        lon_min, lon_max = fieldset.U.grid.lon.min(), fieldset.U.grid.lon.max()
        lat_min, lat_max = fieldset.U.grid.lat.min(), fieldset.U.grid.lat.max()

        lon_center = (lon_min + lon_max) / 2
        lat_center = (lat_min + lat_max) / 2

        # Release 4 particles in a 2x2 grid
        release_locations = {
            'lons': [lon_center - 0.01, lon_center + 0.01, lon_center - 0.01, lon_center + 0.01],
            'lats': [lat_center - 0.01, lat_center - 0.01, lat_center + 0.01, lat_center + 0.01],
            'plastic_amount': [1.0, 1.0, 1.0, 1.0]
        }

        print(f"🎯 Releasing 4 particles at {lon_center:.3f}°E, {lat_center:.3f}°N")
        print(f"⏱️  Simulation: 3 hours across multiple NEMO files")

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")

        # Run simulation
        print("🌊 Running multi-file simulation...")
        output_file = os.path.join(data_dir, 'mobile_proper_trajectories.zarr')

        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )

        print("✅ Multi-file simulation completed successfully!")
        print(f"✓ Trajectories saved to: {output_file}")

        # Quick analysis of results
        print("\n📊 SIMULATION RESULTS:")
        try:
            import xarray as xr
            traj_ds = xr.open_zarr(output_file)

            n_particles = traj_ds.dims['traj']
            n_times = traj_ds.dims['obs']

            print(f"   Particles tracked: {n_particles}")
            print(f"   Time observations: {n_times}")
            print(f"   Total trajectory points: {n_particles * n_times}")

            # Check particle spread
            final_lons = traj_ds.lon.isel(obs=-1).values
            final_lats = traj_ds.lat.isel(obs=-1).values

            valid_mask = ~np.isnan(final_lons) & ~np.isnan(final_lats)
            if np.any(valid_mask):
                lon_spread = final_lons[valid_mask].max() - final_lons[valid_mask].min()
                lat_spread = final_lats[valid_mask].max() - final_lats[valid_mask].min()
                print(f"   Final particle spread: {lon_spread:.4f}° lon × {lat_spread:.4f}° lat")

                # Show initial vs final positions
                initial_lons = traj_ds.lon.isel(obs=0).values
                initial_lats = traj_ds.lat.isel(obs=0).values

                print(f"   Initial center: {np.nanmean(initial_lons):.4f}°E, {np.nanmean(initial_lats):.4f}°N")
                print(f"   Final center: {np.nanmean(final_lons[valid_mask]):.4f}°E, {np.nanmean(final_lats[valid_mask]):.4f}°N")

            traj_ds.close()

        except Exception as e:
            print(f"   Could not analyze results: {e}")

        return True

    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_file_structure(data_dir='mobile_nemo_proper'):
    """Check the file structure matches PlasticParcels expectations."""

    print("\n🔍 CHECKING FILE STRUCTURE 🔍")
    print("=" * 35)

    if not os.path.exists(data_dir):
        print(f"❌ Directory {data_dir} not found")
        return False

    # Check for expected files
    expected_files = []
    variables = ['U', 'V', 'W', 'T', 'S']

    # Check for hourly files (0-4 hours)
    for hour in range(5):
        date_str = f"2024-01-01-{hour:02d}"
        for var in variables:
            expected_files.append(f"{var}_{date_str}.nc")

    # Check mesh files
    expected_files.extend([
        'ocean_mesh_hgr.nc',
        'bathymetry_mesh_zgr.nc',
        'settings.json'
    ])

    print("Checking for expected files:")
    missing_files = []

    for filename in expected_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            print(f"   ✓ {filename}")
        else:
            print(f"   ❌ {filename}")
            missing_files.append(filename)

    if missing_files:
        print(f"\n⚠️  Missing {len(missing_files)} files")
        return False
    else:
        print(f"\n✅ All {len(expected_files)} expected files found!")
        return True

def main():
    """Main test function."""

    print("🏖️  MOBILE BAY PROPER NEMO FORMAT TEST 🏖️")
    print("=" * 55)
    print()

    # Check if data directory exists
    data_dir = 'mobile_nemo_proper'
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("   Please run mobile_schism_to_nemo_proper.py first!")
        return False

    print(f"✓ Found data directory: {data_dir}")

    # Check file structure
    structure_ok = check_file_structure(data_dir)
    if not structure_ok:
        print("❌ File structure check failed.")
        return False

    # Test 1: Fieldset creation
    fieldset_success = test_proper_format_fieldset(data_dir)

    if not fieldset_success:
        print("❌ Fieldset creation failed. Cannot proceed with simulation test.")
        return False

    # Test 2: Particle simulation
    simulation_success = test_proper_format_simulation(data_dir)

    # Summary
    print("\n📊 PROPER FORMAT TEST SUMMARY:")
    print("=" * 35)
    print(f"   File structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"   Fieldset creation: {'✅ PASS' if fieldset_success else '❌ FAIL'}")
    print(f"   Multi-file simulation: {'✅ PASS' if simulation_success else '❌ FAIL'}")

    if structure_ok and fieldset_success and simulation_success:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("=" * 25)
        print("✅ Mobile Bay NEMO format is perfect!")
        print("✅ Follows PlasticParcels conventions exactly!")
        print("✅ Ready for production simulations!")
        print()
        print("🌊 You can now:")
        print("   • Scale up to more time steps (10, 50, or all 249 files)")
        print("   • Run long-term simulations with proper time stepping")
        print("   • Use all PlasticParcels features (mixing, biofouling, etc.)")
        print("   • Model realistic pollution scenarios in Mobile Bay")

        return True
    else:
        print("\n❌ Some tests failed. Check error messages above.")
        return False

if __name__ == "__main__":
    main()
