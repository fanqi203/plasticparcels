#!/usr/bin/env python3
"""
Plastic Parcels Simulation Script

Usage:
    python run_plastic_simulation.py --start "2024-05-01 01:00:00" --end "2024-05-02 01:00:00" --lat 33.5 --lon -78.8

This script:
1. Takes command-line arguments for start/end time and plastic release location
2. Downloads necessary data (uses test data for now)
3. Configures and runs a basic 3D simulation (U/V/W only)
4. Saves output file
5. Plots the trajectory
"""

import argparse
import os
import sys
from datetime import datetime, timedelta
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt

# Add current directory to path for imports
sys.path.insert(0, '.')

import plasticparcels as pp
import parcels
import xarray as xr

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Run plastic particle simulation',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python run_plastic_simulation.py --start "2024-05-01 01:00:00" --end "2024-05-02 01:00:00" --lat 33.5 --lon -78.8
    python run_plastic_simulation.py --start "2020-01-04 00:00:00" --end "2020-01-06 00:00:00" --lat 35.0 --lon 18.0
        """
    )

    parser.add_argument('--start', required=True,
                       help='Start time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--end', required=True,
                       help='End time (YYYY-MM-DD HH:MM:SS)')
    parser.add_argument('--lat', type=float, required=True,
                       help='Latitude of plastic release location (degrees N)')
    parser.add_argument('--lon', type=float, required=True,
                       help='Longitude of plastic release location (degrees E)')
    parser.add_argument('--output', default='plastic_simulation',
                       help='Output filename prefix (default: plastic_simulation)')
    parser.add_argument('--timestep', type=int, default=20,
                       help='Simulation timestep in minutes (default: 20)')
    parser.add_argument('--output_freq', type=int, default=60,
                       help='Output frequency in minutes (default: 60)')

    return parser.parse_args()

def validate_inputs(args):
    """Validate input arguments."""
    try:
        start_time = datetime.strptime(args.start, '%Y-%m-%d %H:%M:%S')
        end_time = datetime.strptime(args.end, '%Y-%m-%d %H:%M:%S')
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}. Use YYYY-MM-DD HH:MM:SS")

    if end_time <= start_time:
        raise ValueError("End time must be after start time")

    if not (-90 <= args.lat <= 90):
        raise ValueError("Latitude must be between -90 and 90 degrees")

    if not (-180 <= args.lon <= 180):
        raise ValueError("Longitude must be between -180 and 180 degrees")

    return start_time, end_time

def check_data_availability(start_time, end_time, lat, lon):
    """Check if we have appropriate data for the requested time/location."""

    # Check if we have test data (Mediterranean Sea region)
    test_data_bounds = {
        'lat_min': 33.0, 'lat_max': 37.0,
        'lon_min': 16.0, 'lon_max': 21.0,
        'time_start': datetime(2020, 1, 1),
        'time_end': datetime(2020, 1, 6)
    }

    original_start = start_time
    original_end = end_time

    # Check if location is within test data bounds
    in_test_region = (test_data_bounds['lat_min'] <= lat <= test_data_bounds['lat_max'] and
                     test_data_bounds['lon_min'] <= lon <= test_data_bounds['lon_max'])

    in_test_time = (test_data_bounds['time_start'] <= start_time <= test_data_bounds['time_end'])

    if in_test_region and in_test_time:
        print(f"✓ Location and time within test data bounds")
        print(f"  Using Mediterranean Sea test data")
        return start_time, end_time, lat, lon

    # If outside test data, inform user about requirements for global data
    print(f"Location ({lat}, {lon}) and/or time period is outside test data region")
    print(f"Test data covers: {test_data_bounds['lat_min']}-{test_data_bounds['lat_max']}°N, "
          f"{test_data_bounds['lon_min']}-{test_data_bounds['lon_max']}°E")
    print(f"Test time period: {test_data_bounds['time_start']} to {test_data_bounds['time_end']}")
    print()
    print("For global simulations, you need to download data from Copernicus Marine Service:")
    print("  • Hydrodynamic: MOI GLO12 (psy4v3r1) - U/V/W velocities, T/S")
    print("  • Biogeochemical: MOI BIO4 (biomer4v2r1) - Nutrients, phytoplankton")
    print("  • Wave: ECMWF ERA5 Wave - Stokes drift")
    print("  • Wind: ECMWF ERA5 Wind - 10m wind components")
    print()
    print("Options:")
    print("  1. Continue with test data (may produce unrealistic results)")
    print("  2. Adjust to test data region/time")
    print("  3. Cancel and download global data")

    choice = input("Choose option (1/2/3): ").strip()

    if choice == '3':
        print("Please download the required data and update the settings file.")
        print("See: https://plastic.oceanparcels.org/en/latest/index.html#required-data")
        sys.exit(0)
    elif choice == '2':
        print("Adjusting to test data region and time...")
        # Store original coordinates
        original_lat, original_lon = lat, lon

        # Adjust to test data period
        duration = original_end - original_start
        start_time = datetime(2020, 1, 4, 0, 0, 0)
        end_time = start_time + duration
        if end_time > test_data_bounds['time_end']:
            end_time = test_data_bounds['time_end']

        # Adjust to test region (center of Mediterranean)
        lat = 35.0
        lon = 18.0

        print(f"Adjusted simulation:")
        print(f"  Original location: ({original_lat}°N, {original_lon}°E)")
        print(f"  Adjusted location: {lat}°N, {lon}°E (Mediterranean Sea)")
        print(f"  Time: {start_time} to {end_time}")
        print("  ⚠️  NOTE: Coordinates have been changed to fit available data!")

        return start_time, end_time, lat, lon
    else:
        print("Continuing with test data (results may be unrealistic)...")
        return start_time, end_time, lat, lon

def setup_simulation(start_time, end_time, lat, lon, timestep_min, output_freq_min):
    """Set up the simulation configuration."""
    print("Setting up simulation configuration...")

    # Load base settings from test data
    settings = pp.utils.load_settings('tests/test_data/test_settings.json')

    # Configure simulation parameters
    runtime = end_time - start_time
    settings['simulation'] = {
        'startdate': start_time,
        'runtime': runtime,
        'outputdt': timedelta(minutes=output_freq_min),
        'dt': timedelta(minutes=timestep_min),
    }

    # Configure plastic properties (basic settings)
    settings['plastictype'] = {
        'wind_coefficient': 0.0,        # No wind effect
        'plastic_diameter': 0.001,      # 1mm particles
        'plastic_density': 1025.0,      # Slightly denser than seawater
    }

    # Enable only basic 3D advection
    settings['use_3D'] = True
    settings['use_biofouling'] = False
    settings['use_stokes'] = False
    settings['use_wind'] = False
    settings['use_mixing'] = False

    print(f"✓ Simulation configured:")
    print(f"  Start: {start_time}")
    print(f"  End: {end_time}")
    print(f"  Duration: {runtime}")
    print(f"  Timestep: {timestep_min} minutes")
    print(f"  Output frequency: {output_freq_min} minutes")

    return settings

def download_data(settings):
    """Download necessary data for the simulation."""
    print("Downloading and checking data availability...")

    # First, download the plasticparcels dataset (release maps, etc.)
    print("1. Downloading plasticparcels release data...")
    try:
        settings = pp.utils.download_plasticparcels_dataset('NEMO0083', settings, 'input_data')
        print("✓ PlasticParcels release data downloaded successfully")

        # Show what was downloaded
        print("  Downloaded files:")
        if 'release_maps' in settings:
            for key, filepath in settings['release_maps'].items():
                if os.path.exists(filepath):
                    size_kb = os.path.getsize(filepath) / 1024
                    print(f"    • {key}: {os.path.basename(filepath)} ({size_kb:.1f} KB)")

        if 'unbeaching' in settings and 'filename' in settings['unbeaching']:
            filepath = settings['unbeaching']['filename']
            if os.path.exists(filepath):
                size_kb = os.path.getsize(filepath) / 1024
                print(f"    • unbeaching: {os.path.basename(filepath)} ({size_kb:.1f} KB)")

    except Exception as e:
        print(f"Warning: Could not download plasticparcels data: {e}")
        print("Continuing with basic simulation...")

    # Check for test oceanographic data
    print("\n2. Checking oceanographic test data...")
    test_data_dir = 'tests/test_data'
    if not os.path.exists(test_data_dir):
        raise FileNotFoundError(f"Test data directory not found: {test_data_dir}")

    # Check if essential files exist
    required_files = [
        'test_U_2020-01-04.nc', 'test_V_2020-01-04.nc', 'test_W_2020-01-04.nc',
        'test_T_2020-01-04.nc', 'test_S_2020-01-04.nc',
        'test_ocean_mesh_hgr.nc', 'test_bathymetry_mesh_zgr.nc'
    ]

    missing_files = []
    for file in required_files:
        if not os.path.exists(os.path.join(test_data_dir, file)):
            missing_files.append(file)

    if missing_files:
        raise FileNotFoundError(f"Missing required oceanographic data files: {missing_files}")

    print("✓ All required oceanographic test data files found")

    # Show available test data
    print("  Available test data files:")
    for file in sorted(required_files):
        filepath = os.path.join(test_data_dir, file)
        if os.path.exists(filepath):
            size_kb = os.path.getsize(filepath) / 1024
            print(f"    • {file} ({size_kb:.1f} KB)")

    print("\n✓ Data preparation complete")
    return settings

def run_simulation(settings, lat, lon, output_prefix):
    """Run the plastic particle simulation."""
    print("Creating fieldset...")

    # Create the fieldset with 3D ocean data
    fieldset = pp.constructors.create_fieldset(settings)
    print(f"✓ Fieldset created with {len(fieldset.get_fields())} fields")

    print("Creating particle set...")

    # Create release locations
    release_locations = {
        'lons': [lon],
        'lats': [lat],
        'plastic_amount': [1.0]  # Release 1 unit of plastic
    }

    # Create particle set
    pset = pp.constructors.create_particleset(fieldset, settings, release_locations)
    print(f"✓ Created {len(pset)} particle(s) at ({lat}°N, {lon}°E)")

    print("Setting up physics kernels...")

    # Create kernels for 3D advection only
    kernels = pp.constructors.create_kernel(fieldset)
    kernel_names = [k.__name__ for k in kernels]
    print(f"✓ Using kernels: {', '.join(kernel_names)}")

    print("Running simulation...")

    # Set up output file
    output_file = f"{output_prefix}.zarr"
    pfile = pp.ParticleFile(output_file, pset, settings=settings,
                           outputdt=settings['simulation']['outputdt'])

    # Run the simulation
    try:
        pset.execute(kernels,
                    runtime=settings['simulation']['runtime'],
                    dt=settings['simulation']['dt'],
                    output_file=pfile)

        print(f"✓ Simulation completed successfully!")
        print(f"✓ Output saved to: {output_file}")

        return output_file

    except Exception as e:
        print(f"✗ Simulation failed: {e}")
        raise

def plot_trajectory(output_file, lat, lon, output_prefix):
    """Plot the particle trajectory."""
    print("Creating trajectory plot...")

    try:
        # Load the simulation results
        ds = xr.open_zarr(output_file)

        # Debug: print available variables
        print(f"Available variables: {list(ds.variables.keys())}")
        print(f"Dataset dimensions: {dict(ds.dims)}")

        # Extract trajectory data - handle different possible variable names
        lons = ds.lon.values
        lats = ds.lat.values

        # Check for depth variable (might be 'z' or 'depth')
        if 'z' in ds.variables:
            depths = ds.z.values
        elif 'depth' in ds.variables:
            depths = ds.depth.values
        else:
            print("Warning: No depth variable found, using zeros")
            depths = np.zeros_like(lons)

        # Get time information - use obs dimension for time steps
        if 'time' in ds.variables:
            times = ds.time.values
        else:
            # Create time array based on obs dimension
            times = np.arange(lons.shape[1])
            print("Using observation steps as time")

        # Create the plot
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))

        # Plot 1: Horizontal trajectory
        ax1.plot(lons[0, :], lats[0, :], 'b-', linewidth=2, alpha=0.7, label='Trajectory')
        ax1.plot(lon, lat, 'ro', markersize=10, label='Start')
        ax1.plot(lons[0, -1], lats[0, -1], 'gs', markersize=10, label='End')

        ax1.set_xlabel('Longitude (°E)')
        ax1.set_ylabel('Latitude (°N)')
        ax1.set_title('Horizontal Trajectory')
        ax1.grid(True, alpha=0.3)
        ax1.legend()

        # Add distance scale
        total_distance = np.sum(np.sqrt(np.diff(lons[0, :])**2 + np.diff(lats[0, :])**2)) * 111.32  # km
        ax1.text(0.02, 0.98, f'Total distance: {total_distance:.1f} km',
                transform=ax1.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        # Plot 2: Depth profile
        if len(times) > 1 and hasattr(times[0], 'total_seconds'):
            # If times are datetime objects
            time_hours = np.array([(t - times[0]).total_seconds() / 3600 for t in times])
        else:
            # Use step numbers as hours
            time_hours = np.arange(len(depths[0, :]))
        ax2.plot(time_hours, depths[0, :], 'r-', linewidth=2)
        ax2.set_xlabel('Time (hours)')
        ax2.set_ylabel('Depth (m)')
        ax2.set_title('Vertical Profile')
        ax2.grid(True, alpha=0.3)
        ax2.invert_yaxis()  # Depth increases downward

        # Add depth change info
        depth_change = depths[0, -1] - depths[0, 0]
        ax2.text(0.02, 0.98, f'Depth change: {depth_change:.1f} m',
                transform=ax2.transAxes, verticalalignment='top',
                bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

        plt.tight_layout()

        # Save the plot
        plot_file = f"{output_prefix}_trajectory.png"
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"✓ Trajectory plot saved to: {plot_file}")

        # Show summary statistics
        print("\nSimulation Summary:")
        print(f"  Start position: ({lat:.3f}°N, {lon:.3f}°E)")
        print(f"  End position: ({lats[0, -1]:.3f}°N, {lons[0, -1]:.3f}°E)")
        print(f"  Total distance: {total_distance:.1f} km")
        print(f"  Depth change: {depth_change:.1f} m")
        print(f"  Duration: {len(times)} time steps")

        return plot_file

    except Exception as e:
        print(f"✗ Plotting failed: {e}")
        raise

def main():
    """Main function to run the complete simulation pipeline."""
    print("=" * 70)
    print("PLASTIC PARCELS SIMULATION")
    print("=" * 70)

    try:
        # Parse command line arguments
        args = parse_arguments()

        # Validate inputs
        start_time, end_time = validate_inputs(args)

        # Check data availability and adjust if needed
        start_time, end_time, final_lat, final_lon = check_data_availability(start_time, end_time, args.lat, args.lon)

        # Set up simulation
        settings = setup_simulation(start_time, end_time, final_lat, final_lon,
                                  args.timestep, args.output_freq)

        # Download/check data
        settings = download_data(settings)

        # Run simulation
        output_file = run_simulation(settings, final_lat, final_lon, args.output)

        # Plot results
        plot_file = plot_trajectory(output_file, final_lat, final_lon, args.output)

        print("\n" + "=" * 70)
        print("🎉 SIMULATION COMPLETED SUCCESSFULLY! 🎉")
        print("=" * 70)
        print(f"Output files:")
        print(f"  Simulation data: {output_file}")
        print(f"  Trajectory plot: {plot_file}")
        print("=" * 70)

    except KeyboardInterrupt:
        print("\n\nSimulation interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Simulation failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
