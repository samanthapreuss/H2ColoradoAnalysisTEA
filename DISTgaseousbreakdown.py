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
def parse_gaseous_csv(data_path, filename="GaseousTruck.csv"):
    file_full_path = data_path / filename
    if not file_full_path.exists():
        print(f"Error: {file_full_path} not found.")
        return []

    # Read the CSV
    df_raw = pd.read_csv(file_full_path)
    
    # Clean headers and fill capacity downwards for block association
    df_raw.columns = df_raw.columns.str.strip()
    df_raw['Capacity'] = df_raw['Capacity'].ffill()
    
    data_blocks = []
    capacities = df_raw['Capacity'].unique()
    
    for cap in capacities:
        # Filter rows for this specific capacity block
        block_df = df_raw[df_raw['Capacity'] == cap]
        
        # Identify the 'Total Cost' row
        total_cost_row = block_df[block_df['Metrics'].str.contains('Total Cost', na=False)]
        
        if not total_cost_row.empty:
            # FIX: Use .values[0] to avoid KeyError: 0
            # Grabbing capital and error metrics from the wide columns
            cap_col = 'Total Capital Investment'
            err_col = 'Standard O&M (less energy cost)'
            
            cap_val = float(total_cost_row[cap_col].values[0]) if cap_col in total_cost_row else 0.0
            std_err = float(total_cost_row[err_col].values[0]) if err_col in total_cost_row else 0.0
            
            # Upstream Categories for Gaseous
            categories = ['GH2 Terminal', 'Compressed H2 Truck-Tube']
            
            # Collect Totals for the Stacked Bar
            cat_totals = {}
            for cat in categories:
                if cat in total_cost_row.columns:
                    cat_totals[cat] = float(total_cost_row[cat].values[0])
                else:
                    cat_totals[cat] = 0.0
            
            net_lcoh = sum(cat_totals.values())

            data_blocks.append({
                'Capacity': cap,
                'Total Capital': cap_val,
                'Standard Error': std_err,
                'Net LCOH': net_lcoh,
                'CatTotals': cat_totals
            })
            
    return data_blocks

data = parse_gaseous_csv(DATA_DIR)

if data:
    # --- 3. GRAPHING (ONE STACKED BAR PER CAPACITY) ---
    # Colors for the components
    colors = {'GH2 Terminal': '#2E5A88', 'Compressed H2 Truck-Tube': '#D97B29'}
    categories = ['GH2 Terminal', 'Compressed H2 Truck-Tube']
    
    fig, ax = plt.subplots(figsize=(12, 8))
    indices = np.arange(len(data))
    bar_width = 0.6
    export_rows = []

    for idx, block in enumerate(data):
        current_bottom = 0
        
        # Build Export Data for CSV
        export_rows.append({
            'Method': f"Gaseous Pathway {int(block['Capacity'])} kg/d",
            'GH2 Terminal': block['CatTotals']['GH2 Terminal'],
            'Compressed H2 Truck-Tube': block['CatTotals']['Compressed H2 Truck-Tube'],
            'Net LCOH': block['Net LCOH'],
            'Total Capital': block['Total Capital'],
            'Capital Standard Error': block['Standard Error']
        })

        # Stack components vertically
        for cat in categories:
            val = block['CatTotals'][cat]
            ax.bar(idx, val, bar_width, bottom=current_bottom, 
                   color=colors[cat], edgecolor='white', zorder=3, 
                   label=cat if idx == 0 else "")
            
            # Add internal labels if the segment is large enough
            if val > 0.05:
                ax.text(idx, current_bottom + (val/2), f'${val:.2f}', 
                        ha='center', va='center', color='white', 
                        fontweight='bold', fontsize=10)
            
            current_bottom += val

        # Add the Pathway Total on top in BLACK
        total_lcoh = block['Net LCOH']
        ax.text(idx, total_lcoh + 0.1, f'Total: ${total_lcoh:.2f}', 
                ha='center', va='bottom', fontsize=12, fontweight='bold', color='black')

    # Final Graph Formatting
    ax.set_title('Gaseous Tube-Trailer Distribution LCOH Component Breakdown', fontsize=16, pad=25)
    ax.set_ylabel('LCOH ($/kg H2)', fontsize=12)
    ax.set_xticks(indices)
    ax.set_xticklabels([f"{int(b['Capacity'])} kg/d" for b in data], fontsize=12, fontweight='bold')
    
    # Buffering and Grid
    ax.set_ylim(0, max([b['Net LCOH'] for b in data]) * 1.3)
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    
    ax.legend(title="Components", loc='upper right')

    # --- 4. EXPORT OUTPUTS ---
    plt.tight_layout()
    # Save Image
    graph_path = OUTPUT_DIR1 / 'gaseousdistribution_stacked_lcoh_final.png'
    plt.savefig(graph_path, dpi=300)
    
    # Save CSV
    df_export = pd.DataFrame(export_rows)
    csv_path = OUTPUT_DIR2 / 'gaseous_distribution_results.csv'
    df_export.to_csv(csv_path, index=False)

    print("-" * 30)
    print(f"SUCCESS!")
    print(f"Graph: {graph_path}")
    print(f"CSV: {csv_path}")
    print("-" * 30)
    
    plt.show()
else:
    print("No data found to process. Please check your GaseousTruck.csv file path.")