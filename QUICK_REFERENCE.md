# PlasticParcels Animated Trajectory System - Quick Reference

## 🚀 Quick Start

### Start Servers
```bash
# Terminal 1: API Server
conda activate plasticparcels-test
cd /mnt/raid5/sbao/plastics
python plasticparcels_api_server.py plasticparcels/mobile_schism_output

# Terminal 2: Web Server
cd /mnt/raid5/sbao/plastics
python -m http.server 8080
```

### Access URLs
- **Web Interface**: `http://localhost:8080/trajectory_map.html`
- **API Health**: `http://localhost:5000/health`
- **File Browser**: `http://localhost:8080/`

### Port Forwarding (HPC)
```bash
ssh -L 5000:localhost:5000 -L 8080:localhost:8080 username@hpc-hostname
```

## 🎮 Basic Usage

### Simulate Trajectory
1. **Right-click** on map
2. **Select** "Simulate Trajectory Here"
3. **Watch** animated particle movement

### Animation Controls
- **Speed**: Very Fast → Very Slow
- **Trail**: Show/Hide particle path
- **Pause/Resume**: Control all animations
- **Clear All**: Remove all trajectories

## ⚙️ Settings Guide

### Recommended Settings

**Quick Analysis:**
- Duration: 6-12 hours
- Output: Every hour
- Speed: Fast (100ms)
- Trail: Hidden

**Detailed Study:**
- Duration: 24-48 hours
- Output: Every 30 minutes
- Speed: Normal (200ms)
- Trail: Visible

**Presentation:**
- Duration: 24 hours
- Output: Every 15 minutes
- Speed: Slow (500ms)
- Trail: Visible

## 🔧 API Reference

### Health Check
```bash
curl http://localhost:5000/health
```

### Simulate Trajectory
```bash
curl -X POST http://localhost:5000/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "release_locations": {
      "lons": [-88.939115],
      "lats": [30.357525]
    },
    "simulation_hours": 24
  }'
```

### Python Client
```python
import requests

response = requests.post('http://localhost:5000/simulate', json={
    'release_locations': {
        'lons': [-88.939115, -88.940000],
        'lats': [30.357525, 30.358000]
    },
    'simulation_hours': 48,
    'output_minutes': 30
})

geojson = response.json()
```

## 🎯 Best Locations to Test

### Mobile Bay Coordinates
- **Bay Entrance**: -87.97°E, 30.25°N
- **Main Channel**: -88.04°E, 30.35°N
- **Upper Bay**: -88.0°E, 30.5°N
- **River Mouth**: -88.1°E, 30.6°N
- **Coastal Area**: -88.2°E, 30.4°N

### Interesting Patterns
- **Tidal oscillation**: Near bay entrance
- **River influence**: Upper bay areas
- **Coastal retention**: Shallow water zones
- **Current convergence**: Channel intersections

## 🐛 Troubleshooting

### Common Issues

**Connection Failed**
```bash
# Check API server
curl http://localhost:5000/health

# Check web server
curl http://localhost:8080/

# Restart if needed
python plasticparcels_api_server.py plasticparcels/mobile_schism_output
python -m http.server 8080
```

**Animation Problems**
- **Too fast/slow**: Adjust speed in settings
- **No trail**: Enable "Show Trail"
- **Freezes**: Pause/Resume or refresh page
- **Multiple confusing**: Use "Clear All"

**Simulation Errors**
- **Outside domain**: Click in Mobile Bay water areas
- **Invalid parameters**: Check duration/frequency settings
- **Server error**: Check terminal output for errors

### Status Check
```bash
# Quick system test
python check_api_status.py

# Test with example client
python api_client_example.py --test
```

## 📊 Parameter Ranges

### Simulation Parameters
- **Duration**: 1-720 hours (1 hour to 30 days)
- **Output Frequency**: 1-1440 minutes (1 minute to 1 day)
- **Time Step**: 1-60 minutes (1 minute to 1 hour)

### Animation Settings
- **Speed**: 50-1000ms intervals
- **Trail**: Show/Hide toggle
- **Colors**: 12 predefined colors cycle

### Domain Bounds
- **Longitude**: -89.124°E to -87.964°E
- **Latitude**: 30.017°N to 30.617°N
- **Coverage**: Mobile Bay, Alabama

## 📁 File Structure

```
plasticparcels/
├── trajectory_map.html          # 🎬 Animated web interface
├── plasticparcels_api_server.py # 🖥️ API server
├── check_api_status.py          # 🔍 Status checker
├── api_client_example.py        # 🐍 Python examples
├── demo.html                    # 📊 Original demo
├── ANIMATION_DOCUMENTATION.md   # 📚 Full documentation
├── USER_GUIDE.md               # 👤 User instructions
├── DEVELOPER_REFERENCE.md      # 🔧 Technical reference
├── QUICK_REFERENCE.md          # ⚡ This file
└── plasticparcels/
    └── mobile_schism_output/    # 📁 Data directory
```

## 🎨 Visual Elements

### Map Markers
- 🔴 **Red dot**: Release point
- 🟡 **Colored particle**: Moving plastic
- ➖ **Dashed line**: Particle trail
- 🔺 **Arrow**: Final position

### Status Colors
- 🟢 **Green**: Success/Connected
- 🟡 **Yellow**: Loading/In progress
- 🔴 **Red**: Error/Failed
- 🔵 **Blue**: Information

## 💡 Pro Tips

### Performance
- **Limit trajectories**: Max 3-5 concurrent animations
- **Use appropriate speed**: Normal (200ms) for most cases
- **Clear regularly**: Remove completed trajectories
- **Refresh if slow**: Browser performance degrades over time

### Analysis
- **Compare locations**: Multiple release points
- **Vary durations**: Short vs long simulations
- **Study patterns**: Tidal cycles, current flows
- **Document results**: Screenshots, notes

### Presentation
- **Slower speeds**: Better for audiences
- **Enable trails**: Visual impact
- **Prepare locations**: Interesting release points
- **Explain context**: What viewers are seeing

## 🔗 Useful Commands

### Server Management
```bash
# Check if servers are running
ps aux | grep python

# Kill servers if needed
pkill -f plasticparcels_api_server
pkill -f "http.server"

# Monitor server logs
tail -f /path/to/logfile
```

### Testing
```bash
# Quick API test
curl -s http://localhost:5000/health | python -m json.tool

# Full system test
python check_api_status.py

# Custom simulation test
python api_client_example.py --custom --lons -88.939 --lats 30.357 --hours 12
```

### Data Export
```bash
# Save GeoJSON from web interface (automatic)
# Files saved as: trajectory_output.geojson, custom_trajectory_*.geojson

# Manual API call with output
curl -X POST http://localhost:5000/simulate \
  -H "Content-Type: application/json" \
  -d '{"release_locations":{"lons":[-88.939],"lats":[30.357]},"simulation_hours":24}' \
  > my_trajectory.geojson
```

## 📞 Support

### Documentation
- **Full docs**: `ANIMATION_DOCUMENTATION.md`
- **User guide**: `USER_GUIDE.md`
- **Developer ref**: `DEVELOPER_REFERENCE.md`
- **API docs**: `API_README.md`

### Testing Tools
- **Status check**: `python check_api_status.py`
- **Client examples**: `python api_client_example.py --help`
- **Browser console**: F12 → Console (for JavaScript errors)

### Common Solutions
1. **Refresh the page** - Fixes most UI issues
2. **Check server status** - Use health endpoints
3. **Verify coordinates** - Must be in Mobile Bay
4. **Clear animations** - Use "Clear All" button
5. **Restart servers** - Last resort for persistent issues

---

**Remember**: Right-click anywhere on the map to start simulating! 🌊✨
