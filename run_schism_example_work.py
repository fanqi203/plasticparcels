#!/usr/bin/env python3
"""
Example script to run SCHISM to PlasticParcels conversion

This demonstrates how to use the complete workflow script with:
1. Basic usage (full domain)
2. Spatial subsetting (subset of domain)
3. Custom release locations
"""

from schism_to_plasticparcels_complete import SCHISMToPlasticParcels

def run_basic_example():
    """Run basic example with full domain."""

    print("🌊 EXAMPLE 1: BASIC USAGE (FULL DOMAIN) 🌊")
    print("=" * 60)

    # Your SCHISM file path
    schism_file = '/anvil/scratch/x-fanqi203/beaufort/wwm_wall_nowetland/out2d_1.nc'

    # Create converter
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='beaufort_basic_example',
        target_resolution=0.01  # 1.1 km resolution
    )

    # Run complete workflow
    success = converter.run_complete_workflow(
        simulation_hours=6,    # 6-hour simulation
        num_particles=16       # 4x4 grid of particles
    )

    return success

def run_subset_example():
    """Run example with spatial subsetting."""

    print("🌊 EXAMPLE 2: SPATIAL SUBSETTING 🌊")
    print("=" * 60)

    # Your SCHISM file path
    schism_file = '/anvil/scratch/x-fanqi203/beaufort/wwm_wall_nowetland/out2d_1.nc'

    # Create converter with spatial bounds (subset of domain)
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='beaufort_subset_example',
        target_resolution=0.005,  # Higher resolution (0.5 km) for smaller domain
        lon_bounds=(-80.7, -80.3),  # Subset longitude range
        lat_bounds=(32.0, 32.4)     # Subset latitude range
    )

    # Run complete workflow
    success = converter.run_complete_workflow(
        simulation_hours=8,    # 8-hour simulation
        num_particles=25       # 5x5 grid of particles
    )

    return success

def run_custom_release_example():
    """Run example with custom release locations."""

    print("🌊 EXAMPLE 3: CUSTOM RELEASE LOCATIONS 🌊")
    print("=" * 60)

    # Your SCHISM file path
    schism_file = '/anvil/scratch/x-fanqi203/beaufort/wwm_wall_nowetland/out2d_1.nc'

    # Create converter
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='beaufort_custom_release_example',
        target_resolution=0.01
    )

    # Define custom release locations (e.g., specific pollution sources)
    custom_releases = {
        'lons': [-80.6, -80.5, -80.4, -80.3, -80.2],  # 5 specific longitudes
        'lats': [32.1, 32.2, 32.3, 32.2, 32.1]        # 5 specific latitudes
    }

    # Run complete workflow
    success = converter.run_complete_workflow(
        simulation_hours=12,           # 12-hour simulation
        release_locations=custom_releases  # Use custom locations
    )

    return success

def run_all_examples():
    """Run all examples to demonstrate different capabilities."""

    print("🚀 RUNNING ALL SCHISM TO PLASTICPARCELS EXAMPLES 🚀")
    print("=" * 70)
    print()

    examples = [
        ("Basic Usage (Full Domain)", run_basic_example),
        ("Spatial Subsetting", run_subset_example),
        ("Custom Release Locations", run_custom_release_example)
    ]

    results = {}

    for name, example_func in examples:
        print(f"Running: {name}")
        try:
            success = example_func()
            results[name] = success
            if success:
                print(f"✅ {name}: SUCCESS")
            else:
                print(f"❌ {name}: FAILED")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
            results[name] = False
        print()

    # Summary
    print("📊 SUMMARY OF ALL EXAMPLES:")
    print("=" * 40)
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")

    total_success = sum(results.values())
    print()
    print(f"🎯 Overall: {total_success}/{len(examples)} examples successful")

    if total_success == len(examples):
        print("🎉 ALL EXAMPLES COMPLETED SUCCESSFULLY! 🎉")
        print()
        print("📁 Check these output directories:")
        print("   • beaufort_basic_example/")
        print("   • beaufort_subset_example/")
        print("   • beaufort_custom_release_example/")
        print()
        print("Each contains NEMO-format files and trajectory visualizations!")

    return total_success == len(examples)

if __name__ == "__main__":
    # You can run individual examples or all of them

    # Option 1: Run all examples
    #run_all_examples()

    # Option 2: Run individual examples (uncomment to use)
    # run_basic_example()
    # run_subset_example()
    run_custom_release_example()
