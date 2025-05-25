#!/usr/bin/env python3
"""
HYCOM Gulf of Mexico Data Download and Visualization Script

This script demonstrates how to download and visualize HYCOM Gulf of Mexico data
from the HYCOM Data Server when available.

HYCOM Gulf of Mexico Hindcast (Free-run):
- Resolution: 1/25° (~4 km) Gulf grid
- Layers: ~20 vertical levels  
- Period: 1992–2009
- Experiment: GOMl0.04 (expt_02.2)
- Data Server: HYCOM THREDDS/HTTP

Usage:
    python download_hycom_data.py --year 2005 --day 100
    python download_hycom_data.py --year 2005 --day 100 --variable ssh
    python download_hycom_data.py --list-variables
"""

import argparse
import requests
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature
from datetime import datetime, timedelta
import os

class HYCOMDownloader:
    """
    HYCOM Gulf of Mexico data downloader and visualizer.
    """
    
    def __init__(self):
        """Initialize HYCOM downloader."""
        # HYCOM Gulf of Mexico experiment URLs
        self.base_urls = [
            'https://tds.hycom.org/thredds/dodsC/GOMl0.04/expt_02.2',
            'https://ncss.hycom.org/thredds/dodsC/GOMl0.04/expt_02.2',
            'https://data.hycom.org/datasets/GOMl0.04/expt_02.2'
        ]
        
        # HYCOM variable mappings
        self.variables = {
            'ssh': 'surf_el',           # Sea surface height
            'sst': 'water_temp',        # Sea surface temperature  
            'u': 'water_u',             # Eastward velocity
            'v': 'water_v',             # Northward velocity
            'salinity': 'salinity',     # Salinity
            'mixed_layer': 'mixed_layer_thickness'
        }
        
        # Gulf of Mexico domain
        self.gom_bounds = {
            'lon_min': -98.0,
            'lon_max': -80.0, 
            'lat_min': 18.0,
            'lat_max': 31.0
        }
    
    def check_server_status(self):
        """Check HYCOM server accessibility."""
        print("🔍 Checking HYCOM server status...")
        
        accessible_urls = []
        for url in self.base_urls:
            try:
                response = requests.head(url, timeout=10)
                if response.status_code == 200:
                    print(f"✅ {url} - Accessible")
                    accessible_urls.append(url)
                else:
                    print(f"❌ {url} - Status {response.status_code}")
            except Exception as e:
                print(f"❌ {url} - Connection error: {e}")
        
        return accessible_urls
    
    def list_available_data(self, base_url, year_range=(1992, 2009)):
        """List available HYCOM data files."""
        print(f"\n📋 Checking available data for {year_range[0]}-{year_range[1]}...")
        
        available_files = []
        
        # Sample a few dates to check availability
        test_dates = [
            (1995, 1),    # Jan 1, 1995
            (2000, 100),  # Apr 10, 2000  
            (2005, 200),  # Jul 19, 2005
            (2008, 300)   # Oct 26, 2008
        ]
        
        for year, day in test_dates:
            filename = f'archv.{year}_{day:03d}_00.nc'
            test_url = f'{base_url}/{filename}'
            
            try:
                response = requests.head(test_url, timeout=5)
                if response.status_code == 200:
                    available_files.append((year, day, filename))
                    print(f"✅ {filename} - Available")
                else:
                    print(f"❌ {filename} - Not found")
            except:
                print(f"❌ {filename} - Connection error")
        
        return available_files
    
    def download_hycom_data(self, year, day, variables=['ssh'], base_url=None):
        """Download HYCOM data for specified date and variables."""
        if base_url is None:
            accessible_urls = self.check_server_status()
            if not accessible_urls:
                raise ConnectionError("No accessible HYCOM servers found")
            base_url = accessible_urls[0]
        
        # HYCOM filename convention
        filename = f'archv.{year}_{day:03d}_00.nc'
        full_url = f'{base_url}/{filename}'
        
        print(f"\n📥 Downloading HYCOM data...")
        print(f"   URL: {full_url}")
        print(f"   Date: {year}, day {day}")
        print(f"   Variables: {variables}")
        
        try:
            # Open dataset
            ds = xr.open_dataset(full_url)
            
            print("✅ Successfully connected to HYCOM data!")
            print(f"   Dimensions: {dict(ds.dims)}")
            print(f"   Available variables: {list(ds.data_vars)}")
            
            # Extract Gulf of Mexico region if global data
            if 'lon' in ds.coords and 'lat' in ds.coords:
                gom_ds = ds.sel(
                    lon=slice(self.gom_bounds['lon_min'], self.gom_bounds['lon_max']),
                    lat=slice(self.gom_bounds['lat_min'], self.gom_bounds['lat_max'])
                )
                print(f"   Extracted Gulf of Mexico region")
                print(f"   GOM grid size: {len(gom_ds.lat)} × {len(gom_ds.lon)}")
                return gom_ds
            else:
                return ds
                
        except Exception as e:
            print(f"❌ Error downloading HYCOM data: {e}")
            return None
    
    def create_visualization(self, ds, variable='ssh', save_plot=True):
        """Create visualization of HYCOM data."""
        print(f"\n🎨 Creating visualization for {variable}...")
        
        # Set up plot
        fig, ax = plt.subplots(1, 1, figsize=(12, 8), 
                              subplot_kw={'projection': ccrs.PlateCarree()})
        
        # Set extent to Gulf of Mexico
        extent = [self.gom_bounds['lon_min'], self.gom_bounds['lon_max'],
                 self.gom_bounds['lat_min'], self.gom_bounds['lat_max']]
        ax.set_extent(extent, crs=ccrs.PlateCarree())
        
        # Add map features
        ax.add_feature(cfeature.COASTLINE, linewidth=0.8)
        ax.add_feature(cfeature.LAND, color='lightgray')
        ax.add_feature(cfeature.BORDERS, linewidth=0.5)
        ax.add_feature(cfeature.STATES, linewidth=0.3, alpha=0.5)
        
        # Plot data based on variable type
        if variable == 'ssh':
            data = ds['surf_el'] if 'surf_el' in ds else ds[list(ds.data_vars)[0]]
            levels = np.linspace(data.min(), data.max(), 20)
            cmap = 'RdYlBu_r'
            units = 'm'
            title = 'Sea Surface Height'
            
        elif variable == 'sst':
            data = ds['water_temp'] if 'water_temp' in ds else ds[list(ds.data_vars)[0]]
            if data.dims[-1] == 'depth':  # Take surface level
                data = data.isel(depth=0)
            levels = np.linspace(data.min(), data.max(), 20)
            cmap = 'plasma'
            units = '°C'
            title = 'Sea Surface Temperature'
            
        elif variable in ['u', 'v']:
            var_name = f'water_{variable}' if f'water_{variable}' in ds else list(ds.data_vars)[0]
            data = ds[var_name]
            if data.dims[-1] == 'depth':  # Take surface level
                data = data.isel(depth=0)
            levels = np.linspace(data.min(), data.max(), 20)
            cmap = 'RdBu_r'
            units = 'm/s'
            title = f'Surface Current ({variable.upper()}-component)'
            
        else:
            data = ds[list(ds.data_vars)[0]]
            levels = 20
            cmap = 'viridis'
            units = 'units'
            title = f'{variable}'
        
        # Create contour plot
        if len(data.dims) == 3:  # time, lat, lon
            plot_data = data.isel(time=0)
        else:
            plot_data = data
            
        contour_plot = ax.contourf(ds.lon, ds.lat, plot_data,
                                  levels=levels, cmap=cmap, extend='both',
                                  transform=ccrs.PlateCarree())
        
        # Add contour lines
        contour_lines = ax.contour(ds.lon, ds.lat, plot_data,
                                  levels=10, colors='black', linewidths=0.5,
                                  transform=ccrs.PlateCarree())
        ax.clabel(contour_lines, inline=True, fontsize=8)
        
        # Add colorbar
        cbar = plt.colorbar(contour_plot, ax=ax, orientation='horizontal',
                           pad=0.08, shrink=0.8)
        cbar.set_label(f'{title} ({units})', fontsize=12)
        
        # Set title
        ax.set_title(f'HYCOM Gulf of Mexico: {title}\\n'
                    f'Resolution: 1/25° (~4 km) • Experiment: GOMl0.04',
                    fontsize=14, fontweight='bold')
        
        # Add gridlines
        ax.gridlines(draw_labels=True, alpha=0.5)
        
        plt.tight_layout()
        
        if save_plot:
            filename = f'hycom_gom_{variable}.png'
            plt.savefig(filename, dpi=300, bbox_inches='tight')
            print(f"✅ Saved plot: {filename}")
        
        return fig, ax


def main():
    """Main function with command line interface."""
    parser = argparse.ArgumentParser(
        description='Download and visualize HYCOM Gulf of Mexico data',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Download SSH data for April 10, 2005
  python %(prog)s --year 2005 --day 100 --variable ssh
  
  # Download SST data for July 19, 2005  
  python %(prog)s --year 2005 --day 200 --variable sst
  
  # List available variables
  python %(prog)s --list-variables
  
  # Check server status
  python %(prog)s --check-servers
        """)
    
    parser.add_argument('--year', type=int, default=2005,
                       help='Year (1992-2009, default: 2005)')
    parser.add_argument('--day', type=int, default=100,
                       help='Day of year (1-365, default: 100)')
    parser.add_argument('--variable', default='ssh',
                       choices=['ssh', 'sst', 'u', 'v', 'salinity'],
                       help='Variable to download and plot (default: ssh)')
    parser.add_argument('--list-variables', action='store_true',
                       help='List available HYCOM variables')
    parser.add_argument('--check-servers', action='store_true',
                       help='Check HYCOM server accessibility')
    
    args = parser.parse_args()
    
    # Initialize downloader
    downloader = HYCOMDownloader()
    
    if args.list_variables:
        print("Available HYCOM variables:")
        for key, value in downloader.variables.items():
            print(f"  {key}: {value}")
        return
    
    if args.check_servers:
        accessible = downloader.check_server_status()
        if accessible:
            print(f"\\n✅ {len(accessible)} server(s) accessible")
        else:
            print("\\n❌ No servers accessible")
        return
    
    # Validate inputs
    if not (1992 <= args.year <= 2009):
        print("❌ Error: Year must be between 1992 and 2009")
        return
    
    if not (1 <= args.day <= 365):
        print("❌ Error: Day must be between 1 and 365")
        return
    
    print(f"🌊 HYCOM Gulf of Mexico Data Download")
    print(f"Year: {args.year}, Day: {args.day}, Variable: {args.variable}")
    
    try:
        # Download data
        ds = downloader.download_hycom_data(args.year, args.day, [args.variable])
        
        if ds is not None:
            # Create visualization
            downloader.create_visualization(ds, args.variable)
            
            # Save dataset
            output_file = f'hycom_gom_{args.year}_{args.day:03d}_{args.variable}.nc'
            ds.to_netcdf(output_file)
            print(f"💾 Saved dataset: {output_file}")
            
            ds.close()
            
            print("\\n🎉 HYCOM data download and visualization complete!")
        else:
            print("❌ Failed to download HYCOM data")
            print("💡 Tip: Try the synthetic data demo instead:")
            print("   python gulf_of_mexico_hycom_demo.py")
    
    except Exception as e:
        print(f"❌ Error: {e}")
        print("💡 Tip: HYCOM servers may be temporarily unavailable")
        print("   Try again later or use the synthetic data demo")


if __name__ == "__main__":
    main()
