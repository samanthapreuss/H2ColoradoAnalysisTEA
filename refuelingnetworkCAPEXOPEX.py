import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_Analysis"
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = BASE_DIR / "outputs" / "absolute_cost_analysis"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

refueling_files = [
    {"name": "Liquid_Refueling", "file": "liquidrefuelingtea.csv"},
    {"name": "Pipeline_Refueling", "file": "pipelinerefuelingtea.csv"},
    {"name": "Gaseous_Refueling", "file": "gaseousrefuelingtea.csv"}
]

def create_absolute_investment_charts(df, title, save_path):
    df.columns = df.columns.str.strip()
    df['Capacity'] = pd.to_numeric(df['Capacity'], errors='coerce')
    df = df.sort_values('Capacity')
    
    sizes = df['T-Shirt Size']
    cap_invest = df['Total Capital Investment ($)']
    ann_om = df['Annual O&M (Less energy cost) ($)']
    ann_energy = df['Energy Cost ($)']
    
    # We create a figure with two subplots: One for CAPEX, one for OPEX
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12))

    # --- PLOT 1: TOTAL CAPITAL INVESTMENT ---
    bars1 = ax1.bar(sizes, cap_invest, color='#2E86C1', edgecolor='white', label='Total Capital Investment')
    ax1.set_title(f'{title.replace("_", " ")}: Total Capital Investment (CAPEX)', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Investment ($)')
    ax1.set_ylim(0, cap_invest.max() * 1.2)
    
    for bar in bars1:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height + (height*0.02), 
                 f'${height/1e6:.2f}M', ha='center', fontweight='bold', color='#1B4F72')

    # --- PLOT 2: ANNUAL OPERATING BREAKDOWN ---
    ax2.bar(sizes, ann_om, label='Annual O&M (Fixed)', color='#F39C12', edgecolor='white')
    ax2.bar(sizes, ann_energy, bottom=ann_om, label='Annual Energy Cost (Variable)', color='#27AE60', edgecolor='white')
    
    ax2.set_title(f'{title.replace("_", " ")}: Annual Operating Expenditure (OPEX)', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Annual Cost ($/year)')
    ax2.legend(loc='upper left')
    
    # Calculate top labels for OPEX
    total_opex = ann_om + ann_energy
    ax2.set_ylim(0, total_opex.max() * 1.25)
    
    for i, val in enumerate(total_opex):
        ax2.text(i, val + (val*0.02), f'${val/1e6:.2f}M', ha='center', fontweight='bold')

    plt.tight_layout(pad=4.0)
    plt.savefig(save_path, dpi=300)
    plt.close()

# --- 2. EXECUTION ---
for item in refueling_files:
    file_path = DATA_DIR / item['file']
    if file_path.exists():
        print(f"Analyzing Absolute Costs for: {item['file']}")
        df_raw = pd.read_csv(file_path)
        output_img = RESULTS_DIR / f"{item['name']}_absolute_costs.png"
        create_absolute_investment_charts(df_raw, item['name'], output_img)

print(f"\nAbsolute cost analysis complete. Files saved in: {RESULTS_DIR}")