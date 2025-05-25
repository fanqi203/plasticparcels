#!/usr/bin/env python3
"""
Simple trajectory plotting script
"""

import os
import numpy as np

def plot_trajectories_simple(trajectory_file, output_dir, suffix, sim_name):
    """Simple trajectory plotting function."""
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend for headless servers
        import matplotlib.pyplot as plt
        import xarray as xr
        
        print(f"   📊 Plotting {sim_name} trajectories...")
        
        traj_ds = xr.open_zarr(trajectory_file)
        
        # Print dataset info
        print(f"   Dataset dimensions: {dict(traj_ds.dims)}")
        print(f"   Dataset variables: {list(traj_ds.data_vars)}")
        
        # Get lon/lat data
        lons = traj_ds.lon.values
        lats = traj_ds.lat.values
        
        print(f"   Lon/lat shape: {lons.shape}")
        print(f"   Lon range: {np.nanmin(lons):.4f} to {np.nanmax(lons):.4f}")
        print(f"   Lat range: {np.nanmin(lats):.4f} to {np.nanmax(lats):.4f}")
        
        fig, ax = plt.subplots(1, 1, figsize=(10, 8))
        
        # Simple plotting - just plot all trajectories
        if len(lons.shape) == 2:
            # 2D array: assume (particles, time) or (time, particles)
            if lons.shape[0] < lons.shape[1]:
                # Likely (particles, time)
                n_particles = lons.shape[0]
                for p in range(n_particles):
                    p_lons = lons[p, :]
                    p_lats = lats[p, :]
                    
                    valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                    if np.any(valid):
                        ax.plot(p_lons[valid], p_lats[valid], 'o-', 
                               linewidth=2, markersize=3, alpha=0.8, 
                               label=f'Particle {p+1}')
            else:
                # Likely (time, particles)
                n_particles = lons.shape[1]
                for p in range(n_particles):
                    p_lons = lons[:, p]
                    p_lats = lats[:, p]
                    
                    valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                    if np.any(valid):
                        ax.plot(p_lons[valid], p_lats[valid], 'o-', 
                               linewidth=2, markersize=3, alpha=0.8, 
                               label=f'Particle {p+1}')
        else:
            # 1D array: single trajectory
            valid = ~np.isnan(lons) & ~np.isnan(lats)
            if np.any(valid):
                ax.plot(lons[valid], lats[valid], 'o-', 
                       linewidth=2, markersize=3, alpha=0.8, 
                       label='Trajectory')
        
        ax.set_xlabel('Longitude (°E)', fontsize=12)
        ax.set_ylabel('Latitude (°N)', fontsize=12)
        ax.set_title(f'Mobile Bay Trajectories - {sim_name}\n(1-hour simulation)', 
                    fontsize=14, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        ax.legend(fontsize=10)
        ax.set_aspect('equal', adjustable='box')
        
        plt.tight_layout()
        
        plot_file = os.path.join(output_dir, f'trajectories_{suffix}.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        traj_ds.close()
        
        print(f"   ✓ Plot saved: {plot_file}")
        return True
        
    except Exception as e:
        print(f"   ❌ Error creating plot: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Test plotting function."""
    
    print("🎨 SIMPLE TRAJECTORY PLOTTING TEST 🎨")
    print("=" * 45)
    
    datasets = [
        ('mobile_6hour_full', 'trajectories_full.zarr', 'full', 'Full Hourly'),
        ('mobile_6hour_single', 'trajectories_single.zarr', 'single', 'Single Time')
    ]
    
    for data_dir, traj_file, suffix, sim_name in datasets:
        print(f"\n--- {sim_name} ---")
        
        traj_path = os.path.join(data_dir, traj_file)
        
        if os.path.exists(traj_path):
            success = plot_trajectories_simple(traj_path, data_dir, suffix, sim_name)
            if success:
                print(f"✅ {sim_name} plot created successfully!")
            else:
                print(f"❌ {sim_name} plot failed!")
        else:
            print(f"❌ Trajectory file not found: {traj_path}")
    
    print(f"\n🎉 PLOTTING TEST COMPLETED! 🎉")
    print("Check for PNG files in the dataset directories.")

if __name__ == "__main__":
    main()
