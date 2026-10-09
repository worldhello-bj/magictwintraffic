#!/usr/bin/env python3
"""Generate evidence-linked JSON/Markdown reports from actual run artifacts."""
import argparse
import json
import html
from pathlib import Path
from traffic_twin.analysis import analyze_study, build_study_plan, load_run


def evidence_svg(report):
    """Dependency-free seed-level evidence plot; never replace missing CIs by zero."""
    rows = [r for r in report["comparisons"] if "paired_differences" in r]
    panel_height = 85 + 32 * max(1, len(rows))
    height = 90 + 3 * panel_height
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="{height}" viewBox="0 0 1200 {height}">',
           '<rect width="100%" height="100%" fill="#f7fafc"/>',
           '<g font-family="Arial,sans-serif" fill="#16324f">',
           '<text x="28" y="30" font-size="20">Paired scenario evidence: candidate minus baseline</text>',
           '<text x="28" y="53" font-size="13">Marginal 95% fixed-sample intervals. Censored system time is finite-window exposure, not final travel time.</text>',
           f'<text x="28" y="75" font-size="13">Actual artifacts: {report["available_runs"]}/{report["expected_runs"]}; {html.escape(report["status"])}. No overall leaderboard.</text>']
    for panel, (metric,title) in enumerate([
            ("tstt_vehicle_seconds","Finite-window system time difference (vehicle-seconds)"),
            ("completion_rate","Completion-rate difference (fraction)"),
            ("terminal_backlog","Terminal-backlog difference (vehicles)")]):
        top = 100 + panel * panel_height
        out.append(f'<text x="28" y="{top}" font-size="16">{title}</text>')
        values = [0.0]
        for row in rows:
            stat = row["paired_differences"][metric]
            values.extend(x for x in (stat["mean_difference"],stat["ci_low"],stat["ci_high"]) if x is not None)
        low, high = min(values), max(values)
        span = high-low or 1.0
        low -= span*.05; high += span*.05
        def x(value): return 380 + 660*(value-low)/(high-low)
        out.append(f'<line x1="{x(0):.2f}" x2="{x(0):.2f}" y1="{top+15}" y2="{top+30+32*max(1,len(rows))}" stroke="#b3c2ce" stroke-dasharray="4,4"/>')
        if not rows:
            out.append(f'<text x="28" y="{top+36}" font-size="13">No valid matched comparisons available.</text>')
        for index,row in enumerate(rows):
            y = top+32+index*32
            stat = row["paired_differences"][metric]
            label = f'{row["phase"]}: {row["policy"]}, {row["period"]}, demand {row["demand_scale"]}'
            out.append(f'<text x="28" y="{y+4}" font-size="12">{html.escape(label)}</text>')
            if stat["ci_low"] is not None:
                out.append(f'<line x1="{x(stat["ci_low"]):.2f}" x2="{x(stat["ci_high"]):.2f}" y1="{y}" y2="{y}" stroke="#237a91" stroke-width="3"/>')
            out.append(f'<circle cx="{x(stat["mean_difference"]):.2f}" cy="{y}" r="4" fill="#16324f"/>')
            note = f'n={stat["n_pairs"]}' + ('; no CI' if stat['ci_low'] is None else '')
            out.append(f'<text x="1060" y="{y+4}" font-size="12">{note}</text>')
        out.append(f'<text x="380" y="{top+58+32*max(1,len(rows))}" font-size="11">{low:.4g}</text>')
        out.append(f'<text x="1000" y="{top+58+32*max(1,len(rows))}" font-size="11">{high:.4g}</text>')
    out.extend(['</g>','</svg>'])
    return "\n".join(out)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runs", type=Path, nargs="+", default=[Path("runs")])
    parser.add_argument("--plan", type=Path)
    parser.add_argument("--write-plan", type=Path)
    parser.add_argument("--candidates", nargs=2, choices=[f"S{i}" for i in range(1,8)])
    parser.add_argument("--output", type=Path, default=Path("reports/study.json"))
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text()) if args.plan else build_study_plan(candidates=args.candidates)
    if args.write_plan:
        args.write_plan.parent.mkdir(parents=True, exist_ok=True)
        args.write_plan.write_text(json.dumps(plan,indent=2)+"\n")
        return
    paths = sorted({p.parent for directory in args.runs for p in directory.glob("*/metrics.json") if (p.parent/"manifest.json").exists()})
    report = analyze_study([load_run(p) for p in paths], plan)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, allow_nan=False)+"\n")
    lines = ["# Traffic policy evidence report", "", "Synthetic scenarios; no local field validation claim.",
             f"Available runs: {report['available_runs']}/{report['expected_runs']}. Status: {report['status']}.",
             f"Verification: {report['verification_status']}.", "", "No overall policy leaderboard is inferred."]
    for item in report["comparisons"]:
        if item["conclusion"] == "invalid_comparison":
            lines.extend(["", f"## {item['phase']} / {item['policy']} / {item['period']} / demand {item['demand_scale']}",
                          f"INVALID: {item['error']}. No ranking or confidence interval produced.",
                          "Evidence: " + "; ".join(f"{r['baseline']} vs {r['candidate']}" for r in item['run_pairs'])])
            continue
        ci = item["paired_differences"]["tstt_vehicle_seconds"]
        completion = item["paired_differences"]["completion_rate"]
        backlog = item["paired_differences"]["terminal_backlog"]
        lines.extend(["", f"## {item['phase']} / {item['policy']} / {item['period']} / demand {item['demand_scale']}",
                      f"Conclusion: {item['conclusion']}; matched pairs: {ci['n_pairs']}.",
                      f"Candidate minus baseline finite-window system time: {ci['mean_difference']:.3f} vehicle-seconds; 95% CI [{ci['ci_low']}, {ci['ci_high']}].",
                      f"Completion-rate difference: {completion['mean_difference']:.6f}; 95% CI [{completion['ci_low']}, {completion['ci_high']}].",
                      f"Terminal-backlog difference: {backlog['mean_difference']:.3f} vehicles; 95% CI [{backlog['ci_low']}, {backlog['ci_high']}].",
                      "Evidence: " + "; ".join(f"{r['baseline']} vs {r['candidate']} (seed {r['seed']})" for r in item['run_pairs']),
                      *[f"- {text}" for text in item["caveats"]]])
    args.output.with_suffix(".md").write_text("\n".join(lines)+"\n")
    args.output.with_suffix(".svg").write_text(evidence_svg(report)+"\n")
    print(args.output)

if __name__ == "__main__":
    main()
