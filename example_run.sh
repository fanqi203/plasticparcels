#!/bin/bash

# Example script to run plastic particle simulations
# Make sure you're in the plasticparcels conda environment

echo "Running Plastic Parcels Simulation Examples"
echo "==========================================="

# Activate the conda environment
source ~/.bashrc
conda activate plasticparcels

# Example 1: Mediterranean Sea simulation (within test data bounds)
echo "Example 1: Mediterranean Sea simulation"
/home/x-fanqi203/.conda/envs/2024.02-py311/plasticparcels/bin/python run_plastic_simulation.py \
    --start "2020-01-04 00:00:00" \
    --end "2020-01-05 12:00:00" \
    --lat 35.0 \
    --lon 18.0 \
    --output "mediterranean_test" \
    --timestep 20 \
    --output_freq 60

echo ""
echo "Example 1 completed!"
echo "Check files: mediterranean_test.zarr and mediterranean_test_trajectory.png"
echo ""

# Example 2: Different location in Mediterranean
echo "Example 2: Different Mediterranean location"
/home/x-fanqi203/.conda/envs/2024.02-py311/plasticparcels/bin/python run_plastic_simulation.py \
    --start "2020-01-04 06:00:00" \
    --end "2020-01-05 06:00:00" \
    --lat 34.5 \
    --lon 19.5 \
    --output "mediterranean_test2" \
    --timestep 30 \
    --output_freq 120

echo ""
echo "Example 2 completed!"
echo "Check files: mediterranean_test2.zarr and mediterranean_test2_trajectory.png"
echo ""

echo "All examples completed successfully!"
echo "You can now examine the output files and trajectory plots."
