from pathlib import Path
import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from shapely.geometry import Point

# Define the directory where the file lives
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
DATA_DIR2 = BASE_DIR / "data"/"script_outputs"
file_path = DATA_DIR / "geocoded_COcaptive_catex.csv"
OUTPUT_DIR = BASE_DIR /"outputs" / "finalized images"

df = pd.read_csv(file_path)

# Clean whitespace
df['Category'] = df['Category'].str.strip()

# 2. Convert to a GeoDataFrame
geometry = [Point(xy) for xy in zip(df['Longitude'], df['Latitude'])]
gdf = gpd.GeoDataFrame(df, geometry=geometry, crs="EPSG:4326")

# 3. Custom Color Mapping
color_map = {
    'Hauling': 'darkblue',
    'Oil, Gas and Utility Services': 'orange',
    'Construction Material and Equipment': '#3cb371',
    'School Transit': 'red',
    'Public Works': '#4b0082',
    'Landscape and Groundskeeping': '#cd853f',
    'Refrigerated Transit': 'lightpink',
    'Public Transit': 'gray',
    'Waste Management Services': 'lightgreen',
    'Rental Services': 'lightblue'
}

gdf['color'] = gdf['Category'].map(color_map).fillna('black')

# 4. Load Colorado Boundary
state_url = "https://www2.census.gov/geo/tiger/GENZ2020/shp/cb_2020_us_state_20m.zip"
usa = gpd.read_file(state_url)
colorado = usa[usa['NAME'] == 'Colorado']

# Project to Colorado Albers (EPSG:3502)
colorado = colorado.to_crs(epsg=3502)
gdf = gdf.to_crs(epsg=3502)

# --- [Keep Sections 1-4 as they are] ---

# --- NEW: LOAD SUMMARY DATA FOR LEGEND ---
SUMMARY_PATH = BASE_DIR / "data" / "script_outputs" / "co_captive_sector_summary.csv" 
if SUMMARY_PATH.exists():
    summary_df = pd.read_csv(SUMMARY_PATH)
    # Create a lookup dictionary: {'Category': Total_Trucks}
    truck_lookup = dict(zip(summary_df['Category'], summary_df['Total_Trucks']))
else:
    print(f"Warning: Summary file not found at {SUMMARY_PATH}. Legend will show categories only.")
    truck_lookup = {}

# --- 5. Create the Map ---
fig, ax = plt.subplots(figsize=(16, 10))

# Plot Colorado base
colorado.plot(ax=ax, color='#f5f5f5', edgecolor='#bcbcbc', linewidth=1.2)

# Plot Fleet locations
ax.scatter(
    gdf.geometry.x, 
    gdf.geometry.y, 
    c=gdf['color'], 
    s=70, 
    edgecolor='black', 
    linewidth=0.5, 
    alpha=0.9,
    zorder=3
)

# --- 6. Create the Legend (UPDATED) ---
legend_elements = []
for cat, color in color_map.items():
    # Pull truck count from lookup; default to 0 if category is missing
    truck_count = truck_lookup.get(cat, 0)
    
    # Create the label: "Category (X,XXX Trucks)"
    label_text = f"{cat} ({int(truck_count):,} Trucks)"
    
    legend_elements.append(
        Line2D([0], [0], marker='o', color='w', label=label_text,
               markerfacecolor=color, markersize=10, markeredgecolor='black')
    )

# Position Legend
ax.legend(
    handles=legend_elements, 
    title="Fleet Categories & Total Trucks", 
    loc='center left',
    bbox_to_anchor=(1.02, 0.5),
    fontsize=10,
    frameon=True,
    borderpad=1
)

# --- 7. Final Formatting & Layout Fix ---
ax.set_title('Colorado Fleet Locations by Category', fontsize=18, fontweight='bold', pad=20)
ax.set_axis_off()

# Adjust layout to prevent legend cutoff
plt.subplots_adjust(right=0.75) # Increased margin for longer text labels

# Save as PNG
plt.savefig(OUTPUT_DIR / "colorado_FLEETS_map.png", dpi=300, bbox_inches='tight')
plt.show()

print(f"Success! Map saved with visible legend to: {OUTPUT_DIR / 'colorado_FLEETS_map.png'}")