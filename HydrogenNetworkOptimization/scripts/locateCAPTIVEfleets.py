import pandas as pd
from geopy.geocoders import ArcGIS
from geopy.extra.rate_limiter import RateLimiter
from pathlib import Path
import time

# --- CONFIGURATION ---
# Replace with your actual filename
FILENAME = 'COcaptive_catex.csv' 

# SCRIPT_DIR is C:\Users\spreuss\Desktop\HydrogenNetworkOptimization\scripts
SCRIPT_DIR = Path(__file__).resolve().parent

# Go up ONE level to HydrogenNetworkOptimization, then down into 'data'
DATA_DIR = SCRIPT_DIR.parent / 'data'

# Define your input and output files using the corrected directory
INPUT_FILE = DATA_DIR / FILENAME
OUTPUT_FILE = DATA_DIR / f"geocoded_{FILENAME}"

def geocode_addresses():
    if not INPUT_FILE.exists():
        print(f"Error: Could not find {INPUT_FILE}")
        return

    print(f"Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # Initialize ArcGIS Geocoder (High accuracy for US addresses)
    geolocator = ArcGIS(user_agent="colorado_h2_research")
    
    # Rate limiter adds a small delay between requests to prevent being blocked
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=0.5)

    print("Starting geocoding (this may take a few minutes)...")
    
    # Create new columns for coordinates
    df['location'] = df['Address'].apply(geocode)
    
    # Extract Lat and Long from the location object
    df['Latitude'] = df['location'].apply(lambda loc: loc.latitude if loc else None)
    df['Longitude'] = df['location'].apply(lambda loc: loc.longitude if loc else None)

    # --- ERROR REPORTING ---
    failed_df = df[df['Latitude'].isnull()]
    
    if not failed_df.empty:
        print(f"\n--- ATTENTION: {len(failed_df)} ADDRESSES FAILED ---")
        for addr in failed_df['Address']:
            print(f"FAILED: {addr}")
    else:
        print("\nSuccess! All addresses were geocoded.")

    # Drop the temporary 'location' object column before saving
    df_final = df.drop(columns=['location'])
    
    # Save to the same folder as the original
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"\nNew file saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    start_time = time.time()
    geocode_addresses()
    print(f"Total time: {round(time.time() - start_time, 2)} seconds")