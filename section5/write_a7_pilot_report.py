#!/usr/bin/env python3
"""Writes PILOT_REPORT_A7.md (+ sidecar) from section5/results/a7_pilot_results.json and a6_pilot_results.json. Facts only. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "PILOT_REPORT_A7.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
r = json.loads((RES / "a7_pilot_results.json").read_text()); a6 = json.loads((RES / "a6_pilot_results.json").read_text()); ut = json.loads((RES / "unit_tests.json").read_text())
ck = r["checks"]; n_pass = sum(str(v).startswith("PASS") for g in ck.values() for v in g.values()); n_all = sum(len(g) for g in ck.values())
L = ["# Machinery pilot under Amendment A7", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Governed by `AMENDMENT_A7.md` (sha256 `{sha(ROOT / 'AMENDMENT_A7.md')}`), committed before this run; A7 widens the threshold range only (continuous thresholds, bisection to the fixed 0.2 alarms/session target, same range for the H1(a) sweep). Same design as the A6 pilot: RAW fold 3, fixed a-priori feature sets, K = 3, lambda = 39, no selection, no evaluation-period data, no protocol change from these results. Machinery outputs, not evidence.", "",
     "## Results", "", f"- Checks: {n_pass} of {n_all} PASS (exclusions {len(ck['exclusions'])}, causal timing {len(ck['causal_timing'])}). Unit tests: {ut['run']} run, {len(ut['failures'])} failures, {len(ut['errors'])} errors. The embargo-spacing check of the A6 pilot is not in this script's list (the embargo is enforced by an assertion inside `fold_segments`, which ran).",
     f"- Stable days: {r['stable_days']['validation']} validation, {r['stable_days']['test']} test (H1(a) evaluable: {r['stable_days']['evaluable']}).", "",
     "### Section 6 thresholds by bisection (target 0.2 confirmed alarms per session on the real validation sessions; HMM/HSMM theta in log-odds, BOCPD drop size m)", "",
     "| detector | A7 threshold | probability equivalent | validation rate | test rate realized | rate evaluations | A6 grid threshold | A6 validation / test |", "|---|---|---|---|---|---|---|---|"]
for k, v in r["calibration"].items():
    o = a6["calibration"][k]; L.append(f"| {k} | {v['threshold']:.4g} ({v['info']}) | {('%.12f' % v['equivalent_probability_threshold']) if v['equivalent_probability_threshold'] else '-'} | {v['validation_rate']:.3f} | {v['test_rate_realized']:.3f} | {v['rate_evaluations']} | {o['threshold']}{' FLAG' if o['flagged_no_feasible'] else ''} | {o['validation_rate']:.3f} / {o['test_rate_realized']:.3f} |")
L += ["", "### H1(a) machinery: partial area (null alarm rate 0-0.5, range 0-1) on the 18 test stable days; sweep theta 0-30 step 0.25 (121 values), m 1-80 step 1 (80 values)", "",
      "| detector | pAUC all (A6) | R=1.5 | R=2 | R=3 | R=5 | R=10 | hit at alarm rate 0.1 | hit at 0.2 | smallest null alarm rate in sweep | sweep points with rate <= 0.5 | run-2 value |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for k, v in r["scoring"].items():
    b = v["by_ratio"]
    L.append(f"| {k} | {b['all']['pauc_0_0p5']:.3f} ({a6['scoring'][k]['by_ratio']['all']['pauc_0_0p5']:.3f}) | " + " | ".join(f"{b[x]['pauc_0_0p5']:.3f}" for x in ("1.5", "2", "3", "5", "10")) + f" | {b['all']['hit_at_alarm_rate_0p1']:.2f} | {b['all']['hit_at_alarm_rate_0p2']:.2f} | {v['smallest_null_alarm_rate_in_sweep']:.3f} | {v['x_values_in_0_0p5']} | {v['run2_threshold'] if v['run2_feasible'] else 'INFEASIBLE'} |")
d = r["scoring_difference_f3_minus_base_pauc_all"]; d6 = a6["scoring_difference_f3_minus_base_pauc_all"]
L += ["", "Partial-area difference f3 minus base (machinery output, not interpreted): " + ", ".join(f"{k} {v:+.3f} (A6 {d6[k]:+.3f})" for k, v in d.items()) + ".", "",
      "## Failures and findings (nothing excluded, nothing changed)", "",
      "1. The A6 failures are resolved mechanically: all 8 bisections end at a validation rate of 0.19 (<= 0.2, none flagged); the H1(a) sweep now has 46-113 points with null alarm rate <= 0.5 for every detector (A6: the f3 models started above 0.1); the D4 run-2 rule is feasible for all 8 detectors (A6: 5 infeasible).",
      "2. Realized test-session frequencies differ from the target: 0.13-0.17 (base HMM/HSMM), 0.21-0.30 (f3 models), 0.23 (BOCPD base), 0.31 (BOCPD f3); the 3-feature models and BOCPD exceed 0.2 on test by 0.01-0.11.",
      "3. BOCPD thresholds land at drop sizes m = 47 and 44 updates: with the most likely run length at most t after t updates, a drop of 44 or more needs t >= 44, i.e. the alarm can only fire from about 13:10 on. Break splices start at 11:05-14:30 (updates 19-60), so at the target rate the BOCPD alarm cannot detect early breaks. BOCPD partial areas are 0.086 (base) and 0.040 (f3).",
      "4. Gaussian HMM f3 has a smallest null alarm rate of 0.050 at theta = 30 (the upper bound), so its curve does not reach rate 0; the other detectors reach 0.000 inside the range.",
      "5. Partial areas are larger than under A6 for every detector (f3 models 0.15-0.22 against 0.06-0.12; base HMM/HSMM models 0.09-0.10 against 0.07-0.09) and rise with the variance ratio; the hit rate at alarm rate 0.1 is 0.00-0.11 and at 0.2 is 0.01-0.15.",
      "6. Edge case found by the new unit test and fixed in the three event functions that track an 'old state' (`detect_old_state`, `detect_old_state_logodds`, `detect_states_mass`): when the first updates of a session are skipped the old state was undefined and the code raised an error; now the first real update sets the old state. Behaviour is otherwise unchanged; the A6 pilot did not hit the case.",
      "7. The sweep stage dominates the runtime (see below): 121 thresholds x 8 detectors x 1,360 test splices in python loops.", "",
      "## Runtime (one machine, 4 worker processes for splice construction)", "", "| Stage | Seconds |", "|---|---|"]
for k, v in r["stage_seconds"].items(): L.append(f"| {k} | {v} |")
L += [f"| **total** | **{r['total_minutes']*60:.0f} ({r['total_minutes']} min)** |", "", "A6 pilot total was 3.0 min.", "", "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_a7.py", "s5_events.py", "s5_a6.py", "s5_tests.py", "write_amendment_a7.py", "write_a7_pilot_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
L.append(f"| section5/results/a7_pilot_results.json | `{sha(RES / 'a7_pilot_results.json')}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(f"{n_pass}/{n_all} checks pass")
