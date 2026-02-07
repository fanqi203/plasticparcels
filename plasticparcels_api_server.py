#!/usr/bin/env python3
"""
PlasticParcels Trajectory API Server

A Flask server that accepts plastic release locations and generates
trajectories in GeoJSON format using PlasticParcels.
"""

import os
import sys
import json
import tempfile
import shutil
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import xarray as xr

# Add current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

app = Flask(__name__)
# Enable CORS for all routes with explicit configuration
CORS(app,
     origins=["*"],  # Allow all origins for development
     methods=["GET", "POST", "OPTIONS"],
     allow_headers=["Content-Type", "Authorization"],
     supports_credentials=False)

# Global configuration
DATA_DIR = None
SETTINGS = None
LAND_MASK = None  # 2D boolean array: True = land, False = ocean

def build_land_mask(data_dir):
    """Build a 2D land mask for the data grid using Natural Earth coastline."""
    try:
        from shapely.geometry import Point
        from shapely.prepared import prep
        import cartopy.io.shapereader as shpreader
        from shapely.ops import unary_union

        # Load Natural Earth 50m coastline
        land_shp = shpreader.natural_earth(resolution='50m', category='physical', name='land')
        reader = shpreader.Reader(land_shp)
        land = unary_union(list(reader.geometries()))
        land_prep = prep(land)

        # Read grid coordinates from first available U file
        u_files = sorted([f for f in os.listdir(data_dir) if f.startswith('U_') and f.endswith('.nc')])
        if not u_files:
            print("⚠️  No U files found, cannot build land mask")
            return None

        ds = xr.open_dataset(os.path.join(data_dir, u_files[0]))
        if 'nav_lat' in ds.data_vars or 'nav_lat' in ds.coords:
            nav_lat = ds['nav_lat'].values
            nav_lon = ds['nav_lon'].values
        else:
            print("⚠️  No nav_lat/nav_lon in data, cannot build land mask")
            ds.close()
            return None
        ds.close()

        ny, nx = nav_lat.shape
        mask = np.zeros((ny, nx), dtype=bool)
        for i in range(ny):
            for j in range(nx):
                mask[i, j] = land_prep.contains(Point(float(nav_lon[i, j]), float(nav_lat[i, j])))

        # Store grid bounds for index lookup
        lat_min_grid = float(nav_lat.min())
        lat_max_grid = float(nav_lat.max())
        lon_min_grid = float(nav_lon.min())
        lon_max_grid = float(nav_lon.max())
        print(f"🗺️  Land mask built: {mask.sum()} land / {(~mask).sum()} ocean points ({ny}×{nx} grid)")
        print(f"    Grid bounds: lat [{lat_min_grid}, {lat_max_grid}], lon [{lon_min_grid}, {lon_max_grid}]")
        return {'mask': mask, 'lat_min': lat_min_grid, 'lat_max': lat_max_grid,
                'lon_min': lon_min_grid, 'lon_max': lon_max_grid, 'ny': ny, 'nx': nx}

    except Exception as e:
        print(f"⚠️  Could not build land mask: {e}")
        return None


def load_mobile_bay_settings(data_dir):
    """Load Mobile Bay settings from the data directory."""
    settings_file = os.path.join(data_dir, 'settings.json')

    if not os.path.exists(settings_file):
        raise FileNotFoundError(f"Settings file not found: {settings_file}")

    with open(settings_file, 'r') as f:
        settings = json.load(f)

    return settings

def zarr_to_geojson(zarr_file):
    """Convert zarr trajectory file to GeoJSON format."""
    try:
        # Open zarr file
        ds = xr.open_zarr(zarr_file)

        # Extract trajectory data
        lons = ds.lon.values
        lats = ds.lat.values
        depths = ds.z.values if 'z' in ds else None
        times = ds.time.values if 'time' in ds else None

        # Handle different data shapes
        features = []

        if len(lons.shape) == 2:
            # Multiple particles: shape (particles, time) or (time, particles)
            if lons.shape[0] < lons.shape[1]:
                # Likely (particles, time)
                n_particles = lons.shape[0]
                for p in range(n_particles):
                    p_lons = lons[p, :]
                    p_lats = lats[p, :]

                    # Remove NaN values
                    valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                    if np.any(valid):
                        if depths is not None:
                            p_depths = depths[p, :]
                            coordinates = [[float(lon), float(lat), float(dep)]
                                         for lon, lat, dep in zip(p_lons[valid], p_lats[valid], p_depths[valid])]
                        else:
                            coordinates = [[float(lon), float(lat)]
                                         for lon, lat in zip(p_lons[valid], p_lats[valid])]

                        feature = {
                            "type": "Feature",
                            "properties": {
                                "particle_id": int(p),
                                "trajectory_length": len(coordinates)
                            },
                            "geometry": {
                                "type": "LineString",
                                "coordinates": coordinates
                            }
                        }
                        features.append(feature)
            else:
                # Likely (time, particles)
                n_particles = lons.shape[1]
                for p in range(n_particles):
                    p_lons = lons[:, p]
                    p_lats = lats[:, p]

                    # Remove NaN values
                    valid = ~np.isnan(p_lons) & ~np.isnan(p_lats)
                    if np.any(valid):
                        if depths is not None:
                            p_depths = depths[:, p]
                            coordinates = [[float(lon), float(lat), float(dep)]
                                         for lon, lat, dep in zip(p_lons[valid], p_lats[valid], p_depths[valid])]
                        else:
                            coordinates = [[float(lon), float(lat)]
                                         for lon, lat in zip(p_lons[valid], p_lats[valid])]

                        feature = {
                            "type": "Feature",
                            "properties": {
                                "particle_id": int(p),
                                "trajectory_length": len(coordinates)
                            },
                            "geometry": {
                                "type": "LineString",
                                "coordinates": coordinates
                            }
                        }
                        features.append(feature)
        else:
            # Single particle: 1D array
            valid = ~np.isnan(lons) & ~np.isnan(lats)
            if np.any(valid):
                if depths is not None:
                    coordinates = [[float(lon), float(lat), float(dep)]
                                 for lon, lat, dep in zip(lons[valid], lats[valid], depths[valid])]
                else:
                    coordinates = [[float(lon), float(lat)]
                                 for lon, lat in zip(lons[valid], lats[valid])]

                feature = {
                    "type": "Feature",
                    "properties": {
                        "particle_id": 0,
                        "trajectory_length": len(coordinates)
                    },
                    "geometry": {
                        "type": "LineString",
                        "coordinates": coordinates
                    }
                }
                features.append(feature)

        # Create GeoJSON
        geojson = {
            "type": "FeatureCollection",
            "features": features
        }

        ds.close()
        return geojson

    except Exception as e:
        raise Exception(f"Error converting zarr to GeoJSON: {e}")

def run_trajectory_simulation(release_locations, simulation_hours=72, output_minutes=30, dt_minutes=5, start_date=None, plastic_density=None, plastic_diameter=None):
    """Run PlasticParcels simulation with given release locations."""
    try:
        # Import PlasticParcels
        from plasticparcels.constructors import create_hydrodynamic_fieldset, create_particleset
        import parcels
        import copy

        # Create a deep copy of settings for this simulation
        settings = copy.deepcopy(SETTINGS)

        # Fix the directory path to be absolute
        if 'ocean' in settings and 'directory' in settings['ocean']:
            # Make sure the directory path is correct
            ocean_dir = settings['ocean']['directory']
            if not os.path.isabs(ocean_dir):
                # If it's relative, make it relative to DATA_DIR
                settings['ocean']['directory'] = os.path.join(DATA_DIR, '')

        # Add simulation settings
        # Use provided start_date or determine from available data
        if start_date is None:
            # Auto-detect start date from available data files
            available_files = [f for f in os.listdir(DATA_DIR) if f.startswith('U_') and f.endswith('.nc')]
            if available_files:
                # Extract dates and use the earliest one
                available_dates = []
                for f in available_files:
                    try:
                        date_part = f.replace('U_', '').replace('.nc', '')
                        date_obj = datetime.strptime(date_part, '%Y-%m-%d')
                        # Ensure timezone-naive for PlasticParcels compatibility
                        date_obj = date_obj.replace(tzinfo=None)
                        available_dates.append(date_obj)
                    except:
                        continue
                if available_dates:
                    start_date = min(available_dates)
                else:
                    start_date = datetime(2024, 1, 1, 0, 0, 0)  # Fallback
            else:
                start_date = datetime(2024, 1, 1, 0, 0, 0)  # Fallback
        
        settings['simulation'] = {
            'startdate': start_date,
            'runtime': timedelta(hours=simulation_hours),
            'outputdt': timedelta(minutes=output_minutes),
            'dt': timedelta(minutes=dt_minutes),
        }

        settings['plastictype'] = {
            'wind_coefficient': 0.0,
            'plastic_diameter': plastic_diameter if plastic_diameter is not None else 0.001,
            'plastic_density': plastic_density if plastic_density is not None else 1028.0,
        }
        print(f"Plastic properties: diameter={settings['plastictype']['plastic_diameter']}m, density={settings['plastictype']['plastic_density']}kg/m3")

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.zarr', delete=False) as tmp_file:
            output_file = tmp_file.name

        # Remove the temporary file (we just need the name)
        os.unlink(output_file)

        # Build kernel list based on 3D/2D mode
        if settings.get('use_3D', False):
            from plasticparcels.constructors import create_kernel
            kernels = create_kernel(fieldset)
            print(f"Running 3D simulation with full kernel chain (including SettlingVelocity)...")
        else:
            kernels = parcels.AdvectionRK4
            print(f"Running 2D simulation (horizontal advection only)...")

        # Run simulation
        pset.execute(
            kernels,
            runtime=settings['simulation']['runtime'],
            dt=settings['simulation']['dt'],
            output_file=pset.ParticleFile(name=output_file, outputdt=settings['simulation']['outputdt'])
        )

        return output_file

    except Exception as e:
        raise Exception(f"Simulation failed: {e}")

@app.route('/', methods=['GET'])
def root():
    """Root endpoint with API information."""
    return jsonify({
        "name": "PlasticParcels API Server",
        "version": "1.0.0",
        "description": "REST API for plastic trajectory simulations using PlasticParcels",
        "endpoints": {
            "health": "/health",
            "info": "/info",
            "simulate": "/simulate"
        },
        "data_dir": DATA_DIR,
        "status": "running"
    })

@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "data_dir": DATA_DIR,
        "settings_loaded": SETTINGS is not None
    })

@app.route('/simulate', methods=['POST'])
def simulate_trajectories():
    """
    Simulate plastic trajectories from given release locations.

    Expected JSON payload:
    {
        "release_locations": {
            "lons": [longitude1, longitude2, ...],
            "lats": [latitude1, latitude2, ...],
            "plastic_amount": [amount1, amount2, ...] (optional)
        },
        "simulation_hours": 72 (optional, default 72),
        "output_minutes": 30 (optional, default 30),
        "dt_minutes": 5 (optional, default 5),
        "start_date": "2025-10-13T00:00:00Z" (optional, auto-detected if not provided)
    }

    Returns GeoJSON FeatureCollection with trajectory LineStrings.
    """
    try:
        # Parse request
        data = request.get_json()

        if not data or 'release_locations' not in data:
            return jsonify({"error": "Missing release_locations in request"}), 400

        release_locations = data['release_locations']

        # Validate release locations
        if 'lons' not in release_locations or 'lats' not in release_locations:
            return jsonify({"error": "release_locations must contain 'lons' and 'lats'"}), 400

        lons = release_locations['lons']
        lats = release_locations['lats']

        if len(lons) != len(lats):
            return jsonify({"error": "lons and lats must have the same length"}), 400

        if len(lons) == 0:
            return jsonify({"error": "At least one release location is required"}), 400

        # Add plastic_amount if not provided
        if 'plastic_amount' not in release_locations:
            release_locations['plastic_amount'] = [1.0] * len(lons)

        # Get simulation parameters
        simulation_hours = data.get('simulation_hours', 72)
        output_minutes = data.get('output_minutes', 30)
        dt_minutes = data.get('dt_minutes', 5)
        
        # Parse start_date if provided
        start_date = None
        if 'start_date' in data:
            try:
                start_date_str = data['start_date']
                if isinstance(start_date_str, str):
                    # Parse ISO format date string and make it timezone-naive
                    start_date = datetime.fromisoformat(start_date_str.replace('Z', '+00:00'))
                    # Convert to timezone-naive datetime for PlasticParcels compatibility
                    start_date = start_date.replace(tzinfo=None)
                    print(f"Using user-specified start date: {start_date}")
            except Exception as e:
                print(f"Error parsing start_date: {e}. Using auto-detection.")
                start_date = None

        # Validate parameters
        if simulation_hours <= 0 or simulation_hours > 720:  # Max 30 days
            return jsonify({"error": "simulation_hours must be between 1 and 720"}), 400

        if output_minutes <= 0 or output_minutes > 1440:  # Max 1 day
            return jsonify({"error": "output_minutes must be between 1 and 1440"}), 400

        if dt_minutes <= 0 or dt_minutes > 60:  # Max 1 hour
            return jsonify({"error": "dt_minutes must be between 1 and 60"}), 400

        # Get plastic properties from request (optional)
        plastic_density = data.get('plastic_density', None)
        plastic_diameter = data.get('plastic_diameter', None)
        if plastic_density is not None:
            plastic_density = float(plastic_density)
        if plastic_diameter is not None:
            plastic_diameter = float(plastic_diameter)

        # Run simulation
        output_file = run_trajectory_simulation(
            release_locations,
            simulation_hours,
            output_minutes,
            dt_minutes,
            start_date,
            plastic_density,
            plastic_diameter
        )

        # Convert to GeoJSON
        geojson = zarr_to_geojson(output_file)

        # Clean up temporary file
        if os.path.exists(output_file):
            shutil.rmtree(output_file)

        return jsonify(geojson)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/vector-field', methods=['GET'])
def get_vector_field():
    """Get vector field data for a specific timestamp and bounding box."""
    try:
        # Get query parameters
        timestamp = request.args.get('timestamp')
        lat_min = float(request.args.get('lat_min', 30.2))
        lat_max = float(request.args.get('lat_max', 30.8))
        lon_min = float(request.args.get('lon_min', -88.6))
        lon_max = float(request.args.get('lon_max', -87.8))
        grid_density = int(request.args.get('grid_density', 15))
        
        if not timestamp:
            return jsonify({"error": "timestamp parameter required"}), 400
            
        # Parse timestamp to find appropriate NetCDF files
        try:
            import pandas as pd
            # More robust timestamp parsing
            if timestamp.endswith('Z'):
                timestamp_clean = timestamp[:-1] + '+00:00'
            else:
                timestamp_clean = timestamp
            
            # Try multiple parsing methods
            try:
                dt = datetime.fromisoformat(timestamp_clean)
            except:
                dt = pd.to_datetime(timestamp).to_pydatetime()
            
            date_str = dt.strftime('%Y-%m-%d')
            print(f"Parsed timestamp {timestamp} -> date {date_str}")
        except Exception as e:
            print(f"Timestamp parsing error: {e}")
            # Fallback to a default date if parsing fails
            date_str = '2024-01-01'
            print(f"Using fallback date: {date_str}")
            
        # Find U and V files for the date
        u_file = os.path.join(DATA_DIR, f'U_{date_str}.nc')
        v_file = os.path.join(DATA_DIR, f'V_{date_str}.nc')
        
        if not os.path.exists(u_file) or not os.path.exists(v_file):
            # Find all available dates and cycle through them based on simulation time
            available_files = [f for f in os.listdir(DATA_DIR) if f.startswith('U_') and f.endswith('.nc')]
            if available_files:
                # Extract dates from available files and sort them
                available_dates = []
                for f in available_files:
                    try:
                        date_part = f.replace('U_', '').replace('.nc', '')
                        available_dates.append(date_part)
                    except:
                        continue
                
                available_dates.sort()
                print(f"Available data dates: {available_dates}")
                
                if available_dates:
                    # Always start from 2024-01-01 and calculate simulation hours from that fixed start
                    try:
                        # Fixed simulation start time - always 2024-01-01T00:00:00Z
                        simulation_start = datetime(2024, 1, 1, 0, 0, 0)
                        
                        # Calculate hours elapsed since simulation start (ignore real-world date)
                        if dt.year == 2024 and dt.month == 1:  # If timestamp is already in simulation timeframe
                            time_diff = dt - simulation_start
                            simulation_hour = int(time_diff.total_seconds() // 3600)
                        else:
                            # For any other timestamp, extract just the hour and use it as simulation hour
                            simulation_hour = dt.hour
                        
                        day_index = (simulation_hour // 24) % len(available_dates)  # Cycle through days
                        selected_date = available_dates[day_index]
                        print(f"Fixed simulation start: 2024-01-01, simulation hour: {simulation_hour}, selected day index: {day_index}, using date: {selected_date}")
                    except Exception as e:
                        print(f"Error in simulation time calculation: {e}")
                        # Fallback to first available date
                        selected_date = available_dates[0]
                        print(f"Using fallback date: {selected_date}")
                    
                    u_file = os.path.join(DATA_DIR, f'U_{selected_date}.nc')
                    v_file = os.path.join(DATA_DIR, f'V_{selected_date}.nc')
                    print(f"Using files: {u_file}, {v_file}")
                else:
                    return jsonify({"error": f"No valid ocean current data files found"}), 404
            else:
                return jsonify({"error": f"No ocean current data available for {date_str}"}), 404
                
        # Load NetCDF data
        u_ds = xr.open_dataset(u_file)
        v_ds = xr.open_dataset(v_file)
        
        # Get variable names for SCHISM ocean model
        # U variable is 'vozocrtx', V variable is 'vomecrty'
        u_var = None
        v_var = None
        
        # Check for SCHISM variable names first
        if 'vozocrtx' in u_ds.data_vars:
            u_var = 'vozocrtx'
        elif 'u' in u_ds.data_vars:
            u_var = 'u'
        else:
            # Try other common names
            for var in u_ds.data_vars:
                if var.lower() in ['u', 'eastward_velocity', 'u_velocity']:
                    u_var = var
                    break
                    
        if 'vomecrty' in v_ds.data_vars:
            v_var = 'vomecrty'
        elif 'v' in v_ds.data_vars:
            v_var = 'v'
        else:
            # Try other common names
            for var in v_ds.data_vars:
                if var.lower() in ['v', 'northward_velocity', 'v_velocity']:
                    v_var = var
                    break
                
        if u_var is None or v_var is None:
            available_vars = list(u_ds.data_vars) + list(v_ds.data_vars)
            return jsonify({"error": f"Could not find U/V velocity variables. Available: {available_vars}"}), 500
            
        print(f"Using variables: U={u_var}, V={v_var}")
            
        # Get the appropriate time step based on requested timestamp
        # SCHISM uses 'time_counter' instead of 'time'
        u_full = u_ds[u_var]
        v_full = v_ds[v_var]
        
        # Find the best time index for the requested timestamp
        time_index = 0  # Default to first time step
        
        if 'time_counter' in u_full.dims:
            time_coords = u_full.time_counter.values
            print(f"Available time steps: {len(time_coords)}")
            print(f"Time range: {time_coords[0]} to {time_coords[-1]}")
            
            # Parse the requested timestamp - simplified approach
            try:
                import numpy as np
                from datetime import datetime
                import pandas as pd
                
                print(f"Raw timestamp received: {timestamp}")
                
                # Parse the requested timestamp
                if timestamp.endswith('Z'):
                    timestamp = timestamp[:-1] + '+00:00'
                
                requested_time = pd.to_datetime(timestamp)
                print(f"Parsed requested time: {requested_time}")
                
                # Convert time coordinates to pandas datetime for easier comparison
                time_coords_pd = pd.to_datetime(time_coords)
                print(f"Time coords range: {time_coords_pd[0]} to {time_coords_pd[-1]}")
                
                # Find the closest time index
                time_diffs = np.abs(time_coords_pd - requested_time)
                time_index = int(np.argmin(time_diffs))
                
                closest_time = time_coords_pd[time_index]
                print(f"Using time index {time_index}: {closest_time}")
                
            except Exception as e:
                print(f"Error parsing timestamp: {e}")
                print(f"Timestamp type: {type(timestamp)}")
                print(f"Time coords type: {type(time_coords)}")
                print(f"Time coords sample: {time_coords[:3] if len(time_coords) > 0 else 'empty'}")
                # For now, use a simple hour-based approach as fallback
                try:
                    # Extract hour from timestamp and use modulo for cycling
                    hour_match = timestamp.split('T')[1].split(':')[0] if 'T' in timestamp else '0'
                    hour = int(hour_match) % len(time_coords)
                    time_index = hour
                    print(f"Fallback: using hour-based index {time_index}")
                except:
                    time_index = 0
                    print("Using first time step as final fallback")
            
            u_data = u_full.isel(time_counter=time_index)
            v_data = v_full.isel(time_counter=time_index)
            
        elif 'time' in u_full.dims:
            # Similar logic for 'time' dimension
            time_coords = u_full.time.values
            try:
                from datetime import datetime
                import numpy as np
                
                requested_time = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                requested_np_time = np.datetime64(requested_time)
                time_diffs = np.abs(time_coords - requested_np_time)
                time_index = int(np.argmin(time_diffs))
                print(f"Using time index {time_index} from 'time' dimension")
            except Exception as e:
                print(f"Error parsing timestamp for 'time' dimension: {e}")
                time_index = 0
                
            u_data = u_full.isel(time=time_index)
            v_data = v_full.isel(time=time_index)
            
        else:
            # Use first time step regardless of dimension name
            time_dims = [d for d in u_full.dims if 'time' in d.lower()]
            if time_dims:
                time_dim = time_dims[0]
                u_data = u_full.isel({time_dim: 0})
                v_data = v_full.isel({time_dim: 0})
                print(f"Using first time step from dimension: {time_dim}")
            else:
                # No time dimension, use data as is
                u_data = u_full
                v_data = v_full
                print("No time dimension found, using data as-is")
        
        # If data has a depth dimension, select surface level (index 0)
        for depth_dim in ['depthw', 'depthu', 'depthv', 'depth']:
            if depth_dim in u_data.dims:
                u_data = u_data.isel({depth_dim: 0})
                print(f"Selected surface level from depth dimension: {depth_dim}")
                break
        for depth_dim in ['depthw', 'depthu', 'depthv', 'depth']:
            if depth_dim in v_data.dims:
                v_data = v_data.isel({depth_dim: 0})
                break
        
        print(f"u_data shape after time/depth selection: {u_data.shape}")

        # Get coordinate arrays for SCHISM format
        # SCHISM uses 'nav_lat' and 'nav_lon' as data variables (not coordinates)
        if 'nav_lat' in u_ds.data_vars and 'nav_lon' in u_ds.data_vars:
            lats = u_ds.nav_lat.values
            lons = u_ds.nav_lon.values
            print(f"Using SCHISM data variables: nav_lat, nav_lon")
        elif 'nav_lat' in u_data.coords and 'nav_lon' in u_data.coords:
            lats = u_data.nav_lat.values
            lons = u_data.nav_lon.values
            print(f"Using SCHISM coordinates: nav_lat, nav_lon")
        elif 'lat' in u_data.coords:
            lats = u_data.lat.values
            lons = u_data.lon.values
        elif 'latitude' in u_data.coords:
            lats = u_data.latitude.values
            lons = u_data.longitude.values
        else:
            available_coords = list(u_data.coords)
            available_vars = list(u_ds.data_vars)
            return jsonify({"error": f"Could not find lat/lon coordinates. Available coords: {available_coords}, Available vars: {available_vars}"}), 500
            
        print(f"Coordinate shapes: lats={lats.shape}, lons={lons.shape}")
            
        # Create meshgrid if needed
        if len(lats.shape) == 1 and len(lons.shape) == 1:
            lon_grid, lat_grid = np.meshgrid(lons, lats)
        else:
            lat_grid = lats
            lon_grid = lons
            
        # Filter data to bounding box
        lat_mask = (lat_grid >= lat_min) & (lat_grid <= lat_max)
        lon_mask = (lon_grid >= lon_min) & (lon_grid <= lon_max)
        mask = lat_mask & lon_mask
        
        # Subsample based on grid density with aspect ratio correction
        if len(lat_grid.shape) == 2:
            # Calculate aspect ratio of the requested region
            lat_range = lat_max - lat_min
            lon_range = lon_max - lon_min
            aspect_ratio = lon_range / lat_range
            
            # Adjust grid density for longitude to account for aspect ratio
            # This ensures more uniform spacing in both directions
            grid_density_lat = grid_density
            grid_density_lon = max(grid_density, int(grid_density * aspect_ratio))
            
            step_lat = max(1, lat_grid.shape[0] // grid_density_lat)
            step_lon = max(1, lat_grid.shape[1] // grid_density_lon)
            
            print(f"Grid density adjustment: lat_range={lat_range:.1f}°, lon_range={lon_range:.1f}°, aspect_ratio={aspect_ratio:.1f}")
            print(f"Grid densities: lat={grid_density_lat}, lon={grid_density_lon}")
            print(f"Steps: lat={step_lat}, lon={step_lon}")
            
            # Apply subsampling
            lat_sub = lat_grid[::step_lat, ::step_lon]
            lon_sub = lon_grid[::step_lat, ::step_lon]
            mask_sub = mask[::step_lat, ::step_lon]
            u_sub = u_data.values[::step_lat, ::step_lon]
            v_sub = v_data.values[::step_lat, ::step_lon]
        else:
            # Handle 1D case
            lat_indices = np.where((lats >= lat_min) & (lats <= lat_max))[0]
            lon_indices = np.where((lons >= lon_min) & (lons <= lon_max))[0]
            
            step_lat = max(1, len(lat_indices) // grid_density)
            step_lon = max(1, len(lon_indices) // grid_density)
            
            lat_sub_idx = lat_indices[::step_lat]
            lon_sub_idx = lon_indices[::step_lon]
            
            lat_sub = lats[lat_sub_idx]
            lon_sub = lons[lon_sub_idx]
            
            # Create subsampled data
            u_sub = u_data.values[np.ix_(lat_sub_idx, lon_sub_idx)]
            v_sub = v_data.values[np.ix_(lat_sub_idx, lon_sub_idx)]
            
            lon_grid_sub, lat_grid_sub = np.meshgrid(lon_sub, lat_sub)
            lat_sub = lat_grid_sub
            lon_sub = lon_grid_sub
            mask_sub = np.ones_like(lat_sub, dtype=bool)
            
        # Create vector field data (skip land points using precomputed land mask)
        vectors = []
        for i in range(lat_sub.shape[0]):
            for j in range(lat_sub.shape[1]):
                if mask_sub[i, j] and not (np.isnan(u_sub[i, j]) or np.isnan(v_sub[i, j])):
                    # Skip land points if land mask is available
                    if LAND_MASK is not None:
                        lm = LAND_MASK
                        lat_val = float(lat_sub[i, j])
                        lon_val = float(lon_sub[i, j])
                        gi = int(round((lat_val - lm['lat_min']) / (lm['lat_max'] - lm['lat_min']) * (lm['ny'] - 1)))
                        gj = int(round((lon_val - lm['lon_min']) / (lm['lon_max'] - lm['lon_min']) * (lm['nx'] - 1)))
                        gi = max(0, min(gi, lm['ny'] - 1))
                        gj = max(0, min(gj, lm['nx'] - 1))
                        if lm['mask'][gi, gj]:
                            continue
                    u_val = float(u_sub[i, j])
                    v_val = float(v_sub[i, j])
                    magnitude = float(np.sqrt(u_val**2 + v_val**2))
                    
                    vectors.append({
                        "lat": float(lat_sub[i, j]),
                        "lng": float(lon_sub[i, j]),
                        "u": u_val,
                        "v": v_val,
                        "magnitude": magnitude
                    })
                    
        # Close datasets
        u_ds.close()
        v_ds.close()
        
        response_data = {
            "timestamp": timestamp,
            "vectors": vectors,
            "bounds": {
                "lat_min": lat_min,
                "lat_max": lat_max,
                "lon_min": lon_min,
                "lon_max": lon_max
            },
            "grid_density": grid_density,
            "data_source": "real",
            "files_used": [u_file, v_file]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error in get_vector_field: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500

@app.route('/info', methods=['GET'])
def get_info():
    """Get information about the loaded dataset."""
    try:
        if SETTINGS is None:
            return jsonify({"error": "No settings loaded"}), 500

        # Import PlasticParcels to get fieldset info
        from plasticparcels.constructors import create_hydrodynamic_fieldset
        import copy

        # Create temporary settings for fieldset creation
        temp_settings = copy.deepcopy(SETTINGS)

        # Fix the directory path to be absolute
        if 'ocean' in temp_settings and 'directory' in temp_settings['ocean']:
            ocean_dir = temp_settings['ocean']['directory']
            if not os.path.isabs(ocean_dir):
                temp_settings['ocean']['directory'] = os.path.join(DATA_DIR, '')

        temp_settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=1),
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=30),
        }

        fieldset = create_hydrodynamic_fieldset(temp_settings)

        info = {
            "domain": {
                "lon_min": float(fieldset.U.grid.lon.min()),
                "lon_max": float(fieldset.U.grid.lon.max()),
                "lat_min": float(fieldset.U.grid.lat.min()),
                "lat_max": float(fieldset.U.grid.lat.max())
            },
            "grid_shape": list(fieldset.U.grid.lat.shape),
            "time_steps": len(fieldset.U.grid.time),
            "time_range": {
                "start": float(fieldset.U.grid.time[0]),
                "end": float(fieldset.U.grid.time[-1])
            },
            "data_directory": DATA_DIR
        }

        return jsonify(info)

    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/data-range', methods=['GET'])
def get_data_range():
    """Get the available data date range."""
    try:
        if not DATA_DIR:
            return jsonify({"error": "Server not initialized"}), 500

        # Find all available U files (velocity data)
        available_files = [f for f in os.listdir(DATA_DIR) if f.startswith('U_') and f.endswith('.nc')]

        if not available_files:
            return jsonify({"error": "No data files found"}), 404

        # Extract dates from filenames
        available_dates = []
        for f in available_files:
            try:
                date_part = f.replace('U_', '').replace('.nc', '')
                # Validate date format
                datetime.strptime(date_part, '%Y-%m-%d')
                available_dates.append(date_part)
            except ValueError:
                continue

        if not available_dates:
            return jsonify({"error": "No valid date files found"}), 404

        available_dates.sort()
        start_date = available_dates[0]
        end_date = available_dates[-1]

        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "total_days": len(available_dates),
            "available_dates": available_dates
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

def initialize_server(data_dir):
    """Initialize the server with Mobile Bay data."""
    global DATA_DIR, SETTINGS, LAND_MASK

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # Load settings
    SETTINGS = load_mobile_bay_settings(data_dir)
    DATA_DIR = data_dir

    # Build land mask for vector field filtering
    LAND_MASK = build_land_mask(data_dir)

    print(f"✅ Server initialized with data from: {data_dir}")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="PlasticParcels Trajectory API Server")
    parser.add_argument('data_dir', help='Directory containing Mobile Bay data')
    parser.add_argument('--host', default='127.0.0.1', help='Host to bind to')
    parser.add_argument('--port', type=int, default=5000, help='Port to bind to')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode')

    args = parser.parse_args()

    # Initialize server
    try:
        initialize_server(args.data_dir)
        print(f"🚀 Starting PlasticParcels API server on {args.host}:{args.port}")
        app.run(host=args.host, port=args.port, debug=args.debug)
    except Exception as e:
        print(f"❌ Failed to start server: {e}")
        sys.exit(1)
