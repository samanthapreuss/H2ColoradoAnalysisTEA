import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.patches import Patch

# 1. Data Setup
data = {
    'Country': ['China (Mainland)', 'Germany', 'India', 'Japan', 'South Korea', 'United States (California)'],
    'Diesel_Base': [4.00, 9.56, 3.70, 3.52, 3.82, 4.06],
    'Diesel_Tax': [0.00, 2.08, 0.00, 0.48, 0.00, 0.90],
    'H2_Base': [3.82, 9.21, 5.65, 7.08, 3.37, 32.94],
    'H2_Incentive': [1.26, 2.35, 0.40, 4.83, 3.50, 5.00]
}

df = pd.DataFrame(data)

# 2. Configuration
countries = df['Country']
x = np.arange(len(countries)) * 7.5  # Wider spacing for leader lines
width = 2.2                          
font_size_labels = 15
font_size_totals = 20

fig, ax = plt.subplots(figsize=(26, 16))

# 3. Plotting Bars
d_base = ax.bar(x - width/2, df['Diesel_Base'], width, label='Diesel Base', color='royalblue')
d_tax = ax.bar(x - width/2, df['Diesel_Tax'], width, bottom=df['Diesel_Base'], label='Diesel Tax', color='deeppink')

h_base = ax.bar(x + width/2, df['H2_Base'], width, label='Hydrogen Base', color='orange')
h_incentive = ax.bar(x + width/2, df['H2_Incentive'], width, bottom=df['H2_Base'], label='H2 Incentive', color='limegreen')

# 4. Smart Labeling with Leader Lines
def add_smart_labels(rects, ax, side='left'):
    for rect in rects:
        height = rect.get_height()
        if height <= 0: continue
            
        y_pos = rect.get_y() + height / 2
        x_pos = rect.get_x() + rect.get_width() / 2
        
        # Threshold: Move labels outside if value is less than $1.00
        if height < 1.0:
            x_offset = -2.0 if side == 'left' else 2.0
            ha = 'right' if side == 'left' else 'left'
            
            # Leader line annotation
            ax.annotate(f'${height:.2f}', 
                        xy=(x_pos, y_pos), 
                        xytext=(x_pos + x_offset, y_pos),
                        arrowprops=dict(arrowstyle='-', color='black', lw=1.5),
                        va='center', ha=ha, fontsize=font_size_labels + 2,
                        fontweight='bold', color='black')
        else:
            # Internal label for larger values
            ax.text(x_pos, y_pos, f'${height:.2f}', ha='center', va='center', 
                    color='white', fontweight='bold', fontsize=font_size_labels)

add_smart_labels(d_base, ax, side='left')
add_smart_labels(d_tax, ax, side='left')
add_smart_labels(h_base, ax, side='right')
add_smart_labels(h_incentive, ax, side='right')

# 5. Adding Red Boxes and Floating Totals (Offset to clear incentives)
for i in range(len(countries)):
    # Diesel
    total_d = df['Diesel_Base'][i] + df['Diesel_Tax'][i]
    rect_d = plt.Rectangle((x[i] - width, 0), width, total_d, 
                           linewidth=4, edgecolor='red', facecolor='none', zorder=10)
    ax.add_patch(rect_d)
    ax.text(x[i] - width/2, total_d + 1.5, f'Total:\n${total_d:.2f}', 
            ha='center', color='red', fontweight='bold', fontsize=font_size_totals)

    # Hydrogen
    total_h = df['H2_Base'][i]
    total_phys_h = total_h + df['H2_Incentive'][i]
    rect_h = plt.Rectangle((x[i], 0), width, total_h, 
                           linewidth=4, edgecolor='red', facecolor='none', zorder=10)
    ax.add_patch(rect_h)
    # Positions label above the green incentive bar but shows base price
    ax.text(x[i] + width/2, total_phys_h + 1.5, f'Total:\n${total_h:.2f}', 
            ha='center', color='red', fontweight='bold', fontsize=font_size_totals)

# 6. Custom Legend
handles, labels = ax.get_legend_handles_labels()
red_box_proxy = Patch(facecolor='none', edgecolor='red', linewidth=3, 
                      label='Total Consumer Price (Excl. Incentives)')
handles.append(red_box_proxy)
ax.legend(handles=handles, loc='upper left', fontsize=16, frameon=True, shadow=True)

# 7. Formatting
ax.set_ylabel('Cost per Unit ($)', fontsize=20, fontweight='bold')
ax.set_title('Diesel vs. Hydrogen Fuel Costs Across the World', fontsize=28, fontweight='bold', pad=40)
ax.set_xticks(x)
ax.set_xticklabels(countries, fontsize=16, fontweight='bold')
ax.grid(axis='y', linestyle='--', alpha=0.4)
ax.set_ylim(0, 50)

plt.tight_layout()
plt.show()