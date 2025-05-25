#!/usr/bin/env python3
"""
Simple test script to demonstrate plasticparcels functionality.
This script creates a basic simulation to verify the installation works.
"""

import plasticparcels as pp
import parcels
import numpy as np
from datetime import datetime, timedelta
import tempfile
import os

def test_basic_functionality():
    """Test basic plasticparcels functionality."""
    print("=" * 60)
    print("PLASTICPARCELS INSTALLATION TEST")
    print("=" * 60)
    
    # Print version information
    print(f"plasticparcels version: {pp.__version__}")
    print(f"parcels version: {parcels.__version__}")
    print()
    
    # Test 1: Create a simple fieldset
    print("Test 1: Creating a simple fieldset...")
    try:
        # Create a simple 2D velocity field
        lon = np.linspace(-1, 1, 10)
        lat = np.linspace(-1, 1, 10)
        U = np.zeros((len(lat), len(lon)))  # No zonal velocity
        V = np.ones((len(lat), len(lon))) * 0.1  # Small meridional velocity
        
        fieldset = parcels.FieldSet.from_data(
            {'U': U, 'V': V},
            {'lon': lon, 'lat': lat},
            mesh='spherical'
        )
        print("✓ Simple fieldset created successfully")
    except Exception as e:
        print(f"✗ Failed to create fieldset: {e}")
        return False
    
    # Test 2: Create a basic particle set
    print("\nTest 2: Creating a basic particle set...")
    try:
        # Create some particles
        lons = np.array([0.0, 0.1, -0.1])
        lats = np.array([0.0, 0.1, -0.1])
        
        pset = parcels.ParticleSet.from_list(
            fieldset=fieldset,
            pclass=parcels.JITParticle,
            lon=lons,
            lat=lats
        )
        print(f"✓ Particle set created with {len(pset)} particles")
    except Exception as e:
        print(f"✗ Failed to create particle set: {e}")
        return False
    
    # Test 3: Test plasticparcels utilities
    print("\nTest 3: Testing plasticparcels utilities...")
    try:
        # Test if we can access plasticparcels modules
        assert hasattr(pp, 'constructors'), "constructors module not found"
        assert hasattr(pp, 'kernels'), "kernels module not found"
        assert hasattr(pp, 'utils'), "utils module not found"
        print("✓ All plasticparcels modules accessible")
    except Exception as e:
        print(f"✗ Failed to access plasticparcels modules: {e}")
        return False
    
    # Test 4: Run a very short simulation
    print("\nTest 4: Running a short simulation...")
    try:
        # Define a simple kernel for advection
        kernel = parcels.AdvectionRK4
        
        # Run for a very short time
        pset.execute(
            kernel,
            runtime=timedelta(hours=1),
            dt=timedelta(minutes=30)
        )
        print("✓ Short simulation completed successfully")
        print(f"  Final particle positions: {[(p.lon, p.lat) for p in pset]}")
    except Exception as e:
        print(f"✗ Failed to run simulation: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("ALL TESTS PASSED! 🎉")
    print("plasticparcels is installed and working correctly.")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = test_basic_functionality()
    exit(0 if success else 1)
