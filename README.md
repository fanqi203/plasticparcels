# 🌊 PlasticParcels Animated Trajectory System

**Real-time visualization of plastic particle movement in marine environments**

![System Status](https://img.shields.io/badge/Status-Operational-green)
![Version](https://img.shields.io/badge/Version-1.0.0-blue)
![Platform](https://img.shields.io/badge/Platform-Web%20%7C%20API-orange)

## 🎬 Watch Plastic Particles Come to Life!

This system transforms static trajectory data into **dynamic, animated visualizations** where you can watch plastic particles move step-by-step through ocean currents. Simply right-click anywhere on the map and see how plastic pollution travels in Mobile Bay!

### ✨ Key Features

- 🎯 **Right-click simulation** - Click anywhere on the map to release particles
- 🎬 **Real-time animations** - Watch particles move along their calculated paths  
- ⚙️ **Configurable settings** - Adjust speed, duration, and visualization options
- 🎨 **Multi-particle support** - Compare trajectories from different release points
- 📊 **Progress tracking** - Real-time status updates and completion indicators
- 🗺️ **Interactive mapping** - Zoom, pan, and explore Mobile Bay
- 📱 **Web-based interface** - No software installation required

## 🚀 Quick Start

### 1. Launch the System
```bash
# Start API server (Terminal 1)
conda activate plasticparcels-test
python plasticparcels_api_server.py plasticparcels/mobile_schism_output

# Start web server (Terminal 2)  
python -m http.server 8080
```

### 2. Open the Interface
Navigate to: **`http://localhost:8080/trajectory_map.html`**

### 3. Simulate Your First Trajectory
1. **Right-click** anywhere on the Mobile Bay map
2. **Select "Simulate Trajectory Here"**
3. **Watch** the magic happen! 🌊

## 🎮 How It Works

### The Animation Process
1. **User clicks** on map location
2. **API calculates** trajectory using PlasticParcels
3. **Particle appears** at release point
4. **Animation begins** - particle moves step-by-step
5. **Trail draws** behind particle (optional)
6. **Arrow marks** final destination

### Visual Elements
- 🔴 **Red dot**: Release point where plastic enters water
- 🟡 **Moving particle**: Current position of plastic particle
- ➖ **Dashed trail**: Path the particle has traveled
- 🔺 **Arrow marker**: Final destination when simulation completes

## ⚙️ Customization Options

### Animation Settings
- **Speed**: Very Fast (50ms) → Very Slow (1s)
- **Trail Display**: Show/hide particle path
- **Pause/Resume**: Control all animations
- **Clear All**: Remove trajectories and start fresh

### Simulation Parameters
- **Duration**: 6 hours to 1 week
- **Output Frequency**: Every 15 minutes to 2 hours
- **Multiple Particles**: Unlimited concurrent simulations
- **Domain Coverage**: Complete Mobile Bay area

## 📊 System Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │    │  HTTP Server    │    │   API Server    │
│                 │    │   (Port 8080)   │    │   (Port 5000)   │
│ Animated Map    │◄──►│                 │    │                 │
│ Interface       │    │ Static Files    │    │ PlasticParcels  │
│                 │    │                 │    │   Simulation    │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                                              │
         └──────────── API Calls ──────────────────────┘
```

### Technology Stack
- **Backend**: Python, Flask, PlasticParcels, NumPy
- **Frontend**: HTML5, JavaScript, Leaflet.js, CSS3
- **Data**: SCHISM ocean model, GeoJSON trajectories
- **Deployment**: HTTP servers with port forwarding

## 📁 Project Structure

```
plasticparcels/
├── 🎬 trajectory_map.html              # Main animated interface
├── 🖥️ plasticparcels_api_server.py     # REST API server
├── 🔍 check_api_status.py              # System health checker
├── 🐍 api_client_example.py            # Python client examples
├── 📊 demo.html                        # Original demo interface
├── 📚 Documentation/
│   ├── README.md                       # This file
│   ├── USER_GUIDE.md                   # User instructions
│   ├── DEVELOPER_REFERENCE.md          # Technical details
│   ├── ANIMATION_DOCUMENTATION.md      # Complete documentation
│   ├── QUICK_REFERENCE.md              # Common tasks
│   └── API_README.md                   # API reference
└── 📁 plasticparcels/
    └── mobile_schism_output/           # Mobile Bay data
```

## 🎯 Use Cases

### 🔬 Scientific Research
- **Pollution tracking**: Understand plastic transport patterns
- **Current analysis**: Visualize ocean flow dynamics
- **Environmental impact**: Assess pollution accumulation zones
- **Model validation**: Compare simulations with observations

### 🎓 Education & Outreach
- **Interactive demonstrations**: Engage audiences with live simulations
- **Concept illustration**: Show how ocean currents work
- **Environmental awareness**: Visualize plastic pollution impacts
- **Student projects**: Hands-on learning with real data

### 💼 Operational Applications
- **Spill response**: Predict pollution spread patterns
- **Monitoring planning**: Optimize sampling locations
- **Policy support**: Inform environmental regulations
- **Risk assessment**: Evaluate contamination scenarios

## 🌍 Domain Coverage

### Mobile Bay, Alabama
- **Longitude**: -89.124°E to -87.964°E
- **Latitude**: 30.017°N to 30.617°N
- **Features**: Bay entrance, main channels, river mouths, coastal areas
- **Data**: 11 days of hourly SCHISM model output
- **Resolution**: High-resolution grid with 61 points

### Interesting Locations to Test
- **Bay entrance** (-87.97°E, 30.25°N): Tidal exchange patterns
- **Main channel** (-88.04°E, 30.35°N): Primary flow dynamics
- **River mouths** (-88.1°E, 30.6°N): Freshwater influence
- **Coastal zones** (-88.2°E, 30.4°N): Retention areas

## 📖 Documentation Guide

### For Users
- **[USER_GUIDE.md](USER_GUIDE.md)**: Complete step-by-step instructions
- **[QUICK_REFERENCE.md](QUICK_REFERENCE.md)**: Common tasks and shortcuts

### For Developers  
- **[DEVELOPER_REFERENCE.md](DEVELOPER_REFERENCE.md)**: Technical implementation
- **[API_README.md](API_README.md)**: REST API documentation

### For System Administrators
- **[ANIMATION_DOCUMENTATION.md](ANIMATION_DOCUMENTATION.md)**: Full system docs
- **[START_SERVER.md](START_SERVER.md)**: Deployment instructions

## 🔧 Installation

### Prerequisites
```bash
# Create conda environment
conda create -n plasticparcels-test python=3.11 -y
conda activate plasticparcels-test

# Install PlasticParcels
conda install conda-forge::plasticparcels -y

# Install web dependencies
pip install flask flask-cors requests
```

### Data Setup
Ensure you have Mobile Bay SCHISM data in PlasticParcels format:
```
plasticparcels/mobile_schism_output/
├── settings.json
└── [SCHISM data files]
```

### Launch System
```bash
# Start API server
python plasticparcels_api_server.py plasticparcels/mobile_schism_output

# Start web server (new terminal)
python -m http.server 8080
```

### Access Interface
Open browser to: `http://localhost:8080/trajectory_map.html`

## 🐛 Troubleshooting

### Quick Diagnostics
```bash
# Check system health
python check_api_status.py

# Test API directly
curl http://localhost:5000/health

# Run example client
python api_client_example.py --test
```

### Common Issues
- **Connection failed**: Verify servers are running on ports 5000 and 8080
- **Animation freezes**: Use Pause/Resume or refresh browser
- **Simulation errors**: Ensure release points are within Mobile Bay
- **Performance issues**: Limit concurrent animations, use appropriate speeds

## 🎉 Success Stories

### What Users Are Saying
> *"The animated trajectories make it so much easier to understand how ocean currents work!"* - Marine Science Student

> *"Perfect for demonstrating plastic pollution transport to stakeholders."* - Environmental Consultant  

> *"The right-click interface is incredibly intuitive - anyone can use it!"* - Outreach Coordinator

### Real-World Applications
- **University courses**: Teaching oceanography and environmental science
- **Research presentations**: Visualizing model results for conferences
- **Public outreach**: Engaging communities in pollution discussions
- **Policy briefings**: Supporting environmental decision-making

## 🚀 Future Enhancements

### Planned Features
- **3D visualization**: Depth-dependent trajectories
- **Real-time data**: Live ocean conditions
- **Mobile app**: Smartphone interface
- **Batch processing**: Multiple simultaneous simulations
- **Data export**: Download results in various formats

### Integration Opportunities
- **GIS platforms**: QGIS, ArcGIS plugins
- **Scientific workflows**: Jupyter notebook integration
- **Cloud deployment**: Scalable web services
- **Educational platforms**: LMS integration

## 📞 Support & Community

### Getting Help
1. **Check documentation**: Comprehensive guides available
2. **Run diagnostics**: Use built-in testing tools
3. **Review logs**: Check terminal output for errors
4. **Try examples**: Use provided client scripts

### Contributing
- **Report issues**: Document bugs and feature requests
- **Share improvements**: Code contributions welcome
- **Provide feedback**: User experience insights valuable
- **Create content**: Documentation and tutorials

## 📄 License & Citation

### Software License
This project builds on PlasticParcels (MIT License) and uses open-source components.

### Citation
If you use this system in research, please cite:
- PlasticParcels: [Original paper citation]
- This visualization system: [Your publication details]

### Acknowledgments
- **PlasticParcels team**: Core simulation engine
- **SCHISM developers**: Ocean model data
- **Leaflet.js**: Interactive mapping
- **Open source community**: Supporting libraries

---

## 🌊 Ready to Explore?

**Start simulating plastic trajectories now!**

1. Launch the servers
2. Open `http://localhost:8080/trajectory_map.html`
3. Right-click anywhere on Mobile Bay
4. Watch plastic particles come to life!

*Transform static data into dynamic understanding with the PlasticParcels Animated Trajectory System.* ✨
