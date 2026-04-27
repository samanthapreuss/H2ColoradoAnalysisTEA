import pandas as pd
from pathlib import Path

# --- 1. CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "data" / "script_outputs"
DATA_DIR.mkdir(parents=True, exist_ok=True)

daily_production_kg = 120000
months_info = [
    ("Jan", 31), ("Feb", 28), ("Mar", 31), ("Apr", 30),
    ("May", 31), ("Jun", 30), ("Jul", 31), ("Aug", 31),
    ("Sep", 30), ("Oct", 31), ("Nov", 30), ("Dec", 31)
]

def generate_demand_csv(tech_name, efficiency, filename):
    # Daily Electricity in MWh
    daily_mwh = (daily_production_kg * efficiency) / 1000
    

    data = {

        "Kg Production / Day": [daily_production_kg],
        "Avg Daily Electricity (MWh)": [round(daily_mwh, 2)]
    }

    # Generate columns for each month
    for month, days in months_info:
        data[f"{month}_Consumption_MWh"] = [round(daily_mwh * days, 2)]

    df = pd.DataFrame(data)
    df.to_csv(OUTPUT_DIR / filename, index=False)
    print(f"File saved: {filename}")

# Execute for both technologies
generate_demand_csv("PEM", 43.64, "PEM_Monthly_Demand.csv")
generate_demand_csv("AWE", 52.4, "AWE_Monthly_Demand.csv")