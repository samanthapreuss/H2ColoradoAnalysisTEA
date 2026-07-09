import pandas as pd
from pathlib import Path

# --- CONFIGURATION ---
# SCRIPT_DIR is C:\Users\spreuss\Desktop\HydrogenNetworkOptimization\scripts
SCRIPT_DIR = Path(__file__).resolve().parent

# Go up ONE level to HydrogenNetworkOptimization, then down into 'data'
DATA_DIR = SCRIPT_DIR.parent / 'data'
INPUT_FILE = DATA_DIR / 'geocoded_COcaptive_catex.csv'
OUTPUT_FILE = DATA_DIR / 'geocoded_COcaptive_catex.csv'

# --- PARAMETERS ---
UTILIZATION_RATE = 0.80  # 80% of fleet active daily
H2_EFFICIENCY_KG_MILE = 0.108  # ~6.7 kg / 100 km, projected 2030 fuel efficiency for heavy-duty trucks (kg/mile)

# --- UPDATED SECTOR DAILY MILEAGE (Based on Fleet DNA) ---
SECTOR_MILEAGE = {
    "PUBLIC WORKS": 26.86,
    "PUBLIC TRANSIT": 108.1,
    "SCHOOL TRANSIT": 60.5,
    "CONSTRUCTION MATERIAL AND EQUIPMENT": 96.1,
    "LANDSCAPE AND GROUNDSKEEPING": 96.1,
    "HAULING": 96.1,
    "GENERAL HAULING": 96.1,
    "WASTE MANAGEMENT SERVICES": 75.0, # Kept estimate as placeholder
    "OIL, GAS AND UTILITY SERVICES": 55.0, # Kept estimate as placeholder
    "REFRIGERATED TRANSIT": 108.1, # Conservative estimate matched to transit
    "RENTAL SERVICES": 70.0 # Kept estimate as placeholder
}

def calculate_demand():
    if not INPUT_FILE.exists():
        print(f"Error: Could not find {INPUT_FILE}")
        return

    df = pd.read_csv(INPUT_FILE)
    df.columns = df.columns.str.strip()
    
    # Ensure Categories are standard for matching
    df['Category_Clean'] = df['Category'].str.upper().str.strip()

    def get_demand(row):
        category = row['Category_Clean']
        # Handle cases where 'Trucks' might have been read as a string with commas
        try:
            truck_count = float(str(row['Trucks']).replace(',', ''))
        except:
            truck_count = 0
            
        # Get mileage for sector, default to 80 if category is missing
        avg_miles = SECTOR_MILEAGE.get(category, 80.0)
        
        # FORMULA: (Fleet Size * 80%) * Daily Miles * Efficiency
        daily_kg = (truck_count * UTILIZATION_RATE) * avg_miles * H2_EFFICIENCY_KG_MILE
        return round(daily_kg, 2)

    print("Running demand calculations for Colorado fleets...")
    df['Daily_Demand'] = df.apply(get_demand, axis=1)

    # Clean up and save
    df = df.drop(columns=['Category_Clean'])
    df.to_csv(OUTPUT_FILE, index=False)
    
    print("-" * 30)
    print(f"Success! Demand added to {OUTPUT_FILE.name}")
    print(f"Total Daily H2 Demand: {df['Daily_Demand'].sum():,.2f} kg/day")
    print("-" * 30)

if __name__ == "__main__":
    calculate_demand()