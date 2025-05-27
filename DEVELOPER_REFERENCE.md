# PlasticParcels Animated Trajectory System - Developer Reference

## Architecture Overview

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  HTTP Server    │    │   API Server    │
│                 │    │   (Port 8080)   │    │   (Port 5000)   │
│ trajectory_map  │◄──►│                 │    │                 │
│     .html       │    │ Static Files    │    │ PlasticParcels  │
│                 │    │                 │    │   Simulation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         └──────────────── API Calls ──────────────────┘
```

### Technology Stack

**Backend:**
- **Python 3.11**: Runtime environment
- **Flask**: Web framework for REST API
- **PlasticParcels**: Ocean particle simulation
- **NumPy/XArray**: Data processing
- **CORS**: Cross-origin resource sharing

**Frontend:**
- **HTML5/CSS3**: User interface structure and styling
- **JavaScript ES6+**: Client-side logic and animations
- **Leaflet.js**: Interactive mapping library
- **Fetch API**: HTTP client for API communication

**Data:**
- **SCHISM**: Ocean model output
- **GeoJSON**: Trajectory data format
- **Zarr**: Temporary simulation storage

## API Server Implementation

### Core Functions

#### 1. Simulation Engine
```python
def run_trajectory_simulation(release_locations, simulation_hours=72, 
                            output_minutes=30, dt_minutes=5):
    """
    Execute PlasticParcels simulation with given parameters.
    
    Args:
        release_locations: Dict with 'lons', 'lats', 'plastic_amount'
        simulation_hours: Duration of simulation (1-720)
        output_minutes: Output frequency (1-1440)
        dt_minutes: Time step (1-60)
    
    Returns:
        str: Path to output zarr file
    """
```

#### 2. Data Conversion
```python
def zarr_to_geojson(zarr_file):
    """
    Convert zarr trajectory output to GeoJSON format.
    
    Args:
        zarr_file: Path to zarr trajectory file
    
    Returns:
        dict: GeoJSON FeatureCollection
    """
```

#### 3. Settings Management
```python
def load_mobile_bay_settings(data_dir):
    """
    Load and validate Mobile Bay configuration.
    
    Args:
        data_dir: Path to data directory
    
    Returns:
        dict: PlasticParcels settings
    """
```

### Flask Route Handlers

#### Root Endpoint
```python
@app.route('/', methods=['GET'])
def root():
    """API information and available endpoints."""
    return jsonify({
        "name": "PlasticParcels API Server",
        "version": "1.0.0",
        "endpoints": {...},
        "status": "running"
    })
```

#### Simulation Endpoint
```python
@app.route('/simulate', methods=['POST'])
def simulate_trajectories():
    """
    Main simulation endpoint.
    
    Request validation:
    - Check required fields
    - Validate coordinate arrays
    - Verify parameter ranges
    
    Response:
    - GeoJSON FeatureCollection
    - Error messages with appropriate HTTP codes
    """
```

### Error Handling

```python
# Parameter validation
if simulation_hours <= 0 or simulation_hours > 720:
    return jsonify({"error": "simulation_hours must be between 1 and 720"}), 400

# Simulation error handling
try:
    output_file = run_trajectory_simulation(...)
    geojson = zarr_to_geojson(output_file)
    return jsonify(geojson)
except Exception as e:
    return jsonify({"error": str(e)}), 500
finally:
    # Cleanup temporary files
    if os.path.exists(output_file):
        shutil.rmtree(output_file)
```

## Frontend Implementation

### Animation System Architecture

#### Core Animation Loop
```javascript
// Animation state management
const animation = {
    particle: L.marker(),           // Moving particle marker
    trail: L.polyline(),           // Path visualization
    startMarker: L.marker(),       // Release point
    endMarker: null,               // Destination marker
    currentIndex: 0,               // Current position index
    intervalId: null,              // Animation timer
    isActive: true                 // Animation state
};

// Main animation loop
animation.intervalId = setInterval(() => {
    // Update particle position
    animation.particle.setLatLng(currentPosition);
    
    // Update trail if enabled
    if (showTrail) {
        animation.trail.setLatLngs(pathPoints);
    }
    
    // Update progress indicator
    updateProgress(currentIndex, totalPoints);
}, animationSpeed);
```

#### Particle Management
```javascript
// Create animated particle
const particle = L.marker(startPosition, {
    icon: L.divIcon({
        className: 'animated-particle',
        html: `<div style="background: ${color}; ..."></div>`,
        iconSize: [8, 8]
    })
});

// Trail visualization
const trail = L.polyline([], {
    color: color,
    weight: 3,
    opacity: showTrail ? 0.7 : 0,
    className: 'particle-trail'
});
```

### Event Handling

#### Right-Click Context Menu
```javascript
// Disable default context menu
map.getContainer().addEventListener('contextmenu', function(e) {
    e.preventDefault();
});

// Custom context menu
map.on('contextmenu', function(e) {
    rightClickLatLng = e.latlng;
    showContextMenu(e);
});

// Menu creation
function showContextMenu(e) {
    const contextMenu = document.createElement('div');
    contextMenu.className = 'context-menu';
    contextMenu.innerHTML = `
        <div class="context-menu-item" onclick="simulateTrajectory()">
            🌊 Simulate Trajectory Here
        </div>
    `;
    // Position and display menu
}
```

#### API Communication
```javascript
async function simulateTrajectory() {
    const requestData = {
        release_locations: {
            lons: [lng],
            lats: [lat]
        },
        simulation_hours: simDuration,
        output_minutes: outputFreq,
        dt_minutes: 5
    };
    
    const response = await fetch(`${apiUrl}/simulate`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(requestData)
    });
    
    if (!response.ok) {
        const error = await response.json();
        throw new Error(error.error);
    }
    
    const geojson = await response.json();
    plotTrajectory(geojson.features[0]);
}
```

### CSS Animations

#### Particle Styling
```css
.animated-particle {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    position: absolute;
    z-index: 1000;
    box-shadow: 0 0 6px rgba(0,0,0,0.5);
    transition: all 0.2s ease-in-out;
}
```

#### Trail Animation
```css
.particle-trail {
    stroke-dasharray: 5,5;
    animation: dash 1s linear infinite;
}

@keyframes dash {
    to {
        stroke-dashoffset: -10;
    }
}
```

## Data Structures

### API Request Format
```typescript
interface SimulationRequest {
    release_locations: {
        lons: number[];
        lats: number[];
        plastic_amount?: number[];
    };
    simulation_hours?: number;    // 1-720
    output_minutes?: number;      // 1-1440
    dt_minutes?: number;          // 1-60
}
```

### GeoJSON Response Format
```typescript
interface TrajectoryResponse {
    type: "FeatureCollection";
    features: Array<{
        type: "Feature";
        properties: {
            particle_id: number;
            trajectory_length: number;
        };
        geometry: {
            type: "LineString";
            coordinates: Array<[number, number]>; // [lon, lat]
        };
    }>;
}
```

### Animation State
```typescript
interface AnimationState {
    particle: L.Marker;
    trail: L.Polyline;
    startMarker: L.Marker;
    endMarker: L.Marker | null;
    color: string;
    points: number;
    feature: GeoJSONFeature;
    isActive: boolean;
    currentIndex: number;
    intervalId: number | null;
}
```

## Configuration Management

### API Server Configuration
```python
# Global configuration variables
DATA_DIR = None          # Data directory path
SETTINGS = None          # PlasticParcels settings

# Server initialization
def initialize_server(data_dir):
    global DATA_DIR, SETTINGS
    SETTINGS = load_mobile_bay_settings(data_dir)
    DATA_DIR = data_dir
```

### Frontend Configuration
```javascript
// Animation settings
const animationSpeed = parseInt(document.getElementById('animationSpeed').value);
const showTrail = document.getElementById('showTrail').value === 'true';
const apiUrl = document.getElementById('apiUrl').value;

// Color palette for trajectories
const colors = [
    '#e74c3c', '#3498db', '#2ecc71', '#f39c12',
    '#9b59b6', '#1abc9c', '#e67e22', '#34495e'
];
```

## Performance Optimization

### Backend Optimizations
```python
# Efficient data processing
import copy
settings = copy.deepcopy(SETTINGS)  # Avoid mutation

# Temporary file management
with tempfile.NamedTemporaryFile(suffix='.zarr', delete=False) as tmp_file:
    output_file = tmp_file.name

# Cleanup
try:
    # Simulation code
finally:
    if os.path.exists(output_file):
        shutil.rmtree(output_file)
```

### Frontend Optimizations
```javascript
// Efficient animation management
function clearAllTrajectories() {
    // Stop all intervals
    activeAnimations.forEach(animation => {
        if (animation.intervalId) {
            clearInterval(animation.intervalId);
        }
    });
    
    // Remove DOM elements
    trajectories.forEach(traj => {
        if (traj.particle) map.removeLayer(traj.particle);
        if (traj.trail) map.removeLayer(traj.trail);
    });
    
    // Clear arrays
    trajectories = [];
    activeAnimations = [];
}
```

## Testing Framework

### API Testing
```python
def test_simulation_endpoint():
    """Test the simulation endpoint with valid data."""
    test_data = {
        "release_locations": {
            "lons": [-88.939115],
            "lats": [30.357525]
        },
        "simulation_hours": 6
    }
    
    response = requests.post(f"{base_url}/simulate", json=test_data)
    assert response.status_code == 200
    
    geojson = response.json()
    assert geojson["type"] == "FeatureCollection"
    assert len(geojson["features"]) > 0
```

### Frontend Testing
```javascript
// Test animation creation
function testAnimationCreation() {
    const mockFeature = {
        geometry: {
            coordinates: [[-88.939, 30.357], [-88.940, 30.358]]
        },
        properties: {
            particle_id: 0,
            trajectory_length: 2
        }
    };
    
    plotTrajectory(mockFeature, mockReleaseMarker);
    
    // Verify animation was created
    assert(trajectories.length === 1);
    assert(activeAnimations.length === 1);
}
```

## Deployment Considerations

### Production Deployment
```python
# Use production WSGI server
# gunicorn --bind 0.0.0.0:5000 plasticparcels_api_server:app

# Environment variables
import os
API_HOST = os.getenv('API_HOST', '127.0.0.1')
API_PORT = int(os.getenv('API_PORT', 5000))
DATA_DIR = os.getenv('DATA_DIR', 'plasticparcels/mobile_schism_output')
```

### Security Considerations
```python
# Input validation
def validate_coordinates(lons, lats):
    """Validate coordinate arrays."""
    if not isinstance(lons, list) or not isinstance(lats, list):
        raise ValueError("Coordinates must be arrays")
    
    if len(lons) != len(lats):
        raise ValueError("Longitude and latitude arrays must have same length")
    
    # Check bounds
    for lon, lat in zip(lons, lats):
        if not (-180 <= lon <= 180) or not (-90 <= lat <= 90):
            raise ValueError("Invalid coordinates")

# Rate limiting (if needed)
from flask_limiter import Limiter
limiter = Limiter(app, key_func=get_remote_address)

@app.route('/simulate', methods=['POST'])
@limiter.limit("10 per minute")
def simulate_trajectories():
    # Simulation code
```

### Monitoring and Logging
```python
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Log simulation requests
@app.route('/simulate', methods=['POST'])
def simulate_trajectories():
    logger.info(f"Simulation request from {request.remote_addr}")
    # Simulation code
    logger.info(f"Simulation completed in {elapsed_time:.2f}s")
```

## Extension Points

### Custom Visualization
```javascript
// Add custom particle types
function createCustomParticle(type, color, position) {
    const icons = {
        'plastic': '🟡',
        'oil': '⚫',
        'debris': '🟤'
    };
    
    return L.marker(position, {
        icon: L.divIcon({
            html: icons[type],
            className: 'custom-particle'
        })
    });
}
```

### Additional API Endpoints
```python
@app.route('/batch_simulate', methods=['POST'])
def batch_simulate():
    """Process multiple simulations in parallel."""
    # Implementation for batch processing

@app.route('/export/<format>', methods=['POST'])
def export_trajectories(format):
    """Export trajectories in different formats."""
    # Support for CSV, KML, Shapefile export
```

This developer reference provides the technical foundation for understanding, modifying, and extending the PlasticParcels Animated Trajectory System.
