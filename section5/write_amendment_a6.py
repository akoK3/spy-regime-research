#!/usr/bin/env python3
"""Writes AMENDMENT_A6.md (+ sidecar). Verifies every cited hash before writing (sidecars, the hash tables inside the D2-D5 reports, the feature ledger count). Refuses to overwrite."""
import hashlib, re, datetime, json
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; R4 = ROOT / "section431_step3_all_in_one_results"
OUT = ROOT / "AMENDMENT_A6.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
notes = []


def verify_report(name, results):
    rp = ROOT / name; side = rp.with_suffix(".sha256").read_text().split()[0]
    assert side == sha(rp), f"{name}: sidecar does not match the file"
    txt = rp.read_text(encoding="utf-8"); listed = dict(re.findall(r"\| (section5/[^|]+?) \| `([0-9a-f]{64})` \|", txt))
    for f in results:
        key = f"section5/results/{f}"; assert key in listed, f"{name}: {key} not listed"
        assert listed[key] == sha(HERE.parent / key), f"{name}: {key} differs from the hash listed in the report"
    changed = [k for k, v in listed.items() if k.endswith(".py") and sha(ROOT / k) != v]
    notes.append((name, sha(rp), changed))
    return sha(rp)


cited = {}
cited["D2_REPORT.md"] = verify_report("D2_REPORT.md", ["d2_stable_days.json", "d2_results.json"])
cited["D3_REPORT.md"] = verify_report("D3_REPORT.md", ["d3_synth_results.json", "d3_results.json"])
cited["D4_REPORT.md"] = verify_report("D4_REPORT.md", ["d4_results.json", "d4_run1_as_first_executed.json"])
cited["D5_REPORT.md"] = verify_report("D5_REPORT.md", ["d5a_results.json", "d5b_results.json", "d5c_results.json"])
for name in ("PILOT_REPORT.md", "PILOT_REPORT_2.md", "AMENDMENT_A6_DRAFT.md", "SECTION5_PROTOCOL.md"):
    assert (ROOT / name).with_suffix(".sha256").read_text().split()[0] == sha(ROOT / name), name; cited[name] = sha(ROOT / name)
m = pd.read_csv(R4 / "a4_sec4_3_9_frozen_matrix_v2.csv"); sens = m.loc[m.sensitivity_outcome == "kept", "column"].tolist()
jv = [c for c in sens if c.startswith("jump_variation") and c.endswith("__sadj")]
assert len(sens) == 83 and jv == ["jump_variation_15__sadj", "jump_variation_30__sadj", "jump_variation_60__sadj"] and len(sens) - len(jv) == 80
ledger = (ROOT / "METHODS_LEDGER.md").read_text(encoding="utf-8"); assert "keep 83 / drop 30" in ledger and "jump_variation_15/30/60__sadj" in ledger
assert (ROOT / "METHODS_LEDGER.sha256").read_text().split()[0] == sha(ROOT / "METHODS_LEDGER.md")
now = datetime.datetime.now(datetime.timezone.utc); ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
L = ["# Amendment A6 to SECTION5_PROTOCOL.md", "", f"Dated {now.isoformat()} UTC ({ny} New York). Status: ADOPTED when committed with its hash sidecar; governs the Section 5 machinery pilot that follows and later Section 5 runs.",
     "Supersedes `AMENDMENT_A6_DRAFT.md`, which stays on record unchanged. Written before the machinery pilot it governs. Facts only.", "",
     "## Evidence cited (hashes recomputed and compared to the sidecars and to the hash tables inside each report before this file was written)", "", "| Document | SHA-256 |", "|---|---|"]
L += [f"| `{k}` | `{v}` |" for k, v in cited.items()]
L += ["", "Results files hashed inside the reports and found equal to the files on disk: D2 `d2_stable_days.json`, `d2_results.json`; D3 `d3_synth_results.json`, `d3_results.json`; D4 `d4_results.json`, `d4_run1_as_first_executed.json`; D5 `d5a_results.json`, `d5b_results.json`, `d5c_results.json` (hashes in each report's Files table).",
      "Code hashes in the reports are hashes at report time; later edits of `s5_events.py`, `s5_models.py`, `s5_eval.py`, `s5_tests.py` changed their hashes. Files whose current hash differs from the one printed in the report: " + "; ".join(f"{n}: {', '.join(c) if c else 'none'}" for n, _, c in notes) + ".", "",
      "## Changes", "",
      "1. **Event rule for HMM and HSMM (replaces the single-new-state T_d/T_c of 5.5 for these two families).** Old state = argmax at updates 1-2 and at each alarm. Alarm (= confirmed event, T_c) when P(old state) < 1 - threshold for 3 consecutive real updates; T_d = the first of the three; a skipped update resets the count to 0; the first 2 updates are silent; 30-min refractory after an alarm. Evidence: D3 test 1 (the single-new-state rule cannot confirm when a regime is split over states: calm-to-stressed hit 0.01 vs 0.90), D4 (pass mark met by Gaussian HMM K=2,3, Student-t HMM K=2,3,4 and HSMM K=2,3,4 on Gaussian noise; Student-t HMM K=4 and HSMM K=2 on Student-t df 5 noise). Code: `detect_old_state` in `s5_events.py`.",
      "2. **H1(a) is a hit-rate versus alarm-rate curve on stable-day splices, from each fold's test sessions.** Stable days: the D2 definition (item 6) applied to the fold's test sessions; a fold with fewer than 8 stable test days is reported as not evaluable. Splices: the D2 design: variance ratios 1.5, 2, 3, 5, 10 (VARIANCE ratios), both directions, permanent and 30/60/120-min sandwiches, 24 splices per cell, 400 null splices of two distinct stable days of the same volatility tercile, tau on the 11:05-14:30 grid (<= 14:00 for sandwiches). Curve: for every threshold of the grid, x = confirmed alarms per null session, y = share of break splices with a confirmed alarm within 60 min after tau; y(x) = the highest y reached at alarm rate <= x. Metric = partial area under y(x) for x in [0, 0.5], divided by 0.5 (range 0-1). Power is reported by variance ratio (pooled over directions and durations) as the partial area and as the hit rate at x = 0.1. The fold-level comparison is feature model minus baseline in partial area, aggregated as in 5.9. This is a sensitivity measure under simulated conditions on real stable days, not real-world detection accuracy. The median-delay formulation of H1(a) in 5.0 is replaced by this metric (D2, D4: hit rates at the 1-per-20 false-alarm target are 0.00-0.11 on the pilot fold, and median delay is undefined when hits are below 50%).",
      "3. **Section 6 event thresholds** are calibrated on the REAL validation sessions of each fold (native sessions, no splices) so that the detector gives 1 confirmed alarm per 5 sessions (0.2 per session): among grid thresholds with a validation alarm rate <= 0.2, the one with the highest rate (ties to the stricter threshold); if none qualifies the strictest grid value is used and the fold is flagged. The realized alarm frequency on the fold's test sessions is reported next to the target. Evidence: D5 part C (thresholds calibrated on synthetic data give 0.15-1.00 real false-alarm shares on stable days).",
      "4. **BOCPD is secondary.** Alarm = the run-length-drop alarm (the most likely run length falls by at least m updates and then holds 3 updates, `detect_bocpd_map`); m chosen by the D4 run-2 rule (item 6). BOCPD is outside H1 and outside its Holm family: Holm in 5.11 runs across 3 families (Gaussian HMM, Student-t HMM, HSMM) for H1, and across 4 assets for H2 as before. Limitation, for the tested specification only (Normal-Gamma prior mu0 0, kappa0 1, alpha0 1, beta0 1 on standardized inputs; lambda 12/39/78; run length truncated at 200; priors scaled to calm or stressed train variance; K/lambda not selected): the changepoint-probability alarms (P(run length <= 2), P(run length < 6)) respond to variance increases and not to decreases (down-hit 0.00-0.15); the implementation equals an independent Adams and MacKay reference to 1.7e-14 (D5 A); the evidence for a 10x variance increase is 3.35 nats per update and for a 10x decrease 0.70 nats; no claim is made for other BOCPD specifications.",
      "5. **Grids and baseline.** The 5-minute grid is primary. The 1-minute grid (390 updates) is a sensitivity analysis only; D5 B: no family reaches 50% hit at 3x variance ratio at FA <= 10% on either grid, 1-minute delays at 10x are shorter, HSMM filtering at 1 minute is about 66x slower. The baseline model = the deseasonalized 5-minute return alone: the 5-minute return divided by the median |5-minute return| of the same grid slot over the previous 20 sessions (>= 10 finite; NaN = skipped update; past sessions only). Every model (baseline and feature models) uses this deseasonalized return as its return input; the other inputs are unchanged. Evidence: D3 (return-only states track the clock, Cramer's V 0.19-0.25; feature inputs V <= 0.06; deseasonalizing the inputs changes feature-model false alarms and hits little).",
      "6. **Threshold rule, stable days, pool count.**",
      "   a. Threshold rule for alarms whose false-alarm rate is not monotone in the threshold (BOCPD alarms): among grid values with calibration-null session false-alarm share <= 0.10, the one with the highest calibration hit rate (mean of the up and down calibration breaks), ties to the smaller grid index; if none qualifies the strictest grid value is used and the cell is flagged INFEASIBLE (D4 run 2; D4 run 1, the smallest-threshold rule, selected a dead zone for P(run length <= 2) and P(run length < 6) and is recorded as a failure).",
      "   b. Stable-day definition (fixed before any detector runs; D2): full 390-bar session with >= 98% finite closes; deseasonalized 1-minute variance = r^2 divided by the median r^2 of the same slot over the previous 20 sessions (>= 10 finite); the mean over the first 195 bars and over the last 195 bars differ by a ratio second/first in [0.8, 1.25]; and no hourly block mean (blocks 0-60, ..., 300-360, 360-390 min) above 2 times the median block mean.",
      f"   c. Sensitivity pool = 80 columns, not 83: matrix v2 (`a4_sec4_3_9_frozen_matrix_v2.csv`, sha256 `{sha(R4 / 'a4_sec4_3_9_frozen_matrix_v2.csv')}`) keeps 83 columns on the RAW sensitivity outcome, including jump_variation_15__sadj, jump_variation_30__sadj and jump_variation_60__sadj; 5.2 drops jump_variation__sadj; 83 - 3 = 80. Verified against the matrix and against `METHODS_LEDGER.md` (sha256 `{sha(ROOT / 'METHODS_LEDGER.md')}`; entry 'keep 83 / drop 30' with jump_variation_15/30/60__sadj).",
      "", "## Not changed", "",
      "5.1 folds and embargo placement, 5.2 pools and exclusions (other than the count above), 5.3 decision bars except the grid roles, 5.4 model fits, 5.6 splice construction except the H1(a) metric, 5.8 selection, 5.12 and 5.13. The primary pool remains 19 columns. No threshold, grid or rule in this amendment was chosen from pilot performance.", "",
      "## Governs", "", "The machinery pilot that follows this amendment (causal timing, exclusions, threshold calibration and synthetic scoring on RAW fold 3 with fixed a-priori feature sets): no evaluation-period access, no selection, no protocol change based on the pilot's performance."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.with_suffix(".sha256").read_text()); print(notes)
