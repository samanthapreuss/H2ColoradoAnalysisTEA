import pandas as pd
import matplotlib.pyplot as plt
import os

# --- SETTINGS ---
storage_target_kg = 10_000_000
pem_capacity_mw = 210
awe_capacity_mw = 240

# Input files
gen_file = 'hourly_generation_2021.csv'
pem_file = 'PEMpowerconsumption.csv'
awe_file = 'AWEpowerconsumption.csv'

# Column names from your files
size_col = 'Plant Size (MW)'
cons_col = 'Electricity Consumption Total Per Day (MWh)'
prod_col = 'Kg Produced per day'

# 1. Load and Calculate Efficiency (MWh per kg)
def get_efficiency(path, target_size):
    df = pd.read_csv(path)
    df.columns = df.columns.str.strip()
    # Clean numeric data
    for col in [size_col, cons_col, prod_col]:
        if df[col].dtype == 'object':
            df[col] = df[col].str.replace(',', '').str.strip().astype(float)
    
    row = df[df[size_col] == target_size]
    if row.empty:
        print(f"!! Warning: Could not find {target_size}MW in {path}. Using nearest available.")
        row = df.iloc[(df[size_col]-target_size).abs().argsort()[:1]]
    
    daily_mwh = row[cons_col].values[0]
    daily_kg = row[prod_col].values[0]
    
    # Efficiency = MWh required to produce 1 kg of H2
    return daily_mwh / daily_kg

# 2. Process Data
print("Calculating efficiencies...")
pem_eff = get_efficiency(pem_file, pem_capacity_mw)
awe_eff = get_efficiency(awe_file, awe_capacity_mw)

# Load hourly wind generation
hourly_gen = pd.read_csv(gen_file)
hourly_gen['GMT_Time'] = pd.to_datetime(hourly_gen['GMT_Time'])

def calculate_fill_time(gen_series, plant_capacity_mw, efficiency):
    # Hourly production = min(available energy, plant capacity) / MWh_per_kg
    # Since hourly generation is in MWh, plant capacity (MW) * 1 hour = MWh capacity
    hourly_h2_kg = gen_series.clip(upper=plant_capacity_mw) / efficiency
    return hourly_h2_kg.cumsum()

# 3. Generate Progress Series
rush_pem = calculate_fill_time(hourly_gen['Rush_Creek_Complex_MWh'], pem_capacity_mw, pem_eff)
rush_awe = calculate_fill_time(hourly_gen['Rush_Creek_Complex_MWh'], awe_capacity_mw, awe_eff)
chey_pem = calculate_fill_time(hourly_gen['Cheyenne_Ridge_MWh'], pem_capacity_mw, pem_eff)
chey_awe = calculate_fill_time(hourly_gen['Cheyenne_Ridge_MWh'], awe_capacity_mw, awe_eff)

# 4. Plotting Function
def plot_storage_fill(pem_series, awe_series, farm_name, filename):
    plt.figure(figsize=(12, 6))
    time_axis = hourly_gen['GMT_Time']
    
    plt.plot(time_axis, pem_series, label=f'PEM ({pem_capacity_mw}MW)', color='#d62728', linewidth=2)
    plt.plot(time_axis, awe_series, label=f'AWE ({awe_capacity_mw}MW)', color='#9467bd', linewidth=2, linestyle='--')
    
    # Storage Limit Line
    plt.axhline(y=storage_target_kg, color='black', linestyle=':', label='Storage Target (10M kg)')
    
    # Identify Fill Date (First time cumulative sum >= target)
    def get_fill_date(series):
        fill_idx = (series >= storage_target_kg).idxmax()
        if series[fill_idx] < storage_target_kg: return "Not filled in 2021"
        return time_axis[fill_idx].strftime('%Y-%m-%d')

    pem_fill = get_fill_date(pem_series)
    awe_fill = get_fill_date(awe_series)

    plt.title(f'{farm_name}: Storage Fill Time (10,000,000 kg H2)\nFill Dates: PEM: {pem_fill} | AWE: {awe_fill}', fontsize=14)
    plt.ylabel('Cumulative Hydrogen (kg)', fontsize=12)
    plt.xlabel('Date (2021)', fontsize=12)
    plt.legend(loc='upper left')
    plt.grid(alpha=0.3)
    plt.ylim(0, storage_target_kg * 1.1)
    plt.tight_layout()
    plt.savefig(filename)
    plt.close()
    print(f"Graph generated: {filename}")

# 5. Create Graphs
plot_storage_fill(rush_pem, rush_awe, 'Rush Creek Complex', 'rush_creek_storage_fill.png')
plot_storage_fill(chey_pem, chey_awe, 'Cheyenne Ridge', 'cheyenne_ridge_storage_fill.png')