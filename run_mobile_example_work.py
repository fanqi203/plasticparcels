#!/usr/bin/env python3
"""
Mobile Bay SCHISM to PlasticParcels example using the working approach

Based on the successful run_schism_example_work.py but adapted for Mobile Bay
with multiple sequential files.
"""

from schism_to_plasticparcels_complete import SCHISMToPlasticParcels
import glob
import re

def run_mobile_single_file_example():
    """Run Mobile Bay example with single file (like the working Beaufort example)."""

    print("🌊 MOBILE BAY EXAMPLE: SINGLE FILE (WORKING APPROACH) 🌊")
    print("=" * 65)

    # Use first Mobile Bay SCHISM file
    schism_file = '/anvil/projects/x-ees240085/sbao/mobile/outputs/out2d_1.nc'

    # Create converter using the same approach as the working example
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='mobile_single_work',
        target_resolution=0.01  # 1.1 km resolution
    )

    # Run complete workflow with the same parameters as working example
    success = converter.run_complete_workflow(
        simulation_hours=1,    # Short 1-hour simulation (single time step)
        num_particles=4        # 2x2 grid of particles
    )

    return success

def run_mobile_multiple_files_example():
    """Run Mobile Bay example processing multiple files sequentially."""

    print("🌊 MOBILE BAY EXAMPLE: MULTIPLE FILES SEQUENTIAL 🌊")
    print("=" * 60)

    # Get first 3 Mobile Bay SCHISM files
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')
    
    # Sort files by the numeric part to get sequential order
    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0
    
    all_files = sorted(all_files, key=extract_number)
    test_files = all_files[:3]  # Use first 3 files
    
    print(f"Processing {len(test_files)} files sequentially:")
    for i, f in enumerate(test_files):
        print(f"  {i+1}. {f.split('/')[-1]}")
    
    results = []
    
    # Process each file individually (like the working approach)
    for i, schism_file in enumerate(test_files):
        print(f"\n--- Processing file {i+1}: {schism_file.split('/')[-1]} ---")
        
        # Create converter for this file
        converter = SCHISMToPlasticParcels(
            schism_file=schism_file,
            output_dir=f'mobile_file_{i+1}_work',
            target_resolution=0.01
        )

        # Run workflow for this file
        try:
            success = converter.run_complete_workflow(
                simulation_hours=1,    # 1-hour simulation per file
                num_particles=4        # 2x2 grid of particles
            )
            results.append(success)
            print(f"✅ File {i+1}: {'SUCCESS' if success else 'FAILED'}")
        except Exception as e:
            print(f"❌ File {i+1}: ERROR - {e}")
            results.append(False)
    
    # Summary
    total_success = sum(results)
    print(f"\n📊 SUMMARY:")
    print(f"   Successful files: {total_success}/{len(test_files)}")
    
    if total_success > 0:
        print("\n📁 Output directories created:")
        for i in range(len(test_files)):
            if results[i]:
                print(f"   • mobile_file_{i+1}_work/")
    
    return total_success == len(test_files)

def run_mobile_custom_release_example():
    """Run Mobile Bay example with custom release locations."""

    print("🌊 MOBILE BAY EXAMPLE: CUSTOM RELEASE LOCATIONS 🌊")
    print("=" * 60)

    # Use first Mobile Bay SCHISM file
    schism_file = '/anvil/projects/x-ees240085/sbao/mobile/outputs/out2d_1.nc'

    # Create converter
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='mobile_custom_release_work',
        target_resolution=0.01
    )

    # Define custom release locations in Mobile Bay
    # These coordinates are within the Mobile Bay domain
    custom_releases = {
        'lons': [-88.6, -88.5, -88.4, -88.3],  # Mobile Bay longitudes
        'lats': [30.2, 30.3, 30.4, 30.5]       # Mobile Bay latitudes
    }

    # Run complete workflow
    success = converter.run_complete_workflow(
        simulation_hours=1,                # 1-hour simulation
        release_locations=custom_releases  # Use custom locations
    )

    return success

def main():
    """Main function to run Mobile Bay examples."""
    
    print("🏖️  MOBILE BAY SCHISM TO PLASTICPARCELS (WORKING APPROACH) 🏖️")
    print("=" * 70)
    print()
    print("Using the same approach as the successful run_schism_example_work.py")
    print("but adapted for Mobile Bay data.")
    print()

    examples = [
        ("Single File (Working Approach)", run_mobile_single_file_example),
        ("Multiple Files Sequential", run_mobile_multiple_files_example),
        ("Custom Release Locations", run_mobile_custom_release_example)
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
    print("📊 FINAL SUMMARY:")
    print("=" * 25)
    for name, success in results.items():
        status = "✅ SUCCESS" if success else "❌ FAILED"
        print(f"  {name}: {status}")

    total_success = sum(results.values())
    print()
    print(f"🎯 Overall: {total_success}/{len(examples)} examples successful")

    if total_success > 0:
        print("\n🎉 AT LEAST ONE EXAMPLE WORKED! 🎉")
        print("This confirms Mobile Bay SCHISM data works with PlasticParcels!")

    return total_success > 0

if __name__ == "__main__":
    main()
