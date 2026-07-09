import pandas as pd
import folium
import numpy as np
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "HydrogenNetworkOptimization"
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "outputs" / "interactive_maps"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# === DYNAMIC CONFIGURATION MATCHING ===
FOOTPRINT_TYPE = 'pipeline' 

OPTIMAL_CSV = DATA_DIR / f'all{FOOTPRINT_TYPE.upper()}_pareto_h2_stations_mapping.csv'
FOOTPRINT_CSV = DATA_DIR / 'Footprint.csv'

SIZE_COLORS = {
    'XS': 'lightgreen', 'S': 'green', 'M': 'orange', 'L': 'red', 'XL': 'darkred'
}

def create_comprehensive_map_by_capacity(target_capacity_kg=118326):
    if not all(p.exists() for p in [OPTIMAL_CSV, FOOTPRINT_CSV]):
        print(f"Error: Missing input files. Ensure you have run the optimization script for {FOOTPRINT_TYPE} first.")
        return

    opt_df = pd.read_csv(OPTIMAL_CSV)
    footprint_df = pd.read_csv(FOOTPRINT_CSV)
    
    # Standardize columns
    for df in [opt_df, footprint_df]:
        df.columns = df.columns.str.strip()

    pareto_col = [col for col in opt_df.columns if col.startswith('Pareto')][0]
    
    # --- AUTOMATIC TARGET SELECTION LOGIC ---
    # Group by the solution ID to analyze unique system metrics per configuration
    summary = opt_df.groupby(pareto_col).agg({
        'Total_System_Capacity_kg': 'first',
        'Address': 'count'  # Counting the number of active rows/stations for this solution
    }).reset_index()
    
    if summary.empty:
        print("Error: No solution configurations found in the dataset.")
        return

    # Calculate absolute difference to the target capacity requested
    summary['capacity_diff'] = (summary['Total_System_Capacity_kg'] - target_capacity_kg).abs()
    
    # Sort first by closest capacity match, then break ties by the fewest number of stations
    summary = summary.sort_values(by=['capacity_diff', 'Address'], ascending=[True, True])
    
    # Extract our winner
    best_match = summary.iloc[0]
    target_solution_id = best_match[pareto_col]
    matched_capacity = best_match['Total_System_Capacity_kg']
    matched_stations = best_match['Address']

    print(f"\n🎯 Target Capacity Request: {target_capacity_kg:,} kg")
    print(f"✅ Best Pareto Match Found: {target_solution_id}")
    print(f"📊 Match Details: {matched_capacity:,} kg across {matched_stations} stations\n")

    # Filter the primary mapping data down to the selected solution choice
    map_data = opt_df[opt_df[pareto_col] == target_solution_id].copy()

    m = folium.Map(location=[39.0, -105.5], zoom_start=7, tiles='CartoDB positron')

    # Marker Loop
    for _, row in map_data.iterrows():
        station_size = row.get('Station_Size', 'S')
        marker_color = SIZE_COLORS.get(station_size, 'blue')
        price_val = row.get('Formatted_Price', f"${row.get('Price', 0):,.2f}")
        capacity_val = f"{int(row['Station_Capacity_kg']):,}" if pd.notnull(row.get('Station_Capacity_kg')) else "N/A"
        utilization = f"{row.get('Utilization_Rate', 'N/A')}"
        trucks_served = f"{int(row.get('Total_Trucks_Served', 0)):,}"
        url_col = row.get('Property_URL', '#')
        
        fleet_raw = str(row.get('Fleet_Breakdown', ''))
        fleet_items = [
            item.strip().replace("trucks", "heavy duty vehicles") 
            for item in fleet_raw.split('|')
        ] if fleet_raw and fleet_raw != 'nan' else []
        fleet_html_list = "".join([f"<li style='margin-bottom:4px;'>{item}</li>" for item in fleet_items])

        popup_html = f"""
        <div style="width:340px; font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; font-size: 13px; color: #333;">
            <h3 style="margin: 0 0 10px 0; color: #2c3e50; font-size: 14px; border-bottom: 2px solid {marker_color}; padding-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px;">
                {FOOTPRINT_TYPE} Hub Details ({target_solution_id})
            </h3>
            
            <table style="width: 100%; border-collapse: collapse; margin-bottom: 10px;">
                <tr><td style="padding: 4px 0; vertical-align: top; width: 55%;"><b>Address</b></td><td style="padding: 4px 0;">{row['Address']}</td></tr>
                <tr style="background-color: #f8f9fa;"><td style="padding: 4px 0;"><b>Land Price</b></td><td style="padding: 4px 0; color: #27ae60; font-weight: bold;">{price_val}</td></tr>
                <tr><td style="padding: 4px 0;"><b>Station Size</b></td><td style="padding: 4px 0;">{station_size} ({capacity_val} kg)</td></tr>
                <tr style="background-color: #f8f9fa;"><td style="padding: 4px 0;"><b>Utilization</b></td><td style="padding: 4px 0;">{utilization}</td></tr>
                <tr><td style="padding: 4px 0;"><b>Heavy Duty Vehicles Served</b></td><td style="padding: 4px 0;">{trucks_served}</td></tr>
            </table>

            <div style="border-top: 1px solid #ddd; padding-top: 10px;">
                <b style="display: block; margin-bottom: 5px;">Fleets Served:</b>
                <ul style="margin: 0; padding-left: 18px; color: #555; font-size: 12px;">
                    {fleet_html_list if fleet_html_list else "<li>No commercial fleets assigned directly</li>"}
                </ul>
            </div>

            <div style="margin-top: 15px; text-align: center;">
                <a href="{url_col}" target="_blank" 
                   style="display: inline-block; padding: 8px 16px; background-color: {marker_color}; color: white; text-decoration: none; border-radius: 4px; font-weight: bold; font-size: 11px; letter-spacing: 0.5px;">
                    VIEW PROPERTY LISTING
                </a>
            </div>
        </div>
        """

        folium.Marker(
            location=[row['Latitude'], row['Longitude']],
            popup=folium.Popup(popup_html, max_width=380),
            tooltip=f"Hub ({station_size}): {row['Address']}",
            icon=folium.Icon(color=marker_color, icon='gas-pump', prefix='fa')
        ).add_to(m)

    # Output map name now explicitly documents the exact capacity setup generated
    map_output = RESULTS_DIR / f'{FOOTPRINT_TYPE}_network_map_{int(matched_capacity)}kg_{target_solution_id}.html'
    m.save(map_output)
    print(f"Map successfully saved to: {map_output}")

if __name__ == "__main__":
    # Define your exact desired structural capacity threshold in kilograms here
    create_comprehensive_map_by_capacity(target_capacity_kg=118326)