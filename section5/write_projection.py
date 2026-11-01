#!/usr/bin/env python3
"""Writes READOUT_AND_PROJECTION_A7.md (+ sidecar): the hit(0.2) >= hit(0.1) check, the vectorised sweep, and the projected full-run time. Facts only. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "READOUT_AND_PROJECTION_A7.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
a7 = json.loads((RES / "a7_pilot_results.json").read_text()); v = json.loads((RES / "a7_readout_vectorised.json").read_text()); a6 = json.loads((RES / "a6_pilot_results.json").read_text())
ut = json.loads((RES / "unit_tests.json").read_text()); p1 = json.loads((RES / "pilot_results.json").read_text())
n_cmp = sum(len(x["by_ratio"]) for x in a7["scoring"].values())
# measured components
st = a7["stage_seconds"]; sweep_loop = st["h1a_sweep"]; sweep_vec = v["sweep_seconds_total"]; splice_wall = st["build_splices"]; n_spl = 1704
splice_cpu = n_spl * 0.2288                      # serial seconds per splice measured in the benchmark (PILOT_REPORT_2.md, 0.23 s)
per_fold_fixed = sweep_vec + st["section6_bisection"] + st["fit_all"] + 5.0   # sweep + bisection + final fits + prep (5 s allowance)
sel_h = 21 + 30 + 128; sel_b = 233                  # selection + tuning per fold, serial seconds (PILOT_REPORT.md projection table; BOCPD D=7 extrapolated)
eff = splice_cpu / splice_wall / 4
L = ["# Hit-rate readout check, vectorised sweep, projected run time", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. RAW fold 3, validation/test machinery data only; no selection, no evaluation-period data.", "",
     "## 1. hit(alarm rate 0.2) versus hit(alarm rate 0.1)", "",
     f"- Result: **no violation exists.** In `a6_pilot_results.json` and `a7_pilot_results.json` every detector and every variance ratio ({n_cmp} A7 readouts, all A6 readouts) has hit at 0.2 >= hit at 0.1; the re-computed readout also has none (`hit0p2_below_hit0p1` empty).",
     "- Why it cannot occur: the readout is `y_at(points, x0)` = the highest hit rate among sweep points whose null alarm rate is <= x0 (a running maximum), so it is non-decreasing in x0 by construction. The partial-area metric uses the same step function.",
     "- Guard added: `test_hit_rate_is_nondecreasing_in_alarm_rate` in `s5_tests.py` checks the property on 300 random point sets and on every stored A6/A7 readout (31 unit tests, 0 failures, 0 errors in the last run).",
     f"- Re-run of the readout only (same data, models, splices and seeds as the A7 pilot, vectorised sweep): maximum absolute difference to the stored loop-based values over partial area and both hit readouts = **{v['max_abs_difference_vs_stored_loop_values']}**; the D4 run-2 thresholds equal the stored ones for {sum(1 for x in v['scoring'].values() if x['run2_matches_stored'])} of {len(v['scoring'])} detectors. Curves are stored in `a7_readout_vectorised.json` so later readouts need no recomputation.", "",
     "## 2. Vectorised threshold sweep", "",
     "`s5_sweep.py` evaluates the alarm state machines (log-odds old-state rule, run-length-drop rule) for all thresholds and all sessions at once; only the loop over updates remains. Equality with the loop implementations (alarm counts and hit flags per session and threshold, with skips, K = 2 and 3) is asserted in `TestSweep.test_vectorised_equals_loops`.", "",
     "| | Loop (A7 pilot) | Vectorised |", "|---|---|---|", f"| H1(a) sweep, 8 detectors, 1,360 test + 344 calibration splices | {sweep_loop:.0f} s | {sweep_vec:.1f} s |",
     f"| speedup | | {sweep_loop / sweep_vec:.0f}x |", "",
     f"Per detector (s): " + ", ".join(f"{k} {x}" for k, x in v["sweep_seconds_per_detector"].items()) + f". The A7 pilot would take about {(a7['total_minutes']*60 - sweep_loop + sweep_vec)/60:.1f} min instead of {a7['total_minutes']} min (projected from the stage times; not re-run end to end).", "",
     "## 3. Projected run time, 34 folds (30 LEGACY + 4 RAW) with selection", "",
     f"Per-fold components (measured unless marked): splice features {n_spl} splices x 0.229 s = {splice_cpu:.0f} s CPU (the A7 pilot built them in {splice_wall:.0f} s wall on 4 workers: speedup {splice_cpu/splice_wall:.1f}x, efficiency {eff:.2f}); vectorised sweep + run-2 + curves {sweep_vec:.0f} s; Section 6 bisection {st['section6_bisection']:.0f} s; fits of the 8 final models {st['fit_all']:.0f} s; prep/other allowance 5 s (estimate). Selection (5.8: greedy forward to 6 of the 19 primary columns, then K tuning with 3 starts; serial seconds per fold from the PILOT_REPORT.md timings, BOCPD D = 7 extrapolated): Gaussian HMM 21, Student-t HMM 30, HSMM 128 (estimates from measured fit times), BOCPD 233.", "",
     "| Case | CPU s per fold | 34 folds CPU h | 34 folds wall h, 4 workers (speedup 3.3x as measured for splices) | 34 folds wall h, 3 workers (2.5x) |", "|---|---|---|---|---|"]
cases = [("H1 families only (3 HMM/HSMM), BOCPD scored with the HMM-selected features", sel_h + splice_cpu + per_fold_fixed),
         ("3 families + BOCPD with its own selection", sel_h + sel_b + splice_cpu + per_fold_fixed)]
for name, c in cases: L.append(f"| {name} | {c:.0f} | {34*c/3600:.1f} | {34*c/3600/(eff*4):.1f} | {34*c/3600/(eff*3):.1f} |")
raw_extra = lambda s: 4 * (s * 4.2 + splice_cpu + per_fold_fixed) / 3600
L += ["", "Add-ons (CPU hours; estimates unless stated):", "",
      f"- RAW sensitivity set (80 columns, 4 RAW folds): selection x4.2 (candidate count 80/19) plus a new set of splice features: {raw_extra(sel_h):.1f} h (3 families) or {raw_extra(sel_h + sel_b):.1f} h (with BOCPD selection).",
      "- 3 seeds: two further fits and sweeps of the final models per fold, splices reused: about 2 x 35 s per fold = 0.6 h over 34 folds.",
      "- Threshold +/-0.05 and LEGACY +5/+10 minute delay: re-use the stored curves and filters for the sweeps (minutes in total); delay re-runs repeat the sweep, about 25 s per fold per variant.",
      "- 1-min and 15-min grids on the final setups: not implemented for features in this pipeline, so not measured. From D5 (synthetic): HMM filtering is cheap on both grids, HSMM filtering at 1 min is about 66x slower per session, sweeps run 5x more updates; my estimate is 3-5 min CPU per fold for the 1-min grid, i.e. 1.7-2.8 h over 34 folds, and a few minutes in total for 15 min.",
      "- One-time: LEGACY feature columns for the 19 primary columns on the full LEGACY panel (1.56 million rows) and the 20-session baselines: not measured in this session (the Section 4 LEGACY feature passes were memory-heavy: two runs were killed for low memory); slow-path splice recomputation is not needed (fast path equals it, rtol 1e-9).",
      "- Not included: H2 placebo (10,000 draws per detector, asset and horizon), power simulations, 5.13 refits, evaluation-period runs.", "",
      "Memory: each worker holds the era panel and features (about 250 MB for RAW; the LEGACY panel is 5.7x larger by rows); with about 2 GB free the practical ceiling observed here is 4 RAW workers, and fewer for LEGACY.", "",
      "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_sweep.py", "s5_a7_sweep.py", "s5_tests.py", "write_projection.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("a7_readout_vectorised.json", "a7_pilot_results.json"): L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print("\n".join(L[L.index('## 3. Projected run time, 34 folds (30 LEGACY + 4 RAW) with selection'):][:14]))
