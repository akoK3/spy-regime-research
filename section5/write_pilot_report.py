#!/usr/bin/env python3
"""Writes PILOT_REPORT.md (+ sidecar hash) from section5/results/*.json. Facts only. Refuses to overwrite."""
import json, hashlib, datetime, subprocess
from pathlib import Path
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"
OUT = ROOT / "PILOT_REPORT.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
r = json.loads((RES / "pilot_results.json").read_text()); ut = json.loads((RES / "unit_tests.json").read_text()); dg = json.loads((RES / "diag_pilot_fa.json").read_text())
T = pd.DataFrame(r["timings"])
fit = T[T.unit == "fit"]
f1 = lambda fam, v: float(fit[(fit.family == fam) & (fit.variant == v) & (fit.starts == 1) & (fit.K == 3)].seconds.iloc[0])
f3s = lambda fam, v: float(fit[(fit.family == fam) & (fit.variant == v) & (fit.starts == 3)].seconds.iloc[0])
flt = lambda fam, v, u: float(T[(T.unit == u) & (T.family == fam) & (T.variant == v) & T.lam.isna()].seconds.iloc[0]) if "lam" in T else float(T[(T.unit == u) & (T.family == fam) & (T.variant == v)].seconds.iloc[0])
SPLICE_S = 4.3   # seconds per spliced session (feature recomputation); from run-log timestamps of the first pilot pass: 24 splices in 1.7-1.8 min, four batches

# ---- projection: per fold, one family, greedy forward (<=6 steps, remaining candidates 19..14) + K/lambda tuning with 3 starts (feature and baseline)
cand_early, cand_late = 19 + 18 + 17, 16 + 15 + 14        # steps 1-3 (D<=4) and 4-6 (D<=7)
proj = {}
for fam in ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"):
    if fam == "bocpd":
        e4 = f1("bocpd", "f3") if False else float(T[(T.unit == "filter_train") & (T.family == "bocpd") & (T.variant == "f3") & (T.lam.isna())].seconds.iloc[0]) + float(T[(T.unit == "filter_val") & (T.family == "bocpd") & (T.variant == "f3")].seconds.iloc[0])
        e7 = e4 * 7 / 4          # extrapolated: no D=7 BOCPD filter was timed
        tune = 3 * 2 * e4
    else:
        v4 = f1(fam, "f3") + float(T[(T.unit == "filter_val") & (T.family == fam) & (T.variant == "f3")].seconds.iloc[0]) + float(T[(T.unit == "filter_train") & (T.family == fam) & (T.variant == "f3")].seconds.iloc[0])
        v7 = f1(fam, "f6") + (v4 - f1(fam, "f3"))
        e4, e7 = v4, v7
        nK = 2 if fam == "hsmm" else 3
        tune = nK * 2 * (f3s(fam, "f3") + (v4 - f1(fam, "f3")))
    proj[fam] = dict(selection_s=cand_early * e4 + cand_late * e7, tuning_s=tune)
sel = {k: v["selection_s"] + v["tuning_s"] for k, v in proj.items()}
spl = 800 * SPLICE_S
fold_s = sum(sel.values()) + spl
sens_factor = 80 / 19

L = ["# Section 5 pilot report", "", "**Status: pilot of DRAFT protocol; no selection run; no evaluation-period data touched.**", ""]
now = datetime.datetime.now(datetime.timezone.utc)
L += [f"Written {now.isoformat()} UTC. Protocol: `SECTION5_PROTOCOL.md` sha256 `{sha(ROOT / 'SECTION5_PROTOCOL.md')}`.", "",
      "## Scope of the run", "",
      f"- Fold: RAW fold 3 (smallest outer block, 75 sessions). Train {r['segments']['train']}, validation {r['segments']['val']}, test {r['segments']['test']} sessions after 5-session embargoes; sessions 2023-09-07..2024-12-23, all TRAIN partition (asserted against `section430_executable_split_manifest.csv`).",
      "- Models fitted with fixed a-priori feature sets (timing only; not selected): f3 = rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj; f6 = f3 + downside5_strict__sadj, momentum15_endpoint, close_location_proxy; base = 5-min return only. K=3, lambda=39, seed 0.",
      f"- Versions: {r['versions']}. Total pilot compute after features: {r['total_minutes']} min (splice features cached from the first pass).",
      "- Splices in pilot: 24 break + 24 null on validation, 24 + 24 on test (protocol: 200 + 200).", "",
      "## Unit tests (synthetic data)", "", f"- {ut['run']} tests, {len(ut['failures'])} failures, {len(ut['errors'])} errors (`section5/results/unit_tests.json`). Families covered: Gaussian HMM, Student-t HMM, HSMM, BOCPD; also events (T_d, T_c, hold, skip reset, refractory, first-2-update rule, direction), pool/era/TRAIN assertions, preprocessing, LM Student-t threshold, checkpoint resume, splice construction, tercile pairing, QLIKE/DM/threshold choice.",
      "- Defects found by the tests and fixed before the pilot: Student-t df update counted the (nu+D) digamma terms twice (df stuck at the 2.1 bound on Gaussian data); NaN-unaware comparison in the splice test; splice tau drawn at a bar with a missing price (assert in `make_splice`); sessions with missing closes now excluded from splice sampling (< 98% finite closes).", "",
      "## Splice-integrity tests on real RAW data (3 splices, B outside A's 20-session history window)", "",
      "| iA | iB | g | continuous at tau | tau exact (first changed bar = g+1) | tau = availability of bar g | tau in 11:00-14:30 | pre-tau features = A native (rtol 1e-9) | B pre-tau edits change nothing | A post-tau edits change nothing | post-tau features differ | PASS |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for x in r["integrity"]:
    c = x["checks"]; L.append(f"| {x['iA']} | {x['iB']} | {x['g']} | " + " | ".join("PASS" if c[k] else "FAIL" for k in ("price_continuous_at_tau", "tau_exact_first_changed_bar_is_g_plus_1", "tau_is_availability_of_bar_g", "tau_in_11:00-14:30", "pre_tau_features_equal_A_native", "B_pre_tau_changes_do_not_move_spliced_features", "A_post_tau_changes_do_not_move_spliced_features", "post_tau_features_differ_from_A_native")) + f" | {'PASS' if c['pass'] else 'FAIL'} |")
L += ["", "- The first pass of these tests reported 2 of 3 FAIL because B sat inside A's 20-session history (the relative-volume and __sadj baselines legitimately use that history) and because NaN closes compared unequal. Test selection and comparison were corrected; the pipeline was unchanged.",
      "- BOCPD confirmation tests (unit tests, synthetic streams): alarm at T_d; T_c at the third real update after T_d with no new alarm; a skip resets the count (T_c moves from update 13 to 15 in the test case); a new alarm during the hold restarts the candidate; no alarm in the first two updates; the third update is not a rising edge; unconfirmed at the close is dropped and counted. All PASS. State-model equivalents (HMM/HSMM) also PASS.", "",
      "## Timings (seconds, one core, RAW fold 3: 14,706 train grid bars)", "", "| Family | base D=1, 1 start | f3 D=4, 1 start | f6 D=7, 1 start | base 3 starts | f3 3 starts | filter val (58 sessions, f3) |", "|---|---|---|---|---|---|---|"]
for fam in ("gaussian_hmm", "student_t_hmm", "hsmm"):
    L.append(f"| {fam} (K=3) | {f1(fam,'base'):.2f} | {f1(fam,'f3'):.2f} | {f1(fam,'f6'):.2f} | {f3s(fam,'base'):.2f} | {f3s(fam,'f3'):.2f} | {float(T[(T.unit=='filter_val')&(T.family==fam)&(T.variant=='f3')].seconds.iloc[0]):.3f} |")
b = lambda v, u: float(T[(T.unit == u) & (T.family == "bocpd") & (T.variant == v) & T.lam.isna()].seconds.iloc[0])
L += [f"| bocpd (lambda=39; no fit; filter train) | {b('base','filter_train'):.2f} | {b('f3','filter_train'):.2f} | not timed | n/a | n/a | {b('f3','filter_val'):.3f} |", "",
      f"- HSMM K=2 base 1 start: {float(fit[(fit.family=='hsmm')&(fit.K==2)].seconds.iloc[0]):.2f} s. BOCPD filter of train at lambda 12 / 78 (f3): {float(T[(T.unit=='filter_train')&(T.lam==12)].seconds.iloc[0]):.2f} / {float(T[(T.unit=='filter_train')&(T.lam==78)].seconds.iloc[0]):.2f} s.",
      f"- EM iterations at 1 start: Gaussian 21/12/14, Student-t 20/17/19, HSMM 13/12/13 (base/f3/f6); tol 1e-4 reached before the 200 cap in every fit.",
      f"- Load RAW panel and compute the 20 columns: {float(T[T.unit=='load_era_and_features'].seconds.iloc[0]):.1f} s (cached afterwards). LM Student-t fit: {float(T[T.unit=='lm_student_t_threshold'].seconds.iloc[0]):.2f} s.",
      f"- Spliced-session feature recomputation: about {SPLICE_S} s per splice (24 splices in 1.7-1.8 min, from run-log timestamps; the per-splice timer was lost on cached reruns). Splice filtering is negligible (HSMM 0.009 s, BOCPD 0.08 s per 24 sessions).", "",
      "## Projected budget (one core)", "",
      "Assumptions: greedy forward selection tries all remaining primary candidates at each of 6 steps (99 fits per family per fold; steps 1-3 timed at D=4, steps 4-6 at D=7), each fit followed by filtering of train and validation; K/lambda tuning with 3 starts for the feature model and the baseline; 200 + 200 validation and 200 + 200 test splices per fold with features recomputed once and shared by all families. BOCPD D=7 is extrapolated (D=4 time x 7/4).", "",
      "| Item | Seconds per fold |", "|---|---|"]
for fam, v in proj.items(): L.append(f"| selection + tuning, {fam} | {v['selection_s'] + v['tuning_s']:.0f} |")
L += [f"| splice feature recomputation (800 splices) | {spl:.0f} |", f"| **Total per fold** | **{fold_s:.0f} ({fold_s/60:.0f} min)** |", "",
      f"- 34 folds: {34*fold_s/3600:.0f} h. Every 2nd fold (17): {17*fold_s/3600:.0f} h. Splice feature recomputation is {spl/fold_s*100:.0f}% of the per-fold time.",
      f"- Sensitivity set (80 columns, RAW only, 4 folds): selection scales with the candidate count (about {sens_factor:.1f}x the selection part, {sum(sel.values())*sens_factor/60:.0f} min per fold) plus the same splice cost.",
      "- Not included: 1-/15-min grid runs (5x / 0.33x the steps per session), 3 seeds, +/-0.05 threshold runs, LEGACY +5/+10 min delay runs, H2 placebo (10,000 draws), power simulations, 5.13 refits.", "",
      "## Pilot sanity numbers (fixed sets, not selected; development evidence only, not results)", "",
      "| Family | variant | threshold chosen on validation nulls | val null FA rate | val hit rate | test FA | test hit rate | val mean QLIKE |", "|---|---|---|---|---|---|---|---|"]
for fam in ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"):
    for v in ("base", "f3"):
        s = r["splice"][fam][v]; q = r["qlike"][fam][v]
        L.append(f"| {fam} | {v} | {s['threshold']} | {s['val_null_fa']} | {s['val_hit_rate']} | {s.get('test_fa')} | {s.get('test_hit_rate')} | {q['mean_qlike_val']:.4f} |")
L += ["", "- `None` = no grid threshold met at most 1 false alarm per 20 validation null sessions. Diagnostic (`diag_pilot_fa.py`, Gaussian HMM, validation nulls): false-alarm rate by threshold for base " + ", ".join(f"{k}:{v:.2f}" for k, v in dg['base']['fa_by_thr'].items() if float(k) >= 0.9) + "; for f3 " + ", ".join(f"{k}:{v:.2f}" for k, v in dg['f3']['fa_by_thr'].items() if float(k) >= 0.9) + f". T_d at threshold 0.99 for f3 relative to the seam bar g (slots): {dg['f3']['T_d_slot_minus_g_at_0_99']} (4 of 5 occur before the seam).",
      f"- Abstention / skip shares (validation, share of grid bars / of used bars): base {r['shares']['base']['val']['abstained_share']:.4f} / {r['shares']['base']['val']['skip_share_after_start']:.4f}; f3 {r['shares']['f3']['val']['abstained_share']:.4f} / {r['shares']['f3']['val']['skip_share_after_start']:.4f}; f6 {r['shares']['f6']['val']['abstained_share']:.4f} / {r['shares']['f6']['val']['skip_share_after_start']:.4f}.",
      f"- Prep (inner train only), 20 inputs: " + ", ".join(f"{k}={sum(1 for x in r['prep'].values() if x == k)}" for k in ("log", "raw")) + "; dropped 0. Student-t Lee-Mykland threshold on inner train: " + f"{r['lm_t']['threshold']:.4f} (df {r['lm_t']['df']:.2f}, scale {r['lm_t']['scale']:.3f}, n {r['lm_t']['n']}) vs 4.6113 Gaussian; used only for the sensitivity-only flag.",
      "- Checkpointing: second and later pilot passes loaded cached fits/splices (hits 98, misses 17 in the last pass); no recomputation of finished units.", "",
      "## Protocol problems found", "",
      "1. 5.2 'sensitivity 83' vs 'jump_variation__sadj dropped': the 83 kept in matrix v2 include jump_variation_15/30/60__sadj; after the drop the set is 80. Assertions enforce 80.",
      "2. 5.1 embargo placement is not specified. A4 gives inner train 189 / validation 63 / outer 126 (RAW fold 3: 75). Here the first 5 sessions of validation and of test are removed (fold 3: 189 / 58 / 70). The outer block is also the 'test' segment; no separate embargo precedes inner train.",
      "3. 5.5 'T_c: 3 consecutive real updates hold': whether T_d counts as one is not stated; chosen: T_c is the third real update after T_d.",
      "4. 5.5 BOCPD 'no new alarm over those 3' is undefined while P(changepoint within 3 updates) stays high for 3 updates after a true change; chosen: alarm = rising edge of P >= threshold. Consequence: a transient outlier (P drops next update) is also confirmed; the rule has no persistence requirement for BOCPD.",
      "5. 5.3 'no alarms on the first 2 updates': for BOCPD P(run length <= 2) equals 1 at updates 1-2 and about 1-(1-1/lambda)^3 at update 3 (22% at lambda 12), so the first-2-updates rule is necessary and sufficient only with the rising-edge definition.",
      "6. 5.5 refractory start and state baseline are not specified; chosen: refractory starts at T_c; the current state is the argmax at updates 1-2 and after each T_c; a cancelled candidate has no refractory.",
      "7. 5.6 threshold rule is infeasible with a grid capped at 0.99 for the f3 models (validation null false-alarm rate 0.21 at 0.99 for the Gaussian HMM; most false alarms are far from the seam, i.e. ordinary state switching, not splice artefacts). Return-only baselines meet the rule only at 0.99 (HMM, HSMM) or 0.70 (BOCPD). The grid needs an upper extension or a different criterion; this changes which model families can be scored.",
      "8. 5.6 hit rates are very low in the pilot (validation 0-8% for baselines at the chosen threshold), so 'median delay' is undefined for most folds unless misses are censored. No censoring rule is given; the pilot reports hit rate and delays of hits separately.",
      "9. 5.6 'calm' / 'stressed' and 'volume tercile' are undefined; chosen: session realized variance and session volume terciles within the fold segment (validation for calibration, test for scoring); calm = lowest, stressed = highest; full 390-bar sessions with >= 98% finite closes only (early closes and gap sessions are excluded from splices).",
      "10. 5.6 QLIKE for BOCPD: 'regime-conditional forecast' has no regimes; chosen: two regimes weighted by P(changepoint within 3), with inner-train regime means of the next-60-min variance. HMM/HSMM use filtered-state-weighted inner-train means. BOCPD QLIKE is 0.51 vs 0.34-0.38 for the state models (pilot).",
      "11. 5.8 objective compares validation QLIKE across feature sets whose start bars differ (abstention f3 1.3%, f6 3.9% of grid bars); the protocol does not say whether to compare on common bars. The pilot DM uses common bars only.",
      "12. 5.2 'log only if strictly positive' does not say which features are log candidates. Chosen: every input except the 5-min return, return_1m, momentum*, close_location* (signed or bounded). Out-of-sample non-positive values of a logged feature become missing (skipped update).",
      "13. 5.1 'Amihud normalization' has no object in the primary 19 (no Amihud column); implemented as division by the inner-train median for the sensitivity set and tested on synthetic data only.",
      "14. 5.3 the 5-min return at the first decision bar (stamped minute 4) has no prior close; chosen: log(close / session open).",
      "15. 5.4 HSMM details unspecified: hazard parameterization with a smoothing prior (0.5 pseudo-count toward the overall hazard), duration cap 78 for all sessions, Gaussian emissions; Student-t HMM uses one hidden scale per observation (multivariate t, diagonal scale); Normal-Gamma prior mu0 0, kappa0 1, alpha0 1, beta0 1 on standardized inputs.",
      "16. 5.6 splice B may come from the 20 sessions before A (inside A's baseline history) or from later sessions; the features use only the spliced series and A's past history in either case; the pilot integrity test excludes the first case because B's edits then legitimately move A's baselines.",
      "17. 5.8 budget: splice-feature recomputation, not model fitting, dominates (see projection); the protocol's 'pilot budget' is therefore a function of the splice count and the 21-session recomputation window.", "",
      "## Choices made without asking (user away)", "",
      "- All items 3, 4, 6, 9, 10, 12, 14, 15 above were decided by the pipeline author as the most reasonable reading and are listed so they can be amended.",
      "- Pilot set: f3/f6 chosen a priori for timing; they are not selection outputs and must not be read as such.",
      "- Splice sizes in the pilot (24 + 24 per segment) were chosen for runtime; test splices were scored once per model at the validation-chosen threshold (fold-3 test segment is TRAIN-partition development data).",
      "- Threshold grids: states 0.50-0.95 step 0.05 plus 0.99; BOCPD 0.05-0.95 step 0.05 plus 0.99.",
      "- QLIKE target floor 1e-10; target needs >= 50 valid minute bars of the next 60; DM uses Newey-West lag 12.",
      "- The protocol file was committed before any Section 5 code was run; no amendments were made to it.", "",
      "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_lib.py", "s5_models.py", "s5_events.py", "s5_eval.py", "s5_tests.py", "s5_pilot.py", "diag_pilot_fa.py", "write_protocol.py", "write_pilot_report.py"):
    L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("pilot_results.json", "unit_tests.json", "diag_pilot_fa.json"):
    L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8"))
OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.read_text(encoding="utf-8")[:6000])
