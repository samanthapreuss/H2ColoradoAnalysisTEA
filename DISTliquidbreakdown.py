import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR1 = BASE_DIR / "outputs" / "finalize images"
OUTPUT_DIR2 = BASE_DIR / "data" / "script_outputs"

# Ensure directories exist
for d in [OUTPUT_DIR1, OUTPUT_DIR2]:
    d.mkdir(parents=True, exist_ok=True)

# --- 2. DATA PARSING ---
def parse_liquid_csv(data_path, filename="Liquid.csv"):
    file_full_path = data_path / filename
    if not file_full_path.exists():
        print(f"Error: {file_full_path} not found.")
        return []

    df_raw = pd.read_csv(file_full_path)
    df_raw['Capacity'] = df_raw['Capacity'].ffill()
    
    data_blocks = []
    capacities = df_raw['Capacity'].unique()
    
    for cap in capacities:
        block_df = df_raw[df_raw['Capacity'] == cap]
        total_cost_row = block_df[block_df['Metrics'].str.contains('Total Cost', na=False)]
        
        if not total_cost_row.empty:
            cap_val = float(total_cost_row['Total Capital Investment'].values[0])
            std_err = float(total_cost_row['Standard O&M (less energy cost)'].values[0])
            
            # Categories for the stack
            categories = ['Liquefier', 'Terminal', 'Tractor-Trailer']
            
            # We will store the totals for each category to stack them
            cat_totals = {cat: float(total_cost_row[cat].values[0]) for cat in categories}
            net_lcoh = sum(cat_totals.values())

            data_blocks.append({
                'Capacity': cap,
                'Total Capital': cap_val,
                'Standard Error': std_err,
                'Net LCOH': net_lcoh,
                'CatTotals': cat_totals
            })
            
    return data_blocks

data = parse_liquid_csv(DATA_DIR)

if data:
 # --- 3. GRAPHING (STACKED STYLE) ---
    colors = {'Liquefier': '#2E5A88', 'Terminal': '#D97B29', 'Tractor-Trailer': '#4A924A'}
    categories = ['Liquefier', 'Terminal', 'Tractor-Trailer']
    
    fig, ax = plt.subplots(figsize=(13, 8)) # Slightly wider figure
    indices = np.arange(len(data))
    bar_width = 0.6
    export_rows = []

    for idx, block in enumerate(data):
        current_bottom = 0
        
        # Build Export Data
        export_rows.append({
            'Method': f"Liquid Pathway {int(block['Capacity'])} kg/d",
            'Liquefier': block['CatTotals']['Liquefier'],
            'Terminal': block['CatTotals']['Terminal'],
            'Tractor-Trailer': block['CatTotals']['Tractor-Trailer'],
            'Net LCOH': block['Net LCOH'],
            'Total Capital': block['Total Capital'],
            'Capital Standard Error': block['Standard Error']
        })

        for cat in categories:
            val = block['CatTotals'][cat]
            ax.bar(idx, val, bar_width, bottom=current_bottom, 
                   color=colors[cat], edgecolor='white', zorder=3, label=cat if idx == 0 else "")
            
            if val > 0.1:
                ax.text(idx, current_bottom + (val/2), f'${val:.2f}', 
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)
            
            current_bottom += val

        total_lcoh = block['Net LCOH']
        ax.text(idx, total_lcoh + 0.1, f'Total: ${total_lcoh:.2f}', 
                ha='center', va='bottom', fontsize=12, fontweight='bold', color='black')

    # --- UPDATED LEGEND AND LAYOUT ---
    ax.set_title('Liquid Distribution Infrastructure LCOH', fontsize=16, pad=25)
    ax.set_ylabel('LCOH ($/kg H2)', fontsize=12)
    ax.set_xticks(indices)
    ax.set_xticklabels([f"{int(b['Capacity'])} kg/d" for b in data], fontsize=12, fontweight='bold')
    
    ax.set_ylim(0, max([b['Net LCOH'] for b in data]) * 1.3) # Increased buffer for top labels
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    
    # Move legend outside the plot to the right
    ax.legend(title="Components", loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0)

    # Adjust layout to make room for the legend on the right
    plt.tight_layout(rect=[0, 0, 0.85, 1]) 
    
    # --- 4. EXPORT ---
    plt.savefig(OUTPUT_DIR1 / 'liquid_stacked_lcoh.png', dpi=300)
    
    df_export = pd.DataFrame(export_rows)
    csv_path = OUTPUT_DIR2 / 'liquid_distribution_results.csv'
    df_export.to_csv(csv_path, index=False)

    print(f"Stacked graph saved to: {OUTPUT_DIR1}")
    print(f"CSV results saved to: {csv_path}")
    plt.show()