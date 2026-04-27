import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR2 = BASE_DIR / "data" / "script_outputs"
RESULTS_DIR = BASE_DIR / "outputs" / "finalize images"

# Ensure the results directory exists
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Define file names
input_filenames = {
    
        'Gaseous': 'final_gasbalanced_sites_details.csv',
        'Liquid': 'final_liquidbalanced_sites_details.csv',
        'Pipeline': 'finalpipelinebalanced_sites_details.csv'
}

size_mapping = {
    'XS': 1000,
    'S': 2000,
    'M': 5000,
    'L': 10000,
    'XL': 20000
}

summary_data = []

# --- 2. PROCESSING ---
for network_type, filename in input_filenames.items():
    # Construct the full path to the file in DATA_DIR2
    file_path = DATA_DIR2 / filename
    
    if file_path.exists():
        df = pd.read_csv(file_path)
        
        # Data Cleaning & Mapping
        df['Price'] = pd.to_numeric(df['Price'].astype(str).str.replace('[\$,]', '', regex=True), errors='coerce')
        df['Station_Capacity'] = df['Station_Size'].map(size_mapping)
        
        # Metrics Calculation
        total_price = df['Price'].sum()
        total_daily_demand = df['Daily_Demand_kg'].sum()
        total_capacity = df['Station_Capacity'].sum()
        
        summary_data.append({
            'Network_Type': network_type,
            'Station_Count': len(df),
            'Total_Price': total_price,
            'Average_Price': df['Price'].mean(),
            'Std_Error_Price': df['Price'].sem(),
            'Total_Daily_Demand': total_daily_demand,
            'Total_Station_Capacity': total_capacity,
            'Utilization_Rate': total_daily_demand / total_capacity if total_capacity > 0 else 0,
            'Total_Trucks_Served': df['Total_Trucks_Served'].sum()
        })
        print(f"Successfully processed: {filename}")
    else:
        print(f"Warning: Could not find {filename} in {DATA_DIR2}")

# --- 3. OUTPUT GENERATION ---
if summary_data:
    output_df = pd.DataFrame(summary_data)
    
    # Save CSV to RESULTS_DIR (Note: changed to your specific filename request)
    csv_output_path = DATA_DIR2 / 'allnetworks_summary_output.csv'
    output_df.to_csv(csv_output_path, index=False)
    
   # --- 4. GRAPHING (UPDATED WITH BAR LABELS) ---
    labels_with_totals = [
        f"{row['Network_Type']}\n(Cap: {row['Total_Station_Capacity']:,.0f} kg)" 
        for _, row in output_df.iterrows()
    ]
    
    x = np.arange(len(labels_with_totals))
    width = 0.25 

    fig, ax = plt.subplots(figsize=(14, 8))

    # Plotting the three metrics
    rects1 = ax.bar(x - width, output_df['Station_Count'], width, label='Stations Built', color="#34d0db")
    rects2 = ax.bar(x, output_df['Total_Price'] / 1e6, width, label='Total Price ($10^6$)', color="#22a037")
    rects3 = ax.bar(x + width, output_df['Total_Trucks_Served'] / 1e3, width, label='Trucks Served ($10^3$)', color="#312ecc")

    # Add the text labels on top of the bars
    # fmt='%.1f' rounds to 1 decimal place; padding=3 moves text slightly above the bar
    ax.bar_label(rects1, padding=3, fmt='%.0f')
    ax.bar_label(rects2, padding=3, fmt='%.1f')
    ax.bar_label(rects3, padding=3, fmt='%.1f')

    # Formatting
    ax.set_ylabel('Scaled Values', fontsize=12)
    ax.set_title('Liquid, Gaseous Tube Trailer, and Pipeline Hydrogen Refueling Network Comparison', fontweight='bold', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(labels_with_totals) 
    ax.legend()
    
    # Increase the top margin slightly so labels don't get cut off
    ax.set_ylim(0, ax.get_ylim()[1] * 1.1)
    ax.grid(axis='y', linestyle='--', alpha=0.4)

    # Save Graph to RESULTS_DIR
    plt.tight_layout()
    graph_output_path = RESULTS_DIR / 'network_comparison_graph.png'
    plt.savefig(graph_output_path)
    
    print(f"Results saved to: {RESULTS_DIR}")
    plt.show()