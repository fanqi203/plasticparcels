import subprocess, shlex

cmd = """
copernicusmarine subset
  --dataset-id cmems_mod_glo_phy_anfc_0.083deg_PT1H-m
  --variable uo
  --variable vo
  --variable thetao
  --variable so
  --start-datetime 2025-10-17T00:00:00
  --end-datetime 2025-10-20T00:00:00
  --minimum-longitude -95 --maximum-longitude -70
  --minimum-latitude 26  --maximum-latitude 31
  --minimum-depth 0 --maximum-depth 50
  --output-filename subset.nc
  --output-directory ./downloads
  --overwrite
"""
subprocess.run(shlex.split(" ".join(line.strip() for line in cmd.splitlines() if line.strip())))
