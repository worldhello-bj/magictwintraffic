# Acceptance matrix

Status snapshot: 2026-10-09. “Implemented” means a code path exists; “verified” requires named executed evidence. “Pending” is not a pass. The v4 plan is broader than the present implementation. This matrix deliberately does not infer field validity or performance from unit tests.

| ID | Acceptance scope | Current status | Evidence / remaining work |
|---|---|---|---|
| GEO-01 | Meter-defined core and coordinate round-trip | Verified projected extent; field survey pending | `data/canonical/validation.json`: projected core sides 1000 m; geodesic sides 1000.299–1000.301m, maximum scale difference 0.03011%. `test_real_osm_scope` passes. Outer envelope is 7.16 km²-like, not a claimed fully populated 4 km² rectangle. |
| GEO-02 | OSM-to-network traceability, grade separation | Traceability implemented; manual review pending | Original OSM hash/tags and per-policy road/lane mappings are retained; elevated geometry is checked in `test_real_osm_scope`. Exhaustive field grade/connection review is not claimed. |
| NET-01 | Positive-demand legal reachability | Verified software preflight | `test_invalid_od_fails_preflight`, API unknown-OD tests and all 316 executed runs preserve positive-demand routing checks. Field legality of every OSM-inferred permission remains unverified. |
| NET-02 | Connections and safe phases | Pending review | Algorithm-generated phases do not establish field correctness. |
| SIM-01 | Free running and red-light stops | Verified isolated mechanism | `tests/traffic_cases/test_red_light.py` executes a one-vehicle red hold and legal release on a clearly labeled test network. It does not replace the real geographic network. |
| SIM-02 | Downstream limits and short-link spillback | Downstream mechanism verified; short-link-specific coverage pending | Real-network `test_downstream_constraint_propagates_and_preserves_external_wait` increases upstream stops/external waiting and reduces completion under a matched receiving constraint; no teleport is used. |
| SIM-03 | Conservation and anomaly audit | Verified for 316 declared evaluations | `tests/test_analysis.py` rejects invalid conservation/anomalies. `evidence/exploration_runs.json` contains all 96 exploration per-step conservation audits; corresponding optimization/verification files cover the remaining 220 runs, with zero reported collisions, teleports or unexplained losses. This does not establish field validity. |
| SIM-04 | Bus stops and permissions/priority | Synthetic mechanisms observed; passenger/field validation pending | `evidence/bus_mechanism_check.json`: 648 actual bus stop-start events and 815 bus-present green extensions across 12 S6 runs. These are real engine actions, not passenger-benefit evidence. |
| DEM-01 | Integer arrivals and OD units | Verified software generation | `test_demand_reproducible_and_piecewise` checks reproducibility, at-most 300 s bins and expected-count sums. Actual integer manifests are saved per run; all-policy paired hashes are audited. |
| DEM-02 | Entry wait and future-departure exclusion | Verified implemented accounting | Future-demand and hand-calculated entry-wait tests pass; all 316 elapsed-time audits include due-but-uninserted trips. Physical queues beyond the modeled boundary remain an assumption. |
| POL-01 | All eight families produce actual changes | Eight families executed; effect/visual coverage partial | All eight real-engine smoke tests and 96 exploration runs pass. S2/S4 network hashes change. S4 has zero route exposure and no demonstrated effect; exhaustive visual verification of every modification remains pending. |
| MET-01 | Cohort-aware system metrics | Verified for implemented finite-window metrics | Hand-calculated paired interval tests pass. `evidence/independent_tstt_check.json` independently recomputes exploration peak-cohort TSTTs from trip elapsed times; stage-specific independent-check files cover all 316 runs, agreeing within 2.5e-8 vehicle-seconds. Physical contiguous queues remain a separate unimplemented metric. |
| STA-01 | Paired demand, cohort guard and independent seeds | Exploration, tuning and independent verification executed | 20 tests in `tests/test_analysis.py` passed on 2026-10-09. Coverage includes 96/180 plan counts, split rejection, mismatched cohorts/hashes/windows, pseudoreplication, censoring and incomplete batches. All 96 full-duration exploration runs completed; paired demand hashes and a common implementation were checked. The separate 180-run independent verification is complete; 40 tuning evaluations are separately accounted for. |
| VIS-01 | Hash-safe, physically faithful replay | Integrity verified; turning fidelity partial | Binary/chunk/hash rejection tests pass. Cloud Canvas replay was exercised; detailed corner interpolation and full GPU-path visual acceptance remain pending. |
| VIS-02 | Synchronized comparison | Cloud fallback synchronization observed | `evidence/browser-qa.md` records shared time/camera and consistent color scales in split view. Full GPU-path and exhaustive structural-change cases remain pending. |
| VIS-03 | Camera-independent results | Architecturally isolated; explicit regression pending | Replay consumes immutable saved results. A dedicated camera/hide-controls invariant test remains pending. |
| PERF-01 | Measured throughput and staged timing | Partial measured evidence | Actual staged timings and 2/4-worker execution are in the exploration/optimization/verification run exports; peak RSS evidence supports the four-worker trial. Full cold/hot, 1/2/4/8-worker and four-output-mode benchmark remains pending. |
| PERF-02 | FPS, memory and seek latency | Pending real-client benchmark | Desktop GPU/browser tests required; build success is not FPS evidence. |
| SYS-01 | Cancel/fail/restart correctness | Verified service tests | Cancellation, live-process termination, restart failure states, launch/time-budget errors, cache corruption, input mutation, quotas and real worker integration tests pass in the 63-test Python suite. |
| SYS-02 | Offline bundle | Cloud recorded-replay verified; clean-machine test pending | Actual cloud-browser QA used locally bundled recorded assets without computation backend. Fresh-machine/Windows installation and full network-isolation tests remain pending. |
| RES-01 | Optional GPU/research engine admission | Not implemented / deferred | MOSS/UNsim cannot participate in policy ranking until functionality, results, speed and cost pass. |
| FIELD-01 | Local calibration and independent validation | Pending external observations | Need dated counts, travel times, signals and bottleneck dynamics; not supplied by map data. |

## Executed software checks

The final full Python command `.venv/bin/python -m pytest -q` passed 63 tests in 24.99 s, with one nonblocking Starlette/httpx deprecation warning. Frontend and cloud-browser observations are recorded separately in `evidence/browser-qa.md`.

### Analysis test command

```sh
.venv/bin/python -m pytest tests/test_analysis.py -q
```

Observed result when this snapshot was written: 20 passed. This is a software test result only. Later integrated results belong in `validation_report.md`, with exact commands, versions and genuine outputs, and may update this matrix when verified. Actual 96/40/180 stage counts are supported by saved ledgers. Independent modeled effects are condition-specific and marginal, with no overall winner. No field benefit, physical-feasibility approval, or measured browser/GPU performance is asserted here.
