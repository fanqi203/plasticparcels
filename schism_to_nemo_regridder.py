#!/usr/bin/env python3
"""
SCHISM to NEMO Format Regridder

This script converts SCHISM unstructured grid output to NEMO-compatible
structured grid format for use with PlasticParcels.

Key transformations:
1. Unstructured triangular mesh → Regular lat/lon grid
2. Sigma coordinates → Z-level coordinates
3. SCHISM variable names → NEMO variable names
4. Combined files → Separate U/V/W/T/S files
5. Node depths → Level indices (mbathy)
"""

import numpy as np
import xarray as xr
import pandas as pd
from scipy.interpolate import griddata
from scipy.spatial import cKDTree
import os
from datetime import datetime, timedelta

class SCHISMToNEMORegridder:
    """
    Class to handle regridding SCHISM output to NEMO format.
    """

    def __init__(self, target_resolution=0.1, target_levels=50):
        """
        Initialize regridder.

        Parameters:
        -----------
        target_resolution : float
            Target grid resolution in degrees (default: 0.1° ≈ 11km)
        target_levels : int
            Number of vertical levels in target grid
        """
        self.target_resolution = target_resolution
        self.target_levels = target_levels
        self.variable_mapping = {
            # SCHISM → NEMO variable names
            'hvel_x': 'vozocrtx',
            'hvel_y': 'vomecrty',
            'vertical_velocity': 'vovecrtz',
            'temp': 'votemper',
            'salt': 'vosaline'
        }

    def load_schism_grid(self, grid_file):
        """
        Load SCHISM grid information.

        Parameters:
        -----------
        grid_file : str
            Path to SCHISM grid file (hgrid.gr3 or .nc format)
        """
        if grid_file.endswith('.gr3'):
            # Read SCHISM .gr3 format
            self.schism_grid = self._read_gr3_file(grid_file)
        else:
            # Read NetCDF format
            self.schism_grid = xr.open_dataset(grid_file)

        # Extract coordinates
        self.schism_lons = self.schism_grid.x.values  # or appropriate coordinate name
        self.schism_lats = self.schism_grid.y.values
        self.schism_depths = self.schism_grid.depth.values

        print(f"Loaded SCHISM grid: {len(self.schism_lons)} nodes")
        print(f"  Longitude range: {self.schism_lons.min():.2f} to {self.schism_lons.max():.2f}")
        print(f"  Latitude range: {self.schism_lats.min():.2f} to {self.schism_lats.max():.2f}")
        print(f"  Depth range: {self.schism_depths.min():.1f} to {self.schism_depths.max():.1f} m")

    def create_target_grid(self, lon_bounds=None, lat_bounds=None):
        """
        Create target regular grid.

        Parameters:
        -----------
        lon_bounds : tuple
            (lon_min, lon_max) or None for auto-detection
        lat_bounds : tuple
            (lat_min, lat_max) or None for auto-detection
        """
        if lon_bounds is None:
            lon_min, lon_max = self.schism_lons.min(), self.schism_lons.max()
        else:
            lon_min, lon_max = lon_bounds

        if lat_bounds is None:
            lat_min, lat_max = self.schism_lats.min(), self.schism_lats.max()
        else:
            lat_min, lat_max = lat_bounds

        # Create regular grid
        self.target_lons = np.arange(lon_min, lon_max + self.target_resolution, self.target_resolution)
        self.target_lats = np.arange(lat_min, lat_max + self.target_resolution, self.target_resolution)

        # Create 2D coordinate arrays
        self.target_lon_2d, self.target_lat_2d = np.meshgrid(self.target_lons, self.target_lats)

        # Create vertical levels (example Z-levels)
        self.target_depths = np.array([
            0.5, 1.5, 2.6, 3.8, 5.1, 6.4, 7.9, 9.6, 11.4, 13.5,
            15.8, 18.4, 21.3, 24.6, 28.2, 32.3, 36.9, 42.0, 47.7, 54.0,
            61.0, 68.8, 77.4, 86.9, 97.4, 109.0, 121.8, 136.0, 151.7, 169.1,
            188.4, 209.7, 233.4, 259.6, 288.6, 320.7, 356.2, 395.4, 438.8, 486.8,
            539.8, 598.2, 662.4, 732.9, 810.2, 895.0, 987.8, 1089.4, 1200.4, 1321.4
        ])[:self.target_levels]

        print(f"Created target grid:")
        print(f"  Horizontal: {len(self.target_lats)} × {len(self.target_lons)} = {len(self.target_lats) * len(self.target_lons)} points")
        print(f"  Vertical: {len(self.target_depths)} levels")
        print(f"  Resolution: {self.target_resolution}° ({self.target_resolution * 111.32:.1f} km)")

    def regrid_variable(self, schism_data, variable_name, time_index=0):
        """
        Regrid a single variable from SCHISM to target grid.

        Parameters:
        -----------
        schism_data : xarray.Dataset
            SCHISM output data
        variable_name : str
            Variable name in SCHISM data
        time_index : int
            Time index to process

        Returns:
        --------
        regridded_data : numpy.array
            Regridded data on target grid
        """
        print(f"Regridding {variable_name}...")

        # Extract SCHISM data for this time step
        if variable_name in schism_data.variables:
            var_data = schism_data[variable_name].isel(time=time_index)
        else:
            raise ValueError(f"Variable {variable_name} not found in SCHISM data")

        # Handle 3D vs 2D variables
        if len(var_data.dims) == 2:  # 2D variable (e.g., surface elevation)
            # Simple 2D interpolation
            regridded = griddata(
                points=np.column_stack([self.schism_lons, self.schism_lats]),
                values=var_data.values.flatten(),
                xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
                method='linear',
                fill_value=np.nan
            ).reshape(self.target_lon_2d.shape)

            return regridded

        elif len(var_data.dims) == 3:  # 3D variable (depth-dependent)
            # 3D interpolation with sigma → z-level transformation
            regridded_3d = np.full((len(self.target_depths), len(self.target_lats), len(self.target_lons)), np.nan)

            for k, target_depth in enumerate(self.target_depths):
                # Interpolate SCHISM sigma levels to target depth
                depth_data = self._interpolate_sigma_to_z(var_data, target_depth)

                if depth_data is not None:
                    # Horizontal interpolation
                    regridded_3d[k, :, :] = griddata(
                        points=np.column_stack([self.schism_lons, self.schism_lats]),
                        values=depth_data,
                        xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
                        method='linear',
                        fill_value=np.nan
                    ).reshape(self.target_lon_2d.shape)

            return regridded_3d

    def _interpolate_sigma_to_z(self, var_data, target_depth):
        """
        Interpolate from SCHISM sigma coordinates to target Z-level.

        This is a simplified version - real implementation would need
        proper sigma coordinate transformation.
        """
        # Placeholder: In reality, you'd need to:
        # 1. Calculate actual depths from sigma coordinates
        # 2. Interpolate vertically to target depth
        # 3. Handle dry/wet cells properly

        # For now, just use the closest sigma level
        n_sigma = var_data.shape[0]  # Number of sigma levels
        sigma_index = min(int(target_depth / 100), n_sigma - 1)  # Rough approximation

        return var_data[sigma_index, :].values

    def create_nemo_bathymetry(self):
        """
        Create NEMO-style bathymetry (mbathy indices).
        """
        # Create bathymetry field
        bathymetry_depths = griddata(
            points=np.column_stack([self.schism_lons, self.schism_lats]),
            values=self.schism_depths,
            xi=np.column_stack([self.target_lon_2d.flatten(), self.target_lat_2d.flatten()]),
            method='linear',
            fill_value=0
        ).reshape(self.target_lon_2d.shape)

        # Convert depths to level indices (mbathy)
        mbathy = np.zeros_like(bathymetry_depths, dtype=int)
        for i, depth in enumerate(self.target_depths):
            mask = bathymetry_depths > depth
            mbathy[mask] = i + 1

        return mbathy, bathymetry_depths

    def save_nemo_format(self, regridded_data, output_dir, date_str):
        """
        Save regridded data in NEMO format.

        Parameters:
        -----------
        regridded_data : dict
            Dictionary of regridded variables
        output_dir : str
            Output directory
        date_str : str
            Date string for filename (e.g., '2024-05-01')
        """
        os.makedirs(output_dir, exist_ok=True)

        # Create coordinate variables
        coords = {
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
            'deptht': ('deptht', self.target_depths),
            'time_counter': ('time_counter', [0])
        }

        dims = ['time_counter', 'deptht', 'y', 'x']

        # Save each variable in separate file (NEMO style)
        for schism_var, nemo_var in self.variable_mapping.items():
            if schism_var in regridded_data:
                data = regridded_data[schism_var]

                # Create dataset
                if len(data.shape) == 2:  # 2D variable
                    data_array = xr.DataArray(
                        data[np.newaxis, np.newaxis, :, :],  # Add time and depth dims
                        dims=['time_counter', 'deptht_2d', 'y', 'x'],
                        coords={k: v for k, v in coords.items() if k != 'deptht'}
                    )
                else:  # 3D variable
                    data_array = xr.DataArray(
                        data[np.newaxis, :, :, :],  # Add time dim
                        dims=dims,
                        coords=coords
                    )

                # Create dataset
                ds = xr.Dataset({nemo_var: data_array})

                # Add attributes
                ds.attrs.update({
                    'Conventions': 'CF-1.0',
                    'source': 'SCHISM regridded to NEMO format',
                    'institution': 'PlasticParcels Regridder',
                    'references': 'Converted from SCHISM unstructured grid'
                })

                # Save file
                var_letter = nemo_var[2].upper()  # U, V, W, T, S
                filename = f"{var_letter}_{date_str.replace('-', '')}.nc"
                filepath = os.path.join(output_dir, filename)

                ds.to_netcdf(filepath)
                print(f"Saved {filepath}")

        # Save mesh and bathymetry files
        self._save_mesh_files(output_dir)

    def _save_mesh_files(self, output_dir):
        """Save NEMO-style mesh and bathymetry files."""
        # Mesh file
        mesh_ds = xr.Dataset({
            'glamf': (['y', 'x'], self.target_lon_2d),
            'gphif': (['y', 'x'], self.target_lat_2d),
        })
        mesh_ds.to_netcdf(os.path.join(output_dir, 'ocean_mesh_hgr.nc'))

        # Bathymetry file
        mbathy, depths = self.create_nemo_bathymetry()
        bathy_ds = xr.Dataset({
            'mbathy': (['time_counter', 'y', 'x'], mbathy[np.newaxis, :, :]),
            'nav_lon': (['y', 'x'], self.target_lon_2d),
            'nav_lat': (['y', 'x'], self.target_lat_2d),
        })
        bathy_ds.to_netcdf(os.path.join(output_dir, 'bathymetry_mesh_zgr.nc'))

        print("Saved mesh and bathymetry files")

# Test with your specific SCHISM file
def test_beaufort_regridding():
    """
    Test regridding with the Beaufort Sea SCHISM file.
    """
    print("TESTING SCHISM TO NEMO REGRIDDING")
    print("=================================")
    print()

    # Your specific file
    schism_file = '/anvil/scratch/x-fanqi203/beaufort/wwm_wall_nowetland/out2d_1.nc'

    print("1. Loading SCHISM data...")
    ds = xr.open_dataset(schism_file)

    # Extract coordinates
    lons = ds['SCHISM_hgrid_node_x'].values
    lats = ds['SCHISM_hgrid_node_y'].values
    depths = ds['depth'].values

    print(f"   Loaded {len(lons)} nodes")
    print(f"   Longitude range: {lons.min():.3f} to {lons.max():.3f}")
    print(f"   Latitude range: {lats.min():.3f} to {lats.max():.3f}")
    print(f"   Depth range: {depths.min():.1f} to {depths.max():.1f} m")

    print()
    print("2. Creating target regular grid...")

    # Create target grid for Beaufort Sea region
    target_resolution = 0.01  # 0.01° ≈ 1.1km (high resolution for coastal area)

    lon_min, lon_max = lons.min(), lons.max()
    lat_min, lat_max = lats.min(), lats.max()

    target_lons = np.arange(lon_min, lon_max + target_resolution, target_resolution)
    target_lats = np.arange(lat_min, lat_max + target_resolution, target_resolution)
    target_lon_2d, target_lat_2d = np.meshgrid(target_lons, target_lats)

    print(f"   Target grid: {len(target_lats)} × {len(target_lons)} = {len(target_lats) * len(target_lons)} points")
    print(f"   Resolution: {target_resolution}° ({target_resolution * 111.32:.1f} km)")

    print()
    print("3. Regridding variables...")

    # Regrid the key variables
    from scipy.interpolate import griddata

    regridded_data = {}

    # Velocity components (U, V)
    print("   Regridding depthAverageVelX (U velocity)...")
    u_data = ds['depthAverageVelX'][0, :].values  # Remove time dimension
    u_regridded = griddata(
        points=np.column_stack([lons, lats]),
        values=u_data,
        xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
        method='linear',
        fill_value=0.0  # Use 0 for land areas
    ).reshape(target_lon_2d.shape)
    regridded_data['U'] = u_regridded

    print("   Regridding depthAverageVelY (V velocity)...")
    v_data = ds['depthAverageVelY'][0, :].values
    v_regridded = griddata(
        points=np.column_stack([lons, lats]),
        values=v_data,
        xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
        method='linear',
        fill_value=0.0
    ).reshape(target_lon_2d.shape)
    regridded_data['V'] = v_regridded

    # W velocity (set to zero for 2D case)
    print("   Setting W velocity to zero (2D case)...")
    regridded_data['W'] = np.zeros_like(u_regridded)

    # Surface elevation (can be used as a tracer)
    print("   Regridding elevation...")
    elev_data = ds['elevation'][0, :].values
    elev_regridded = griddata(
        points=np.column_stack([lons, lats]),
        values=elev_data,
        xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
        method='linear',
        fill_value=0.0
    ).reshape(target_lon_2d.shape)
    regridded_data['elevation'] = elev_regridded

    # Bathymetry
    print("   Regridding bathymetry...")
    bathy_regridded = griddata(
        points=np.column_stack([lons, lats]),
        values=depths,
        xi=np.column_stack([target_lon_2d.flatten(), target_lat_2d.flatten()]),
        method='linear',
        fill_value=0.0
    ).reshape(target_lon_2d.shape)
    regridded_data['bathymetry'] = bathy_regridded

    print()
    print("4. Creating NEMO-compatible output...")

    # Create NEMO-style files
    output_dir = 'beaufort_nemo_output'
    os.makedirs(output_dir, exist_ok=True)

    # Create coordinate variables
    coords = {
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
        'time_counter': ('time_counter', [0])
    }

    # Save U velocity
    u_ds = xr.Dataset({
        'vozocrtx': (['time_counter', 'y', 'x'], regridded_data['U'][np.newaxis, :, :])
    }, coords=coords)
    u_ds.attrs.update({
        'Conventions': 'CF-1.0',
        'source': 'SCHISM Beaufort Sea regridded to NEMO format',
        'institution': 'PlasticParcels Regridder'
    })
    u_file = os.path.join(output_dir, 'U_beaufort.nc')
    u_ds.to_netcdf(u_file)
    print(f"   Saved {u_file}")

    # Save V velocity
    v_ds = xr.Dataset({
        'vomecrty': (['time_counter', 'y', 'x'], regridded_data['V'][np.newaxis, :, :])
    }, coords=coords)
    v_ds.attrs.update(u_ds.attrs)
    v_file = os.path.join(output_dir, 'V_beaufort.nc')
    v_ds.to_netcdf(v_file)
    print(f"   Saved {v_file}")

    # Save W velocity (zeros)
    w_ds = xr.Dataset({
        'vovecrtz': (['time_counter', 'y', 'x'], regridded_data['W'][np.newaxis, :, :])
    }, coords=coords)
    w_ds.attrs.update(u_ds.attrs)
    w_file = os.path.join(output_dir, 'W_beaufort.nc')
    w_ds.to_netcdf(w_file)
    print(f"   Saved {w_file}")

    # Save temperature (use elevation as proxy)
    t_ds = xr.Dataset({
        'votemper': (['time_counter', 'y', 'x'], regridded_data['elevation'][np.newaxis, :, :])
    }, coords=coords)
    t_ds.attrs.update(u_ds.attrs)
    t_file = os.path.join(output_dir, 'T_beaufort.nc')
    t_ds.to_netcdf(t_file)
    print(f"   Saved {t_file}")

    # Save salinity (constant value)
    s_ds = xr.Dataset({
        'vosaline': (['time_counter', 'y', 'x'], np.full_like(regridded_data['U'][np.newaxis, :, :], 35.0))
    }, coords=coords)
    s_ds.attrs.update(u_ds.attrs)
    s_file = os.path.join(output_dir, 'S_beaufort.nc')
    s_ds.to_netcdf(s_file)
    print(f"   Saved {s_file}")

    # Save mesh file
    mesh_ds = xr.Dataset({
        'glamf': (['y', 'x'], target_lon_2d),
        'gphif': (['y', 'x'], target_lat_2d),
    })
    mesh_file = os.path.join(output_dir, 'ocean_mesh_hgr.nc')
    mesh_ds.to_netcdf(mesh_file)
    print(f"   Saved {mesh_file}")

    # Save bathymetry file (convert depths to level indices)
    # For 2D case, just use 1 level everywhere there's water
    mbathy = np.ones_like(regridded_data['bathymetry'], dtype=int)
    mbathy[regridded_data['bathymetry'] <= 0] = 0  # Land areas

    bathy_ds = xr.Dataset({
        'mbathy': (['time_counter', 'y', 'x'], mbathy[np.newaxis, :, :]),
        'nav_lon': (['y', 'x'], target_lon_2d),
        'nav_lat': (['y', 'x'], target_lat_2d),
    })
    bathy_file = os.path.join(output_dir, 'bathymetry_mesh_zgr.nc')
    bathy_ds.to_netcdf(bathy_file)
    print(f"   Saved {bathy_file}")

    print()
    print("5. Statistics:")
    print(f"   U velocity range: {regridded_data['U'].min():.3f} to {regridded_data['U'].max():.3f} m/s")
    print(f"   V velocity range: {regridded_data['V'].min():.3f} to {regridded_data['V'].max():.3f} m/s")
    print(f"   Elevation range: {regridded_data['elevation'].min():.3f} to {regridded_data['elevation'].max():.3f} m")
    print(f"   Bathymetry range: {regridded_data['bathymetry'].min():.1f} to {regridded_data['bathymetry'].max():.1f} m")

    print()
    print("6. Creating PlasticParcels settings file...")

    # Create settings file
    settings = {
        "use_3D": False,  # 2D simulation
        "allow_time_extrapolation": True,
        "verbose_delete": False,
        "use_mixing": False,
        "use_biofouling": False,
        "use_stokes": False,
        "use_wind": False,
        "ocean": {
            "modelname": "NEMO0083",
            "directory": "beaufort_nemo_output/",
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
                "U": {"lon": "glamf", "lat": "gphif", "time": "time_counter"},
                "V": {"lon": "glamf", "lat": "gphif", "time": "time_counter"},
                "W": {"lon": "glamf", "lat": "gphif", "time": "time_counter"},
                "conservative_temperature": {"lon": "glamf", "lat": "gphif", "time": "time_counter"},
                "absolute_salinity": {"lon": "glamf", "lat": "gphif", "time": "time_counter"}
            },
            "indices": {},
            "bathymetry_variables": {"bathymetry": "mbathy"},
            "bathymetry_dimensions": {"lon": "nav_lon", "lat": "nav_lat"}
        }
    }

    import json
    settings_file = os.path.join(output_dir, 'beaufort_settings.json')
    with open(settings_file, 'w') as f:
        json.dump(settings, f, indent=2)
    print(f"   Saved {settings_file}")

    print()
    print("✅ REGRIDDING COMPLETE!")
    print("You can now use these files with PlasticParcels:")
    print(f"   Data directory: {output_dir}/")
    print(f"   Settings file: {settings_file}")
    print()
    print("Next step: Test with PlasticParcels simulation!")

    ds.close()
    return output_dir, settings_file

# Example usage
if __name__ == "__main__":
    test_beaufort_regridding()
