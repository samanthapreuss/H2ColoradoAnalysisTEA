import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
RESULTS_DIR = DATA_DIR / "script_outputs"
OUTPUT_DIR1 = BASE_DIR / "outputs" / "finalize images" 
OUTPUT_DIR2 = DATA_DIR / "script_outputs"

# 2. PATHWAY FILE MAPPING
pathways = {
    "Gaseous": {
        "results": RESULTS_DIR / "gaseous_distribution_results.csv",
        "sites": RESULTS_DIR / "final_gasbalanced_sites_details.csv"
    },
    "Liquid": {
        "results": RESULTS_DIR / "liquid_distribution_results.csv",
        "sites": RESULTS_DIR / "final_liquidbalanced_sites_details.csv"
    },
    "Pipeline": {
        "results": RESULTS_DIR / "pipeline_distribution_results.csv",
        "sites": RESULTS_DIR / "finalpipelinebalanced_sites_details.csv"
    }
}

OUTPUT_DIR1.mkdir(parents=True, exist_ok=True)

def analyze_all_pathways_fleet_fixed():
    try:
        fleet_stats = []
        size_map = {'XS': 1000, 'S': 2000, 'M': 5000, 'L': 10000, 'XL': 20000}

        for tech, paths in pathways.items():
            results_path = paths["results"]
            sites_path = paths["sites"]

            if not results_path.exists() or not sites_path.exists():
                print(f"Warning: Skipping {tech}. Missing files.")
                continue
            
            df_tea = pd.read_csv(results_path)
            df_tea.columns = df_tea.columns.str.strip()
            df_tea['Cap_Int'] = df_tea['Method'].str.extract(r'(\d+)').astype(int)

            df_sites = pd.read_csv(sites_path)
            df_sites.columns = df_sites.columns.str.strip()
            df_sites['Cap_Mapped'] = df_sites['Station_Size'].astype(str).str.strip().map(size_map)

            merged = df_sites.merge(df_tea, left_on='Cap_Mapped', right_on='Cap_Int', how='left')
            merged = merged.dropna(subset=['Net LCOH', 'Total Capital'])
            
            n = len(merged)
            if n > 0:
                fleet_stats.append({
                    'Technology': tech,
                    'Avg_LCOH': merged['Net LCOH'].mean(),
                    'LCOH_SE': merged['Net LCOH'].std() / np.sqrt(n),
                    'Avg_Capital': merged['Total Capital'].mean(),
                    'Capital_SE': merged['Total Capital'].std() / np.sqrt(n),
                    'Station_Count': n
                })

        if not fleet_stats:
            print("No data was successfully merged.")
            return

        df_final = pd.DataFrame(fleet_stats)
        colors = ["#2E883D", "#2958D9", "#c0392b"] 

        # --- 4. PLOT 1: LCOH COMPARISON ---
        fig1, ax1 = plt.subplots(figsize=(12, 7))
        
        ax1.bar(df_final['Technology'], df_final['Avg_LCOH'], color=colors, edgecolor='black', alpha=0.8, zorder=3, width=0.5)
        ax1.errorbar(df_final['Technology'], df_final['Avg_LCOH'], yerr=df_final['LCOH_SE'], fmt='none', ecolor='black', capsize=10, elinewidth=2, zorder=4)

        for i, row in df_final.iterrows():
            # Use your custom formatting: Avg: $0.00 \n ±0.000
            label_text = f'Avg: ${row["Avg_LCOH"]:.2f}\n±{row["LCOH_SE"]:.3f}'
            ax1.text(i, row['Avg_LCOH'] + row['LCOH_SE'] + 0.15, label_text, 
                     ha='center', fontweight='bold', fontsize=10,
                     bbox=dict(facecolor='white', alpha=0.7, boxstyle='round', edgecolor='none'), zorder=10)

        ax1.set_title('Distribution Weighted Average LCOH Comparison', fontsize=15, fontweight='bold', pad=20)
        ax1.set_ylabel('Average LCOH ($/kg H2)', fontsize=12)
        ax1.set_ylim(0, df_final['Avg_LCOH'].max() * 1.5) # Increased for label room
        ax1.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
        ax1.set_axisbelow(True)
        plt.tight_layout()
        plt.savefig(OUTPUT_DIR1 / "distributionAVG_lcoh_comparison.png", dpi=300)

        # --- 5. PLOT 2: CAPITAL COST COMPARISON ---
        fig2, ax2 = plt.subplots(figsize=(12, 7))
        
        avg_cap_m = df_final['Avg_Capital'] / 1e6
        cap_se_m = df_final['Capital_SE'] / 1e6

        ax2.bar(df_final['Technology'], avg_cap_m, color=colors, edgecolor='black', alpha=0.8, zorder=3, width=0.5)
        ax2.errorbar(df_final['Technology'], avg_cap_m, yerr=cap_se_m, fmt='none', ecolor='black', capsize=10, elinewidth=2, zorder=4)

        for i, val in enumerate(avg_cap_m):
            # Format: Total: $0.0M \n ±0.0
            label_text = f'Total: ${val:.1f}M\n±{cap_se_m[i]:.1f}'
            ax2.text(i, val + cap_se_m[i] + (val * 0.05), label_text, 
                     ha='center', fontweight='bold', fontsize=10,
                     bbox=dict(facecolor='white', alpha=0.7, boxstyle='round', edgecolor='none'), zorder=10)

        ax2.set_title('Distribution Average Capital Investment per Network', fontsize=15, fontweight='bold', pad=20)
        ax2.set_ylabel('Average Capital Cost ($ Millions)', fontsize=12)
        ax2.set_ylim(0, avg_cap_m.max() * 1.5) # Increased for label room
        ax2.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
        ax2.set_axisbelow(True)

        plt.tight_layout()
        plt.savefig(OUTPUT_DIR1 / "distributionAVG_capital_comparison.png", dpi=300)
        
        print("-" * 50)
        print(f"SUCCESS: Comparison generated for {len(fleet_stats)} technologies.")
        print("-" * 50)
        plt.show()

    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    analyze_all_pathways_fleet_fixed()