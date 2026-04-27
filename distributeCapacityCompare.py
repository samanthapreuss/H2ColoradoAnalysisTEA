import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "script_outputs"
OUTPUT_DIR1 = BASE_DIR / "outputs" / "finalize images"

OUTPUT_DIR1.mkdir(parents=True, exist_ok=True)

# 2. FILE CONFIGURATION
result_files = {
    "Liquid Pathway": RESULTS_DIR / "liquid_distribution_results.csv",
    "Gaseous Truck": RESULTS_DIR / "gaseous_distribution_results.csv",
    "Pipeline": RESULTS_DIR / "pipeline_distribution_results.csv"
}

def load_standardized_results():
    all_data = []
    for tech, path in result_files.items():
        if path.exists():
            df = pd.read_csv(path)
            df.columns = df.columns.str.strip() # Clean column names
            
            # Extract capacity from "Method" column
            df['Capacity'] = df['Method'].str.extract(r'(\d+)').astype(int)
            
            for _, row in df.iterrows():
                all_data.append({
                    "Capacity": row['Capacity'],
                    "Technology": tech,
                    "LCOH": row['Net LCOH'],
                    "Total Capital": row['Total Capital'] # Added this
                })
        else:
            print(f"Warning: Results for {tech} not found at {path}.")
    return pd.DataFrame(all_data)

# --- 3. PROCESSING ---
df_master = load_standardized_results()

if not df_master.empty:
    # Custom colors
    colors = ["#27ae49", "#4860a1", '#c0392b'] 
    
    # --- PLOT 1: LCOH COMPARISON ---
    plot_lcoh = df_master.pivot(index="Capacity", columns="Technology", values="LCOH").sort_index()
    fig1, ax1 = plt.subplots(figsize=(14, 8))
    
    plot_lcoh.plot(kind='bar', ax=ax1, width=0.8, color=colors, edgecolor='white', zorder=3)
    
    for p in ax1.patches:
        height = p.get_height()
        if height > 0:
            ax1.annotate(f'${height:.2f}', (p.get_x() + p.get_width() / 2., height),
                        ha='center', va='bottom', xytext=(0, 5), textcoords='offset points',
                        fontsize=10, fontweight='bold')

    ax1.set_title("Hydrogen Distribution Infrastructure: Pathway LCOH Comparison", fontsize=16, fontweight='bold', pad=30)
    ax1.set_ylabel("Total LCOH ($/kg H2)", fontsize=12, fontweight='bold')
    ax1.set_xlabel("System Capacity (kg/day)", fontsize=12, fontweight='bold')
    ax1.set_ylim(0, plot_lcoh.max().max() * 1.25)
    ax1.legend(title="Distribution Pathway", bbox_to_anchor=(1.02, 1), loc='upper left')
    ax1.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    plt.xticks(rotation=0)
    fig1.tight_layout(rect=[0, 0, 0.85, 1])
    fig1.savefig(OUTPUT_DIR1 / 'Distribution_LCOH_comparison.png', dpi=300)

    # --- PLOT 2: TOTAL CAPITAL COMPARISON ---
    # Create pivot for Capital
    plot_cap = df_master.pivot(index="Capacity", columns="Technology", values="Total Capital").sort_index()
    
    # Convert to Millions for readability
    plot_cap_m = plot_cap / 1e6
    
    fig2, ax2 = plt.subplots(figsize=(14, 8))
    plot_cap_m.plot(kind='bar', ax=ax2, width=0.8, color=colors, edgecolor='white', zorder=3)
    
    for p in ax2.patches:
        val = p.get_height()
        if val > 0:
            ax2.annotate(f'${val:.1f}M', (p.get_x() + p.get_width() / 2., val),
                        ha='center', va='bottom', xytext=(0, 5), textcoords='offset points',
                        fontsize=7, fontweight='bold')

    ax2.set_title("Hydrogen Distribution Infrastructure: Total Capital Investment", fontsize=16, fontweight='bold', pad=30)
    ax2.set_ylabel("Total Capital Cost ($ Millions)", fontsize=12, fontweight='bold')
    ax2.set_xlabel("System Capacity (kg/day)", fontsize=12, fontweight='bold')
    ax2.set_ylim(0, plot_cap_m.max().max() * 1.25)
    ax2.legend(title="Distribution Pathway", bbox_to_anchor=(1.02, 1), loc='upper left')
    ax2.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)
    plt.xticks(rotation=0)
    fig2.tight_layout(rect=[0, 0, 0.85, 1])
    fig2.savefig(OUTPUT_DIR1 / 'Distribution_Capital_comparison.png', dpi=300)

    print(f"Success: Both LCOH and Capital graphs saved to {OUTPUT_DIR1}")
    plt.show()
else:
    print("Error: No data available to plot.")