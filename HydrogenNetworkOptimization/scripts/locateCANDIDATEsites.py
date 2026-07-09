import pandas as pd
from geopy.geocoders import ArcGIS
from geopy.extra.rate_limiter import RateLimiter
from pathlib import Path
import time

FILENAME = "candidate_sites.csv"  # Input CSV file name

# SCRIPT_DIR is C:\Users\spreuss\Desktop\HydrogenNetworkOptimization\scripts
SCRIPT_DIR = Path(__file__).resolve().parent

# Go up ONE level to HydrogenNetworkOptimization, then down into 'data'
DATA_DIR = SCRIPT_DIR.parent / 'data'

# Define your input and output files using the corrected directory
INPUT_FILE = DATA_DIR / FILENAME
OUTPUT_FILE = DATA_DIR / f"geocoded_{FILENAME}"
def geocode_addresses():
    if not INPUT_FILE.exists():
        print(f"Error: Could not find {INPUT_FILE} at {INPUT_FILE.absolute()}")
        return

    print(f"Loading data from {INPUT_FILE}...")
    df = pd.read_csv(INPUT_FILE)

    # 1. PRE-PROCESSING: Combine columns into a single search string
    # We combine 'Address' (Street) and 'City' (City, State, Zip)
    # Using astype(str) and strip() to prevent errors with missing data
    df['full_address_query'] = (
        df['Address'].astype(str).str.strip() + ", " + 
        df['City'].astype(str).str.strip()
    )

    # 2. Initialize ArcGIS Geocoder
    geolocator = ArcGIS(user_agent="colorado_h2_research_v2")
    
    # Rate limiter ensures stability and prevents timeouts
    geocode = RateLimiter(geolocator.geocode, min_delay_seconds=0.6)

    print(f"Starting geocoding for {len(df)} sites...")
    
    # 3. Geocode using the new combined column
    df['location'] = df['full_address_query'].apply(geocode)
    
    # Extract Lat and Long
    df['Latitude'] = df['location'].apply(lambda loc: loc.latitude if loc else None)
    df['Longitude'] = df['location'].apply(lambda loc: loc.longitude if loc else None)

    # --- ERROR REPORTING ---
    failed_df = df[df['Latitude'].isnull()]
    
    if not failed_df.empty:
        print(f"\n--- ATTENTION: {len(failed_df)} ADDRESSES FAILED ---")
        # Showing the combined address helps you see if the CSV data was formatted weirdly
        for addr in failed_df['full_address_query']:
            print(f"FAILED TO MAP: {addr}")
    else:
        print("\nSuccess! All addresses were geocoded with high accuracy.")

    # Drop temporary columns to keep the output file clean
    df_final = df.drop(columns=['location', 'full_address_query'])
    
    # Save to the data folder
    df_final.to_csv(OUTPUT_FILE, index=False)
    print(f"\nGeocoded file saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    start_time = time.time()
    geocode_addresses()
    elapsed = round(time.time() - start_time, 2)
    print(f"Finished. Total processing time: {elapsed} seconds")