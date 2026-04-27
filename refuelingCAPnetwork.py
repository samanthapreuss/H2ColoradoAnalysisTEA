import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_Analysis"
DATA_DIR = BASE_DIR / "data"                                # Folder for refuelingtea.csv files
DATA2_DIR = BASE_DIR / "scripts" / "DONE" / "outputs"        # Folder for balanced_sites_details.csv files
RESULTS_DIR = BASE_DIR / "outputs" / "fleet_analysis"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Define the pairs across directories
scenarios = [
    {
        "name": "Liquid",
        "sites": DATA2_DIR / "liquidbalanced_sites_details.csv",
        "specs": DATA_DIR / "liquidrefuelingtea.csv"
    },
    {
        "name": "Pipeline",
        "sites": DATA2_DIR / "pipelinebalanced_sites_details.csv",
        "specs": DATA_DIR / "pipelinerefuelingtea.csv"
    },
    {
        "name": "Gaseous",
        "sites": DATA2_DIR / "gaseousbalanced_sites_details.csv",
        "specs": DATA_DIR / "gaseousrefuelingtea.csv"
    }
]

def generate_total_capex_by_size():
    all_capex_data = []
    size_order = ['XS', 'S', 'M', 'L', 'XL']
    
    for sc in scenarios:
        sites_path = sc['sites']
        specs_path = sc['specs']
        
        if not (sites_path.exists() and specs_path.exists()):
            print(f"Skipping {sc['name']}: Paired files not found.")
            continue
            
        # Load and clean headers
        sites_df = pd.read_csv(sites_path)
        specs_df = pd.read_csv(specs_path)
        sites_df.columns = sites_df.columns.str.strip()
        specs_df.columns = specs_df.columns.str.strip()
        
        # Merge individual sites with their size-specific absolute investment
        merged = sites_df.merge(
            specs_df[['T-Shirt Size', 'Total Capital Investment ($)']],
            left_on='Station_Size',
            right_on='T-Shirt Size',
            how='left'
        )
        
        # Sum Total CAPEX by size for this specific method
        capex_by_size = merged.groupby('Station_Size')['Total Capital Investment ($)'].sum().reset_index()
        capex_by_size['Method'] = sc['name']
        all_capex_data.append(capex_by_size)
        
    if not all_capex_data:
        print("No paired data found. Please check your folder paths.")
        return
        
    # Combine results from all methods
    master_capex = pd.concat(all_capex_data)
    
    # Pivot for grouped plotting (X-Axis = Size, Bars = Method)
    pivot_df = master_capex.pivot(index='Station_Size', columns='Method', values='Total Capital Investment ($)')
    pivot_df = pivot_df.reindex(size_order)

    # --- 2. PLOTTING ---
    fig, ax = plt.subplots(figsize=(14, 8))
    
    # Grouped Bar Plot
    pivot_df.plot(kind='bar', ax=ax, width=0.8, edgecolor='white', color=['#2E86C1', '#F39C12', '#27AE60'])
    
    # Formatting
    ax.set_title('Total Network CAPEX Investment by Station Size\n(Sum of Absolute Dollars per Size Category)', fontsize=15, pad=30, fontweight='bold')
    ax.set_ylabel('Total Investment ($)', fontsize=12)
    ax.set_xlabel('Station Size', fontsize=12)
    ax.set_ylim(0, pivot_df.max().max() * 1.25) # Headroom for $M labels
    ax.legend(title="Refueling Method", bbox_to_anchor=(1.02, 1), loc='upper left')
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    plt.xticks(rotation=0)

    # Add Value Labels in Millions ($M)
    for p in ax.patches:
        if p.get_height() > 0:
            ax.annotate(f'${p.get_height()/1e6:.1f}M', 
                        (p.get_x() + p.get_width() / 2., p.get_height()), 
                        ha='center', va='center', 
                        xytext=(0, 10), 
                        textcoords='offset points',
                        fontsize=9, fontweight='bold')

    # Ensure no cutoffs
    plt.tight_layout(rect=[0, 0, 0.85, 0.95])
    
    output_path = RESULTS_DIR / "total_capex_by_size_comparison.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    
    # Save raw sums to CSV for auditing
    master_capex.to_csv(RESULTS_DIR / "total_capex_by_size_summary.csv", index=False)
    print(f"Total CAPEX analysis complete. Chart saved to: {output_path}")

if __name__ == "__main__":
    generate_total_capex_by_size()