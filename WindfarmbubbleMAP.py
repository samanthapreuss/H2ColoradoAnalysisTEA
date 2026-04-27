from pathlib import Path
import geopandas as gpd
import pandas as pd
import matplotlib.pyplot as plt
from shapely.geometry import box

# Define the directory where the file lives
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
geojson_path = DATA_DIR / "colorado_subset.geojson"
OUTPUT_DIR = BASE_DIR /"outputs" / "finalize images"

# Load it
gdf = gpd.read_file(geojson_path)


# 2. Aggregation Logic
agg_rules = {'t_cap': 'sum', 'geometry': 'first'}
farm_clusters_df = gdf.groupby('p_name').agg(agg_rules).reset_index()
farm_clusters = gpd.GeoDataFrame(farm_clusters_df, geometry='geometry', crs=gdf.crs)

# 3. Apply the 100 MW Threshold
major_farms = farm_clusters[farm_clusters['t_cap'] >= 100000].copy()
major_farms['total_mw'] = major_farms['t_cap'] / 1000.0
major_farms = major_farms.sort_values('p_name').reset_index(drop=True)

# 4. Create Colorado Boundary
co_bounds = box(-109.05, 37.0, -102.05, 41.0)
colorado = gpd.GeoDataFrame(geometry=[co_bounds], crs="EPSG:4326")

if major_farms.empty:
    print("No farms found exceeding 100 MW.")
else:
    colorado = colorado.to_crs(epsg=3857)
    major_farms = major_farms.to_crs(epsg=3857)

    fig, ax = plt.subplots(figsize=(22, 12)) 
    fig.patch.set_facecolor("#ffffff") 
    ax.set_facecolor('#fdfcf5')

    colorado.plot(ax=ax, color="#ffffffff", edgecolor="#F3E7E700", linewidth=2, zorder=1)

   # 5. Fine-Tuned Directions for Specific Points
    # Format: {PointNumber: (x_offset, y_offset)}
    custom_offsets = {
        4: (-45, -10),  # Left and slightly Down
        14: (0, 45),    # Directly Above the circle
        17: (50, 40),  # Further to the Lower Right
        12: (0, 45),    # Directly Above the circle
        2: (-35, -35),  # Bottom Left
        1: (35, 40),    # Top Right
        13: (35, 35),   # Top Right
        5: (0, 45),     # Above
        11: (-15, 45)    # Below
    }

 # ... [Keep previous sections 1-5 the same] ...

    # 6. Plot Points with DYNAMIC SIZING
    scale_factor = 4  

    for i, row in major_farms.iterrows():
        x, y = row.geometry.x, row.geometry.y
        num = i + 1  
        mw = row['total_mw']
        
        dynamic_size = mw * scale_factor
        marker_size = max(dynamic_size, 300) 

        # --- UPDATED: HIGHLIGHT LOGIC ---
        edge_color = 'black'
        edge_width = 1.0
        
        if num == 7:
            edge_color = 'red'
            edge_width = 3.0
        elif num in [19, 20]:
            edge_color = '#00BFFF' # Bright Blue (DeepSkyBlue)
            edge_width = 3.0

        ax.scatter(x, y, color='teal', s=marker_size, 
                   edgecolor=edge_color, linewidth=edge_width, # Applied highlights
                   alpha=0.8, zorder=3, 
                   label=f"{num}. {row['p_name']} ({mw:.0f} MW)")
        
        # [Annotation logic remains exactly the same as your snippet]
        if num in custom_offsets:
            off_x, off_y = custom_offsets[num]
            ax.annotate(str(num), xy=(x, y), xytext=(off_x, off_y),
                        textcoords="offset points", ha='center', va='center',
                        fontsize=12, fontweight='bold', color='black',
                        arrowprops=dict(arrowstyle='-', color='black', lw=1), zorder=5)
        else:
            inner_fs = 11 if marker_size > 400 else 9
            ax.annotate(str(num), xy=(x, y), ha='center', va='center',
                        fontsize=inner_fs, fontweight='bold', color='white', zorder=5)

    # 7. Legend and Formatting
    lgnd = ax.legend(title="Wind Projects (Size ∝ MW)", 
                     loc='center left', 
                     bbox_to_anchor=(1, 0.5), 
                     fontsize=10, frameon=True, facecolor='white', labelspacing=1.4)
    
    # Force legend icons to uniform size
    for handle in lgnd.legend_handles:
        handle.set_sizes([150.0])

    # --- UPDATED: LEGEND BOX LOGIC ---
    # We iterate through the text labels in the legend to find our target numbers
    for text in lgnd.get_texts():
        label_text = text.get_text()
        if label_text.startswith("7. "):
            text.set_bbox(dict(facecolor='none', edgecolor='red', boxstyle='round,pad=0.2', lw=1.5))
        elif label_text.startswith("19. ") or label_text.startswith("20. "):
            text.set_bbox(dict(facecolor='none', edgecolor='#00BFFF', boxstyle='round,pad=0.2', lw=1.5))

    plt.title("Colorado Major Wind Projects\nBubble Size Relative to Rated Capacity (MW)", 
              fontsize=22, fontweight='bold', pad=30)
    
    ax.set_xlim(colorado.total_bounds[0] - 50000, colorado.total_bounds[2] + 50000)
    ax.set_ylim(colorado.total_bounds[1] - 50000, colorado.total_bounds[3] + 50000)
    ax.set_axis_off()

    plt.savefig(OUTPUT_DIR / "Colorado_Wind_Bubble_Map.png", dpi=300, bbox_inches='tight')
    print("Success! Map created with capacity-proportional bubble sizes.")