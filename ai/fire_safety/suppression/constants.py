"""Sourced constants for the Suppression Advisor.

Every value carries its source; the full citations and page context are in
``docs/data/SUPPRESSION_SOURCES.md``. Values marked ``ASSUMPTION`` are user-adjustable defaults,
not facts, and the API labels them as such.
"""
from __future__ import annotations

LB_TO_KG = 0.45359237
R = 8.314462618               # J/(mol·K)
MMHG_PER_KPA = 760.0 / 101.325

M_CO2 = 44.0095e-3            # kg/mol
M_N2 = 28.0134e-3
M_H2O = 18.01528e-3

# --- Extinguisher charges -------------------------------------------------------------------
# ISS CO2 PFE: "6 lbs of CO2 at 850 psi; discharges in 45 sec".
# Ruff, Hicks, Pettegrew, NASA/CP-2004-213205/VOL2 p. 357, NTRS 20040161262.
CO2_PFE = {"agent_kg": 6.0 * LB_TO_KG, "discharge_s": 45.0,
           "source": "NTRS 20040161262 (NASA/CP-2004-213205/VOL2, p. 357)"}
# ISS Fine Water Mist PFE: "6 pounds (lbs) of water and 1.2 lbs of nitrogen pressurized to approximately 1270 psia".
# Rodriguez & Young, NTRS 20130011664.
FWM_PFE = {"water_kg": 6.0 * LB_TO_KG, "nitrogen_kg": 1.2 * LB_TO_KG,
           "source": "NTRS 20130011664 (Development of the ISS Fine Water Mist PFE)"}

# --- Thermochemistry: H°(1600 K) − H°(298.15 K), kJ/mol, NIST-JANAF via the NIST Chemistry WebBook ---
# 1600 K is the reference flame temperature of the effective-enthalpy criterion (Sheinson et al. 1989,
# as used by Ruff et al., NTRS 20040161262 p. 361).
T_REF_K = 298.15
T_FLAME_K = 1600.0
DH_GAS_KJ = {
    "N2": 41.90,     # webbook.nist.gov, ID C7727379, JANAF table
    "O2": 44.27,     # ID C7782447
    "CO2": 67.57,    # ID C124389
    "H2O": 52.91,    # ID C7732185 (gas)
    "He": 2.5 * R * (T_FLAME_K - T_REF_K) / 1000.0,   # monatomic ideal gas, cp = 5/2 R (27.06 kJ/mol)
}
# Liquid water at 298.15 K -> vapour at 1600 K, by Hess's law: ΔvapH°(298.15) = ΔfH°(g) − ΔfH°(l)
# = −241.826 − (−285.830) = 44.004 kJ/mol (NIST WebBook, ID C7732185), plus the gas-phase ΔH above.
DH_WATER_LIQUID_TO_1600_KJ = 44.004 + DH_GAS_KJ["H2O"]   # 96.91 kJ/mol
KJ_PER_KCAL = 4.184

# Normal-gravity suppression threshold for PMMA, used as a literature sanity check only (never fitted on):
# "Normal gravity suppression is at 63.2 kcal/mol O2" (Ruff et al., NTRS 20040161262, p. 362).
# Huggett's threshold heat capacity, 40–50 cal/(°C·mol O2) at 1 atm (same source, p. 361).
LITERATURE_H_EFF_KCAL_PER_MOL_O2 = 63.2

# --- Crew exposure --------------------------------------------------------------------------
# NASA-STD-3001 Vol. 2 [V2 6004]: one-hour average CO2 partial pressure no more than 3 mmHg.
PPCO2_1H_LIMIT_MMHG = 3.0
# NIOSH IDLH for CO2: 40,000 ppm, "based on acute inhalation toxicity data in humans"
# (cdc.gov/niosh/idlh/124389.html). Applied here as a partial pressure at 1 atm (0.04 × 760 mmHg):
# ASSUMPTION that the physiological effect scales with partial pressure.
PPCO2_IDLH_MMHG = 0.04 * 760.0

# --- Microgravity water-mist evidence (MIST, STS-107; NIST R0401173) --------------------------
# Lean (φ = 0.7) propane–air premixed flames: water mass fractions (mass of suspended water per mass
# of gas) at which the flame was extinguished, and the highest tested loading that did not extinguish it.
MIST_EXTINCTION = [
    {"cmd_um": 20, "omega_w_extinguished": 0.033, "omega_w_not_extinguished": 0.025},
    {"cmd_um": 30, "omega_w_extinguished": 0.048, "omega_w_not_extinguished": 0.033},
]
MIST_PHI = 0.7

# --- Sourced rules --------------------------------------------------------------------------
BATTERY_RULE = {
    "statement": ("NASA reports that commercial CO₂ extinguishers were noted as ineffective on stored-energy (battery) "
                  "fires, while the ISS Fine Water Mist PFE extinguished 15 of 16 battery-fire tests (ground tests)."),
    "source": "NTRS 20130011664",
}
CO2_BREATHING_RULE = {
    "statement": ("ISS emergency breathing equipment does not filter CO₂ or supply oxygen; after a CO₂ PFE discharge the "
                  "crew must wear a breathing apparatus that supplies oxygen."),
    "source": "NTRS 20130011664",
}
WATER_MIST_FLAGS = [
    {"flag": "free_floating_water", "statement": "In microgravity undelivered mist does not settle; it stays airborne and "
     "collects on surfaces and equipment.", "source": "NIST R0401173 (mist remained suspended for minutes in microgravity)"},
    {"flag": "electronics", "statement": "Water reaching powered electronics is a hazard; NIST notes deionized water may be "
     "used for electrical fires. Remove power first per the fire response procedure.", "source": "NIST R0401173"},
]

# --- Defaults that are ASSUMPTIONS, not facts --------------------------------------------------
# Example cabin; the only sourced volume is the ISS airlock (31 m³ nominal, NTRS 20130011664), offered as a preset.
DEFAULT_CABIN_VOLUME_M3 = 100.0
AIRLOCK_VOLUME_M3 = 31.0
DEFAULT_CABIN_TEMPERATURE_K = 295.0
DEFAULT_LOCAL_ZONE_FRACTION = 0.10    # share of the cabin the discharge fills when aimed at the fire
DEFAULT_DELIVERY_FRACTION = 0.5       # η: share of the water reaching the fire zone as fine mist

# --- D2 gates and decision margins -------------------------------------------------------------
GATE_FLEX_AUC_LOWER_BOUND = 0.75      # mean − 1 SD of repeated grouped-CV extinction ROC-AUC
CLEAR_WINNER_MARGIN = 0.15            # difference in P(extinction) needed to name a winner
HIGH_CONFIDENCE_MARGIN = 0.30
