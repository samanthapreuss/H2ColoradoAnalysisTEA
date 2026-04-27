import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
INPUT_DIR = BASE_DIR / "data" / "script_outputs" 
FINAL_OUT = BASE_DIR / "outputs" / "finalize images" 
FINAL_OUT.mkdir(parents=True, exist_ok=True)

# Column Headers
TECH_ID_COL = 'Method' 
COL_LCOH = 'Net LCOH'
COL_LCOH_ERR = 'LCOH_SE'
CAPITAL_COST = 'Total Capital'
CAPITAL_ERR = 'Capital Standard Error'

def safe_get(row, col, default=0):
    if col in row and pd.notnull(row[col]):
        return float(row[col])
    return float(default)

def get_integrated_analysis():
    try:
        production = pd.read_csv(INPUT_DIR / "electrolyzer_production_results.csv")
        storage = pd.read_csv(INPUT_DIR / "geologic_storage_results.csv")
        distribution = pd.read_csv(INPUT_DIR / "distribution_summary.csv")
        refueling = pd.read_csv(INPUT_DIR / "network_refueling_summary.csv")

        # Config with scaling for Billions
        metrics = [
            {
                'name': 'LCOH', 
                'val': COL_LCOH, 'err': COL_LCOH_ERR, 
                'unit': '$/kg H2', 'fmt': '${:.2f}', 'scale': 1
            },
            {
                'name': 'Capital Cost', 
                'val': CAPITAL_COST, 'err': CAPITAL_ERR, 
                'unit': 'Billions of $ USD', 'fmt': '${:.2f}B', 'scale': 1e9
            }
        ]

        for tech in ['PEM', 'AWE']:
            for m in metrics:
                pathway_data = []
                p_match = production[production[TECH_ID_COL].str.contains(tech, case=False, na=False)]
                if p_match.empty: continue
                p_row = p_match.iloc[0]

                for _, s_row in storage.iterrows():
                    s_name = s_row[TECH_ID_COL]
                    for chain in ['Gaseous', 'Liquid', 'Pipeline']:
                        d_match = distribution[distribution[TECH_ID_COL].str.contains(chain, case=False, na=False)]
                        r_match = refueling[refueling[TECH_ID_COL].str.contains(chain, case=False, na=False)]
                        
                        if d_match.empty or r_match.empty: continue
                        d_row, r_row = d_match.iloc[0], r_match.iloc[0]

                        pathway_data.append({
                            'Label': f"{s_name}\n({chain})",
                            'Production': safe_get(p_row, m['val']),
                            'Storage': safe_get(s_row, m['val']),
                            'Distribution': safe_get(d_row, m['val']),
                            'Refueling': safe_get(r_row, m['val']),
                            'Total_Err': np.sqrt(safe_get(p_row, m['err'])**2 + 
                                                 safe_get(s_row, m['err'])**2 + 
                                                 safe_get(d_row, m['err'])**2 + 
                                                 safe_get(r_row, m['err'])**2)
                        })

                df_plot = pd.DataFrame(pathway_data)
                if not df_plot.empty:
                    plot_results(df_plot, tech, m)

    except Exception as e:
        print(f"Error: {e}")

def plot_results(df, tech, m):
    fig, ax = plt.subplots(figsize=(16, 10))
    categories = ['Production', 'Storage', 'Distribution', 'Refueling']
    colors = ['#1a3a5a', '#3498db', '#2ecc71', '#e67e22'] 
    
    x = np.arange(len(df))
    bottoms = np.zeros(len(df))
    totals = df[categories].sum(axis=1)

    # Scaling the values for the axis and the bars if it's Capital Cost
    # (Optional: Keep bars in raw units but labels in Billions, 
    # but it's usually cleaner to scale the whole axis)
    y_vals = df[categories] / m['scale']
    y_totals = totals / m['scale']
    y_errs = df['Total_Err'] / m['scale']

    for i, cat in enumerate(categories):
        vals = y_vals[cat].values
        ax.bar(x, vals, bottom=bottoms, label=cat, color=colors[i], width=0.7)
        
        for j, val in enumerate(vals):
            if y_totals[j] > 0 and (val / y_totals[j]) > 0.01:
                ax.text(j, bottoms[j] + val/2, f'{(val/y_totals[j]*100):.1f}%', 
                        ha='center', va='center', color='white', fontweight='bold', fontsize=9)
        bottoms += vals

    ax.errorbar(x, y_totals, yerr=y_errs, fmt='none', ecolor='black', capsize=6, elinewidth=1.5)
    
    for j, total_val in enumerate(y_totals):
        err = y_errs.iloc[j]
        label_text = f"Total: {m['fmt'].format(total_val)}\n±{m['fmt'].format(err)}"
        ax.text(j, total_val + err + (max(y_totals)*0.03), label_text, 
                ha='center', va='bottom', fontsize=10, fontweight='bold')

    ax.set_title(f'Integrated {m["name"]} Analysis: {tech} Electrolysis', fontsize=20, fontweight='bold', pad=45)
    ax.set_ylabel(f'Value ({m["unit"]})', fontsize=14)
    ax.set_xticks(x)
    ax.set_xticklabels(df['Label'], rotation=45, ha='right', fontsize=11)
    ax.set_ylim(0, max(y_totals) * 1.4)
    ax.legend(title="Chain Segment", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=False, fontsize=12)
    
    plt.grid(axis='y', linestyle='--', alpha=0.3)
    plt.tight_layout()
    
    save_path = FINAL_OUT / f"{m['name']}_Breakdown_{tech}.png"
    plt.savefig(save_path, dpi=300)
    print(f"Generated {save_path.name}")
    plt.close()

if __name__ == "__main__":
    get_integrated_analysis()