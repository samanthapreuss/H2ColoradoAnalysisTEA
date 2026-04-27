import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_Analysis"
DATA_DIR = BASE_DIR / "data"                                # Folder for refuelingtea.csv files
DATA2_DIR = BASE_DIR / "scripts" / "DONE" / "outputs"        # Folder for balanced_sites_details.csv files
RESULTS_DIR = BASE_DIR / "outputs" / "investment_comparison"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# Define the scenarios
scenarios = [
    {
        "name": "Liquid",
        "sites": DATA2_DIR / "liquidbalanced_sites_details.csv",
        "specs": DATA_DIR / "liquidrefuelingtea.csv",
        "color": "#2E86C1"
    },
    {
        "name": "Pipeline",
        "sites": DATA2_DIR / "pipelinebalanced_sites_details.csv",
        "specs": DATA_DIR / "pipelinerefuelingtea.csv",
        "color": "#F39C12"
    },
    {
        "name": "Gaseous",
        "sites": DATA2_DIR / "gaseousbalanced_sites_details.csv",
        "specs": DATA_DIR / "gaseousrefuelingtea.csv",
        "color": "#27AE60"
    }
]

def generate_total_fleet_investment():
    final_results = []
    
    for sc in scenarios:
        sites_path = sc['sites']
        specs_path = sc['specs']
        
        if not (sites_path.exists() and specs_path.exists()):
            print(f"Skipping {sc['name']}: Paired files not found.")
            continue
            
        # Load and clean headers
        sites_df = pd.read_csv(sites_path)
        specs_df = pd.read_csv(specs_path)
        sites_df.columns = sites_df.columns.str.strip()
        specs_df.columns = specs_df.columns.str.strip()
        
        # Calculate investment per station by merging
        merged = sites_df.merge(
            specs_df[['T-Shirt Size', 'Total Capital Investment ($)']],
            left_on='Station_Size',
            right_on='T-Shirt Size',
            how='left'
        )
        
        # Sum the total capital needed for the whole network
        total_investment = merged['Total Capital Investment ($)'].sum()
        station_count = len(sites_df)
        
        final_results.append({
            'Method': sc['name'],
            'Total_Investment': total_investment,
            'Station_Count': station_count,
            'Color': sc['color']
        })
        
    if not final_results:
        print("No paired data found. Verify your CSV filenames and folder paths.")
        return
        
    # --- 2. PLOTTING ---
    df_res = pd.DataFrame(final_results)
    fig, ax = plt.subplots(figsize=(10, 7))
    
    # Comparison Bar Chart
    bars = ax.bar(df_res['Method'], df_res['Total_Investment'], color=df_res['Color'], edgecolor='black', alpha=0.85, width=0.6)
    
    # Formatting
    ax.set_title('Total Network Capital Investment Comparison\n(Final Cumulative CAPEX)', fontsize=15, pad=30, fontweight='bold')
    ax.set_ylabel('Total Cumulative Investment ($)', fontsize=12)
    ax.set_ylim(0, df_res['Total_Investment'].max() * 1.3)
    ax.grid(axis='y', linestyle='--', alpha=0.3)

    # Data Labels ($Millions and Station Count)
    for i, bar in enumerate(bars):
        height = bar.get_height()
        count = df_res.iloc[i]['Station_Count']
        ax.annotate(f'${height/1e6:.1f}M\n({count} Stations)', 
                    (bar.get_x() + bar.get_width() / 2., height), 
                    ha='center', va='center', 
                    xytext=(0, 18), 
                    textcoords='offset points',
                    fontsize=10, fontweight='bold',
                    bbox=dict(facecolor='white', alpha=0.7, edgecolor='none'))

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    
    output_path = RESULTS_DIR / "total_fleet_investment_comparison.png"
    plt.savefig(output_path, dpi=300)
    plt.close()
    
    # Save the summary table
    df_res.to_csv(RESULTS_DIR / "total_fleet_investment_summary.csv", index=False)
    print(f"Final investment comparison completed. Chart saved to: {output_path}")

if __name__ == "__main__":
    generate_total_fleet_investment()