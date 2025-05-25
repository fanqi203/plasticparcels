import json
from datetime import datetime, timedelta
from plasticparcels.constructors import create_hydrodynamic_fieldset

# Load settings
with open('mobile/mobile_settings.json', 'r') as f:
    settings = json.load(f)

settings['simulation'] = {
    'startdate': datetime(2024, 1, 1, 0, 0, 0),
    'runtime': timedelta(hours=2),
    'outputdt': timedelta(hours=1),
    'dt': timedelta(minutes=20),
}

# Test fieldset creation
fieldset = create_hydrodynamic_fieldset(settings)
print('✅ SUCCESS! Fieldset created!')
print(f'Domain: {fieldset.U.grid.lon.min():.3f}°E to {fieldset.U.grid.lon.max():.3f}°E')
print(f'        {fieldset.U.grid.lat.min():.3f}°N to {fieldset.U.grid.lat.max():.3f}°N')
print(f'Time steps: {len(fieldset.U.grid.time)}')

