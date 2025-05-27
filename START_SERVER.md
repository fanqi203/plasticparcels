# 🚀 PlasticParcels API Server - Quick Start Guide

## Current Status: ✅ RUNNING

The PlasticParcels API server is currently **RUNNING** and ready to accept requests!

- **Server URL**: http://127.0.0.1:5000
- **Status**: Healthy and functional
- **Data**: Mobile Bay SCHISM output
- **Domain**: -89.124°E to -87.964°E, 30.017°N to 30.617°N

## Quick Test

```bash
# Check if server is running
python check_api_status.py

# Test with curl
curl http://127.0.0.1:5000/health
```

## If You Need to Restart the Server

### 1. Stop Current Server
If the server is running, stop it with `Ctrl+C` in the terminal.

### 2. Start Server
```bash
# Activate conda environment
conda activate plasticparcels-test

# Navigate to project directory
cd /mnt/raid5/sbao/plastics

# Start the server
python plasticparcels_api_server.py plasticparcels/mobile_schism_output
```

### 3. Optional: Custom Host/Port
```bash
# Run on different port
python plasticparcels_api_server.py plasticparcels/mobile_schism_output --port 8080

# Run on all interfaces (accessible from other machines)
python plasticparcels_api_server.py plasticparcels/mobile_schism_output --host 0.0.0.0 --port 5000
```

## Usage Examples

### Python Client
```bash
# Run basic tests
python api_client_example.py --test

# Custom simulation
python api_client_example.py --custom \
  --lons -88.939115 -88.940000 \
  --lats 30.357525 30.358000 \
  --hours 24
```

### cURL Commands
```bash
# Health check
curl http://127.0.0.1:5000/health

# Dataset info
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

### Web Demo
Open `demo.html` in your browser for an interactive map interface.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Server health check |
| `/info` | GET | Dataset information |
| `/simulate` | POST | Run trajectory simulation |

## Simulation Parameters

```json
{
  "release_locations": {
    "lons": [longitude1, longitude2, ...],
    "lats": [latitude1, latitude2, ...],
    "plastic_amount": [amount1, amount2, ...] // optional
  },
  "simulation_hours": 72,    // 1-720 hours
  "output_minutes": 30,      // 1-1440 minutes  
  "dt_minutes": 5            // 1-60 minutes
}
```

## Output Format

Returns GeoJSON FeatureCollection with trajectory LineStrings:

```json
{
  "type": "FeatureCollection",
  "features": [
    {
      "type": "Feature",
      "properties": {
        "particle_id": 0,
        "trajectory_length": 24
      },
      "geometry": {
        "type": "LineString",
        "coordinates": [
          [-88.939115, 30.357525],
          [-88.962018, 30.343197],
          ...
        ]
      }
    }
  ]
}
```

## Files Overview

- **`plasticparcels_api_server.py`** - Main API server
- **`api_client_example.py`** - Python client examples
- **`check_api_status.py`** - Server status checker
- **`demo.html`** - Interactive web demo
- **`API_README.md`** - Complete documentation
- **Generated GeoJSON files** - Simulation results

## Troubleshooting

### Server Won't Start
```bash
# Check conda environment
conda activate plasticparcels-test
conda list | grep plastic

# Check data directory
ls plasticparcels/mobile_schism_output/settings.json
```

### Connection Errors
```bash
# Check if server is running
python check_api_status.py

# Check port availability
netstat -an | grep 5000
```

### Simulation Errors
- Verify release locations are within domain bounds (-89.124°E to -87.964°E, 30.017°N to 30.617°N)
- Check simulation parameters are within valid ranges
- Ensure sufficient disk space for temporary files

## Success! 🎉

Your PlasticParcels API server is fully functional and ready to generate plastic trajectory simulations in GeoJSON format!
