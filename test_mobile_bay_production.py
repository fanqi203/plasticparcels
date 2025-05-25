#!/usr/bin/env python3
"""
Production test script for Mobile Bay SCHISM to PlasticParcels integration

Validates the converted data and runs a sample simulation to ensure
the production converter is working correctly.

Usage:
    conda activate plasticparcels
    python test_mobile_bay_production.py [data_directory]
"""

import sys
import os
import json
import numpy as np
from datetime import datetime, timedelta
import argparse

def test_file_structure(data_dir):
    """Test that all required files exist."""

    print("🔍 TESTING FILE STRUCTURE")
    print("=" * 30)

    required_files = [
        'settings.json',
        'ocean_mesh_hgr.nc',
        'bathymetry_mesh_zgr.nc'
    ]

    # Check for at least one day of data files
    variables = ['U', 'V', 'W', 'T', 'S']
    for var in variables:
        required_files.append(f'{var}_2024-01-01.nc')

    missing_files = []
    for filename in required_files:
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            print(f"   ✓ {filename}")
        else:
            print(f"   ❌ {filename}")
            missing_files.append(filename)

    if missing_files:
        print(f"\n❌ Missing {len(missing_files)} required files")
        return False
    else:
        print(f"\n✅ All required files found!")
        return True

def test_plasticparcels_integration(data_dir):
    """Test PlasticParcels fieldset creation."""

    print("\n🧪 TESTING PLASTICPARCELS INTEGRATION")
    print("=" * 40)

    settings_file = os.path.join(data_dir, 'settings.json')

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        print("✓ Settings loaded successfully")

        # Add minimal simulation settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=6),
            'outputdt': timedelta(hours=2),
            'dt': timedelta(minutes=30),
        }

        # Import PlasticParcels
        from plasticparcels.constructors import create_hydrodynamic_fieldset
        print("✓ PlasticParcels imported successfully")

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✓ Fieldset created successfully")

        # Check fieldset properties
        print(f"\n📋 FIELDSET PROPERTIES:")
        print(f"   Domain: {fieldset.U.grid.lon.min():.3f}°E to {fieldset.U.grid.lon.max():.3f}°E")
        print(f"           {fieldset.U.grid.lat.min():.3f}°N to {fieldset.U.grid.lat.max():.3f}°N")
        print(f"   Grid size: {fieldset.U.grid.lat.shape}")
        print(f"   Time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")

        return True

    except Exception as e:
        print(f"❌ PlasticParcels integration failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_sample_simulation(data_dir):
    """Run a minimal particle simulation."""

    print("\n🚀 TESTING SAMPLE SIMULATION")
    print("=" * 35)

    # Set matplotlib backend for headless servers
    try:
        import matplotlib
        matplotlib.use('Agg')
    except ImportError:
        pass  # matplotlib not available

    settings_file = os.path.join(data_dir, 'settings.json')

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Add simulation settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=4),
            'outputdt': timedelta(hours=2),
            'dt': timedelta(minutes=30),
        }

        settings['plastictype'] = {
            'wind_coefficient': 0.0,
            'plastic_diameter': 0.001,
            'plastic_density': 1028.0,
        }

        # Import required modules
        from plasticparcels.constructors import create_hydrodynamic_fieldset, create_particleset
        import parcels

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✓ Fieldset created")

        # Set up minimal particle release
        lon_center = (fieldset.U.grid.lon.min() + fieldset.U.grid.lon.max()) / 2
        lat_center = (fieldset.U.grid.lat.min() + fieldset.U.grid.lat.max()) / 2

        release_locations = {
            'lons': [lon_center],
            'lats': [lat_center],
            'plastic_amount': [1.0]
        }

        print(f"✓ Releasing 1 particle at {lon_center:.3f}°E, {lat_center:.3f}°N")

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particle")

        # Run simulation
        output_file = os.path.join(data_dir, 'test_trajectories.zarr')

        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )

        print("✓ Simulation completed successfully")
        print(f"✓ Test trajectories saved to: {output_file}")

        # Quick validation
        import xarray as xr
        traj_ds = xr.open_zarr(output_file)
        n_obs = traj_ds.dims['obs']
        final_lon = traj_ds.lon.isel(obs=-1).values[0]
        final_lat = traj_ds.lat.isel(obs=-1).values[0]
        traj_ds.close()

        print(f"✓ Particle tracked for {n_obs} time steps")
        print(f"✓ Final position: {final_lon:.4f}°E, {final_lat:.4f}°N")

        return True

    except Exception as e:
        print(f"❌ Sample simulation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""

    parser = argparse.ArgumentParser(
        description="Test Mobile Bay SCHISM to PlasticParcels production integration"
    )
    parser.add_argument(
        'data_dir',
        nargs='?',
        default='mobile_bay_production',
        help='Directory containing converted data (default: mobile_bay_production)'
    )

    args = parser.parse_args()

    print("🏖️  MOBILE BAY PRODUCTION INTEGRATION TEST 🏖️")
    print("=" * 60)
    print(f"Testing data directory: {args.data_dir}")
    print()

    if not os.path.exists(args.data_dir):
        print(f"❌ Data directory not found: {args.data_dir}")
        print("   Please run the converter first:")
        print(f"   python mobile_bay_schism_converter.py <schism_dir> {args.data_dir}")
        return False

    # Run tests
    tests = [
        ("File Structure", lambda: test_file_structure(args.data_dir)),
        ("PlasticParcels Integration", lambda: test_plasticparcels_integration(args.data_dir)),
        ("Sample Simulation", lambda: test_sample_simulation(args.data_dir))
    ]

    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results[test_name] = False

    # Summary
    print("\n📊 PRODUCTION TEST SUMMARY")
    print("=" * 30)

    all_passed = True
    for test_name, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False

    print()
    if all_passed:
        print("🎉 ALL TESTS PASSED! 🎉")
        print("=" * 25)
        print("✅ Mobile Bay integration is ready for production!")
        print("✅ You can now run realistic plastic pollution simulations!")
        print()
        print("🌊 Next steps:")
        print("   • Scale up to longer simulations (days/weeks)")
        print("   • Add more particles and release locations")
        print("   • Include additional physics (mixing, biofouling)")
        print("   • Validate against field observations")
        return True
    else:
        print("❌ SOME TESTS FAILED")
        print("=" * 20)
        print("Please check the error messages above and fix issues before production use.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
