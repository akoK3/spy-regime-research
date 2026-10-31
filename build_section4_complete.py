#!/usr/bin/env python3
"""Build SECTION4_COMPLETE.md from the repository documents and METHODS_LEDGER.md. 4.1/4.2 is a marked placeholder."""
import json, hashlib, subprocess, datetime, re
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
DATA = Path(r"C:\Users\kakij\OneDrive\Desktop\data\section4_3_rebuild_20261028")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


TRACKED = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split())


def rel(p):
    p = Path(p)
    try: r = p.relative_to(ROOT).as_posix()
    except ValueError: return f"{p} (not in repository)"
    return r if r in TRACKED else f"{r} (not in repository)"


def g(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def esc(t):
    return str(t).replace("|", "\\|").replace("\n", " ")


ledger = (ROOT / "METHODS_LEDGER.md").read_text(encoding="utf-8")
def section(title_start, next_start=None):
    a = ledger.index(title_start)
    b = ledger.index(next_start, a) if next_start else len(ledger)
    return ledger[a:b].rstrip().split("\n")[1:]

cl431, cl43 = g("section_4_3_1_closing_report_2*.json"), g("section_4_3_closing_report_section4_2*.json")
a2, a3, n1, n2 = g("amendment_4_3_1_A2_*.json"), g("amendment_4_3_A3_2*.json"), g("note_4_3_N1_2*.json"), g("note_4_3_N2_2*.json")
p1, p1a, ver1, ver2 = g("policy_4_3_1_P1_2*.json"), g("policy_4_3_1_P1_addendum_2*.json"), g("policy_4_3_1_P1_verification_2*.json"), g("policy_4_3_1_P1_verification_v2_*.json")
appr, v1, v2 = g("approval_4_3_0_A1_2*.json"), FZ / "protocol_20261029T032504Z.json", FZ / "protocol_20261029T032641Z.json"
a1, covam = FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json", FZ / "protocol_amendment_431_A2_FROZEN_coverage.json"
r49, r78, r5b = R / "sec4_3_4_to_4_3_9_report.json", R / "sec4_3_7_8_pool116_report.json", R / "sec4_3_5b_legacy_stale_zero_volume.json"
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

# ---- dictionary
a4, a5, n3, cold = g("amendment_4_3_A4_2*.json"), g("amendment_4_3_A5_2*.json"), g("note_4_3_N3_2*.json"), ROOT / "cold_audit_20261030.md"
a4res, a5res, cal = R / "a4_results_report.json", R / "a5_results_report.json", R / "a4_lm_threshold_calibration.json"
a4rep, a4pi, f1chk = R / "a4_sec4_3_4_7_8_report.json", R / "a4_prefix_isolation_report.json", R / "a4_folds_check.json"
cladd_audit, cladd_avail = g("section_4_3_closing_report_addendum_audit_2*.json"), g("section_4_3_closing_report_addendum_availability_2*.json")
am5, jv5, cut5 = R / "a5_amihud_adjustment_check.json", R / "a5_jump_variation_redundancy.json", R / "a5_train_cutoffs.json"
dic = {x["output"]: x for x in load(cl431)["feature_dictionary"]}
a3m = pd.read_csv(R / "sec4_3_9_frozen_matrix.csv").set_index("output")
pool = pd.read_csv(R / "a4_sec4_3_9_frozen_matrix.csv").set_index("column")  # current frozen matrix: 78 raw + 35 adjusted, coverage recomputed under A4 and A5
reg69, g3c = R / "a4_sec4_3_6_9_report.json", R / "a5_jump_variation_redundancy_corrected.json"
thr = load(cal)["threshold"]
word = lambda s: str(s).split(":")[0]
rows = []
for n in pool.index:
    raw = n.replace("__sadj", "")
    d = dic[raw]; pr = pool.loc[n]
    adj = n.endswith("__sadj")
    note = ""
    if adj:
        formula = "raw value / median of the same slot over the previous 20 sessions of the same era (at least 10 finite values); NaN if the raw value or the baseline is missing, or the baseline is <= 0 (A4 F2)"
        look, minobs, warm = f"{d['lookback_bars']} / 20", f"{d['min_valid_obs']}; baseline needs 10 of the previous 20 sessions", d["warmup"].replace("session 0", "session 10")
        note = "definition changed by A4 F2" + ("; coverage reduced after A5 G3 (about half of the raw values are exactly 0, so the baseline is 0 on many slots)" if raw.startswith("jump_variation_") else "")
    else:
        formula, look, minobs, warm = d["definition"], f"{d['lookback_bars']} / {d['lookback_sessions']}", d["min_valid_obs"], d["warmup"]
        if raw.startswith("jump_variation_"):
            formula = "max(0, sum of r_i^2 over the w returns - (w/(w-1)) * (pi/2) * sum over the w-1 adjacent pairs of |r_i||r_(i-1)|) (A5 G3)"; note = "formula changed by A5 G3"
        if raw == "lee_mykland_jump60":
            formula = f"1.0 if |lee_mykland_approx60| > {thr} (99th percentile of the session maximum of |stat| over 200,000 simulated Gaussian 390-bar no-jump sessions, A4 F3), else 0.0; undefined where the statistic is undefined"; note = "threshold changed by A4 F3 (was 5.4667)"
    if raw.startswith("amihud_"):
        note = (note + "; " if note else "") + "LEGACY closes appear dividend-adjusted; normalize per fold in Section 5 (N3)"
    cls = "adjusted" if adj else a3m.loc[raw, "feature_class"]
    rows.append((n, cls, formula, look, minobs, warm, f"{pr.coverage_LEGACY_pct:.3f}", f"{pr.coverage_RAW_pct:.3f}",
                 "yes" if pr.primary_eligible else "no", word(pr.primary_outcome), word(pr.sensitivity_outcome), note or "-"))

# ---- tests
T = []
def tr(test, scope, result, f):
    T.append((test, scope, result, rel(f), sha(f)))
ph = FZ / "step3_phaseA_report.json"
if ph.exists():
    for t in load(ph)["existing_tests"]:
        tr(f"Existing test file {t['test']}", "phase A baseline (Step 3)", t["status"] + (" (pytest: no tests ran)" if t["status"] == "FAIL_EXISTING_TESTS" else ""), ph)
tr("test_candidates.py, 6 tests", "frozen implementation, rebuild folder", "OK 6/6", FZ / "validation_tests.txt")
tr("4.3.2/4.3.3 source-level synthetic tests, 12 tests", "2026-10-29 audit", load(FZ / "audit_4_3_2_4_3_3_report.json")["status"], FZ / "audit_4_3_2_4_3_3_report.json")
m2f = FZ / "feature_family_eligibility_matrix.csv"
m2 = pd.read_csv(m2f)
tr("Step 2 family coverage screen (11 families, 80% floor)", "TRAIN, both eras", f"{(m2.coverage_screen == 'MEETS_FROZEN_FLOOR').sum()} meet, {(m2.coverage_screen == 'BELOW_FROZEN_FLOOR').sum()} below", m2f)
for era in ("RAW", "LEGACY"):
    f = R / f"step3_{era}_report.json"; r = load(f)
    for k, v in r["checks"].items(): tr(f"Step 3 {k}", era, v["status"], f)
    tr("Step 3 overall", era, r["status"], f)
t4 = load(R / "step4_parameter_table.json")
tr("Step 4 comparison with frozen v2 and A2 (81 outputs)", "synthetic probe panel", f"PASS {t4['counts']['PASS']}, FAIL {t4['counts']['FAIL']}, EXCLUDED {t4['counts']['EXCLUDED']}", R / "step4_parameter_table.json")
for f, label in ((ver1, "Step 5 verification v1"), (ver2, "Step 5 verification v2")):
    for it in load(f)["table"]:
        res = it["status"] + (f" [{it['label']}]" if "label" in it else "")
        tr(f"{label}: {it['item']}", "saved Step 3/4 results" if it["item"].startswith("R") else "dataset named in the test", res, f)
tr("Step 5 delay-test diagnosis", "mismatching rows of the original shift test", "mismatches only at slot W (partial90) and slot 210 after an early close (RAW relative volume)", R / "step5_delay_failure_diagnosis.json")
c6 = load(R / "step6_coverage_TRAIN.json")
tr("Step 6 coverage cross-check against saved Step 3 counts", "both eras", c6["checked_against"], R / "step6_coverage_TRAIN.json")
tr("Step 6 coverage result", "80 detector outputs", f"PASS {c6['counts']['PASS']}, BELOW {c6['counts']['BELOW']}", R / "step6_coverage_TRAIN.json")
rep = load(r49)
for sec, v in rep["subsections"].items():
    if "checks" in v and isinstance(v["checks"], dict):
        for k, ok in v["checks"].items():
            if isinstance(ok, bool): tr(f"{sec}: {k}", "TRAIN, RAW then LEGACY", "PASS" if ok else "FAIL", r49)
    tr(f"{sec} subsection", "TRAIN, RAW then LEGACY", v["status"], r49)
rp = load(r78)
for sec, v in rp["subsections"].items():
    for k, ok in v["checks"].items(): tr(f"Pool 116, {sec}: {k}", "TRAIN, RAW then LEGACY", "PASS" if ok else "FAIL", r78)
tr("4.3.5b flagged bars equal the 4.3.5 LEGACY result", "LEGACY", "PASS (assertion held)", r5b)
# ---- A4 and A5
fold = load(f1chk)
tr("A4 F1: " + fold["assertions"], "TRAIN sessions per era from the manifest", fold["status"], f1chk)
calj = load(cal)
tr("A4 F3: second-seed false-alarm rate between 0.9% and 1.1% at the threshold", "200,000 simulated sessions", f"{calj['check_second_seed_between_0_9_and_1_1_pct']} ({calj['false_alarm_rate_at_threshold']['seed_43106']:.4%}; threshold {calj['threshold']})", cal)
a4repd = load(a4rep)
for sec, v in a4repd["subsections"].items():
    if sec.startswith("F2"):
        for era, c in v["checks"].items():
            tr(f"A4 {sec}: brute-force cells, prefix invariance, first 10 sessions NaN", era, f"{c['status']} ({c['brute_force_cells']} cells, {len(c['brute_force_mismatches'])} mismatches)", a4rep)
    elif isinstance(v.get("checks"), dict):
        for k, ok in v["checks"].items():
            if isinstance(ok, bool): tr(f"A4 {sec}: {k}", "TRAIN, RAW then LEGACY, 113-column pool", "PASS" if ok else "FAIL", a4rep)
    tr(f"A4 {sec}", "TRAIN, RAW then LEGACY, 113-column pool", v["status"], a4rep)
for t in load(a4pi)["table"]:
    tr(f"A4 F4: {t['item']}", "relative tolerance rtol 1e-9, atol 0", t["status"], a4pi)
for it in load(a4res)["items"]:
    tr(f"A4 result {it['item']}", "A4 results report", f"{it['status']}: {it['detail']}", a4res)
for it in load(a5res)["items"]:
    tr(f"A5 result {it['item']}", "A5 results report", f"{it['status']}: {it['detail']}", a5res)
g3cd = load(g3c)
for k, ok in g3cd["checks"].items(): tr(f"A5 G3 corrected run: {k}", "RAW, TRAIN only", "PASS" if ok else "FAIL", g3c)
r69 = load(reg69)
tr("4.3.6 regenerated under A4/A5", "TRAIN only, 113 columns", f"DESCRIPTIVE: {r69['sections']['4.3.6']['rows']} rows", R / "a4_sec4_3_6_yearly_median_iqr.csv")
for k, ok in r69["sections"]["4.3.9"]["checks"].items(): tr(f"4.3.9 regenerated: {k}", "TRAIN only, 113 columns", "PASS" if ok else "FAIL", reg69)

# ---- deviations and post-hoc items: (item, detail, file)
D = [
    ("Protocol v1 replaced by v2", "First full-data run failed at a date-endpoint assertion (NumPy 2.5 min/max on Unicode arrays); v2 changes the check only", v2),
    ("Amendment 4.3.0-A1 approved after use", "A2 cited A1 by hash and the 4.3.1 closing report listed it as a proposal before approval", appr),
    ("Coverage amendment is post-screening", "Aggregate and annual coverage had been observed before it was written; numerators defined for 11 family proxies only", covam),
    ("Step 1 label undefined", "No file defines 'Step 1'; the 4.3.1 closing report lists the baseline inputs instead", cl431),
    ("Formula source differs from the file named", "build_features_4_3_1.py does not exist; close_location_proxy, overnight_return_open, lee_mykland_* ported from section-4.3.1.py (lm_stat60, lm_jump60 names differ)", a2),
    ("Extra output lee_mykland_jump60", "Added as a fourth ported output; 81 outputs instead of 80", a2),
    ("A2 specification written after implementation", "45 outputs specified from measured values; not ex ante", a2),
    ("Cap defined on return-bars", "60 prior return-bars, Step 4 lookback limit 61; a literal 60-bar cap would exclude shock_prior60_mad and lee_mykland_*", a2),
    ("Two documents named A2", "4.3.1-A2 (specification) and 4.3.1-A2-post-screening (coverage)", covam),
    ("Step 3 slice method", "Prefix and isolation tests use a 40-session slice, last 15 sessions compared, for both eras", g("step3_RAW_report.json") if False else R / "step3_RAW_report.json"),
    ("Step 3 status rule changed", "Era PASS when every check passes; fixed caveat notes removed", R / "step3_LEGACY_report.json"),
    ("Step 4 probe corrections", "First pass gave 11 FAIL from probe artifacts (floating-point tolerance; missing-return counting); corrected, no code mismatch", R / "step4_parameter_table.json"),
    ("Policy P1 written after implementation", "States the rules the implementation follows; not preregistered", p1),
    ("Original delay test failed and was replaced", "Strict one-bar shift test FAIL in 3 datasets; addendum written after the failure labels it MIS-SPECIFIED, retained, not counted", p1a),
    ("Step 6 numerator is an extension", "Column's own finite values used; the amendment defines numerators only through family proxies; chosen by the repository owner", R / "step6_coverage_TRAIN.json"),
    ("A3 tie-break rule (3) added", "Dictionary position added as a deterministic tie-break; not part of the instruction as first given", a3),
    ("A3 readings stated", "4.3.5 shares reported against both denominators; 4.3.9 primary and sensitivity matrices are views of one matrix", r49),
    ("A3 written with pre-rebuild results possibly known", "Sections 4.4, 4.6, 4.7 results from the earlier pipeline exist and used the 2025-2026 period", a3),
    ("4.3.2/4.3.3 had an earlier run", "Source-level synthetic audit of 2026-10-29 predates A3; A3 adds no work", a3),
    ("4.3.5b follow-up is post-hoc", "LEGACY stale runs and zero volume, run after the A3 run, not defined in A3", r5b),
    ("Note N1 changes two A3 sentences", "Written after the 4.3.4-4.3.9 run; adjusted columns become separate candidates and redundancy covers them", n1),
    ("Note N2 tie-break for adjusted columns", "Positions 80-115, raw wins ties; chosen by the repository owner; note committed before the pool run", n2),
    ("Closing report scope", "Closing report covers Section 4.3 (4.3.0-4.3.9), marker SECTION_4_3_CLOSED; later results added as an addendum, closed report unchanged", cl43),
    ("List of 10 open items is derived", "No document defines a list of 10 postponed items; merged from the documents' deferred and not-decided lists", ROOT / "METHODS_LEDGER.md"),
    ("Cold audit applied after the closing reports", "The audit found 12 problems; A4 and A5 fix them; the closed reports are not edited and corrections are in addenda", cold),
    ("Seasonal adjustment replaced", "The A3 definition (median over all TRAIN rows) is replaced by a causal 20-session baseline (A4 F2); the A3-run and 116-column-pool results for the adjusted columns are superseded; 4.3.6 and the 4.3.9 matrix were regenerated afterwards for the 113-column pool", reg69),
    ("A5 G3 redundancy ranked with stale coverage", "Step 13 used the A4-run coverage; the A5 scaling makes about half of the jump_variation values exactly 0, so jump_variation_w__sadj lost coverage; the rerun with current coverage (step 16) gave the same RAW sensitivity outcome (keep 83, drop 30); the committed G3 files are not edited", g3c),
    ("First 4.3.9 matrix failed its coverage cross-check", "The first regeneration wrote a matrix with the A4-run coverage; the check failed for the three jump_variation__sadj columns; the matrix was rebuilt from the kept 4.3.6 file; the failed report is kept as a4_first_attempt_sec4_3_6_9_report.json", reg69),
    ("Lee-Mykland threshold replaced", "5.4667 (A2) replaced by 4.6113 from simulation (A4 F3)", cal),
    ("jump_variation formula changed", "Bipower term scaled by w/(w-1) (A5 G3), superseding the A2 definition; bipower_w unchanged (reading stated by the assistant); F4 not rerun for it", jv5),
    ("Volume columns taken out of the detector set", "raw_volume, log_raw_volume and raw_volume__sadj are diagnostics-only (A4 F5, decision of the repository owner); the N1/N2 116-column pool is superseded by the 113-column pool", a4),
    ("rv10 approved in place of rv15 after the audit", "Approved by the repository owner in A5 G5; amended tiers still contain below-floor members; the frozen protocol file is not edited", a5),
    ("F2/F5 rerun needed three attempts", "The first was killed during the LEGACY feature pass; the second failed on this repository's own overwrite guard before any analysis; the third completed", a4res),
    ("F4 run per era with spilled features", "The first attempt was stopped for low system memory; float32 was not used because it would coarsen the rtol 1e-9 tolerance; each era has its own fixed seed", a4res),
    ("F7 checker defects corrected", "The first evaluation failed on two defects in the checker (a text label matched; an untracked unrelated file compiled); corrected, criterion unchanged", a4res),
    ("G4 reads one non-TRAIN price level", "The junction ratio uses one LEGACY close from 2022-03-04 (EVALUATION_EXPOSED in the manifest); no return statistic from that period is computed", am5),
    ("Amihud finding is an inference", "LEGACY closes appear dividend-adjusted; the rule-based reading was inconclusive and the price-level evidence uses an external reference not in the repository; N3 records the requirement to normalize Amihud per fold", n3),
    ("TRAIN cutoffs recorded from a derived manifest", "The manifest is not an approved frozen document (A1 manifest item unverified)", cut5),
]

L = ["# SECTION4_COMPLETE", "", f"Generated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} | repository HEAD before this commit `{head}`",
     "Scope: Section 4 as recorded in this repository: 4.3.0-4.3.9, including amendments A4 and A5, notes N1 to N3 and the cold audit. Sections 4.1 and 4.2: placeholder below. Pre-rebuild results of sections 4.4-4.9: not part of this record.", "",
     "## 4.1 and 4.2", "", "> **PLACEHOLDER: 4.1/4.2 TEXT NOT PROVIDED.**", ">", "> To be added by the repository owner. When added: source path and SHA-256 of the source file.", "",
     "## Chronological decision log", "", f"Source: METHODS_LEDGER.md (SHA-256 `{sha(ROOT / 'METHODS_LEDGER.md')}`).", ""] + section("## 1. Chronology", "## 2. Limitations")
L += ["", f"## Dictionary of the current pool ({len(rows)} columns: {sum(not r[0].endswith('__sadj') for r in rows)} raw + {sum(r[0].endswith('__sadj') for r in rows)} adjusted, as of amendments A4 and A5)", "",
      "Columns: lookback = bars / sessions; Primary eligible = at least 80% in both eras (own coverage); Primary (A4 run) and RAW sensitivity (A4 run) = outcome of the A4 rerun of 4.3.8 (kept or dropped; sensitivity is RAW only); 'not in set' = not in that set. Earlier results (A3 run on 80 raw columns; N2 run on 116 columns) are superseded for this pool and are listed in the decision log.", "",
      "| # | Column | Class | Formula | Lookback | Min valid obs | Warmup | LEGACY % | RAW % | Primary eligible | Primary (A4 run) | RAW sensitivity (A4 run) | Note |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
L += [f"| {i} | {esc(r[0])} | {esc(r[1])} | {esc(r[2])} | {r[3]} | {esc(r[4])} | {esc(r[5])} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {esc(r[11])} |" for i, r in enumerate(rows, 1)]
ov, rv, lrv = dic["overnight_return_open"], dic["raw_volume"], dic["log_raw_volume"]
L += ["", "Not in the pool:", "", "| Column | Reason | Formula | Lookback | Min valid obs | Warmup |", "|---|---|---|---|---|---|",
      f"| overnight_return_open | response-side only (A2, N1) | {esc(ov['definition'])} | {ov['lookback_bars']} / {ov['lookback_sessions']} | {esc(ov['min_valid_obs'])} | {esc(ov['warmup'])} |",
      f"| raw_volume | diagnostics-only (A4 F5; frozen protocol: raw/log volume are diagnostic candidates only) | {esc(rv['definition'])} | {rv['lookback_bars']} / {rv['lookback_sessions']} | {esc(rv['min_valid_obs'])} | {esc(rv['warmup'])} |",
      f"| log_raw_volume | diagnostics-only (A4 F5) | {esc(lrv['definition'])} | {lrv['lookback_bars']} / {lrv['lookback_sessions']} | {esc(lrv['min_valid_obs'])} | {esc(lrv['warmup'])} |"]
L += ["", "## Tests and results", "", "| Test | Scope | Result | File | SHA-256 |", "|---|---|---|---|---|"] + [f"| {esc(a)} | {esc(b)} | {esc(c)} | {esc(d)} | `{h}` |" for a, b, c, d, h in T]
L += ["", "## Deviations and post-hoc items", "", "| # | Item | Detail | File | SHA-256 |", "|---|---|---|---|---|"] + [f"| {i} | {esc(a)} | {esc(b)} | {esc(rel(f))} | `{sha(f)}` |" for i, (a, b, f) in enumerate(D, 1)]
L += ["", "## Limitations"] + section("## 2. Limitations", "## 3. Open items")
L += ["", "## Open items for Section 5"] + section("## 3. Open items")
out = ROOT / "SECTION4_COMPLETE.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
(ROOT / "SECTION4_COMPLETE.sha256").write_text(f"{sha(out)}  {out.name}\n", encoding="ascii")
print(out.name, sha(out), "| dictionary rows:", len(rows), "| tests:", len(T), "| deviations:", len(D))
