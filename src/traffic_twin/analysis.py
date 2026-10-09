"""Paired, cohort-safe analysis. No completed-only or censored travel-time rankings."""
from __future__ import annotations

import json
import hashlib
import math
import statistics
from itertools import product
from pathlib import Path
from typing import Iterable, Mapping

POLICIES = tuple(f"S{i}" for i in range(8))
DEMAND_LEVELS = {"low": 0.6, "medium": 1.0, "high": 1.4}
# Two-sided 95% Student t quantiles, degrees of freedom 1..30.
_T95 = (12.706204736,4.302652730,3.182446305,2.776445105,2.570581836,
        2.446911851,2.364624252,2.306004135,2.262157163,2.228138852,
        2.200985160,2.178812830,2.160368656,2.144786688,2.131449546,
        2.119905299,2.109815578,2.100922040,2.093024054,2.085963447,
        2.079613845,2.073873068,2.068657610,2.063898562,2.059538553,
        2.055529439,2.051830516,2.048407142,2.045229642,2.042272456)


def paired_interval(differences: Iterable[float]) -> dict:
    """Fixed-sample CI on seed-level paired differences, not individual trips.

    Requires approximately independent, normally distributed replicate differences.
    A singleton is descriptive only: never invent a zero-width confidence interval.
    """
    values = [float(x) for x in differences]
    if not values or not all(math.isfinite(x) for x in values):
        raise ValueError("Nonempty finite paired observations required")
    n = len(values)
    mean = statistics.mean(values)
    result = {"n_pairs": n, "mean_difference": mean, "confidence": 0.95,
              "ci_low": None, "ci_high": None, "method": "paired Student t, fixed sample"}
    if n < 2:
        return result
    df = n - 1
    if df <= 30:
        critical = _T95[df - 1]
    else:
        z = statistics.NormalDist().inv_cdf(0.975)
        critical = z + (z**3 + z)/(4*df) + (5*z**5 + 16*z**3 + 3*z)/(96*df**2)
    half = critical * statistics.stdev(values) / math.sqrt(n)
    result.update(ci_low=mean-half, ci_high=mean+half)
    return result


def build_study_plan(exploration_seeds=(11, 29), verification_seeds=tuple(range(101,111)),
                     candidates=None, *, duration_seconds=9900, warmup_seconds=900,
                     demand_end_seconds=8100, rate_per_gate=120, step_seconds=0.5,
                     candidate_parameters=None) -> dict:
    """Build explicit stages; only unlock verification after two candidates are frozen."""
    if not 0 <= warmup_seconds < demand_end_seconds <= duration_seconds:
        raise ValueError("Require warmup < demand end <= observation horizon")
    experiment_config = {"duration_seconds": duration_seconds, "warmup_seconds": warmup_seconds,
                         "demand_end_seconds": demand_end_seconds, "rate_per_gate": rate_per_gate,
                         "step_seconds": step_seconds}
    exploration_seeds, verification_seeds = tuple(exploration_seeds), tuple(verification_seeds)
    if (not exploration_seeds or not verification_seeds or
        len(set(exploration_seeds)) != len(exploration_seeds) or
        len(set(verification_seeds)) != len(verification_seeds) or
        set(exploration_seeds) & set(verification_seeds)):
        raise ValueError("Distinct, nonempty, nonoverlapping seed sets required")
    if any(type(seed) is not int or seed < 0 for seed in (*exploration_seeds, *verification_seeds)):
        raise ValueError("Seeds must be nonnegative integers")
    candidates = tuple(candidates) if candidates is not None else ()
    if candidates and (len(candidates) != 2 or len(set(candidates)) != 2 or
                       any(p not in POLICIES[1:] for p in candidates)):
        raise ValueError("Freeze exactly two distinct non-baseline policy families")
    candidate_parameters = candidate_parameters or {}
    if set(candidate_parameters) - set(candidates):
        raise ValueError("Parameters may only be frozen for selected candidate families")
    def stage(name, policies, seeds):
        return [{"phase": name, "policy": p, "period": period, "demand_level": level,
                 "demand_scale": scale, "seed": seed, "trajectory": False, **experiment_config,
                 **({"policy_parameters": candidate_parameters[p]} if name == "verification" and p in candidate_parameters else {})}
                for p, period, (level, scale), seed in product(
                    policies, ("am", "pm"), DEMAND_LEVELS.items(), seeds)]
    return {"schema_version": "1.0", "experiment_config": experiment_config, "exploration_seeds": list(exploration_seeds),
            "verification_seeds": list(verification_seeds), "frozen_candidates": list(candidates), "frozen_candidate_parameters": candidate_parameters,
            "exploration": stage("exploration", POLICIES, exploration_seeds),
            "verification": stage("verification", ("S0", *candidates), verification_seeds) if candidates else [],
            "verification_status": "ready" if candidates else "pending candidate freeze",
            "stopping_rule": "Fixed independent verification batch; uncertain effects remain inconclusive. Additional batches require a new declared analysis plan.",
            "scope": "Synthetic scenario evidence; no field-calibration claim"}


def load_run(path: str | Path) -> dict:
    path = Path(path)
    manifest = json.loads((path / "manifest.json").read_text())
    content = (path / "metrics.json").read_bytes()
    expected = manifest.get("artifact_hashes", {}).get("metrics.json")
    if expected and hashlib.sha256(content).hexdigest() != expected:
        raise ValueError(f"Metrics checksum mismatch: {path.name}")
    return {"manifest": manifest, "metrics": json.loads(content)}


def _config(manifest, key):
    return manifest.get(key, manifest.get("config", {}).get(key))


def _check_pair(a: Mapping, b: Mapping):
    ma, mb = a["manifest"], b["manifest"]
    for key in ("demand_hash", "cohort", "duration_seconds", "seed", "period"):
        va, vb = _config(ma, key), _config(mb, key)
        if va is None or vb is None or va != vb:
            raise ValueError(f"Incompatible paired runs: {key}")
    cohort = _config(ma, "cohort")
    if isinstance(cohort, dict) and cohort.get("demand_end_seconds", 0) > _config(ma, "duration_seconds"):
        raise ValueError("Evaluation ends before target cohort window")
    for key in ("step_seconds", "action_step_seconds", "engine_version", "implementation_hash", "demand_scale", "rate_per_gate", "downstream_block", "od"):
        if _config(ma, key) != _config(mb, key):
            raise ValueError(f"Incompatible paired configuration: {key}")
    # Topology and policy hashes may differ by design, but all must be traceable.
    for manifest in (ma, mb):
        for key in ("run_id", "network_hash", "policy_hash"):
            if not manifest.get(key):
                raise ValueError(f"Missing provenance: {key}")
        if manifest.get("valid_for_ranking") is False:
            raise ValueError("Run audit marks results invalid for ranking")
        if manifest.get("status", "succeeded") not in ("succeeded", "completed"):
            raise ValueError("Cannot compare unfinished or failed runs")
    for run in (a, b):
        m = run["metrics"]
        for key in ("due", "completed", "inside", "external_waiting", "explicit_failure",
                    "tstt_vehicle_seconds", "collisions", "teleports"):
            value = m.get(key)
            if not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0:
                raise ValueError(f"Missing or invalid metric: {key}")
        if any(m[key] != int(m[key]) for key in ("due", "completed", "inside", "external_waiting", "explicit_failure")):
            raise ValueError("Vehicle counts must be integers")
        if m.get("generated", m["due"]) != m["due"]:
            raise ValueError("Evaluation ended before all target trips became due")
        if m["due"] != sum(m[key] for key in ("completed", "inside", "external_waiting", "explicit_failure")):
            raise ValueError("Conservation violation")
        if any(m[key] for key in ("explicit_failure", "collisions", "teleports")):
            raise ValueError("Anomalous run cannot participate in policy ranking")
        if m["due"] <= 0:
            raise ValueError("No due target-cohort trips")
    if a["metrics"]["due"] != b["metrics"]["due"]:
        raise ValueError("Target cohort counts differ")


def compare_pairs(pairs: Iterable[tuple[Mapping, Mapping]], *, phase="verification") -> dict:
    """Candidate-minus-baseline intervals for one policy/period/demand condition.

    Censored runs may show completion/backlog dominance, never full-trip time wins.
    Intervals are marginal/descriptive, with no family-wise or sequential guarantee.
    """
    pairs = list(pairs)
    if not pairs:
        raise ValueError("At least one matched pair required")
    seen, conditions, policy_versions = set(), set(), set()
    delta = {k: [] for k in ("tstt_vehicle_seconds", "completion_rate", "terminal_backlog", "external_waiting")}
    all_complete = True
    run_ids = []
    for baseline, candidate in pairs:
        _check_pair(baseline, candidate)
        ma, mb = baseline["manifest"], candidate["manifest"]
        policy_versions.add((ma["network_hash"], ma["policy_hash"], mb["network_hash"], mb["policy_hash"]))
        seed = _config(ma, "seed")
        if seed in seen:
            raise ValueError("Duplicate seed would create pseudoreplication")
        seen.add(seed)
        conditions.add(json.dumps([_config(ma,"policy"), _config(mb,"policy"), _config(ma,"period"),
                                   _config(ma,"demand_scale"), ma["cohort"], _config(ma,"duration_seconds"),
                                   _config(ma,"step_seconds"), _config(ma,"downstream_block")], sort_keys=True))
        a, b = baseline["metrics"], candidate["metrics"]
        backlog_a, backlog_b = a["inside"] + a["external_waiting"], b["inside"] + b["external_waiting"]
        all_complete &= backlog_a == 0 and backlog_b == 0
        delta["tstt_vehicle_seconds"].append(b["tstt_vehicle_seconds"] - a["tstt_vehicle_seconds"])
        delta["completion_rate"].append(b["completed"]/b["due"] - a["completed"]/a["due"])
        delta["terminal_backlog"].append(backlog_b - backlog_a)
        delta["external_waiting"].append(b["external_waiting"] - a["external_waiting"])
        run_ids.append({"baseline":ma["run_id"], "candidate":mb["run_id"], "seed":seed})
    if len(policy_versions) != 1:
        raise ValueError("Policy/network versions changed within a replicate batch")
    if len(conditions) != 1:
        raise ValueError("Do not pool different policy, period, demand, cohort or evaluation windows")
    intervals = {key: paired_interval(values) for key, values in delta.items()}
    completion_dominates = (all(x >= 0 for x in delta["completion_rate"]) and
                           all(x <= 0 for x in delta["terminal_backlog"]) and
                           all(x <= 0 for x in delta["external_waiting"]) and
                           any(x > 0 for x in delta["completion_rate"]))
    time_ci = intervals["tstt_vehicle_seconds"]
    conclusion = "inconclusive"
    if phase != "verification":
        conclusion = "exploratory_only"
    elif not all_complete:
        conclusion = "observed_completion_backlog_dominance" if completion_dominates else "censored_no_travel_time_ranking"
    elif time_ci["ci_high"] is not None and time_ci["ci_high"] < 0:
        conclusion = "lower_system_time_in_this_condition"
    elif time_ci["ci_low"] is not None and time_ci["ci_low"] > 0:
        conclusion = "higher_system_time_in_this_condition"
    return {"phase":phase, "run_pairs":run_ids, "paired_differences":intervals,
            "all_target_trips_complete":all_complete, "observed_completion_backlog_dominance":completion_dominates,
            "conclusion":conclusion, "travel_time_ranking_allowed":all_complete and phase=="verification",
            "caveats":["95% intervals are marginal fixed-sample intervals, not simultaneous or sequential guarantees.",
                       "Completed-only travel time is descriptive and never used to rank censored runs.",
                       "Random seeds quantify simulation noise, not field validity or parameter uncertainty."]}


def compare_runs(baseline: Mapping, candidate: Mapping) -> dict:
    return compare_pairs([(baseline, candidate)])


def analyze_study(runs: Iterable[Mapping], plan: Mapping) -> dict:
    """Validate seed split and exact stage membership before reporting comparisons."""
    expected = {}
    for phase in ("exploration", "verification"):
        for spec in plan[phase]:
            key = (phase,spec["policy"],spec["period"],spec["demand_scale"],spec["seed"])
            if key in expected:
                raise ValueError("Duplicate study specification")
            expected[key] = spec
    if set(plan["exploration_seeds"]) & set(plan["verification_seeds"]):
        raise ValueError("Verification seed leakage")
    indexed = {}
    for run in runs:
        manifest = run["manifest"]
        seed = _config(manifest,"seed")
        phase = "exploration" if seed in plan["exploration_seeds"] else "verification"
        key = (phase,_config(manifest,"policy"),_config(manifest,"period"),_config(manifest,"demand_scale"),seed)
        if key not in expected or key in indexed:
            raise ValueError(f"Unplanned or duplicate run: {key}")
        for name, expected_value in plan.get("experiment_config", {}).items():
            actual = _config(manifest, name)
            if actual is None and name in ("warmup_seconds", "demand_end_seconds"):
                actual = manifest.get("cohort", {}).get(name)
            if actual != expected_value:
                raise ValueError(f"Run violates frozen study configuration: {name}")
        parameters = manifest.get("config", {}).get("policy_parameters", {}) or {}
        if parameters != (expected[key].get("policy_parameters", {}) or {}):
            raise ValueError("Run violates frozen policy parameters")
        indexed[key] = run
    reports = []
    for phase, policy, period, scale in sorted({key[:4] for key in indexed if key[1] != "S0"}):
        pairs = []
        seeds = plan[f"{phase}_seeds"]
        for seed in seeds:
            base, cand = (phase,"S0",period,scale,seed), (phase,policy,period,scale,seed)
            if base in indexed and cand in indexed:
                pairs.append((indexed[base],indexed[cand]))
        if pairs:
            complete = len(pairs) == len(seeds)
            try:
                report = compare_pairs(pairs, phase=phase if complete else "incomplete")
            except ValueError as exc:
                report = {"phase": phase, "conclusion": "invalid_comparison", "error": str(exc),
                          "travel_time_ranking_allowed": False,
                          "run_pairs": [{"baseline": a["manifest"].get("run_id"),
                                         "candidate": b["manifest"].get("run_id"),
                                         "seed": _config(a["manifest"], "seed")} for a,b in pairs]}
            report.update(policy=policy,period=period,demand_scale=scale,complete=complete)
            reports.append(report)
    return {"expected_runs":len(expected), "available_runs":len(indexed),
            "missing_runs":[expected[k] for k in expected if k not in indexed], "comparisons":reports,
            "status":("invalid" if any(r["conclusion"] == "invalid_comparison" for r in reports)
                      else "complete" if len(indexed)==len(expected) else "incomplete"),
            "verification_status":plan["verification_status"]}
