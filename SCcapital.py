import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
from matplotlib.ticker import FuncFormatter

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_Analysis"
INPUT_DIR = BASE_DIR / "outputs" / "fleet_analysis"
FINAL_OUT = BASE_DIR / "outputs" / "total_supply_chain"
FINAL_OUT.mkdir(parents=True, exist_ok=True)

def get_total_supply_chain_analysis():
    try:
        # Load the results files
        production = pd.read_csv(INPUT_DIR / "electrolyzerRESULTS.csv", on_bad_lines='skip')
        storage = pd.read_csv(INPUT_DIR / "geologicRESULTS.csv", on_bad_lines='skip')
        
        dist_dfs = {
            'Liquid': pd.read_csv(INPUT_DIR / "distribution_liquidRESULTS.csv", on_bad_lines='skip'),
            'Gaseous': pd.read_csv(INPUT_DIR / "distribution_gasRESULTS.csv", on_bad_lines='skip'),
            'Pipeline': pd.read_csv(INPUT_DIR / "distribution_pipelineRESULTS.csv", on_bad_lines='skip')
        }
        refueling = pd.read_csv(INPUT_DIR / "refuelingRESULTS.csv", on_bad_lines='skip')
        
        # Clean headers and strip string whitespace
        for df in [production, storage, refueling] + list(dist_dfs.values()):
            df.columns = df.columns.str.strip()
            for col in df.select_dtypes(['object']).columns:
                df[col] = df[col].str.strip()

    except Exception as e:
        print(f"Error loading files: {e}")
        return

    def get_specific_val(df, row_query, col_type="lcoh", is_se=False):
        """
        col_type can be: "lcoh", "capital", or "se"
        """
        if is_se:
            target_keywords = ["se", "error", "std"]
        elif col_type == "capital":
            target_keywords = ["total capital", "cap ex", "investment"]
        else:
            target_keywords = ["total_lcoh", "net lcoh", "total", "avg"]
        
        actual_col = None
        for kw in target_keywords:
            match_cols = [c for c in df.columns if kw.lower() in c.lower()]
            if match_cols:
                actual_col = match_cols[0]
                break
        
        if not actual_col: 
            return 0.0
        
        match = df[df['Method'].str.contains(row_query, case=False, na=False)]
        if match.empty: 
            return None
            
        try:
            return float(str(match[actual_col].values[0]).replace(',', ''))
        except:
            return 0.0

    # --- 2. DEFINE COMBINATIONS ---
    storage_types = ['Lined Rock Cavern', 'Salt Cavern', 'Depleted Gas Reservior']
    dist_methods = ['Liquid', 'Gaseous', 'Pipeline']
    techs = ['PEM 210MW', 'AWE 240MW']
    
    colors = ['#2E5A88', '#95A5A6', '#D97B29', '#4A924A'] # Prod, Stor, Dist, Ref
    components = ['Production', 'Storage', 'Distribution', 'Refueling']

    for tech in techs:
        lcoh_data = []
        cap_data = []

        for st in storage_types:
            for dist in dist_methods:
                # --- Fetch LCOH Averages & SE ---
                p_lcoh = get_specific_val(production, tech, "lcoh")
                p_se = get_specific_val(production, tech, "se", True)
                s_lcoh = get_specific_val(storage, st, "lcoh")
                s_se = get_specific_val(storage, st, "se", True)
                d_lcoh = get_specific_val(dist_dfs[dist], dist, "lcoh")
                d_se = get_specific_val(dist_dfs[dist], dist, "se", True)
                r_lcoh = get_specific_val(refueling, dist, "lcoh")
                r_se = get_specific_val(refueling, dist, "se", True)

                # --- Fetch Capital Costs ---
                p_cap = get_specific_val(production, tech, "capital")
                s_cap = get_specific_val(storage, st, "capital")
                d_cap = get_specific_val(dist_dfs[dist], dist, "capital")
                r_cap = get_specific_val(refueling, dist, "capital")

                if None in [p_lcoh, s_lcoh, d_lcoh, r_lcoh]:
                    continue

                # Combine Data
                total_se = np.sqrt(p_se**2 + s_se**2 + d_se**2 + r_se**2)
                short_st = st.replace(' Cavern', '').replace(' Reservior', '').replace('Lined Rock', 'Lined')
                path_label = f"{short_st}\n({dist})"

                lcoh_data.append({
                    'Pathway': path_label, 'Production': p_lcoh, 'Storage': s_lcoh,
                    'Distribution': d_lcoh, 'Refueling': r_lcoh, 'Total': p_lcoh + s_lcoh + d_lcoh + r_lcoh,
                    'SE': total_se
                })

                cap_data.append({
                    'Pathway': path_label, 'Production': p_cap, 'Storage': s_cap,
                    'Distribution': d_cap, 'Refueling': r_cap, 'Total': p_cap + s_cap + d_cap + r_cap
                })

        # --- 3. PLOTTING FUNCTION ---
        def create_stacked_plot(data_list, title, ylabel, filename, is_lcoh=True):
            df = pd.DataFrame(data_list)
            fig, ax = plt.subplots(figsize=(18, 11))
            for spine in ax.spines.values(): spine.set_linewidth(2)
            
            bottom = np.zeros(len(df))
            for i, comp in enumerate(components):
                ax.bar(df['Pathway'], df[comp], bottom=bottom, label=comp, color=colors[i], edgecolor='white', width=0.75)
                for idx, val in enumerate(df[comp]):
                    pct = (val / df['Total'][idx]) * 100
                    if pct > 3.0:
                        ax.text(idx, bottom[idx] + (val/2), f'{pct:.1f}%', ha='center', va='center', color='white', fontweight='bold', fontsize=10)
                bottom += df[comp]

            if is_lcoh:
                ax.errorbar(np.arange(len(df)), df['Total'], yerr=df['SE'], fmt='none', ecolor='black', capsize=10, elinewidth=2)
                for idx, (tot, se) in enumerate(zip(df['Total'], df['SE'])):
                    ax.text(idx, tot + se + 0.1, f'${tot:.2f}\n±{se:.2f}', ha='center', va='bottom', fontweight='bold', fontsize=11)
            else:
                # Formatter for large dollar amounts (Millions)
                ax.yaxis.set_major_formatter(FuncFormatter(lambda x, p: f'${x/1e6:.0f}M'))
                for idx, tot in enumerate(df['Total']):
                    ax.text(idx, tot + (tot*0.02), f'${tot/1e6:.1f}M', ha='center', va='bottom', fontweight='bold', fontsize=11)

            ax.set_title(title, fontsize=24, pad=65, fontweight='bold')
            ax.set_ylabel(ylabel, fontsize=16, labelpad=20)
            ax.set_ylim(0, df['Total'].max() * 1.35)
            ax.legend(title="Segments", bbox_to_anchor=(1.02, 1), loc='upper left', frameon=True, edgecolor='black', fontsize=12)
            plt.xticks(rotation=0, fontsize=11, fontweight='bold')
            plt.grid(axis='y', linestyle='--', alpha=0.3)
            plt.subplots_adjust(left=0.08, right=0.82, top=0.85, bottom=0.15)
            plt.savefig(FINAL_OUT / filename, dpi=300)
            plt.close()

        # Generate the two graphs for this tech
        create_stacked_plot(lcoh_data, f'Integrated Supply Chain LCOH: {tech}', 'Total LCOH ($/kg H2)', f'LCOH_Comparison_{tech.replace(" ", "_")}.png', is_lcoh=True)
        create_stacked_plot(cap_data, f'Total Capital Investment: {tech} Pathways', 'Capital Expenditure ($)', f'Capital_Comparison_{tech.replace(" ", "_")}.png', is_lcoh=False)
        print(f"Completed analysis for {tech}")

if __name__ == "__main__":
    get_total_supply_chain_analysis()