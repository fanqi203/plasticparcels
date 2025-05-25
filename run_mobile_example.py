#!/usr/bin/env python3
"""
Mobile Bay SCHISM to PlasticParcels Example Script

This demonstrates how to use the time series converter for Mobile Bay with:
1. Multiple SCHISM files (out2d_1.nc, out2d_2.nc, ...)
2. Full domain processing
3. Spatial subsetting options
4. Custom release locations

Usage:
    conda activate plasticparcels
    python run_mobile_example.py
"""

from schism_timeseries_to_plasticparcels import SCHISMTimeSeriesConverter

def run_mobile_basic_example():
    """Run basic example with Mobile Bay data - first 10 time steps."""

    print("🌊 MOBILE BAY EXAMPLE 1: BASIC USAGE (10 TIME STEPS) 🌊")
    print("=" * 65)

    # Mobile Bay SCHISM files path
    schism_pattern = '/anvil/projects/x-ees240085/sbao/mobile/outputs/out2d_*.nc'

    # Create converter for first 10 files
    converter = SCHISMTimeSeriesConverter(
        schism_files=schism_pattern,
        output_dir='mobile_basic_timeseries',
        target_resolution=0.01  # 1.1 km resolution
    )

    # Limit to first 10 files for testing
    converter.schism_files = sorted(converter.schism_files)[:10]
    
    print(f"Processing {len(converter.schism_files)} files:")
    for i, f in enumerate(converter.schism_files):
        print(f"  {i+1}. {f.split('/')[-1]}")

    # Run complete workflow
    success = converter.run_complete_workflow()

    return success

def run_mobile_subset_example():
    """Run example with spatial subsetting of Mobile Bay."""

    print("🌊 MOBILE BAY EXAMPLE 2: SPATIAL SUBSETTING 🌊")
    print("=" * 60)

    # Mobile Bay SCHISM files path
    schism_pattern = '/anvil/projects/x-ees240085/sbao/mobile/outputs/out2d_*.nc'

    # Create converter with spatial bounds (focus on main bay area)
    converter = SCHISMTimeSeriesConverter(
        schism_files=schism_pattern,
        output_dir='mobile_subset_timeseries',
        target_resolution=0.005,  # Higher resolution (0.5 km) for smaller domain
        lon_bounds=(-88.5, -87.8),  # Main Mobile Bay area
        lat_bounds=(30.2, 30.5)     # Main Mobile Bay area
    )

    # Use first 5 files for subset example
    converter.schism_files = sorted(converter.schism_files)[:5]
    
    print(f"Processing {len(converter.schism_files)} files with spatial subsetting:")
    print(f"  Longitude: {converter.lon_bounds[0]}° to {converter.lon_bounds[1]}°")
    print(f"  Latitude: {converter.lat_bounds[0]}° to {converter.lat_bounds[1]}°")

    # Run complete workflow
    success = converter.run_complete_workflow()

    return success

def run_mobile_full_example():
    """Run example with many time steps (first 50 files)."""

    print("🌊 MOBILE BAY EXAMPLE 3: EXTENDED TIME SERIES (50 STEPS) 🌊")
    print("=" * 70)

    # Mobile Bay SCHISM files path
    schism_pattern = '/anvil/projects/x-ees240085/sbao/mobile/outputs/out2d_*.nc'

    # Create converter for extended time series
    converter = SCHISMTimeSeriesConverter(
        schism_files=schism_pattern,
        output_dir='mobile_extended_timeseries',
        target_resolution=0.01  # 1.1 km resolution
    )

    # Use first 50 files for extended example
    converter.schism_files = sorted(converter.schism_files)[:50]
    
    print(f"Processing {len(converter.schism_files)} files for extended time series")
    print(f"This will create a {len(converter.schism_files)}-hour simulation dataset")

    # Run complete workflow
    success = converter.run_complete_workflow()

    return success

def run_all_mobile_examples():
    """Run all Mobile Bay examples to demonstrate different capabilities."""

    print("🚀 RUNNING ALL MOBILE BAY SCHISM TO PLASTICPARCELS EXAMPLES 🚀")
    print("=" * 75)
    print()

    examples = [
        ("Basic Usage (10 time steps)", run_mobile_basic_example),
        ("Spatial Subsetting (5 time steps)", run_mobile_subset_example),
        ("Extended Time Series (50 time steps)", run_mobile_full_example)
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
    print("📊 SUMMARY OF ALL MOBILE BAY EXAMPLES:")
    print("=" * 45)
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")

    total_success = sum(results.values())
    print()
    print(f"🎯 Overall: {total_success}/{len(examples)} examples successful")

    if total_success == len(examples):
        print("🎉 ALL MOBILE BAY EXAMPLES COMPLETED SUCCESSFULLY! 🎉")
        print()
        print("📁 Check these output directories:")
        print("   • mobile_basic_timeseries/")
        print("   • mobile_subset_timeseries/")
        print("   • mobile_extended_timeseries/")
        print()
        print("Each contains NEMO-format time series files ready for PlasticParcels!")
        print()
        print("🌊 Next steps:")
        print("   1. Test PlasticParcels integration with any of the output directories")
        print("   2. Run plastic pollution simulations with realistic time-varying currents")
        print("   3. Scale up to process all 249 time steps if needed")

    return total_success == len(examples)

if __name__ == "__main__":
    # You can run individual examples or all of them
    
    print("🏖️  MOBILE BAY SCHISM TO PLASTICPARCELS CONVERTER 🏖️")
    print("=" * 60)
    print()
    print("This script will convert Mobile Bay SCHISM data to PlasticParcels format")
    print("Make sure you have activated the plasticparcels conda environment!")
    print()

    # Option 1: Run all examples
    run_all_mobile_examples()

    # Option 2: Run individual examples (uncomment to use)
    # run_mobile_basic_example()
    # run_mobile_subset_example()
    # run_mobile_full_example()
