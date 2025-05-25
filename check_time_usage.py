#!/usr/bin/env python3
"""
Check how PlasticParcels is using the time data from our daily files.
"""

import json
import numpy as np
from datetime import datetime, timedelta
import os

def check_fieldset_time_usage():
    """Check what time data PlasticParcels fieldset contains."""
    
    print("🔍 CHECKING PLASTICPARCELS TIME USAGE 🔍")
    print("=" * 50)
    
    data_dir = 'mobile_daily_format'
    settings_file = os.path.join(data_dir, 'settings.json')
    
    if not os.path.exists(settings_file):
        print(f"❌ Settings file not found: {settings_file}")
        return False
    
    try:
        # Load settings
        with open(settings_file, 'r') as f:
            settings = json.load(f)
        
        # Add simulation settings
        settings['simulation'] = {
            'startdate': datetime(2024, 1, 1, 0, 0, 0),
            'runtime': timedelta(days=1, hours=12),  # 1.5 day simulation
            'outputdt': timedelta(hours=3),
            'dt': timedelta(minutes=20),
        }
        
        # Import PlasticParcels
        from plasticparcels.constructors import create_hydrodynamic_fieldset
        
        # Create fieldset
        print("📊 Creating fieldset...")
        fieldset = create_hydrodynamic_fieldset(settings)
        print("✅ Fieldset created successfully!")
        
        # Check time information
        print("\n📋 FIELDSET TIME INFORMATION:")
        print(f"   Available time steps: {len(fieldset.U.grid.time)}")
        print(f"   Time range: {fieldset.U.grid.time[0]:.1f} to {fieldset.U.grid.time[-1]:.1f} hours")
        print(f"   Time values: {fieldset.U.grid.time}")
        
        # Check individual file time data
        print("\n📁 INDIVIDUAL FILE TIME DATA:")
        import xarray as xr
        
        for day, date in enumerate(['2024-01-01', '2024-01-02']):
            u_file = os.path.join(data_dir, f'U_{date}.nc')
            if os.path.exists(u_file):
                ds = xr.open_dataset(u_file)
                print(f"   {date}: time_counter = {ds.time_counter.values}")
                ds.close()
        
        # Test velocity sampling at different times
        print("\n🌊 TESTING VELOCITY SAMPLING AT DIFFERENT TIMES:")
        lon_center = (fieldset.U.grid.lon.min() + fieldset.U.grid.lon.max()) / 2
        lat_center = (fieldset.U.grid.lat.min() + fieldset.U.grid.lat.max()) / 2
        
        # Sample every 2 hours
        sample_times = range(0, min(12, len(fieldset.U.grid.time)), 2)
        
        for t in sample_times:
            try:
                u_val = fieldset.U[t, 0, lat_center, lon_center]
                v_val = fieldset.V[t, 0, lat_center, lon_center]
                speed = np.sqrt(u_val**2 + v_val**2)
                actual_time = fieldset.U.grid.time[t]
                print(f"   Time index {t} (hour {actual_time:.1f}): U={u_val:.4f}, V={v_val:.4f}, Speed={speed:.4f} m/s")
            except Exception as e:
                print(f"   Time index {t}: Error - {e}")
        
        # Check if velocities change over time (indicating hourly data is being used)
        print("\n📈 CHECKING IF VELOCITIES CHANGE OVER TIME:")
        velocities = []
        for t in range(min(6, len(fieldset.U.grid.time))):
            try:
                u_val = fieldset.U[t, 0, lat_center, lon_center]
                v_val = fieldset.V[t, 0, lat_center, lon_center]
                velocities.append((u_val, v_val))
            except:
                velocities.append((np.nan, np.nan))
        
        # Check if velocities are different (not constant)
        u_vals = [v[0] for v in velocities if not np.isnan(v[0])]
        v_vals = [v[1] for v in velocities if not np.isnan(v[1])]
        
        if len(u_vals) > 1:
            u_variation = np.std(u_vals)
            v_variation = np.std(v_vals)
            print(f"   U velocity variation (std): {u_variation:.6f} m/s")
            print(f"   V velocity variation (std): {v_variation:.6f} m/s")
            
            if u_variation > 1e-6 or v_variation > 1e-6:
                print("   ✅ VELOCITIES CHANGE OVER TIME - Using hourly data!")
            else:
                print("   ⚠️  VELOCITIES ARE CONSTANT - May only be using first time step")
        
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    check_fieldset_time_usage()
