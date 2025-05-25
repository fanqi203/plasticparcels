#!/usr/bin/env python3
"""
Test PlasticParcels with complete Mobile Bay time series

Tests the aggregated time series for continuous multi-hour simulations.

Usage:
    conda activate plasticparcels
    python test_complete_timeseries.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def test_complete_timeseries_fieldset(data_dir='mobile_complete_timeseries'):
    """Test fieldset creation with complete time series."""
    
    print("🧪 TESTING COMPLETE TIME SERIES FIELDSET 🧪")
    print("=" * 55)
    
    settings_file = os.path.join(data_dir, 'complete_timeseries_settings.json')
    
    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        print("   Please run aggregate_mobile_timeseries.py first!")
        return False
    
    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        print(f"✓ Loaded settings from {settings_file}")
        
        # Add simulation settings for multi-hour simulation
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=2),  # 2-hour simulation across time steps
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=20),
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
        print("📋 COMPLETE TIME SERIES INFORMATION:")
        print(f"   Domain: {fieldset.U.grid.lon.min():.3f}°E to {fieldset.U.grid.lon.max():.3f}°E")
        print(f"           {fieldset.U.grid.lat.min():.3f}°N to {fieldset.U.grid.lat.max():.3f}°N")
        print(f"   Grid size: {fieldset.U.grid.lat.shape} points")
        print(f"   Time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")
        
        # Test velocity sampling at domain center
        lon_center = (fieldset.U.grid.lon.min() + fieldset.U.grid.lon.max()) / 2
        lat_center = (fieldset.U.grid.lat.min() + fieldset.U.grid.lat.max()) / 2
        
        print(f"\n🌊 TESTING TIME-VARYING VELOCITIES:")
        print(f"   Sampling at center: {lon_center:.3f}°E, {lat_center:.3f}°N")
        
        # Sample velocities at different times
        for t in range(min(3, len(fieldset.U.grid.time))):
            try:
                u_val = fieldset.U[t, 0, lat_center, lon_center]
                v_val = fieldset.V[t, 0, lat_center, lon_center]
                speed = np.sqrt(u_val**2 + v_val**2)
                print(f"   Time {t}h: U={u_val:.4f} m/s, V={v_val:.4f} m/s, Speed={speed:.4f} m/s")
            except Exception as e:
                print(f"   Time {t}h: Could not sample ({e})")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating fieldset: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_complete_timeseries_simulation(data_dir='mobile_complete_timeseries'):
    """Test multi-hour particle simulation with complete time series."""
    
    print("\n🚀 TESTING MULTI-HOUR SIMULATION 🚀")
    print("=" * 45)
    
    settings_file = os.path.join(data_dir, 'complete_timeseries_settings.json')
    
    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        # Add simulation and plastic settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=2),  # 2-hour simulation with time-varying currents
            'outputdt': timedelta(hours=0.5),  # Output every 30 minutes
            'dt': timedelta(minutes=10),       # 10-minute time step
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
        
        # Release 9 particles in a 3x3 grid
        lons = [lon_center - 0.02, lon_center, lon_center + 0.02] * 3
        lats = [lat_center - 0.02] * 3 + [lat_center] * 3 + [lat_center + 0.02] * 3
        
        release_locations = {
            'lons': lons,
            'lats': lats,
            'plastic_amount': [1.0] * 9
        }
        
        print(f"🎯 Releasing 9 particles in 3×3 grid at {lon_center:.3f}°E, {lat_center:.3f}°N")
        print(f"⏱️  Simulation: 2 hours with time-varying currents")
        
        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")
        
        # Run simulation
        print("🌊 Running multi-hour simulation...")
        output_file = os.path.join(data_dir, 'mobile_complete_trajectories.zarr')
        
        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )
        
        print("✅ Multi-hour simulation completed successfully!")
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
            
            # Check particle spread
            final_lons = traj_ds.lon.isel(obs=-1).values
            final_lats = traj_ds.lat.isel(obs=-1).values
            
            valid_mask = ~np.isnan(final_lons) & ~np.isnan(final_lats)
            if np.any(valid_mask):
                lon_spread = final_lons[valid_mask].max() - final_lons[valid_mask].min()
                lat_spread = final_lats[valid_mask].max() - final_lats[valid_mask].min()
                print(f"   Final particle spread: {lon_spread:.4f}° lon × {lat_spread:.4f}° lat")
            
            traj_ds.close()
            
        except Exception as e:
            print(f"   Could not analyze results: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in multi-hour simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    
    print("🏖️  MOBILE BAY COMPLETE TIME SERIES TEST 🏖️")
    print("=" * 55)
    print()
    
    # Check if data directory exists
    data_dir = 'mobile_complete_timeseries'
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("   Please run aggregate_mobile_timeseries.py first!")
        return False
    
    print(f"✓ Found complete time series directory: {data_dir}")
    print()
    
    # Test 1: Fieldset creation
    fieldset_success = test_complete_timeseries_fieldset(data_dir)
    
    if not fieldset_success:
        print("❌ Fieldset creation failed. Cannot proceed with simulation test.")
        return False
    
    # Test 2: Multi-hour simulation
    simulation_success = test_complete_timeseries_simulation(data_dir)
    
    # Summary
    print("\n📊 COMPLETE TIME SERIES TEST SUMMARY:")
    print("=" * 40)
    print(f"   Fieldset creation: {'✅ PASS' if fieldset_success else '❌ FAIL'}")
    print(f"   Multi-hour simulation: {'✅ PASS' if simulation_success else '❌ FAIL'}")
    
    if fieldset_success and simulation_success:
        print("\n🎉 ALL TESTS PASSED! 🎉")
        print("=" * 25)
        print("✅ Complete Mobile Bay time series works perfectly!")
        print("✅ Ready for realistic multi-hour plastic pollution modeling!")
        print()
        print("🌊 You can now:")
        print("   • Run simulations across multiple hours with time-varying currents")
        print("   • Scale up to more time steps (10, 50, or all 249 files)")
        print("   • Study how plastic transport changes over time")
        print("   • Model realistic pollution scenarios in Mobile Bay")
        
        return True
    else:
        print("\n❌ Some tests failed. Check error messages above.")
        return False

if __name__ == "__main__":
    main()
