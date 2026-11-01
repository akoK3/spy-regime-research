#!/usr/bin/env python3
"""Writes PILOT_REPORT_A6.md (+ sidecar) from section5/results/a6_pilot_results.json. Facts only. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "PILOT_REPORT_A6.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
r = json.loads((RES / "a6_pilot_results.json").read_text()); ut = json.loads((RES / "unit_tests.json").read_text())
ck = r["checks"]; n_pass = sum(v == "PASS" or str(v).startswith("PASS") for g in ck.values() for v in g.values()); n_all = sum(len(g) for g in ck.values())
L = ["# Machinery pilot under Amendment A6", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Governed by `AMENDMENT_A6.md` (sha256 `{sha(ROOT / 'AMENDMENT_A6.md')}`), committed before this run. RAW fold 3, fixed a-priori feature sets (base = deseasonalized 5-min return; f3 = + rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj), K = 3, lambda = 39, 1 start, seed 0. No selection, no evaluation-period data, no protocol change from these results. Numbers are machinery outputs, not evidence.", "",
     "## Results", "", f"- Checks: {n_pass} of {n_all} PASS (exclusions 13, causal timing 5; listed below). Unit tests: {ut['run']} run, {len(ut['failures'])} failures, {len(ut['errors'])} errors.",
     f"- Stable days (D2 definition, A6 item 6b): {r['stable_days']['validation']} validation, {r['stable_days']['test']} test; H1(a) evaluable (>= 8 test days): {r['stable_days']['evaluable']}.", "",
     "| Check | Result |", "|---|---|"]
for g, v in ck.items():
    for a, b in v.items(): L.append(f"| {g}: {a} | {b} |")
L += ["", "### Section 6 thresholds (A6 item 3): calibrated on real validation sessions to 0.2 confirmed alarms per session; realized on test sessions", "",
      "| detector | threshold | flagged (no value <= 0.2) | validation rate | test rate realized |", "|---|---|---|---|---|"]
for k, v in r["calibration"].items(): L.append(f"| {k} | {v['threshold']} | {'FLAG' if v['flagged_no_feasible'] else 'no'} | {v['validation_rate']:.3f} | {v['test_rate_realized']:.3f} |")
L += ["", "### H1(a) machinery (A6 item 2): hit rate vs null alarm rate on the 18 test stable days; partial area for alarm rate 0-0.5 (range 0-1)", "",
      "Splices: 400 null; 960 breaks (5 ratios x 2 directions x 4 durations x 24). Power by ratio = partial area for the breaks of that variance ratio.", "",
      "| detector | pAUC all | R=1.5 | R=2 | R=3 | R=5 | R=10 | hit at alarm rate 0.1 | null alarm rate: strictest / loosest threshold | BOCPD/threshold run-2 value |", "|---|---|---|---|---|---|---|---|---|---|"]
for k, v in r["scoring"].items():
    b = v["by_ratio"]; a = list(v["alarm_rate_by_threshold"].values())
    L.append(f"| {k} | {b['all']['pauc_0_0p5']:.3f} | " + " | ".join(f"{b[x]['pauc_0_0p5']:.3f}" for x in ("1.5", "2", "3", "5", "10")) + f" | {b['all']['hit_at_alarm_rate_0p1']:.2f} | {a[-1]:.2f} / {a[0]:.2f} | {v['run2_threshold'] if v['run2_feasible'] else 'INFEASIBLE'} |")
d = r["scoring_difference_f3_minus_base_pauc_all"]
L += ["", "Partial-area difference f3 minus base (machinery output, not interpreted): " + ", ".join(f"{k} {v:+.3f}" for k, v in d.items()) + ".", "",
      "## Failures and findings (nothing excluded, nothing changed)", "",
      "1. Section 6 thresholds miss the 0.2 per session target at the strict end of the grid for the f3 models and for BOCPD: Gaussian HMM f3 and HSMM f3 are flagged (strictest value 0.9999 still gives 0.26 and 0.28 alarms per validation session); Student-t HMM f3 reaches 0.155 on validation but 0.271 on test; BOCPD base and f3 are flagged (run-length-drop m = 30 gives 0.47 and 0.60). Realized test frequencies range 0.07-0.53 against the target 0.2.",
      "2. H1(a) curves for the f3 models and BOCPD start at a null alarm rate above 0.1 (strictest-threshold null rates: f3 models 0.28-0.38, BOCPD f3 0.58) so the 0-0.5 window is mostly empty: hit at alarm rate 0.1 is 0.00 for all f3 models; BOCPD f3 partial area is 0.000. The base models have strictest-threshold null rates of 0.00-0.03 (BOCPD base 0.32) and score 0.06-0.09.",
      "3. Partial areas are small throughout (all-ratio 0.00-0.12; R = 10 up to 0.24), as in D2, D4 and D5; partial area rises monotonically with the variance ratio for every detector except BOCPD f3 (all zero).",
      "4. The D4 run-2 rule (A6 item 6a) is INFEASIBLE (no grid value with calibration null FA <= 0.10) for all three f3 HMM/HSMM models and for both BOCPD sets on validation stable-day splices; it selects 0.99 / 0.999 / 0.9999 for the three base HMM/HSMM models.",
      "5. The strict end of the HMM threshold grid (0.9999) and of the drop grid (m = 30) is not strict enough for 3-feature models on real data; A6 does not define a wider grid (change not made).",
      "6. Splice features, deseasonalization and filters are causal as tested (prefix invariance, truncated-history scale, alarm time = bar stamp + 1 min over 501 events); splice integrity PASS on 3 real splices.", "",
      "## Runtime (one machine, 4 worker processes for splice construction)", "", "| Stage | Seconds |", "|---|---|"]
for k, v in r["stage_seconds"].items(): L.append(f"| {k} | {v} |")
L += [f"| **total** | **{r['total_minutes']*60:.0f} ({r['total_minutes']} min)** |", "", "Fit seconds (K = 3, 1 start): " + ", ".join(f"{k} {v}" for k, v in r["fit_seconds"].items()) + ".", "",
      "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_a6.py", "s5_events.py", "s5_models.py", "s5_fast.py", "s5_tests.py", "write_a6_pilot_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
L.append(f"| section5/results/a6_pilot_results.json | `{sha(RES / 'a6_pilot_results.json')}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(f"{n_pass}/{n_all} checks pass")
