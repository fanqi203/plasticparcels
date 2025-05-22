#!/usr/bin/env python3
"""
Enhanced SCHISM to PlasticParcels converter for time series data

Handles multiple SCHISM output scenarios:
1. Multiple files: out2d_1.nc, out2d_2.nc, out2d_3.nc, ...
2. Single file with multiple time steps
3. Mixed scenarios

Usage:
    # Multiple files
    python schism_timeseries_to_plasticparcels.py --schism_files "out2d_*.nc"

    # Single file with time series
    python schism_timeseries_to_plasticparcels.py --schism_files "out2d_full.nc"

    # Specific file list
    python schism_timeseries_to_plasticparcels.py --schism_files "out2d_1.nc,out2d_2.nc,out2d_3.nc"
"""

import argparse
import os
import glob
import numpy as np
import xarray as xr
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import parcels
from datetime import datetime, timedelta
from scipy.interpolate import griddata
import json

class SCHISMTimeSeriesConverter:
    """
    Enhanced converter for SCHISM time series data.
    """

    def __init__(self, schism_files, output_dir='schism_timeseries_output',
                 target_resolution=0.01, lon_bounds=None, lat_bounds=None):
        """
        Initialize converter for time series data.

        Parameters:
        -----------
        schism_files : str or list
            SCHISM file pattern, single file, or list of files
        output_dir : str
            Output directory
        target_resolution : float
            Grid resolution in degrees
        lon_bounds : tuple
            (lon_min, lon_max) for spatial subsetting
        lat_bounds : tuple
            (lat_min, lat_max) for spatial subsetting
        """
        self.schism_files = self._parse_file_input(schism_files)
        self.output_dir = output_dir
        self.target_resolution = target_resolution
        self.lon_bounds = lon_bounds
        self.lat_bounds = lat_bounds

        os.makedirs(output_dir, exist_ok=True)

    def _parse_file_input(self, file_input):
        """Parse different file input formats."""
        if isinstance(file_input, str):
            if '*' in file_input or '?' in file_input:
                # Glob pattern
                files = sorted(glob.glob(file_input))
                if not files:
                    raise ValueError(f"No files found matching pattern: {file_input}")
                return files
            elif ',' in file_input:
                # Comma-separated list
                return [f.strip() for f in file_input.split(',')]
            else:
                # Single file
                return [file_input]
        elif isinstance(file_input, list):
            return file_input
        else:
            raise ValueError("schism_files must be string or list")

    def analyze_time_structure(self):
        """Analyze the time structure of SCHISM files."""
        print("🔍 Analyzing SCHISM time structure...")

        self.time_info = []
        total_time_steps = 0

        for i, file_path in enumerate(self.schism_files):
            if not os.path.exists(file_path):
                print(f"⚠️  Warning: File not found: {file_path}")
                continue

            ds = xr.open_dataset(file_path)
            n_times = ds.dims.get('time', 1)

            # Get time values if available
            if 'time' in ds.variables and n_times > 1:
                time_values = ds['time'].values
                start_time = time_values[0]
                end_time = time_values[-1]
            else:
                # Assume single time step
                start_time = f"File_{i+1}_t0"
                end_time = f"File_{i+1}_t0"

            file_info = {
                'file': file_path,
                'n_times': n_times,
                'start_time': start_time,
                'end_time': end_time,
                'nodes': ds.dims.get('nSCHISM_hgrid_node', 0)
            }

            self.time_info.append(file_info)
            total_time_steps += n_times

            print(f"   File {i+1}: {os.path.basename(file_path)}")
            print(f"     Time steps: {n_times}")
            print(f"     Nodes: {file_info['nodes']:,}")

            ds.close()

        print(f"✓ Total files: {len(self.time_info)}")
        print(f"✓ Total time steps: {total_time_steps}")

        return total_time_steps

    def load_and_concatenate_data(self):
        """Load and concatenate SCHISM data from multiple files/times."""
        print("📥 Loading and concatenating SCHISM data...")

        all_datasets = []

        for file_info in self.time_info:
            file_path = file_info['file']
            print(f"   Loading: {os.path.basename(file_path)}")

            ds = xr.open_dataset(file_path)

            # Ensure time dimension exists
            if 'time' not in ds.dims:
                # Add time dimension for single time step files
                ds = ds.expand_dims('time')

            all_datasets.append(ds)

        # Concatenate along time dimension
        print("   Concatenating datasets...")
        self.combined_ds = xr.concat(all_datasets, dim='time')

        print(f"✓ Combined dataset shape:")
        print(f"   Time steps: {self.combined_ds.dims['time']}")
        print(f"   Nodes: {self.combined_ds.dims['nSCHISM_hgrid_node']:,}")

        # Extract coordinates (same for all time steps)
        all_lons = self.combined_ds['SCHISM_hgrid_node_x'].values
        all_lats = self.combined_ds['SCHISM_hgrid_node_y'].values
        all_depths = self.combined_ds['depth'].values

        # Apply spatial subsetting if specified
        if self.lon_bounds or self.lat_bounds:
            print("   Applying spatial subsetting...")

            lon_min = self.lon_bounds[0] if self.lon_bounds else all_lons.min()
            lon_max = self.lon_bounds[1] if self.lon_bounds else all_lons.max()
            lat_min = self.lat_bounds[0] if self.lat_bounds else all_lats.min()
            lat_max = self.lat_bounds[1] if self.lat_bounds else all_lats.max()

            spatial_mask = ((all_lons >= lon_min) & (all_lons <= lon_max) &
                           (all_lats >= lat_min) & (all_lats <= lat_max))

            self.lons = all_lons[spatial_mask]
            self.lats = all_lats[spatial_mask]
            self.depths = all_depths[spatial_mask]
            self.spatial_mask = spatial_mask

            print(f"   Subset: {len(self.lons):,} nodes ({len(self.lons)/len(all_lons)*100:.1f}%)")
        else:
            self.lons = all_lons
            self.lats = all_lats
            self.depths = all_depths
            self.spatial_mask = None

        # Close individual datasets
        for ds in all_datasets:
            ds.close()

    def create_target_grid(self):
        """Create regular target grid."""
        print("🎯 Creating target grid...")

        lon_min, lon_max = self.lons.min(), self.lons.max()
        lat_min, lat_max = self.lats.min(), self.lats.max()

        self.target_lons = np.arange(lon_min, lon_max + self.target_resolution, self.target_resolution)
        self.target_lats = np.arange(lat_min, lat_max + self.target_resolution, self.target_resolution)
        self.target_lon_2d, self.target_lat_2d = np.meshgrid(self.target_lons, self.target_lats)

        print(f"✓ Target grid: {len(self.target_lats)} × {len(self.target_lons)} = {len(self.target_lats) * len(self.target_lons):,} points")
        print(f"✓ Resolution: {self.target_resolution}° ({self.target_resolution * 111.32:.1f} km)")

    def regrid_timeseries(self):
        """Regrid time series data to regular grid."""
        print("🔄 Regridding time series data...")

        n_times = self.combined_ds.dims['time']
        grid_shape = (n_times, len(self.target_lats), len(self.target_lons))

        # Initialize output arrays
        self.regridded_data = {
            'U': np.zeros(grid_shape),
            'V': np.zeros(grid_shape),
            'W': np.zeros(grid_shape),  # Always zero for 2D
            'elevation': np.zeros(grid_shape)
        }

        # Process each time step
        for t in range(n_times):
            print(f"   Processing time step {t+1}/{n_times}")

            # Extract data for this time step
            if self.spatial_mask is not None:
                u_data = self.combined_ds['depthAverageVelX'][t, :].values[self.spatial_mask]
                v_data = self.combined_ds['depthAverageVelY'][t, :].values[self.spatial_mask]
                elev_data = self.combined_ds['elevation'][t, :].values[self.spatial_mask]
            else:
                u_data = self.combined_ds['depthAverageVelX'][t, :].values
                v_data = self.combined_ds['depthAverageVelY'][t, :].values
                elev_data = self.combined_ds['elevation'][t, :].values

            # Regrid each variable
            for var_name, data in [('U', u_data), ('V', v_data), ('elevation', elev_data)]:
                regridded = griddata(
                    points=np.column_stack([self.lons, self.lats]),
                    values=data,
                    xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
                    method='linear',
                    fill_value=0.0
                ).reshape(self.target_lon_2d.shape)

                self.regridded_data[var_name][t, :, :] = regridded

        print(f"✓ Regridded {n_times} time steps")

        # Create bathymetry (time-independent)
        print("   Creating bathymetry...")
        bathy_regridded = griddata(
            points=np.column_stack([self.lons, self.lats]),
            values=self.depths,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(self.target_lon_2d.shape)
        self.regridded_data['bathymetry'] = bathy_regridded

    def save_nemo_timeseries(self):
        """Save regridded time series in NEMO format."""
        print("💾 Saving NEMO-compatible time series...")

        n_times = self.regridded_data['U'].shape[0]

        # Create time coordinate (hours since start)
        time_hours = np.arange(n_times, dtype=float)

        # Create coordinate variables
        coords = {
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
            'time_counter': ('time_counter', time_hours)
        }

        # Save each variable
        variables = {
            'U': ('vozocrtx', self.regridded_data['U']),
            'V': ('vomecrty', self.regridded_data['V']),
            'W': ('vovecrtz', self.regridded_data['W']),
            'T': ('votemper', self.regridded_data['elevation']),
            'S': ('vosaline', np.full_like(self.regridded_data['U'], 35.0))
        }

        for var_letter, (nemo_var, data) in variables.items():
            ds = xr.Dataset({
                nemo_var: (['time_counter', 'y', 'x'], data)
            }, coords=coords)

            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': 'SCHISM time series regridded to NEMO format',
                'institution': 'PlasticParcels Regridder',
                'time_steps': n_times
            })

            filename = f"{var_letter}_timeseries.nc"
            filepath = os.path.join(self.output_dir, filename)
            ds.to_netcdf(filepath)
            print(f"   ✓ Saved {filepath}")

        # Save mesh and bathymetry files
        self._save_mesh_files()

        print(f"✓ Saved {n_times} time steps in NEMO format")

    def _save_mesh_files(self):
        """Save mesh and bathymetry files."""
        # Mesh file
        mesh_ds = xr.Dataset({
            'glamf': (['y', 'x'], self.target_lon_2d),
            'gphif': (['y', 'x'], self.target_lat_2d),
        })
        mesh_file = os.path.join(self.output_dir, 'ocean_mesh_hgr.nc')
        mesh_ds.to_netcdf(mesh_file)
        print(f"   ✓ Saved {mesh_file}")

        # Bathymetry file
        mbathy = np.ones_like(self.regridded_data['bathymetry'], dtype=int)
        mbathy[self.regridded_data['bathymetry'] <= 0] = 0

        bathy_ds = xr.Dataset({
            'mbathy': (['time_counter', 'y', 'x'], mbathy[np.newaxis, :, :]),
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
        })
        bathy_file = os.path.join(self.output_dir, 'bathymetry_mesh_zgr.nc')
        bathy_ds.to_netcdf(bathy_file)
        print(f"   ✓ Saved {bathy_file}")

    def create_settings_file(self):
        """Create PlasticParcels settings file for time series."""
        print("⚙️  Creating PlasticParcels settings...")

        settings = {
            "use_3D": False,
            "allow_time_extrapolation": False,  # Now we have real time series!
            "verbose_delete": False,
            "use_mixing": False,
            "use_biofouling": False,
            "use_stokes": False,
            "use_wind": False,
            "ocean": {
                "modelname": "NEMO0083",
                "directory": f"{self.output_dir}/",
                "filename_style": "timeseries",
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

        settings_file = os.path.join(self.output_dir, 'timeseries_settings.json')
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
        print(f"   ✓ Saved {settings_file}")

        return settings_file

    def run_complete_workflow(self):
        """Run complete time series conversion workflow."""
        print("🌊 SCHISM TIME SERIES TO PLASTICPARCELS WORKFLOW 🌊")
        print("=" * 70)

        try:
            # Step 1: Analyze time structure
            total_times = self.analyze_time_structure()

            # Step 2: Load and concatenate data
            self.load_and_concatenate_data()

            # Step 3: Create target grid
            self.create_target_grid()

            # Step 4: Regrid time series
            self.regrid_timeseries()

            # Step 5: Save NEMO format
            self.save_nemo_timeseries()

            # Step 6: Create settings
            settings_file = self.create_settings_file()

            print()
            print("🎉 TIME SERIES CONVERSION COMPLETED! 🎉")
            print("=" * 50)
            print(f"✅ Processed {len(self.schism_files)} SCHISM files")
            print(f"✅ Converted {total_times} time steps")
            print(f"✅ Created NEMO-compatible time series")
            print()
            print("📁 OUTPUT FILES:")
            print(f"   • Data directory: {self.output_dir}/")
            print(f"   • Settings file: {settings_file}")
            print(f"   • Time series files: U/V/W/T/S_timeseries.nc")
            print()
            print("🚀 Ready for realistic time-varying PlasticParcels simulations!")

            return True

        except Exception as e:
            print(f"❌ Error in workflow: {e}")
            import traceback
            traceback.print_exc()
            return False

        finally:
            # Clean up
            if hasattr(self, 'combined_ds'):
                self.combined_ds.close()


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


def main():
    """Main function for time series conversion."""
    parser = argparse.ArgumentParser(
        description='Convert SCHISM time series to PlasticParcels format',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Multiple files with wildcard
  python %(prog)s --schism_files "out2d_*.nc"

  # Specific file list
  python %(prog)s --schism_files "out2d_1.nc,out2d_2.nc,out2d_3.nc"

  # Single file with multiple time steps
  python %(prog)s --schism_files "out2d_full.nc"

  # With spatial subsetting
  python %(prog)s --schism_files "out2d_*.nc" --lon_bounds -82,-78 --lat_bounds 32,36
        """)

    # Required arguments
    parser.add_argument('--schism_files', required=True,
                       help='SCHISM files: pattern ("out2d_*.nc"), list ("file1.nc,file2.nc"), or single file')

    # Output options
    parser.add_argument('--output_dir', default='schism_timeseries_output',
                       help='Output directory (default: schism_timeseries_output)')
    parser.add_argument('--resolution', type=float, default=0.01,
                       help='Target grid resolution in degrees (default: 0.01)')

    # Spatial subsetting
    parser.add_argument('--lon_bounds', type=str, default=None,
                       help='Longitude bounds as "lon_min,lon_max"')
    parser.add_argument('--lat_bounds', type=str, default=None,
                       help='Latitude bounds as "lat_min,lat_max"')

    args = parser.parse_args()

    # Parse bounds
    try:
        lon_bounds = parse_bounds(args.lon_bounds)
        lat_bounds = parse_bounds(args.lat_bounds)
    except ValueError as e:
        print(f"❌ Error: {e}")
        return False

    # Print configuration
    print("🔧 CONFIGURATION:")
    print(f"   SCHISM files: {args.schism_files}")
    print(f"   Output directory: {args.output_dir}")
    print(f"   Resolution: {args.resolution}° ({args.resolution * 111.32:.1f} km)")
    if lon_bounds:
        print(f"   Longitude bounds: {lon_bounds[0]}° to {lon_bounds[1]}°")
    if lat_bounds:
        print(f"   Latitude bounds: {lat_bounds[0]}° to {lat_bounds[1]}°")
    print()

    # Create converter and run
    converter = SCHISMTimeSeriesConverter(
        schism_files=args.schism_files,
        output_dir=args.output_dir,
        target_resolution=args.resolution,
        lon_bounds=lon_bounds,
        lat_bounds=lat_bounds
    )

    success = converter.run_complete_workflow()
    return success


if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)
