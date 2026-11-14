# physics/: gravity-aware flame-physics models

A review of `cv/pinn_pipeline.py` found that its equation, `du/dt = alpha d2u/dx2`, is 1D heat conduction. It has no
velocity field, no buoyancy, no reaction term and no gravity, so it could not see the variable the project is about.
This package replaces it with a model whose equations *do* depend on gravity, and validates it on real NASA fields.

## What was wrong, and what changed

| Gap in the old prototype | Now |
|---|---|
| No velocity field, so no convection | Network predicts `(u, v, p, T)` from `(x, y)` |
| No buoyancy, so gravity had no entry point | Body force `G (rho - 1)` in y-momentum, `G = -g Lo / Uo^2 = -1/Fr^2` |
| Constant diffusivity and density | `rho = 1/T*`, `mu* = T*^0.7` (variable density, as the data's own solver) |
| 1D | 2D steady Cartesian |
| No heat of combustion | Optional `source` hook in the energy equation (zero for PSI-115, which has no combustion) |
| Used to *predict* temperature, which was never measured | Used to *infer coefficients* from fields that exist |
| Needed `u_measured` that the project does not have | Trains on NASA PSI-115 fields |

## The equations

Steady, dimensionless, low-Mach variable density, +y up (reduced from eqs. 1, 2, 5 of the PSI-115 final report):

```
continuity  d(rho u)/dx + d(rho v)/dy = 0,                    rho = 1/T*
momentum    rho (u.grad) u_i = -dp/dx_i + (1/Re) d(tau_ij)/dx_j + G (rho - 1) delta_iy
energy      rho (u.grad) T   = (1/Pe) div(mu* grad T)  [ - Q ]
```

Gravity appears only through `G`: **-6.74 at Earth gravity, exactly 0 in microgravity** (Re = 22.3, Lo = 4.4 mm,
Uo = 0.08 m/s). Boussinesq was rejected because the report itself calls it invalid at this density variation
(T from 300 K to 473 K, about 36 % density change).

## The data: NASA PSI-115

Steady 2D air flow past a heated block in a channel, simulated at Earth gravity and at microgravity, on a
960 x 240 grid (`datasets/raw/psi_api/PSI-115/Analyzed Data/`, git-ignored, about 55 MB).

```bash
python knowledge/ingestion/psi_download.py datasets/manifests/psi115_pinn_selection.csv
```

**Read these limits before quoting any number from here:**

- It is **simulation output, not a measurement.** Recovering the coefficients shows the *formulation* is right; it
  is not an experimental result.
- It is a **heated surface expelling vapour (smoke precursor), not a flame.** There is no chemical heat release, so
  the reaction source `Q` is exercised only by a unit test, not by data.
- One snapshot at t = 7 s, treated as steady (the report says the flow is steady; the aerosol is not).
- `Pr = 0.71` is assumed (standard for air); the report does not state it.

## Results (CPU, 4,500 steps each, seed 0; `results/*.json`)

Both coefficients start from a deliberately wrong value (`G = 0`, `1/Pe = 0.1`).

| Method | Earth `G` (expected -6.744) | Micro `G` (expected 0) | `1/Pe` (nominal 0.0632) |
|---|---|---|---|
| Finite differences, no training (`fd_baseline.py`) | **-6.57** | **+0.015** | 0.061 / 0.057 |
| PINN, current defaults (weak momentum + energy, separate pressure branch, weight 0.05) | **-6.27** | **-0.045** | **0.059 / 0.054** |
| PINN, weak energy only, shared body (`*_weak_energy_only.json`) | -6.16 | -0.042 | 0.055 / 0.059 |
| PINN, first version (strong form, weight 1.0; `*_strong_pw1.json`) | -6.40 | +0.066 | 0.037 / 0.016 (biased low) |

- The PINN **separates the gravity levels and gets the sign right**: about -6.3 against about -0.05. It is 7 % low on Earth
  and 4 % below the finite-difference estimate on the same data.
- **The `1/Pe` bias was diagnosed and fixed in three measured steps:**
  1. *Cause.* Regressing `1/Pe` on the network's own second derivatives gives 0.019 (correlation 0.42) even for a
     fields-only fit, against 0.061 on the exact data. Noisy second derivatives shrink the coefficient toward zero.
  2. *Weak energy form.* `weak_energy_residual` integrates `div(rho u T - (1/Pe) mu grad T) = 0` over small cells, so only
     first derivatives appear. On the same network the regression gives 0.071. (`weak_residuals` now does the same for
     momentum; it is the default `residual_form`.)
  3. *Low physics weight.* In joint training the physics term still dragged the network off the exact data and
     `1/Pe` fell to 0.02-0.03. Weight 0.05 keeps the network on the data: `1/Pe` 0.055 / 0.059 (nominal 0.063, FD 0.061 / 0.057).
- **Earth `G` accuracy, what was tried** (the lower physics weight had cost it, -6.40 to -6.16):
  - More joint steps (7,500) and a 5x faster coefficient learning rate both plateaued at about -6.2: not under-training.
  - Weak (finite-volume) momentum made `1/Pe` essentially exact (0.0635 / 0.0627) but left `G` at -6.16, and microgravity
    `G` drifted to -0.34. So the viscous second derivatives were not what limited `G`.
  - A separate pressure branch (pressure is trained only by physics, so it was starved inside the shared body) cut the
    microgravity error from -0.34 to -0.045 and moved Earth `G` to -6.27. That is the current default.
  - **Remaining gap (about 7 %) is part model error, part network.** A finite-difference sweep over the viscosity
    exponent `n` in `mu* = T*^n` (Earth, expected -6.744; scratch script, numpy only):

    | `n` | 0 | 0.5 | **0.7** (report) | 0.85 | 1.0 | 1.2 | 2.0 |
    |---|---|---|---|---|---|---|---|
    | FD Earth `G` | -6.95 | -6.69 | **-6.57** | -6.48 | -6.38 | -6.24 | -5.60 |
    | fit R² | 0.31 | 0.52 | 0.60 | 0.61 | 0.56 | 0.43 | 0.08 |
    | FD micro `G` | +0.007 | +0.012 | +0.015 | +0.017 | +0.019 | +0.022 | +0.036 |

    `G` is sensitive to the viscosity law (about 0.1 per 0.2 of exponent), so the reduced model does leak into `G`.
    But with the report's `n = 0.7` the FD estimate is -6.57 (2.5 % low), and the PINN's -6.27 would match FD only at
    `n` of about 1.2, which the report's law does not allow. So roughly 2.5 points of the 7 % are model error and the
    other roughly 4.5 are the PINN. The R² does not pick the exponent that gives the right `G` (it peaks near 0.85), so
    `n` cannot be fitted from this data. Still untested: the unsteady term (only a t = 7 s snapshot exists).
- Field fit over every fluid cell, **a training fit and not a held-out test** (4,500 steps of 4,096 random points
  visit each of the 230k cells many times): Earth RMSE u 0.025, v 0.017, T 0.006; micro u 0.026, v 0.015, T 0.006
  (dimensionless). A genuine held-out check (for example training on one half of the channel) is not done.
- One seed. Variation across seeds has not been measured.

## Use

```bash
python -m physics.buoyant_pinn --gravity earth --out results.json     # about 30 min on 12 CPU cores
python -m pytest tests/physics                                         # 30 tests, under a minute
pip install -r physics/requirements.txt                                # PyTorch is optional; CI skips the torch tests
```

```python
from physics.psi115 import load_case
from physics.fd_baseline import estimate_parameters_fd
est = estimate_parameters_fd(load_case("earth"))      # numpy only, seconds
```

## Files

| File | Role |
|---|---|
| `psi115.py` | Loader, constants, signed buoyancy coefficient (numpy) |
| `fd_baseline.py` | Training-free recovery of `G` and `1/Pe` via the pressure-free curl of the momentum equation (numpy) |
| `buoyant_pinn.py` | PyTorch PINN: autograd residuals, trainable coefficients, training loop, CLI |
| `results/` | Result files quoted above (`*_strong_pw1.json` is the first, biased version, kept for comparison) |
| `tests/physics/` | Loader, residuals on exact solutions (hydrostatic balance, Poiseuille), weak vs strong energy form, FD recovery on real data, training smoke tests |

## Not done yet

- Real **flame** data. PSI-115 is the only local set with T, u, v at two gravity levels; combustion sets
  (FLEX PSI-69, SAFFIRE PSI-98) are not field data: FLEX is droplet-combustion video (flame and droplet size from images, no
  temperature or velocity fields), so the PINN cannot be fitted to it as it stands. The local SAFFIRE-I copy is also images only:
  a 2-row sample table (SIBAL fabric, concurrent and opposed flow), and one pre-test flow-visualisation camera run
  (F2C2, 778 JPEGs at about 30 fps, raw and "mapped"). The big spreadsheet is just a per-frame filename and timestamp index.
  The sensor channels were downloaded separately (`datasets/manifests/saffire1_sensor_selection.csv`, 4 files, 51 MB):
  per-sample workbooks with 6 plume and 6 sample thermocouples, 4 radiometers, 2 anemometers, CO2, O2, pressure,
  humidity, inlet temperature and igniter V/I (about 20,000 time rows for sample 1), plus a telemetry workbook that also
  has the host vehicle's accelerations (a microgravity quality check) and the thermocouple placement PDF. These are
  real flame temperature records, but at 12 points only, so they cannot constrain the 2D PINN.
  SAFFIRE-II (PSI-99, 9 samples) and SAFFIRE-III (PSI-100, 2 samples) sensor and telemetry files were downloaded the same
  way (`saffire23_sensor_selection.csv`, 26 files, 267 MB). They have the same 12-thermocouple channel layout at about 30 Hz.
  Checked values and units (SAFFIRE-I sample 1, plus samples I-2, II-1, III-1 on key channels; the units row under the
  header gives RPM, %, cm/sec, PSIA, mW/cm2, degrees C, Amps, Volts, identical across flights):
  - Anemometers read about 21 and 18.5 cm/s (I-1) against 20 cm/s nominal; O2 22.4 % against 21.5 % nominal (I-1), 21.5 % (II-1),
    19.8 % (III-1); pressure 14.9 PSIA (14.5 in III); humidity 45 to 51 %. Gas, flow and pressure channels look plausible but are
    not calibration-checked, and the O2 offset in I-1 is about 1 point.
  - Radiometers have a negative baseline of -8 to -17 mW/cm2 and peak near 130 to 150; the extra columns "Downstream Front" and
    similar are offset-corrected versions (baseline near 0).
  - Sample thermocouples peak at 330 to 1,090 degrees C in I-1 and III-1. Their quiet baseline sits 2 to 7 degrees C below the inlet
    temperature, which suggests a cold-junction or calibration offset. Plume TCs peak at 58 to 122 degrees C (I-1).
  - Igniter: SAFFIRE-I peaks at 45.8 V x 4.12 A = 189 W, matching the 182 W in the sample table. SAFFIRE-II sample 1 reports
    670 to 770 V at 3.6 to 3.8 A (about 2.9 kW), which is not physical, so that voltage channel looks mis-scaled.
  - No burn signal in SAFFIRE-II sample 1 (all thermocouples stay under 24 degrees C) or in SAFFIRE-I sample 2's sample TCs (under 25 degrees C,
    though plume TC3 reaches 94 degrees C and the table lists a 70 s burn). Check before using those samples.
  - The workbooks carry many blank trailing rows (32,599 rows, of which 13,182 hold data in II-1). Count rows with numeric elapsed time.
  - "Timestamp (ms)" is a date string, and "Epoch Time" is in ms. Time steps are about 33 ms.
  - The thermocouple placement PDF (SFSDP-VIS-0295) is a 3-page verification sheet, not a drawing. It says only that 6 temperature
    sensors were installed on the flame-spread sample "as specified in Table 3.7.4-7 and Figure 3.7.4-1" of the system
    requirements document SFSDP-REQ-102, with as-built drawings 120102MFA000 and 120102MFA310. Those table, figure and drawings are
    not in the PDF and not mirrored, so TC positions are still unknown. It also gives the required sample size as 300 x 800 mm
    (12 x 31.5 in), whereas the sample table lists 40.6 cm length and 94 cm width, which needs reconciling.
    The 6 sample TCs (TC7 to 12) are the ones this covers; nothing here describes the 6 plume TCs.
  - The objectives paper (Schoren et al., NTRS 20170001636) and the SAFFIRE-I/III readme settle two of the questions above.
    The SIBAL sample (75 % cotton, 25 % fiberglass) is about 0.94 m long and 0.4 m wide, so the sample table's "length 40.6 /
    width 94 cm" has the labels swapped, and the 300 x 800 mm in the verification sheet is only the minimum requirement.
    SAFFIRE-II carries nine 5 x 29 cm samples (silicone 0.25, 0.61, 1.02 and 0.36 mm (S4 has the igniter downstream, opposed), SIBAL 0.33 mm at 20 and 30 cm/s,
    PMMA-to-Nomex, structured PMMA, flat PMMA), chosen to burn just above and below 21 % O2, so "some are expected not to burn":
    the dead SAFFIRE-II sample 1 (0.25 mm silicone) is probably a non-burn, not a sensor fault. Design flow is 20 cm/s (I) and 30 cm/s (III);
    SAFFIRE-III sample 1 anemometers read about 24 and 26 cm/s, 15 to 20 % below that, which is unexplained.
    Sensor locations (paper Table 2): flow-temperature TCs at duct inlet and outlet, flame TCs embedded in the sample, plume TC (no
    location given), 4 radiometers (2 viewing the front of the sample, 2 the back, matching the "Upstream/Downstream Front/Back"
    columns), O2 at the avionics-bay inlet, CO2 and pressure in the avionics bay (so not measured at the sample), one anemometer
    each side, 2 cameras on the front, smoke wire at the leading edge. TC coordinates are still not given anywhere read so far.
    The paper's dates are plans (SAFFIRE-I on 2 Jun 2016, II on 19 Sep 2016, III on 3 Mar 2017); the workbook timestamps show the
    actual burns on 14 Jun 2016, 21 Nov 2016 and 4 Jun 2017. The readme explains the image sets: "Mapped" means distortion-corrected
    to a flat grid (the one to use for measuring flame fronts), and "icmad" files carry exposure and gain in a strip under each frame.
  - The SAFFIRE-I Operations note and the Image Directory Nomenclature sheet add no sensor positions. They say the SAFFIRE-I/III
    sample is 0.4 m wide by 0.94 m tall (so the long side is along the flow), that the SAFFIRE-II samples are 5 cm wide x 25 cm long
    (the objectives paper says 5 x 29 cm, a small unresolved difference), that the whole burn is recorded and downlinked (at most
    20 gigabit), and that SAFFIRE-II samples burn one at a time with the cameras recording only the sample being burned. Image
    sets: "Raw_CamOriginal" carries an 8-byte offset that must be corrected first, "Raw_DistroMaster" is the corrected raw,
    "jpeg" is the flight-generated version, and "jpeg_corrupt" holds frames damaged in downlink (so expect missing frames).
- **Flame spread measured from the SAFFIRE-I sample 1 Mapped frames** (`saffire1_s1_mapped_selection.csv`, 7 zips, 874 MB;
  result `results/saffire1_s1_flame_front.csv`, 200 one-second points). Reproduce with
  `python -m physics.saffire_flame_front --cache-dir <dir>` (about 2 minutes for the decode with 6 worker processes; needs pillow;
  `tests/physics/test_saffire_flame_front.py` covers the tracker on synthetic profiles). A full rerun reproduced the numbers below.
  Camera 1 has 14,388 frames over 602 s and camera 2 has 14,553 unique frames over 577 s (S1C2 `part3` repeats `part2`'s 5,000
  frame names, so it was dropped as a duplicate). Roughly a fifth of the frames are LED-lit and show the dark burned region against
  bright unburned fabric; in the rest only the dim flame glow is visible.
  - The burned/unburned boundary in the lit frames moves in a straight line, right to left, in both cameras. Camera 2 sees the same
    front shifted by a constant 221.5 +/- 3 columns (quarter-resolution pixels), so the two chain into one track covering 11 to 418 s.
    The track ends at 418 s, matching the 420 s burn time in the sample table.
  - Steady spread rate (100 to 410 s): 0.991 px/s at quarter resolution (residual 2.7 px). Camera 1 and camera 2 alone give
    1.011 and 1.006 px/s, and the glow centroid gives 1.02 to 1.05 px/s. The first 40 s are about twice as fast (1.9 px/s), then
    0.92 to 1.12 px/s with a slight rise near the end (about 10 % over the run).
  - **Scale, settled with the distortion-grid images** (`saffire1_distortion_grids_selection.csv`, 6 of 7 files, 3 MB; the
    ROI-offsets PDF returns 404 from PSI's own storage, so it is not available). The Mapped "30mmBlock" checkerboards have 66.7 px blocks
    for 30 mm in both cameras (Fourier peak; left, right and centre crops agree within about 1.5 %), so **0.450 mm per full-resolution
    pixel, 1.80 mm per quarter px**. That gives a steady spread rate of **1.78 mm/s** (0.9916 px/s) and a front travel of about 836 mm by 416 s
    (the sample is 940 mm). It matches the bright-band estimate (0.445 mm per px) and rules out the length-based one (0.49 mm per px).
    It assumes the checkerboard lay in the sample plane. The CSV now has one position column, `x_mm`.
  - **Is the dark side burned fabric? Image check (2026-11-14).** Seven lit S1C1 Mapped frames at 1, 29, 99, 199, 275, 399 and 419 s
    show: a uniformly bright sample at 1 s (no dark region before the burn, so it is not a fixture shadow); a sharp edge with a steady shape
    that grows right to left and never recedes; glowing embers along the advancing edge; a mottled fibrous texture behind it, as expected for
    the fiberglass skeleton left once the cotton is gone; and a fully dark sample at 399 and 419 s with the flame out, so the change
    is lasting and not smoke or flame shadow. The glow also sits about 30 px behind the boundary. This supports "dark side = burned fabric".
    It is not a physical inspection: there is no measured char, mass loss or post-burn photo in what is mirrored (the readme lists
    "post-flow" image sets that were not downloaded and could be a stronger check). The 1 s frame is much more exposed than the later ones, so brightness is not compared across times.
  - **Airflow direction: concurrent.** The PSI-98 experimental table (`Experimental table/PSI-98_Experimental table_SAFFIRE-1.csv`)
    lists sample S1 (cameras S1C1/S1C2) with Flow Direction "Concurrent", 20 cm/s, 8 s ignition, 420 s burn, and sample S2 as "Opposed"
    (70 s burn). So the 1.78 mm/s front spreads with the flow. This comes from the table, not from the pixels: I did not measure the flow
    direction in the images, and the F2C2 flow-visualisation run belongs to sample 2 (opposed), so it does not decide sample 1;
    the sample 1 run (F1C1/F1C2) was only downloaded as distortion grids. Use 1.78 mm/s as a concurrent-flow rate at 20 cm/s and about 21.5 % O2
    when comparing with published rates. The `source` hook is where a reaction model plugs in.
- A second inlet speed (PSI-115 Case 2, Uo = 0.1 m/s) to test that `G` is a property of gravity rather than of one flow.
- Multiple seeds for a spread on `G` and `1/Pe` (one seed so far).
- Close the PINN-specific part of the Earth `G` gap (about 4.5 points below the FD estimate). The viscosity sweep did
  not explain it. A larger network (128 units, 1,024 cells per step, `--hidden 128 --n-cells 1024`) gave `G` = -6.305
  (from -6.27) and `1/Pe` = 0.0635 (nominal 0.0632), RMSE u 0.021, v 0.017, T 0.005. So capacity is not the limit
  either. Not tried: several seeds, a longer weak-form schedule, a different coefficient parametrisation.
