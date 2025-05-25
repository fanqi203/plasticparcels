#!/usr/bin/env python3
"""
Test PlasticParcels with single-hour diagnostic data

Runs the same simulation as the hourly test but with only one time step per day
to compare results and see if hourly resolution matters.

Usage:
    conda activate plasticparcels
    python test_single_hour_diagnostic.py
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def plot_trajectories_comparison(trajectory_file, output_dir, suffix="single_hour"):
    """Create a PNG plot of particle trajectories for comparison."""
    
    try:
        import matplotlib.pyplot as plt
        import xarray as xr
        
        print("📊 Creating single-hour trajectory plot...")
        
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
        ax.set_title('Mobile Bay Plastic Trajectories - SINGLE HOUR DIAGNOSTIC\n(Daily Snapshots Only)', 
                    fontsize=14, fontweight='bold')
        
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
        
        # Add diagnostic info
        ax.text(0.02, 0.02, 'DIAGNOSTIC: Single hour per day\n(No hourly resolution)', 
               transform=ax.transAxes, verticalalignment='bottom', fontsize=10,
               bbox=dict(boxstyle='round', facecolor='orange', alpha=0.7))
        
        # Tight layout
        plt.tight_layout()
        
        # Save plot
        plot_file = os.path.join(output_dir, f'mobile_bay_trajectories_{suffix}.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        traj_ds.close()
        
        print(f"   ✓ Single-hour trajectory plot saved to: {plot_file}")
        return True
        
    except ImportError:
        print("   ⚠️  matplotlib not available for plotting")
        return False
    except Exception as e:
        print(f"   ❌ Error creating plot: {e}")
        return False

def test_single_hour_simulation(data_dir='mobile_single_hour'):
    """Test particle simulation with single-hour diagnostic data."""
    
    print("🚀 TESTING SINGLE HOUR DIAGNOSTIC SIMULATION 🚀")
    print("=" * 55)
    
    settings_file = os.path.join(data_dir, 'settings.json')
    
    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        # Add simulation and plastic settings (SAME as hourly test)
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(days=1, hours=12),  # Same 1.5 day simulation
            'outputdt': timedelta(hours=3),          # Same output frequency
            'dt': timedelta(minutes=20),             # Same time step
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
        
        # Check what time data is available
        print(f"\n📋 SINGLE HOUR FIELDSET INFO:")
        print(f"   Available time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")
        print(f"   Time values: {fieldset.U.grid.time}")
        
        # Set up particle release locations (SAME as hourly test)
        lon_min, lon_max = fieldset.U.grid.lon.min(), fieldset.U.grid.lon.max()
        lat_min, lat_max = fieldset.U.grid.lat.min(), fieldset.U.grid.lat.max()
        
        lon_center = (lon_min + lon_max) / 2
        lat_center = (lat_min + lat_max) / 2
        
        # Release 6 particles in a 2x3 grid (SAME as hourly test)
        lons = [lon_center - 0.02, lon_center, lon_center + 0.02] * 2
        lats = [lat_center - 0.01] * 3 + [lat_center + 0.01] * 3
        
        release_locations = {
            'lons': lons,
            'lats': lats,
            'plastic_amount': [1.0] * 6
        }
        
        print(f"🎯 Releasing 6 particles in 2×3 grid at {lon_center:.3f}°E, {lat_center:.3f}°N")
        print(f"⏱️  Simulation: 1.5 days with SINGLE HOUR per day data")
        
        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)
        print(f"✓ Created {pset.size} particles")
        
        # Run simulation
        print("🌊 Running single-hour diagnostic simulation...")
        output_file = os.path.join(data_dir, 'mobile_single_hour_trajectories.zarr')
        
        pset.execute(
            parcels.AdvectionRK4,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )
        
        print("✅ Single-hour diagnostic simulation completed!")
        print(f"✓ Trajectories saved to: {output_file}")
        
        # Quick analysis of results
        print("\n📊 SINGLE HOUR SIMULATION RESULTS:")
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
            plot_success = plot_trajectories_comparison(output_file, data_dir, "single_hour")
            if plot_success:
                print(f"   ✓ Single-hour trajectory plot saved!")
        except Exception as e:
            print(f"   Could not create trajectory plot: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main test function."""
    
    print("🏖️  MOBILE BAY SINGLE HOUR DIAGNOSTIC TEST 🏖️")
    print("=" * 60)
    print()
    print("This test uses only ONE time step per day to compare")
    print("with the full hourly resolution results.")
    print()
    
    # Check if data directory exists
    data_dir = 'mobile_single_hour'
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("   Please run mobile_schism_single_hour.py first!")
        return False
    
    print(f"✓ Found data directory: {data_dir}")
    
    # Test single-hour simulation
    simulation_success = test_single_hour_simulation(data_dir)
    
    # Summary
    print("\n📊 SINGLE HOUR DIAGNOSTIC SUMMARY:")
    print("=" * 40)
    print(f"   Single-hour simulation: {'✅ PASS' if simulation_success else '❌ FAIL'}")
    
    if simulation_success:
        print("\n🎉 SINGLE HOUR DIAGNOSTIC COMPLETED! 🎉")
        print("=" * 45)
        print("✅ Single-hour simulation successful!")
        print("✅ Ready for comparison with hourly results!")
        print()
        print("🔍 COMPARISON ANALYSIS:")
        print("   Compare these files:")
        print("   • mobile_daily_format/mobile_bay_trajectories.png (HOURLY)")
        print("   • mobile_single_hour/mobile_bay_trajectories_single_hour.png (DAILY)")
        print()
        print("   Look for differences in:")
        print("   • Particle end positions")
        print("   • Trajectory shapes")
        print("   • Dispersion patterns")
        print("   • Net displacement")
        
        return True
    else:
        print("\n❌ Single hour diagnostic failed.")
        return False

if __name__ == "__main__":
    main()
