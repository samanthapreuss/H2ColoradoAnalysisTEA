import pandas as pd
import geopandas as gpd
import matplotlib.pyplot as plt
import os
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data" / "2021" 
DATA_DIR2 = BASE_DIR / "data"
OUTPUT_DIR1 = BASE_DIR / "data" / "script_outputs"
OUTPUT_DIR2 = BASE_DIR / "outputs" / "finalize images"

# Ensure output directories exist
OUTPUT_DIR1.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR2.mkdir(parents=True, exist_ok=True)

# Configuration
files = [DATA_DIR / 'Rush Creek I.csv', DATA_DIR / 'Rush Creek II.csv', DATA_DIR / 'Cheyenne Ridge.csv']
geojson_path = DATA_DIR2 / 'colorado_subset.geojson'
cf_column = 'HRRR CF (density and loss adjusted)'

farm_map = {
    'Rush Creek I.csv': 'Rush Creek I',
    'Rush Creek II.csv': 'Rush Creek II',
    'Cheyenne Ridge.csv': 'Cheyenne Ridge'
}

# --- 2. Extract Capacities ---
print("Reading GeoJSON...")
gdf = gpd.read_file(geojson_path)
farm_capacities_kw = {}

for file_str, p_name in farm_map.items():
    # Store using the filename string as the key
    total_cap_kw = gdf[gdf['p_name'].str.strip() == p_name]['t_cap'].sum()
    farm_capacities_kw[file_str] = total_cap_kw
    print(f"-> {p_name}: {total_cap_kw:,.2f} kW")

# --- 3. Define the 2021 GMT Time Range ---
full_year_index = pd.date_range(
    start='2021-01-01 00:00:00', 
    end='2021-12-31 23:00:00', 
    freq='h', 
    tz='GMT'
)

# --- 4. Process Each CSV ---
print("\nProcessing hourly CSV data...")
farm_hourly_mwh = {}
farm_hourly_cf = {}

for file in files:
    name_key = file.name  # Get 'Rush Creek I.csv'
    
    if not file.exists():
        print(f"!! Warning: {file} not found.")
        continue
        
    df = pd.read_csv(file)
    
    # Standardize time
    df['gmt'] = pd.to_datetime(df['gmt'].astype(str), format='%Y%m%d%H')
    if df['gmt'].dt.tz is None:
        df['gmt'] = df['gmt'].dt.tz_localize('GMT')
    
    df = df.set_index('gmt')
    df = df.reindex(full_year_index).fillna(0)
    
    cf_values = pd.to_numeric(df[cf_column], errors='coerce').fillna(0)
    
    # Store using the name_key string
    farm_hourly_mwh[name_key] = (cf_values * farm_capacities_kw[name_key]) / 1000
    farm_hourly_cf[name_key] = cf_values

# --- 5. Combine and Aggregate ---
# Pulling using the exact string keys
rc1_mwh = farm_hourly_mwh.get('Rush Creek I.csv', 0)
rc2_mwh = farm_hourly_mwh.get('Rush Creek II.csv', 0)
rush_creek_complex_mwh = rc1_mwh + rc2_mwh
cheyenne_mwh = farm_hourly_mwh.get('Cheyenne Ridge.csv', 0)

total_fleet_mwh = rush_creek_complex_mwh + cheyenne_mwh

# Weighted Fleet Average CF
total_cap_mw = sum(farm_capacities_kw.values()) / 1000
fleet_avg_cf = total_fleet_mwh / total_cap_mw

# --- 6. Export Hourly CSV ---
hourly_export = pd.DataFrame({
    'GMT_Time': full_year_index,
    'Rush_Creek_Complex_MWh': rush_creek_complex_mwh.values,
    'Cheyenne_Ridge_MWh': cheyenne_mwh.values,
    'Total_of_Both_Farms_MWh': total_fleet_mwh.values,
    'Fleet_Average_CF': fleet_avg_cf.values
})
hourly_export.to_csv(OUTPUT_DIR1 / 'hourly_generation_2021.csv', index=False)

# --- 7. Resample for Monthly Comparison ---
monthly_mwh = hourly_export.set_index('GMT_Time').resample('M').sum()
monthly_cf = hourly_export.set_index('GMT_Time')['Fleet_Average_CF'].resample('M').mean()

monthly_export = monthly_mwh.copy()
monthly_export['Fleet_Average_CF'] = monthly_cf.values
monthly_export.index = monthly_export.index.strftime('%b')
monthly_export.to_csv(OUTPUT_DIR1 / 'monthly_generation_2021.csv', index=False)

# --- 8. Plotting Production ---
print("Generating production graph...")
plt.figure(figsize=(12, 6))
x = range(len(monthly_export.index))
width = 0.35

plt.bar([i - width/2 for i in x], monthly_export['Rush_Creek_Complex_MWh'], width, label='Rush Creek Complex', color='#1f77b4')
plt.bar([i + width/2 for i in x], monthly_export['Cheyenne_Ridge_MWh'], width, label='Cheyenne Ridge', color='#ff7f0e')

plt.title('2021 Monthly Wind Production (MWh)', fontsize=14)
plt.ylabel('Energy Output (MWh)')
plt.xticks(x, monthly_export.index)
plt.legend()
plt.grid(axis='y', linestyle='--', alpha=0.7)
plt.savefig(OUTPUT_DIR2 / 'monthly_production_comparison.png')

# --- 9. Plotting Capacity Factor ---
print("Generating Capacity Factor graph...")
plt.figure(figsize=(12, 6))
plt.plot(monthly_export.index, monthly_export['Fleet_Average_CF'], marker='o', linewidth=3, color='#2ca02c', label='Monthly Avg. CF')

annual_avg_cf = hourly_export['Fleet_Average_CF'].mean()
plt.axhline(y=annual_avg_cf, color='red', linestyle='--', alpha=0.6, label=f'Annual Mean ({annual_avg_cf:.2f})')

plt.title('2021 Monthly Average Capacity Factor for Cheyenne Ridge and Rush Creek', fontsize=14, fontweight='bold')
plt.ylabel('Capacity Factor (0.0 - 1.0)')
plt.xticks(monthly_export.index)
plt.legend()
plt.grid(axis='both', linestyle='--', alpha=0.4)

for i, val in enumerate(monthly_export['Fleet_Average_CF']):
    plt.text(i, val + 0.02, f'{val:.2f}', ha='center', fontweight='bold')

plt.tight_layout()
plt.savefig(OUTPUT_DIR2 / 'monthly_capacity_factor_trend.png')

# --- 10. Yearly Summary ---
yearly_summary = pd.DataFrame({
    'Project': ['Rush Creek Complex', 'Cheyenne Ridge', 'Total Fleet'],
    'Annual_Total_MWh': [rush_creek_complex_mwh.sum(), cheyenne_mwh.sum(), total_fleet_mwh.sum()],
    'Annual_Average_CF': [
        (rush_creek_complex_mwh.sum() / ((farm_capacities_kw['Rush Creek I.csv'] + farm_capacities_kw['Rush Creek II.csv'])/1000 * 8760)),
        (cheyenne_mwh.sum() / (farm_capacities_kw['Cheyenne Ridge.csv']/1000 * 8760)),
        (total_fleet_mwh.sum() / (total_cap_mw * 8760))
    ]
})
yearly_summary.to_csv(OUTPUT_DIR1 / 'yearly_generation_2021.csv', index=False)

print("\nProcessing Complete. All files saved to outputs folder.")