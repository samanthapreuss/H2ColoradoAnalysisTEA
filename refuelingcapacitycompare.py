import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs" / "finalize images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Reordered to Gaseous, Liquid, Pipeline
refueling_files = [
    {"name": "Gaseous", "file": "gaseousrefuelingtea.csv"},
    {"name": "Liquid", "file": "liquidrefuelingtea.csv"},
    {"name": "Pipeline", "file": "pipelinerefuelingtea.csv"}
]

# --- 2. DATA LOADING ---
all_data = []
for item in refueling_files:
    file_path = DATA_DIR / item['file']
    if file_path.exists():
        df = pd.read_csv(file_path)
        df.columns = df.columns.str.strip()
        df['Pathway'] = item['name']
        all_data.append(df)

if not all_data:
    print("No data files found.")
else:
    df_master = pd.concat(all_data, ignore_index=True)
    df_master['Capacity'] = pd.to_numeric(df_master['Capacity'], errors='coerce')
    
    # Define orders for sorting
    t_shirt_order = ['XS', 'S', 'M', 'L', 'XL']
    pathway_order = ["Gaseous", "Liquid", "Pipeline"]
    
    df_master['T-Shirt Size'] = pd.Categorical(df_master['T-Shirt Size'], categories=t_shirt_order, ordered=True)
    df_master['Pathway'] = pd.Categorical(df_master['Pathway'], categories=pathway_order, ordered=True)
    
    # Sort data by size then by the new pathway order
    df_master = df_master.sort_values(['T-Shirt Size', 'Pathway'])

    # --- 3. PLOTTING ---
    fig, ax = plt.subplots(figsize=(18, 11))
    
    x = np.arange(len(t_shirt_order))
    width = 0.25 
    colors = {'Capital': '#2E86C1', 'O&M': '#F39C12', 'Energy': '#27AE60'}
    
    # Iterate through the reordered pathways
    for i, path in enumerate(pathway_order):
        subset = df_master[df_master['Pathway'] == path]
        if subset.empty: continue
        
        pos = x + (i - 1) * width 
        
        cap = subset['Capital ($/kg)'].values
        om = subset['O&M less energy ($/kg)'].values
        eng = subset['Energy/Fuel ($/kg)'].values
        total = subset['Total Cost ($/kg)'].values
        
        # Plot stacked components
        ax.bar(pos, cap, width, label='Capital' if i == 0 else "", color=colors['Capital'], edgecolor='white', zorder=3)
        ax.bar(pos, om, width, bottom=cap, label='O&M' if i == 0 else "", color=colors['O&M'], edgecolor='white', zorder=3)
        ax.bar(pos, eng, width, bottom=cap+om, label='Energy/Fuel' if i == 0 else "", color=colors['Energy'], edgecolor='white', zorder=3)
        
        # --- NEW: PERCENTAGE LABELS INSIDE SEGMENTS ---
        for p, c, o, e, t in zip(pos, cap, om, eng, total):
            if t > 0:
                # Capital Percentage
                ax.text(p, c/2, f'{(c/t)*100:.0f}%', ha='center', va='center', 
                        color='white', fontsize=9, fontweight='bold')
                # O&M Percentage
                ax.text(p, c + (o/2), f'{(o/t)*100:.0f}%', ha='center', va='center', 
                        color='white', fontsize=9, fontweight='bold')
                # Energy/Fuel Percentage
                ax.text(p, c + o + (e/2), f'{(e/t)*100:.0f}%', ha='center', va='center', 
                        color='white', fontsize=9, fontweight='bold')

        # Total Cost Labels on top of bars
        for p, tot in zip(pos, total):
            ax.text(p, tot + 0.1, f'${tot:.2f}', ha='center', va='bottom', fontsize=11, fontweight='bold')
            
        # Pathway IDs (G, L, P)
        for p in pos:
            ax.text(p, -0.05, path[0], ha='center', va='top', fontsize=10, fontweight='bold', color='#555555')

    # Formatting
    ax.set_title('Hydrogen Refueling Station LCOH: Pathway Comparison', fontsize=22, fontweight='bold', pad=40)
    ax.set_ylabel('LCOH ($/kg H2)', fontsize=14, fontweight='bold')
    
    # Labels and Ticks
    ax.set_xlabel('Station Size', fontsize=16, fontweight='bold', labelpad=45)
    ax.set_xticks(x)
    ax.set_xticklabels(t_shirt_order, fontsize=14, fontweight='bold')
    ax.tick_params(axis='x', which='major', pad=25) 

    ax.set_ylim(0, df_master['Total Cost ($/kg)'].max() * 1.2)
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    ax.set_axisbelow(True)
    ax.legend(title="Cost Components", loc='upper right', fontsize=12)

    plt.subplots_adjust(bottom=0.15)
    
    save_path = OUTPUT_DIR / "Refueling_Comparison_with_Percentages.png"
    plt.savefig(save_path, dpi=300)
    print(f"Graph saved with percentages to: {save_path}")
    plt.show()