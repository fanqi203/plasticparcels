# PlasticParcels Animated Trajectory System - User Guide

## Getting Started

### Accessing the System

1. **Open your web browser** and navigate to:
   ```
   http://localhost:8080/trajectory_map.html
   ```

2. **Verify connection** - You should see:
   - 🟢 "Connected to PlasticParcels API Server" in the status panel
   - Interactive map centered on Mobile Bay
   - Settings panel on the left side

3. **If connection fails**:
   - Check that both servers are running (API on port 5000, web on port 8080)
   - Verify port forwarding if using HPC
   - Refresh the page

## Basic Usage

### Simulating Your First Trajectory

1. **Right-click anywhere on the map** (preferably in water areas)
2. **Select "Simulate Trajectory Here"** from the context menu
3. **Watch the animation**:
   - Red dot appears (release point)
   - Colored particle starts moving
   - Trail draws behind the particle (if enabled)
   - Progress updates in status panel
   - Arrow appears when complete

### Understanding the Animation

**Visual Elements:**
- 🔴 **Red dot**: Release point where plastic enters the water
- 🟡 **Moving particle**: Current position of the plastic particle
- ➖ **Dashed trail**: Path the particle has traveled
- 🔺 **Arrow marker**: Final position when simulation completes

**Status Updates:**
- "Simulating trajectory..." - API is calculating the path
- "Animating trajectory... X% complete" - Animation in progress
- "Animation completed!" - Simulation finished

## Advanced Features

### Animation Controls

#### Speed Settings
- **Very Fast (50ms)**: Quick overview, good for long trajectories
- **Fast (100ms)**: Rapid visualization
- **Normal (200ms)**: ⭐ **Recommended** - balanced speed
- **Slow (500ms)**: Detailed observation
- **Very Slow (1s)**: Frame-by-frame analysis

#### Trail Display
- **Show Trail**: ✅ **Default** - See complete path as it develops
- **Hide Trail**: Focus only on moving particle, cleaner view

#### Animation Control Buttons
- **Pause All**: Freeze all active animations
- **Resume All**: Continue paused animations
- **Clear All**: Remove all trajectories and stop animations

### Simulation Settings

#### Duration Options
- **6 hours**: Quick local movement patterns
- **12 hours**: Tidal cycle effects
- **24 hours**: ⭐ **Recommended** - Full day cycle
- **48 hours**: Multi-day patterns
- **72 hours**: Extended drift patterns
- **1 week**: Long-term transport

#### Output Frequency
- **Every 15 minutes**: High detail, slower animation
- **Every 30 minutes**: ⭐ **Recommended** - Good balance
- **Every hour**: Faster animation, less detail
- **Every 2 hours**: Quick overview

## Multiple Trajectory Comparison

### Comparing Different Locations

1. **Right-click in first location** → Simulate
2. **Right-click in second location** → Simulate
3. **Each trajectory gets a different color**
4. **Compare movement patterns**:
   - Different starting points
   - Varying drift directions
   - Speed differences
   - Final destinations

### Analyzing Results

**Look for:**
- **Current patterns**: How particles follow water flow
- **Tidal effects**: Back-and-forth movement
- **Convergence zones**: Where particles collect
- **Divergence areas**: Where particles spread out
- **Coastal interactions**: How shorelines affect movement

## Best Practices

### Optimal Simulation Settings

**For Quick Analysis:**
- Duration: 6-12 hours
- Output: Every hour
- Speed: Fast (100ms)
- Trail: Hidden

**For Detailed Study:**
- Duration: 24-48 hours
- Output: Every 30 minutes
- Speed: Normal (200ms)
- Trail: Visible

**For Presentation:**
- Duration: 24 hours
- Output: Every 15 minutes
- Speed: Slow (500ms)
- Trail: Visible

### Strategic Release Locations

**Interesting Areas to Test:**

1. **River mouths**: See freshwater influence
2. **Bay entrance**: Observe tidal exchange
3. **Shallow areas**: Study coastal retention
4. **Deep channels**: Track main flow patterns
5. **Near islands**: Examine flow splitting
6. **Industrial areas**: Assess pollution transport

### Performance Tips

**For Smooth Animation:**
- Limit to 3-5 concurrent trajectories
- Use normal or fast speed settings
- Clear completed animations regularly
- Refresh browser if performance degrades

**For Detailed Analysis:**
- Use slower speeds for careful observation
- Enable trails to see complete paths
- Pause animations to examine specific moments
- Take screenshots for documentation

## Interpreting Results

### Understanding Particle Movement

**Normal Patterns:**
- **Tidal oscillation**: Back-and-forth movement
- **Net drift**: Overall direction over time
- **Coastal following**: Movement along shorelines
- **Eddy formation**: Circular motion patterns

**Environmental Factors:**
- **Wind effects**: Surface drift (if wind coefficient > 0)
- **Current strength**: Speed of particle movement
- **Bathymetry**: Depth effects on flow
- **Tidal stage**: High/low tide influences

### Scientific Applications

**Research Questions:**
- Where do particles released at different locations end up?
- How long do particles remain in the bay?
- Which areas act as particle traps?
- How do tidal cycles affect transport?
- What are the dominant flow patterns?

**Data Collection:**
- Screenshot key moments in animations
- Note final positions of particles
- Compare trajectories from different release points
- Document unusual or interesting patterns

## Troubleshooting

### Common Issues and Solutions

**Problem: Animation is too fast/slow**
- Solution: Adjust animation speed in settings panel

**Problem: Can't see the particle trail**
- Solution: Enable "Show Trail" in settings

**Problem: Animation freezes**
- Solution: Click "Pause All" then "Resume All", or refresh page

**Problem: Simulation fails**
- Solution: Check that release point is in water (within Mobile Bay domain)

**Problem: Multiple particles are confusing**
- Solution: Use "Clear All" to start fresh, or pause to examine

**Problem: Can't right-click on map**
- Solution: Ensure you're clicking on the map area, not the sidebar

### Error Messages

**"Cannot connect to API server"**
- Check that API server is running on port 5000
- Verify port forwarding setup
- Try refreshing the page

**"Simulation failed"**
- Release point may be outside valid domain
- Check simulation parameters are reasonable
- Try a different location

**"Not enough trajectory points"**
- Simulation duration may be too short
- Try increasing duration or decreasing output frequency

## Tips for Effective Use

### Educational Applications

**For Students:**
- Start with simple, short simulations
- Compare particles from different locations
- Discuss why particles move differently
- Relate to real-world pollution scenarios

**For Researchers:**
- Use consistent settings for comparative studies
- Document methodology and parameters
- Take systematic screenshots or recordings
- Validate results with field observations

### Presentation Tips

**For Demonstrations:**
- Use slower animation speeds
- Enable trails for visual impact
- Prepare interesting release locations
- Explain what viewers are seeing
- Pause at key moments for discussion

**For Documentation:**
- Screenshot key frames of animations
- Note simulation parameters used
- Describe observed patterns
- Compare multiple scenarios

## Advanced Usage

### Custom API Integration

If you want to integrate the API into your own applications:

```python
import requests

# Custom simulation
response = requests.post('http://localhost:5000/simulate', json={
    'release_locations': {
        'lons': [-88.939115, -88.940000],
        'lats': [30.357525, 30.358000]
    },
    'simulation_hours': 48,
    'output_minutes': 30
})

trajectories = response.json()
```

### Batch Processing

For multiple simulations:

```python
locations = [
    (-88.939115, 30.357525),
    (-88.940000, 30.358000),
    (-88.938000, 30.357000)
]

results = []
for lon, lat in locations:
    response = requests.post('http://localhost:5000/simulate', json={
        'release_locations': {'lons': [lon], 'lats': [lat]},
        'simulation_hours': 24
    })
    results.append(response.json())
```

## Support and Resources

### Documentation Files
- `ANIMATION_DOCUMENTATION.md`: Technical documentation
- `API_README.md`: API reference
- `START_SERVER.md`: Setup instructions
- `DEPLOYMENT_SUMMARY.md`: System overview

### Testing Tools
- `check_api_status.py`: Verify system health
- `api_client_example.py`: Python client examples
- Browser developer tools: Debug JavaScript issues

### Getting Help

**Check these first:**
1. Status panel for connection/error messages
2. Browser console (F12) for JavaScript errors
3. Server terminal output for API errors
4. This user guide for common solutions

**For technical issues:**
- Verify all servers are running
- Check port forwarding configuration
- Test API endpoints directly
- Review system requirements

Remember: The system is designed to be intuitive - right-click anywhere on the map and watch plastic particles come to life! 🌊
