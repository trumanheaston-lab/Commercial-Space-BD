# launch_trade_study.py
# Launch Vehicle Trade Study: 500 kg Payload to SSO
# Truman Heaston
# Compares: Rocket Lab Electron, SpaceX Transporter Rideshare, Exolaunch (via Falcon 9)
# Pricing data sourced from publicly available figures as of 2026

import math
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

# ─────────────────────────────────────────────
# MISSION PARAMETERS
# ─────────────────────────────────────────────

PAYLOAD_MASS_KG = 500.0
TARGET_ORBIT    = "SSO (~550 km)"

# ─────────────────────────────────────────────
# LAUNCH VEHICLE DATABASE
# Data sources:
#   - SpaceX: $350,000 base (50 kg) + $7,000/kg beyond — Transporter-16, 2026
#   - Rocket Lab Electron: ~$7.5M per launch, 300 kg max to LEO, ~$25,000/kg to SSO
#   - Exolaunch: acts as rideshare integrator on Falcon 9; adds ~15-20% margin
#     over raw SpaceX rate for integration, deployer hardware, and mission mgmt
# ─────────────────────────────────────────────

vehicles = {
    "SpaceX Transporter\n(Direct Rideshare)": {
        "type":               "rideshare",
        "max_payload_kg":     1000,          # Falcon 9 rideshare practical cap per slot
        "price_base":         350_000,       # USD — first 50 kg
        "price_base_mass_kg": 50,
        "price_per_kg":       7_000,         # USD/kg beyond base
        "launch_cadence_days":90,            # ~4x per year to SSO
        "reliability":        0.985,         # Falcon 9 success rate
        "orbit_flexibility":  "Low",         # Fixed SSO insertion, no orbit adjust
        "schedule_control":   "Low",         # Shared manifest, SpaceX sets date
        "integration_lead_wks": 26,          # ~6 months from contract to launch
        "notes": "Direct booking via SpaceX rideshare portal. Fixed SSO orbit. "
                 "Payload must conform to ESPA-class interface standards.",
        "color": "#1d9e75",
    },
    "Exolaunch\n(Rideshare Integrator)": {
        "type":               "rideshare_integrator",
        "max_payload_kg":     800,
        "price_base":         350_000,
        "price_base_mass_kg": 50,
        "price_per_kg":       7_000,
        "integrator_margin":  0.18,          # ~18% markup for integration services
        "deployer_fee":       85_000,        # Flat deployer hardware/service fee
        "launch_cadence_days":90,
        "reliability":        0.985,
        "orbit_flexibility":  "Medium",      # Access to Transporter + Bandwagon + Twilight
        "schedule_control":   "Low-Medium",
        "integration_lead_wks": 20,          # Faster due to Exolaunch's standing manifest
        "notes": "Full-service integrator. Handles dispensers, LEOP support, "
                 "vibration/EMC testing coordination. Access to SSO, mid-inc, dawn-dusk.",
        "color": "#534ab7",
    },
    "Rocket Lab\nElectron": {
        "type":               "dedicated",
        "max_payload_kg":     300,           # Hard cap — 300 kg to LEO, ~200 kg to SSO
        "price_per_launch":   7_500_000,     # ~$7.5M per dedicated launch
        "launch_cadence_days":30,            # High cadence from NZ + VA pads
        "reliability":        0.952,         # 83/87 success rate as of 2026
        "orbit_flexibility":  "High",        # Any inclination, any RAAN, precise injection
        "schedule_control":   "High",        # Dedicated — you own the manifest
        "integration_lead_wks": 12,          # Faster for dedicated small missions
        "notes": "Dedicated small launch. Precise orbital insertion. "
                 "500 kg EXCEEDS Electron capacity — flagged as infeasible.",
        "color": "#d85a30",
    },
}

# ─────────────────────────────────────────────
# COST MODEL
# ─────────────────────────────────────────────

def compute_cost(vehicle_name, vehicle, payload_kg):
    """
    Returns (total_cost_usd, cost_per_kg, feasible, note)
    """
    vtype = vehicle["type"]
    max_kg = vehicle["max_payload_kg"]

    if payload_kg > max_kg:
        return None, None, False, f"INFEASIBLE: {payload_kg} kg exceeds max capacity {max_kg} kg"

    if vtype == "dedicated":
        total = vehicle["price_per_launch"]
        cpk   = total / payload_kg
        return total, cpk, True, "Dedicated launch — full vehicle cost regardless of payload mass"

    elif vtype == "rideshare":
        base_mass = vehicle["price_base_mass_kg"]
        base_cost = vehicle["price_base"]
        excess_kg = max(0, payload_kg - base_mass)
        total = base_cost + excess_kg * vehicle["price_per_kg"]
        cpk   = total / payload_kg
        return total, cpk, True, "Rideshare pricing: base slot + excess mass"

    elif vtype == "rideshare_integrator":
        base_mass = vehicle["price_base_mass_kg"]
        base_cost = vehicle["price_base"]
        excess_kg = max(0, payload_kg - base_mass)
        raw_launch_cost = base_cost + excess_kg * vehicle["price_per_kg"]
        margin_cost     = raw_launch_cost * vehicle["integrator_margin"]
        deployer_fee    = vehicle["deployer_fee"]
        total = raw_launch_cost + margin_cost + deployer_fee
        cpk   = total / payload_kg
        return total, cpk, True, "Rideshare base + integrator margin + deployer hardware fee"

    return None, None, False, "Unknown vehicle type"


# ─────────────────────────────────────────────
# SCORING MODEL  (weighted multi-criteria)
# ─────────────────────────────────────────────
# Weights reflect typical commercial smallsat operator priorities

WEIGHTS = {
    "cost_score":        0.40,
    "schedule_score":    0.20,
    "orbit_score":       0.20,
    "reliability_score": 0.20,
}

flexibility_map = {"Low": 1, "Low-Medium": 2, "Medium": 3, "Medium-High": 4, "High": 5}
schedule_map    = {"Low": 1, "Low-Medium": 2, "Medium": 3, "Medium-High": 4, "High": 5}

def score_vehicles(results):
    """Normalize and weight scores across feasible vehicles."""
    feasible = {k: v for k, v in results.items() if v["feasible"]}
    if not feasible:
        return {}

    costs = [v["total_cost"] for v in feasible.values()]
    min_cost, max_cost = min(costs), max(costs)

    scored = {}
    for name, data in feasible.items():
        v = vehicles[name]
        cost_score = 1 - (data["total_cost"] - min_cost) / (max_cost - min_cost + 1)
        orbit_score = flexibility_map.get(v["orbit_flexibility"], 1) / 5
        sched_score = schedule_map.get(v["schedule_control"], 1) / 5
        rel_score   = v["reliability"]

        weighted = (
            WEIGHTS["cost_score"]        * cost_score +
            WEIGHTS["schedule_score"]    * sched_score +
            WEIGHTS["orbit_flexibility"] * orbit_score
            if "orbit_flexibility" in WEIGHTS else 0
        )
        weighted = (
            cost_score        * WEIGHTS["cost_score"] +
            sched_score       * WEIGHTS["schedule_score"] +
            orbit_score       * WEIGHTS["orbit_score"] +
            rel_score         * WEIGHTS["reliability_score"]
        )
        scored[name] = {**data, "weighted_score": round(weighted, 4)}

    return scored


# ─────────────────────────────────────────────
# RUN ANALYSIS
# ─────────────────────────────────────────────

results = {}
for name, v in vehicles.items():
    total, cpk, feasible, note = compute_cost(name, v, PAYLOAD_MASS_KG)
    results[name] = {
        "total_cost":   total,
        "cost_per_kg":  cpk,
        "feasible":     feasible,
        "note":         note,
        "reliability":  v["reliability"],
        "orbit_flex":   v["orbit_flexibility"],
        "sched_ctrl":   v["schedule_control"],
        "cadence_days": v["launch_cadence_days"],
        "lead_wks":     v["integration_lead_wks"],
        "color":        v["color"],
    }

scored = score_vehicles(results)

# ─────────────────────────────────────────────
# PRINT REPORT
# ─────────────────────────────────────────────

SEP = "─" * 65

print(f"\n{SEP}")
print(f"  LAUNCH VEHICLE TRADE STUDY")
print(f"  Mission: {PAYLOAD_MASS_KG} kg to {TARGET_ORBIT}")
print(SEP)

for name, r in results.items():
    label = name.replace("\n", " ")
    print(f"\n  {label}")
    print(f"  {'Feasible':<22} {'YES' if r['feasible'] else 'NO — ' + r['note']}")
    if r["feasible"]:
        print(f"  {'Total Cost':<22} ${r['total_cost']:>12,.0f}")
        print(f"  {'Cost per kg':<22} ${r['cost_per_kg']:>12,.0f} /kg")
        print(f"  {'Reliability':<22} {r['reliability']*100:.1f}%")
        print(f"  {'Orbit Flexibility':<22} {r['orbit_flex']}")
        print(f"  {'Schedule Control':<22} {r['sched_ctrl']}")
        print(f"  {'Launch Cadence':<22} Every ~{r['cadence_days']} days")
        print(f"  {'Integration Lead':<22} ~{r['lead_wks']} weeks")
        if name in scored:
            print(f"  {'Weighted Score':<22} {scored[name]['weighted_score']:.3f} / 1.000")
    print(f"  {r['note']}")

print(f"\n{SEP}")
feasible_scored = {k: v for k, v in scored.items() if v["feasible"]}
if feasible_scored:
    best = max(feasible_scored, key=lambda k: feasible_scored[k]["weighted_score"])
    print(f"  RECOMMENDATION: {best.replace(chr(10), ' ')}")
    print(f"  Weighted score: {scored[best]['weighted_score']:.3f}")
print(SEP)

# ─────────────────────────────────────────────
# COST SENSITIVITY: vary payload mass 50–500 kg
# ─────────────────────────────────────────────

mass_range = np.linspace(50, 500, 200)

sensitivity = {name: [] for name in vehicles}
for m in mass_range:
    for name, v in vehicles.items():
        total, cpk, feasible, _ = compute_cost(name, v, m)
        sensitivity[name].append(total if feasible else None)

# ─────────────────────────────────────────────
# PLOTTING
# ─────────────────────────────────────────────

fig, axes = plt.subplots(2, 2, figsize=(14, 10))
fig.patch.set_facecolor("#f8f8f6")
for ax in axes.flatten():
    ax.set_facecolor("#f8f8f6")

plt.rcParams.update({
    "font.family":    "monospace",
    "axes.spines.top":    False,
    "axes.spines.right":  False,
})

SHORT_NAMES = {
    "SpaceX Transporter\n(Direct Rideshare)":    "SpaceX Direct",
    "Exolaunch\n(Rideshare Integrator)":          "Exolaunch",
    "Rocket Lab\nElectron":                       "Electron",
}

# ── Plot 1: Total mission cost at 500 kg ──────────────────────────────────────
ax1 = axes[0, 0]
feasible_names  = [n for n, r in results.items() if r["feasible"]]
infeasible_names= [n for n, r in results.items() if not r["feasible"]]
bar_labels  = [SHORT_NAMES[n] for n in feasible_names]
bar_costs   = [results[n]["total_cost"] / 1_000_000 for n in feasible_names]
bar_colors  = [results[n]["color"] for n in feasible_names]

bars = ax1.bar(bar_labels, bar_costs, color=bar_colors, width=0.5, zorder=2)
for bar, cost in zip(bars, bar_costs):
    ax1.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.05,
             f"${cost:.2f}M", ha="center", va="bottom", fontsize=9, fontfamily="monospace")

for name in infeasible_names:
    ax1.text(0.5, 0.5, f"{SHORT_NAMES[name]}: INFEASIBLE\n(payload exceeds capacity)",
             transform=ax1.transAxes, ha="center", va="center",
             fontsize=8, color="#d85a30", fontfamily="monospace",
             bbox=dict(boxstyle="round,pad=0.3", facecolor="#faece7", edgecolor="#d85a30", alpha=0.8))

ax1.set_title("Total Mission Cost @ 500 kg", fontsize=11, pad=10, fontfamily="monospace")
ax1.set_ylabel("Cost (USD millions)", fontsize=9, fontfamily="monospace")
ax1.set_ylim(0, max(bar_costs) * 1.25 if bar_costs else 5)
ax1.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))
ax1.grid(axis="y", alpha=0.3, zorder=1)
ax1.tick_params(labelsize=9)

# ── Plot 2: Cost sensitivity by mass ─────────────────────────────────────────
ax2 = axes[0, 1]
for name, costs in sensitivity.items():
    valid_m = [mass_range[i] for i, c in enumerate(costs) if c is not None]
    valid_c = [c / 1_000_000 for c in costs if c is not None]
    if valid_m:
        ax2.plot(valid_m, valid_c, color=results[name]["color"],
                 linewidth=2, label=SHORT_NAMES[name])
        # mark 500 kg point
        total_at_500, _, feasible, _ = compute_cost(name, vehicles[name], 500)
        if feasible:
            ax2.scatter([500], [total_at_500 / 1_000_000],
                        color=results[name]["color"], s=60, zorder=5)

ax2.axvline(500, color="#888780", linestyle="--", linewidth=1, alpha=0.6, label="Your payload (500 kg)")
ax2.set_title("Cost Sensitivity: 50–500 kg Payload", fontsize=11, pad=10, fontfamily="monospace")
ax2.set_xlabel("Payload Mass (kg)", fontsize=9, fontfamily="monospace")
ax2.set_ylabel("Total Cost (USD millions)", fontsize=9, fontfamily="monospace")
ax2.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.1f}M"))
ax2.legend(fontsize=8, framealpha=0.5)
ax2.grid(alpha=0.3)
ax2.tick_params(labelsize=9)

# ── Plot 3: Cost per kg ───────────────────────────────────────────────────────
ax3 = axes[1, 0]
feasible_cpk    = [results[n]["cost_per_kg"] / 1000 for n in feasible_names]
bars3 = ax3.bar(bar_labels, feasible_cpk, color=bar_colors, width=0.5, zorder=2)
for bar, cpk in zip(bars3, feasible_cpk):
    ax3.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.2,
             f"${cpk:.1f}K/kg", ha="center", va="bottom", fontsize=9, fontfamily="monospace")

ax3.set_title("Cost per Kilogram @ 500 kg", fontsize=11, pad=10, fontfamily="monospace")
ax3.set_ylabel("Cost (USD thousands / kg)", fontsize=9, fontfamily="monospace")
ax3.yaxis.set_major_formatter(plt.FuncFormatter(lambda x, _: f"${x:.0f}K"))
ax3.grid(axis="y", alpha=0.3, zorder=1)
ax3.tick_params(labelsize=9)

# ── Plot 4: Weighted scorecard (radar-style bar) ──────────────────────────────
ax4 = axes[1, 1]
categories    = ["Cost\n(40%)", "Schedule\nControl\n(20%)", "Orbit\nFlex\n(20%)", "Reliability\n(20%)"]
n_cats        = len(categories)
bar_width     = 0.2
x             = np.arange(n_cats)

for i, name in enumerate(feasible_names):
    v = vehicles[name]
    cost_score = 1 - (results[name]["total_cost"] - min(results[n]["total_cost"] for n in feasible_names)) / \
                 max(1, max(results[n]["total_cost"] for n in feasible_names) - min(results[n]["total_cost"] for n in feasible_names))
    orbit_score = flexibility_map.get(v["orbit_flexibility"], 1) / 5
    sched_score = schedule_map.get(v["schedule_control"], 1) / 5
    rel_score   = v["reliability"]
    scores = [cost_score, sched_score, orbit_score, rel_score]
    ax4.bar(x + i * bar_width, scores, width=bar_width,
            color=results[name]["color"], label=SHORT_NAMES[name], zorder=2, alpha=0.85)

ax4.set_xticks(x + bar_width * (len(feasible_names) - 1) / 2)
ax4.set_xticklabels(categories, fontsize=8, fontfamily="monospace")
ax4.set_yticks([0, 0.25, 0.5, 0.75, 1.0])
ax4.set_yticklabels(["0", "0.25", "0.50", "0.75", "1.00"], fontsize=8)
ax4.set_title("Scorecard by Criterion", fontsize=11, pad=10, fontfamily="monospace")
ax4.set_ylabel("Normalized Score (0–1)", fontsize=9, fontfamily="monospace")
ax4.legend(fontsize=8, framealpha=0.5)
ax4.grid(axis="y", alpha=0.3, zorder=1)
ax4.tick_params(labelsize=8)

# ── Global title ──────────────────────────────────────────────────────────────
fig.suptitle(
    f"Launch Vehicle Trade Study  |  {PAYLOAD_MASS_KG} kg to {TARGET_ORBIT}  |  2026 Pricing",
    fontsize=13, fontfamily="monospace", y=1.01
)

plt.tight_layout()
plt.savefig("/home/claude/launch_trade_study/launch_trade_study.png",
            dpi=150, bbox_inches="tight", facecolor=fig.get_facecolor())
plt.close()
print("\n  Chart saved → launch_trade_study.png")
