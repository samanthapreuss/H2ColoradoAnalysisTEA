import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patheffects as path_effects
import matplotlib.container as container
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

# --- 2. SETTINGS & COLOR PALETTES ---
files = {
    DATA_DIR / 'PEMfacility542MW.csv': "PEM 542 MW", 
    DATA_DIR / 'AWEfacility609MW.csv': "AWE 609 MW"
}

# LCOH uses a specific list of colors
lcoh_colors = ['#1f77b4', '#ff7f0e', '#2ca02c', '#d62728'] # Blue, Orange, Green, Red
# Capital uses a built-in colormap (try 'viridis', 'tab10', or 'Set3')
cap_colormap = 'tab10' 

case_cols = ["Case 1: Lower Range CAPEX, Fixed OPEX", "Case 2: Higher Range CAPEX, Fixed OPEX"]
lcoh_cats = ["Capital", "Fixed OPEX", "Electricity", "Water"]
cap_cats = ["Stack", "Balance of Plant (BOP)", "Installation", "General Facilities", "Engineering", "Permitting", "Contingency"]

# --- HELPER FUNCTIONS ---

def load_and_clean_data(filename):
    df = pd.read_csv(filename, sep=None, engine='python', index_col=0)
    df.index = df.index.astype(str).str.strip()
    df.columns = df.columns.astype(str).str.strip()
    return df

def add_stacked_labels(ax, df, total_col):
    """Adds percentage labels and the user-specified Total/Error labels."""
    # 1. Add Section Percentages inside segments
    for c in ax.containers:
        if not isinstance(c, container.BarContainer):
            continue
            
        labels = []
        for i, v in enumerate(c.datavalues):
            if v > 0:
                total = df.iloc[i][total_col]
                pct = (v / total) * 100
                labels.append(f'{pct:.1f}%')
            else:
                labels.append('')
        
        txt_labels = ax.bar_label(c, labels=labels, label_type='center', fontsize=9, 
                                 fontweight='bold', color='white', 
                                 path_effects=[path_effects.withStroke(linewidth=2, foreground="black")])
        for txt in txt_labels:
            txt.set_zorder(10)

    # 2. Add Totals at the Top using your specific formatting
    for i in range(len(df)):
        total_val = df.iloc[i][total_col]
        
        # Determine error column and formatting based on data type
        is_lcoh = 'LCOH' in total_col
        err_col = 'LCOH_Standard_Error' if is_lcoh else 'Capital_Standard_Error'
        error_val = df.iloc[i].get(err_col, 0)
        
        if is_lcoh:
            # Format: Avg: $0.00 \n ±0.000
            label_text = f'Avg: ${total_val:.2f}\n±{error_val:.3f}'
            # Smaller fixed offset for LCOH scale
            y_pos = total_val + error_val + 0.15 
        else:
            # Format: Total: $1,000 \n ±100
            label_text = f'Total: ${total_val:,.0f}\n±{error_val:,.0f}'
            # Percentage-based offset for large Capital scale
            y_pos = total_val + error_val + (total_val * 0.05)

        # Apply your specific bbox and text style
        ax.text(i, y_pos, label_text, ha='center', fontweight='bold', fontsize=10,
                bbox=dict(facecolor='white', alpha=0.7, boxstyle='round', edgecolor='none'),
                zorder=10)

# --- 3. DATA PROCESSING ---
lcoh_means, lcoh_se = [], []
cap_means, cap_se = [], []
labels = []
n = len(case_cols)

print("Reading and processing technology data...")
for file_path, tech_label in files.items():
    if not file_path.exists():
        print(f"!! Warning: {file_path.name} not found.")
        continue
    
    df = load_and_clean_data(file_path)
    labels.append(tech_label)
    
    subset_lcoh = df.loc[lcoh_cats, case_cols].apply(pd.to_numeric, errors='coerce')
    lcoh_means.append(subset_lcoh.mean(axis=1))
    lcoh_se.append(subset_lcoh.sum().std() / np.sqrt(n))
    
    subset_cap = df.loc[cap_cats, case_cols].apply(pd.to_numeric, errors='coerce')
    cap_means.append(subset_cap.mean(axis=1))
    cap_se.append(subset_cap.sum().std() / np.sqrt(n))

df_results_lcoh = pd.DataFrame(lcoh_means, index=labels)
df_results_lcoh['Total_LCOH'] = df_results_lcoh.sum(axis=1)
df_results_lcoh['LCOH_Standard_Error'] = lcoh_se

df_results_cap = pd.DataFrame(cap_means, index=labels)
df_results_cap['Total_Capital'] = df_results_cap.sum(axis=1)
df_results_cap['Capital_Standard_Error'] = cap_se

# --- 4. PLOTTING ---
plt.style.use('default') 

# --- Plot 1: LCOH Breakdown ---
fig1, ax1 = plt.subplots(figsize=(12, 8))
fig1.patch.set_facecolor('white')
ax1.set_facecolor('white')

df_results_lcoh[lcoh_cats].plot(kind='bar', stacked=True, ax=ax1, zorder=3, 
                               edgecolor='white', color=lcoh_colors)

ax1.errorbar(x=range(len(df_results_lcoh)), y=df_results_lcoh['Total_LCOH'], 
             yerr=df_results_lcoh['LCOH_Standard_Error'], fmt='none', c='black', 
             capsize=10, elinewidth=2, zorder=4)

add_stacked_labels(ax1, df_results_lcoh, 'Total_LCOH')

# Adjust Y-Limit for text headroom (1.3 multiplier for 30% buffer)
max_lcoh = (df_results_lcoh['Total_LCOH'] + df_results_lcoh['LCOH_Standard_Error']).max()
ax1.set_ylim(0, max_lcoh * 1.3) 

ax1.set_title('Electrolyzer Production Facility LCOH Component Breakdown', fontsize=16, fontweight='bold', pad=25)
ax1.set_ylabel('Cost ($/kg H2)', fontsize=12)
ax1.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
ax1.legend(title="Cost Components", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(OUTPUT_DIR1 / 'Electrolyzer_LCOH_Breakdown_Final.png', dpi=300)

# --- Plot 2: Capital Breakdown ---
fig2, ax2 = plt.subplots(figsize=(12, 8))
fig2.patch.set_facecolor('white')
ax2.set_facecolor('white')

df_results_cap[cap_cats].plot(kind='bar', stacked=True, ax=ax2, zorder=3, 
                               edgecolor='white', colormap=cap_colormap)

ax2.errorbar(x=range(len(df_results_cap)), y=df_results_cap['Total_Capital'], 
             yerr=df_results_cap['Capital_Standard_Error'], fmt='none', c='black', 
             capsize=10, elinewidth=2, zorder=4)

add_stacked_labels(ax2, df_results_cap, 'Total_Capital')

# Adjust Y-Limit for text headroom
max_cap = (df_results_cap['Total_Capital'] + df_results_cap['Capital_Standard_Error']).max()
ax2.set_ylim(0, max_cap * 1.3)

ax2.set_title('Electrolyzer Production Facility Capital Cost Component Breakdown', fontsize=16, fontweight='bold', pad=25)
ax2.set_ylabel('Total Capital Cost ($)', fontsize=12)
ax2.grid(axis='y', linestyle='--', alpha=0.7, zorder=0)
ax2.legend(title="Capital Components", bbox_to_anchor=(1.05, 1), loc='upper left')
plt.xticks(rotation=0)
plt.tight_layout()
plt.savefig(OUTPUT_DIR1 / 'Electrolyzer_Capital_Breakdown_Final.png', dpi=300)

print(f"\nProcessing Complete. Graphs saved to: {OUTPUT_DIR1}")
plt.show()

# --- 5. EXPORT TO CSV (CONSOLIDATED FORMAT) ---
# 1. Prepare the LCOH data
export_df = df_results_lcoh[lcoh_cats].copy()

# 2. Add Net LCOH and the specific LCOH_SE column
export_df['Net LCOH'] = df_results_lcoh['Total_LCOH']
export_df['LCOH_SE'] = df_results_lcoh['LCOH_Standard_Error']

# 3. Integrate Capital metrics
export_df['Total Capital'] = df_results_cap['Total_Capital']
export_df['Capital Standard Error'] = df_results_cap['Capital_Standard_Error']

# 4. Final Cleanup: Ensure numeric conversion and column trimming for the TEA
export_df.columns = export_df.columns.str.strip()
export_df = export_df.apply(pd.to_numeric, errors='ignore')

# 5. Save to the script_outputs folder
export_path = OUTPUT_DIR2 / 'electrolyzer_production_results.csv'
export_df.to_csv(export_path, index_label="Method")

print(f"\nConsolidated results saved to: {export_path}")
print(f"LCOH Standard Error saved under column: 'LCOH_SE'")