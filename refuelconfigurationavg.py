import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"                                
DATA2_DIR = DATA_DIR / "script_outputs"                      
RESULTS_DIR = BASE_DIR / "outputs" / "finalize images"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

scenarios = [
    {
        "name": "Gaseous",
        "sites": DATA2_DIR / "final_gasbalanced_sites_details.csv",
        "specs": DATA_DIR / "gaseousrefuelingtea.csv"
    },
    {
        "name": "Liquid",
        "sites": DATA2_DIR / "final_liquidbalanced_sites_details.csv",
        "specs": DATA_DIR / "liquidrefuelingtea.csv"
    },
    {
        "name": "Pipeline",
        "sites": DATA2_DIR / "finalpipelinebalanced_sites_details.csv",
        "specs": DATA_DIR / "pipelinerefuelingtea.csv"
    }
]

def generate_network_fleet_analysis():
    summary_results = []
    
    print("--- Starting Network Analysis ---")
    for sc in scenarios:
        sites_path = sc['sites']
        specs_path = sc['specs']
        
        if not sites_path.exists() or not specs_path.exists():
            print(f"Skipping {sc['name']}: Files not found.")
            continue
            
        print(f"Processing {sc['name']} pathway...")
        
        sites_df = pd.read_csv(sites_path)
        specs_df = pd.read_csv(specs_path)
        
        sites_df.columns = sites_df.columns.str.strip()
        specs_df.columns = specs_df.columns.str.strip()
        
        # --- ROBUST COLUMN DETECTION ---
        capex_col = None
        target_name = 'Total Capital Investment ($)'
        
        if target_name in specs_df.columns:
            capex_col = target_name
        else:
            for col in specs_df.columns:
                if 'total' in col.lower() and 'capital' in col.lower():
                    capex_col = col
                    break
        
        if capex_col is None:
            print(f"!! Error: Could not find Capital Investment column in {sc['name']} specs.")
            continue

        cols_to_use = ['T-Shirt Size', 'Capital ($/kg)', 'O&M less energy ($/kg)', 
                       'Energy/Fuel ($/kg)', 'Total Cost ($/kg)', capex_col]
        
        merged = sites_df.merge(
            specs_df[cols_to_use],
            left_on='Station_Size',
            right_on='T-Shirt Size',
            how='left'
        )
        
        n = len(merged)
        if n == 0:
            print(f"!! No matches found for {sc['name']}")
            continue

        # RENAMED: Key changed to 'Total Capital' for CSV export
        stats = {
            'Method': sc['name'],
            'LCOH_Capital': merged['Capital ($/kg)'].mean(),
            'LCOH_OM': merged['O&M less energy ($/kg)'].mean(),
            'LCOH_Energy': merged['Energy/Fuel ($/kg)'].mean(),
            'LCOH_Total': merged['Total Cost ($/kg)'].mean(),
            'LCOH_SE': merged['Total Cost ($/kg)'].std() / np.sqrt(n),
            'Total Capital': merged[capex_col].sum(), 
            'Station_Count': n
        }
        summary_results.append(stats)
        
    if not summary_results:
        print("\nERROR: No data was successfully processed.")
        return

    df_plot = pd.DataFrame(summary_results)
    # This will now contain a column named 'Total Capital'
    df_plot.to_csv(DATA2_DIR / "network_refueling_summary.csv", index=False)

    # --- 2. PLOT 1: LCOH BREAKDOWN (AVERAGE) ---
    fig1, ax1 = plt.subplots(figsize=(13, 8))
    colors = {'Cap': '#2E86C1', 'OM': '#F39C12', 'Eng': '#27AE60'}
    methods = df_plot['Method']
    
    ax1.bar(methods, df_plot['LCOH_Capital'], label='Capital', color=colors['Cap'], width=0.6, zorder=3)
    ax1.bar(methods, df_plot['LCOH_OM'], bottom=df_plot['LCOH_Capital'], label='O&M (Fixed)', color=colors['OM'], width=0.6, zorder=3)
    ax1.bar(methods, df_plot['LCOH_Energy'], bottom=df_plot['LCOH_Capital']+df_plot['LCOH_OM'], label='Energy/Fuel', color=colors['Eng'], width=0.6, zorder=3)
    
    ax1.errorbar(methods, df_plot['LCOH_Total'], yerr=df_plot['LCOH_SE'], fmt='none', ecolor='black', capsize=10, elinewidth=2, zorder=4)

    for i in range(len(methods)):
        tot = df_plot['LCOH_Total'].iloc[i]
        c, o, e = df_plot['LCOH_Capital'].iloc[i], df_plot['LCOH_OM'].iloc[i], df_plot['LCOH_Energy'].iloc[i]
        
        for val, bottom in [(c, 0), (o, c), (e, c+o)]:
            if (val/tot) > 0.04:
                ax1.text(i, bottom + (val/2), f'{(val/tot)*100:.1f}%', 
                        ha='center', va='center', color='white', fontweight='bold', fontsize=10)
        
        ax1.text(i, tot + df_plot['LCOH_SE'].iloc[i] + 0.15, f'Avg: ${tot:.2f}\n±{df_plot["LCOH_SE"].iloc[i]:.3f}', 
                 ha='center', fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, boxstyle='round'))

    ax1.set_title('Refueling Network Average Refueling LCOH', fontsize=16, fontweight='bold', pad=35)
    ax1.set_ylabel('LCOH ($/kg H2)')
    ax1.set_ylim(0, df_plot['LCOH_Total'].max() * 1.5)
    ax1.legend(bbox_to_anchor=(1.02, 1), loc='upper left')
    ax1.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
    
    fig1.tight_layout(rect=[0, 0, 0.85, 0.95])
    fig1.savefig(RESULTS_DIR / "refueling_network_lcoh_breakdown.png", dpi=300)

    # --- 3. PLOT 2: TOTAL NETWORK CAPITAL INVESTMENT ($M) ---
    fig2, ax2 = plt.subplots(figsize=(11, 8))
    
    # Referenced renamed key 'Total Capital' for plotting
    network_capex_m = df_plot['Total Capital'] / 1e6
    bar_colors = ["#48a166", "#2752ae", '#c0392b'] 

    ax2.bar(methods, network_capex_m, color=bar_colors, alpha=0.8, width=0.5, edgecolor='black', zorder=3)

    for i, val in enumerate(network_capex_m):
        count = df_plot['Station_Count'].iloc[i]
        ax2.text(i, val + (val * 0.02), f'${val:,.1f}M\n({int(count)} Stations)', 
                 ha='center', va='bottom', fontweight='bold', fontsize=12)

    ax2.set_title('Total Refueling Network Capital Investment: Build-out Cost', fontsize=16, fontweight='bold', pad=25)
    ax2.set_ylabel('Total Capital ($ Millions)', fontsize=12)
    ax2.set_ylim(0, network_capex_m.max() * 1.25)
    ax2.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)

    fig2.tight_layout()
    fig2.savefig(RESULTS_DIR / "refueling_network_total_capital_comparison.png", dpi=300)
    
    print("-" * 45)
    print(f"SUCCESS: Analysis complete. CSV exported with 'Total Capital' column.")
    print("-" * 45)
    plt.show()

if __name__ == "__main__":
    generate_network_fleet_analysis()