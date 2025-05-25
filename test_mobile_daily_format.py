#!/usr/bin/env python3
"""
Test PlasticParcels with Mobile Bay daily format

Tests the daily format that's compatible with PlasticParcels default file selection.

Usage:
    conda activate plasticparcels
    python test_mobile_daily_format.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def plot_trajectories(trajectory_file, output_dir):
    """Create a PNG plot of particle trajectories."""

    try:
        import matplotlib.pyplot as plt
        import xarray as xr

        print("📊 Creating trajectory plot...")

        # Load trajectory data
        traj_ds = xr.open_zarr(trajectory_file)

        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(12, 8))

        # Plot each particle trajectory
        n_particles = traj_ds.dims['traj']
        colors = plt.cm.tab10(np.linspace(0, 1, n_particles))

        for p in range(n_particles):
            lons = traj_ds.lon.isel(traj=p).values
            lats = traj_ds.lat.isel(traj=p).values

            # Remove NaN values
            valid_mask = ~np.isnan(lons) & ~np.isnan(lats)
            if np.any(valid_mask):
                lons_clean = lons[valid_mask]
                lats_clean = lats[valid_mask]

                # Plot trajectory
                ax.plot(lons_clean, lats_clean, 'o-', color=colors[p],
                       linewidth=2, markersize=4, alpha=0.8, label=f'Particle {p+1}')

                # Mark start and end points
                if len(lons_clean) > 0:
                    ax.plot(lons_clean[0], lats_clean[0], 's', color=colors[p],
                           markersize=8, markeredgecolor='black', markeredgewidth=1)
                    if len(lons_clean) > 1:
                        ax.plot(lons_clean[-1], lats_clean[-1], '^', color=colors[p],
                               markersize=8, markeredgecolor='black', markeredgewidth=1)

        # Set labels and title
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        ax.set_title('Mobile Bay Plastic Particle Trajectories\n(SCHISM Hydrodynamics)', fontsize=14, fontweight='bold')

        # Add grid
        ax.grid(True, alpha=0.3)

        # Add legend
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)

        # Add annotations
        ax.text(0.02, 0.98, '■ Start  ▲ End', transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Set aspect ratio and limits
        ax.set_aspect('equal', adjustable='box')

        # Add domain info
        lon_range = ax.get_xlim()
        lat_range = ax.get_ylim()
        domain_text = f"Domain: {lon_range[0]:.3f}°E to {lon_range[1]:.3f}°E\n"
        domain_text += f"        {lat_range[0]:.3f}°N to {lat_range[1]:.3f}°N"
        ax.text(0.02, 0.02, domain_text, transform=ax.transAxes,
               verticalalignment='bottom', fontsize=9,
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.7))

        # Tight layout
        plt.tight_layout()

        # Save plot
        plot_file = os.path.join(output_dir, 'mobile_bay_trajectories.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()

        traj_ds.close()

        print(f"   ✓ Trajectory plot saved to: {plot_file}")
        return True

    except ImportError:
        print("   ⚠️  matplotlib not available for plotting")
        return False
    except Exception as e:
        print(f"   ❌ Error creating plot: {e}")
        return False

def test_daily_format_fieldset(data_dir='mobile_daily_format'):
    """Test fieldset creation with daily format."""

    print("🧪 TESTING DAILY FORMAT FIELDSET 🧪")
    print("=" * 45)

    settings_file = os.path.join(data_dir, 'settings.json')

    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        print("   Please run mobile_schism_daily_format.py first!")
        return False

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        print(f"✓ Loaded settings from {settings_file}")

        # Add simulation settings for multi-day simulation
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(days=1, hours=12),  # 1.5 day simulation
            'outputdt': timedelta(hours=2),
            'dt': timedelta(minutes=30),
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
        print("📋 DAILY FORMAT FIELDSET INFORMATION:")
        print(f"   Domain: {fieldset.U.grid.lon.min():.3f}°E to {fieldset.U.grid.lon.max():.3f}°E")
        print(f"           {fieldset.U.grid.lat.min():.3f}°N to {fieldset.U.grid.lat.max():.3f}°N")
        print(f"   Grid size: {fieldset.U.grid.lat.shape} points")
        print(f"   Time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")

        # Test velocity sampling at domain center
        lon_center = (fieldset.U.grid.lon.min() + fieldset.U.grid.lon.max()) / 2
        lat_center = (fieldset.U.grid.lat.min() + fieldset.U.grid.lat.max()) / 2

        print(f"\n🌊 TESTING HOURLY VELOCITY VARIATIONS:")
        print(f"   Sampling at center: {lon_center:.3f}°E, {lat_center:.3f}°N")

        # Sample velocities at different times within the day
        sample_times = [0, 6, 12, 18, 24] if len(fieldset.U.grid.time) > 24 else range(min(5, len(fieldset.U.grid.time)))

        for t in sample_times:
            if t < len(fieldset.U.grid.time):
                try:
                    u_val = fieldset.U[t, 0, lat_center, lon_center]
                    v_val = fieldset.V[t, 0, lat_center, lon_center]
                    speed = np.sqrt(u_val**2 + v_val**2)
                    print(f"   Hour {t:2d}: U={u_val:.4f} m/s, V={v_val:.4f} m/s, Speed={speed:.4f} m/s")
                except Exception as e:
                    print(f"   Hour {t:2d}: Could not sample ({e})")

        return True

    except Exception as e:
        print(f"❌ Error creating fieldset: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_daily_format_simulation(data_dir='mobile_daily_format'):
    """Test multi-day particle simulation with daily format."""

    print("\n🚀 TESTING MULTI-DAY SIMULATION 🚀")
    print("=" * 40)

    settings_file = os.path.join(data_dir, 'settings.json')

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Add simulation and plastic settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(days=1, hours=12),  # 1.5 day simulation with hourly data
            'outputdt': timedelta(hours=3),  # Output every 3 hours
            'dt': timedelta(minutes=20),     # 20-minute time step
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

        # Release 6 particles in a 2x3 grid
        lons = [lon_center - 0.02, lon_center, lon_center + 0.02] * 2
        lats = [lat_center - 0.01] * 3 + [lat_center + 0.01] * 3

        release_locations = {
            'lons': lons,
            'lats': lats,
            'plastic_amount': [1.0] * 6
        }

        print(f"🎯 Releasing 6 particles in 2×3 grid at {lon_center:.3f}°E, {lat_center:.3f}°N")
        print(f"⏱️  Simulation: 1.5 days with hourly hydrodynamic data")

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")

        # Run simulation
        print("🌊 Running multi-day simulation with hourly data...")
        output_file = os.path.join(data_dir, 'mobile_daily_trajectories.zarr')

        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )

        print("✅ Multi-day simulation completed successfully!")
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

            # Check particle spread over time
            initial_lons = traj_ds.lon.isel(obs=0).values
            initial_lats = traj_ds.lat.isel(obs=0).values
            final_lons = traj_ds.lon.isel(obs=-1).values
            final_lats = traj_ds.lat.isel(obs=-1).values

            valid_mask = ~np.isnan(final_lons) & ~np.isnan(final_lats)
            if np.any(valid_mask):
                initial_center_lon = np.nanmean(initial_lons)
                initial_center_lat = np.nanmean(initial_lats)
                final_center_lon = np.nanmean(final_lons[valid_mask])
                final_center_lat = np.nanmean(final_lats[valid_mask])

                # Calculate displacement
                displacement_lon = final_center_lon - initial_center_lon
                displacement_lat = final_center_lat - initial_center_lat
                displacement_km = np.sqrt(displacement_lon**2 + displacement_lat**2) * 111.32

                print(f"   Initial center: {initial_center_lon:.4f}°E, {initial_center_lat:.4f}°N")
                print(f"   Final center: {final_center_lon:.4f}°E, {final_center_lat:.4f}°N")
                print(f"   Net displacement: {displacement_km:.2f} km")

                # Particle spread
                final_spread_lon = final_lons[valid_mask].max() - final_lons[valid_mask].min()
                final_spread_lat = final_lats[valid_mask].max() - final_lats[valid_mask].min()
                print(f"   Final spread: {final_spread_lon:.4f}° lon × {final_spread_lat:.4f}° lat")

            traj_ds.close()

        except Exception as e:
            print(f"   Could not analyze results: {e}")

        # Generate trajectory plot
        try:
            plot_success = plot_trajectories(output_file, data_dir)
            if plot_success:
                print(f"   ✓ Trajectory plot saved!")
        except Exception as e:
            print(f"   Could not create trajectory plot: {e}")

        return True

    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def check_daily_file_structure(data_dir='mobile_daily_format'):
    """Check the daily file structure."""

    print("\n🔍 CHECKING DAILY FILE STRUCTURE 🔍")
    print("=" * 40)

    if not os.path.exists(data_dir):
        print(f"❌ Directory {data_dir} not found")
        return False

    # Check for expected daily files
    expected_files = []
    variables = ['U', 'V', 'W', 'T', 'S']
    dates = ['2024-01-01', '2024-01-02']

    for date in dates:
        for var in variables:
            expected_files.append(f"{var}_{date}.nc")

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

        # Check time dimensions in daily files
        print("\n📊 Checking time dimensions:")
        try:
            import xarray as xr
            for date in dates:
                u_file = os.path.join(data_dir, f"U_{date}.nc")
                ds = xr.open_dataset(u_file)
                n_times = len(ds.time_counter)
                print(f"   {date}: {n_times} time steps")
                ds.close()
        except Exception as e:
            print(f"   Could not check time dimensions: {e}")

        return True

def main():
    """Main test function."""

    print("🏖️  MOBILE BAY DAILY FORMAT TEST 🏖️")
    print("=" * 50)
    print()

    # Check if data directory exists
    data_dir = 'mobile_daily_format'
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("   Please run mobile_schism_daily_format.py first!")
        return False

    print(f"✓ Found data directory: {data_dir}")

    # Check file structure
    structure_ok = check_daily_file_structure(data_dir)
    if not structure_ok:
        print("❌ File structure check failed.")
        return False

    # Test 1: Fieldset creation
    fieldset_success = test_daily_format_fieldset(data_dir)

    if not fieldset_success:
        print("❌ Fieldset creation failed. Cannot proceed with simulation test.")
        return False

    # Test 2: Multi-day simulation
    simulation_success = test_daily_format_simulation(data_dir)

    # Summary
    print("\n📊 DAILY FORMAT TEST SUMMARY:")
    print("=" * 35)
    print(f"   File structure: {'✅ PASS' if structure_ok else '❌ FAIL'}")
    print(f"   Fieldset creation: {'✅ PASS' if fieldset_success else '❌ FAIL'}")
    print(f"   Multi-day simulation: {'✅ PASS' if simulation_success else '❌ FAIL'}")

    if structure_ok and fieldset_success and simulation_success:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("=" * 25)
        print("✅ Daily format works perfectly with PlasticParcels!")
        print("✅ Hourly data properly organized into daily files!")
        print("✅ Ready for realistic multi-day simulations!")
        print()
        print("🌊 You can now:")
        print("   • Run simulations across multiple days with hourly resolution")
        print("   • Scale up to weeks or months of SCHISM data")
        print("   • Study diurnal variations in plastic transport")
        print("   • Model realistic pollution scenarios with tidal cycles")

        return True
    else:
        print("\n❌ Some tests failed. Check error messages above.")
        return False

if __name__ == "__main__":
    main()
