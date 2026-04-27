import pandas as pd
from geopy.distance import geodesic
from pathlib import Path

def calculate_site_distances():
    # 1. Define Coordinates
    # Format: (Latitude, Longitude)
    start_pos = (39.687317, -104.016903)  # 39°41'14.34"N 104°01'00.85"W
    inter_pos = (39.746428, -104.608069)  # 39°44'47.14"N 104°36'29.05"W

    # 2. Calculate initial leg distance
    initial_dist = geodesic(start_pos, inter_pos).miles
    print(f"Distance from Start to Intermediate: {initial_dist:.2f} miles\n")

    # 3. Setup File Paths
    # "two up from the directory where the script is run"
    base_path = Path(__file__).resolve().parent.parent.parent
    data_dir = base_path / "data"
    site_dir = base_path / "scripts" / "DONE" / "outputs"
    
    balanced_sites_path = site_dir / "balanced_sites_details.csv"
    geocoded_sites_path = data_dir / "geocoded_candidate_sites.csv"

    # 4. Load Data
    try:
        balanced_df = pd.read_csv(balanced_sites_path)
        geocoded_df = pd.read_csv(geocoded_sites_path)
    except FileNotFoundError as e:
        print(f"Error: Could not find file. {e}")
        return

    # 5. Merge Data
    # We join the sites we want (balanced) with their coordinates (geocoded) via 'Address'
    merged_df = pd.merge(
        balanced_df[['Address']], 
        geocoded_df[['Address', 'Latitude', 'Longitude']], 
        on='Address', 
        how='left'
    )

    # 6. Calculate Distances from the Intermediate Point to each site
    def get_dist(row):
        if pd.isna(row['Latitude']) or pd.isna(row['Longitude']):
            return None
        site_coords = (row['Latitude'], row['Longitude'])
        return geodesic(inter_pos, site_coords).miles

    merged_df['distance_from_inter_miles'] = merged_df.apply(get_dist, axis=1)

    # 7. Output Results
    print(merged_df[['Address', 'distance_from_inter_miles']])
    
    # Optional: Save to new CSV
    merged_df.to_csv("site_distances_outputRushC.csv", index=False)

if __name__ == "__main__":
    calculate_site_distances()