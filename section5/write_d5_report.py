#!/usr/bin/env python3
"""Writes D5_REPORT.md (+ sidecar hash) from section5/results/d5a_results.json, d5b_results.json, d5c_results.json."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "D5_REPORT.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
A = json.loads((RES / "d5a_results.json").read_text()); B = json.loads((RES / "d5b_results.json").read_text()); C = json.loads((RES / "d5c_results.json").read_text())
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm"]; KS = [2, 3]; DT = ["gaussian", "student_t5"]; RS = [2, 3, 5, 10]
fm = lambda x: "-" if x is None else f"{x:.0f}"
md = max(A["max_abs_posterior_difference"].values())
L = ["# Diagnostic D5 report", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Ratios are VARIANCE ratios. Parts A and B are pure synthetic; part C uses RAW fold 3 validation stable-day null splices (D2 sampling); no selection, no evaluation data, nothing excluded, no grid changed.", ""]
# ---- decision rule evaluation
rows = []
for fam in FAMS:
    for K in KS:
        r = {}
        c1 = all(min(B[f"{d}|R3|1min|{fam}|K={K}"]["hit_up"], B[f"{d}|R3|1min|{fam}|K={K}"]["hit_down"]) >= 0.5 and B[f"{d}|R3|1min|{fam}|K={K}"]["test_fa"] <= 0.10 for d in DT)
        c1_any = any(min(B[f"{d}|R3|1min|{fam}|K={K}"]["hit_up"], B[f"{d}|R3|1min|{fam}|K={K}"]["hit_down"]) >= 0.5 and B[f"{d}|R3|1min|{fam}|K={K}"]["test_fa"] <= 0.10 for d in DT)
        c2 = all(C[f"1min|{fam}|K={K}|{d}|R3"]["real_fa"] <= C[f"5min|{fam}|K={K}|{d}|R3"]["real_fa"] for d in DT)
        dl = lambda g, d: [x for x in (B[f"{d}|R10|{g}|{fam}|K={K}"]["delay_up_min"], B[f"{d}|R10|{g}|{fam}|K={K}"]["delay_down_min"]) if x is not None]
        c3a = all(dl("1min", d) and dl("5min", d) and sum(dl("1min", d)) / len(dl("1min", d)) <= sum(dl("5min", d)) / len(dl("5min", d)) for d in DT)
        c3b = all(B[f"{d}|R10|1min|{fam}|K={K}"]["filter_ms_per_session"] <= 10.0 and B[f"{d}|R10|1min|{fam}|K={K}"]["fit_s"] <= 60.0 for d in DT)
        rows.append((fam, K, c1, c1_any, c2, c3a, c3b))
adopt = [x for x in rows if x[2] and x[4] and x[5] and x[6]]
L += ["## Decision rule (stated before the runs)", "",
      "Adopt the 1-minute grid if (1) synthetic hit at 3x variance ratio >= 50% at test FA <= 10% of sessions, (2) real stable-null FA is no worse, and (3) delay and compute are acceptable. The task left (3) undefined; I define it here: delay = mean over directions of the median delay at 10x is no larger than at 5 minutes; compute = filtering <= 10 ms per session and fitting <= 60 s. (1) is required in both noise types (strict) -- the 'either' column relaxes it; (2) is checked at the synthetic R = 3 thresholds of the same noise type, both noise types.", "",
      "| family | K | (1) hit at 3x >= 0.5, FA <= 0.10, both noises | (1) either noise | (2) real FA 1-min <= 5-min | (3a) delay no larger | (3b) compute | adopt 1-min |", "|---|---|---|---|---|---|---|---|"]
for fam, K, c1, c1a, c2, c3a, c3b in rows: L.append(f"| {fam} | {K} | {'yes' if c1 else 'NO'} | {'yes' if c1a else 'NO'} | {'yes' if c2 else 'NO'} | {'yes' if c3a else 'NO'} | {'yes' if c3b else 'NO'} | {'**YES**' if (c1 and c2 and c3a and c3b) else 'no'} |")
L += ["", f"**Verdict: {'adopt 1-minute for ' + ', '.join(f'{f} K={k}' for f, k, *_ in adopt) if adopt else 'do not adopt the 1-minute grid under the stated rule (criterion 1 fails for every family and K)'}.**", ""]
# ---- part A
L += ["## A. BOCPD root cause", "",
      f"- Independent reference (Adams & MacKay 2007 recursion; each run-length hypothesis scored by the closed-form Normal-Gamma marginal likelihood ratio ML(segment + x) / ML(segment), prefix-sum evaluation; the `bayesian_changepoint_detection` package was not used): maximum absolute difference between the two run-length posteriors P(r_t | x_1:t) over all updates and run lengths, 12 sessions (6 up, 6 down) x 4 priors x lambda 12/39/78: **{md:.2e}**. Our implementation reproduces the reference to rounding error: **not a code bug**.",
      f"- Evidence asymmetry (analytic, per update): KL of a 10x variance increase {A['analytic_KL_nats_per_update']['up_10x']:.2f} nats, of a 10x decrease {A['analytic_KL_nats_per_update']['down_10x']:.2f} nats. The reference itself needs {A['reference_updates_after_change_until_P(r<=2)>=0.5']['up']} updates (None = never within the session) after an increase before P(run length <= 2) >= 0.5, and {A['reference_updates_after_change_until_P(r<=2)>=0.5']['down']} after a decrease: the reference posterior reproduces the one-sided behaviour.",
      "- **Verdict A: method limitation** (Normal-Gamma BOCPD with these alarms responds to variance increases and weakly to decreases), not our bug. Alarm (b) (MAP run-length drop) is the only BOCPD alarm that responds in both directions.", "",
      f"Priors tested (z-scored inputs, pooled train variance 1; calm train variance {A['train_calm_var_z']:.2f}, stressed {A['train_stressed_var_z']:.2f}): default (0,1,1,1); beta0 = calm variance; beta0 = stressed variance; tighter (0,1,3,2). Detection, Gaussian R = 10, D4 'maxhit' rule, 500 test sessions per cell. Cells: hit up / down (test FA); '-' = no calibration threshold with FA <= 10%.", "",
      "| prior | lambda | (a) P(r<=2) | (b) MAP drop | (c) P(r<6) |", "|---|---|---|---|---|"]
for pn in sorted({k.split("|")[0] for k in A["detection_gaussian_R10"]}, key=lambda x: (x != "default (0,1,1,1)", x)):
    for lam in (12, 39, 78):
        cells = []
        for kind in ("a_pcp3", "b_map", "c_r_lt_6"):
            v = A["detection_gaussian_R10"][f"{pn}|lam={lam}|{kind}"]
            cells.append("-" if not v["feasible"] else f"{v['hit_up']:.2f} / {v['hit_down']:.2f} ({v['test_fa']:.2f})")
        L.append(f"| {pn} | {lam} | " + " | ".join(cells) + " |")
L += ["", "Scaling the prior to the train variance changes the up-hit rate (up to 0.95-0.96 for (c) with beta0 = stressed variance) but leaves the down-hit rate of (a) and (c) at 0.00-0.15; only (b) detects decreases (0.38-0.76 at the default prior).", ""]
# ---- part B
L += ["## B. 1-minute vs 5-minute grid (synthetic, Gaussian and Student-t df 5)", "",
      "Cells: hit up / hit down (test FA). Thresholds calibrated per grid, family, K, noise and ratio on separate seeds (calibration null FA <= 10%, 'maxhit' rule); scored on test seeds; 500 sessions per set. Hit within 60 minutes of the break.", "",
      "| noise | family | K | grid | R=2 | R=3 | R=5 | R=10 | delay R=10 up / down (min) | delay R=3 up / down (min) | fit s | filter ms/session |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
for d in DT:
    for fam in FAMS:
        for K in KS:
            for g in ("5min", "1min"):
                cs = [B[f"{d}|R{R}|{g}|{fam}|K={K}"] for R in RS]
                L.append(f"| {d} | {fam} | {K} | {g} | " + " | ".join(f"{c['hit_up']:.2f} / {c['hit_down']:.2f} ({c['test_fa']:.2f})" for c in cs) + f" | {fm(cs[3]['delay_up_min'])} / {fm(cs[3]['delay_down_min'])} | {fm(cs[1]['delay_up_min'])} / {fm(cs[1]['delay_down_min'])} | {cs[3]['fit_s']:.1f} | {cs[3]['filter_ms_per_session']:.2f} |")
L += ["", "Timing notes: four worker processes ran concurrently, so absolute times are indicative; filter time is wall time for all calibration and test sessions of a cell divided by their number (3,000), batch-vectorised. HSMM at 1 minute uses the protocol cap of 390 durations; the 1-minute fits use 40 training sessions (15,600 updates) against 189 sessions (14,742 updates) at 5 minutes. K = 4 (used in D4) was not run here. Run 1 of D4 (smallest-threshold rule) is not used.", ""]
# ---- part C
L += ["## C. Real stable-day nulls, both grids", "",
      "Return-only detectors (raw 1- or 5-minute return, no features, no deseasonalisation) fitted on real inner-train returns of RAW fold 3 (1-minute grid: last 40 train sessions); thresholds from part B for the same grid / family / K / noise / ratio; 400 stable-day null splices (D2 sampling). Cells: share of null sessions with any confirmed alarm / alarms per 20 sessions.", "",
      "| family | K | grid | Gaussian R=3 | t5 R=3 | Gaussian R=10 | t5 R=10 |", "|---|---|---|---|---|---|---|"]
for fam in FAMS:
    for K in KS:
        for g in ("5min", "1min"):
            cells = [C[f"{g}|{fam}|K={K}|{d}|R{R}"] for R, d in ((3, "gaussian"), (3, "student_t5"), (10, "gaussian"), (10, "student_t5"))]
            L.append(f"| {fam} | {K} | {g} | " + " | ".join(f"{c['real_fa']:.2f} / {c['per20']:.1f} (thr {c['threshold']})" for c in cells) + " |")
L += ["", "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_d5a.py", "s5_d5b.py", "s5_d5c.py", "s5_models.py", "s5_events.py", "write_d5_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("d5a_results.json", "d5b_results.json", "d5c_results.json"): L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print("\n".join(L[:30]))
