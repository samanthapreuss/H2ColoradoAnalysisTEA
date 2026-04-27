import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_Analysis"
INPUT_DIR = BASE_DIR / "outputs" / "fleet_analysis"
FINAL_OUTPUT_DIR = BASE_DIR / "outputs" / "fleet_analysis"
FINAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# List of the summary files created from each delivery method
files = {
    "Liquid": INPUT_DIR / "liquid_upstream_fleet_summary.csv",
    "Gaseous": INPUT_DIR / "gaseous_upstream_fleet_summary.csv",
    "Pipeline": INPUT_DIR / "pipeline_upstream_fleet_summary.csv"
}

def generate_method_comparison_chart():
    summary_data = []
    
    # 2. LOAD AND STACK DATA
    for method, path in files.items():
        if path.exists():
            df = pd.read_csv(path)
            # Map the CSV columns to a consistent plotting format
            stats = {
                'Method': method,
                'Capital': df['Capital'].iloc[0],
                'OM': df['OM'].iloc[0],
                'Energy': df['Energy'].iloc[0],
                'Total': df['Total'].iloc[0],
                'SE': df['SE'].iloc[0]
            }
            summary_data.append(stats)
        else:
            print(f"Skipping {method}: File not found at {path}")

    if not summary_data:
        print("Error: No summary CSV files found. Run the liquid, gaseous, and pipeline scripts first.")
        return

    df_plot = pd.DataFrame(summary_data)

    # 3. PLOTTING
    fig, ax = plt.subplots(figsize=(12, 8))
    
    methods = df_plot['Method']
    cap = df_plot['Capital']
    om = df_plot['OM']
    energy = df_plot['Energy']
    se = df_plot['SE']
    total = df_plot['Total']

    # Draw Stacked Bars
    ax.bar(methods, cap, label='Capital', color='#2E86C1', width=0.5)
    ax.bar(methods, om, bottom=cap, label='O&M', color='#F39C12', width=0.5)
    ax.bar(methods, energy, bottom=cap+om, label='Energy/Fuel', color='#27AE60', width=0.5)

    # Add Standard Error Bars (Precision of the fleet average)
    ax.errorbar(methods, total, yerr=se, fmt='none', ecolor='black', capsize=10, elinewidth=2, label='Std Error')

    # Add Labels: Percentages inside and Totals on top
    for i in range(len(methods)):
        tot = total.iloc[i]
        
        # Internal Percentage contribution labels
        def add_pct(val, bottom):
            if tot > 0:
                pct = (val / tot) * 100
                if pct > 4: # Prevent overlapping in very small segments
                    ax.text(i, bottom + (val/2), f'{pct:.1f}%', 
                            ha='center', va='center', color='white', 
                            fontsize=10, fontweight='bold')

        add_pct(cap.iloc[i], 0)
        add_pct(om.iloc[i], cap.iloc[i])
        add_pct(energy.iloc[i], cap.iloc[i] + om.iloc[i])
        
        # Display Total Average and SE on top
        ax.text(i, tot + se.iloc[i] + 0.1, f'Avg: ${tot:.2f}\n±{se.iloc[i]:.3f}', 
                ha='center', fontweight='bold', fontsize=10, bbox=dict(facecolor='white', alpha=0.6))

    # Formatting Fixes
    ax.set_title('Upstream Delivery LCOH: Comparative Fleet Analysis', fontsize=15, fontweight='bold', pad=30)
    ax.set_ylabel('Cost ($/kg)', fontsize=12)
    ax.set_ylim(0, total.max() * 1.45) # Leave headroom for labels
    ax.legend(bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout(rect=[0, 0, 0.85, 1]) # Ensure legend is not cutoff
    
    output_path = FINAL_OUTPUT_DIR / "method_comparison_summary.png"
    plt.savefig(output_path, dpi=300)
    
    print("-" * 40)
    print(f"COMPARISON COMPLETE")
    print(f"Chart saved to: {output_path}")
    print("-" * 40)

if __name__ == "__main__":
    generate_method_comparison_chart()