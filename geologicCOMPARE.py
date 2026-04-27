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
OUTPUT_DIR1.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR2.mkdir(parents=True, exist_ok=True)


# 1. SETUP
filename = DATA_DIR / "geologicstorage.csv"
lcoh_components = ["Lining", "Mining", "Wells", "Piping", "PSA Unit", "Cushion Gas"]

def load_geologic_data(file_path):
    df = pd.read_csv(file_path, index_col=0)
    df.index = df.index.astype(str).str.strip()
    df.columns = df.columns.astype(str).str.strip()
    for col in df.columns:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    return df
# Check if file exists and run the logic
if os.path.exists(filename):
    df = load_geologic_data(filename) # df is defined here
    num_bars = len(df)
    
    df['Net LCOH'] = df['LCOH total'] - df['Compressor']
    
    # --- UPDATED: CONSOLIDATED CSV EXPORT ---
    # 1. Select the LCOH components and the Net LCOH
    export_df = df[lcoh_components + ['Net LCOH']].copy()
    
    # 2. Add/Rename the Financial columns to match the screenshot
    # Assuming 'Capital Expenditure' is the "Total Capital" shown in your image
    export_df['Total Capital'] = df['Capital Expenditure']
    
    # 3. Add the "Capital Standard Error" column (filled with 0 as per image)
    export_df['Capital Standard Error'] = 0
    
    # 4. Save to CSV without the headers text to keep it as a clean raw data table
    export_path = OUTPUT_DIR2 / 'geologic_storage_results.csv'
    export_df.to_csv(export_path, index_label="Method")
    
    print(f"Geologic storage results saved to '{export_path}'.")

   # --- GRAPH 1: LCOH BREAKDOWN ---
    fig1, ax1 = plt.subplots(figsize=(11, 8))
    colors_lcoh = plt.cm.viridis(np.linspace(0, 0.8, len(lcoh_components)))
    df[lcoh_components].plot(kind='bar', stacked=True, ax=ax1, color=colors_lcoh, edgecolor='white', width=0.6)
    
    # Add Grid Lines (Set behind the bars)
    ax1.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
    ax1.set_axisbelow(True)

    totals_lcoh = df['Net LCOH'].values
    bottoms = np.zeros(num_bars)
    for col_idx, component in enumerate(lcoh_components):
        values = df[component].values
        percentages = (values / totals_lcoh) * 100
        for i, (val, pct) in enumerate(zip(values, percentages)):
            if val > 0:
                center_y = bottoms[i] + val / 2
                text_color = 'white' if (component == "Lining" or pct > 15) else 'black'
                if pct < 5:
                    ax1.annotate(f'{pct:.1f}%', xy=(i, center_y), xytext=(i + 0.32, center_y),
                                arrowprops=dict(arrowstyle='->', color='black', lw=0.8),
                                ha='left', va='center', fontsize=9, fontweight='bold')
                else:
                    ax1.text(i, center_y, f'{pct:.1f}%', ha='center', va='center', 
                            color=text_color, fontsize=10, fontweight='bold')
            bottoms[i] += val

    for i, total in enumerate(totals_lcoh):
        # Changed color to 'black'
        ax1.text(i, total + 0.02, f'Total: ${total:.2f}', ha='center', va='bottom', 
                fontweight='bold', fontsize=12, color='black')

    ax1.set_xlim(-0.5, num_bars - 0.5 + 0.45) 
    ax1.set_ylim(0, max(totals_lcoh) * 1.3)
    ax1.set_title("Geologic Storage: LCOH Component Breakdown", fontsize=14, pad=25)
    ax1.set_ylabel("LCOH ($/kg H2)", fontsize=12)
    plt.xticks(rotation=0)
    ax1.legend(title="Components", bbox_to_anchor=(1.01, 1), loc='upper left', fontsize=10)
    plt.tight_layout(rect=[0, 0, 0.95, 1])
    plt.savefig(OUTPUT_DIR1 / 'geologicLCOHfinal.png')

# --- 6. GRAPH 2: FINANCIAL COMPARISON (Single Axis) ---
    fig2, ax2 = plt.subplots(figsize=(11, 8))
    
    # Add Grid Lines
    ax2.grid(axis='y', linestyle=':', alpha=0.6, zorder=0)
    ax2.set_axisbelow(True)
    
    x = np.arange(num_bars)
    width = 0.35
    
    # Plot both on ax2 (No twinx)
    rects1 = ax2.bar(x - width/2, df['Capital Expenditure'], width, label='CAPEX ($)', color="#a3ad45")
    rects2 = ax2.bar(x + width/2, df['Annual Operating Costs'], width, label='OPEX ($/yr)', color="#e66a22")
    
    # Add labels for CAPEX (Force color to BLACK)
    for i, val in enumerate(df['Capital Expenditure']):
        ax2.text(i - width/2, val + (val * 0.01), f'${val/1e6:.1f}M', 
                 ha='center', va='bottom', fontweight='bold', color='black') # Changed to black
                 
    # Add labels for OPEX (Force color to BLACK)
    for i, val in enumerate(df['Annual Operating Costs']):
        ax2.text(i + width/2, val + (val * 0.01), f'${val/1e6:.2f}M', 
                 ha='center', va='bottom', fontweight='bold', color='black') # Changed to black

    ax2.set_xlim(-0.6, num_bars - 0.4)
    # Set ylim based on the largest value (usually CAPEX)
    ax2.set_ylim(0, df['Capital Expenditure'].max() * 1.2)
    
    ax2.set_title("Geologic Storage: Capital vs. Annual Operating Costs", fontsize=14, pad=25)
    ax2.set_ylabel("Cost (USD)", fontsize=12)
    ax2.set_xticks(x)
    ax2.set_xticklabels(df.index)
    
    # Simple legend since we only have one axis now
    ax2.legend(loc='upper left', bbox_to_anchor=(1, 1))

    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(OUTPUT_DIR1 / 'geologic_CAPEXOPEXfinal.png')
    plt.show()