import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib.patches as patches

# --- 1. DIRECTORY CONFIGURATION ---
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
# This is your target destination
OUTPUT_DIR = BASE_DIR / "outputs" / "finalize images" 

# Data extraction
countries = ['China', 'Germany', 'India', 'Japan', 'South Korea', 'USA (CA)']

# Hydrogen Data (Price Per Mile)
h_base = np.array([0.30, 0.72, 0.44, 0.55, 0.26, 2.57])
h_base_err_low = np.array([0.04, 0.10, 0.06, 0.08, 0.04, 0.36])
h_base_err_high = np.array([0.06, 0.14, 0.09, 0.11, 0.05, 0.50])

h_incentive = np.array([0.10, 0.18, 0.03, 0.38, 0.27, 0.39])
h_incentive_err_low = np.array([0.01, 0.03, 0.00, 0.05, 0.04, 0.05])
h_incentive_err_high = np.array([0.02, 0.04, 0.01, 0.07, 0.05, 0.08])

# Diesel Data (Price Per Mile)
d_base = np.array([0.57, 1.07, 0.53, 0.43, 0.55, 0.71])
d_base_err_low = np.array([0.04, 0.07, 0.04, 0.03, 0.04, 0.05])
d_base_err_high = np.array([0.04, 0.08, 0.04, 0.03, 0.04, 0.05])

d_tax = np.array([0.00, 0.30, 0.00, 0.07, 0.00, 0.00])
d_tax_err_low = np.array([0.00, 0.02, 0.00, 0.00, 0.00, 0.00])
d_tax_err_high = np.array([0.00, 0.02, 0.00, 0.01, 0.00, 0.00])

# Calculations
d_total = d_base + d_tax
h_stack_total = h_base + h_incentive

# Spacing
x = np.arange(len(countries)) * 2.0  # More space between countries
width = 0.6

fig, ax = plt.subplots(figsize=(20, 10))

# Colors
c_d_base, c_d_tax = 'blue', 'purple'
c_h_base, c_h_inc = 'orange', 'green'

pos_d = x - width/2
pos_h = x + width/2

# Plot Bars
ax.bar(pos_d, d_base, width, label='Diesel Base', color=c_d_base, zorder=2)
ax.bar(pos_d, d_tax, width, bottom=d_base, label='Diesel Tax', color=c_d_tax, zorder=2)
ax.bar(pos_h, h_base, width, label='Hydrogen Base', color=c_h_base, zorder=2)
ax.bar(pos_h, h_incentive, width, bottom=h_base, label='Hydrogen Incentive', color=c_h_inc, zorder=2)

# --- TWO ERROR MEASUREMENTS PER COLUMN ---
# Diesel Base Error
ax.errorbar(pos_d, d_base, yerr=[d_base_err_low, d_base_err_high], fmt='none', ecolor='black', capsize=4, zorder=4)
# Diesel Tax Error (starts from total height)
ax.errorbar(pos_d, d_total, yerr=[d_tax_err_low, d_tax_err_high], fmt='none', ecolor='black', capsize=4, zorder=4)

# Hydrogen Base Error
ax.errorbar(pos_h, h_base, yerr=[h_base_err_low, h_base_err_high], fmt='none', ecolor='black', capsize=4, zorder=4)
# Hydrogen Incentive Error (starts from total height)
ax.errorbar(pos_h, h_stack_total, yerr=[h_incentive_err_low, h_incentive_err_high], fmt='none', ecolor='black', capsize=4, zorder=4)

def add_label(ax, x_pos, y_bottom, val, threshold=0.15, side='left'):
    if val <= 0: return
    y_center = y_bottom + val/2
    if val < threshold:
        offset = -0.4 if side == 'left' else 0.4
        ax.annotate(f'${val:.2f}', xy=(x_pos, y_center), xytext=(x_pos + offset, y_center),
                    arrowprops=dict(arrowstyle='->', color='black', lw=1),
                    va='center', ha='center', fontweight='bold', color='black', fontsize=11, zorder=6)
    else:
        ax.text(x_pos, y_center, f'${val:.2f}', ha='center', va='center', color='white', fontweight='bold', zorder=6)

# Labels, Outlines, and Totals
for i in range(len(countries)):
    add_label(ax, pos_d[i], 0, d_base[i], side='left')
    add_label(ax, pos_d[i], d_base[i], d_tax[i], side='left')
    add_label(ax, pos_h[i], 0, h_base[i], side='right')
    add_label(ax, pos_h[i], h_base[i], h_incentive[i], side='right')

    # Diesel Total
    ax.text(pos_d[i], d_total[i] + d_tax_err_high[i] + 0.15, f'Total:\n${d_total[i]:.2f}', 
            ha='center', fontweight='bold', color='black', fontsize=13, zorder=7)
    # Hydrogen Total (Base Only Value)
    ax.text(pos_h[i], h_stack_total[i] + h_incentive_err_high[i] + 0.15, f'Total:\n${h_base[i]:.2f}', 
            ha='center', fontweight='bold', color='black', fontsize=13, zorder=7)

    # Red Outlines
    ax.add_patch(patches.Rectangle((pos_d[i] - width/2, 0), width, d_total[i], linewidth=2, edgecolor='red', facecolor='none', zorder=5))
    ax.add_patch(patches.Rectangle((pos_h[i] - width/2, 0), width, h_base[i], linewidth=2, edgecolor='red', facecolor='none', zorder=5))

# Custom Legend
cost_patch = patches.Patch(edgecolor='red', facecolor='none', linewidth=2, label='Cost to consumer')
handles, labels = ax.get_legend_handles_labels()
ax.legend(handles=[cost_patch] + handles, labels=['Cost to consumer'] + labels, loc='upper left', fontsize=20)

ax.set_ylabel('Price Per Mile ($)', fontsize=13)
ax.set_title('Price per Mile: Diesel vs Hydrogen Considering Tax and Incentives', fontsize=30, pad=25, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(countries, fontsize=15)
ax.set_ylim(0, 3.5)
ax.grid(axis='y', linestyle='--', alpha=0.5)

plt.tight_layout()
plt.savefig(OUTPUT_DIR / "Global Price Per Mile.png")
print(f"Graph saved as {OUTPUT_DIR / 'Global Price Per Mile.png'}")