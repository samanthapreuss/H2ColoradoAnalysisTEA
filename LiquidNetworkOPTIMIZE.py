import pandas as pd
import numpy as np
from pathlib import Path
from pymoo.core.problem import ElementwiseProblem
from pymoo.algorithms.moo.nsga2 import NSGA2
from pymoo.optimize import minimize
from pymoo.core.callback import Callback
import matplotlib.pyplot as plt

# --- 1. DIRECTORY CONFIGURATION --- Set file directory
BASE_DIR = Path.home() / "Desktop" / "ColoradoH2_AnalysisFinal"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR /"outputs" / "finalize images"
OUTPUT_DIR2 = BASE_DIR / "data" / "script_outputs"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_RADIUS_MILES = 10.0 
MAX_CAPACITY = 20000 

# --- 2. PROGRESS CALLBACK --- This captures how the optimization evaluates different solutions to visualize the process later. 
class OptimizationCallback(Callback):
    def __init__(self):
        super().__init__()
        self.all_generation_data = []

    def notify(self, algorithm):
        best_idx = np.argmin(algorithm.pop.get("F")[:, 0])
        best_f = algorithm.pop.get("F")[best_idx]
        print(f"Gen {algorithm.n_gen:03} | Trucks Covered: {int(-best_f[0]):,} | Hubs: {int(best_f[1])} | Cost: ${best_f[2]:,.0f}")
        
        current_pop_f = algorithm.pop.get("F").copy()
        for sol in current_pop_f:
            self.all_generation_data.append([algorithm.n_gen, -sol[0], sol[1], sol[2]])

# --- 3. DATA PREPARATION --- Calculate distance matrix between fleets and sites.
def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlam = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

print("Loading Data...")
fleets = pd.read_csv(DATA_DIR / 'geocoded_COcaptive_catex.csv').dropna(subset=['Latitude', 'Longitude'])
sites = pd.read_csv(DATA_DIR / 'geocoded_candidate_sites.csv').dropna(subset=['Latitude', 'Longitude'])
footprint = pd.read_csv(DATA_DIR / 'Footprint.csv')

# Clean Site Data
sites['Price'] = sites['Price'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
sites['Price'] = pd.to_numeric(sites['Price'], errors='coerce').fillna(0)
sites['Acreage'] = pd.to_numeric(sites['Acreage'], errors='coerce').fillna(0)

print("Pre-calculating Spatial Matrix...")
dist_matrix = np.zeros((len(sites), len(fleets)))
for i, s in sites.iterrows():
    dist_matrix[i, :] = haversine(s['Latitude'], s['Longitude'], fleets['Latitude'], fleets['Longitude'])

# --- 4. OPTIMIZATION PROBLEM --- NSGA-II optimization applied here
class HydrogenHubOptimization(ElementwiseProblem):
    def __init__(self, sites, fleets, footprint, dist_matrix):
        super().__init__(n_var=len(sites), n_obj=3, n_constr=1, xl=0, xu=1)
        self.sites, self.fleets, self.footprint, self.dist_matrix = sites, fleets, footprint, dist_matrix

    def _evaluate(self, x, out, *args, **kwargs):
        selected = np.where(x > 0.5)[0]
        if len(selected) == 0:
            out["F"], out["G"] = [0.0, 1000.0, 1e9], [1.0]
            return

        active_count, total_trucks, total_cost = 0, 0, 0.0
        assignments = {s: [] for s in selected}

        # CRITICAL: Fleet Assignment (Closest Hub Wins) to ensure that each fleet is only assigned to one station - avoids double counting trucks across multiple sites to improve their ranking
        for f_idx in range(len(self.fleets)):
            dists = self.dist_matrix[selected, f_idx]
            if np.min(dists) <= MAX_RADIUS_MILES:
                # Assign to the SINGLE closest station among the current selection
                closest_hub = selected[np.argmin(dists)]
                assignments[closest_hub].append(f_idx)

        # Capacity & Land Feasibility Check
        for s_idx, f_list in assignments.items(): 
            if not f_list: continue
            f_list.sort(key=lambda f: self.dist_matrix[s_idx, f])
            area_avail = self.sites.iloc[s_idx]['Acreage']
            
            while f_list:
                demand = sum(self.fleets.iloc[f]['Daily_Demand'] for f in f_list)
                if demand > MAX_CAPACITY:
                    f_list.pop(-1)
                    continue
                
                possible = self.footprint[self.footprint['Capacity (kilograms)'] >= demand]
                if not possible.empty:
                    if area_avail >= possible.iloc[0]['Liquid Footprint (acres)']:
                        active_count += 1
                        total_trucks += sum(self.fleets.iloc[f]['Trucks'] for f in f_list)
                        total_cost += float(self.sites.iloc[s_idx]['Price'])
                        break
                f_list.pop(-1)

        out["F"] = [float(-total_trucks), float(active_count), total_cost]
        out["G"] = [0.0]

# --- 5. EXECUTION ---
print("Starting Evolutionary Optimization (NSGA-II)...")
problem = HydrogenHubOptimization(sites, fleets, footprint, dist_matrix)
gen_callback = OptimizationCallback()
res = minimize(problem, NSGA2(pop_size=100), ('n_gen', 200), seed=1, callback=gen_callback)

# --- 6. FINAL DATA COMPILATION (TARGETED CAPACITY SELECTION) ---
if res.F is not None:
    print("\nSearching Pareto Front for Total Capacity ~100,000 kg...")
    TARGET_CAPACITY = 100000
    pareto_solutions_data = []

    # Iterate through all solutions in the Pareto Front to find their total capacity
    for idx in range(len(res.X)):
        selected_indices = np.where(res.X[idx] > 0.5)[0]
        
        # Unique fleet assignment for this specific solution
        unique_assignments = {s: [] for s in selected_indices}
        for f_idx in range(len(fleets)):
            dists = dist_matrix[selected_indices, f_idx]
            if np.min(dists) <= MAX_RADIUS_MILES:
                closest_site_idx = selected_indices[np.argmin(dists)]
                unique_assignments[closest_site_idx].append(f_idx)

        current_solution_capacity = 0
        current_solution_details = []

        for s_idx in selected_indices:
            f_list = list(unique_assignments[s_idx])
            if not f_list: continue
            
            f_list.sort(key=lambda f: dist_matrix[s_idx, f])
            area_avail = sites.iloc[s_idx]['Acreage']
            
            # Match demand to station size (same logic as your original script)
            while f_list:
                demand = sum(fleets.iloc[f]['Daily_Demand'] for f in f_list)
                possible = footprint[footprint['Capacity (kilograms)'] >= demand]
                if not possible.empty and demand <= MAX_CAPACITY:
                    if area_avail >= possible.iloc[0]['Liquid Footprint (acres)']:
                        # This station is valid. Add its rated capacity to the total
                        station_cap = possible.iloc[0]['Capacity (kilograms)']
                        current_solution_capacity += station_cap
                        
                        # Store details for the CSV if this solution wins
                        current_solution_details.append({
                            'Address': sites.iloc[s_idx]['Address'],
                            'Price': f"${sites.iloc[s_idx]['Price']:,.2f}",
                            'Daily_Demand_kg': demand,
                            'Station_Capacity_kg': station_cap,
                            'Station_Size': possible.iloc[0]['T-Shirt Size'],
                            'Utilization_Rate': f"{(demand / station_cap) * 100:.2f}%",
                            'Total_Trucks_Served': sum(fleets.iloc[f]['Trucks'] for f in f_list),
                            'Fleet_Breakdown': " | ".join([f"{fleets.iloc[f]['Fleet_Name']} ({int(fleets.iloc[f]['Trucks'])} trucks)" for f in f_list])
                        })
                        break
                f_list.pop(-1)

        pareto_solutions_data.append({
            'index': idx,
            'total_capacity': current_solution_capacity,
            'details': current_solution_details
        })

    # Find the solution with the total capacity closest to 100,000
    caps = np.array([sol['total_capacity'] for sol in pareto_solutions_data])
    best_idx_by_cap = np.argmin(np.abs(caps - TARGET_CAPACITY))
    winner = pareto_solutions_data[best_idx_by_cap]
    
    # Update best_idx for the visualization sections (7 & 8) to use this capacity-based choice
    best_idx = winner['index']

    print(f"Target: {TARGET_CAPACITY:,} kg | Found: {winner['total_capacity']:,} kg")

    if winner['details']:
        pd.DataFrame(winner['details']).to_csv(OUTPUT_DIR2 / 'final_liquidbalanced_sites_details.csv', index=False)
        print(f"Success! Data exported to: {OUTPUT_DIR2 / 'final_liquidbalanced_sites_details.csv'}")
# --- 7. VISUALIZATION: OPTIMIZATION PROCESS MAP --- This shows how the algorithm explored the solution space across generations, with color indicating generation number (blue = early random guesses, red = later optimized solutions)
if len(gen_callback.all_generation_data) > 0:
    print("\nGenerating Process Map (How the Algorithm optimized)...")
    proc_data = np.array(gen_callback.all_generation_data)
    
    # Extract data for clarity
    gens = proc_data[:, 0]
    trucks = proc_data[:, 1]
    stations = proc_data[:, 2]
    costs = proc_data[:, 3]

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    # Explicitly define the colormap and the normalization range
    # This ensures "Blue" is exactly Gen 1 and "Red" is exactly Gen 200
    cmap = plt.colormaps.get_cmap('coolwarm')
    norm = plt.Normalize(vmin=gens.min(), vmax=gens.max())

    # Plot historical attempts
    # Note: 'c=gens' tells it to color by generation using the 'norm' we just defined
    sc = ax.scatter(trucks, stations, costs, 
                    c=gens, 
                    cmap=cmap, 
                    norm=norm, 
                    s=15, 
                    alpha=0.2, 
                    edgecolors='none')
    
    # Highlight the final Pareto Front
    ax.scatter(-res.F[:, 0], res.F[:, 1], res.F[:, 2], 
               color='green', s=50, edgecolors='white', linewidth=0.5, label='Final Pareto Front')

    # Create the colorbar using the SAME scalar mappable
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = plt.colorbar(sm, ax=ax, shrink=0.5, aspect=10, pad=0.1)
    cbar.set_label('Generation Number (Progress)', fontsize=12)

    ax.set_xlabel('Trucks Covered', labelpad=10)
    ax.set_ylabel('Stations Built', labelpad=10)
    ax.set_zlabel('Land Cost ($)', labelpad=10)
    plt.title('Optimization Progression\n(Blue = Initial Random Guesses | Red = Optimized Frontier)', fontsize=14)
    
    ax.legend(loc='upper left')
    ax.view_init(elev=20, azim=135)

    plt.savefig(OUTPUT_DIR / 'final_liquid_optimization_process_map.png', dpi=300)
    plt.show()

# --- 8. VISUALIZATION: FINAL PARETO FRONT ---
if res.F is not None:
    print("Generating Final Pareto Front Plot...")
    fig = plt.figure(figsize=(12, 9))
    ax = fig.add_subplot(111, projection='3d')

    # All efficient options
    ax.scatter(-res.F[:, 0], res.F[:, 1], res.F[:, 2], c=res.F[:, 2], cmap='viridis', s=50, alpha=0.6)

    # Selected Best Point (The Star)
    best_f = res.F[best_idx]
    ax.scatter(-best_f[0], best_f[1], best_f[2], color='red', marker='*', s=400, edgecolors='black', label='Selected Solution')

    ax.set_xlabel('Trucks Covered')
    ax.set_ylabel('Stations Built')
    ax.set_zlabel('Total Land Cost ($)')
    plt.legend()
    plt.savefig(OUTPUT_DIR / 'final_liquid_pareto_with_selection.png', dpi=300)
    plt.show()

print("\nAll figure outputs generated in:", OUTPUT_DIR)

import pandas as pd
import matplotlib.pyplot as plt

# --- 9. VISUALIZATION: 6-PLOT OBJECTIVE ANALYSIS ---
if res.F is not None:
    print("\nGenerating 6 Detailed Analysis Plots...")
    
    # 1. Prepare Data
    df_pareto = pd.DataFrame({
        'Trucks Covered': -res.F[:, 0],
        'Stations Built': res.F[:, 1],
        'Total Land Cost ($)': res.F[:, 2]
    })
    
    cols = list(df_pareto.columns)
    fig, axes = plt.subplots(2, 3, figsize=(18, 10))
    plt.subplots_adjust(hspace=0.3, wspace=0.3)

    # 2. TOP ROW: Distributions (How many solutions hit certain values?)
    for i, col in enumerate(cols):
        # Using a histogram with a Kernel Density Estimate line
        df_pareto[col].plot(kind='hist', bins=15, ax=axes[0, i], color='#2e7d32', alpha=0.4, edgecolor='black')
        ax2 = axes[0, i].twinx() # Add a density curve on a secondary axis
        df_pareto[col].plot(kind='kde', ax=ax2, color='#1b5e20', lw=2)
        ax2.set_yticks([]) # Hide density numbers for cleanliness
        axes[0, i].set_title(f'Distribution of {col}', fontweight='bold')
        axes[0, i].set_ylabel('Frequency')

    # 3. BOTTOM ROW: Unique Pairwise Trade-offs
    # Plot 4: Trucks vs Stations
    axes[1, 0].scatter(df_pareto[cols[0]], df_pareto[cols[1]], alpha=0.7, edgecolors='w', color='#2e7d32', s=60)
    axes[1, 0].set_xlabel(cols[0]); axes[1, 0].set_ylabel(cols[1])
    axes[1, 0].set_title(f'{cols[0]} vs {cols[1]}')

    # Plot 5: Trucks vs Cost
    axes[1, 1].scatter(df_pareto[cols[0]], df_pareto[cols[2]], alpha=0.7, edgecolors='w', color='#2e7d32', s=60)
    axes[1, 1].set_xlabel(cols[0]); axes[1, 1].set_ylabel(cols[2])
    axes[1, 1].set_title(f'{cols[0]} vs {cols[2]}')

    # Plot 6: Stations vs Cost
    axes[1, 2].scatter(df_pareto[cols[1]], df_pareto[cols[2]], alpha=0.7, edgecolors='w', color='#2e7d32', s=60)
    axes[1, 2].set_xlabel(cols[1]); axes[1, 2].set_ylabel(cols[2])
    axes[1, 2].set_title(f'{cols[1]} vs {cols[2]}')

    # 4. Save and Show
    plt.suptitle('Liquid Hydrogen Refueling Infrastructure: Pareto Front Diagnostic (6 Perspectives)', fontsize=20, y=0.98)
    plt.savefig(OUTPUT_DIR / 'final_liquid_detailed_objective_analysis.png', dpi=300, bbox_inches='tight')
    print(f"[Visual] Analysis plots saved to: {OUTPUT_DIR / 'final_liquid_detailed_objective_analysis.png'}")
    plt.show()