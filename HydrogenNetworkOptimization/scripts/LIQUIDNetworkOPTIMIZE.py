import pandas as pd #tabular data handling
import numpy as np #math operations
from pathlib import Path #file path handling
from pymoo.core.problem import ElementwiseProblem #base class for defining optimization problems in pymoo
from pymoo.algorithms.moo.nsga2 import NSGA2 #bring in NSGA-II
from pymoo.optimize import minimize #set function of optimization to minimize
from pymoo.core.callback import Callback #how we track optimization progress in real time and log data for visualization later
import matplotlib.pyplot as plt #for plotting results
import time #track execution time
import psutil #track CPU and RAM usage
import os #for file handling and process information
from pymoo.core.termination import Termination #optimization stopping function 

# --- 1. DIRECTORY & CONFIGURATION --- Set file directory to match your local environment. 
BASE_DIR = Path.home() / "Desktop" / "HydrogenNetworkOptimization"
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "outputs" / "finalized images"
OUTPUT_DIR2 = BASE_DIR / "outputs" / "interactive_maps"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

MAX_RADIUS_MILES = 10.0 #the maximum distance a fleet is will to travel to a station. 
MAX_CAPACITY = 20000 # the maximum capacity of a single station. 

# === NEW: DYNAMIC FOOTPRINT SELECTION ===
# Change this variable to match what footprint you want to run!
# Options: 'liquid', 'gaseous', or 'pipeline'
FOOTPRINT_TYPE = 'liquid' 

FOOTPRINT_COLUMN_MAP = {
    'liquid': 'Liquid Footprint (acres)',
    'gaseous': 'Gaseous Tube-Trailer Footprint (acres)',  # Adjust string if your CSV header differs slightly
    'pipeline': 'Pipeline Footprint (acres)'             # Adjust string if your CSV header differs slightly
}
TARGET_FOOTPRINT_COL = FOOTPRINT_COLUMN_MAP[FOOTPRINT_TYPE]

# --- 2. PROGRESS TRACKING -- How we are saving the progress of the optimization in real time so we can see it in the terminal
class OptimizationCallback(Callback):
    def __init__(self):
        super().__init__()
        self.all_generation_data = []

    def notify(self, algorithm): # Outlines what we are seeing in the terminal as the optimization progresses.
        best_idx = np.argmin(algorithm.pop.get("F")[:, 0])
        best_f = algorithm.pop.get("F")[best_idx]
        print(f"Gen {algorithm.n_gen:03} | Trucks Covered: {int(-best_f[0]):,} | Stations: {int(best_f[1])} | Cost: ${best_f[2]:,.0f}")
        
        current_pop_f = algorithm.pop.get("F").copy() 
        for sol in current_pop_f:
            self.all_generation_data.append([algorithm.n_gen, -sol[0], sol[1], sol[2]])


class CostStabilityTermination(Termination):
    def __init__(self, period=20, tol=1000.0, n_max_gen=200):
        super().__init__()
        self.period = period        # How many generations to look back
        self.tol = tol              # Allowable dollar variance
        self.n_max_gen = n_max_gen  # Absolute safety ceiling generations
        self.cost_history = []

    def _update(self, algorithm):
        # 1. Capture the lowest network land cost from the current generation
        current_costs = algorithm.pop.get("F")[:, 2]
        min_cost = np.min(current_costs)
        self.cost_history.append(min_cost)
        
        # 2. Safety Net: If we hit or exceed the max generation limit, we are finished (progress = 1.0)
        if algorithm.n_gen >= self.n_max_gen:
            print(f"\n[Termination] Reached maximum generation limit ({self.n_max_gen}).")
            return 1.0
            
        # 3. If we haven't even run enough generations to fill our window, keep going (progress = 0.0)
        if algorithm.n_gen < self.period:
            return 0.0
            
        # 4. Check the cost variance over the rolling window
        recent_history = self.cost_history[-self.period:]
        cost_variance = np.max(recent_history) - np.min(recent_history)
        
        # 5. If the variance is within our tolerance, flag convergence (progress = 1.0)
        if cost_variance <= self.tol:
            print(f"\n[Termination] Optimization converged. Best cost has varied by less than ${self.tol} for {self.period} generations.")
            return 1.0
            
        # Otherwise, let the algorithm know it hasn't finished yet
        return 0.0

# --- 3. DATA PREPARATION --- Import data and calculate distance matrix. 
def haversine(lat1, lon1, lat2, lon2): #Measuring the distance between two points on the earth's surface using the Haversine formula.
    R = 3958.8 
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi, dlam = np.radians(lat2 - lat1), np.radians(lon2 - lon1)
    a = np.sin(dphi/2)**2 + np.cos(phi1)*np.cos(phi2)*np.sin(dlam/2)**2
    return 2 * R * np.arcsin(np.sqrt(a))

print("Loading Data...") #Loading inputs: captive fleet depot locations, candidate station sites locations, station footprints for liquid tanker, gaseous tube-trailer, and pipeline delievered stations. 
fleets = pd.read_csv(DATA_DIR / 'geocoded_COcaptive_catex.csv').dropna(subset=['Latitude', 'Longitude'])
sites = pd.read_csv(DATA_DIR / 'geocoded_candidate_sites.csv').dropna(subset=['Latitude', 'Longitude'])
footprint = pd.read_csv(DATA_DIR / 'Footprint.csv')

# Clean Formatting Errors in the candidate site data (remove $ and commas from Price, convert to numeric, fill NaN with 0)
sites['Price'] = sites['Price'].astype(str).str.replace('$', '', regex=False).str.replace(',', '', regex=False).str.strip()
sites['Price'] = pd.to_numeric(sites['Price'], errors='coerce').fillna(0)
sites['Acreage'] = pd.to_numeric(sites['Acreage'], errors='coerce').fillna(0)

print("Pre-calculating Spatial Matrix...") #Pre-calculate the distance matrix between all candidate sites and all fleets to save time during optimization.  
dist_matrix = np.zeros((len(sites), len(fleets)))
for i, s in sites.iterrows():
    dist_matrix[i, :] = haversine(s['Latitude'], s['Longitude'], fleets['Latitude'], fleets['Longitude'])

# --- 4. OPTIMIZATION PROBLEM --- This is where we are defining the optimization problem!!
class HydrogenNetworkOptimization(ElementwiseProblem):
    def __init__(self, sites, fleets, footprint, dist_matrix, target_col):
        super().__init__(n_var=len(sites), n_obj=3, n_constr=1, xl=0, xu=1) #number of sites to investigate, number of objectives, constraint, binary bounds of 0 not chosen or 1 chosen.
        self.sites, self.fleets, self.footprint, self.dist_matrix = sites, fleets, footprint, dist_matrix
        self.target_col = target_col  # Saved as object property

    def _evaluate(self, x, out, *args, **kwargs): #How the optimization problem is evaluated. 
        selected = np.where(x > 0.5)[0] #Is a site chosen?
        if len(selected) == 0: #Penalized if no stations are built (to avoid the algorithm just choosing zero stations to minimize cost).
            out["F"], out["G"] = [0.0, 1000.0, 1e9], [1.0]
            return

        active_count, total_trucks, total_cost = 0, 0, 0.0
        assignments = {s: [] for s in selected}

        # CRITICAL: Fleet Assignment (Closest Station Wins)
        for f_idx in range(len(self.fleets)):
            dists = self.dist_matrix[selected, f_idx]
            if np.min(dists) <= MAX_RADIUS_MILES:
                # Assign to the SINGLE closest station among the current selection
                closest_station = selected[np.argmin(dists)]
                assignments[closest_station].append(f_idx)

        # Capacity & Land Feasibility Check: If the demand exceed the station's capacity or the station's footprint exceeds the available land, we remove fleets it meets constraints. 
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
                    # UPDATED TO USE THE SPECIFIED TARGET FOOTPRINT COLUMN DYNAMICALLY
                    if area_avail >= possible.iloc[0][self.target_col]: 
                        active_count += 1
                        total_trucks += sum(self.fleets.iloc[f]['Trucks'] for f in f_list)
                        total_cost += float(self.sites.iloc[s_idx]['Price'])
                        break
                f_list.pop(-1)

        out["F"] = [float(-total_trucks), float(active_count), total_cost]
        out["G"] = [0.0]

# --- 5. EXECUTION WITH PERFORMANCE & COST CONVERGENCE TRACKING ---
print(f"Starting Evolutionary Optimization (NSGA-II) using [{TARGET_FOOTPRINT_COL}]...")

# Initialize performance tracking
process = psutil.Process(os.getpid())
start_time = time.perf_counter()
start_cpu_time = process.cpu_times()
start_ram = process.memory_info().rss / (1024 * 1024) 

# Stops if the lowest network land cost fluctuates by less than $1,000.00 over 200 generations. 
termination = CostStabilityTermination(period=20, tol=1000.0, n_max_gen=200) 

# Instantiate the problem with our dynamic column choice
problem = HydrogenNetworkOptimization(sites, fleets, footprint, dist_matrix, TARGET_FOOTPRINT_COL)
gen_callback = OptimizationCallback()

# Run the optimization
res = minimize(
    problem, 
    NSGA2(pop_size=100), 
    termination,  # Employs our custom cost tolerance convergence 
    seed=1, 
    callback=gen_callback
)

# Calculate final computational metrics
end_time = time.perf_counter()
end_cpu_time = process.cpu_times()
end_ram = process.memory_info().rss / (1024 * 1024)

execution_time_seconds = end_time - start_time
cpu_user_time = end_cpu_time.user - start_cpu_time.user
peak_ram_used = end_ram - start_ram

print("\n" + "="*40)
print("       COMPUTATIONAL PERFORMANCE       ")
print("="*40)
print(f"Total Generations: {res.algorithm.n_gen} (Stopped via Cost Tolerance Reached (200 max gens possible))")
print(f"Wall-Clock Time  : {execution_time_seconds:.2f} seconds ({execution_time_seconds/60:.2f} minutes)")
print(f"CPU User Time    : {cpu_user_time:.2f} seconds")
print(f"Incremental RAM  : {peak_ram_used:.2f} MB")
print("="*40)

# --- 6. VISUALIZATION: OPTIMIZATION PROCESS MAP ---
if len(gen_callback.all_generation_data) > 0:
    print("\nGenerating Process Map (How the algorithm optimized)...")
    proc_data = np.array(gen_callback.all_generation_data)
    
    # Extract data for clarity
    gens = proc_data[:, 0]
    trucks = proc_data[:, 1]
    stations = proc_data[:, 2]
    costs = proc_data[:, 3]

    fig = plt.figure(figsize=(14, 10))
    ax = fig.add_subplot(111, projection='3d')
    
    cmap = plt.colormaps.get_cmap('coolwarm')
    norm = plt.Normalize(vmin=gens.min(), vmax=gens.max())

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

    # Dynamic file naming based on selection
    plt.savefig(OUTPUT_DIR / f'{FOOTPRINT_TYPE}_optimization_process_map.png', dpi=300)
    plt.show()


# --- 7. FINAL DATA COMPILATION (EXPORTING ALL PARETO SOLUTIONS FOR GIS MAPPING) ---
if res.F is not None:
    print(f"\nCompiling all {len(res.X)} Pareto-optimal solutions for master GIS export...")
    
    master_mapping_rows = []
    summary_rows = []

    for idx in range(len(res.X)):
        selected_indices = np.where(res.X[idx] > 0.5)[0]
        
        unique_assignments = {s: [] for s in selected_indices}
        for f_idx in range(len(fleets)):
            dists = dist_matrix[selected_indices, f_idx]
            if np.min(dists) <= MAX_RADIUS_MILES:
                closest_site_idx = selected_indices[np.argmin(dists)]
                unique_assignments[closest_site_idx].append(f_idx)

        current_solution_capacity = 0
        station_details_for_this_sol = []

        for s_idx in selected_indices:
            f_list = list(unique_assignments[s_idx])
            if not f_list: continue
            
            f_list.sort(key=lambda f: dist_matrix[s_idx, f])
            area_avail = sites.iloc[s_idx]['Acreage']
            
            while f_list:
                demand = sum(fleets.iloc[f]['Daily_Demand'] for f in f_list)
                possible = footprint[footprint['Capacity (kilograms)'] >= demand]
                if not possible.empty and demand <= MAX_CAPACITY:
                    # UPDATED TO USE THE SPECIFIED TARGET FOOTPRINT COLUMN DYNAMICALLY
                    if area_avail >= possible.iloc[0][TARGET_FOOTPRINT_COL]:
                        station_cap = possible.iloc[0]['Capacity (kilograms)']
                        current_solution_capacity += station_cap
                        
                        station_details_for_this_sol.append({
                            'Pareto_Solution_ID': f"Sol_{idx:03d}",
                            'Address': sites.iloc[s_idx]['Address'],
                            'Property_URL': sites.iloc[s_idx].get('Property URL', sites.iloc[s_idx].get('Property_URL', 'N/A')),
                            'City': sites.iloc[s_idx].get('City', 'N/A'),
                            'Acreage': area_avail,
                            'Price': float(sites.iloc[s_idx]['Price']),
                            'Latitude': sites.iloc[s_idx]['Latitude'],
                            'Longitude': sites.iloc[s_idx]['Longitude'],
                            'Daily_Demand_kg': demand,
                            'Station_Capacity_kg': station_cap,
                            'Station_Size': possible.iloc[0]['T-Shirt Size'],
                            'Utilization_Rate': f"{(demand / station_cap) * 100:.2f}%",
                            'Total_Trucks_Served': sum(fleets.iloc[f]['Trucks'] for f in f_list),
                            'Fleet_Breakdown': " | ".join([f"{fleets.iloc[f]['Fleet_Name']} ({int(fleets.iloc[f]['Trucks'])} trucks)" for f in f_list])
                        })
                        break
                f_list.pop(-1)

        for station in station_details_for_this_sol:
            station['Total_System_Capacity_kg'] = current_solution_capacity
            station['Total_System_Trucks_Covered'] = int(-res.F[idx, 0])
            station['Total_System_Land_Cost'] = res.F[idx, 2]
            master_mapping_rows.append(station)

        summary_rows.append({
            'Pareto_Solution_ID': f"Sol_{idx:03d}",
            'Total_System_Capacity_kg': current_solution_capacity,
            'Trucks_Covered': int(-res.F[idx, 0]),
            'Stations_Built': int(res.F[idx, 1]),
            'Total_Land_Cost': res.F[idx, 2],
            'Pareto_Index': idx
        })

    df_master_mapping = pd.DataFrame(master_mapping_rows)
    df_summary = pd.DataFrame(summary_rows)

    df_summary = df_summary.sort_values(by='Total_System_Capacity_kg').reset_index(drop=True)
    summary_rows = df_summary.to_dict(orient='records') 

    if not df_master_mapping.empty:
        df_master_mapping['Formatted_Price'] = df_master_mapping['Price'].apply(lambda val: f"${val:,.2f}")

    # Dynamic File Saving so different configurations don't overwrite each other
    df_master_mapping.to_csv(DATA_DIR / f'all{FOOTPRINT_TYPE.upper()}_pareto_h2_stations_mapping.csv', index=False)
    df_summary.to_csv(DATA_DIR / f'all{FOOTPRINT_TYPE.upper()}_pareto_solutions_summary.csv', index=False)

    print(f"Success! Master GIS File Generated: {DATA_DIR / f'all{FOOTPRINT_TYPE.upper()}_pareto_h2_stations_mapping.csv'}")
    print(f"Master Summary File Generated: {DATA_DIR / f'all{FOOTPRINT_TYPE.upper()}_pareto_solutions_summary.csv'}")

    best_idx = int(df_summary.iloc[len(df_summary)//2]['Pareto_Index'])


# --- 8. VISUALIZATION: MULTI-CAPACITY SCENARIO COMPARISON ---
if 'summary_rows' in locals() and len(summary_rows) > 0:
    print("\nGenerating 3-panel multi-capacity chart with trendline knee points...")
    
    df_summary = pd.DataFrame(summary_rows)
    X = df_summary['Total_System_Capacity_kg'].values
    X_smooth = np.linspace(X.min(), X.max(), 200) 
    
    plt.style.use('default') 
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 6.5)) 
    plt.subplots_adjust(wspace=0.35)

    def find_curve_inflection(x_smooth, y_smooth, tolerance_ratio=0.10):
        x_norm = (x_smooth - x_smooth.min()) / (x_smooth.max() - x_smooth.min())
        y_norm = (y_smooth - y_smooth.min()) / (y_smooth.max() - y_smooth.min())
        p1, p2 = np.array([x_norm[0], y_norm[0]]), np.array([x_norm[-1], y_norm[-1]])
        chord_len = np.linalg.norm(p2 - p1)
        if chord_len == 0: return None
        
        distances = [np.abs(np.cross(p2 - p1, p1 - np.array([x_norm[i], y_norm[i]]))) / chord_len for i in range(len(x_norm))]
        max_idx = np.argmax(distances)
        if distances[max_idx] < tolerance_ratio: return None 
        return x_smooth[max_idx], y_smooth[max_idx]

    # --- Plot 1: Trucks Covered ---
    Y1 = df_summary['Trucks_Covered'].values
    ax1.scatter(X, Y1, color='#004d40', s=40, zorder=3) 
    ax1.grid(True, linestyle=':', alpha=0.5)
    
    p1 = np.polyfit(X, Y1, 2) 
    Y1_smooth = np.polyval(p1, X_smooth)
    r2_1 = 1 - (np.sum((Y1 - np.polyval(p1, X))**2) / np.sum((Y1 - np.mean(Y1))**2))
    eq1 = f"$y = {p1[0]:.2e}x^2 + {p1[1]:.2e}x + {p1[2]:.2f}$"
    ax1.plot(X_smooth, Y1_smooth, color='#00796b', linewidth=2, label=f"Trend: {eq1}\n$R^2 = {r2_1:.4f}$")
    
    inf_result1 = find_curve_inflection(X_smooth, Y1_smooth, tolerance_ratio=0.1)
    if inf_result1 is not None:
        ax1.scatter(inf_result1[0], inf_result1[1], color='red', marker='*', s=200, edgecolors='black', zorder=5)
        ax1.annotate(f"Inflection: {int(inf_result1[0]):,} kg", xy=inf_result1, xytext=(0, 43), textcoords="offset points", color='red', fontweight='bold', ha='center', va='bottom')
    ax1.set_xlabel('Total Network Capacity (kg)', fontweight='bold')
    ax1.set_ylabel('Total Trucks Covered', fontweight='bold')
    ax1.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    ax1.set_title('Fleet Coverage Snapshot', fontweight='bold')
    ax1.legend(loc='upper left', frameon=True)
    
    # --- Plot 2: Total Land Cost ---
    Y2 = df_summary['Total_Land_Cost'].values
    ax2.scatter(X, Y2, color='#b71c1c', marker='s', s=40, zorder=3)
    ax2.grid(True, linestyle=':', alpha=0.5)
    
    p2 = np.polyfit(X, Y2, 2) 
    Y2_smooth = np.polyval(p2, X_smooth)
    r2_2 = 1 - (np.sum((Y2 - np.polyval(p2, X))**2) / np.sum((Y2 - np.mean(Y2))**2))
    eq2 = f"$y = {p2[0]:.2e}x^2 + {p2[1]:.2e}x + {p2[2]:.2e}$"
    ax2.plot(X_smooth, Y2_smooth, color='#c62828', linewidth=2, label=f"Trend: {eq2}\n$R^2 = {r2_2:.4f}$")
    
    inf_result2 = find_curve_inflection(X_smooth, Y2_smooth, tolerance_ratio=0.1)
    if inf_result2 is not None:
        ax2.scatter(inf_result2[0], inf_result2[1], color='red', marker='*', s=200, edgecolors='black', zorder=5)
        ax2.annotate(f"Inflection: {int(inf_result2[0]):,} kg", xy=inf_result2, xytext=(0, -30), textcoords="offset points", color='red', fontweight='bold', ha='center', va='top')
    ax2.set_xlabel('Total Network Capacity (kg)', fontweight='bold')
    ax2.set_ylabel('Total Land Cost ($)', fontweight='bold')
    ax2.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    ax2.get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,}".format(int(x))))
    ax2.set_title('Capital Land Cost Snapshot', fontweight='bold')
    ax2.legend(loc='upper left', frameon=True)
    
    # --- Plot 3: Stations Built ---
    Y3 = df_summary['Stations_Built'].values
    ax3.scatter(X, Y3, color='#455a64', marker='^', s=40, zorder=3) 
    ax3.grid(True, linestyle=':', alpha=0.5)
    
    p3 = np.polyfit(X, Y3, 2) 
    Y3_smooth = np.polyval(p3, X_smooth)
    r2_3 = 1 - (np.sum((Y3 - np.polyval(p3, X))**2) / np.sum((Y3 - np.mean(Y3))**2))
    eq3 = f"$y = {p3[0]:.2e}x^2 + {p3[1]:.2e}x + {p3[2]:.2f}$"
    ax3.plot(X_smooth, Y3_smooth, color='#607d8b', linewidth=2, linestyle='--', label=f"Trend: {eq3}\n$R^2 = {r2_3:.4f}$")
    
    inf_result3 = find_curve_inflection(X_smooth, np.polyval(p3, X_smooth), tolerance_ratio=0.10)
    if inf_result3 is not None:
        ax3.scatter(inf_result3[0], inf_result3[1], color='red', marker='*', s=200, edgecolors='black', zorder=5)
        ax3.annotate(f"Inflection: {int(inf_result3[0]):,} kg", xy=inf_result3, xytext=(0, 15), textcoords="offset points", color='red', fontweight='bold', ha='center', va='bottom')
    ax3.set_xlabel('Total Network Capacity (kg)', fontweight='bold')
    ax3.set_ylabel('Number of Active Stations', fontweight='bold')
    ax3.get_xaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "{:,}".format(int(x))))
    ax3.set_title('Station Count Snapshot', fontweight='bold')
    ax3.legend(loc='upper left', frameon=True)
    
    plt.suptitle(f'{FOOTPRINT_TYPE.capitalize()} Supplied Hydrogen Refueling Infrastructure: Performance Across Capacities', fontsize=15, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'{FOOTPRINT_TYPE}_multi_capacity_3panel_tradeoffs.png', dpi=300, bbox_inches='tight')
    plt.show()


# --- 9. VISUALIZATION: PARETO FRONT PAIRWISE OBJECTIVE ANALYSIS ---
if res.F is not None:
    print("\nGenerating 3 Detailed Pairwise Trade-off Plots...")
    df_pareto = pd.DataFrame({'Trucks Covered': -res.F[:, 0], 'Stations Built': res.F[:, 1], 'Total Land Cost ($)': res.F[:, 2]})
    cols = list(df_pareto.columns)
    
    fig, axes = plt.subplots(1, 3, figsize=(20, 5.5))
    plt.subplots_adjust(wspace=0.3)

    def find_inflection_point(x_arr, y_arr, tolerance_ratio):
        x_norm = (x_arr - x_arr.min()) / (x_arr.max() - x_arr.min()) if x_arr.max() != x_arr.min() else x_arr
        y_norm = (y_arr - y_arr.min()) / (y_arr.max() - y_arr.min()) if y_arr.max() != y_arr.min() else y_arr
        idx_sort = np.argsort(x_norm)
        x_s, y_s = x_norm[idx_sort], y_norm[idx_sort]
        p1, p2 = np.array([x_s[0], y_s[0]]), np.array([x_s[-1], y_s[-1]])
        chord_length = np.linalg.norm(p2 - p1)
        if chord_length == 0: return None
        
        distances = [np.abs(np.cross(p2 - p1, p1 - np.array([x_s[i], y_s[i]]))) / chord_length for i in range(len(x_s))]
        knee_idx = np.argmax(distances)
        if distances[knee_idx] < tolerance_ratio: return None 
        return x_arr[idx_sort[knee_idx]], y_arr[idx_sort[knee_idx]]

    # Plot 1: Trucks vs Stations
    X1, Y1 = df_pareto[cols[0]].values, df_pareto[cols[1]].values
    axes[0].scatter(X1, Y1, alpha=0.5, color='#2e7d32', s=50, label='Pareto Options')
    inf_result1 = find_inflection_point(X1, Y1, tolerance_ratio=0.20)
    if inf_result1 is not None:
        inf_x1, inf_y1 = inf_result1
        axes[0].scatter(inf_x1, inf_y1, color='red', marker='*', s=250, edgecolors='black', zorder=5)
        axes[0].text(inf_x1, inf_y1 + (Y1.max()*0.02), f" {int(inf_x1):,}, {int(inf_y1)} St.", color='red', fontweight='bold', fontsize=9)
    axes[0].set_xlabel(cols[0], fontweight='bold')
    axes[0].set_ylabel(cols[1], fontweight='bold')
    axes[0].set_title(f'{cols[0]} vs {cols[1]}', fontweight='bold')
    axes[0].grid(True, linestyle=':')

    # Plot 2: Trucks vs Cost
    X2, Y2 = df_pareto[cols[0]].values, df_pareto[cols[2]].values
    axes[1].scatter(X2, Y2, alpha=0.5, color='#2e7d32', s=50, label='Pareto Options')
    inf_result2 = find_inflection_point(X2, Y2, tolerance_ratio=0.20)
    if inf_result2 is not None:
        inf_x2, inf_y2 = inf_result2
        axes[1].scatter(inf_x2, inf_y2, color='red', marker='*', s=250, edgecolors='black', zorder=5)
        x_offset, y_offset = -500, Y2.max() * 0.05
        axes[1].text(inf_x2 + x_offset, inf_y2 - y_offset, f" {int(inf_x2):,}, ${inf_y2/1e6:.2f}M", color='red', fontweight='bold', fontsize=9)
    axes[1].set_xlabel(cols[0], fontweight='bold')
    axes[1].set_ylabel(cols[2], fontweight='bold')
    axes[1].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,}".format(int(x))))
    axes[1].set_title(f'{cols[0]} vs {cols[2]}', fontweight='bold')
    axes[1].grid(True, linestyle=':')

    # Plot 3: Stations vs Cost
    X3, Y3 = df_pareto[cols[1]].values, df_pareto[cols[2]].values
    axes[2].scatter(X3, Y3, alpha=0.5, color='#2e7d32', s=50, label='Pareto Options')
    inf_result3 = find_inflection_point(X3, Y3, tolerance_ratio=0.20)
    if inf_result3 is not None:
        inf_x3, inf_y3 = inf_result3
        axes[2].scatter(inf_x3, inf_y3, color='red', marker='*', s=250, edgecolors='black', zorder=5)
        axes[2].text(inf_x3, inf_y3 + (Y3.max()*0.03), f" {int(inf_x3)} St., ${inf_y3/1e6:.2f}M", color='red', fontweight='bold', fontsize=9)
    axes[2].set_xlabel(cols[1], fontweight='bold')
    axes[2].set_ylabel(cols[2], fontweight='bold')
    axes[2].get_yaxis().set_major_formatter(plt.FuncFormatter(lambda x, loc: "${:,}".format(int(x))))
    axes[2].set_title(f'{cols[1]} vs {cols[2]}', fontweight='bold')
    axes[2].grid(True, linestyle=':')

    plt.suptitle(f'{FOOTPRINT_TYPE.capitalize()} Supplied Hydrogen Infrastructure: Pareto Front Breakdown', fontsize=16, fontweight='bold', y=1.02)
    plt.tight_layout()
    plt.savefig(OUTPUT_DIR / f'{FOOTPRINT_TYPE}_detailed_objective_analysis.png', dpi=300, bbox_inches='tight')
    plt.show()