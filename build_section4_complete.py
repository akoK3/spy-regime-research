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
dic = {x["output"]: x for x in load(cl431)["feature_dictionary"]}
a3m = pd.read_csv(R / "sec4_3_9_frozen_matrix.csv").set_index("output")
pool = pd.read_csv(R / "sec4_3_7_8_pool116_matrix.csv").set_index("column")
word = lambda s: str(s).split(":")[0]
rows = []
for n in pool.index:
    raw = n.replace("__sadj", "")
    d = dic[raw]; pr = pool.loc[n]
    adj = n.endswith("__sadj")
    formula = ("raw value / TRAIN median of the raw column at the same minute of the session, per era; NaN where that median is missing or <= 0 (A3 4.3.4)" if adj else d["definition"])
    cls = "adjusted" if adj else a3m.loc[raw, "feature_class"]
    a3p, a3s = ("-", "-") if adj else (word(a3m.loc[raw, "primary_redundancy"]), word(a3m.loc[raw, "sensitivity_redundancy"]))
    rows.append((n, cls, formula, f"{d['lookback_bars']} / {d['lookback_sessions']}", d["min_valid_obs"], d["warmup"], f"{pr.coverage_LEGACY_pct:.3f}", f"{pr.coverage_RAW_pct:.3f}",
                 "yes" if pr.primary_eligible else "no", a3p, a3s, word(pr.primary_outcome), word(pr.sensitivity_outcome)))

# ---- tests
T = []
def tr(test, scope, result, f):
    T.append((test, scope, result, rel(f), sha(f)))
ph = ROOT / "section431_step3_verification" / "step3_phaseA_report.json"
if ph.exists():
    for t in load(ph)["existing_tests"]:
        tr(f"Existing test file {t['test']}", "phase A baseline (Step 3)", t["status"] + (" (pytest: no tests ran)" if t["status"] == "FAIL_EXISTING_TESTS" else ""), ph)
tr("test_candidates.py, 6 tests", "frozen implementation, rebuild folder", "OK 6/6", DATA / "validation_tests.txt")
tr("4.3.2/4.3.3 source-level synthetic tests, 12 tests", "2026-10-29 audit", load(DATA / "audit_4_3_2_4_3_3_report.json")["status"], DATA / "audit_4_3_2_4_3_3_report.json")
m2 = pd.read_csv(ROOT / "section431_step2_final_audit" / "feature_family_eligibility_matrix.csv") if (ROOT / "section431_step2_final_audit" / "feature_family_eligibility_matrix.csv").exists() else pd.read_csv(Path(r"C:\Users\kakij\Downloads\section431_step2_final_audit\feature_family_eligibility_matrix.csv"))
m2f = Path(r"C:\Users\kakij\Downloads\section431_step2_final_audit\feature_family_eligibility_matrix.csv")
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
]

L = ["# SECTION4_COMPLETE", "", f"Generated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} | repository HEAD before this commit `{head}`",
     "Scope: Section 4 as recorded in this repository: 4.3.0-4.3.9. Sections 4.1 and 4.2: placeholder below. Pre-rebuild results of sections 4.4-4.9: not part of this record.", "",
     "## 4.1 and 4.2", "", "> **PLACEHOLDER: 4.1/4.2 TEXT NOT PROVIDED.**", ">", "> To be added by the repository owner. When added: source path and SHA-256 of the source file.", "",
     "## Chronological decision log", "", f"Source: METHODS_LEDGER.md (SHA-256 `{sha(ROOT / 'METHODS_LEDGER.md')}`).", ""] + section("## 1. Chronology", "## 2. Limitations")
L += ["", f"## Dictionary of the 116-column pool ({len(rows)} columns)", "",
      "Columns: lookback = bars / sessions; Primary eligible = at least 80% in both eras; A3 primary / A3 sens. = outcome of the A3 run on the 80 raw columns (kept or dropped); Pool primary / Pool sens. = outcome of the run on the 116-column pool under note N2 (sensitivity = RAW only). 'not in set' = not in that set.", "",
      "| # | Column | Class | Formula | Lookback | Min valid obs | Warmup | LEGACY % | RAW % | Primary eligible | A3 primary | A3 sens. | Pool primary | Pool sens. |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
L += [f"| {i} | {esc(r[0])} | {esc(r[1])} | {esc(r[2])} | {r[3]} | {esc(r[4])} | {esc(r[5])} | {r[6]} | {r[7]} | {r[8]} | {r[9]} | {r[10]} | {r[11]} | {r[12]} |" for i, r in enumerate(rows, 1)]
ov = dic["overnight_return_open"]
L += ["", "Excluded from the pool (response-side only, A2 and N1):", "", "| Column | Formula | Lookback | Min valid obs | Warmup |", "|---|---|---|---|---|",
      f"| overnight_return_open | {esc(ov['definition'])} | {ov['lookback_bars']} / {ov['lookback_sessions']} | {esc(ov['min_valid_obs'])} | {esc(ov['warmup'])} |"]
L += ["", "## Tests and results", "", "| Test | Scope | Result | File | SHA-256 |", "|---|---|---|---|---|"] + [f"| {esc(a)} | {esc(b)} | {esc(c)} | {esc(d)} | `{h}` |" for a, b, c, d, h in T]
L += ["", "## Deviations and post-hoc items", "", "| # | Item | Detail | File | SHA-256 |", "|---|---|---|---|---|"] + [f"| {i} | {esc(a)} | {esc(b)} | {esc(rel(f))} | `{sha(f)}` |" for i, (a, b, f) in enumerate(D, 1)]
L += ["", "## Limitations"] + section("## 2. Limitations", "## 3. Open items")
L += ["", "## Open items for Section 5"] + section("## 3. Open items")
out = ROOT / "SECTION4_COMPLETE.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
(ROOT / "SECTION4_COMPLETE.sha256").write_text(f"{sha(out)}  {out.name}\n", encoding="ascii")
print(out.name, sha(out), "| dictionary rows:", len(rows), "| tests:", len(T), "| deviations:", len(D))
