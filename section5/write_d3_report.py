#!/usr/bin/env python3
"""Writes D3_REPORT.md (+ sidecar hash) from section5/results/d3_synth_results.json and d3_results.json (and d2_results.json for the reproducibility check)."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "D3_REPORT.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
sy = json.loads((RES / "d3_synth_results.json").read_text()); r = json.loads((RES / "d3_results.json").read_text()); d2 = json.loads((RES / "d2_results.json").read_text())
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = ["base", "f3", "f6"]; BINS = ["09:30", "10", "11", "12", "13", "14", "15"]
SIZES = [1.5, 2, 3, 5, 10]


def pooled(h, f):
    n = c = 0
    for k, v in h.items():
        R, dr, du = k.split("|")
        if f(float(R), dr, du): n += v["n"]; c += v["n_hits"]
    return c / n if n else float("nan")


perm = lambda R, dr, du: du == "None"
perm3 = lambda R, dr, du: du == "None" and R >= 3
L = ["# Diagnostic D3 report", "", "**RAW fold 3, validation sessions only (test 1 uses synthetic data only); frozen pilot detectors (K=3, lambda=39, 1 start, seed 0), fixed a-priori feature sets; no selection; no evaluation data.**", "",
     f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC.", "", "## Verdicts", "",
     "1. **Implementation sanity: FAIL under the protocol event rule; not an implementation bug in the models.** On synthetic iid Gaussian data with a 10x variance jump no family reaches FA <= 0.05 with hit >= 0.9 in both directions. The Gaussian HMM, Student-t HMM and HSMM catch stressed-to-calm (0.86-0.94 at threshold 0.5) but not calm-to-stressed (0.34-0.41 at 0.5, 0.00-0.03 at >= 0.9). Cause found: with K=3 the 2-regime data splits the stressed regime over two states (fitted variances 0.99 / 6.0 / 6.6) and the protocol rule needs ONE new state to win for 3 updates; with K=2 (variances 0.99 / 10.2) or the mass rule the jump is caught (up 0.90-0.92 at 0.9, FA 0.04-0.06). Filtering, EM and the unit tests are consistent with this; the defect is the state-identity requirement in 5.5. BOCPD also fails: no threshold gives FA <= 0.05 with both hits >= 0.9 (0.5: FA 0.06, up 0.59, down 0.00).",
     "2. **Seasonality: CONFIRMED for return-only inputs, ABSENT for feature inputs.** Return-only HMM/HSMM states track the clock (Cramer's V 0.19-0.25, medium; the highest-variance state holds 26-36% of first-hour bars vs 9-13% mid-day). With f3/f6 inputs V <= 0.06 (negligible). Deseasonalising the return cuts the return-only V to 0.04-0.11.",
     "3. **Seasonality fix: NO material change.** Stable-null false alarms and permanent-break hit rates are essentially unchanged for f3/f6 (e.g. Gaussian f3 at 0.99: FA 5.1 -> 5.1, hit 0.28 -> 0.26; HSMM f3: 6.8 -> 6.5, 0.26 -> 0.28). Only the Student-t f6 false alarms fall (5.2 -> 2.7 at 0.99, hit unchanged), and return-only hits stay <= 0.10. Seasonality is not the cause of the low hit rates or the false alarms. The raw mode reproduces D2 exactly.",
     "4. **BOCPD: no usable contrast between null and break.** The changepoint probability is nearly the same on null and break splices (f3 pooled 99th percentile 0.71 null vs 0.90 break; base 0.29 vs 0.32-0.37; session maxima on null days reach 0.72 median for f3 and 0.97 for f6). At thresholds 0.05-0.5 the stable-null false-alarm rate is 15-20 per 20 for f3/f6 (return-only: 16-20 at 0.05-0.1, 0.2 at 0.5) while hit rates are 0.31-0.78; below 0.05 nothing fires. No threshold gives FA <= 1 per 20 with hit above ~0.04 (return-only 0.5: 0.2 / 0.04). Hyperparameters are listed under test 4.",
     "5. **Extra finding (not requested): the protocol event rule itself lowers hit rates.** The mass rule raises permanent-break hit rates for R>=3 (Gaussian f3 at 0.99: 0.38 -> 0.51, up-direction 0.47 -> 0.68) but also raises stable-null false alarms (5.1 -> 10.5 per 20), so the false-alarm trade-off is not removed by changing the rule.", ""]
# ---------- test 1
V1 = {k: v for k, v in sy.items() if k != "verdict"}
L += ["## Test 1: implementation sanity (synthetic iid Gaussian, 10x variance jump at update 36 of 78)", "",
      "Cells: null false-alarm rate / hit up (calm to stressed) / hit down (stressed to calm), hit = T_c within 60 min of the jump; 200 sessions each; training set = 189 regime-mixture sessions; protocol event rule ('state').", "",
      "| model | D | 0.5 | 0.9 | 0.99 | 0.999 | best (FA<=0.05, both hits>=0.9) |", "|---|---|---|---|---|---|---|"]
for fam in FAMS:
    for D in (1, 4):
        res = sy[f"{fam}|D={D}"]; g = lambda t: f"{res[t]['fa']:.2f}/{res[t]['up']['hit']:.2f}/{res[t]['down']['hit']:.2f}" if t in res else "-"
        L.append(f"| {fam} | {D} | {g('0.5')} | {g('0.9')} | {g('0.99')} | {g('0.999')} | {sy['verdict'][f'{fam}|D={D}']['smallest_passing_threshold']} |")
L += ["", "BOCPD low thresholds (D=1): " + ", ".join(f"{t}: {v['fa']:.2f}/{v['up']['hit']:.2f}/{v['down']['hit']:.2f}" for t, v in sy["bocpd|D=1"].items() if float(t) <= 0.5) + ".", "",
      "Probe (not saved as a script; run inline during the session): Gaussian HMM, D=1, same data generator, 200 sessions each. K=2 recovers variances 0.99 and 10.21. K=3 fits variances 0.99 / 6.02 / 6.63, i.e. the stressed regime is split over two states. Protocol 'state' rule (one new state must win for 3 updates): K=2 at 0.9: FA 0.06, up 0.92, down 0.61; K=3 at 0.9: FA 0.04, up 0.01, down 0.51. Mass rule (1 - P[baseline state] >= thr for 3 updates; `s5_events.detect_states_mass`): K=3 at 0.9: FA 0.04, up 0.90, down 0.85.", ""]
# ---------- test 2
L += ["## Test 2: state occupancy by time of day (train sessions, filtered argmax; Cramer's V of state x clock bin, 7 bins; df* = 2: V 0.07 small, 0.21 medium, 0.35 large)", "",
      "| model | set | V raw | V deseasonalised | NMI raw | NMI des | share of the highest-variance state by bin (raw): 09:30 / 10 / 11 / 12 / 13 / 14 / 15 |", "|---|---|---|---|---|---|---|"]
for fam in FAMS[:3]:
    for s in SETS:
        a, b = r["raw"]["occupancy"][f"{fam}|{s}"], r["des"]["occupancy"][f"{fam}|{s}"]; top = int(max(range(len(a["state_var_ret"])), key=lambda i: a["state_var_ret"][i]))
        L.append(f"| {fam} | {s} | {a['cramers_v']:.2f} | {b['cramers_v']:.2f} | {a['nmi']:.3f} | {b['nmi']:.3f} | " + " / ".join(f"{x:.2f}" for x in a["share_by_bin"][top]) + " |")
L += [""]
# ---------- test 3
L += ["## Test 3: D2 vs D3 (all inputs deseasonalised), side by side", "",
      "Stable-null false alarms per 20 sessions (95% CI) and pooled hit rates over D2 breaks (permanent; all sizes / R>=3; both directions). Rule 'state' = protocol; 'mass' = diagnostic alternative (HMM/HSMM only). 'D2' columns are from this run's raw mode (identical splices to `d2_results.json`; reproducibility check below).", "",
      "| detector | set | rule | thr | FA D2 | FA D3 | hit perm D2 (all / R>=3) | hit perm D3 (all / R>=3) | D3 up R>=3 | D3 down R>=3 |", "|---|---|---|---|---|---|---|---|---|---|"]
for fam in FAMS:
    for s in SETS:
        for rule in (("state", "mass") if fam != "bocpd" else ("state",)):
            for t in (0.99, 0.999):
                k = f"{fam}|{s}|{rule}|{t}"; a, b = r["raw"], r["des"]
                fa_ = lambda o: f"{o['fa'][k]['per20']:.1f} [{o['fa'][k]['ci95_per20'][0]:.1f}-{o['fa'][k]['ci95_per20'][1]:.1f}]"
                hp = lambda o: f"{pooled(o['hit'][k], perm):.2f} / {pooled(o['hit'][k], perm3):.2f}"
                up3 = pooled(b["hit"][k], lambda R, dr, du: du == "None" and R >= 3 and dr == "up"); dn3 = pooled(b["hit"][k], lambda R, dr, du: du == "None" and R >= 3 and dr == "down")
                L.append(f"| {fam} | {s} | {rule} | {t} | {fa_(a)} | {fa_(b)} | {hp(a)} | {hp(b)} | {up3:.2f} | {dn3:.2f} |")
mism = [k for k in d2["fa"] if "|" in k and k.split("|")[2] in ("0.99", "0.999") and f"{k.split('|')[0]}|{k.split('|')[1]}|state|{k.split('|')[2]}" in r["raw"]["fa"] and abs(d2["fa"][k]["stable_null"]["per20"] - r["raw"]["fa"][f"{k.split('|')[0]}|{k.split('|')[1]}|state|{k.split('|')[2]}"]["per20"]) > 1e-9]
L += ["", f"Reproducibility: raw-mode stable-null false-alarm rates equal D2's for all {len([k for k in d2['fa'] if k.split('|')[2] in ('0.99','0.999')])} detector/threshold cells checked" + ("." if not mism else f"; MISMATCH in {mism[:5]}."), ""]
# ---------- test 4
L += ["## Test 4: BOCPD", "",
      "Hyperparameters: independent Normal-Gamma per input dimension (Student-t predictive), prior mu0 = 0, kappa0 = 1, alpha0 = 1, beta0 = 1 on inputs standardised with inner-train statistics; constant hazard 1/lambda with lambda = 39 (12 and 78 in the protocol grid, not used here); run length truncated at 200 (mass beyond is merged into the last bucket); statistic = P(run length <= 2) = P(changepoint within the last 3 updates); alarm = rising edge of the statistic >= threshold at update >= 3; hold 3 real updates without a new alarm; skip = hazard-only step with statistics unchanged; first 2 updates silent (the statistic is 1.0 there by construction).", "",
      "Changepoint-probability quantiles (50 / 90 / 99 / 99.9%) at updates >= 3, raw inputs: null = stable-null splices (all update values; per-session maximum); breaks = permanent D2 breaks, updates within 60 min after tau.", "",
      "| set | null pooled | null session max | breaks pooled (all) | breaks session max (all) | breaks pooled (R>=3) | breaks session max (R>=3) |", "|---|---|---|---|---|---|---|"]
for s in SETS:
    p = r["raw"]["pcp"][s]; L.append(f"| {s} | {p['null_pooled_q50_90_99_999']} | {p['null_session_max_q50_90_99_999']} | {p['break_perm_window_pooled_all']} | {p['break_perm_window_session_max_all']} | {p['break_perm_window_pooled_R_ge_3']} | {p['break_perm_window_session_max_R_ge_3']} |")
L += ["", "Same, deseasonalised inputs:", "", "| set | null pooled | null session max | breaks pooled (all) | breaks session max (all) | breaks pooled (R>=3) | breaks session max (R>=3) |", "|---|---|---|---|---|---|---|"]
for s in SETS:
    p = r["des"]["pcp"][s]; L.append(f"| {s} | {p['null_pooled_q50_90_99_999']} | {p['null_session_max_q50_90_99_999']} | {p['break_perm_window_pooled_all']} | {p['break_perm_window_session_max_all']} | {p['break_perm_window_pooled_R_ge_3']} | {p['break_perm_window_session_max_R_ge_3']} |")
L += ["", "BOCPD thresholds 0.01-0.5 (stable null FA per 20 / hit perm all sizes / hit perm R>=3):", "", "| inputs | set | " + " | ".join(str(t) for t in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5)) + " |", "|---|---|" + "---|" * 7]
for mode in ("raw", "des"):
    for s in SETS:
        cells = []
        for t in (0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5):
            k = f"bocpd|{s}|state|{t}"; o = r[mode]; cells.append(f"{o['fa'][k]['per20']:.1f} / {pooled(o['hit'][k], perm):.2f} / {pooled(o['hit'][k], perm3):.2f}")
        L.append(f"| {mode} | {s} | " + " | ".join(cells) + " |")
L += ["", "## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_d3_synth.py", "s5_d3.py", "s5_events.py", "write_d3_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("d3_synth_results.json", "d3_results.json"): L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.read_text(encoding="utf-8")[:200])
