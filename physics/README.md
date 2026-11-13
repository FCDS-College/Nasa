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
  (FLEX PSI-69, SAFFIRE PSI-98) need thermocouple extraction first. The `source` hook is where a reaction model plugs in.
- A second inlet speed (PSI-115 Case 2, Uo = 0.1 m/s) to test that `G` is a property of gravity rather than of one flow.
- Multiple seeds for a spread on `G` and `1/Pe` (one seed so far).
- Close the PINN-specific part of the Earth `G` gap (about 4.5 points below the FD estimate). The viscosity sweep did
  not explain it, so look at the network and training instead (larger network, more cells, several seeds).
