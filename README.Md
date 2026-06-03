# Launch Vehicle Trade Study

**Mission:** Deploy a 500 kg satellite to Sun-Synchronous Orbit (SSO, ~550 km)  
**Author:** Truman Heaston  
**Pricing Data:** 2026 publicly available figures  

---

## What This Is

A multi-criteria trade study comparing commercial launch options for a 500 kg smallsat mission. Goes beyond raw cost-per-kg to model the tradeoffs operators actually face: orbit flexibility, schedule control, integration lead time, and reliability.

This bridges the gap between orbital mechanics and launch economics — the kind of analysis a technical BD team runs when a customer asks "what's the best way to get my satellite up?"

---

## Vehicles Compared

| Vehicle | Type | Max Payload (SSO) | Cost Model |
|---|---|---|---|
| SpaceX Transporter (Direct) | Rideshare | ~1000 kg/slot | $350K base (50 kg) + $7,000/kg |
| Exolaunch (Integrator) | Rideshare via Falcon 9 | ~800 kg | SpaceX rate + 18% margin + $85K deployer fee |
| Rocket Lab Electron | Dedicated | 200–300 kg | ~$7.5M flat per launch |

---

## Key Findings (500 kg payload)

**Electron: INFEASIBLE.** 500 kg exceeds Electron's maximum SSO capacity (~200–300 kg). Electron is the right answer for payloads under ~150 kg that require precise orbital insertion or scheduling control.

**SpaceX Direct: $3.5M total, $7,000/kg.** Cheapest option by a wide margin at this mass. Trade-off: low orbit flexibility (fixed SSO insertion point), low schedule control (shared manifest), and 26-week integration lead.

**Exolaunch: $4.2M total, $8,430/kg.** ~20% premium over direct SpaceX booking. What you're buying: dedicated mission management, access to multiple orbit types (SSO, Bandwagon mid-inc, Twilight dawn-dusk), faster integration pipeline, and deployer hardware. Worth it if your mission requires a specific LTAN or non-standard SSO.

**Recommendation:** SpaceX Direct Rideshare wins on cost for a standard SSO mission. Exolaunch wins if orbit flexibility or dedicated integration support justifies the premium.

---

## Weighted Scoring Methodology

Criteria weighted to reflect typical commercial operator priorities:

| Criterion | Weight | Rationale |
|---|---|---|
| Cost | 40% | Dominant factor for most commercial missions |
| Orbit Flexibility | 20% | Critical for EO, comms, and DoD payloads |
| Schedule Control | 20% | Constellation timing and launch windows |
| Reliability | 20% | Mission risk |

---

## Cost Sensitivity

The script models costs across 50–500 kg to show where each vehicle's economics break. Key crossover: below ~100 kg, Exolaunch's integration services add less relative cost; above ~300 kg, Electron is entirely out of the picture.

---

## How to Run

```bash
python launch_trade_study.py
```

Outputs:
- Terminal report with full cost breakdown and weighted scores
- `launch_trade_study.png` — 4-panel chart (mission cost, cost sensitivity, cost/kg, scorecard)

Dependencies: `matplotlib`, `numpy`

```bash
pip install matplotlib numpy
```

---

## Data Sources

- SpaceX rideshare pricing: Transporter-16 manifest, NewSpaceEconomy (Feb 2026)
- Rocket Lab Electron specs: Wikipedia, RocketLab investor presentations
- Exolaunch pricing model: Exolaunch public statements, industry estimates
- Reliability figures: Launch history databases as of Q1 2026

---

## Limitations & Future Work

- Does not model last-mile orbit raising (propulsion cost to reach final orbit from SSO insertion)
- Exolaunch margin is estimated — actual pricing requires direct quote
- Does not include launch insurance (~5–10% of launch cost)
- Future: add Firefly Alpha and Rocket Lab Neutron (when pricing is public) for medium-lift comparison
- Future: integrate delta-V cost layer from `hohmann_sandbox.py` to model full mission economics end-to-end
