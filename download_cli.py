import subprocess, shlex
from datetime import datetime, timedelta

# Calculate today + 3 days forecast
today = datetime.now().date()
start_date = today
end_date = today + timedelta(days=3)

# Format dates for Copernicus Marine API (ISO format)
start_datetime = f"{start_date}T00:00:00"
end_datetime = f"{end_date}T00:00:00"

print(f"📅 Downloading ocean data from {start_date} to {end_date}")
print(f"🌊 Date range: {start_datetime} to {end_datetime}")

cmd = f"""
copernicusmarine subset
  --dataset-id cmems_mod_glo_phy_anfc_0.083deg_PT1H-m
  --variable uo
  --variable vo
  --variable thetao
  --variable so
  --start-datetime {start_datetime}
  --end-datetime {end_datetime}
  --minimum-longitude -95 --maximum-longitude -70
  --minimum-latitude 26  --maximum-latitude 31
  --minimum-depth 0 --maximum-depth 50
  --output-filename subset.nc
  --output-directory ./downloads
  --overwrite
"""
subprocess.run(shlex.split(" ".join(line.strip() for line in cmd.splitlines() if line.strip())))
