#!/usr/bin/env python3
"""Writes PILOT_REPORT_2.md and AMENDMENT_A6_DRAFT.md (draft, NOT applied) from section5/results/*.json. Facts only. Refuses to overwrite."""
import json, hashlib, datetime, re
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"
OUT, A6 = ROOT / "PILOT_REPORT_2.md", ROOT / "AMENDMENT_A6_DRAFT.md"
assert not OUT.exists() and not A6.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
fx = json.loads((RES / "fixes_results.json").read_text()); bn = json.loads((RES / "bench_results.json").read_text()); pr = json.loads((RES / "pilot_results.json").read_text())
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = ["base", "f3", "f6"]
now = datetime.datetime.now(datetime.timezone.utc).isoformat()
f = lambda x: "-" if x is None else (f"{x:.3g}" if isinstance(x, float) else str(x))

L = ["# Section 5 pilot report 2", "", "**Status: diagnosis and fix tests on the pilot fold (RAW fold 3). No selection run. No evaluation-period data. The fold's test segment is not used in this report.**", "",
     f"Written {now} UTC. Follows `PILOT_REPORT.md`. Protocol `SECTION5_PROTOCOL.md` sha256 `{sha(ROOT / 'SECTION5_PROTOCOL.md')}` (unchanged).", "",
     "## Setup", "",
     f"- Data: validation sessions of RAW fold 3 (58 sessions, TRAIN partition). {fx['n_break']} break and {fx['n_null']} null splices built from them (fast path, 4 worker processes). Models fitted on the inner-train segment only (189 sessions), K=3, lambda=39, 1 start, seed 0.",
     "- Feature sets (a priori, not selected): base = 5-min return; f3 = + rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj; f6 = f3 + downside5_strict__sadj, momentum15_endpoint, close_location_proxy.",
     "- Threshold rule as in 5.6: smallest grid threshold with at most 1 false alarm per 20 null sessions (null false-alarm rate <= 0.05 on the same null splices). Hit = confirmed (T_c) within 60 min of tau. 'Chance' = rate of a confirmed event in [tau, tau+60 min] of a NULL splice at the same threshold.",
     f"- Break splices: post/pre variance ratio quantiles (10/25/50/75/90%) {', '.join(f'{x:.2f}' for x in fx['break_variance_ratio_post_over_pre_quantiles'])} (half are stressed-to-calm).",
     "- Fast splice path (features of the spliced session computed alone; relative_volume20 and __sadj baselines from A's 20 previous sessions) equals the 21-session recomputation on 6 real splices (rtol 1e-9, all equal): " + f"{bn['equivalence_fast_vs_slow']['slow_s']:.2f} s vs {bn['equivalence_fast_vs_slow']['fast_s']:.2f} s per splice.", "",
     "## 1. Diagnosis: null-splice false alarms (raw 5-min return, as piloted)", "",
     "Share of the 100 null sessions with at least one confirmed event, and confirmed events by clock hour of T_d availability; 'pre/post' = T_d at or before / after the seam bar g.", ""]
bins = ["09:30-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00"]
for thr in ("0.9", "0.99"):
    L += [f"### Threshold {thr}", "", "| model | set | sessions with FA | events | " + " | ".join(bins) + " | pre | post |", "|---|---|---|---|" + "---|" * len(bins) + "---|---|"]
    for fam in FAMS:
        for s in SETS:
            e = fx["diag"][f"{fam}|{s}|{thr}"]
            L.append(f"| {fam} | {s} | {e['fa_rate']:.2f} | {e['events']} | " + " | ".join(str(e['events_by_clock_hour'].get(b, 0)) for b in bins) + f" | {e['events_T_d_at_or_before_seam']} | {e['events_T_d_after_seam']} |")
    L.append("")
L += ["### By feature: null false-alarm rate with the 5-min return + ONE feature (raw return, K=3 / lambda=39)", "", "| feature | " + " | ".join(f"{fam} @0.9 / @0.99" for fam in FAMS) + " |", "|---|" + "---|" * len(FAMS)]
feats = sorted({k.split("|", 1)[1] for k in fx["per_feature"]})
for ft in feats:
    L.append(f"| {ft} | " + " | ".join(f"{fx['per_feature'][f'{fam}|{ft}']['0.9']:.2f} / {fx['per_feature'][f'{fam}|{ft}']['0.99']:.2f}" for fam in FAMS) + " |")
tot = {fam: sum(fx["per_feature"][f"{fam}|{ft}"]["0.99"] for ft in feats) / len(feats) for fam in FAMS}
L += ["", "Findings:",
      "- False alarms are spread over all clock hours (no concentration at the open, lunch or close) and split roughly evenly between before and after the seam. They are not seam artefacts and not a time-of-day seasonality effect.",
      "- The return-only models have 0 false alarms at 0.99 (HSMM 0.10); every added feature raises them. At 0.99 the mean null false-alarm rate over single-feature models is " + ", ".join(f"{k} {v:.2f}" for k, v in tot.items()) + ".",
      "- f6 is worse than f3 for all four families (null false-alarm rate at 0.99: 0.25-0.45 vs 0.16-0.25).", ""]

L += ["## 2-3. Fix tests", "", "Configurations: piloted = raw return, grid <= 0.99; (b) = grid extended by 0.995, 0.999, 0.9995, 0.9999; (a) = 5-min return divided by the median |return| of the same grid slot over the previous 20 sessions (>= 10 finite; causal; spliced sessions use A's history); (d) = BOCPD persistence: at the would-be T_c, P(run length <= 5) >= threshold; (c) = miss rule, delay censored at 60 min (a metric rule: median over all breaks with misses = 60).", "",
      "| model | set | configuration | threshold | null FA | hit rate | chance (null window) | median delay of hits (min) | median delay, misses = 60 (min) |", "|---|---|---|---|---|---|---|---|---|"]
for k, v in fx["fixes"].items():
    fam, s, label = k.split("|")
    var = "des" if label.startswith("a") else "raw"
    thr = v["threshold"]
    if thr is None: L.append(f"| {fam} | {s} | {label} | none feasible | - | - | - | - | - |"); continue
    ch = fx["sweep"][f"{fam}|{s}|{var}"][str(thr)]["null_window_rate"]
    L.append(f"| {fam} | {s} | {label} | {thr} | {v['null_fa']:.2f} | {v['hit_rate']:.2f} | {ch:.2f} | {f(v['median_delay_hits_min'])} | {f(v['median_delay_censored60_min'])} |")
feas = lambda lab, sets=("base", "f3", "f6"): sum(1 for fam in FAMS for s in sets if fx["fixes"].get(f"{fam}|{s}|{lab}", {}).get("threshold") is not None)
nfeas = nabove = 0
for k_, v_ in fx["fixes"].items():
    if v_["threshold"] is None: continue
    fam_, s_, lab_ = k_.split("|"); var_ = "des" if lab_.startswith("a") else "raw"
    nfeas += 1; nabove += v_["hit_rate"] > fx["sweep"][f"{fam_}|{s_}|{var_}"][str(v_["threshold"])]["null_window_rate"]
best = max((v["hit_rate"], k) for k, v in fx["fixes"].items() if v["threshold"] is not None)
L += ["", "Feasibility (number of the 12 model x set cells with a threshold meeting the false-alarm target): piloted " + str(feas("piloted (raw, grid<=0.99)")) + ", (b) " + str(feas("b: extended grid")) + ", (a) " + str(feas("a: deseasonalised return")) + ", (a)+(b) " + str(feas("a+b")) + ".", "",
      "Findings:",
      "- (b) extended grid: makes f3 feasible for all four families (thresholds 0.999 to 0.9999). f6 stays infeasible for the Gaussian HMM, HSMM and BOCPD in every configuration and for the Student-t HMM except raw at 0.9999 (null FA 0.05).",
      "- (a) deseasonalised return: makes the return-only Gaussian HMM, HSMM and BOCPD feasible at lower thresholds (Gaussian 0.99 to 0.90, HSMM none to 0.95, BOCPD 0.70 to 0.85) with hit rates 0.04-0.05. For f3 it does not help without (b).",
      "- (d) persistence: BOCPD return-only threshold falls from 0.70 to 0.55 (hit 0.05 to 0.07); BOCPD f3 with (a)+(b)+(d) reaches hit 0.11 at 0.995. Effect is small.",
      f"- Hit rates are not reasonable under any configuration: the highest feasible hit rate is {best[0]:.2f} ({best[1]}). At the false-alarm target " + f"{nabove} of {nfeas} feasible cells have a hit rate above the chance rate, and hit rates are 0.00-0.11 (0.04-0.11 where hit > 0).",
      "- Away from the target the detectors carry signal (Gaussian HMM f3, deseasonalised, threshold 0.99: hit 0.22 vs chance 0.04, but null false-alarm 0.15, above target).",
      "- (c) miss rule: with hit rates below 50% the censored median delay equals 60 min in every cell, so it carries no information; hit rate (and delay among hits) is the usable summary until hit rates exceed 50%.",
      "- Unconstrained detection (threshold 0.5 sweeps in `fixes_results.json`, key `sweep`) reaches hit 0.20-0.78 with null false-alarm 0.26-0.86 in the cells inspected (Gaussian base/f3, HSMM base, BOCPD base/f3): the trade-off between the false-alarm target and hit rate is steep for the 3-update hold on a 5-min grid.",
      "- Not tested (listed for the decision on A6): shorter hold, a looser false-alarm target, a longer hit window, regime-specific (direction-specific) thresholds, hit rate split by direction.", ""]

W = bn["splice_pool_seconds_for_64"]; Fp = bn["fit_pool_seconds_for_16_hsmm_incl_init"]
sp_fast, sp_slow = bn["equivalence_fast_vs_slow"]["fast_s"], bn["equivalence_fast_vs_slow"]["slow_s"]
sel_serial = 412.0   # seconds per fold, selection + tuning, 4 families (PILOT_REPORT.md projection table)
spl_fast = 800 * sp_fast
L += ["## 4. Parallelization and re-projected budget", "",
      f"- Machine: {bn['logical_cores']} logical cores, about 2.3 GB free RAM at the time; each worker process holds about 250 MB, so 4 workers were used (6 is the practical ceiling).",
      f"- Splice features, 64 splices: 1 worker {W['1']:.1f} s, 4 workers {W['4']:.1f} s (speedup {W['1']/W['4']:.1f}x including process start and data load in each worker).",
      f"- Model fits, 16 HSMM fits including setup: 1 worker {Fp['1']:.1f} s, 4 workers {Fp['4']:.1f} s (speedup {Fp['1']/Fp['4']:.1f}x including the same per-worker setup).",
      f"- 200 + 200 splices (fixes run) with 4 workers: 18-19 s wall.",
      f"- Splice feature recomputation per fold: slow path {800*sp_slow:.0f} s (800 splices x {sp_slow:.2f} s); fast path {spl_fast:.0f} s serial.", "",
      "Per fold (800 splices + selection and tuning for the 4 families, serial 412 s from PILOT_REPORT.md; BOCPD D=7 extrapolated). Folds are independent, so parallelism is across folds; the measured end-to-end speedups above include setup, a long run amortizes setup. Two efficiency assumptions: measured (2.0x at 4 workers) and amortized (0.85 per worker).", "",
      "| Setting | Seconds per fold | 34 folds (h) | 17 folds (h) |", "|---|---|---|---|"]
base_fold = sel_serial + spl_fast
for name, fold_s in (("serial, slow splice path (PILOT_REPORT.md)", sel_serial + 800 * sp_slow), ("serial, fast splice path", base_fold),
                     ("4 workers, measured speedup 2.0x", base_fold / 2.0), ("4 workers, amortized 0.85 efficiency", base_fold / (4 * 0.85)), ("6 workers, amortized 0.85 efficiency", base_fold / (6 * 0.85))):
    L.append(f"| {name} | {fold_s:.0f} | {34*fold_s/3600:.1f} | {17*fold_s/3600:.1f} |")
L += ["", f"- Selection and tuning (412 s of the serial {base_fold:.0f} s) is now the dominant cost: BOCPD 233 s and HSMM 128 s per fold.",
      "- Sensitivity set (80 columns, RAW only, 4 folds): selection x4.2, i.e. about 29 min serial per fold.",
      "- Not included: 1-/15-min grids, 3 seeds, +/-0.05 threshold runs, LEGACY delay runs, H2 placebo (10,000 draws), power simulations, 5.13 refits.", "",
      "## 5. 80 vs 83", "",
      "- Matrix v2 keeps 83 sensitivity columns; 5.2 drops `jump_variation__sadj` (three columns: jump_variation_15/30/60__sadj), so the set that reaches models is 80. `assert_pool` and the unit tests already enforce 80 (and 83 for the matrix itself); no code uses 83 as a model pool.",
      "- The protocol file is not edited (changes only by dated, hashed amendment); the correction is item 1 of `AMENDMENT_A6_DRAFT.md`.", "",
      "## Choices made without asking (user away)", "",
      "- Diagnosis and fix tests use validation splices only (100 + 100). The fold's test segment was not scored, to keep it unused for choosing fixes.",
      "- Threshold calibration and hit rate use the same 100 + 100 splices (hit rate is not used to choose the threshold).",
      "- 'Reasonable' hit rate: above 50% at the false-alarm target (my criterion; the protocol has none). No configuration meets it.",
      "- Deseasonalization: scale = median |ret5| per grid slot over the previous 20 sessions, >= 10 finite, NaN if <= 0 (a missing scale is a skipped update); applied to the return column only; the preprocessing (log/winsorize/z-score) is refit on the deseasonalized column.",
      "- Persistence statistic: P(run length <= 5) = hold + 2 at the would-be T_c, same threshold as the alarm. The choice of 5 was not tuned.",
      "- Extended grid values 0.995, 0.999, 0.9995, 0.9999 chosen by me; the 0.9999 cell is printed as 1.0 in some outputs (rounded).",
      "- Process pool of 4 workers (memory-limited); the first benchmark attempt was re-run with 1 and 4 workers only. The earlier session's benchmark did not finish; cause not established beyond memory and spawn overhead.",
      "- A6 is drafted as a file only; nothing in the pipeline or protocol was changed to apply it, except the BOCPD persistence statistic and the extended-grid option, which were added as off-by-default code paths.", "",
      "## Files", "", "| File | SHA-256 |", "|---|---|"]
for fn in ("s5_fast.py", "s5_fixes.py", "s5_bench.py", "s5_eval.py", "s5_events.py", "s5_models.py", "write_pilot_report_2.py"):
    L.append(f"| section5/{fn} | `{sha(HERE / fn)}` |")
for fn in ("fixes_results.json", "bench_results.json"):
    L.append(f"| section5/results/{fn} | `{sha(RES / fn)}` |")
L.append(f"| AMENDMENT_A6_DRAFT.md | see its sidecar `AMENDMENT_A6_DRAFT.sha256` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")

a = ["# Amendment A6 (DRAFT, NOT APPLIED)", "", "**Status: DRAFT. Not applied. No run is governed by this document until it is dated, hashed and approved.**", "",
     f"Drafted {now} UTC against `SECTION5_PROTOCOL.md` sha256 `{sha(ROOT / 'SECTION5_PROTOCOL.md')}`. Evidence: `PILOT_REPORT.md`, `PILOT_REPORT_2.md`, `section5/results/fixes_results.json`.", "",
     "## Proposed changes", "",
     "1. 5.2 count: the sensitivity pool is 80 columns, not 83 (83 kept in matrix v2 minus jump_variation_15/30/60__sadj dropped by 5.2).",
     "2. 5.6 threshold grid: add 0.995, 0.999, 0.9995, 0.9999 above 0.99 for all families. Evidence: with the grid capped at 0.99 no threshold meets the false-alarm target for any 3-feature model; with the extension all four families are feasible at f3 (0.999-0.9999).",
     "3. 5.2 / 5.3 return input: replace the 5-min return by the 5-min return divided by the causal slot scale (median |return| of the same grid slot over the previous 20 sessions, >= 10 finite). Evidence: makes return-only baselines feasible at lower thresholds (Gaussian HMM 0.99 to 0.90, HSMM none to 0.95, BOCPD 0.70 to 0.85); gain for feature models is nil without item 2. Applies to baselines and feature models alike.",
     "4. 5.6 miss rule: delays are censored at 60 min for misses; report hit rate and the delay among hits next to the censored median. Evidence: censored median is 60 min in every pilot cell because hit rates are below 50%, so the median-delay comparison in H1(a) is uninformative at the current hit rates.",
     "5. 5.5 BOCPD persistence: T_c additionally requires P(run length <= hold + 2) >= threshold at the third update after T_d. Evidence: small gain (return-only threshold 0.70 to 0.55; f3 hit rate up to 0.11).",
     "6. 5.6 reporting: report the chance rate (confirmed event in [tau, tau+60 min] of null splices at the same threshold) beside every hit rate.",
     "7. 5.5 definitions to state explicitly (currently chosen in the pipeline, see PILOT_REPORT.md): T_c is the third real update after T_d; BOCPD alarm = rising edge; refractory starts at T_c.", "",
     "## Open points this draft does not settle (decision needed)", "",
     "- Hit rates at the 1-per-20 false-alarm target are 0.00-0.11 in every tested configuration (the highest is in the fixes table of PILOT_REPORT_2.md). H1(a) as specified has little power at 200 breaks per fold. Untested options: shorter hold, looser false-alarm target, longer hit window, split by direction.",
     "- f6 (6 features) is infeasible for three of four families in every configuration; the 5.8 greedy search to 6 features will often hit infeasible setups unless the false-alarm target or grid is revised.",
     "- BOCPD regime-conditional QLIKE forecast (two regimes from P(changepoint within 3)) is a pipeline choice; the protocol should define it.", "",
     "## Not applied", "", "Nothing above has been applied to code defaults or to the protocol. The extended grid and the persistence rule exist as off-by-default options (`thr_grid(extended=True)`, `persistence=True`)."]
A6.write_bytes(("\n".join(a) + "\n").encode("utf-8")); A6.with_suffix(".sha256").write_text(f"{sha(A6)}  {A6.name}\n", encoding="ascii")
print(OUT.read_text(encoding="utf-8")[:3000])
