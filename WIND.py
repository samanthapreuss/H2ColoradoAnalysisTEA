import geopandas as gpd
from pathlib import Path
import os

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
# This is your target destination
OUTPUT_DIR = BASE_DIR / "outputs" / "script_outputs"

# CRITICAL STEP: Create the directory if it doesn't exist
# 'parents=True' creates any missing folders in the middle of the path
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- 2. LOAD DATA ---
input_file = "uswtdb_V8_2_20251210.geojson" 
print("Loading data...")
gdf = gpd.read_file(DATA_DIR / input_file)

# --- 3. FILTER ---
colorado_data = gdf[gdf['t_state'] == 'CO']

# --- 4. SAVE TO THE TARGET DIRECTORY ---
output_filename = "colorado_subset.geojson"
# Join the directory path and the filename using the / operator
full_output_path = OUTPUT_DIR / output_filename

colorado_data.to_file(full_output_path, driver='GeoJSON')

print(f"Done! Saved Colorado data to: {full_output_path}")