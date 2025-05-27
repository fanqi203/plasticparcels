# PlasticParcels Animated Trajectory System - Documentation

## Overview

The PlasticParcels Animated Trajectory System is a comprehensive web-based platform for simulating and visualizing plastic particle movement in marine environments. The system combines a REST API backend with an interactive web frontend featuring real-time trajectory animations.

## System Architecture

### Components

1. **PlasticParcels API Server** (`plasticparcels_api_server.py`)
   - Flask-based REST API
   - Handles trajectory simulation requests
   - Returns GeoJSON formatted results
   - Manages Mobile Bay SCHISM data

2. **Interactive Web Interface** (`trajectory_map.html`)
   - Leaflet-based mapping interface
   - Right-click trajectory simulation
   - Real-time particle animations
   - Configurable visualization settings

3. **HTTP File Server** (Python built-in)
   - Serves static web files
   - Enables remote access via port forwarding

### Data Flow

```
User Right-Click → API Request → PlasticParcels Simulation → GeoJSON Response → Animation Rendering
```

## API Documentation

### Base URL
```
http://127.0.0.1:5000
```

### Endpoints

#### 1. Root Information
```http
GET /
```

**Response:**
```json
{
  "name": "PlasticParcels API Server",
  "version": "1.0.0",
  "description": "REST API for plastic trajectory simulations using PlasticParcels",
  "endpoints": {
    "health": "/health",
    "info": "/info",
    "simulate": "/simulate"
  },
  "data_dir": "plasticparcels/mobile_schism_output",
  "status": "running"
}
```

#### 2. Health Check
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "data_dir": "plasticparcels/mobile_schism_output",
  "settings_loaded": true
}
```

#### 3. Dataset Information
```http
GET /info
```

**Response:**
```json
{
  "domain": {
    "lon_min": -89.124,
    "lon_max": -87.964,
    "lat_min": 30.017,
    "lat_max": 30.617
  },
  "grid_shape": [61],
  "time_steps": 96,
  "time_range": {
    "start": 0.0,
    "end": 95.0
  },
  "data_directory": "plasticparcels/mobile_schism_output"
}
```

#### 4. Simulate Trajectory
```http
POST /simulate
```

**Request Body:**
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

**Parameters:**
- `release_locations` (required): Release point coordinates
  - `lons`: Array of longitude values
  - `lats`: Array of latitude values  
  - `plastic_amount`: Array of plastic amounts (optional, defaults to 1.0)
- `simulation_hours`: Duration in hours (1-720, default: 72)
- `output_minutes`: Output frequency in minutes (1-1440, default: 30)
- `dt_minutes`: Time step in minutes (1-60, default: 5)

**Response:**
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

### Error Handling

**Error Response Format:**
```json
{
  "error": "Description of the error"
}
```

**Common HTTP Status Codes:**
- `200`: Success
- `400`: Bad Request (invalid parameters)
- `404`: Not Found (invalid endpoint)
- `500`: Internal Server Error (simulation failed)

## Web Interface Documentation

### User Interface Components

#### 1. Map View
- **Base Map**: OpenStreetMap tiles
- **Zoom Controls**: Mouse wheel, +/- buttons
- **Pan**: Click and drag
- **Right-Click Menu**: Context menu for trajectory simulation

#### 2. Settings Panel

**Simulation Settings:**
- **Duration**: 6 hours to 1 week
- **Output Frequency**: 15 minutes to 2 hours
- **API Server URL**: Configurable endpoint

**Animation Settings:**
- **Speed**: 50ms to 1000ms intervals
- **Trail Display**: Show/hide particle path
- **Pause/Resume**: Control animation playback

#### 3. Status Panel
- **Connection Status**: API server connectivity
- **Simulation Progress**: Real-time updates
- **Error Messages**: User-friendly error reporting

#### 4. Trajectory List
- **Active Trajectories**: List of current simulations
- **Color Coding**: Visual identification
- **Point Counts**: Trajectory statistics

### Animation System

#### Particle Animation
```javascript
// Animation loop structure
setInterval(() => {
    // Update particle position
    particle.setLatLng(currentPosition);
    
    // Update trail if enabled
    if (showTrail) {
        trail.setLatLngs(pathPoints);
    }
    
    // Update progress indicator
    showProgress(currentIndex, totalPoints);
}, animationSpeed);
```

#### Visual Elements
- **Release Points**: Red circular markers
- **Animated Particles**: Colored moving dots with shadows
- **Trails**: Dashed lines showing particle path
- **End Markers**: Arrow indicators at trajectory completion

#### Animation Controls
- **Speed Control**: Adjustable timing intervals
- **Pause/Resume**: Global animation control
- **Trail Toggle**: Show/hide path visualization
- **Clear All**: Remove all trajectories and stop animations

## Installation and Setup

### Prerequisites
```bash
# Conda environment with PlasticParcels
conda create -n plasticparcels-test python=3.11 -y
conda activate plasticparcels-test
conda install conda-forge::plasticparcels -y

# Additional dependencies
pip install flask flask-cors requests
```

### Data Requirements
- Mobile Bay SCHISM data converted to PlasticParcels format
- `settings.json` configuration file
- Proper directory structure in `plasticparcels/mobile_schism_output/`

### Server Startup
```bash
# Start API server
python plasticparcels_api_server.py plasticparcels/mobile_schism_output

# Start file server (separate terminal)
python -m http.server 8080
```

### Port Forwarding (for HPC)
```bash
# Forward both API and web server ports
ssh -L 5000:localhost:5000 -L 8080:localhost:8080 username@hpc-hostname
```

### Access URLs
- **Web Interface**: `http://localhost:8080/trajectory_map.html`
- **API Server**: `http://localhost:5000`
- **Documentation**: `http://localhost:8080/`

## Usage Examples

### Basic Trajectory Simulation
1. Open web interface in browser
2. Right-click on Mobile Bay map
3. Select "Simulate Trajectory Here"
4. Watch animated particle movement
5. Adjust settings as needed

### Multiple Particle Comparison
1. Right-click in different locations
2. Each particle gets unique color
3. Compare movement patterns
4. Use pause/resume for detailed analysis

### API Integration
```python
import requests

# Simulate trajectory
response = requests.post('http://localhost:5000/simulate', json={
    'release_locations': {
        'lons': [-88.939115],
        'lats': [30.357525]
    },
    'simulation_hours': 24
})

geojson = response.json()
```

### JavaScript Integration
```javascript
// Fetch trajectory data
const response = await fetch('http://localhost:5000/simulate', {
    method: 'POST',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify({
        release_locations: {
            lons: [-88.939115],
            lats: [30.357525]
        },
        simulation_hours: 24
    })
});

const trajectories = await response.json();
```

## Performance Considerations

### Simulation Performance
- **Single particle, 6 hours**: ~1-2 seconds
- **Multiple particles, 24 hours**: ~3-5 seconds
- **Memory usage**: Minimal, temporary files auto-cleaned
- **Concurrent requests**: Supported with proper resource management

### Animation Performance
- **Optimal speed**: 100-500ms intervals
- **Browser performance**: Depends on trajectory length and number of particles
- **Memory management**: Automatic cleanup of completed animations

### Optimization Tips
- Use shorter simulations for real-time applications
- Reduce output frequency for longer simulations
- Limit concurrent animations for better performance
- Clear completed trajectories regularly

## Troubleshooting

### Common Issues

**1. API Connection Failed**
- Verify API server is running on port 5000
- Check firewall settings
- Confirm port forwarding setup

**2. Simulation Errors**
- Ensure release points are within domain bounds
- Verify simulation parameters are within valid ranges
- Check available disk space for temporary files

**3. Animation Issues**
- Refresh browser if animations freeze
- Clear browser cache for updated code
- Check browser console for JavaScript errors

**4. Performance Problems**
- Reduce animation speed for smoother playback
- Limit number of concurrent trajectories
- Use shorter simulation durations

### Debug Tools
```bash
# Check API status
curl http://localhost:5000/health

# Test simulation
python check_api_status.py

# Monitor server logs
# Check terminal output for error messages
```

## File Structure

```
plasticparcels/
├── plasticparcels_api_server.py      # Main API server
├── trajectory_map.html               # Animated web interface
├── demo.html                        # Original demo interface
├── api_client_example.py            # Python client examples
├── check_api_status.py              # Server testing script
├── test_api_server.py               # Function testing
├── API_README.md                    # API documentation
├── ANIMATION_DOCUMENTATION.md       # This file
├── START_SERVER.md                  # Quick start guide
├── DEPLOYMENT_SUMMARY.md            # Deployment overview
└── plasticparcels/
    └── mobile_schism_output/        # Data directory
        ├── settings.json            # Configuration
        └── [data files]             # SCHISM output
```

## Future Enhancements

### Planned Features
- **Real-time streaming**: WebSocket-based live updates
- **Batch processing**: Multiple simulations in parallel
- **Data export**: Download trajectories in various formats
- **Advanced visualization**: 3D trajectories, time-series plots
- **User authentication**: Secure access control
- **Result caching**: Improved performance for repeated simulations

### Integration Possibilities
- **Mobile applications**: React Native or Flutter apps
- **Desktop GIS**: QGIS plugins
- **Scientific workflows**: Jupyter notebook integration
- **Cloud deployment**: Docker containers, Kubernetes
- **Database storage**: Persistent trajectory storage
