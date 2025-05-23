#!/usr/bin/env python3
"""
Complete SCHISM to PlasticParcels Integration Script

This script provides a complete workflow for:
1. Loading SCHISM unstructured grid output
2. Regridding to NEMO-compatible structured format
3. Running PlasticParcels simulations
4. Creating trajectory visualizations

Usage:
    python schism_to_plasticparcels_complete.py --schism_file /path/to/schism/out2d_1.nc

Author: AI Assistant for PlasticParcels Integration
Date: 2024
"""

import argparse
import os
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import parcels
from datetime import datetime, timedelta
from scipy.interpolate import griddata
import json

class SCHISMToPlasticParcels:
    """
    Complete workflow class for SCHISM to PlasticParcels integration.
    """

    def __init__(self, schism_file, output_dir='schism_nemo_output', target_resolution=0.01,
                 lon_bounds=None, lat_bounds=None):
        """
        Initialize the converter.

        Parameters:
        -----------
        schism_file : str
            Path to SCHISM output file
        output_dir : str
            Directory for NEMO-format output files
        target_resolution : float
            Target grid resolution in degrees
        lon_bounds : tuple or None
            (lon_min, lon_max) to subset domain, None for full domain
        lat_bounds : tuple or None
            (lat_min, lat_max) to subset domain, None for full domain
        """
        self.schism_file = schism_file
        self.output_dir = output_dir
        self.target_resolution = target_resolution
        self.lon_bounds = lon_bounds
        self.lat_bounds = lat_bounds

        # Create output directory
        os.makedirs(output_dir, exist_ok=True)

    def load_schism_data(self):
        """Load and analyze SCHISM data with optional spatial subsetting."""
        print("1. Loading SCHISM data...")

        self.ds = xr.open_dataset(self.schism_file)

        # Extract coordinates
        all_lons = self.ds['SCHISM_hgrid_node_x'].values
        all_lats = self.ds['SCHISM_hgrid_node_y'].values
        all_depths = self.ds['depth'].values

        print(f"   ✓ Full domain: {len(all_lons)} nodes")
        print(f"   ✓ Full longitude range: {all_lons.min():.3f} to {all_lons.max():.3f}°")
        print(f"   ✓ Full latitude range: {all_lats.min():.3f} to {all_lats.max():.3f}°")

        # Apply spatial subsetting if bounds specified
        if self.lon_bounds is not None or self.lat_bounds is not None:
            print("   • Applying spatial subsetting...")

            # Default bounds if not specified
            lon_min = self.lon_bounds[0] if self.lon_bounds else all_lons.min()
            lon_max = self.lon_bounds[1] if self.lon_bounds else all_lons.max()
            lat_min = self.lat_bounds[0] if self.lat_bounds else all_lats.min()
            lat_max = self.lat_bounds[1] if self.lat_bounds else all_lats.max()

            # Create spatial mask
            spatial_mask = ((all_lons >= lon_min) & (all_lons <= lon_max) &
                           (all_lats >= lat_min) & (all_lats <= lat_max))

            # Apply mask
            self.lons = all_lons[spatial_mask]
            self.lats = all_lats[spatial_mask]
            self.depths = all_depths[spatial_mask]
            self.spatial_mask = spatial_mask

            print(f"   ✓ Subset domain: {len(self.lons)} nodes ({len(self.lons)/len(all_lons)*100:.1f}% of full domain)")
            print(f"   ✓ Subset bounds: {lon_min:.3f} to {lon_max:.3f}°E, {lat_min:.3f} to {lat_max:.3f}°N")

            if len(self.lons) == 0:
                raise ValueError(f"No SCHISM nodes found in specified bounds: "
                               f"lon=[{lon_min}, {lon_max}], lat=[{lat_min}, {lat_max}]")
        else:
            # Use full domain
            self.lons = all_lons
            self.lats = all_lats
            self.depths = all_depths
            self.spatial_mask = None
            print("   ✓ Using full domain (no spatial subsetting)")

        print(f"   ✓ Final longitude range: {self.lons.min():.3f} to {self.lons.max():.3f}°")
        print(f"   ✓ Final latitude range: {self.lats.min():.3f} to {self.lats.max():.3f}°")
        print(f"   ✓ Depth range: {self.depths.min():.1f} to {self.depths.max():.1f} m")

    def create_target_grid(self):
        """Create regular target grid."""
        print("2. Creating target regular grid...")

        # Define grid bounds
        lon_min, lon_max = self.lons.min(), self.lons.max()
        lat_min, lat_max = self.lats.min(), self.lats.max()

        # Create regular grid
        self.target_lons = np.arange(lon_min, lon_max + self.target_resolution, self.target_resolution)
        self.target_lats = np.arange(lat_min, lat_max + self.target_resolution, self.target_resolution)
        self.target_lon_2d, self.target_lat_2d = np.meshgrid(self.target_lons, self.target_lats)

        print(f"   ✓ Target grid: {len(self.target_lats)} × {len(self.target_lons)} points")
        print(f"   ✓ Resolution: {self.target_resolution}° ({self.target_resolution * 111.32:.1f} km)")

    def regrid_variables(self):
        """Regrid SCHISM variables to regular grid with spatial subsetting support."""
        print("3. Regridding variables...")

        self.regridded_data = {}

        # Extract data with spatial subsetting if applied
        if self.spatial_mask is not None:
            # Apply spatial mask to data variables
            u_data = self.ds['depthAverageVelX'][0, :].values[self.spatial_mask]
            v_data = self.ds['depthAverageVelY'][0, :].values[self.spatial_mask]
            elev_data = self.ds['elevation'][0, :].values[self.spatial_mask]
            print(f"   • Using {len(u_data)} nodes from spatial subset")
        else:
            # Use full domain data
            u_data = self.ds['depthAverageVelX'][0, :].values
            v_data = self.ds['depthAverageVelY'][0, :].values
            elev_data = self.ds['elevation'][0, :].values
            print(f"   • Using all {len(u_data)} nodes from full domain")

        # Velocity components
        print("   • Regridding U velocity (depthAverageVelX)...")
        u_regridded = griddata(
            points=np.column_stack([self.lons, self.lats]),
            values=u_data,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(self.target_lon_2d.shape)
        self.regridded_data['U'] = u_regridded

        print("   • Regridding V velocity (depthAverageVelY)...")
        v_regridded = griddata(
            points=np.column_stack([self.lons, self.lats]),
            values=v_data,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(self.target_lon_2d.shape)
        self.regridded_data['V'] = v_regridded

        # W velocity (zeros for 2D)
        print("   • Setting W velocity to zero (2D case)...")
        self.regridded_data['W'] = np.zeros_like(u_regridded)

        # Surface elevation as temperature proxy
        print("   • Regridding elevation...")
        elev_regridded = griddata(
            points=np.column_stack([self.lons, self.lats]),
            values=elev_data,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(self.target_lon_2d.shape)
        self.regridded_data['elevation'] = elev_regridded

        # Bathymetry
        print("   • Regridding bathymetry...")
        bathy_regridded = griddata(
            points=np.column_stack([self.lons, self.lats]),
            values=self.depths,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(self.target_lon_2d.shape)
        self.regridded_data['bathymetry'] = bathy_regridded

        print("   ✓ All variables regridded successfully")

        # Print regridding statistics
        speed_field = np.sqrt(self.regridded_data['U']**2 + self.regridded_data['V']**2)
        print(f"   ✓ Current speed range: {speed_field.min():.3f} to {speed_field.max():.3f} m/s")
        print(f"   ✓ Elevation range: {self.regridded_data['elevation'].min():.3f} to {self.regridded_data['elevation'].max():.3f} m")

    def save_nemo_format(self):
        """Save regridded data in NEMO format."""
        print("4. Saving NEMO-compatible files...")

        # Create coordinate variables
        coords = {
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
            'time_counter': ('time_counter', [0])
        }

        # Save each variable in separate file
        variables = {
            'U': ('vozocrtx', self.regridded_data['U']),
            'V': ('vomecrty', self.regridded_data['V']),
            'W': ('vovecrtz', self.regridded_data['W']),
            'T': ('votemper', self.regridded_data['elevation']),
            'S': ('vosaline', np.full_like(self.regridded_data['U'], 35.0))
        }

        for var_letter, (nemo_var, data) in variables.items():
            ds = xr.Dataset({
                nemo_var: (['time_counter', 'y', 'x'], data[np.newaxis, :, :])
            }, coords=coords)

            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': 'SCHISM regridded to NEMO format',
                'institution': 'PlasticParcels Regridder'
            })

            filename = f"{var_letter}_{os.path.basename(self.schism_file).split('.')[0]}.nc"
            filepath = os.path.join(self.output_dir, filename)
            ds.to_netcdf(filepath)
            print(f"   ✓ Saved {filepath}")

        # Save mesh file
        mesh_ds = xr.Dataset({
            'glamf': (['y', 'x'], self.target_lon_2d),
            'gphif': (['y', 'x'], self.target_lat_2d),
        })
        mesh_file = os.path.join(self.output_dir, 'ocean_mesh_hgr.nc')
        mesh_ds.to_netcdf(mesh_file)
        print(f"   ✓ Saved {mesh_file}")

        # Save bathymetry file
        mbathy = np.ones_like(self.regridded_data['bathymetry'], dtype=int)
        mbathy[self.regridded_data['bathymetry'] <= 0] = 0  # Land areas

        bathy_ds = xr.Dataset({
            'mbathy': (['time_counter', 'y', 'x'], mbathy[np.newaxis, :, :]),
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
        })
        bathy_file = os.path.join(self.output_dir, 'bathymetry_mesh_zgr.nc')
        bathy_ds.to_netcdf(bathy_file)
        print(f"   ✓ Saved {bathy_file}")

    def create_settings_file(self):
        """Create PlasticParcels settings file."""
        print("5. Creating PlasticParcels settings file...")

        base_filename = os.path.basename(self.schism_file).split('.')[0]

        settings = {
            "use_3D": False,
            "allow_time_extrapolation": True,
            "verbose_delete": False,
            "use_mixing": False,
            "use_biofouling": False,
            "use_stokes": False,
            "use_wind": False,
            "ocean": {
                "modelname": "NEMO0083",
                "directory": f"{self.output_dir}/",
                "filename_style": base_filename,
                "ocean_mesh": "ocean_mesh_hgr.nc",
                "bathymetry_mesh": "bathymetry_mesh_zgr.nc",
                "variables": {
                    "U": "vozocrtx",
                    "V": "vomecrty",
                    "W": "vovecrtz",
                    "conservative_temperature": "votemper",
                    "absolute_salinity": "vosaline"
                },
                "dimensions": {
                    "U": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "V": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "W": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "conservative_temperature": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"},
                    "absolute_salinity": {"lon": "nav_lon", "lat": "nav_lat", "time": "time_counter"}
                },
                "indices": {},
                "bathymetry_variables": {"bathymetry": "mbathy"},
                "bathymetry_dimensions": {"lon": "nav_lon", "lat": "nav_lat"}
            }
        }

        self.settings_file = os.path.join(self.output_dir, f'{base_filename}_settings.json')
        with open(self.settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"   ✓ Saved {self.settings_file}")

    def run_simulation(self, simulation_hours=6, num_particles=16, release_locations=None):
        """Run PlasticParcels simulation with configurable release locations."""
        print("6. Running PlasticParcels simulation...")

        # Load regridded data
        base_filename = os.path.basename(self.schism_file).split('.')[0]
        filenames = {
            'U': os.path.join(self.output_dir, f'U_{base_filename}.nc'),
            'V': os.path.join(self.output_dir, f'V_{base_filename}.nc'),
        }

        variables = {'U': 'vozocrtx', 'V': 'vomecrty'}
        dimensions = {
            'U': {'lon': 'nav_lon', 'lat': 'nav_lat', 'time': 'time_counter'},
            'V': {'lon': 'nav_lon', 'lat': 'nav_lat', 'time': 'time_counter'},
        }

        # Create fieldset
        fieldset = parcels.FieldSet.from_netcdf(
            filenames, variables, dimensions,
            mesh='spherical', allow_time_extrapolation=True
        )

        # Create release locations
        if release_locations is not None:
            # Use provided release locations
            if isinstance(release_locations, dict):
                # Format: {'lons': [lon1, lon2, ...], 'lats': [lat1, lat2, ...]}
                release_grid_lons = release_locations['lons']
                release_grid_lats = release_locations['lats']
            elif isinstance(release_locations, list):
                # Format: [(lon1, lat1), (lon2, lat2), ...]
                release_grid_lons = [loc[0] for loc in release_locations]
                release_grid_lats = [loc[1] for loc in release_locations]
            else:
                raise ValueError("release_locations must be dict with 'lons'/'lats' keys or list of (lon,lat) tuples")

            print(f"   ✓ Using {len(release_grid_lons)} custom release locations")

            # Validate release locations are within domain
            domain_lon_min, domain_lon_max = self.lons.min(), self.lons.max()
            domain_lat_min, domain_lat_max = self.lats.min(), self.lats.max()

            for i, (lon, lat) in enumerate(zip(release_grid_lons, release_grid_lats)):
                if not (domain_lon_min <= lon <= domain_lon_max and domain_lat_min <= lat <= domain_lat_max):
                    print(f"   ⚠️  Warning: Release location {i+1} ({lon:.3f}, {lat:.3f}) is outside domain bounds")
                    print(f"      Domain: [{domain_lon_min:.3f}, {domain_lon_max:.3f}]°E, [{domain_lat_min:.3f}, {domain_lat_max:.3f}]°N")
        else:
            # Create default grid of release locations
            n_side = int(np.sqrt(num_particles))
            release_lons = np.linspace(self.lons.min() + 0.1, self.lons.max() - 0.1, n_side)
            release_lats = np.linspace(self.lats.min() + 0.1, self.lats.max() - 0.1, n_side)

            release_grid_lons = []
            release_grid_lats = []
            for lon in release_lons:
                for lat in release_lats:
                    release_grid_lons.append(lon)
                    release_grid_lats.append(lat)

            print(f"   ✓ Created {len(release_grid_lons)} default release locations in {n_side}×{n_side} grid")

        # Print release location summary
        print(f"   ✓ Release longitude range: {min(release_grid_lons):.3f} to {max(release_grid_lons):.3f}°")
        print(f"   ✓ Release latitude range: {min(release_grid_lats):.3f} to {max(release_grid_lats):.3f}°")

        # Create particles
        pset = parcels.ParticleSet.from_list(
            fieldset=fieldset,
            pclass=parcels.JITParticle,
            lon=release_grid_lons,
            lat=release_grid_lats
        )

        print(f"   ✓ Created {len(pset)} particles")

        # Store initial positions
        initial_lons = np.array(pset.lon.copy())
        initial_lats = np.array(pset.lat.copy())

        # Track trajectories
        trajectory_lons = [initial_lons.copy()]
        trajectory_lats = [initial_lats.copy()]
        times = [0]

        # Run simulation
        kernel = parcels.AdvectionRK4
        dt = timedelta(minutes=20)
        total_time = timedelta(hours=simulation_hours)
        step_time = timedelta(hours=1)

        current_time = timedelta(0)
        while current_time < total_time:
            pset.execute(kernel, runtime=step_time, dt=dt)
            current_time += step_time

            trajectory_lons.append(np.array(pset.lon.copy()))
            trajectory_lats.append(np.array(pset.lat.copy()))
            times.append(current_time.total_seconds() / 3600)

        print(f"   ✓ Simulation completed ({simulation_hours} hours)")

        # Store results
        self.trajectory_lons = trajectory_lons
        self.trajectory_lats = trajectory_lats
        self.times = times
        self.release_grid_lons = release_grid_lons
        self.release_grid_lats = release_grid_lats

        return trajectory_lons, trajectory_lats, times

    def create_visualization(self):
        """Create comprehensive trajectory visualization."""
        print("7. Creating trajectory visualization...")

        # Load velocity field for background
        base_filename = os.path.basename(self.schism_file).split('.')[0]
        u_data = xr.open_dataset(os.path.join(self.output_dir, f'U_{base_filename}.nc'))
        v_data = xr.open_dataset(os.path.join(self.output_dir, f'V_{base_filename}.nc'))

        u_field = u_data['vozocrtx'][0, :, :].values
        v_field = v_data['vomecrty'][0, :, :].values
        speed_field = np.sqrt(u_field**2 + v_field**2)

        # Create figure
        fig = plt.figure(figsize=(20, 12))

        # Plot 1: Main trajectory map
        ax1 = plt.subplot(2, 3, 1)

        # Background velocity field
        speed_plot = ax1.contourf(self.target_lon_2d, self.target_lat_2d, speed_field,
                                 levels=20, cmap='Blues', alpha=0.7)
        plt.colorbar(speed_plot, ax=ax1, label='Current Speed (m/s)', shrink=0.8)

        # Velocity vectors
        skip = max(1, len(self.target_lons) // 20)
        u_sub = u_field[::skip, ::skip]
        v_sub = v_field[::skip, ::skip]
        lons_sub = self.target_lon_2d[::skip, ::skip]
        lats_sub = self.target_lat_2d[::skip, ::skip]

        ax1.quiver(lons_sub, lats_sub, u_sub, v_sub,
                  alpha=0.6, scale=5, width=0.003, color='darkblue')

        # Plot trajectories
        colors = plt.cm.Set3(np.linspace(0, 1, len(self.release_grid_lons)))

        for i in range(len(self.release_grid_lons)):
            traj_lons = [pos[i] for pos in self.trajectory_lons]
            traj_lats = [pos[i] for pos in self.trajectory_lats]

            ax1.plot(traj_lons, traj_lats, 'o-',
                    color=colors[i], linewidth=2, markersize=4, alpha=0.8)

            # Mark start and end
            ax1.plot(traj_lons[0], traj_lats[0], 'o',
                    color='red', markersize=10, markeredgecolor='black',
                    markeredgewidth=2, zorder=10)
            ax1.plot(traj_lons[-1], traj_lats[-1], 's',
                    color='blue', markersize=10, markeredgecolor='black',
                    markeredgewidth=2, zorder=10)

        ax1.set_xlabel('Longitude (°)')
        ax1.set_ylabel('Latitude (°)')
        ax1.set_title('Plastic Particle Trajectories\\n(Red: Release, Blue: Final)', fontsize=12)
        ax1.grid(True, alpha=0.3)

        # Plot 2: Release locations
        ax2 = plt.subplot(2, 3, 2)
        ax2.scatter(self.release_grid_lons, self.release_grid_lats,
                   c='red', s=150, marker='o', edgecolors='black', linewidth=2)

        for i, (lon, lat) in enumerate(zip(self.release_grid_lons, self.release_grid_lats)):
            ax2.annotate(f'{i+1}', (lon, lat), xytext=(5, 5),
                        textcoords='offset points', fontsize=8)

        ax2.set_xlabel('Longitude (°)')
        ax2.set_ylabel('Latitude (°)')
        ax2.set_title(f'Release Locations ({len(self.release_grid_lons)} particles)')
        ax2.grid(True, alpha=0.3)

        # Plot 3: Distance over time
        ax3 = plt.subplot(2, 3, 3)

        for i in range(len(self.release_grid_lons)):
            distances = [0]
            for t in range(1, len(self.times)):
                prev_lon = self.trajectory_lons[t-1][i]
                prev_lat = self.trajectory_lats[t-1][i]
                curr_lon = self.trajectory_lons[t][i]
                curr_lat = self.trajectory_lats[t][i]

                dlat = curr_lat - prev_lat
                dlon = curr_lon - prev_lon
                dist_km = np.sqrt(dlat**2 + dlon**2) * 111.32
                distances.append(distances[-1] + dist_km)

            ax3.plot(self.times, distances, 'o-', color=colors[i], alpha=0.7)

        ax3.set_xlabel('Time (hours)')
        ax3.set_ylabel('Cumulative Distance (km)')
        ax3.set_title('Distance Traveled Over Time')
        ax3.grid(True, alpha=0.3)

        # Plot 4: Displacement vectors
        ax4 = plt.subplot(2, 3, 4)

        for i in range(len(self.release_grid_lons)):
            final_lon = self.trajectory_lons[-1][i]
            final_lat = self.trajectory_lats[-1][i]
            initial_lon = self.trajectory_lons[0][i]
            initial_lat = self.trajectory_lats[0][i]

            dlat = final_lat - initial_lat
            dlon = final_lon - initial_lon

            ax4.arrow(initial_lon, initial_lat, dlon, dlat,
                     head_width=0.01, head_length=0.01,
                     fc=colors[i], ec=colors[i], alpha=0.8)

            ax4.plot(initial_lon, initial_lat, 'ro', markersize=8)
            ax4.plot(final_lon, final_lat, 'bs', markersize=8)

        ax4.set_xlabel('Longitude (°)')
        ax4.set_ylabel('Latitude (°)')
        ax4.set_title('Displacement Vectors')
        ax4.grid(True, alpha=0.3)

        # Plot 5: Speed histogram
        ax5 = plt.subplot(2, 3, 5)

        avg_speeds = []
        for i in range(len(self.release_grid_lons)):
            total_distance = 0
            for t in range(1, len(self.times)):
                prev_lon = self.trajectory_lons[t-1][i]
                prev_lat = self.trajectory_lats[t-1][i]
                curr_lon = self.trajectory_lons[t][i]
                curr_lat = self.trajectory_lats[t][i]

                dlat = curr_lat - prev_lat
                dlon = curr_lon - prev_lon
                dist_km = np.sqrt(dlat**2 + dlon**2) * 111.32
                total_distance += dist_km

            avg_speed = total_distance / self.times[-1]
            avg_speeds.append(avg_speed)

        ax5.hist(avg_speeds, bins=8, alpha=0.7, color='skyblue', edgecolor='black')
        ax5.set_xlabel('Average Speed (km/h)')
        ax5.set_ylabel('Number of Particles')
        ax5.set_title('Speed Distribution')
        ax5.grid(True, alpha=0.3)

        # Plot 6: Summary
        ax6 = plt.subplot(2, 3, 6)
        ax6.axis('off')

        avg_displacement = np.mean([
            np.sqrt((self.trajectory_lons[-1][i] - self.trajectory_lons[0][i])**2 +
                   (self.trajectory_lats[-1][i] - self.trajectory_lats[0][i])**2) * 111.32
            for i in range(len(self.release_grid_lons))
        ])

        summary_text = f'''SIMULATION SUMMARY

Duration: {self.times[-1]:.1f} hours
Particles: {len(self.release_grid_lons)}

DOMAIN:
Lon: {self.lons.min():.2f}° to {self.lons.max():.2f}°
Lat: {self.lats.min():.2f}° to {self.lats.max():.2f}°

RESULTS:
Avg displacement: {avg_displacement:.2f} km
Avg speed: {np.mean(avg_speeds):.2f} km/h
Max current: {speed_field.max():.3f} m/s

SOURCE: SCHISM regridded to NEMO
'''

        ax6.text(0.05, 0.95, summary_text, transform=ax6.transAxes,
                fontsize=11, verticalalignment='top', fontfamily='monospace',
                bbox=dict(boxstyle='round,pad=0.5', facecolor='lightgray', alpha=0.8))

        plt.tight_layout()

        # Save plot
        plot_file = os.path.join(self.output_dir, f'{base_filename}_trajectories.png')
        plt.savefig(plot_file, dpi=300, bbox_inches='tight')
        print(f"   ✓ Saved {plot_file}")

        # Clean up
        u_data.close()
        v_data.close()

        return plot_file

    def run_complete_workflow(self, simulation_hours=6, num_particles=16, release_locations=None):
        """Run the complete SCHISM to PlasticParcels workflow."""
        print("🌊 SCHISM TO PLASTICPARCELS COMPLETE WORKFLOW 🌊")
        print("=" * 60)

        # Print configuration summary
        if self.lon_bounds or self.lat_bounds:
            print(f"📍 Spatial subsetting: lon={self.lon_bounds}, lat={self.lat_bounds}")
        else:
            print("📍 Using full SCHISM domain")

        if release_locations:
            print(f"🎯 Custom release locations: {len(release_locations['lons']) if isinstance(release_locations, dict) else len(release_locations)} points")
        else:
            print(f"🎯 Default release grid: {num_particles} particles")

        print(f"⏱️  Simulation duration: {simulation_hours} hours")
        print(f"🔍 Target resolution: {self.target_resolution}° ({self.target_resolution * 111.32:.1f} km)")
        print()

        try:
            # Step 1: Load SCHISM data
            self.load_schism_data()

            # Step 2: Create target grid
            self.create_target_grid()

            # Step 3: Regrid variables
            self.regrid_variables()

            # Step 4: Save NEMO format
            self.save_nemo_format()

            # Step 5: Create settings
            self.create_settings_file()

            # Step 6: Run simulation
            self.run_simulation(simulation_hours, num_particles, release_locations)

            # Step 7: Create visualization
            plot_file = self.create_visualization()

            print()
            print("🎉 WORKFLOW COMPLETED SUCCESSFULLY! 🎉")
            print("=" * 60)
            print(f"✅ SCHISM data regridded to NEMO format")
            print(f"✅ PlasticParcels simulation completed")
            print(f"✅ Trajectory visualization created")
            print()
            print("📁 OUTPUT FILES:")
            print(f"   • Data directory: {self.output_dir}/")
            print(f"   • Settings file: {self.settings_file}")
            print(f"   • Trajectory plot: {plot_file}")
            print()
            if self.lon_bounds or self.lat_bounds:
                print(f"📊 DOMAIN SUMMARY:")
                print(f"   • Original SCHISM domain: {len(self.ds['SCHISM_hgrid_node_x'])} nodes")
                print(f"   • Subset domain: {len(self.lons)} nodes ({len(self.lons)/len(self.ds['SCHISM_hgrid_node_x'])*100:.1f}%)")
                print(f"   • Target grid: {len(self.target_lats)}×{len(self.target_lons)} = {len(self.target_lats)*len(self.target_lons)} points")
                print()
            print("🚀 Your SCHISM data is now fully compatible with PlasticParcels!")

            return True

        except Exception as e:
            print(f"❌ Error in workflow: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Clean up
            if hasattr(self, 'ds'):
                self.ds.close()


def parse_bounds(bounds_str):
    """Parse bounds string like 'lon_min,lon_max' into tuple."""
    if bounds_str is None:
        return None
    try:
        values = [float(x.strip()) for x in bounds_str.split(',')]
        if len(values) != 2:
            raise ValueError("Bounds must have exactly 2 values")
        return tuple(values)
    except Exception as e:
        raise ValueError(f"Invalid bounds format '{bounds_str}': {e}")

def parse_release_locations(locations_str):
    """Parse release locations string like 'lon1,lat1;lon2,lat2;...' into list."""
    if locations_str is None:
        return None
    try:
        locations = []
        for loc_str in locations_str.split(';'):
            lon, lat = [float(x.strip()) for x in loc_str.split(',')]
            locations.append((lon, lat))
        return locations
    except Exception as e:
        raise ValueError(f"Invalid release locations format '{locations_str}': {e}")

def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Convert SCHISM output to PlasticParcels format with spatial subsetting and custom release locations',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python %(prog)s --schism_file out2d_1.nc

  # Subset domain to specific region
  python %(prog)s --schism_file out2d_1.nc --lon_bounds -82,-78 --lat_bounds 32,36

  # Custom release locations
  python %(prog)s --schism_file out2d_1.nc --release_locations "-80.5,32.0;-80.3,32.2;-80.1,32.4"

  # Full customization
  python %(prog)s --schism_file out2d_1.nc \\
    --output_dir my_simulation \\
    --lon_bounds -81,-79 --lat_bounds 31.5,32.5 \\
    --resolution 0.005 --hours 12 \\
    --release_locations "-80.5,32.0;-80.3,32.2"
        """)

    # Required arguments
    parser.add_argument('--schism_file', required=True,
                       help='Path to SCHISM output file (e.g., out2d_1.nc)')

    # Output options
    parser.add_argument('--output_dir', default='schism_nemo_output',
                       help='Output directory for NEMO-format files (default: schism_nemo_output)')
    parser.add_argument('--resolution', type=float, default=0.01,
                       help='Target grid resolution in degrees (default: 0.01, ~1.1km)')

    # Spatial subsetting options
    parser.add_argument('--lon_bounds', type=str, default=None,
                       help='Longitude bounds as "lon_min,lon_max" (e.g., "-82,-78")')
    parser.add_argument('--lat_bounds', type=str, default=None,
                       help='Latitude bounds as "lat_min,lat_max" (e.g., "32,36")')

    # Simulation options
    parser.add_argument('--hours', type=int, default=6,
                       help='Simulation duration in hours (default: 6)')
    parser.add_argument('--particles', type=int, default=16,
                       help='Number of particles for default grid (default: 16)')

    # Release location options
    parser.add_argument('--release_locations', type=str, default=None,
                       help='Custom release locations as "lon1,lat1;lon2,lat2;..." (e.g., "-80.5,32.0;-80.3,32.2")')

    args = parser.parse_args()

    # Validate inputs
    if not os.path.exists(args.schism_file):
        print(f"❌ Error: SCHISM file not found: {args.schism_file}")
        return False

    # Parse bounds
    try:
        lon_bounds = parse_bounds(args.lon_bounds)
        lat_bounds = parse_bounds(args.lat_bounds)
        release_locations = parse_release_locations(args.release_locations)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False

    # Validate bounds
    if lon_bounds and lon_bounds[0] >= lon_bounds[1]:
        print(f"❌ Error: Invalid longitude bounds: {lon_bounds[0]} >= {lon_bounds[1]}")
        return False
    if lat_bounds and lat_bounds[0] >= lat_bounds[1]:
        print(f"❌ Error: Invalid latitude bounds: {lat_bounds[0]} >= {lat_bounds[1]}")
        return False

    # Print configuration
    print("🔧 CONFIGURATION:")
    print(f"   SCHISM file: {args.schism_file}")
    print(f"   Output directory: {args.output_dir}")
    print(f"   Resolution: {args.resolution}° ({args.resolution * 111.32:.1f} km)")
    if lon_bounds:
        print(f"   Longitude bounds: {lon_bounds[0]}° to {lon_bounds[1]}°E")
    if lat_bounds:
        print(f"   Latitude bounds: {lat_bounds[0]}° to {lat_bounds[1]}°N")
    if release_locations:
        print(f"   Custom release locations: {len(release_locations)} points")
    else:
        print(f"   Default release grid: {args.particles} particles")
    print(f"   Simulation duration: {args.hours} hours")
    print()

    # Create converter and run workflow
    converter = SCHISMToPlasticParcels(
        schism_file=args.schism_file,
        output_dir=args.output_dir,
        target_resolution=args.resolution,
        lon_bounds=lon_bounds,
        lat_bounds=lat_bounds
    )

    # Convert release locations to dict format if provided
    release_dict = None
    if release_locations:
        release_dict = {
            'lons': [loc[0] for loc in release_locations],
            'lats': [loc[1] for loc in release_locations]
        }

    success = converter.run_complete_workflow(
        simulation_hours=args.hours,
        num_particles=args.particles,
        release_locations=release_dict
    )

    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
