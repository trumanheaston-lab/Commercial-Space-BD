# advanced_launch_trade_study.py
"""Concurrent mission design and launch procurement optimization."""

import math
import numpy as np
import matplotlib.pyplot as plt

MU_EARTH = 3.986004418e14        # Earth gravitational parameter (m^3/s^2)
R_EARTH = 6378137.0              # Earth equatorial radius (meters)
G0 = 9.80665

DRY_SAT_MASS_KG = 400.0
TARGET_ALT_KM = 700.0
TARGET_INC_DEG = 98.2
REVENUE_PER_DAY = 3500.0

SATELLITE_PROPULSION = {
    "Chemical (Monoprop)":  {"Isp": 230.0, "Thrust_N": 20.0,  "Dry_Mass_Fraction": 0.10},
    "Electric (Hall Effect)": {"Isp": 1500.0, "Thrust_N": 0.08, "Dry_Mass_Fraction": 0.25}
}

LAUNCH_VEHICLES = {
    "SpaceX Transporter (Direct)": {
        "max_payload_kg": 1000, "price_base": 350000, "price_base_mass_kg": 50, "price_per_kg": 7000,
        "drop_alt_km": 500.0, "drop_inc_deg": 97.4,
    },
    "SpaceX Transporter (Custom Drop)": {
        "max_payload_kg": 1000, "price_base": 350000, "price_base_mass_kg": 50, "price_per_kg": 7000,
        "drop_alt_km": 400.0, "drop_inc_deg": 97.0,
    },
    "Dedicated Small Launcher": {
        "max_payload_kg": 600, "price_flat": 6500000,
        "drop_alt_km": 700.0, "drop_inc_deg": 98.2,
    }
}

def compute_delta_v(r1, r2, delta_inc_rad):
    """Calculates combined Hohmann transfer and plane-change Delta-V."""
    v1 = math.sqrt(MU_EARTH / r1)
    v2 = math.sqrt(MU_EARTH / r2)
    a_trans = (r1 + r2) / 2.0
    v_pos1 = math.sqrt(MU_EARTH * (2.0/r1 - 1.0/a_trans))
    v_pos2 = math.sqrt(MU_EARTH * (2.0/r2 - 1.0/a_trans))
    dv1 = abs(v_pos1 - v1)
    dv2 = math.sqrt(v_pos2**2 + v2**2 - 2 * v_pos2 * v2 * math.cos(delta_inc_rad))
    return dv1 + dv2

def Tsiolkovsky_fuel_mass(m_dry, dv, isp):
    """Calculates wet mass required to achieve a specific Delta-V."""
    if dv == 0: return 0.0
    return m_dry * (math.exp(dv / (isp * G0)) - 1)

def run_trade_study():
    r_target = (TARGET_ALT_KM * 1000) + R_EARTH
    inc_target_rad = math.radians(TARGET_INC_DEG)
    results = []

    for lv_name, lv in LAUNCH_VEHICLES.items():
        r_drop = (lv["drop_alt_km"] * 1000) + R_EARTH
        inc_drop_rad = math.radians(lv["drop_inc_deg"])
        dv_required = compute_delta_v(r_drop, r_target, abs(inc_target_rad - inc_drop_rad))

        for prop_name, prop in SATELLITE_PROPULSION.items():
            fuel_mass = Tsiolkovsky_fuel_mass(DRY_SAT_MASS_KG, dv_required, prop["Isp"])
            prop_hardware_mass = fuel_mass * prop["Dry_Mass_Fraction"]
            total_wet_mass = DRY_SAT_MASS_KG + fuel_mass + prop_hardware_mass

            if total_wet_mass > lv["max_payload_kg"]:
                continue

            if "price_flat" in lv:
                launch_cost = lv["price_flat"]
            else:
                excess_kg = max(0.0, total_wet_mass - lv["price_base_mass_kg"])
                launch_cost = lv["price_base"] + (excess_kg * lv["price_per_kg"])

            if dv_required == 0:
                transit_days = 0.0
            elif "Electric" in prop_name:
                mass_flow_rate = prop["Thrust_N"] / (prop["Isp"] * G0)
                seconds = fuel_mass / mass_flow_rate
                transit_days = seconds / 86400.0
            else:
                transit_days = 2.0

            revenue_penalty = transit_days * REVENUE_PER_DAY
            total_effective_cost = launch_cost + revenue_penalty
            
            results.append({
                "LV": lv_name,
                "Propulsion": prop_name,
                "Wet Mass (kg)": total_wet_mass,
                "Delta-V (m/s)": dv_required,
                "Transit Time (days)": transit_days,
                "Launch Cost ($)": launch_cost,
                "Effective Cost ($)": total_effective_cost
            })

    return results

# EXECUTION & PLOT GENERATION
results = run_trade_study()

print("="*80)
print(f"      CONCURRENT MISSION DESIGN & PROCUREMENT OPTIMIZATION REPORT")
print(f"      Target Orbit: {TARGET_ALT_KM}km SSO  |  Satellite Dry Mass: {DRY_SAT_MASS_KG}kg")
print("="*80)
print(f"{'Launch Vehicle':<30} | {'Prop Type':<15} | {'Wet Mass':<8} | {'Transit':<7} | {'Effective Cost':<12}")
print("-"*80)

results = sorted(results, key=lambda x: x["Effective Cost ($)"])
for r in results:
    print(f"{r['LV']:<30} | {r['Propulsion']:<15} | {r['Wet Mass (kg)']:>6.1f}kg | {r['Transit Time (days)']:>5.1f}d | ${r['Effective Cost ($)']:>10,.2f}")
print("="*80)

fig, ax = plt.subplots(figsize=(10, 6))
ax.set_facecolor('#fdfdfd')

colors = {'Chemical (Monoprop)': '#d95f02', 'Electric (Hall Effect)': '#7570b3'}

placed_labels = []
for r in results:
    x = r["Transit Time (days)"]
    y = r["Launch Cost ($)"] / 1e6
    ax.scatter(x, y, s=r["Wet Mass (kg)"]*1.5, color=colors[r["Propulsion"]], alpha=0.7, edgecolors='black')
    offset_x = 10 if x >= 5 else -10
    offset_y = 4
    for placed in placed_labels:
        if abs(x - placed["x"]) < 2 and abs(y - placed["y"]) < 0.25:
            offset_y += 14
    placed_labels.append({"x": x, "y": y})
    ha = 'left' if offset_x > 0 else 'right'
    ax.annotate(
        f"{r['LV']}\n${r['Effective Cost ($)']/1e6:.2f}M",
        xy=(x, y), xytext=(offset_x, offset_y), textcoords='offset points',
        ha=ha, va='center', fontsize=7, weight='bold',
        bbox=dict(boxstyle='round,pad=0.2', fc='white', alpha=0.85, ec='gray', lw=0.5),
        arrowprops=dict(arrowstyle='-', color='gray', lw=0.5, shrinkA=0, shrinkB=0)
    )

ax.set_title("The Pareto Frontier: Launch Cost vs. Transit Time to Operational Orbit", fontsize=12, pad=15, weight='bold')
ax.set_xlabel("Transit Time / Orbit Raising Delay (Days)", fontsize=10)
ax.set_ylabel("Raw Launch Cost ($ Millions)", fontsize=10)
ax.grid(True, linestyle='--', alpha=0.5)
ax.set_xlim(-10, max([r["Transit Time (days)"] for r in results]) * 1.3)
ax.set_ylim(0, max([r["Launch Cost ($)"]/1e6 for r in results]) * 1.2)

from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], marker='o', color='w', label='Chemical Propulsion', markerfacecolor='#d95f02', markersize=10),
                   Line2D([0], [0], marker='o', color='w', label='Electric Propulsion', markerfacecolor='#7570b3', markersize=10)]
ax.legend(handles=legend_elements, loc='upper right')

plt.tight_layout()
plt.savefig("delta_v_vs_dollar_v.png", dpi=300)
print("\n[SUCCESS] Architectural trade plot saved as 'delta_v_vs_dollar_v.png'")
