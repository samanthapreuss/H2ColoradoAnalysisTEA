import pandas as pd
import folium
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
DATA_DIR2 = BASE_DIR / "data" / "script_outputs"
RESULTS_DIR = BASE_DIR / "outputs" / "interactive_maps"

OPTIMAL_CSV = DATA_DIR2 / 'finalpipelinebalanced_sites_details.csv'
MASTER_SITES_CSV = DATA_DIR / 'geocoded_candidate_sites.csv'
FOOTPRINT_CSV = DATA_DIR / 'Footprint.csv'
MAP_OUTPUT = RESULTS_DIR / 'pipeline_hydrogen_network_map.html'


SIZE_COLORS = {
    'XS': 'lightgreen', 'S': 'green', 'M': 'orange', 'L': 'red', 'XL': 'darkred'
}

def create_comprehensive_map():
    if not all(p.exists() for p in [OPTIMAL_CSV, MASTER_SITES_CSV, FOOTPRINT_CSV]):
        print("Error: Missing input files.")
        return

    opt_df = pd.read_csv(OPTIMAL_CSV)
    master_df = pd.read_csv(MASTER_SITES_CSV)
    footprint_df = pd.read_csv(FOOTPRINT_CSV)
    
    # Standardize columns
    for df in [opt_df, master_df, footprint_df]:
        df.columns = df.columns.str.strip()

    # Merge Data
    map_data = pd.merge(opt_df, master_df[['Address', 'Latitude', 'Longitude', 'Property URL']], on='Address', how='left')
    map_data = pd.merge(map_data, footprint_df[['T-Shirt Size', 'Capacity (kilograms)']], left_on='Station_Size', right_on='T-Shirt Size', how='left')

    m = folium.Map(location=[39.0, -105.5], zoom_start=7, tiles='CartoDB positron')

    # Marker Loop
    for _, row in map_data.iterrows():
        marker_color = SIZE_COLORS.get(row['Station_Size'], 'blue')

        # Formatting Land Price
        try:
            raw_price = str(row['Price']).replace('$', '').replace(',', '').strip()
            formatted_price = f"${float(raw_price):,.0f}"
        except:
            formatted_price = row['Price']

        # Formatting Capacity and Utilization
        capacity_val = f"{int(row['Capacity (kilograms)']):,}" if pd.notnull(row['Capacity (kilograms)']) else "N/A"
        utilization = f"{row['Utilization_Rate']}"
        
        # Terminology Swap: "trucks" -> "heavy duty vehicles"
        fleet_raw = str(row['Fleet_Breakdown'])
        fleet_items = [
            item.strip().replace("trucks", "heavy duty vehicles") 
            for item in fleet_raw.split('|')
        ]
        fleet_html_list = "".join([f"<li style='margin-bottom:4px;'>{item}</li>" for item in fleet_items])

        popup_html = f"""
        <div style="width:340px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #333;">
            <h3 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 16px; border-bottom: 2px solid {marker_color}; padding-bottom: 5px;">
                Refueling Hub Details
            </h3>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                <tr><td style="padding: 4px 0; vertical-align: top; width: 60%;"><b>Address</b></td><td style="padding: 4px 0;">{row['Address']}</td></tr>
                <tr style="background-color: #f8f9fa;"><td style="padding: 4px 0;"><b>Land Price</b></td><td style="padding: 4px 0; color: #27ae60; font-weight: bold;">{formatted_price}</td></tr>
                <tr><td style="padding: 4px 0;"><b>Station Size</b></td><td style="padding: 4px 0;">{row['Station_Size']} ({capacity_val} kg)</td></tr>
                <tr style="background-color: #f8f9fa;"><td style="padding: 4px 0;"><b>Utilization</b></td><td style="padding: 4px 0;">{utilization}</td></tr>
                <tr><td style="padding: 4px 0;"><b>Heavy Duty Vehicles in 10 mile radius</b></td><td style="padding: 4px 0;">{row['Total_Trucks_Served']}</td></tr>
            </table>

            <div style="border-top: 1px solid #ddd; padding-top: 10px;">
                <b style="display: block; margin-bottom: 5px;">Fleets Served:</b>
                <ul style="margin: 0; padding-left: 18px; color: #555; font-size: 12px;">
                    {fleet_html_list}
                </ul>
            </div>

            <div style="margin-top: 15px; text-align: center;">
                <a href="{row['Property URL']}" target="_blank" 
                   style="display: inline-block; padding: 8px 16px; background-color: {marker_color}; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;">
                   VIEW LISTING
                </a>
            </div>
        </div>
        """

        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=380),
            tooltip=f"Hub: {row['Address']}",
            icon=folium.Icon(color=marker_color, icon='gas-pump', prefix='fa')
        ).add_to(m)

    m.save(MAP_OUTPUT)
    print(f"Map updated with 'Land Price' label: {MAP_OUTPUT}")

if __name__ == "__main__":
    create_comprehensive_map()