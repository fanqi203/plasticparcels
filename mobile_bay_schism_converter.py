#!/usr/bin/env python3
"""
Mobile Bay SCHISM to PlasticParcels Converter - Production Version

Converts SCHISM hydrodynamic model output to PlasticParcels-compatible NEMO format
for plastic pollution modeling in Mobile Bay, Alabama.

Features:
- Converts SCHISM unstructured grid to regular lat/lon grid
- Preserves full hourly temporal resolution
- Creates PlasticParcels-compatible daily files
- Supports scalable processing (hours to months of data)
- Includes comprehensive error handling and logging

Author: Augment Agent
Date: 2024
Version: 1.0
"""

import os
import sys
import glob
import re
import argparse
import logging
import numpy as np
import xarray as xr
from scipy.interpolate import griddata
import json
from datetime import datetime, timedelta
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('mobile_bay_converter.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

class MobileBayConverter:
    """
    Converts SCHISM model output to PlasticParcels format for Mobile Bay.
    """

    def __init__(self, schism_dir, output_dir, target_resolution=0.01, hours_per_day=24):
        """
        Initialize the converter.

        Parameters:
        -----------
        schism_dir : str
            Directory containing SCHISM out2d_*.nc files
        output_dir : str
            Output directory for converted files
        target_resolution : float
            Target grid resolution in degrees (default: 0.01° ≈ 1.1 km)
        hours_per_day : int
            Number of hourly files to combine per daily file (default: 24)
        """
        self.schism_dir = Path(schism_dir)
        self.output_dir = Path(output_dir)
        self.target_resolution = target_resolution
        self.hours_per_day = hours_per_day

        # Validate inputs
        if not self.schism_dir.exists():
            raise FileNotFoundError(f"SCHISM directory not found: {schism_dir}")

        # Create output directory
        self.output_dir.mkdir(parents=True, exist_ok=True)

        logger.info(f"Initialized Mobile Bay Converter")
        logger.info(f"  SCHISM directory: {self.schism_dir}")
        logger.info(f"  Output directory: {self.output_dir}")
        logger.info(f"  Target resolution: {self.target_resolution}° ({self.target_resolution * 111.32:.1f} km)")
        logger.info(f"  Hours per day: {self.hours_per_day}")

    def get_schism_files(self, max_files=None):
        """Get sorted list of SCHISM files."""

        pattern = self.schism_dir / "out2d_*.nc"
        all_files = glob.glob(str(pattern))

        def extract_number(filename):
            match = re.search(r'out2d_(\d+)\.nc', filename)
            return int(match.group(1)) if match else 0

        all_files = sorted(all_files, key=extract_number)

        if max_files:
            all_files = all_files[:max_files]

        logger.info(f"Found {len(all_files)} SCHISM files")
        if max_files:
            logger.info(f"Processing first {len(all_files)} files")

        return all_files

    def load_schism_grid(self, schism_file):
        """Load SCHISM grid structure from first file."""

        logger.info("Loading SCHISM grid structure...")

        with xr.open_dataset(schism_file) as ds:
            lons = ds['SCHISM_hgrid_node_x'].values
            lats = ds['SCHISM_hgrid_node_y'].values
            depths = ds['depth'].values

        logger.info(f"SCHISM grid:")
        logger.info(f"  Nodes: {len(lons):,}")
        logger.info(f"  Longitude range: {lons.min():.3f} to {lons.max():.3f}")
        logger.info(f"  Latitude range: {lats.min():.3f} to {lats.max():.3f}")
        logger.info(f"  Depth range: {depths.min():.1f} to {depths.max():.1f} m")

        return lons, lats, depths

    def create_target_grid(self, lons, lats):
        """Create regular target grid."""

        logger.info(f"Creating target grid (resolution: {self.target_resolution}°)...")

        lon_min, lon_max = lons.min(), lons.max()
        lat_min, lat_max = lats.min(), lats.max()

        target_lons = np.arange(lon_min, lon_max + self.target_resolution, self.target_resolution)
        target_lats = np.arange(lat_min, lat_max + self.target_resolution, self.target_resolution)
        target_lon_2d, target_lat_2d = np.meshgrid(target_lons, target_lats)

        logger.info(f"Target grid: {len(target_lats)} × {len(target_lons)} = {len(target_lats) * len(target_lons):,} points")

        return target_lon_2d, target_lat_2d

    def create_bathymetry(self, lons, lats, depths, target_lon_2d, target_lat_2d):
        """Create regridded bathymetry."""

        logger.info("Creating bathymetry...")

        valid_mask = ~np.isnan(depths) & ~np.isnan(lons) & ~np.isnan(lats)

        if np.sum(valid_mask) == 0:
            logger.warning("No valid bathymetry data, using zero depth")
            return np.zeros(target_lon_2d.shape)

        bathy_regridded = griddata(
            points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
            values=depths[valid_mask],
            xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
            method='linear',
            fill_value=0.0
        ).reshape(target_lon_2d.shape)

        return bathy_regridded

    def regrid_schism_data(self, schism_file, lons, lats, target_lon_2d, target_lat_2d):
        """Regrid SCHISM data to regular grid."""

        with xr.open_dataset(schism_file) as ds:
            # Extract velocity and elevation data
            try:
                if len(ds['depthAverageVelX'].shape) == 2:
                    u_vals = ds['depthAverageVelX'][0, :].values
                    v_vals = ds['depthAverageVelY'][0, :].values
                    elev_vals = ds['elevation'][0, :].values
                else:
                    u_vals = ds['depthAverageVelX'].values
                    v_vals = ds['depthAverageVelY'].values
                    elev_vals = ds['elevation'].values
            except Exception as e:
                logger.warning(f"Error extracting data from {schism_file}: {e}")
                u_vals = ds['depthAverageVelX'].values.flatten()
                v_vals = ds['depthAverageVelY'].values.flatten()
                elev_vals = ds['elevation'].values.flatten()

        # Regrid each variable
        regridded_data = {}

        for var_name, vals in [('U', u_vals), ('V', v_vals), ('elevation', elev_vals)]:
            valid_mask = ~np.isnan(vals) & ~np.isnan(lons) & ~np.isnan(lats)

            if np.sum(valid_mask) == 0:
                logger.warning(f"No valid data for {var_name}, using zeros")
                regridded = np.zeros(target_lon_2d.shape)
            else:
                regridded = griddata(
                    points=np.column_stack([lons[valid_mask], lats[valid_mask]]),
                    values=vals[valid_mask],
                    xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
                    method='linear',
                    fill_value=0.0
                ).reshape(target_lon_2d.shape)

            regridded_data[var_name] = regridded

        return regridded_data

    def save_daily_files(self, day, date_str, daily_data, target_lon_2d, target_lat_2d):
        """Save daily NEMO-format files."""

        n_hours = daily_data['U'].shape[0]
        # Convert time to seconds (PlasticParcels expects seconds since reference date)
        time_hours = np.arange(day * self.hours_per_day, (day + 1) * self.hours_per_day, dtype=float)[:n_hours]
        time_seconds = time_hours * 3600.0  # Convert hours to seconds

        # Create coordinate variables
        coords = {
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
            'time_counter': ('time_counter', time_seconds),  # Use seconds for PlasticParcels
            'x': ('x', np.arange(target_lon_2d.shape[1])),
            'y': ('y', np.arange(target_lon_2d.shape[0]))
        }

        # Save variables
        variables = {
            'U': ('vozocrtx', daily_data['U']),
            'V': ('vomecrty', daily_data['V']),
            'W': ('vovecrtz', np.zeros_like(daily_data['U'])),
            'T': ('votemper', daily_data['elevation']),
            'S': ('vosaline', np.full_like(daily_data['U'], 35.0))
        }

        for var_letter, (nemo_var, data) in variables.items():
            ds = xr.Dataset({
                nemo_var: (['time_counter', 'y', 'x'], data)
            }, coords=coords)

            # Add proper time coordinate attributes for PlasticParcels
            ds.time_counter.attrs.update({
                'units': 'seconds since 2024-01-01 00:00:00',
                'calendar': 'gregorian',
                'long_name': 'time',
                'standard_name': 'time'
            })

            ds.attrs.update({
                'Conventions': 'CF-1.0',
                'source': f'Mobile Bay SCHISM {date_str} regridded to NEMO format',
                'institution': 'PlasticParcels Converter',
                'history': f'Created on {datetime.now().isoformat()}'
            })

            filename = f"{var_letter}_{date_str}.nc"
            filepath = self.output_dir / filename
            ds.to_netcdf(filepath)
            ds.close()

        logger.info(f"Saved daily files for {date_str} ({n_hours} time steps)")

    def save_mesh_files(self, target_lon_2d, target_lat_2d, bathy_regridded):
        """Save mesh and bathymetry files."""

        logger.info("Saving mesh and bathymetry files...")

        # Mesh file
        mesh_ds = xr.Dataset({
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
            'x': ('x', np.arange(target_lon_2d.shape[1])),
            'y': ('y', np.arange(target_lon_2d.shape[0]))
        })
        mesh_file = self.output_dir / 'ocean_mesh_hgr.nc'
        mesh_ds.to_netcdf(mesh_file)

        # Bathymetry file
        mbathy = np.ones_like(bathy_regridded, dtype=int)
        mbathy[bathy_regridded <= 0] = 0

        bathy_ds = xr.Dataset({
            'mbathy': (['y', 'x'], mbathy),
            'nav_lon': (['y', 'x'], target_lon_2d),
            'nav_lat': (['y', 'x'], target_lat_2d),
        })
        bathy_file = self.output_dir / 'bathymetry_mesh_zgr.nc'
        bathy_ds.to_netcdf(bathy_file)

        logger.info(f"Saved mesh file: {mesh_file}")
        logger.info(f"Saved bathymetry file: {bathy_file}")

    def save_settings(self):
        """Save PlasticParcels settings file."""

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
                "filename_style": "",
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

        settings_file = self.output_dir / 'settings.json'
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)

        logger.info(f"Saved settings file: {settings_file}")

    def convert(self, max_files=None):
        """
        Main conversion function.

        Parameters:
        -----------
        max_files : int, optional
            Maximum number of SCHISM files to process (for testing)
        """

        logger.info("Starting Mobile Bay SCHISM to PlasticParcels conversion")

        try:
            # Get SCHISM files
            schism_files = self.get_schism_files(max_files)

            if not schism_files:
                raise ValueError("No SCHISM files found")

            # Load grid structure
            lons, lats, depths = self.load_schism_grid(schism_files[0])

            # Create target grid
            target_lon_2d, target_lat_2d = self.create_target_grid(lons, lats)

            # Create bathymetry
            bathy_regridded = self.create_bathymetry(lons, lats, depths, target_lon_2d, target_lat_2d)

            # Process files in daily chunks
            base_date = datetime(2024, 1, 1)
            n_days = len(schism_files) // self.hours_per_day + (1 if len(schism_files) % self.hours_per_day else 0)

            logger.info(f"Processing {len(schism_files)} files into {n_days} daily files")

            for day in range(n_days):
                day_date = base_date + timedelta(days=day)
                date_str = day_date.strftime('%Y-%m-%d')

                # Get files for this day
                start_idx = day * self.hours_per_day
                end_idx = min((day + 1) * self.hours_per_day, len(schism_files))
                day_files = schism_files[start_idx:end_idx]

                logger.info(f"Processing day {day+1}/{n_days}: {date_str} ({len(day_files)} files)")

                # Initialize arrays for this day
                n_hours = len(day_files)
                grid_shape = (n_hours, len(target_lat_2d), len(target_lat_2d[0]))

                daily_data = {
                    'U': np.zeros(grid_shape),
                    'V': np.zeros(grid_shape),
                    'elevation': np.zeros(grid_shape)
                }

                # Process each hour
                for h, file_path in enumerate(day_files):
                    logger.debug(f"  Processing hour {h}: {os.path.basename(file_path)}")

                    regridded = self.regrid_schism_data(file_path, lons, lats, target_lon_2d, target_lat_2d)

                    for var in ['U', 'V', 'elevation']:
                        daily_data[var][h, :, :] = regridded[var]

                # Save daily files
                self.save_daily_files(day, date_str, daily_data, target_lon_2d, target_lat_2d)

            # Save mesh and settings files
            self.save_mesh_files(target_lon_2d, target_lat_2d, bathy_regridded)
            self.save_settings()

            logger.info("Conversion completed successfully!")
            logger.info(f"Output directory: {self.output_dir}")
            logger.info(f"Processed {len(schism_files)} SCHISM files into {n_days} daily files")

            return True

        except Exception as e:
            logger.error(f"Conversion failed: {e}")
            raise

def main():
    """Command-line interface."""

    parser = argparse.ArgumentParser(
        description="Convert Mobile Bay SCHISM output to PlasticParcels format",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )

    parser.add_argument(
        'schism_dir',
        help='Directory containing SCHISM out2d_*.nc files'
    )

    parser.add_argument(
        'output_dir',
        help='Output directory for converted files'
    )

    parser.add_argument(
        '--resolution',
        type=float,
        default=0.01,
        help='Target grid resolution in degrees'
    )

    parser.add_argument(
        '--hours-per-day',
        type=int,
        default=24,
        help='Number of hourly files to combine per daily file'
    )

    parser.add_argument(
        '--max-files',
        type=int,
        help='Maximum number of SCHISM files to process (for testing)'
    )

    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level'
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(getattr(logging, args.log_level))

    # Create converter and run
    converter = MobileBayConverter(
        schism_dir=args.schism_dir,
        output_dir=args.output_dir,
        target_resolution=args.resolution,
        hours_per_day=args.hours_per_day
    )

    success = converter.convert(max_files=args.max_files)

    if success:
        print(f"\n🎉 Conversion completed successfully!")
        print(f"📁 Output files saved to: {args.output_dir}")
        print(f"🧪 Test with PlasticParcels using the generated settings.json")
        sys.exit(0)
    else:
        print(f"\n❌ Conversion failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()
