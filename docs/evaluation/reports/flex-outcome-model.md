# FLEX flame-outcome model: model card and evaluation

| Owner | Status | Version | Last updated | Plan items | Code paths |
|---|---|---|---|---|---|
| Lead (Anas), built with Claude Code | Current (needs review by Ziad, E5) | 1.0.0 | 2026-11-07 | T4 (final challenge plan) | `ai/fire_safety/`, `apps/api/flame_api/investigations.py` |

Every number below is copied from `ai/fire_safety/artifacts/flex_outcome_evaluation.json`. That file is written by:

```text
python -m ai.fire_safety.train_flex_outcome            # retrain, rewrite artefact + report
python -m ai.fire_safety.train_flex_outcome --check    # retrain and fail if the committed artefact differs ("artefact current")
```

## 1. What it does

Given pre-ignition conditions of a FLEX-style droplet burn, the model estimates how the flame ends:

- **Extinction**: the flame self-extinguished before the fuel was consumed. This is the fire-safe outcome.
- **Disruption**: the droplet broke apart.
- **Completion**: the droplet burned until the fuel was consumed.

Inputs:

- fuel (methanol or heptane);
- O₂ mole fraction;
- total pressure;
- CO₂ and He diluent fractions;
- initial droplet diameter.

The model also uses O₂ partial pressure as a derived feature.

It is served as `GET /api/insights/flex-outcome` with claim class **estimated**. Every response also returns the 8 most similar real flight tests with their recorded end state, so a judge can compare the estimate with what actually happened on the ISS.

**It does not** predict:

- solid materials;
- fuels other than methanol and heptane;
- partial gravity (Moon or Mars);
- flame temperature;
- anything outside the flight-tested ranges.

Outside the applicability domain the API returns `probabilities: null` and states the reasons.

## 2. Data

| Item | Value |
|---|---|
| Source | NASA PSI FLEX (FF-PSI-69), `datasets/raw/psi_api/PSI-69/Experimental table/PSI-69_Experimental table_FLEX.csv`, CC0, sha256 `37c88ce8…7e1b96` |
| Rows | 274 published; **261 used** |
| Excluded rows | 12 with a missing required condition; 1 more (`C11M201`) whose pressure of 0 mmHg is physically impossible |
| Classes | Extinction 179 · Disruption 55 · Completion 27 |
| Test days | 80 |
| Gravity | microgravity (ISS Combustion Integrated Rack) |
| Excluded columns (leakage) | burn time, extinction diameter, burning rate: all measured after ignition |
| Data-quality note | FLEX identifier `193F001` is published on two rows with different conditions; both are kept |

The API rebuilds the features from ingested database rows. `test_api_features_match_training_features_for_every_flex_test` asserts that all 261 match the training features exactly.

## 3. Protocol

1. **Grouping.** Tests flown on the same day share hardware state and often near-identical conditions. Every split is therefore by test day, and no day is ever in both the training and the scoring set.
2. **Hold-out.** 20 % of test days (16 days, 49 tests) are held out once, with seed 2026.
3. **Selection.** Candidates are compared by 5× repeated grouped 5-fold CV on the other 80 % of days, using macro-F1 because the classes are imbalanced. Logistic regression is preferred unless another exportable model beats it by more than one SD.
4. **Primary estimate.** 5× repeated grouped 5-fold CV over all 261 rows.
5. **Deployment.** The deployed model is the selected candidate refit on all rows. It is exported to JSON and executed with numpy in the API. The numpy and scikit-learn probabilities differ by at most 2.2 × 10⁻¹⁶.

**Disclosure (protocol history).** The first version selected by a *single* grouped 5-fold split on the development days, and that chose random forest (0.570 vs 0.540). On the held-out days the random forest then scored 0.497, against 0.640 for logistic regression. A single split was judged too noisy to select on, so selection moved to repeated grouped CV.

That change was made **after** the hold-out had been viewed, so the hold-out is no longer untouched. That is why the repeated grouped CV over all rows, not the hold-out, is the primary estimate.

## 4. Results

**Primary estimate: 5× repeated grouped 5-fold CV, all 261 rows (mean ± SD).**

| Model | Macro-F1 | Balanced accuracy | Extinction ROC-AUC |
|---|---|---|---|
| Majority class (baseline) | 0.271 ± 0.000 | 0.333 | 0.500 |
| **Logistic regression (deployed)** | **0.540 ± 0.018** | **0.576 ± 0.032** | **0.857 ± 0.010** |
| kNN (k = 15) | 0.532 ± 0.027 | 0.531 ± 0.015 | 0.859 ± 0.014 |
| Random forest | 0.516 ± 0.014 | 0.532 ± 0.017 | 0.837 ± 0.018 |

**Selection: repeated grouped CV on the development days only.** Logistic 0.505 ± 0.013 · random forest 0.508 ± 0.019 · kNN 0.501 ± 0.026. The forest's margin over logistic regression was 0.003, less than one SD, so logistic regression was selected.

**Hold-out days (49 tests; see the disclosure in §3).**

| Model | Macro-F1 | Balanced accuracy | Extinction ROC-AUC | Extinction Brier |
|---|---|---|---|---|
| Majority class | 0.258 | 0.333 | 0.500 | 0.367 |
| Logistic regression | 0.640 | 0.700 | 0.927 | 0.134 |
| Random forest | 0.497 | 0.536 | 0.936 | 0.130 |

Logistic regression on the hold-out, per class:

| Class | Precision | Recall | F1 | Support |
|---|---|---|---|---|
| Completion | 0.29 | 0.80 | 0.42 | 5 |
| Disruption | 1.00 | 0.46 | 0.63 | 13 |
| Extinction | 0.90 | 0.84 | 0.87 | 31 |

Confusion matrix (rows are true labels, columns are predictions, order Completion / Disruption / Extinction): `[[4,0,1],[5,6,2],[5,0,26]]`.

Calibration of P(extinction) on the hold-out (predicted → observed):

| Bin | Tests | Predicted | Observed |
|---|---|---|---|
| 0.0–0.2 | 11 | 0.12 | 0.00 |
| 0.2–0.4 | 10 | 0.28 | 0.50 |
| 0.4–0.6 | 6 | 0.52 | 1.00 |
| 0.6–0.8 | 12 | 0.70 | 0.83 |
| 0.8–1.0 | 10 | 0.87 | 1.00 |

The probabilities are under-confident in the middle range. The bins are small, so the figure is indicative only.

## 5. What drives the estimate

**Permutation importance.** The model is fit on the development days and scored on held-out days, with 30 repeats; each figure is the drop in macro-F1 when that input is shuffled.

| Input | Drop in macro-F1 |
|---|---|
| O₂ mole fraction | 0.217 ± 0.059 |
| He | 0.055 ± 0.038 |
| CO₂ | 0.049 ± 0.033 |
| Droplet diameter | 0.017 ± 0.037 |
| Pressure | 0.013 ± 0.009 |
| ppO₂ | 0.001 ± 0.006 |
| Fuel | −0.019 ± 0.026 |

**Standardized coefficients of the deployed model, Extinction class.**

| Input | Coefficient |
|---|---|
| O₂ | −1.25 |
| Droplet diameter | +0.50 |
| He | +0.38 |
| Pressure | +0.23 |
| CO₂ | +0.16 |
| ppO₂ | −0.13 |
| Heptane | −0.39 |

The signs agree with the physics FLEX was designed to probe:
- More oxygen keeps flames burning.
- Inert diluents favour extinction.
- Larger droplets are more prone to radiative extinction, which FLEX observed.

Together, inert diluents and radiative extinction are the mechanisms behind the LOI-mapping objective in NASA's FLEX metadata.

## 6. Applicability domain (strict)

- Each input must lie within the range seen in the 261 tests: O₂ 0.12–0.34, pressure 70.2–309.3 kPa, and the recorded CO₂, He and droplet ranges.
- The query must also be within the 95th-percentile nearest-neighbour distance of the training tests, in standardized units.

Example: the Altair lunar-lander atmosphere (34 % O₂ at 62.7 kPa) is refused because 62.7 kPa is below the lowest FLEX pressure. The UI shows the refusal, and still lists the nearest flight tests.

## Known limitations

- Droplet combustion of two fuels only; spacecraft cabin fires are mostly solid materials.
- 261 tests on 80 days; the Completion class has only 27 examples, so its precision is low (0.29 on the hold-out).
- Microgravity only; partial gravity is not represented.
- The hold-out was viewed before the final selection rule was fixed (§3).
- The gold labels are NASA's published `Test end` values; their definitions come from the FLEX documentation and were not re-reviewed by a domain expert for this report.

## Changelog
- 1.0.0 (2026-11-07): first release (`flex-outcome-logreg-1.0.0`).
