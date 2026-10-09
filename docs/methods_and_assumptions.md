# Methods and assumptions

## Claim boundary

This repository implements a reproducible offline scenario laboratory. A working simulation, real OSM geometry and repeatable seeds do not establish calibrated Chengdu traffic. Unless a separate data-quality record supplies dated observations, demand, signal timing, behavior, curb events, downstream supply and passenger loading are experimental assumptions. No observed crash reduction, induced-demand response, full-person door-to-door benefit, GPU speedup or real-time field reconstruction is inferred.

`implementation_plan.md` is the research specification, not a certificate that all features have passed. `acceptance_matrix.md` distinguishes implementation from verification. Generated reports are linked to actual run identifiers and never replace missing runs with estimates.

## Scope and identities

Use the frozen real network's source and projection manifests. Synthetic test networks serve mechanism tests only. Core boundaries are observation boundaries; the outer network carries traffic. E0 describes boundary traffic. E1/internal activity, pedestrians, bicycles, person travel, sophisticated bus priority and dynamic route choice require their own implemented mechanisms and tests; do not assume these from vehicle appearance or a policy label.

An exogenous trip inventory carries persistent trip identity, desired departure, gates, vehicle type, cohort and source. The demand hash must describe this inventory independently of policy-dependent routing. Same demand hash, seed, period, target cohort and observation duration are required for pairing. Network and policy hashes may differ, since topology changes are part of the intervention. Different demand levels, AM/PM conditions, policy pairs and evaluation windows are analyzed separately. An integer seed alone is insufficient proof of common arrivals.

## Time, cohorts and conservation

Target trips are those whose planned departure lies in the peak window, after warmup and before demand end. Warmup trips affect congestion but are excluded from target metrics. Demand-end and final simulation horizon differ: vehicles can continue during a drain interval, but a hard horizon leaves right-censored trips.

At every audited time, due = not inserted + inside + completed + explicit failure. Future departures do not count as waiting. Entry-blocked demand remains pending. Anomalies, teleports and collisions prohibit policy ranking; failed/cancelled runs cannot masquerade as success.

Finite-horizon total system travel time is the integral of target in-network vehicles plus target external waiting vehicles. Completed-trip time starts at desired departure, not insertion. When trips remain, finite-horizon system time is accumulated exposure and is not the eventual total trip time. Keep completion, end backlog and backlog location beside it. Never choose the apparently fastest completed vehicles while ignoring the stalled vehicles.

## Statistical implementation

`traffic_twin.analysis` estimates candidate-minus-baseline differences for each matched seed. The replication unit is an independently generated demand/behavior seed, not a vehicle or trajectory frame. The reported two-sided 95% interval is a fixed-sample paired Student t interval. Critical values for 1–30 degrees of freedom are tabulated; larger samples use a second-order normal expansion. Assumptions are independent replicates and approximately normal replicate differences; two exploratory seeds cannot diagnose that approximation. A singleton has no confidence interval.

These are marginal, descriptive intervals. They are not multiplicity-adjusted family-wise guarantees and do not justify repeated optional stopping. Multiple condition findings remain conditional, not an overall winner. A fixed independent verification batch is declared before inspecting its results. If uncertainty remains, report inconclusive; a new batch requires a separately declared analysis plan and must not be silently pooled after repeated peeking.

For complete paired cohorts, an interval wholly below zero supports lower modeled system time in that particular condition. For censored cohorts, travel-time ranking is disabled. A candidate can receive the descriptive label “observed completion/backlog dominance” only if every paired replicate has at least as high completion, no more terminal backlog, no more external waiting, and some strictly higher completion. This is observed finite-window dominance, not a confidence-backed statement about final travel times. Completed-only means and P95 values are descriptive only.

## Exploration and independent verification

`build_study_plan()` creates 8 families × AM/PM × low/medium/high demand × 2 seeds = 96 exploration runs. Demand multipliers 0.6/1.0/1.4 and default exploratory seeds 11/29 are scenario choices, not observed local demand. `--write-plan` persists the exact design, including a 9900 s horizon, 900 s warmup, demand ending at 8100 s, 120 veh/h base gate rate and 0.5 s integration. These are configurable scenario assumptions; the reporter rejects runs with different frozen settings. No verification candidates are silently chosen.

After reviewing all six demand/time conditions and anomalies, explicitly freeze two distinct nonbaseline candidates, their full parameter configurations, network versions and baseline. `build_study_plan(candidates=(...))` then creates baseline plus the two candidates × 2 periods × 3 demand levels × 10 independent seeds = 180 verification runs. Default verification seeds 101–110 cannot overlap exploration. Calling the planner only creates specifications; it does not claim these runs have executed.

Do not select candidates using the verification runs. All policies in a pair reuse the same actual trip inventory. `analyze_study` rejects duplicate, unplanned and overlapping-seed inputs, distinguishes missing pairs, and disables verification conclusions for an incomplete fixed batch in a condition. No one is ranked globally by pooled AM/PM results or by a single favorable seed. Parameter search (40–80 evaluations) and robustness (24–48) are separate budgets and remain pending unless run artifacts document execution.

## Evidence and reporting

Example commands (after installation):

```sh
python scripts/report_results.py --write-plan reports/exploration-plan.json
python scripts/run_study.py --plan reports/exploration-plan.json --phase exploration --state var/exploration --workers 2
# After candidates and configurations are frozen:
python scripts/report_results.py --candidates S3 S7 --write-plan reports/study-plan.json
python scripts/run_study.py --plan reports/study-plan.json --phase verification --state var/verification --workers 2
python scripts/report_results.py --runs var/exploration/runs var/verification/runs --plan reports/study-plan.json --output reports/study.json
```

S3/S7 above illustrate syntax, not recommendations. Stage state directories keep immutable plan snapshots and execution ledgers; use a new directory when extending an exploration-only plan with frozen candidates. The combined plan report remains incomplete if only verification artifacts are supplied; pass both stage run directories to `--runs` for complete coverage. `--limit` is an explicit partial batch, not a smaller declared sample. The batch runner fails fast by default, saves failures/cancellations and stops if the implementation changes during the batch. The CLI reads actual manifest/metric files and emits JSON, Markdown and a standalone SVG evidence plot. Missing runs stay explicitly missing. Tables include finite-window exposure, completion/backlog intervals and evidence run IDs in JSON; Markdown summarizes those findings without a league table. Software-test fixtures are not real-network evidence.

## Uncertainty and acceptance still needed

Random repeats do not address misspecified OD, signal safety, unverified turn permissions, incorrect source maps, unknown roadside events, boundary truncation or driver behavior. These need external evidence and sensitivity analysis. Compare 0.5 s and 0.25 s integration while preserving behavior semantics, inspect downstream spillback and short links, test downstream receiving capacity and expanded boundaries with rebuilt demand. Investigate policy effects and who loses, not only aggregate gains.

CPU/GPU and browser speed must be measured separately on recorded hardware. No wall time, FPS, memory target or 5090 claim is certified by these methods. Final field accuracy requires independent dated observations withheld from calibration.

## Executed exploration and frozen next stages

The full 96-run exploration completed with 9900 s per run and no reported collision, teleport or unexplained-loss anomaly. Evidence lives in `evidence/exploration.json`, `exploration_runs.json`, `exploration_execution.json` and `independent_tstt_check.json`. All eight policies share identical exogenous-demand hashes within each condition/seed. Each terminal TSTT was independently reconstructed from trip elapsed times.

The two shortlisted families are S1 and S5. Among families with nonzero measured E0 effects, these had the smallest worst-condition mean completion losses (approximately 0.20 and 0.39 percentage points). This conservative exploration-only choice is recorded in `evidence/candidate_selection.json`; it is not a benefit claim. Both have adverse conditions and boundary-wait tradeoffs. S4 produced exactly baseline outputs, and its restricted link appeared in zero of 57,214 reference routes across the 12 baseline inventories including warmup. It is a null-exposure result, not validated neighborhood traffic management.

A bounded 40-evaluation parameter search is declared in `evidence/optimization_plan.json`: ten parameter configurations, each tested in AM/PM with two new tuning seeds 41/43 at medium demand. The default configuration is a reference. A variant must have no lower completion, no higher external waiting and no higher finite-window exposure in every paired tuning case to be eligible; otherwise the default remains. Only after those results are frozen may the reserved 101–110 seed set be used for 180 independent verification runs across all six demand/time conditions. All 40 tuning evaluations have now completed. No nondefault variant passed the declared no-regression rule across all four tuning cases, so both defaults remain (S1 green extension 8 s; S5 managed curb stop 8 s). The independent 180-run verification is complete. It identifies no overall winner: S1 is inconclusive in every condition; S5 has a small nominal PM-low improvement but worsens AM-medium finite-window exposure. Medium/high comparisons include censored repeats. See `statistical_findings.md` for all intervals and limits. See `evidence/optimization_results.json` and `verification_plan.json`.

Post-exploration code changes are restricted to integrity guards, replay API/RSS metadata and a controller-polling fix for 0.25 s sensitivity. The default 0.5 s traffic behavior was checked unchanged on a representative S3 rerun. Controller and vehicle behavior decision intervals remain 0.5 s for either integration step. Later stages carry their own frozen implementation identity.

### Integration-method caveat discovered before robustness interpretation

The .25 s smoke tests preserve .5 s vehicle and controller decision intervals, but that alone does not freeze the integrator. An actual SUMO startup probe emits a warning that differing action and integration steps enable ballistic integration. The raw option query still returned false, so it cannot certify the internal setting. `evidence/integrator_probe.json` records separate .5/.25 startup outputs. This behavior is documented by [SUMO's integration and action-step reference](https://sumo.dlr.de/docs/Simulation/Basic_Definition.html).

All primary .5 s experiments are internally consistent. The current .25 s smoke test demonstrates execution, conservation and fixed decision intervals; it is not same-integrator numerical convergence evidence. An explicit matched ballistic .5/.25 comparison, and preferably an Euler reference, is needed before claiming pure step-size robustness. No ongoing primary-run source or input was changed when this issue was discovered.
