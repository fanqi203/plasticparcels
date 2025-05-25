#!/usr/bin/env python3
"""
Simple Mobile Bay SCHISM to PlasticParcels converter

Processes the first 5 sequential files: out2d_1.nc, out2d_2.nc, out2d_3.nc, out2d_4.nc, out2d_5.nc

Usage:
    conda activate plasticparcels
    python run_mobile_simple.py
"""

from schism_timeseries_to_plasticparcels import SCHISMTimeSeriesConverter
import glob
import re

def run_mobile_simple():
    """Simple Mobile Bay conversion - first 5 sequential files."""

    print("🌊 MOBILE BAY SIMPLE CONVERTER 🌊")
    print("=" * 45)

    # Get all Mobile Bay SCHISM files
    schism_dir = '/anvil/projects/x-ees240085/sbao/mobile/outputs'
    all_files = glob.glob(f'{schism_dir}/out2d_*.nc')
    
    # Sort files by the numeric part to get sequential order (1, 2, 3, 4, 5...)
    def extract_number(filename):
        match = re.search(r'out2d_(\d+)\.nc', filename)
        return int(match.group(1)) if match else 0
    
    all_files = sorted(all_files, key=extract_number)
    
    # Use first 5 files
    test_files = all_files[:5]
    
    print(f"Found {len(all_files)} total SCHISM files")
    print(f"Processing first 5 sequential files:")
    for i, f in enumerate(test_files):
        print(f"  {i+1}. {f.split('/')[-1]}")
    print()

    # Create converter
    converter = SCHISMTimeSeriesConverter(
        schism_files=test_files,
        output_dir='mobile_simple',
        target_resolution=0.01  # 1.1 km resolution
    )

    # Run complete workflow
    print("🚀 Starting conversion workflow...")
    success = converter.run_complete_workflow()

    if success:
        print()
        print("🎉 CONVERSION SUCCESSFUL! 🎉")
        print("=" * 35)
        print("✅ Created NEMO-compatible time series files")
        print("✅ Ready for PlasticParcels simulations")
        print()
        print("📁 Output directory: mobile_simple/")
        print("📄 Files created:")
        print("   • U_timeseries.nc, V_timeseries.nc, W_timeseries.nc")
        print("   • T_timeseries.nc, S_timeseries.nc")
        print("   • ocean_mesh_hgr.nc, bathymetry_mesh_zgr.nc")
        print("   • timeseries_settings.json")
        print()
        print("🧪 Test PlasticParcels integration:")
        print("   conda activate plasticparcels")
        print("   python test_mobile_plasticparcels.py")
        
    else:
        print("❌ Conversion failed. Check error messages above.")

    return success

if __name__ == "__main__":
    run_mobile_simple()
