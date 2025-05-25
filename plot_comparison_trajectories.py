#!/usr/bin/env python3
"""
Plot comparison of single vs full hourly trajectories on the same plot
"""

import os
import numpy as np

def plot_comparison_trajectories():
    """Plot single and full trajectories together for comparison."""
    
    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend for headless servers
        import matplotlib.pyplot as plt
        import xarray as xr
        
        print("🎨 CREATING COMPARISON TRAJECTORY PLOT 🎨")
        print("=" * 50)
        
        # File paths
        full_file = 'mobile_6hour_full/trajectories_full.zarr'
        single_file = 'mobile_6hour_single/trajectories_single.zarr'
        
        # Check if files exist
        if not os.path.exists(full_file):
            print(f"❌ Full trajectory file not found: {full_file}")
            return False
            
        if not os.path.exists(single_file):
            print(f"❌ Single trajectory file not found: {single_file}")
            return False
        
        print("✓ Both trajectory files found")
        
        # Load datasets
        print("\n📊 Loading trajectory data...")
        
        full_ds = xr.open_zarr(full_file)
        single_ds = xr.open_zarr(single_file)
        
        print(f"Full dataset shape: {full_ds.lon.shape}")
        print(f"Single dataset shape: {single_ds.lon.shape}")
        
        # Get trajectory data
        full_lons = full_ds.lon.values
        full_lats = full_ds.lat.values
        single_lons = single_ds.lon.values
        single_lats = single_ds.lat.values
        
        # Create comparison plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 10))
        
        # Define colors for particles
        colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown', 'pink', 'gray']
        
        print("\n🎯 Plotting trajectories...")
        
        # Function to plot trajectories from a dataset
        def plot_trajectories(lons, lats, linestyle, label_prefix, alpha=0.8):
            if len(lons.shape) == 2:
                # Determine if (particles, time) or (time, particles)
                if lons.shape[0] < lons.shape[1]:
                    # (particles, time)
                    n_particles = lons.shape[0]
                    for p in range(min(n_particles, len(colors))):
                        p_lons = lons[p, :]
                        p_lats = lats[p, :]
                        
                        valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                        if np.any(valid):
                            ax.plot(p_lons[valid], p_lats[valid], 
                                   linestyle=linestyle, color=colors[p], 
                                   linewidth=2, alpha=alpha, 
                                   label=f'{label_prefix} P{p+1}')
                            
                            # Mark start and end points
                            if len(p_lons[valid]) > 0:
                                ax.plot(p_lons[valid][0], p_lats[valid][0], 
                                       'o', color=colors[p], markersize=6, 
                                       markeredgecolor='black', markeredgewidth=1)
                                if len(p_lons[valid]) > 1:
                                    ax.plot(p_lons[valid][-1], p_lats[valid][-1], 
                                           's', color=colors[p], markersize=6, 
                                           markeredgecolor='black', markeredgewidth=1)
                else:
                    # (time, particles)
                    n_particles = lons.shape[1]
                    for p in range(min(n_particles, len(colors))):
                        p_lons = lons[:, p]
                        p_lats = lats[:, p]
                        
                        valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                        if np.any(valid):
                            ax.plot(p_lons[valid], p_lats[valid], 
                                   linestyle=linestyle, color=colors[p], 
                                   linewidth=2, alpha=alpha, 
                                   label=f'{label_prefix} P{p+1}')
                            
                            # Mark start and end points
                            if len(p_lons[valid]) > 0:
                                ax.plot(p_lons[valid][0], p_lats[valid][0], 
                                       'o', color=colors[p], markersize=6, 
                                       markeredgecolor='black', markeredgewidth=1)
                                if len(p_lons[valid]) > 1:
                                    ax.plot(p_lons[valid][-1], p_lats[valid][-1], 
                                           's', color=colors[p], markersize=6, 
                                           markeredgecolor='black', markeredgewidth=1)
            else:
                # 1D trajectory
                valid = ~np.isnan(lons) & ~np.isnan(lats)
                if np.any(valid):
                    ax.plot(lons[valid], lats[valid], 
                           linestyle=linestyle, color=colors[0], 
                           linewidth=2, alpha=alpha, 
                           label=f'{label_prefix} Trajectory')
                    
                    # Mark start and end points
                    if len(lons[valid]) > 0:
                        ax.plot(lons[valid][0], lats[valid][0], 
                               'o', color=colors[0], markersize=6, 
                               markeredgecolor='black', markeredgewidth=1)
                        if len(lons[valid]) > 1:
                            ax.plot(lons[valid][-1], lats[valid][-1], 
                                   's', color=colors[0], markersize=6, 
                                   markeredgecolor='black', markeredgewidth=1)
        
        # Plot single time trajectories (solid lines)
        print("   Plotting single time trajectories (solid lines)...")
        plot_trajectories(single_lons, single_lats, '-', 'Single', alpha=0.9)
        
        # Plot full hourly trajectories (dashed lines)
        print("   Plotting full hourly trajectories (dashed lines)...")
        plot_trajectories(full_lons, full_lats, '--', 'Hourly', alpha=0.7)
        
        # Customize plot
        ax.set_xlabel('Longitude (°E)', fontsize=14)
        ax.set_ylabel('Latitude (°N)', fontsize=14)
        ax.set_title('Mobile Bay Trajectory Comparison\nSingle Time (solid) vs Hourly Resolution (dashed)', 
                    fontsize=16, fontweight='bold')
        
        ax.grid(True, alpha=0.3)
        ax.set_aspect('equal', adjustable='box')
        
        # Create legend
        ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
        
        # Add annotations
        ax.text(0.02, 0.98, '● Start  ■ End', transform=ax.transAxes, 
               verticalalignment='top', fontsize=12, 
               bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
        
        ax.text(0.02, 0.02, 'Solid = Constant velocity\nDashed = Hourly resolution', 
               transform=ax.transAxes, verticalalignment='bottom', fontsize=12,
               bbox=dict(boxstyle='round', facecolor='lightblue', alpha=0.8))
        
        plt.tight_layout()
        
        # Save plot
        output_file = 'mobile_bay_trajectory_comparison.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.close()
        
        # Close datasets
        full_ds.close()
        single_ds.close()
        
        print(f"\n✅ Comparison plot saved: {output_file}")
        
        # Print summary statistics
        print(f"\n📊 TRAJECTORY COMPARISON SUMMARY:")
        
        # Calculate displacement differences
        if len(full_lons.shape) == 2 and len(single_lons.shape) == 2:
            # Get final positions
            if full_lons.shape[0] < full_lons.shape[1]:  # (particles, time)
                full_final_lons = full_lons[:, -1]
                full_final_lats = full_lats[:, -1]
                single_final_lons = single_lons[:, -1]
                single_final_lats = single_lats[:, -1]
            else:  # (time, particles)
                full_final_lons = full_lons[-1, :]
                full_final_lats = full_lats[-1, :]
                single_final_lons = single_lons[-1, :]
                single_final_lats = single_lats[-1, :]
            
            # Calculate differences
            for p in range(min(len(full_final_lons), len(single_final_lons))):
                if not (np.isnan(full_final_lons[p]) or np.isnan(single_final_lons[p])):
                    dx = (full_final_lons[p] - single_final_lons[p]) * 111.32 * np.cos(np.radians(full_final_lats[p]))
                    dy = (full_final_lats[p] - single_final_lats[p]) * 111.32
                    distance = np.sqrt(dx**2 + dy**2)
                    print(f"   Particle {p+1} final position difference: {distance:.2f} km")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating comparison plot: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main function."""
    
    success = plot_comparison_trajectories()
    
    if success:
        print(f"\n🎉 TRAJECTORY COMPARISON COMPLETED! 🎉")
        print("=" * 45)
        print("✅ Comparison plot created: mobile_bay_trajectory_comparison.png")
        print("✅ Shows impact of temporal resolution on particle transport")
        print("\n🔍 Visual comparison shows:")
        print("   • Solid lines = Constant velocity (single time step)")
        print("   • Dashed lines = Time-varying velocity (hourly resolution)")
        print("   • Different colors = Different particles")
        print("   • Circles = Start positions, Squares = End positions")
    else:
        print(f"\n❌ Trajectory comparison failed!")

if __name__ == "__main__":
    main()
