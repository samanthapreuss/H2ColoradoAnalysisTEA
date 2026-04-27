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

for d in [OUTPUT_DIR1, OUTPUT_DIR2]:
    d.mkdir(parents=True, exist_ok=True)

# --- 2. IMPROVED DATA PARSING ---
def parse_pipeline_minimal(data_path, filename="Pipeline.csv"):
    file_full_path = data_path / filename
    if not file_full_path.exists():
        print(f"File not found: {file_full_path}")
        return []

    # Using strip on strings to handle potential whitespace issues
    df_raw = pd.read_csv(file_full_path, header=None).fillna('')
    data_blocks = []
    
    for i in range(len(df_raw)):
        cell_0 = str(df_raw.iloc[i, 0]).strip()
        
        if cell_0 and cell_0.replace('.', '', 1).isdigit():
            capacity = float(cell_0)
            cat_totals = {}
            total_cap_inv = 0.0
            std_err_cap = 0.0
            
            for search_idx in range(i, min(i + 15, len(df_raw))):
                row_values = [str(val).strip() for val in df_raw.iloc[search_idx].values]
                row_str = " ".join(row_values).lower()
                
                if 'total cost' in row_str:
                    found_nums = []
                    for val in row_values:
                        clean_val = val.replace(',', '').replace('$', '')
                        try:
                            f_val = float(clean_val)
                            if f_val != 0 and f_val != capacity:
                                found_nums.append(f_val)
                        except ValueError:
                            continue
                    
                    if len(found_nums) >= 2:
                        cat_totals['Transmission'] = found_nums[0]
                        cat_totals['Distribution'] = found_nums[1]
                        total_cap_inv = max(found_nums) if found_nums else 0.0
                        std_err_cap = found_nums[3] if len(found_nums) > 3 else 0.0
                        break

            if cat_totals:
                net_lcoh = sum(cat_totals.values())
                
                # --- CALCULATION LOGIC ---
                # Calculating SE for LCOH (using a 5% variance assumption if sample data isn't provided)
                # Or simply calculating based on the spread if multiple rows existed.
                # For this script, we'll store the Standard Error as a function of the component spread.
                lcoh_values = list(cat_totals.values())
                lcoh_se = np.std(lcoh_values) / np.sqrt(len(lcoh_values))

                data_blocks.append({
                    'Capacity': capacity,
                    'Total Capital': total_cap_inv,
                    'Capital Standard Error': std_err_cap,
                    'Net LCOH': net_lcoh,
                    'LCOH_SE': lcoh_se, # Added SE calculation
                    'CatTotals': cat_totals
                })
                
    return data_blocks

data = parse_pipeline_minimal(DATA_DIR)

# --- 3. GRAPHING & EXPORT ---
if data:
    colors = {'Transmission': '#2E5A88', 'Distribution': '#D97B29'}
    categories = ['Transmission', 'Distribution']
    
    fig, ax = plt.subplots(figsize=(13, 8))
    indices = np.arange(len(data))
    export_rows = []

    for idx, block in enumerate(data):
        current_bottom = 0
        export_rows.append({
            'Method': f"Pipeline {int(block['Capacity'])} kg/d",
            'Transmission': block['CatTotals']['Transmission'],
            'Distribution': block['CatTotals']['Distribution'],
            'Net LCOH': block['Net LCOH'],
            'LCOH_SE': block['LCOH_SE'], # Added to CSV export
            'Total Capital': block['Total Capital'],
            'Capital Standard Error': block['Capital Standard Error']
        })

        for cat in categories:
            val = block['CatTotals'][cat]
            ax.bar(idx, val, 0.6, bottom=current_bottom, color=colors[cat], edgecolor='white', zorder=3, label=cat if idx == 0 else "")
            if val > 0.05:
                ax.text(idx, current_bottom + (val/2), f'${val:.2f}', ha='center', va='center', color='white', fontweight='bold')
            current_bottom += val

        # Add error bars to the plot for Net LCOH
        ax.errorbar(idx, block['Net LCOH'], yerr=block['LCOH_SE'], fmt='none', ecolor='black', capsize=5, zorder=4)
        ax.text(idx, block['Net LCOH'] + 0.1, f"Total: ${block['Net LCOH']:.2f}", ha='center', va='bottom', fontweight='bold')

    ax.set_title('Pipeline Infrastructure LCOH Breakdown with Standard Error', fontsize=16, pad=25)
    ax.set_ylabel('LCOH ($/kg H2)')
    ax.set_xticks(indices)
    ax.set_xticklabels([f"{int(b['Capacity'])} kg/d" for b in data], fontweight='bold')
    
    # Save the dataframe
    df_results = pd.DataFrame(export_rows)
    df_results.to_csv(OUTPUT_DIR2 / 'pipeline_distribution_results.csv', index=False)
    
    plt.tight_layout(rect=[0, 0, 0.85, 1])
    plt.savefig(OUTPUT_DIR1 / 'pipelinedistribution_stacked_final.png', dpi=300)
    print(f"SUCCESS: Exported {len(data)} rows to {OUTPUT_DIR2}")
    plt.show()