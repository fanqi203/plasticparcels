#!/usr/bin/env python3
"""
Test diagnostic comparison between hourly and single-time datasets

Runs identical simulations on:
1. 6-hour dataset with full hourly resolution
2. 6-hour dataset with single time step (constant velocities)

This provides a fair comparison to see if hourly resolution matters.

Usage:
    conda activate plasticparcels
    python test_diagnostic_comparison.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def run_simulation(data_dir, sim_name, plot_suffix):
    """Run a simulation with given dataset."""

    print(f"\n🚀 RUNNING {sim_name.upper()} SIMULATION 🚀")
    print("=" * 50)

    settings_file = os.path.join(data_dir, 'settings.json')

    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        return None

    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)

        # Set appropriate time extrapolation based on dataset type
        if 'single' in data_dir.lower():
            settings['allow_time_extrapolation'] = True  # Required for constant velocity fields
            print(f"   Setting allow_time_extrapolation=True for {sim_name}")
        else:
            settings['allow_time_extrapolation'] = False  # Strict for varying fields
            print(f"   Setting allow_time_extrapolation=False for {sim_name}")

        # Add simulation settings (IDENTICAL for both)
        # Very conservative: run for 1 hour to stay well within dataset
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=4),      # 1-hour simulation
            'outputdt': timedelta(minutes=30),  # Output every 30 minutes
            'dt': timedelta(minutes=10),        # 10-minute time step
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

        # Check fieldset time information
        print(f"📋 FIELDSET INFO ({sim_name}):")
        print(f"   Available time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")
        print(f"   Time values: {fieldset.U.grid.time}")

        # Set up particle release locations (IDENTICAL for both)
        lon_min, lon_max = fieldset.U.grid.lon.min(), fieldset.U.grid.lon.max()
        lat_min, lat_max = fieldset.U.grid.lat.min(), fieldset.U.grid.lat.max()

        lon_center = (lon_min + lon_max) / 2
        lat_center = (lat_min + lat_max) / 2

        # Release 4 particles in a 2x2 grid (IDENTICAL for both)
        release_locations = {
            'lons': [lon_center - 0.01, lon_center + 0.01, lon_center - 0.01, lon_center + 0.01],
            'lats': [lat_center - 0.01, lat_center - 0.01, lat_center + 0.01, lat_center + 0.01],
            'plastic_amount': [1.0, 1.0, 1.0, 1.0]
        }

        print(f"🎯 Releasing 4 particles at {lon_center:.3f}°E, {lat_center:.3f}°N")

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")

        # Run simulation
        print(f"🌊 Running {sim_name} simulation...")
        output_file = os.path.join(data_dir, f'trajectories_{plot_suffix}.zarr')

        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )

        print(f"✅ {sim_name} simulation completed!")
        print(f"✓ Trajectories saved to: {output_file}")

        # Analyze results
        results = analyze_trajectories(output_file, sim_name)

        # Create plot
        plot_trajectories(output_file, data_dir, plot_suffix, sim_name)

        return results

    except Exception as e:
        print(f"❌ Error in {sim_name} simulation: {e}")
        import traceback
        traceback.print_exc()
        return None

def analyze_trajectories(trajectory_file, sim_name):
    """Analyze trajectory results."""

    try:
        import xarray as xr

        traj_ds = xr.open_zarr(trajectory_file)

        n_particles = traj_ds.dims['traj']
        n_times = traj_ds.dims['obs']

        # Calculate final positions
        final_lons = traj_ds.lon.isel(obs=-1).values
        final_lats = traj_ds.lat.isel(obs=-1).values

        # Calculate initial positions
        initial_lons = traj_ds.lon.isel(obs=0).values
        initial_lats = traj_ds.lat.isel(obs=0).values

        # Calculate displacements
        displacements = []
        for p in range(n_particles):
            if not (np.isnan(final_lons[p]) or np.isnan(final_lats[p])):
                dx = (final_lons[p] - initial_lons[p]) * 111.32 * np.cos(np.radians(initial_lats[p]))
                dy = (final_lats[p] - initial_lats[p]) * 111.32
                displacement = np.sqrt(dx**2 + dy**2)
                displacements.append(displacement)

        # Calculate center of mass displacement
        valid_mask = ~np.isnan(final_lons) & ~np.isnan(final_lats)
        if np.any(valid_mask):
            initial_center_lon = np.nanmean(initial_lons)
            initial_center_lat = np.nanmean(initial_lats)
            final_center_lon = np.nanmean(final_lons[valid_mask])
            final_center_lat = np.nanmean(final_lats[valid_mask])

            center_dx = (final_center_lon - initial_center_lon) * 111.32 * np.cos(np.radians(initial_center_lat))
            center_dy = (final_center_lat - initial_center_lat) * 111.32
            center_displacement = np.sqrt(center_dx**2 + center_dy**2)
        else:
            center_displacement = 0.0

        traj_ds.close()

        results = {
            'sim_name': sim_name,
            'n_particles': n_particles,
            'n_times': n_times,
            'individual_displacements': displacements,
            'mean_displacement': np.mean(displacements) if displacements else 0.0,
            'center_displacement': center_displacement,
            'final_positions': list(zip(final_lons, final_lats))
        }

        print(f"\n📊 {sim_name.upper()} RESULTS:")
        print(f"   Particles: {n_particles}, Time steps: {n_times}")
        print(f"   Mean displacement: {results['mean_displacement']:.2f} km")
        print(f"   Center displacement: {center_displacement:.2f} km")

        return results

    except Exception as e:
        print(f"❌ Error analyzing {sim_name} trajectories: {e}")
        return None

def plot_trajectories(trajectory_file, output_dir, suffix, sim_name):
    """Create trajectory plot."""

    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend for headless servers
        import matplotlib.pyplot as plt
        import xarray as xr

        traj_ds = xr.open_zarr(trajectory_file)

        # Check available dimensions
        print(f"   Available dimensions: {list(traj_ds.dims.keys())}")
        print(f"   Available variables: {list(traj_ds.data_vars.keys())}")

        # Find particle dimension (could be 'traj', 'trajectory', or similar)
        particle_dim = None
        for dim_name in ['traj', 'trajectory', 'particle', 'p']:
            if dim_name in traj_ds.dims:
                particle_dim = dim_name
                break

        if particle_dim is None:
            print(f"   ❌ No particle dimension found in {list(traj_ds.dims.keys())}")
            traj_ds.close()
            return

        n_particles = traj_ds.dims[particle_dim]
        print(f"   Found {n_particles} particles in dimension '{particle_dim}'")

        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        colors = plt.cm.tab10(np.linspace(0, 1, n_particles))

        for p in range(n_particles):
            lons = traj_ds.lon.isel(traj=p).values
            lats = traj_ds.lat.isel(traj=p).values

            valid_mask = ~np.isnan(lons) & ~np.isnan(lats)
            if np.any(valid_mask):
                lons_clean = lons[valid_mask]
                lats_clean = lats[valid_mask]

                ax.plot(lons_clean, lats_clean, 'o-', color=colors[p],
                       linewidth=2, markersize=4, alpha=0.8, label=f'Particle {p+1}')

                if len(lons_clean) > 0:
                    ax.plot(lons_clean[0], lats_clean[0], 's', color=colors[p],
                           markersize=8, markeredgecolor='black', markeredgewidth=1)
                    if len(lons_clean) > 1:
                        ax.plot(lons_clean[-1], lats_clean[-1], '^', color=colors[p],
                               markersize=8, markeredgecolor='black', markeredgewidth=1)

        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        ax.set_title(f'Mobile Bay Plastic Trajectories - {sim_name.upper()}\n(1-hour simulation)',
                    fontsize=14, fontweight='bold')

        ax.grid(True, alpha=0.3)
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        ax.text(0.02, 0.98, '■ Start  ▲ End', transform=ax.transAxes,
               verticalalignment='top', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        ax.set_aspect('equal', adjustable='box')
        plt.tight_layout()

        plot_file = os.path.join(output_dir, f'trajectories_{suffix}.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()

        traj_ds.close()
        print(f"   ✓ Plot saved: {plot_file}")

    except Exception as e:
        print(f"   ❌ Error creating plot: {e}")

def compare_results(results_full, results_single):
    """Compare results between full and single time step simulations."""

    print(f"\n🔍 DIAGNOSTIC COMPARISON ANALYSIS 🔍")
    print("=" * 50)

    if not results_full or not results_single:
        print("❌ Cannot compare - missing results")
        return

    print(f"📊 DISPLACEMENT COMPARISON:")
    print(f"   Full hourly mean displacement:   {results_full['mean_displacement']:.3f} km")
    print(f"   Single time mean displacement:   {results_single['mean_displacement']:.3f} km")
    print(f"   Difference:                      {abs(results_full['mean_displacement'] - results_single['mean_displacement']):.3f} km")

    print(f"\n📊 CENTER OF MASS COMPARISON:")
    print(f"   Full hourly center displacement: {results_full['center_displacement']:.3f} km")
    print(f"   Single time center displacement: {results_single['center_displacement']:.3f} km")
    print(f"   Difference:                      {abs(results_full['center_displacement'] - results_single['center_displacement']):.3f} km")

    # Calculate position differences
    pos_diffs = []
    for i, (pos_full, pos_single) in enumerate(zip(results_full['final_positions'], results_single['final_positions'])):
        if not (np.isnan(pos_full[0]) or np.isnan(pos_single[0])):
            dx = (pos_full[0] - pos_single[0]) * 111.32 * np.cos(np.radians(pos_full[1]))
            dy = (pos_full[1] - pos_single[1]) * 111.32
            diff = np.sqrt(dx**2 + dy**2)
            pos_diffs.append(diff)
            print(f"   Particle {i+1} position difference: {diff:.3f} km")

    if pos_diffs:
        mean_pos_diff = np.mean(pos_diffs)
        max_pos_diff = np.max(pos_diffs)

        print(f"\n📊 FINAL POSITION DIFFERENCES:")
        print(f"   Mean position difference:        {mean_pos_diff:.3f} km")
        print(f"   Maximum position difference:     {max_pos_diff:.3f} km")

        print(f"\n🎯 CONCLUSION:")
        if mean_pos_diff > 0.1:  # 100m threshold
            print(f"   ✅ HOURLY RESOLUTION MATTERS! (Mean diff: {mean_pos_diff:.3f} km)")
            print(f"   ✅ Temporal resolution significantly affects particle transport")
        else:
            print(f"   ⚠️  MINIMAL DIFFERENCE (Mean diff: {mean_pos_diff:.3f} km)")
            print(f"   ⚠️  Hourly resolution may not be critical for this case")

def main():
    """Main comparison function."""

    print("🔬 MOBILE BAY DIAGNOSTIC COMPARISON TEST 🔬")
    print("=" * 60)
    print()
    print("Comparing identical simulations with:")
    print("1. Full 6-hour hourly resolution")
    print("2. Single time step (constant velocities)")
    print()

    # Check if datasets exist
    if not os.path.exists('mobile_6hour_full'):
        print("❌ mobile_6hour_full not found. Run mobile_schism_diagnostic_comparison.py first!")
        return False

    if not os.path.exists('mobile_6hour_single'):
        print("❌ mobile_6hour_single not found. Run mobile_schism_diagnostic_comparison.py first!")
        return False

    # Run both simulations
    results_full = run_simulation('mobile_6hour_full', 'Full Hourly', 'full')
    results_single = run_simulation('mobile_6hour_single', 'Single Time', 'single')

    # Compare results
    compare_results(results_full, results_single)

    print(f"\n🎉 DIAGNOSTIC COMPARISON COMPLETED! 🎉")
    print("=" * 45)
    print("📁 Compare these plots:")
    print("   • mobile_6hour_full/trajectories_full.png")
    print("   • mobile_6hour_single/trajectories_single.png")

if __name__ == "__main__":
    main()
