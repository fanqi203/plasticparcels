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

def run_trajectory_simulation(release_locations, simulation_hours=72, output_minutes=30, dt_minutes=5):
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
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(hours=simulation_hours),
            'outputdt': timedelta(minutes=output_minutes),
            'dt': timedelta(minutes=dt_minutes),
        }

        settings['plastictype'] = {
            'wind_coefficient': 0.0,
            'plastic_diameter': 0.001,
            'plastic_density': 1028.0,
        }

        # Create fieldset
        fieldset = create_hydrodynamic_fieldset(settings)

        # Create particle set
        pset = create_particleset(fieldset, settings, release_locations)

        # Create temporary output file
        with tempfile.NamedTemporaryFile(suffix='.zarr', delete=False) as tmp_file:
            output_file = tmp_file.name

        # Remove the temporary file (we just need the name)
        os.unlink(output_file)

        # Run simulation
        pset.execute(
            parcels.AdvectionRK4,
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
        "dt_minutes": 5 (optional, default 5)
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

        # Validate parameters
        if simulation_hours <= 0 or simulation_hours > 720:  # Max 30 days
            return jsonify({"error": "simulation_hours must be between 1 and 720"}), 400

        if output_minutes <= 0 or output_minutes > 1440:  # Max 1 day
            return jsonify({"error": "output_minutes must be between 1 and 1440"}), 400

        if dt_minutes <= 0 or dt_minutes > 60:  # Max 1 hour
            return jsonify({"error": "dt_minutes must be between 1 and 60"}), 400

        # Run simulation
        output_file = run_trajectory_simulation(
            release_locations,
            simulation_hours,
            output_minutes,
            dt_minutes
        )

        # Convert to GeoJSON
        geojson = zarr_to_geojson(output_file)

        # Clean up temporary file
        if os.path.exists(output_file):
            shutil.rmtree(output_file)

        return jsonify(geojson)

    except Exception as e:
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

def initialize_server(data_dir):
    """Initialize the server with Mobile Bay data."""
    global DATA_DIR, SETTINGS

    if not os.path.exists(data_dir):
        raise FileNotFoundError(f"Data directory not found: {data_dir}")

    # Load settings
    SETTINGS = load_mobile_bay_settings(data_dir)
    DATA_DIR = data_dir

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
