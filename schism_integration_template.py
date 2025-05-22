#!/usr/bin/env python3
"""
Template for integrating SCHISM hydrodynamic model with PlasticParcels

This shows the key modifications needed to use SCHISM instead of NEMO data.
"""

import os
import numpy as np
from parcels import FieldSet, Field
from plasticparcels.utils import select_files

def create_schism_fieldset(settings):
    """
    Modified version of create_hydrodynamic_fieldset for SCHISM data.
    
    Key differences from NEMO:
    1. Different variable names (hvel_x/y vs vozocrtx/vomecrty)
    2. Unstructured grid (triangular mesh vs curvilinear)
    3. Sigma coordinates vs Z-levels
    4. Combined files vs separate U/V/W files
    """
    
    # SCHISM data location
    dirread_model = os.path.join(settings['ocean']['directory'], 
                                settings['ocean']['filename_style'])
    
    # Simulation parameters
    startdate = settings['simulation']['startdate']
    runtime = int(np.ceil(settings['simulation']['runtime'].total_seconds()/86400.))
    
    # SCHISM typically has combined output files
    schism_files = select_files(dirread_model, 'schout_%4i*.nc', startdate, runtime, dt_margin=3)
    
    # SCHISM grid file (contains mesh connectivity)
    grid_file = os.path.join(settings['ocean']['directory'], 'hgrid.gr3')  # or .nc format
    
    # File structure for SCHISM (all variables in same files)
    filenames = {
        'U': {'lon': grid_file, 'lat': grid_file, 'depth': schism_files[0], 'data': schism_files},
        'V': {'lon': grid_file, 'lat': grid_file, 'depth': schism_files[0], 'data': schism_files},
        'W': {'lon': grid_file, 'lat': grid_file, 'depth': schism_files[0], 'data': schism_files},
        'conservative_temperature': {'lon': grid_file, 'lat': grid_file, 'depth': schism_files[0], 'data': schism_files},
        'absolute_salinity': {'lon': grid_file, 'lat': grid_file, 'depth': schism_files[0], 'data': schism_files}
    }
    
    # SCHISM variable names (different from NEMO)
    variables = {
        'U': 'hvel_x',                    # Horizontal velocity X-component
        'V': 'hvel_y',                    # Horizontal velocity Y-component  
        'W': 'vertical_velocity',         # Vertical velocity
        'conservative_temperature': 'temp', # Temperature
        'absolute_salinity': 'salt'       # Salinity
    }
    
    # SCHISM dimensions (unstructured grid)
    dimensions = {
        'U': {
            'lon': 'SCHISM_hgrid_node_x',   # Node X coordinates
            'lat': 'SCHISM_hgrid_node_y',   # Node Y coordinates
            'depth': 'sigma',               # Sigma coordinates (terrain-following)
            'time': 'time'
        },
        'V': {
            'lon': 'SCHISM_hgrid_node_x',
            'lat': 'SCHISM_hgrid_node_y', 
            'depth': 'sigma',
            'time': 'time'
        },
        'W': {
            'lon': 'SCHISM_hgrid_node_x',
            'lat': 'SCHISM_hgrid_node_y',
            'depth': 'sigma', 
            'time': 'time'
        },
        'conservative_temperature': {
            'lon': 'SCHISM_hgrid_node_x',
            'lat': 'SCHISM_hgrid_node_y',
            'depth': 'sigma',
            'time': 'time'
        },
        'absolute_salinity': {
            'lon': 'SCHISM_hgrid_node_x', 
            'lat': 'SCHISM_hgrid_node_y',
            'depth': 'sigma',
            'time': 'time'
        }
    }
    
    # Indices (may need modification for unstructured grid)
    indices = settings['ocean'].get('indices', {})
    if not settings['use_3D']:
        indices['depth'] = range(0, 2)  # Surface layers only
    
    # Create fieldset - KEY MODIFICATION: Use from_netcdf instead of from_nemo
    try:
        fieldset = FieldSet.from_netcdf(filenames, variables, dimensions,
                                       mesh='flat',  # SCHISM often uses flat coordinates
                                       indices=indices, 
                                       allow_time_extrapolation=settings['allow_time_extrapolation'])
    except Exception as e:
        print(f"Error creating SCHISM fieldset: {e}")
        print("Trying alternative mesh configuration...")
        fieldset = FieldSet.from_netcdf(filenames, variables, dimensions,
                                       mesh='spherical',  # Try spherical if flat fails
                                       indices=indices,
                                       allow_time_extrapolation=settings['allow_time_extrapolation'])
    
    # Add constants (same as NEMO version)
    fieldset.add_constant('use_mixing', settings['use_mixing'])
    fieldset.add_constant('use_biofouling', settings['use_biofouling'])
    fieldset.add_constant('use_stokes', settings['use_stokes'])
    fieldset.add_constant('use_wind', settings['use_wind'])
    fieldset.add_constant('G', 9.81)
    fieldset.add_constant('use_3D', settings['use_3D'])
    
    # SCHISM bathymetry handling
    fieldset.add_constant('z_start', 0.5)
    
    # SCHISM bathymetry (node depths instead of level indices)
    bathymetry_file = os.path.join(settings['ocean']['directory'], 'hgrid.gr3')  # or depth.nc
    bathymetry_variables = {'bathymetry': 'depth'}  # SCHISM uses actual depths
    bathymetry_dimensions = {
        'lon': 'SCHISM_hgrid_node_x',
        'lat': 'SCHISM_hgrid_node_y'
    }
    
    try:
        bathymetry_field = Field.from_netcdf(bathymetry_file, bathymetry_variables, bathymetry_dimensions)
        fieldset.add_field(bathymetry_field)
    except Exception as e:
        print(f"Warning: Could not load SCHISM bathymetry: {e}")
        print("Simulation may not have proper bottom boundary conditions")
    
    # Vertical mixing (if available in SCHISM output)
    if fieldset.use_mixing:
        try:
            mixing_variables = {'mixing_kz': 'diffusivity_z'}  # SCHISM vertical diffusivity
            mixing_dimensions = dimensions['U']  # Same as velocity
            mixing_filenames = filenames['U']    # Same files as velocity
            
            mixing_fieldset = FieldSet.from_netcdf(mixing_filenames, mixing_variables, mixing_dimensions)
            fieldset.add_field(mixing_fieldset.mixing_kz)
        except Exception as e:
            print(f"Warning: Could not load SCHISM mixing data: {e}")
            fieldset.use_mixing = False
    
    return fieldset

def create_schism_settings_template():
    """
    Create a template settings dictionary for SCHISM integration.
    """
    schism_settings = {
        "use_3D": True,
        "allow_time_extrapolation": True,
        "verbose_delete": False,
        "use_mixing": False,  # Start with False, enable if data available
        "use_biofouling": False,
        "use_stokes": False,
        "use_wind": False,
        "ocean": {
            "modelname": "SCHISM",
            "directory": "/path/to/schism/outputs/",
            "filename_style": "schout_",
            "grid_file": "hgrid.gr3",  # SCHISM grid file
            "variables": {
                "U": "hvel_x",
                "V": "hvel_y", 
                "W": "vertical_velocity",
                "conservative_temperature": "temp",
                "absolute_salinity": "salt"
            },
            "dimensions": {
                # All variables use same dimensions in SCHISM
                "lon": "SCHISM_hgrid_node_x",
                "lat": "SCHISM_hgrid_node_y",
                "depth": "sigma",
                "time": "time"
            },
            "indices": {},
            "bathymetry_variables": {
                "bathymetry": "depth"
            },
            "bathymetry_dimensions": {
                "lon": "SCHISM_hgrid_node_x",
                "lat": "SCHISM_hgrid_node_y"
            }
        }
    }
    return schism_settings

# Example usage
if __name__ == "__main__":
    print("SCHISM Integration Template")
    print("===========================")
    print()
    print("To integrate SCHISM with PlasticParcels:")
    print("1. Modify plasticparcels/constructors.py")
    print("2. Add model detection logic")
    print("3. Use create_schism_fieldset() for SCHISM data")
    print("4. Create SCHISM-specific settings file")
    print("5. Test with simple 2D case first")
    print()
    print("Key challenges:")
    print("- Unstructured grid interpolation")
    print("- Sigma coordinate transformation") 
    print("- Different file structure")
    print("- Variable name mapping")
