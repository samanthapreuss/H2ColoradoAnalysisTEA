import matplotlib.pyplot as plt
import numpy as np
import os
from pathlib import Path

# --- 1. DIRECTORY CONFIGURATION ---
# Using the same structure from your other ColoradoH2 scripts
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
OUTPUT_DIR = BASE_DIR / "outputs" / "finalize images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# --- 2. DATA & PLOTTING ---
countries = ['China (Mainland)', 'Germany', 'India', 'Japan', 'South Korea', 'United States (California)']
active = [384, 113, 2, 161, 400, 50]
planned = [38, 40, 9, 739, 260, 40]

x = np.arange(len(countries)) * 3.5 
width = 1.0 

fig, ax = plt.subplots(figsize=(22, 12))

active_bars = ax.bar(x - width/2, active, width, label='Active Stations', color='limegreen')
planned_bars = ax.bar(x + width/2, planned, width, label='Planned Stations', color='orange')

def add_labels(rects, ax):
    for rect in rects:
        height = rect.get_height()
        ax.text(rect.get_x() + rect.get_width()/2., height + 5,
                f'{int(height)}', ha='center', va='bottom', 
                fontweight='bold', fontsize=16)

add_labels(active_bars, ax)
add_labels(planned_bars, ax)

ax.set_ylabel('Number of Stations', fontsize=20, fontweight='bold')
ax.set_title('Hydrogen Refueling Station Infrastructure: Active vs. Planned', fontsize=28, fontweight='bold', pad=40)
ax.set_xticks(x)
ax.set_xticklabels(countries, fontsize=16, fontweight='bold')
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.legend(loc='upper left', fontsize=18, frameon=True, shadow=True)
ax.set_ylim(0, 850)

plt.tight_layout()

# --- 3. SAVE THE IMAGE ---
# Use .png for high quality or .pdf for vector graphics
save_path = OUTPUT_DIR / 'globalhydrogen_infrastructure_comparison.png'
plt.savefig(save_path, dpi=300)

print(f"Graph successfully saved to: {save_path}")

plt.show()