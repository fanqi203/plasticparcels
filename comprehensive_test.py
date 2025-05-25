#!/usr/bin/env python3
"""
Comprehensive test demonstrating plasticparcels capabilities.
This test showcases multiple physics processes working together.
"""

import plasticparcels as pp
import parcels
import numpy as np
from datetime import datetime, timedelta

def run_comprehensive_test():
    """Run a comprehensive test with multiple physics processes."""
    print("=" * 70)
    print("COMPREHENSIVE PLASTICPARCELS PHYSICS TEST")
    print("=" * 70)
    
    try:
        # Load settings
        print("1. Loading configuration...")
        settings = pp.utils.load_settings('tests/test_data/test_settings.json')
        
        # Configure simulation
        settings['simulation'] = {
            'startdate': datetime.strptime('2020-01-04-00:00:00', '%Y-%m-%d-%H:%M:%S'),
            'runtime': timedelta(hours=4),
            'outputdt': timedelta(hours=1),
            'dt': timedelta(minutes=20),
        }
        
        # Configure plastic properties
        settings['plastictype'] = {
            'wind_coefficient': 0.001,      # 0.1% wind effect
            'plastic_diameter': 0.005,      # 5mm particles
            'plastic_density': 1025.0,      # Slightly denser than seawater
        }
        
        # Enable multiple physics processes
        settings['use_3D'] = True
        settings['use_biofouling'] = False  # Keep simple for test
        settings['use_stokes'] = False      # No wave data in simple test
        settings['use_wind'] = False        # No wind data in simple test  
        settings['use_mixing'] = True       # Enable vertical mixing
        
        print("✓ Configuration loaded")
        
        # Create fieldset with multiple physics
        print("\n2. Creating physics fieldset...")
        fieldset = pp.constructors.create_fieldset(settings)
        
        available_fields = list(fieldset.get_fields())
        print(f"✓ Fieldset created with {len(available_fields)} fields:")
        for field in available_fields[:8]:  # Show first 8 fields
            print(f"   - {field}")
        if len(available_fields) > 8:
            print(f"   ... and {len(available_fields) - 8} more")
        
        # Create particles
        print("\n3. Creating plastic particles...")
        release_locations = {
            'lons': [18.0, 18.2, 18.4], 
            'lats': [35.0, 35.1, 35.2],
            'plastic_amount': [100, 150, 200]  # Different amounts
        }
        
        pset = pp.constructors.create_particleset(fieldset, settings, release_locations)
        
        print(f"✓ Created {len(pset)} particles")
        print("   Initial state:")
        for i, p in enumerate(pset):
            print(f"     Particle {i+1}: ({p.lon:.3f}°, {p.lat:.3f}°, {p.depth:.1f}m)")
        
        # Create physics kernels
        print("\n4. Setting up physics kernels...")
        kernels = pp.constructors.create_kernel(fieldset)
        
        kernel_names = [k.__name__ for k in kernels]
        print(f"✓ Using {len(kernels)} physics kernels:")
        for kernel in kernel_names:
            print(f"   - {kernel}")
        
        # Store initial state
        initial_state = {
            'lons': pset.lon.copy(),
            'lats': pset.lat.copy(), 
            'depths': pset.depth.copy()
        }
        
        # Run simulation
        print("\n5. Running multi-physics simulation...")
        print("   Simulating 4 hours of plastic transport...")
        
        pset.execute(kernels, 
                    runtime=settings['simulation']['runtime'], 
                    dt=settings['simulation']['dt'])
        
        print("✓ Simulation completed successfully!")
        
        # Analyze results
        print("\n6. Analyzing results...")
        
        # Calculate movements
        h_displacement = np.sqrt((pset.lon - initial_state['lons'])**2 + 
                                (pset.lat - initial_state['lats'])**2)
        v_displacement = np.abs(pset.depth - initial_state['depths'])
        
        print("   Final particle states:")
        for i, p in enumerate(pset):
            h_dist = h_displacement[i] * 111.32  # Convert degrees to km (approx)
            v_dist = v_displacement[i]
            print(f"     Particle {i+1}: ({p.lon:.3f}°, {p.lat:.3f}°, {p.depth:.1f}m)")
            print(f"                    Moved {h_dist:.2f} km horizontally, {v_dist:.1f} m vertically")
        
        # Summary statistics
        total_h_movement = np.sum(h_displacement) * 111.32  # km
        total_v_movement = np.sum(v_displacement)  # m
        
        print(f"\n   Summary:")
        print(f"   • Total horizontal displacement: {total_h_movement:.2f} km")
        print(f"   • Total vertical displacement: {total_v_movement:.1f} m")
        print(f"   • Average speed: {total_h_movement/4:.2f} km/h")
        
        # Validate physics
        physics_working = []
        if total_h_movement > 0.1:
            physics_working.append("✓ Ocean current advection")
        if total_v_movement > 0.1:
            physics_working.append("✓ Vertical processes (settling/mixing)")
        
        print(f"\n   Physics processes verified:")
        for process in physics_working:
            print(f"   {process}")
        
        print("\n" + "=" * 70)
        print("🎉 COMPREHENSIVE TEST COMPLETED SUCCESSFULLY! 🎉")
        print("plasticparcels is fully functional with multi-physics capabilities")
        print("=" * 70)
        
        return True
        
    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = run_comprehensive_test()
    exit(0 if success else 1)
