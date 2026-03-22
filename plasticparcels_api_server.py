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
import threading
from flask import Flask, request, jsonify
from flask_cors import CORS
import numpy as np
import xarray as xr
import pandas as pd

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
SIM_LOCK = threading.Lock()  # Serialize simulations to prevent HDF5 concurrency issues

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

def SurfaceWindageDrift(particle, fieldset, time):
    """Custom windage kernel without the depth-restriction from the stock WindageDrift.

    The built-in WindageDrift only fires when particle.depth < 0.5*plastic_diameter
    (i.e. < 0.5 mm for 1-mm particles), which is never satisfied in 3-D sigma-level
    grids where even the surface layer centre sits at ~0.5 m depth.

    This kernel applies leeway to ALL particles, making it suitable for sigma-
    coordinate ocean models such as STOFS-3D / SCHISM.
    NOTE: Do not use 'import' statements inside Parcels kernels - they are transpiled to C.
    """
    (ocean_U, ocean_V) = fieldset.UV[particle]
    wind_U = fieldset.Wind_U[time, particle.depth, particle.lat, particle.lon]
    wind_V = fieldset.Wind_V[time, particle.depth, particle.lat, particle.lon]
    # Leeway: u_eff = u_ocean + C_w * (u_wind - u_ocean)
    particle_dlon += particle.wind_coefficient * (wind_U - ocean_U) * particle.dt  # noqa
    particle_dlat += particle.wind_coefficient * (wind_V - ocean_V) * particle.dt  # noqa


def run_trajectory_simulation(release_locations, simulation_hours=72, output_minutes=30, dt_minutes=5, start_date=None, plastic_density=None, plastic_diameter=None, wind_coefficient=None, use_biofouling=False, use_stokes=True):
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

        # Apply use_biofouling flag (must be in settings before create_hydrodynamic_fieldset)
        settings['use_biofouling'] = bool(use_biofouling)

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

        # Determine wind coefficient (used by WindageDrift kernel magnitude)
        actual_wind_coefficient = float(wind_coefficient) if wind_coefficient is not None else 0.0

        settings['plastictype'] = {
            'wind_coefficient': actual_wind_coefficient,
            'plastic_diameter': plastic_diameter if plastic_diameter is not None else 0.001,
            'plastic_density': plastic_density if plastic_density is not None else 1028.0,
        }
        print(f"Plastic properties: diameter={settings['plastictype']['plastic_diameter']}m, density={settings['plastictype']['plastic_density']}kg/m3, wind_coeff={actual_wind_coefficient}")

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)

        # Load optional wind/wave fields (must be done BEFORE creating particleset)
        wind_loaded = False
        stokes_loaded = False

        wind_dir = os.path.join(DATA_DIR, 'wind')
        wind_file = os.path.join(wind_dir, f'Wind_{start_date.strftime("%Y-%m-%d")}.nc')
        print(f"Looking for wind file: {wind_file}")

        if os.path.exists(wind_file):
            try:
                from parcels import FieldSet as ParcelsFieldSet
                from parcels.tools.converters import Geographic, GeographicPolar

                filenames_wind = {'Wind_U': wind_file, 'Wind_V': wind_file}
                variables_wind = {'Wind_U': 'u10', 'Wind_V': 'v10'}
                dimensions_wind = {'lon': 'longitude', 'lat': 'latitude', 'time': 'time'}

                fieldset_wind = ParcelsFieldSet.from_netcdf(
                    filenames_wind, variables_wind, dimensions_wind,
                    mesh='spherical', allow_time_extrapolation=True
                )
                fieldset_wind.Wind_U.units = GeographicPolar()
                fieldset_wind.Wind_V.units = Geographic()

                fieldset.add_field(fieldset_wind.Wind_U)
                fieldset.add_field(fieldset_wind.Wind_V)

                wind_loaded = True
                print(f"Wind fields loaded from {wind_file}")
            except Exception as e:
                print(f"WARNING: Failed to load wind fields: {e}")
                wind_loaded = False
        else:
            print(f"WARNING: Wind file not found: {wind_file}. Running without wind.")

        # Stokes is enabled when use_stokes=True AND a matching waves file exists.
        waves_dir = os.path.join(DATA_DIR, 'waves')
        waves_file = os.path.join(waves_dir, f'Waves_{start_date.strftime("%Y-%m-%d")}.nc')
        if use_stokes:
            print(f"Looking for waves file: {waves_file}")
        else:
            print("Stokes drift disabled by use_stokes=False.")
        if use_stokes and os.path.exists(waves_file):
            try:
                from parcels import FieldSet as ParcelsFieldSet
                from parcels.tools.converters import Geographic, GeographicPolar

                filenames_stokes = {'Stokes_U': waves_file, 'Stokes_V': waves_file, 'wave_Tp': waves_file}
                variables_stokes = {'Stokes_U': 'Stokes_U', 'Stokes_V': 'Stokes_V', 'wave_Tp': 'wave_Tp'}
                dimensions_stokes = {'lon': 'longitude', 'lat': 'latitude', 'time': 'time'}

                fieldset_stokes = ParcelsFieldSet.from_netcdf(
                    filenames_stokes, variables_stokes, dimensions_stokes,
                    mesh='spherical', allow_time_extrapolation=True
                )
                fieldset_stokes.Stokes_U.units = GeographicPolar()
                fieldset_stokes.Stokes_V.units = Geographic()

                fieldset.add_field(fieldset_stokes.Stokes_U)
                fieldset.add_field(fieldset_stokes.Stokes_V)
                fieldset.add_field(fieldset_stokes.wave_Tp)

                stokes_loaded = True
                print(f"Stokes fields loaded from {waves_file}")
            except Exception as e:
                print(f"WARNING: Failed to load Stokes fields: {e}")
                stokes_loaded = False
        else:
            print(f"WARNING: Waves file not found: {waves_file}. Running without Stokes drift.")

        # ── BGC fields for biofouling ──────────────────────────────────────────
        if use_biofouling:
            bgc_dir = os.path.join(DATA_DIR, 'bgc')
            bgc_file = os.path.join(bgc_dir, f'BGC_{start_date.strftime("%Y-%m-%d")}.nc')

            # Fallback: find the closest available BGC file
            if not os.path.exists(bgc_file) and os.path.isdir(bgc_dir):
                available_bgc = sorted([
                    f for f in os.listdir(bgc_dir) if f.startswith('BGC_') and f.endswith('.nc')
                ])
                if available_bgc:
                    bgc_file = os.path.join(bgc_dir, available_bgc[-1])
                    print(f"BGC file for {start_date.date()} not found; using {available_bgc[-1]}")

            if os.path.exists(bgc_file):
                # ── Pre-validate BGC file to avoid segfault in C netCDF/HDF5 layer ──
                # ParcelsField.from_netcdf segfaults on malformed/stub files; always
                # check with netCDF4 first before handing off to Parcels.
                _required_bgc_vars = ('nppv', 'phy', 'phy2')
                _bgc_valid = False
                try:
                    import netCDF4 as _nc4
                    with _nc4.Dataset(bgc_file) as _ds:
                        _file_vars = set(_ds.variables.keys())
                        _missing = [v for v in _required_bgc_vars if v not in _file_vars]
                        if _missing:
                            print(f"WARNING: BGC file missing required variables {_missing}. "
                                  "Biofouling disabled for this run.")
                        else:
                            _bgc_valid = True
                except Exception as _e:
                    print(f"WARNING: Could not validate BGC file: {_e}. "
                          "Biofouling disabled for this run.")

                if _bgc_valid:
                    try:
                        from parcels import Field as ParcelsField
                        bgc_dims = {'lon': 'longitude', 'lat': 'latitude',
                                    'depth': 'depth', 'time': 'time'}

                        pp_phyto = ParcelsField.from_netcdf(
                            bgc_file, ('pp_phyto', 'nppv'), bgc_dims,
                            mesh='spherical', allow_time_extrapolation=True)
                        bio_nanophy = ParcelsField.from_netcdf(
                            bgc_file, ('bio_nanophy', 'phy'), bgc_dims,
                            mesh='spherical', allow_time_extrapolation=True)
                        bio_diatom = ParcelsField.from_netcdf(
                            bgc_file, ('bio_diatom', 'phy2'), bgc_dims,
                            mesh='spherical', allow_time_extrapolation=True)

                        fieldset.add_field(pp_phyto)
                        fieldset.add_field(bio_nanophy)
                        fieldset.add_field(bio_diatom)

                        # Add BGC constants from settings
                        bgc_constants = settings.get('bgc', {}).get('constants', {})
                        for key, val in bgc_constants.items():
                            fieldset.add_constant(key, val)

                        print(f"✅ BGC fields loaded from {bgc_file}")
                    except Exception as e:
                        print(f"WARNING: Failed to load BGC fields: {e}. "
                              "Biofouling disabled for this run.")
                        settings['use_biofouling'] = False
                        fieldset.use_biofouling = 0
                else:
                    settings['use_biofouling'] = False
                    fieldset.use_biofouling = 0
            else:
                print(f"WARNING: BGC file not found: {bgc_file}. "
                      "Biofouling disabled for this run.")
                settings['use_biofouling'] = False
                fieldset.use_biofouling = 0

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

            def _kernel_name(kernel_obj):
                name = getattr(kernel_obj, '__name__', None)
                if name:
                    return name
                pyfunc = getattr(kernel_obj, 'pyfunc', None)
                return getattr(pyfunc, '__name__', None)

            def _has_kernel(name):
                return any(_kernel_name(k) == name for k in kernels)

            def _insert_before_status_checks(kernel_fn):
                insert_pos = len(kernels)
                for i, k in enumerate(kernels):
                    if _kernel_name(k) in ('checkThroughBathymetry', 'checkErrorThroughSurface', 'periodicBC', 'deleteParticle'):
                        insert_pos = i
                        break
                kernels.insert(insert_pos, kernel_fn)

            if stokes_loaded and not _has_kernel('StokesDrift'):
                from plasticparcels.kernels import StokesDrift
                _insert_before_status_checks(StokesDrift)
                print("Added StokesDrift kernel")

            if wind_loaded and actual_wind_coefficient > 0 and not _has_kernel('SurfaceWindageDrift'):
                _insert_before_status_checks(SurfaceWindageDrift)
                print(f"Added SurfaceWindageDrift kernel (wind_coefficient={actual_wind_coefficient})")
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
        "start_date": "2025-10-13T00:00:00Z" (optional, auto-detected if not provided),
        "use_biofouling": false (optional, default false — enables algal biofouling settling)
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

        # Get wind coefficient from request (optional)
        wind_coefficient = data.get('wind_coefficient', 0.0)
        if wind_coefficient is not None:
            wind_coefficient = float(wind_coefficient)

        # Get biofouling flag from request (optional, default False)
        use_biofouling = bool(data.get('use_biofouling', False))

        # Get Stokes drift flag from request (optional, default True)
        use_stokes = bool(data.get('use_stokes', True))

        # Run simulation (serialized to avoid HDF5 thread conflicts)
        with SIM_LOCK:
            output_file = run_trajectory_simulation(
            release_locations,
            simulation_hours,
            output_minutes,
            dt_minutes,
            start_date,
            plastic_density,
            plastic_diameter,
            wind_coefficient,
            use_biofouling,
            use_stokes,
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
        requested_depth = float(request.args.get('depth', 0.0))  # depth in meters (positive down)
        
        if not timestamp:
            return jsonify({"error": "timestamp parameter required"}), 400
            
        # Parse timestamp once and normalize to UTC for robust matching
        try:
            requested_time_utc = pd.to_datetime(timestamp, utc=True)
            # Use timezone-naive datetime only where date strings are needed
            dt = requested_time_utc.tz_localize(None).to_pydatetime()
            date_str = requested_time_utc.strftime('%Y-%m-%d')
            print(f"Parsed timestamp {timestamp} -> {requested_time_utc.isoformat()} (date {date_str})")
        except Exception as e:
            return jsonify({"error": f"Invalid timestamp format: {timestamp} ({e})"}), 400
            
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
            
            # Parse and match timestamps in UTC to avoid tz-aware/naive mismatch
            try:
                print(f"Requested UTC time: {requested_time_utc.isoformat()}")

                # Convert model timestamps to UTC-aware values
                time_coords_pd = pd.to_datetime(time_coords, utc=True)
                print(f"Time coords range (UTC): {time_coords_pd[0]} to {time_coords_pd[-1]}")

                # Find closest available model time step
                time_diffs = np.abs(time_coords_pd - requested_time_utc)
                time_index = int(np.argmin(time_diffs))

                closest_time = time_coords_pd[time_index]
                print(f"Using time index {time_index}: {closest_time} (UTC)")
            except Exception as e:
                print(f"Error matching requested timestamp to model times: {e}")
                print(f"Timestamp type: {type(timestamp)}")
                print(f"Time coords type: {type(time_coords)}")
                print(f"Time coords sample: {time_coords[:3] if len(time_coords) > 0 else 'empty'}")
                time_index = 0
                print("Fallback: using first time step")
            
            u_data = u_full.isel(time_counter=time_index)
            v_data = v_full.isel(time_counter=time_index)
            
        elif 'time' in u_full.dims:
            # Similar logic for 'time' dimension
            time_coords = u_full.time.values
            try:
                time_coords_pd = pd.to_datetime(time_coords, utc=True)
                time_diffs = np.abs(time_coords_pd - requested_time_utc)
                time_index = int(np.argmin(time_diffs))
                closest_time = time_coords_pd[time_index]
                print(f"Using time index {time_index} from 'time' dimension: {closest_time} (UTC)")
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
        
        # Select depth level closest to requested depth
        depth_index = 0  # default: surface
        selected_depth = 0.0
        for depth_dim in ['depthw', 'depthu', 'depthv', 'depth']:
            if depth_dim in u_data.dims:
                depth_values = u_data[depth_dim].values
                # Find closest depth level (depths are positive: 0, 5, 10, 20, ...)
                abs_requested = abs(requested_depth)  # handle negative depths too
                depth_index = int(np.argmin(np.abs(depth_values - abs_requested)))
                selected_depth = float(depth_values[depth_index])
                u_data = u_data.isel({depth_dim: depth_index})
                print(f"Requested depth: {requested_depth}m -> selected depth level {depth_index}: {selected_depth}m (dim: {depth_dim})")
                break
        for depth_dim in ['depthw', 'depthu', 'depthv', 'depth']:
            if depth_dim in v_data.dims:
                v_data = v_data.isel({depth_dim: depth_index})
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
            "depth": selected_depth,
            "files_used": [u_file, v_file]
        }
        
        return jsonify(response_data)
        
    except Exception as e:
        import traceback
        print(f"Error in get_vector_field: {e}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500


@app.route('/wind-field', methods=['GET'])
def get_wind_field():
    """Get wind vector field data for a specific timestamp and bounding box."""
    try:
        import numpy as np
        import pandas as pd
        
        # Get query parameters
        timestamp = request.args.get('timestamp')
        lat_min = float(request.args.get('lat_min', 24.0))
        lat_max = float(request.args.get('lat_max', 34.0))
        lon_min = float(request.args.get('lon_min', -93.0))
        lon_max = float(request.args.get('lon_max', -71.0))
        grid_density = int(request.args.get('grid_density', 15))
        
        if not timestamp:
            return jsonify({"error": "timestamp parameter required"}), 400
        
        # Parse timestamp to find appropriate wind file
        try:
            if timestamp.endswith('Z'):
                timestamp_clean = timestamp[:-1] + '+00:00'
            else:
                timestamp_clean = timestamp
            try:
                dt = datetime.fromisoformat(timestamp_clean)
            except:
                dt = pd.to_datetime(timestamp).to_pydatetime()
            date_str = dt.strftime('%Y-%m-%d')
        except Exception as e:
            return jsonify({"error": f"Invalid timestamp: {e}"}), 400
        
        # Find wind file for the date
        wind_dir = os.path.join(DATA_DIR, 'wind')
        wind_file = os.path.join(wind_dir, f'Wind_{date_str}.nc')
        
        if not os.path.exists(wind_file):
            # Try to find closest available wind file
            available = sorted([f for f in os.listdir(wind_dir) if f.startswith('Wind_') and f.endswith('.nc')]) if os.path.isdir(wind_dir) else []
            if available:
                # Use the closest date
                available_dates = [f.replace('Wind_', '').replace('.nc', '') for f in available]
                closest_date = min(available_dates, key=lambda d: abs(pd.to_datetime(d) - pd.to_datetime(date_str)))
                wind_file = os.path.join(wind_dir, f'Wind_{closest_date}.nc')
                print(f"Wind file for {date_str} not found, using closest: {closest_date}")
            else:
                return jsonify({"error": f"No wind data available. Wind dir: {wind_dir}"}), 404
        
        # Load wind NetCDF
        ds = xr.open_dataset(wind_file)
        
        # Find closest time step
        time_index = 0
        try:
            requested_time = pd.to_datetime(timestamp.replace('Z', '+00:00'))
            time_coords = pd.to_datetime(ds.time.values)
            time_diffs = np.abs(time_coords - requested_time)
            time_index = int(np.argmin(time_diffs))
        except Exception as e:
            print(f"Wind time parsing fallback: {e}")
        
        u10 = ds['u10'].isel(time=time_index).values  # shape: (lat, lon)
        v10 = ds['v10'].isel(time=time_index).values
        lats = ds['latitude'].values
        lons = ds['longitude'].values
        
        ds.close()
        
        # Create meshgrid
        lon_grid, lat_grid = np.meshgrid(lons, lats)
        
        # Filter to bounding box
        lat_mask = (lat_grid >= lat_min) & (lat_grid <= lat_max)
        lon_mask = (lon_grid >= lon_min) & (lon_grid <= lon_max)
        bbox_mask = lat_mask & lon_mask
        
        # Subsample based on grid density
        lat_range = lat_max - lat_min
        lon_range = lon_max - lon_min
        aspect_ratio = lon_range / lat_range if lat_range > 0 else 1.0
        
        grid_density_lat = grid_density
        grid_density_lon = max(grid_density, int(grid_density * aspect_ratio))
        
        step_lat = max(1, lat_grid.shape[0] // grid_density_lat)
        step_lon = max(1, lat_grid.shape[1] // grid_density_lon)
        
        lat_sub = lat_grid[::step_lat, ::step_lon]
        lon_sub = lon_grid[::step_lat, ::step_lon]
        mask_sub = bbox_mask[::step_lat, ::step_lon]
        u_sub = u10[::step_lat, ::step_lon]
        v_sub = v10[::step_lat, ::step_lon]
        
        # Build vectors list (skip land using precomputed mask)
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
        
        print(f"Wind field: {len(vectors)} vectors for {date_str}, time_index={time_index}")
        
        return jsonify({
            "timestamp": timestamp,
            "vectors": vectors,
            "bounds": {"lat_min": lat_min, "lat_max": lat_max, "lon_min": lon_min, "lon_max": lon_max},
            "grid_density": grid_density,
            "data_source": "real",
            "files_used": [wind_file]
        })
        
    except Exception as e:
        import traceback
        print(f"Error in get_wind_field: {e}")
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
