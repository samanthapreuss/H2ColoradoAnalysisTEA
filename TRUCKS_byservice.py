import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
from pathlib import Path
import os
import numpy as np

# --- CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
INPUT_FILE_PATH = BASE_DIR/ 'data' / 'COcaptive_catex.csv'
OUTPUT_DIR1 = BASE_DIR/ 'outputs'/ 'finalize images'
OUTPUT_DIR2 = BASE_DIR / 'data' / 'script_outputs'
os.makedirs(OUTPUT_DIR1, exist_ok=True)

COLOR_MAP = {
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

TARGET_CATEGORIES = list(COLOR_MAP.keys())

def create_donut_chart(data, title, output_path, label_col, value_col):
    data = data[data[value_col] > 0].sort_values(by=value_col, ascending=False).copy()
    if data.empty:
        return

    chart_colors = [COLOR_MAP.get(label, 'gray') for label in data[label_col]]
    display_data = data.copy()
    display_data[label_col] = display_data[label_col].str.title()

    # Wider figure to accommodate the tall vertical legend on the right
    fig, ax = plt.subplots(figsize=(15, 10)) 
    
    wedges, texts, autotexts = ax.pie(
        display_data[value_col], 
        autopct='%1.1f%%', 
        startangle=140, 
        pctdistance=0.85,
        colors=chart_colors,
        wedgeprops={'width': 0.4, 'edgecolor': 'w'}
    )

    # White font with black outline for the percentages
    outline = [path_effects.withStroke(linewidth=1, foreground='black')]
    for autotext in autotexts:
        autotext.set_color('white')
        autotext.set_weight('bold')
        autotext.set_size(12)
        autotext.set_path_effects(outline)
    
    legend_labels = [f"{row[label_col]}: {int(row[value_col]):,}" for _, row in display_data.iterrows()]
    
    # LEGEND: A tall, thin vertical rectangle on the right
    ax.legend(
        wedges, 
        legend_labels, 
        title="Fleets/Trucks per Sector", 
        loc="center left", 
        bbox_to_anchor=(1.05, 0.5), # Positions it to the right of the chart
        ncol=1,                     # Single column makes it tall and thin
        fontsize=12,
        frameon=True,
        fancybox=False,             # Sharp rectangular corners
        edgecolor='black',
        borderpad=1.5,              # Increases vertical "length"
        labelspacing=1.2            # Adds extra space between rows to make it taller
    )

    plt.title(title, fontsize=22, pad=30)
    
    plt.savefig(output_path, bbox_inches='tight', dpi=300) 
    plt.close()

# --- MAIN EXECUTION ---
# --- MAIN EXECUTION ---
if __name__ == "__main__":
    try:
        df = pd.read_csv(INPUT_FILE_PATH)
        df.columns = [col.strip() for col in df.columns]

        df['Trucks'] = pd.to_numeric(df['Trucks'], errors='coerce').fillna(0)
        df_filtered = df[df['Category'].isin(TARGET_CATEGORIES)].copy()

        # 1. Generate Summary Data
        fleet_data = df_filtered.groupby('Category')['Fleet_Name'].nunique().reset_index()
        fleet_data.columns = ['Category', 'Fleet_Count']

        truck_data = df_filtered.groupby('Category')['Trucks'].sum().reset_index()
        truck_data.columns = ['Category', 'Total_Trucks']

        # 2. Merge and Save CSV Summary
        # Merge both datasets on Category
        summary_df = pd.merge(fleet_data, truck_data, on='Category')
        
        # Optional: Add percentage columns
        summary_df['Fleet_Percentage'] = (summary_df['Fleet_Count'] / summary_df['Fleet_Count'].sum() * 100).round(2)
        summary_df['Truck_Percentage'] = (summary_df['Total_Trucks'] / summary_df['Total_Trucks'].sum() * 100).round(2)
        
        # Save to the outputs directory
        csv_path = OUTPUT_DIR2 / 'co_captive_sector_summary.csv'
        summary_df.to_csv(csv_path, index=False)

        # 3. Create Charts (Existing Logic)
        create_donut_chart(
            fleet_data, 
            "Number of Fleets (Companies) per Sector in Colorado", 
            OUTPUT_DIR1 / 'fleets_by_category.png',
            'Category', 'Fleet_Count'
        )

        create_donut_chart(
            truck_data, 
            "Total Truck Distribution per Sector in CO", 
            OUTPUT_DIR1 / 'trucks_by_category.png',
            'Category', 'Total_Trucks'
        )

        print(f"Success!")
        print(f"Summary CSV saved to: {csv_path}")
        print(f"Charts saved in: {OUTPUT_DIR1}")

    except Exception as e:
        print(f"An error occurred: {e}")