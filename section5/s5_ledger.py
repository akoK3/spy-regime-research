#!/usr/bin/env python3
"""Section 5 part of METHODS_LEDGER.md. `init` appends the part once (all Section 5 amendments, diagnostics, pilots and audit, with date, decision, reason, file, SHA-256); `add` appends one row
after any later step. Hashes are computed from the files; dates are the 'Dated/Written' stamp inside the file, else the last git commit time of the file. The Section 5 table is the last
thing in the ledger, so rows are appended at the end of the file. The ledger's own sidecar is rewritten after every change. Usage:
  s5_ledger.py init
  s5_ledger.py add FILE "KIND" "DECISION" "REASON"      (FILE relative to the repository root)"""
import sys, re, hashlib, subprocess, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent; LEDGER = ROOT / "METHODS_LEDGER.md"; SIDE = LEDGER.with_suffix(".sha256"); MARK = "## 5. Section 5 (detection and model evaluation)"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
HEAD = ["| Date (UTC) | Kind | Decision | Reason | File | SHA-256 |", "|---|---|---|---|---|---|"]


def date_of(f):
    t = (ROOT / f).read_text(encoding="utf-8", errors="ignore")[:3000] if f.endswith((".md", ".json")) else ""
    m = re.search(r"(?:Dated|Written|Generated|created_utc\"?:?)\s*\"?(\d{4}-\d\d-\d\dT[\d:.]+(?:[+-]\d\d:\d\d|Z)?)", t)
    if m: return datetime.datetime.fromisoformat(m.group(1).replace("Z", "+00:00")).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    o = subprocess.run(["git", "log", "-1", "--format=%aI", "--", f], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    return datetime.datetime.fromisoformat(o).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ") if o else datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


def row(f, kind, decision, reason):
    esc = lambda s: s.replace("|", "/").replace("\n", " ")
    return f"| {date_of(f)} | {kind} | {esc(decision)} | {esc(reason)} | {f} | `{sha(ROOT / f)}` |"


def finish():
    SIDE.write_text(f"{sha(LEDGER)}  {LEDGER.name}\n", encoding="ascii")


R = "section5/results/"
ROWS = [
    ("SECTION5_PROTOCOL.md", "Protocol", "Section 5 protocol 5.0-5.13 adopted as DRAFT pending pilot; changes by dated, hashed amendment only", "Governing document written before any Section 5 code ran; text supplied by the user, reproduced unchanged"),
    ("PILOT_REPORT.md", "Pilot", "Section 5 pipeline built; RAW fold 3 machinery pilot, no selection, no evaluation data", "Check pipeline, causal timing, isolation and run time before any scored run"),
    ("PILOT_REPORT_2.md", "Pilot", "False-alarm diagnosis, fix tests, parallel benchmark, re-projected budget; amendment A6 drafted, not applied", "Pilot 1 alarm behaviour needed diagnosis before an event rule could be fixed"),
    (R + "extreme_results.json", "Diagnostic", "Variance ratio at tau and extreme-decile splices (validation only)", "Check what the splice labels mean in variance terms"),
    (R + "cusum_results.json", "Diagnostic", "CUSUM sanity detector and alarm volatility ratio versus random times (validation only)", "Reference detector independent of the models"),
    ("D2_REPORT.md", "Diagnostic D2", "Stable-day null and variance-ratio breaks (sizes, directions, durations) beside the tercile test; stable-day rule introduced", "Null splices from different days carry natural shifts; breaks of known size needed"),
    ("D3_REPORT.md", "Diagnostic D3", "Synthetic sanity, seasonality, deseasonalised D2 rerun, BOCPD", "Separate model behaviour from data artefacts"),
    ("D4_REPORT.md", "Diagnostic D4", "Synthetic power study with the new HMM/HSMM rule and three BOCPD alarms", "Compare alarm rules on known breaks before adoption"),
    ("D5_REPORT.md", "Diagnostic D5", "BOCPD against an independent reference; 1-min versus 5-min grid (synthetic); real stable-day nulls", "Validate the BOCPD implementation and the grid choice"),
    ("AMENDMENT_A6_DRAFT.md", "Amendment A6 draft", "Draft of A6; not applied", "Proposed rules after pilot 2; superseded by A6, stays on record unchanged"),
    ("AMENDMENT_A6.md", "Amendment A6", "Adopted: event rule, H1(a) partial-area metric, Section 6 thresholds, BOCPD secondary, grids and baseline, stable days, pool = 80", "Pilot 2 and D2-D5 showed the median-delay metric and the old event rule did not fit; written before the A6 pilot"),
    ("PILOT_REPORT_A6.md", "Pilot", "Machinery pilot under A6 (RAW fold 3): exclusions, causal timing, threshold calibration, synthetic scoring", "Run A6 machinery end to end; its test-segment curves were scored (disclosed in A8)"),
    ("AMENDMENT_A7.md", "Amendment A7", "Continuous thresholds (log-odds; BOCPD drop size), bisection to the fixed 0.2 alarms per session, same range for the H1(a) sweep", "A6 grids were too coarse for the fixed alarm-rate target; decided after the A6 pilot test curves were seen (disclosed in A8 item 2)"),
    ("PILOT_REPORT_A7.md", "Pilot", "Machinery pilot under A7 (RAW fold 3); fix for the undefined old state when the first updates are skipped", "Run A7 machinery; skipped first updates left the old state undefined"),
    ("READOUT_AND_PROJECTION_A7.md", "Check", "Hit(0.2) >= hit(0.1) holds by construction (no violation); vectorised sweep 27x faster; 34-fold run-time projection", "User-raised readout question; sweep dominated run time"),
    ("PILOT_REPORT_LEGACY.md", "Pilot", "LEGACY fold 29 machinery pilot: build timing, 25/25 checks, kill and resume, memory, revised projections", "LEGACY panel is 5.7x larger; memory and checkpoint recovery needed checking (2 workers at most)"),
    ("section5_cold_audit.md", "Audit", "Cold audit of Section 5 code and records: 22 findings, 2 critical (splice scale not in the detector's units; A7 decided after test curves seen)", "Independent check before main runs; findings drove A8"),
    ("D6_REPORT.md", "Diagnostic D6", "SPY variance ratio 60 min after versus before FOMC 14:00 statements and three shocks, against random same-time moments; descriptive, no detectors", "Context for H1(c); FOMC median ratio 8.56 against 0.91 at random times"),
    ("AMENDMENT_A8.md", "Amendment A8", "Splice fix (scale in detector units) with R=1 gate; contamination list and fold exclusion; fewer than 8 stable days skips H1(a); N.3 justification; H1(c) secondary", "Cold audit findings 1-4 and 5; D6"),
    ("A8_GATE_REPORT.md", "Gate", "R=1 gate against null splices FAILED (LEGACY 29: 4/8, RAW 3: 3/8); stopped as specified", "Null splices carry natural variance shifts (audit finding 8), inference"),
    ("AMENDMENT_A8_1.md", "Amendment A8.1", "Zero-effect reference = R=1 placebo splices; gate becomes P1 versus P2 construction check", "Decided after the A8 gate failed (disclosed); same construction for reference and effect curves"),
    ("A8_1_GATE_REPORT.md", "Gate", "P1 versus P2 gate: LEGACY 29 FAILED (3/8), RAW 3 passed (8/8); stopped", "Placebo sets reuse few stable days; splice-level bootstrap too narrow (inference)"),
    ("AMENDMENT_A8_2.md", "Amendment A8.2", "Gate bootstrap resamples stable days; D6 is descriptive, not contamination; H1(c) event choice disclosed as made knowing FOMC moves are large", "Decided after the LEGACY 29 failure; D6 ran no detector"),
    ("A8_2_GATE_REPORT.md", "Gate", "Day-level bootstrap gate: LEGACY 29 FAILED (5/8), RAW 3 passed (8/8); stopped", "Seed 777 is the decision seed; no re-draw"),
    ("AMENDMENT_A8_3.md", "Amendment A8.3", "Characterize the gate over 20 new seeds on both folds; pre-stated rule: LEGACY failure rate per detector within 2x RAW's (RAW floored at 0.05) means chance", "One seed cannot separate chance from a fold effect; no re-roll"),
    ("A8_3_GATE_CHARACTERIZATION.md", "Gate", "Rule result: Gaussian HMM base and HSMM f3 above 2x RAW (3/20 against 1/20 and 0/20); to be investigated", "Pooled failure rate 7.5% LEGACY, 3.1% RAW; intervals overlap"),
    ("AMENDMENT_A8_4.md", "Amendment A8.4", "Investigation scoped to multiplicity (permutation) and leave-one-day-out; decision rule pre-stated", "Two flagged detectors of eight; check chance and single-day drivers"),
    ("A8_4_INVESTIGATION.md", "Investigation", "P(>=2 of 8 exceed by chance) = 0.152 (> 10%); no single driving day; rule: document and proceed", "Pre-stated rule of A8.4; proceed = contamination list and eligible FOMC event list only"),
    (R + "contamination_list.json", "Result (A8 item 2, H1(c) event list)", "6 of 34 folds excluded from confirmatory H1 (LEGACY 27-29, RAW 1-3); 112 eligible FOMC events in 28 folds; D6 not counted as contamination", "Mechanical list from the script registry; A8.2 for D6; no detector scored on test data"),
    ("section5/s5_contamination.py", "Code", "Contamination registry, fold exclusion, H1(c) eligible event list", "A8 item 2, A8.2"),
    ("section5/s5_h1c.py", "Code", "H1(c) scoring functions (14:00-15:00 hit, earliest-fold assignment, paired sign test, Wilson); not run on real data", "A8 item 5"),
    ("section5/s5_select.py", "Code", "5.8 selection: greedy forward from return-only, K=3 / lambda=39, 1 start, stop under 1% gain or at 6 features, tuning with 3 starts, final-setup aggregation; objective injected", "Protocol 5.8; unit tested on synthetic objectives; not run on data"),
    ("section5/s5_stats.py", "Code", "5.9 and 5.11 statistics: block bootstrap (block 3), Wilcoxon, sign consistency, IU, Holm, BH, minimum detectable effect", "Protocol 5.9, 5.11; unit tested; not run on data"),
    ("section5/s5_h1.py", "Code", "H1(a)/(b) fold effects, family results (confirmatory and all-folds), Holm over four families", "Protocol 5.9, A6/A7/A8 (a) metric and fold exclusion; unit tested; not run on data"),
    ("section5/s5_freeze.py", "Code", "5.12 freeze document and 5.13 guarded refit runner (hash check, token, once per era, no retuning); H2 primary detector rule", "Protocol 5.12-5.13; unit tested with stubs; no evaluation data touched"),
    ("section5/s5_tests_build.py", "Code", "22 unit tests for the selection, statistics, H1 scoring and freeze modules", "Test coverage requested with the code"),
]


def init():
    t = LEDGER.read_text(encoding="utf-8")
    if MARK in t: raise SystemExit("Section 5 part already present; use add")
    if not t.endswith("\n"): t += "\n"
    intro = ["", MARK, "",
             "Scope: Section 5 records (protocol, amendments A6-A8.4, diagnostics D2-D6, pilots, cold audit, gates, code). Section 4 amendments A1-A5 and notes are in parts 1-4 above; Section 5 has no A1-A5 of its own (its amendments start at A6 by the A1-A5 numbering of Section 4).",
             "Rows are appended after every Section 5 step (`section5/s5_ledger.py add`). Hashes are of the files as committed; where a file is later superseded the row stays.", ""] + HEAD
    LEDGER.write_text(t + "\n".join(intro + [row(*r) for r in ROWS]) + "\n", encoding="utf-8"); finish(); print(len(ROWS), "rows")


def add(f, kind, decision, reason):
    t = LEDGER.read_text(encoding="utf-8")
    if MARK not in t: raise SystemExit("run init first")
    LEDGER.write_text(t.rstrip("\n") + "\n" + row(f, kind, decision, reason) + "\n", encoding="utf-8"); finish(); print("added", f)


if __name__ == "__main__":
    {"init": lambda: init(), "add": lambda: add(*sys.argv[2:6])}[sys.argv[1]]()
