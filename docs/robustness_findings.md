# Bounded downstream-receiving robustness findings

This 24-run extension completes a bounded part of experiment E. It is a small exploratory sensitivity check, not a comprehensive robustness or field-validation result. The original 316 evaluations remain a separate study; the completed total is now 340.

The added evidence does not establish a robust winner. For example, S1’s mean PM exposure difference changes from +181,616 vehicle-s nominally to -31,059 vehicle-s under the restriction; the two restricted-PM seed differences have opposite signs. All eight comparisons contain unfinished trips, so these are observed-window effects rather than eventual full-trip-time estimates.

## Frozen design

- S0, S1 and S5 × AM/PM × fresh seeds 211 and 223 × nominal/constrained exit, all at medium demand (1.0).
- All runs cover 9900 s: 900 s warmup, 7200 s target demand and 1800 s drain cap. Step, driver decision and control intervals remain 0.5 s.
- S1 green extension and S5 managed curb stop remain fixed at 8 s. No tuning used these outcomes.
- The hypothetical external constraint sets all lanes of terminal edge 441574379 at gate W_exit_441574379 to 0.1 m/s from t=3600 to 4500 s (45–60 minutes after the peak starts), then restores their original maximum speeds. It is a speed restriction, not a fully closed exit or a calibrated downstream service rate.
- The affected gate had 2227 scheduled peak destinations across the four existing medium-demand exploration inventories (AM/PM, seeds 11/29), the largest gate total. Selection used scheduled demand only, not policy performance.
- Two fresh seeds were frozen before execution and are disjoint from exploration, tuning and independent verification. No seed or condition was dropped or added after observing results.
- The unchanged runner uses its “verification” storage slot. This is only an execution adapter; the results below remain exploratory robustness and are not pooled into the earlier 180 verification runs.

## Integrity and actual execution

- All 24 planned runs succeeded. Full artifact checksums, unique trip identities, valid trip event ordering, and final all-cohort and peak counts passed.
- All 47,520 saved 5-second peak-population rows were independently reconstructed from desired-departure, insertion and arrival events; maximum conservation residual was zero.
- Independent peak trip-elapsed-time totals agree with the evaluator within 6.98e-09 vehicle-s. Maximum saved-time-series exposure discrepancy was 3.31e-08 vehicle-s; external-wait-time discrepancy was 0 vehicle-s.
- No reported collisions, teleports, explicit failures or unexplained losses. All 12 constrained runs logged the exact scheduled start/end; nominal runs logged none.
- Every period/seed has identical exogenous demand hashes across all six policy/condition cells. Implementation, network and engine versions are shared.
- Observed stage elapsed: 5.47 minutes with 4 workers. Largest reported worker peak RSS: 321.8 MiB. These are environment measurements, not hardware performance guarantees.

## Policy effects within each external condition

Each row is candidate minus S0 for two paired seeds. Exposure includes unfinished and uninserted target trips up to the common horizon. Negative exposure is not an eventual full-trip-time benefit when cohorts remain unfinished. The intervals are unadjusted two-sided paired Student t intervals with only one degree of freedom; their distributional assumption cannot be assessed with two seeds. Use these as descriptive sensitivity evidence, not confirmatory significance tests.

| Condition | Period | Policy | Seed 211 Δ exposure | Seed 223 Δ exposure | Mean Δ exposure | Marginal 95% CI | Mean Δ completion (pp) | Mean Δ external waiting |
|---|---|---|---:|---:|---:|---|---:|---:|
| nominal | AM | S1 | -537,453.5 | +219,772.5 | -158,840.5 | [-4,969,574.8, +4,651,893.8] | +0.664 | +5.0 |
| nominal | AM | S5 | -199,444.0 | -21,080.5 | -110,262.3 | [-1,243,423.8, +1,022,899.3] | +0.289 | -10.0 |
| nominal | PM | S1 | +190,155.5 | +173,076.0 | +181,615.7 | [+73,107.9, +290,123.6] | -0.094 | +8.0 |
| nominal | PM | S5 | +177,442.5 | -135,767.0 | +20,837.7 | [-1,969,014.3, +2,010,689.8] | +0.095 | +0.0 |
| exit_constraint | AM | S1 | -645,991.5 | -362,663.0 | -504,327.3 | [-2,304,342.2, +1,295,687.7] | +1.682 | -47.0 |
| exit_constraint | AM | S5 | -7,638.5 | -82,219.0 | -44,928.7 | [-518,746.3, +428,888.8] | +0.708 | -20.5 |
| exit_constraint | PM | S1 | -192,332.5 | +130,213.5 | -31,059.5 | [-2,080,227.3, +2,018,108.3] | +0.271 | -8.5 |
| exit_constraint | PM | S5 | -526,513.0 | +272,391.0 | -127,061.0 | [-5,202,579.9, +4,948,457.9] | +0.330 | +6.5 |

8 of the eight policy/condition comparisons include unfinished target trips. Completed-only means and P95 values are not used for ranking. Full seed-level completion, backlog and waiting differences are in `evidence/robustness_pairs.csv`.

## Effect of the external constraint

These differences compare the same policy, period and seed under constrained versus nominal receiving conditions. They show the scenario perturbation, not a policy benefit.

| Period | Policy | Seed 211 Δ exposure | Seed 223 Δ exposure | Mean Δ exposure | Mean Δ completion (pp) | Mean Δ external waiting |
|---|---|---:|---:|---:|---:|---:|
| AM | S0 | -90,472.5 | +146,579.0 | +28,053.3 | -0.209 | +6.5 |
| AM | S1 | -199,010.5 | -435,856.5 | -317,433.5 | +0.810 | -45.5 |
| AM | S5 | +101,333.0 | +85,440.5 | +93,386.8 | +0.211 | -4.0 |
| PM | S0 | +633,802.0 | +23,154.5 | +328,478.2 | -0.342 | +8.5 |
| PM | S1 | +251,314.0 | -19,708.0 | +115,803.0 | +0.024 | -8.0 |
| PM | S5 | -70,153.5 | +431,312.5 | +180,579.5 | -0.106 | +15.0 |

Some restriction-minus-nominal differences are negative. The full-network stochastic response is not monotonic in this small sample; this does not justify deliberate exit restriction as a beneficial intervention.

## Policy-by-condition sensitivity

Each interaction is (candidate − S0 under the constraint) − (candidate − S0 under nominal conditions). A positive exposure interaction means the candidate’s relative observed-window performance deteriorated under the constraint; it does not establish a general failure or an eventual travel-time effect.

| Period | Policy | Seed 211 interaction | Seed 223 interaction | Mean exposure interaction (vehicle-s) |
|---|---|---:|---:|---:|
| AM | S1 | -108,538.0 | -582,435.5 | -345,486.8 |
| AM | S5 | +191,805.5 | -61,138.5 | +65,333.5 |
| PM | S1 | -382,488.0 | -42,862.5 | -212,675.2 |
| PM | S5 | -703,955.5 | +408,158.0 | -147,898.7 |

## Limits and reproduction

This one-gate, one-duration perturbation does not cover internal E1 activity, reconstructed expanded-boundary demand, navigation response, independent curb-event intensity changes, matched fixed-integrator step-size tests, or field calibration. Those remain pending. Existing curb events are retained and paired; S5 changes their stop duration as its frozen policy mechanism, not as an independently varied external condition.

A lower exposure observation, wide interval, or two same-direction seeds cannot identify an overall robust winner. Interpretation must retain completion and external backlog alongside exposure.

From the repository root with locked dependencies installed:

```sh
PYTHONPATH=src python scripts/plan_robustness.py
PYTHONPATH=src python scripts/run_study.py --plan docs/evidence/robustness_plan.json --phase verification --state var/robustness-v1 --workers 4 --keep-going
PYTHONPATH=src python scripts/report_robustness.py --plan docs/evidence/robustness_plan.json --state var/robustness-v1
PYTHONPATH=src python scripts/check_robustness_report.py --state var/robustness-v1
```

Use a new state directory if the frozen plan changes. The scheduler checks source/input/dependency fingerprints, bounds each worker, validates artifacts, and marks a partial or failed matrix incomplete.

Evidence: `robustness_plan.json`, `robustness_results.json`, `robustness_pairs.csv`, `robustness_runs.json`, `robustness_execution.json`, `robustness_subgroups.json`, `robustness_independent_check.json`, and `robustness_report_validation.json` under `docs/evidence/`. The results file additionally contains the event-based audit of every saved population row, constraint event records, external-condition effects and interactions. Raw trip inventories and time series stay in the reproducible ignored run state; their hashes are preserved in exported manifests.
