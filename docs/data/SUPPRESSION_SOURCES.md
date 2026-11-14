# Suppression Advisor: evidence sources

| Owner | Status | Last updated | Plan |
|---|---|---|---|
| Lead (Anas) | D1 search complete (time-boxed); constants for CO₂ PFE, module volumes and exposure limits still to source | 2026-11-13 | `docs/plan/SUPPRESSION_ADVISOR_PLAN.md` |

Every constant used by `ai/fire_safety/suppression/` must be listed here with its source and location. Numbers below are copied from the sources' text. Nothing here has been ingested into the corpus yet.

## 1. Outcome of the D1 search (water-mist evidence)

**Result: no per-test, tabulated microgravity water-mist dataset was found.** The one microgravity flight experiment (MIST, STS-107) reports its results in text and figures, and the final dataset was not located. We therefore fall back to option (a): a thermal model calibrated on FLEX. MIST is added as a **validation anchor** for the water-mist branch, not as training data.

What the search did produce:

1. **Measured microgravity extinction thresholds for water mist** (MIST, §2.1). A small set of numbers, but real flight data.
2. **The ISS water-mist extinguisher's charge and ground-test results** (FWM PFE, §2.2).
3. **A finding that changes the model framing** (§3): a pure heat-sink estimate *under-predicts* how well a uniform fine mist suppresses a flame. The main uncertainty in a cabin is therefore **delivery** (does the mist reach the flame as fine droplets?), not evaporation inside the flame.

## 2. Sources

### 2.1 MIST: Water-Mist Fire Suppression Experiment, STS-107 (microgravity, flown January 2003)

- Abbud-Madrid, A., McKinnon, J. T., Amon, F. K., Gokoglu, S. *Suppression of Premixed Flames by Water Mist in Microgravity: Findings from the MIST Experiment on STS-107.* NIST record R0401173. <https://www.nist.gov/system/files/documents/el/fire_research/R0401173.pdf>
- Preliminary version: NASA/CP-2003-212376/REV1, pp. 281–284, NTRS `20040053582`. <https://ntrs.nasa.gov/citations/20040053582>

| Item | Value (as published) |
|---|---|
| Configuration | Premixed propane–air flame propagating through a uniform, quiescent mist cloud; tube 6.3 cm diameter × 49.5 cm; isobaric |
| Tests | 32; equivalence ratio φ = 0.6, 0.7, 1.0, 1.3; droplet count median diameter (CMD) 20 and 30 µm; water mass fraction ω_w 0.0–0.1 (mass of suspended water per mass of gas) |
| Data recovery | "over 90% of the information gathered in orbit was downlinked" before the loss of Columbia |
| **Extinction, φ = 0.7, CMD 30 µm** | near-extinction (pulsating) at ω_w = 3.3 %; **extinguished at ω_w = 4.8 %** |
| **Extinction, φ = 0.7, CMD 20 µm** | pulsating at ω_w = 2.5 %; **extinguished at ω_w = 3.3 %** |
| Burning-velocity reduction, ω_w = 0.2 %, CMD 20 µm | 46 % (φ = 0.7), 55 % (φ = 0.6) |
| Burning-velocity reduction, ω_w = 0.2 %, CMD 30 µm, φ = 0.6 | 49 % |
| φ = 0.7, CMD 30 µm, moist air / 0.2 % / 2.5 % | reduced by 40 % / 44 % / "to about 76% of the dry-flame value" (the paper's wording is ambiguous; check Fig. 6 before using) |
| Dry reference burning velocities used | 13 cm/s (φ = 0.6), 23 cm/s (φ = 0.7), from literature |
| Stated trend | smaller droplets are more effective; leaner (weaker) flames are suppressed more easily |

**Limits for our use.** Premixed gas flames, not droplet diffusion flames (FLEX) or cabin fires. Narrow-tube heat loss helps extinction. Stoichiometric and rich results were not analysed in this paper. Only lean-flame numbers are usable.

### 2.2 ISS Fine Water Mist Portable Fire Extinguisher (FWM PFE)

- Rodriguez, B., Young, G. *Development of the International Space Station Fine Water Mist Portable Fire Extinguisher.* AIAA / NASA JSC, NTRS `20130011664`. <https://ntrs.nasa.gov/api/citations/20130011664/downloads/20130011664.pdf>
- Related: NTRS `20110012300`, `20120018019` (development papers, not yet read).

| Item | Value (as published) |
|---|---|
| Charge | **6 lb water + 1.2 lb nitrogen**, pressurised to approximately 1270 psia, in a titanium bellows |
| Why it was developed | ISS emergency breathing equipment "does not filter CO2, nor does it provide oxygen"; after a CO₂ PFE discharge crew must wear a portable breathing apparatus that supplies oxygen. Commercial CO₂ extinguishers were noted as ineffective on stored-energy battery fires. |
| Results, ISS fire test standards (engineering development unit, ground tests) | open cabin 16/16 extinguished, mean 1 s · rack fire 16/16, mean ~60 s · elevated-oxygen fire 16/16, mean ~0.3 s · stored-energy battery fire 15/16 |
| Elevated-O₂ test atmosphere (airlock standard) | 527.5 mmHg (10.2 psia), O₂ 24–30 %; airlock volume 31 m³ nominal (equipment displaces an unknown amount) |
| Test configuration notes | 50 % packing factor chosen as the conservative standard; PMMA crib fire at ≥ 90 g mass loss before discharge |

**Limits for our use.** These are 1-g ground tests, pass/fail with extinguishment times. They do not give the concentration needed. They do give the water-mist extinguisher's charge for the discharge model, and a sourced crew-hazard reason for the CO₂ branch.

### 2.3 Read but not quantitatively useful

- Delplanque, J.-P., Abbud-Madrid, A., et al. *Feasibility Study of Water Mist for Spacecraft Fire Suppression.* NIST R0401172. Project-start paper: describes planned CO₂ vs water-mist vs N₂ comparisons and a droplet evaporation model (e.g. a 30 µm droplet vanishes ~7 cm from the nozzle in their case). No comparison results. It states water is "as effective as Halon 1301" per unit mass and "more effective for surface and deep-seated fires" than CO₂, but cites no measurement.
- Ground cup-burner water-mist studies (search results only, not read): a reported n-heptane cup-burner extinction at 174 g/m³ of ultrafine mist; a modelling result that the extinguishing water mass fraction rises from 10.5 % to 15 % as droplets shrink from 32 to 4 µm. To be verified before use.

## 3. What the evidence implies for the model

**Correction (2026-11-14).** An earlier version of this section argued, from an adiabatic-flame-temperature estimate, that a heat-sink model would *under*-predict water mist on MIST. The calibrated model shows the opposite, and the calibrated result is the one that counts.

- The model is fitted on FLEX (`ai/fire_safety/artifacts/suppression_thermal_evaluation.json`). It predicts P(extinction) = 0.5 for the MIST flames at ω_w ≈ 2.0 %, but MIST needed 3.3 % (20 µm) and 4.8 % (30 µm).
- So it **over-predicts** water mist by a factor of about 1.6–2.4, and the MIST gate fails.
- The likely reason is that FLEX droplet flames are weak. Their 50 % point is 52 kcal/mol O₂ for heptane and 43 for methanol at 1 atm, against 48 for plain air: methanol droplets often go out in air. A threshold fitted on them is too low for MIST's stronger premixed flames.
- **η is still the effective delivery fraction**: the share of the discharged water that reaches the fire zone as fine mist. Aim, distance, obstructions (rack fires took ~60 s) and droplet size control it.

## 4. Constants added for implementation (2026-11-14)

| Constant | Value | Source |
|---|---|---|
| ISS CO₂ PFE charge | "6 lbs of CO2 at 850 psi; discharges in 45 sec" | Ruff, Hicks, Pettegrew, NASA/CP-2004-213205/VOL2 p. 357, NTRS `20040161262` |
| Effective-enthalpy criterion | Energy to heat the mixture from 298 K to 1600 K per mol O₂ (Sheinson et al. 1989); CO₂, He and N₂ limiting data correlate with it in microgravity; "Normal gravity suppression is at 63.2 kcal/mol O2" (PMMA); Huggett's threshold 40–50 cal/(°C·mol O₂) | Same paper, pp. 361–362 |
| H°(1600 K) − H°(298 K), kJ/mol | N₂ 41.90, O₂ 44.27, CO₂ 67.57, H₂O(g) 52.91; He 5/2 R ΔT = 27.06 | NIST Chemistry WebBook, JANAF tables (IDs C7727379, C7782447, C124389, C7732185) |
| Water, liquid 298 K → vapour 1600 K | 44.004 + 52.91 = 96.91 kJ/mol (ΔvapH°298 from ΔfH° gas −241.826, liquid −285.830) | NIST WebBook, C7732185 |
| ppCO₂ one-hour average limit | ≤ 3 mmHg | NASA-STD-3001 Vol. 2 [V2 6004] |
| CO₂ IDLH | 40,000 ppm, "based on acute inhalation toxicity data in humans"; applied as 0.04 × 760 = 30.4 mmHg partial pressure (assumption) | NIOSH, cdc.gov/niosh/idlh/124389.html |
| CO₂ PFE crew procedure | Crew must wear a breathing apparatus that supplies O₂ after a CO₂ PFE discharge | NTRS `20130011664`; NASA-STD-3001 fire protection technical brief |

**Not sourced, kept as labelled assumptions or user inputs:**
- module free volumes (only the 31 m³ airlock is sourced);
- the local-zone fraction;
- the delivery fraction η;
- O₂ hypoxia limits (ppO₂ is reported without a verdict).

**Still to do:** add NTRS `20040053582`, `20130011664`, `20110012300`, `20120018019` and `20040161262` to `knowledge/ingestion/fetch_ntrs.py` and the source registry, with checksums.
