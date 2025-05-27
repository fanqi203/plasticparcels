# PlasticParcels Animated Trajectory System

A comprehensive web-based platform for simulating and visualizing plastic particle movement in marine environments. The system combines a REST API backend with an interactive web frontend featuring **real-time trajectory animations**.

## 🎬 New: Animated Trajectories!

**Watch plastic particles move in real-time!** The system now features smooth animations where particles travel step-by-step along their calculated paths, making it easy to understand ocean current patterns and plastic transport dynamics.

### Key Features
- 🌊 **Real-time particle animations** with configurable speed
- 🗺️ **Interactive map interface** with right-click simulation
- ⚙️ **Configurable settings** for duration, frequency, and visualization
- 🎨 **Multiple particle support** with color-coded trajectories
- ⏸️ **Animation controls** (pause, resume, clear)
- 📊 **Progress tracking** and status updates

## Features

- 🌊 **Trajectory Simulation**: Run PlasticParcels simulations with custom release locations
- 📍 **GeoJSON Output**: Get trajectory results in standard GeoJSON format
- ⚙️ **Configurable Parameters**: Adjust simulation duration, time steps, and output frequency
- 🔍 **Dataset Information**: Query domain bounds and grid information
- 🏥 **Health Monitoring**: Built-in health check endpoint

## Installation

### Prerequisites

1. **Conda Environment with PlasticParcels**:
   ```bash
   conda create -n plasticparcels-test python=3.11 -y
   conda activate plasticparcels-test
   conda install conda-forge::plasticparcels -y
   ```

2. **Additional Dependencies**:
   ```bash
   pip install flask flask-cors requests
   ```

### Mobile Bay Data

You need Mobile Bay SCHISM data converted to PlasticParcels format. If you have the converted data in a directory (e.g., `mobile_schism_output`), you're ready to go.

## 🎮 Quick Start - Animated Interface

### 1. Start the System
```bash
# Terminal 1: API Server
conda activate plasticparcels-test
python plasticparcels_api_server.py plasticparcels/mobile_schism_output

# Terminal 2: Web Server
python -m http.server 8080
```

### 2. Access the Animated Interface
Open your browser to: `http://localhost:8080/trajectory_map.html`

### 3. Simulate Trajectories
1. **Right-click** anywhere on the Mobile Bay map
2. **Select "Simulate Trajectory Here"**
3. **Watch** the animated particle move along its path!

### 4. Customize Animation
- **Speed**: Adjust from very fast (50ms) to very slow (1s)
- **Trail**: Show/hide the particle's path
- **Duration**: From 6 hours to 1 week
- **Multiple particles**: Right-click in different locations

## 📚 Documentation

- **[User Guide](USER_GUIDE.md)**: Complete instructions for using the animated interface
- **[Developer Reference](DEVELOPER_REFERENCE.md)**: Technical implementation details
- **[Quick Reference](QUICK_REFERENCE.md)**: Common tasks and troubleshooting
- **[Animation Documentation](ANIMATION_DOCUMENTATION.md)**: Full system documentation

## Usage

### Starting the Server

```bash
# Activate the environment
conda activate plasticparcels-test

# Start the server with your data directory
python plasticparcels_api_server.py mobile_schism_output

# Optional: specify host and port
python plasticparcels_api_server.py mobile_schism_output --host 0.0.0.0 --port 8080
```

The server will start on `http://127.0.0.1:5000` by default.

### API Endpoints

#### 1. Health Check
```bash
GET /health
```

Returns server status and configuration:
```json
{
  "status": "healthy",
  "data_dir": "mobile_schism_output",
  "settings_loaded": true
}
```

#### 2. Dataset Information
```bash
GET /info
```

Returns information about the loaded dataset:
```json
{
  "domain": {
    "lon_min": -88.95,
    "lon_max": -88.92,
    "lat_min": 30.35,
    "lat_max": 30.38
  },
  "grid_shape": [100, 150],
  "time_steps": 144,
  "time_range": {
    "start": 0.0,
    "end": 143.0
  }
}
```

#### 3. Simulate Trajectories
```bash
POST /simulate
```

**Request Body**:
```json
{
  "release_locations": {
    "lons": [-88.939115, -88.940000],
    "lats": [30.357525, 30.358000],
    "plastic_amount": [1.0, 1.0]
  },
  "simulation_hours": 72,
  "output_minutes": 30,
  "dt_minutes": 5
}
```

**Parameters**:
- `release_locations` (required): Object with `lons`, `lats`, and optional `plastic_amount` arrays
- `simulation_hours` (optional): Duration in hours (1-720, default: 72)
- `output_minutes` (optional): Output frequency in minutes (1-1440, default: 30)
- `dt_minutes` (optional): Time step in minutes (1-60, default: 5)

**Response**: GeoJSON FeatureCollection with trajectory LineStrings:
```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "particle_id": 0,
        "trajectory_length": 145
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-88.939115, 30.357525],
          [-88.939120, 30.357530],
          ...
        ]
      }
    }
  ]
}
```

## Client Examples

### Python Client

Use the provided client example:

```bash
# Test the API
python api_client_example.py --test

# Run custom simulation
python api_client_example.py --custom \
  --lons -88.939115 -88.940000 \
  --lats 30.357525 30.358000 \
  --hours 48
```

### cURL Examples

```bash
# Health check
curl http://127.0.0.1:5000/health

# Get dataset info
curl http://127.0.0.1:5000/info

# Run simulation
curl -X POST http://127.0.0.1:5000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "release_locations": {
      "lons": [-88.939115],
      "lats": [30.357525]
    },
    "simulation_hours": 24
  }'
```

### JavaScript/Fetch Example

```javascript
// Run simulation
const response = await fetch('http://127.0.0.1:5000/simulate', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    release_locations: {
      lons: [-88.939115, -88.940000],
      lats: [30.357525, 30.358000]
    },
    simulation_hours: 72,
    output_minutes: 60
  })
});

const geojson = await response.json();
console.log('Trajectories:', geojson);
```

## Output Format

The API returns trajectories in standard GeoJSON format:

- **Type**: FeatureCollection
- **Features**: Each feature represents one particle trajectory
- **Geometry**: LineString with coordinate pairs [longitude, latitude]
- **Properties**:
  - `particle_id`: Unique identifier for the particle
  - `trajectory_length`: Number of points in the trajectory

This format is compatible with:
- 🗺️ **Mapping libraries**: Leaflet, Mapbox, OpenLayers
- 📊 **GIS software**: QGIS, ArcGIS
- 🐍 **Python**: GeoPandas, Folium
- 🌐 **Web applications**: Any GeoJSON-compatible viewer

## Error Handling

The API returns appropriate HTTP status codes:

- `200`: Success
- `400`: Bad request (invalid parameters)
- `500`: Server error (simulation failed)

Error responses include descriptive messages:
```json
{
  "error": "simulation_hours must be between 1 and 720"
}
```

## Performance Notes

- **Simulation time** scales with number of particles and simulation duration
- **Memory usage** depends on output frequency and trajectory length
- **Temporary files** are automatically cleaned up after each simulation
- Consider using shorter simulations for real-time applications

## Troubleshooting

1. **Server won't start**: Check that the data directory exists and contains `settings.json`
2. **Simulation fails**: Verify release locations are within the domain bounds
3. **Import errors**: Ensure PlasticParcels is properly installed in the conda environment
4. **Memory issues**: Reduce simulation duration or output frequency

## Development

To extend the API:

1. **Add new endpoints** in `plasticparcels_api_server.py`
2. **Modify simulation parameters** in the `run_trajectory_simulation` function
3. **Customize output format** in the `zarr_to_geojson` function
4. **Add validation** for new parameters in the request handlers
