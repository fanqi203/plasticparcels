#!/usr/bin/env python3
"""
Example script to run SCHISM to PlasticParcels conversion

This demonstrates how to use the complete workflow script.
"""

from schism_to_plasticparcels_complete import SCHISMToPlasticParcels

def run_beaufort_example():
    """Run the example with your Beaufort Sea SCHISM file."""
    
    print("🌊 RUNNING SCHISM TO PLASTICPARCELS EXAMPLE 🌊")
    print("=" * 60)
    
    # Your SCHISM file path
    schism_file = '/anvil/scratch/x-fanqi203/beaufort/wwm_wall_nowetland/out2d_1.nc'
    
    # Create converter
    converter = SCHISMToPlasticParcels(
        schism_file=schism_file,
        output_dir='beaufort_example_output',
        target_resolution=0.01  # 1.1 km resolution
    )
    
    # Run complete workflow
    success = converter.run_complete_workflow(
        simulation_hours=6,    # 6-hour simulation
        num_particles=16       # 4x4 grid of particles
    )
    
    if success:
        print()
        print("🎉 SUCCESS! 🎉")
        print("Check the 'beaufort_example_output/' directory for results!")
        print("The trajectory plot shows plastic movement based on SCHISM currents.")
    else:
        print("❌ Something went wrong. Check the error messages above.")
    
    return success

if __name__ == "__main__":
    run_beaufort_example()
