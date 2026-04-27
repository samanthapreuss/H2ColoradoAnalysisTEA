import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import os
import numpy as np
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR1 = DATA_DIR / "script_outputs"
OUTPUT_DIR2 = BASE_DIR / "outputs" / "finalize images"

# Ensure output folder exists
OUTPUT_DIR2.mkdir(parents=True, exist_ok=True)

# Input filenames - Pointing to the 'data' folder where we saved them
pem_file = DATA_DIR / 'script_outputs' / 'PEM_Monthly_Demand.csv'
awe_file = DATA_DIR / 'script_outputs' / 'AWE_Monthly_Demand.csv'
gen_file = OUTPUT_DIR1 / 'monthly_generation_2021.csv'

# Settings
month_names = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
kg_day_label = "120,000 kg/day"

# --- 2. PLOTTING ---
try:
    print("Loading data for combined plot...")
    wind_df = pd.read_csv(gen_file)
    pem_df = pd.read_csv(pem_file)
    awe_df = pd.read_csv(awe_file)

    fig, ax = plt.subplots(figsize=(14, 8))
    fig.patch.set_facecolor('white')
    ax.set_facecolor('white')
    
    x = np.arange(12)
    width = 0.4

    # 1. Plot Wind Generation (Bars)
    ax.bar(x - width/2, wind_df['Rush_Creek_Complex_MWh'], width, 
            label='Rush Creek Wind Gen.', color='#1f77b4', alpha=0.5, zorder=2)
    ax.bar(x + width/2, wind_df['Cheyenne_Ridge_MWh'], width, 
            label='Cheyenne Ridge Wind Gen.', color='#aec7e8', alpha=0.5, zorder=2)

    # 2. Extract and Plot PEM (542 MW)
    # Logic: Get the last 12 columns which are always Jan-Dec MWh
    pem_demand = pem_df.iloc[0, -12:].values
    ax.plot(x, pem_demand, marker='o', color="#3164c2", linewidth=3, 
            markersize=10, label=f'PEM 542 MW Demand ({kg_day_label})', zorder=4)

    # 3. Extract and Plot AWE (609 MW)
    awe_demand = awe_df.iloc[0, -12:].values
    ax.plot(x, awe_demand, marker='s', color="#9467bd", linewidth=3, 
            markersize=10, label=f'AWE 609 MW Demand ({kg_day_label})', zorder=5)

    # --- Formatting ---
    ax.set_title('2021 Wind Generation vs. Electrolyzer Load Profiles', fontsize=16, fontweight='bold', pad=20)
    ax.set_ylabel('Energy (MWh / Month)', fontsize=12)
    ax.set_xticks(x)
    ax.set_xticklabels(month_names)
    
    # Add a subtle grid
    ax.grid(axis='y', linestyle='--', alpha=0.4, zorder=0)
    
    # Place legend outside
    ax.legend(bbox_to_anchor=(1.02, 1), loc="upper left", borderaxespad=0)

    plt.tight_layout()
    
    # Save the combined image
    save_path = OUTPUT_DIR2 / 'combined_wind_vs_h2_demand.png'
    plt.savefig(save_path, dpi=300, bbox_inches='tight')
    print(f"✅ Success! Combined graph saved to: {save_path.name}")
    plt.show()

except Exception as e:
    print(f"!! Error: {e}")

try:
    print("Analyzing individual farm performance...")
    # Load Data
    wind_df = pd.read_csv(gen_file)
    pem_df = pd.read_csv(pem_file)
    awe_df = pd.read_csv(awe_file)

    # Extract Generation for individual farms
    rc_gen = wind_df['Rush_Creek_Complex_MWh'].values
    cr_gen = wind_df['Cheyenne_Ridge_MWh'].values
    
    # Extract Demands (Using positional slicing to avoid column name errors)
    pem_demand = pem_df.iloc[0, -12:].astype(float).values
    awe_demand = awe_df.iloc[0, -12:].astype(float).values

    # 1. Calculate Balances for Rush Creek Scenario
    bal_rc_pem = rc_gen - pem_demand
    bal_rc_awe = rc_gen - awe_demand

    # 2. Calculate Balances for Cheyenne Ridge Scenario
    bal_cr_pem = cr_gen - pem_demand
    bal_cr_awe = cr_gen - awe_demand

    # --- 3. PLOTTING ---
    # We will use two subplots to compare the two potential suppliers
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
    fig.patch.set_facecolor('white')
    
    x = np.arange(12)
    width = 0.35

    # SUBPLOT 1: RUSH CREEK PERFORMANCE
    ax1.bar(x - width/2, bal_rc_pem, width, label='PEM 542MW', color="#3164c2", alpha=0.85, zorder=3)
    ax1.bar(x + width/2, bal_rc_awe, width, label='AWE 609MW', color="#bd67b1", alpha=0.85, zorder=3)
    ax1.axhline(0, color='black', linewidth=2, zorder=4)
    ax1.set_title(f'Net Energy Balance: RUSH CREEK ({kg_day_label})', fontsize=14, fontweight='bold')
    ax1.set_ylabel('Net MWh (Surplus/Deficit)')
    ax1.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
    ax1.legend(loc='lower right')

    # SUBPLOT 2: CHEYENNE RIDGE PERFORMANCE
    ax2.bar(x - width/2, bal_cr_pem, width, label='PEM 542MW', color="#3164c2", alpha=0.85, zorder=3)
    ax2.bar(x + width/2, bal_cr_awe, width, label='AWE 609MW', color="#bd67b1", alpha=0.85, zorder=3)
    ax2.axhline(0, color='black', linewidth=2, zorder=4)
    ax2.set_title(f'Net Energy Balance: CHEYENNE RIDGE ({kg_day_label})', fontsize=14, fontweight='bold')
    ax2.set_ylabel('Net MWh (Surplus/Deficit)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(month_names)
    ax2.grid(axis='y', linestyle='--', alpha=0.3, zorder=0)
    ax2.legend(loc='lower right')

    fig.suptitle('Renewable Over Supply and Deficit for Electrolyzer Demand', fontsize=18, fontweight='bold', y=0.98)
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    # Save the combined comparison
    save_path = OUTPUT_DIR2 / 'individual_wind_farm_net_balance.png'
    plt.savefig(save_path, dpi=300)
    print(f"✅ Comparison complete! Saved to: {save_path}")
    plt.show()

except Exception as e:
    print(f"!! Critical Error: {e}")

pem_eff = 43.64 # kWh/kg
awe_eff = 52.5  # kWh/kg

try:
    print("Calculating Energy and Hydrogen Production Deficits...")
    wind_df = pd.read_csv(gen_file)
    pem_df = pd.read_csv(pem_file)
    awe_df = pd.read_csv(awe_file)

    # Extract Generation
    rc_gen = wind_df['Rush_Creek_Complex_MWh'].values
    cr_gen = wind_df['Cheyenne_Ridge_MWh'].values
    
    # Extract Demands
    pem_demand = pem_df.iloc[0, -12:].astype(float).values
    awe_demand = awe_df.iloc[0, -12:].astype(float).values

    # Calculate MWh Deficits (Only negative values, stored as positive "needed" amounts)
    def_rc_pem_mwh = np.array([abs(min(0, rc_gen[i] - pem_demand[i])) for i in range(12)])
    def_rc_awe_mwh = np.array([abs(min(0, rc_gen[i] - awe_demand[i])) for i in range(12)])
    def_cr_pem_mwh = np.array([abs(min(0, cr_gen[i] - pem_demand[i])) for i in range(12)])
    def_cr_awe_mwh = np.array([abs(min(0, cr_gen[i] - awe_demand[i])) for i in range(12)])

    # Convert MWh Deficit to H2 Kg Deficit: (MWh * 1000) / efficiency
    def_rc_pem_kg = (def_rc_pem_mwh * 1000) / pem_eff
    def_rc_awe_kg = (def_rc_awe_mwh * 1000) / awe_eff
    def_cr_pem_kg = (def_cr_pem_mwh * 1000) / pem_eff
    def_cr_awe_kg = (def_cr_awe_mwh * 1000) / awe_eff

    # --- 2. PLOTTING H2 KG DEFICIT ---
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(14, 12), sharex=True)
    fig.patch.set_facecolor('white')
    x = np.arange(12)
    width = 0.35

    # Subplot 1: Rush Creek H2 Shortfall
    ax1.bar(x - width/2, def_rc_pem_kg, width, color='#3164c2', alpha=0.8, label=f'PEM Deficit (Total: {def_rc_pem_kg.sum():,.0f} kg/yr)')
    ax1.bar(x + width/2, def_rc_awe_kg, width, color='#bd67b1', alpha=0.8, label=f'AWE Deficit (Total: {def_rc_awe_kg.sum():,.0f} kg/yr)')
    ax1.set_title('2021 Monthly Hydrogen Production Deficit: RUSH CREEK', fontsize=14, fontweight='bold')
    ax1.set_ylabel('H2 Production Deficit (kg / Month)')
    ax1.legend(loc='upper right', title="Annual Deficit")
    ax1.grid(axis='y', linestyle='--', alpha=0.3)

    # Subplot 2: Cheyenne Ridge H2 Shortfall
    ax2.bar(x - width/2, def_cr_pem_kg, width, color='#3164c2', alpha=0.8, label=f'PEM Deficit (Total: {def_cr_pem_kg.sum():,.0f} kg/yr)')
    ax2.bar(x + width/2, def_cr_awe_kg, width, color='#bd67b1', alpha=0.8, label=f'AWE Deficit (Total: {def_cr_awe_kg.sum():,.0f} kg/yr)')
    ax2.set_title('2021 Monthly Hydrogen Production Deficit: CHEYENNE RIDGE', fontsize=14, fontweight='bold')
    ax2.set_ylabel('H2 Production Deficit (kg / Month)')
    ax2.set_xticks(x)
    ax2.set_xticklabels(month_names)
    ax2.legend(loc='upper right', title="Annual Deficit")
    ax2.grid(axis='y', linestyle='--', alpha=0.3)

    plt.tight_layout()
    plt.savefig(OUTPUT_DIR2 / 'h2_production_DEFICIT_kg.png', dpi=300)

    # --- 3. SAVE TO CSV ---
    df_out = pd.DataFrame({
        'Month': month_names,
        'RC_PEM_MWh_Deficit': def_rc_pem_mwh,
        'RC_PEM_Kg_Deficit': def_rc_pem_kg,
        'RC_AWE_MWh_Deficit': def_rc_awe_mwh,
        'RC_AWE_Kg_Deficit': def_rc_awe_kg,
        'CR_PEM_MWh_Deficit': def_cr_pem_mwh,
        'CR_PEM_Kg_Deficit': def_cr_pem_kg,
        'CR_AWE_MWh_Deficit': def_cr_awe_mwh,
        'CR_AWE_Kg_Deficit': def_cr_awe_kg
    })
    
    # Add Totals Row
    totals = df_out.iloc[:, 1:].sum()
    totals_df = pd.DataFrame([['ANNUAL TOTAL'] + totals.tolist()], columns=df_out.columns)
    df_final = pd.concat([df_out, totals_df], ignore_index=True)
    
    csv_path = OUTPUT_DIR1 / 'detailed_h2_deficit_summary.csv'
    df_final.to_csv(csv_path, index=False)
    print(f"✅ Success! Graphs and CSV ('{csv_path.name}') generated.")
    plt.show()

except Exception as e:
    print(f"!! Error: {e}")