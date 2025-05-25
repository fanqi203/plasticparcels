#!/usr/bin/env python3
"""
Debug script to check why trajectories are not being plotted
"""

import os
import numpy as np

def check_trajectory_files():
    """Check if trajectory files exist and can be read."""

    print("🔍 CHECKING TRAJECTORY FILES")
    print("=" * 35)

    datasets = [
        ('mobile_6hour_full', 'trajectories_full.zarr'),
        ('mobile_6hour_single', 'trajectories_single.zarr')
    ]

    for data_dir, traj_file in datasets:
        print(f"\n📊 {data_dir}:")

        traj_path = os.path.join(data_dir, traj_file)

        if os.path.exists(traj_path):
            print(f"   ✓ Trajectory file exists: {traj_path}")

            try:
                import xarray as xr
                traj_ds = xr.open_zarr(traj_path)

                print(f"   ✓ Can open trajectory file")
                print(f"   Dimensions: {dict(traj_ds.dims)}")
                print(f"   Variables: {list(traj_ds.data_vars)}")

                if 'lon' in traj_ds and 'lat' in traj_ds:
                    print(f"   ✓ Has lon/lat variables")

                    # Check data
                    lons = traj_ds.lon.values
                    lats = traj_ds.lat.values

                    print(f"   Lon range: {np.nanmin(lons):.4f} to {np.nanmax(lons):.4f}")
                    print(f"   Lat range: {np.nanmin(lats):.4f} to {np.nanmax(lats):.4f}")
                    print(f"   Valid points: {np.sum(~np.isnan(lons))}/{lons.size}")

                else:
                    print(f"   ❌ Missing lon/lat variables")

                traj_ds.close()

            except Exception as e:
                print(f"   ❌ Error reading trajectory file: {e}")
        else:
            print(f"   ❌ Trajectory file not found: {traj_path}")

def check_matplotlib():
    """Check if matplotlib is available and working."""

    print(f"\n🎨 CHECKING MATPLOTLIB")
    print("=" * 25)

    try:
        import matplotlib
        matplotlib.use('Agg')  # Use non-interactive backend for headless servers
        print(f"   ✓ matplotlib version: {matplotlib.__version__}")
        print(f"   ✓ Using backend: {matplotlib.get_backend()}")

        import matplotlib.pyplot as plt
        print(f"   ✓ pyplot imported successfully")

        # Test basic plotting
        fig, ax = plt.subplots(1, 1, figsize=(6, 4))
        ax.plot([0, 1], [0, 1], 'o-')
        ax.set_title('Test Plot')

        test_file = 'test_plot.png'
        plt.savefig(test_file, dpi=150)
        plt.close()

        if os.path.exists(test_file):
            print(f"   ✓ Can create and save plots")
            os.remove(test_file)
        else:
            print(f"   ❌ Cannot save plots")

    except ImportError as e:
        print(f"   ❌ matplotlib not available: {e}")
    except Exception as e:
        print(f"   ❌ matplotlib error: {e}")

def test_plotting_function():
    """Test the actual plotting function."""

    print(f"\n🧪 TESTING PLOTTING FUNCTION")
    print("=" * 35)

    datasets = [
        ('mobile_6hour_full', 'trajectories_full.zarr', 'full', 'Full Hourly'),
        ('mobile_6hour_single', 'trajectories_single.zarr', 'single', 'Single Time')
    ]

    for data_dir, traj_file, suffix, sim_name in datasets:
        print(f"\n--- {sim_name} ---")

        traj_path = os.path.join(data_dir, traj_file)

        if not os.path.exists(traj_path):
            print(f"   ❌ Trajectory file not found: {traj_path}")
            continue

        try:
            import matplotlib
            matplotlib.use('Agg')  # Use non-interactive backend for headless servers
            import matplotlib.pyplot as plt
            import xarray as xr

            traj_ds = xr.open_zarr(traj_path)

            fig, ax = plt.subplots(1, 1, figsize=(10, 8))

            n_particles = traj_ds.dims['traj']
            colors = plt.cm.tab10(np.linspace(0, 1, n_particles))

            print(f"   Processing {n_particles} particles...")

            for p in range(n_particles):
                lons = traj_ds.lon.isel(traj=p).values
                lats = traj_ds.lat.isel(traj=p).values

                valid_mask = ~np.isnan(lons) & ~np.isnan(lats)
                valid_count = np.sum(valid_mask)

                print(f"   Particle {p+1}: {valid_count} valid points")

                if np.any(valid_mask):
                    lons_clean = lons[valid_mask]
                    lats_clean = lats[valid_mask]

                    ax.plot(lons_clean, lats_clean, 'o-', color=colors[p],
                           linewidth=2, markersize=4, alpha=0.8, label=f'Particle {p+1}')

                    if len(lons_clean) > 0:
                        ax.plot(lons_clean[0], lats_clean[0], 's', color=colors[p],
                               markersize=8, markeredgecolor='black', markeredgewidth=1)
                        if len(lons_clean) > 1:
                            ax.plot(lons_clean[-1], lats_clean[-1], '^', color=colors[p],
                                   markersize=8, markeredgecolor='black', markeredgewidth=1)

            ax.set_xlabel('Longitude (°E)', fontsize=12)
            ax.set_ylabel('Latitude (°N)', fontsize=12)
            ax.set_title(f'Mobile Bay Plastic Trajectories - {sim_name.upper()}\n(1-hour simulation)',
                        fontsize=14, fontweight='bold')

            ax.grid(True, alpha=0.3)
            ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=10)
            ax.text(0.02, 0.98, '■ Start  ▲ End', transform=ax.transAxes,
                   verticalalignment='top', fontsize=10,
                   bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))

            ax.set_aspect('equal', adjustable='box')
            plt.tight_layout()

            plot_file = os.path.join(data_dir, f'trajectories_{suffix}.png')
            plt.savefig(plot_file, dpi=300, bbox_inches='tight')
            plt.close()

            traj_ds.close()

            if os.path.exists(plot_file):
                print(f"   ✓ Plot saved successfully: {plot_file}")
            else:
                print(f"   ❌ Plot file not created: {plot_file}")

        except Exception as e:
            print(f"   ❌ Error creating plot: {e}")
            import traceback
            traceback.print_exc()

def main():
    """Main debug function."""

    print("🐛 TRAJECTORY PLOTTING DEBUG 🐛")
    print("=" * 40)

    check_trajectory_files()
    check_matplotlib()
    test_plotting_function()

    print(f"\n📋 SUMMARY")
    print("=" * 15)
    print("Check the output above to identify the issue:")
    print("1. Are trajectory files being created?")
    print("2. Is matplotlib available and working?")
    print("3. Are there errors in the plotting function?")

if __name__ == "__main__":
    main()
