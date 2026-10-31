#!/usr/bin/env python3
"""Build METHODS_LEDGER.md from the frozen documents, reports and notes in the repository.
Dates come from each document's own timestamp, hashes from the files, limitations and open items from the documents' own lists."""
import json, hashlib, subprocess, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def rel(p):
    return Path(p).relative_to(ROOT).as_posix()


def g(pattern, base=R):
    files = sorted(base.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def esc(t):
    return str(t).replace("|", "\\|").replace("\n", " ")


KEYS = ("created_utc", "generated_utc", "closed_utc", "frozen_utc", "date_utc")


def date_of(p):
    d = load(p)
    for k in KEYS:
        if k in d: return d[k]
    raise KeyError(f"no date in {p}")


def fmt(ts):
    if len(ts) == 10: return ts
    return datetime.datetime.fromisoformat(ts).astimezone(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")


tracked = set(subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True).stdout.split())
head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, text=True).stdout.strip()

v1, v2 = FZ / "protocol_20261029T032504Z.json", FZ / "protocol_20261029T032641Z.json"
a1, cov_am = FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json", FZ / "protocol_amendment_431_A2_FROZEN_coverage.json"
s3r, s3l = R / "step3_RAW_report.json", R / "step3_LEGACY_report.json"
a2, p1, p1a = g("amendment_4_3_1_A2_*.json"), g("policy_4_3_1_P1_2*.json"), g("policy_4_3_1_P1_addendum_2*.json")
ver1, ver2 = g("policy_4_3_1_P1_verification_2*.json"), g("policy_4_3_1_P1_verification_v2_*.json")
diag, t4, c6 = R / "step5_delay_failure_diagnosis.json", R / "step4_parameter_table.json", R / "step6_coverage_TRAIN.json"
cl431, cl43, cladd = g("section_4_3_1_closing_report_2*.json"), g("section_4_3_closing_report_section4_2*.json"), g("section_4_3_closing_report_addendum_pool116_2*.json")
appr, a3, n1, n2 = g("approval_4_3_0_A1_2*.json"), g("amendment_4_3_A3_2*.json"), g("note_4_3_N1_2*.json"), g("note_4_3_N2_2*.json")
r49, r5b, r78 = R / "sec4_3_4_to_4_3_9_report.json", R / "sec4_3_5b_legacy_stale_zero_volume.json", R / "sec4_3_7_8_pool116_report.json"

# (file, section, decision, rationale, file that carries the date)
E = [
    (v1, "4.3.0 / 4.3.1", "Freeze v1: development spans (LEGACY 2003-01-02..2022-03-04, RAW 2022-03-07..2024-12-31); exposed retrospective evaluation 2025-01-02..2026-10-12; provider separation; clocks; 35 candidate features", "Prior exposure of the 2025-2026 period (PRIOR_FEATURE_AND_MODEL_SELECTION_EXPOSURE); NO_UNEXPOSED_PERIOD_IDENTIFIED", None),
    (v2, "4.3.0 / 4.3.1", "Freeze v2 (supersedes v1): endpoint check changed to first/last session on time-sorted data; loader/availability regression test added; scientific decisions unchanged", "v1 first full-data run failed: NumPy 2.5 does not reduce Unicode arrays with min/max; no feature file or score produced", None),
    (a1, "4.3.0", "Proposal 4.3.0-A1: embargo 5 complete sessions; max feature lookback 60 minutes; refit policy frozen; LEGACY evaluation 2019-01-02..2022-03-04 (retrospective/previously exposed); SPY evaluation end 2026-10-12; IEX detector trained only on 2022-03-07..2024-12-31", "An embargo cannot erase prior exploratory exposure; status AMENDMENT PROPOSAL requiring audit and explicit approval before use", None),
    (cov_am, "4.3.1 Step 2", "Coverage amendment 4.3.1-A2-post-screening: floor 80% in each era; minute denominator = all frozen TRAIN canonical grid rows incl. unavailable bars and session openings; overnight denominator = TRAIN session transitions; 11 family eligibility proxies", "Feature observable in at least four of five eligible time positions per training era; post-screening: aggregate and annual coverage already observed", None),
    (s3r, "4.3.1 Step 3", "Audit of 81 outputs, RAW: 8 of 8 checks PASS; prefix/isolation tests by 40-session slice; era PASS only if every check PASS", "Independent per-row oracle on synthetic panel; real-data spot checks; provider isolation; deferred-output check", None),
    (s3l, "4.3.1 Step 3", "Audit of 81 outputs, LEGACY: 8 of 8 checks PASS; same method as RAW", "Same as RAW", None),
    (a2, "4.3.1 Step 4", "Amendment 4.3.1-A2: lookback, minimum valid observations, warmup for 45 outputs; cap = 60 prior return-bars (Step 4 lookback limit 61); overnight_return_open excluded from detector features", "Written after implementation; frozen clocks: 'No overnight returns'; shock_prior60_mad and lee_mykland_* use 60 prior returns plus the current one", None),
    (t4, "4.3.1 Step 4", "Parameters extracted from code for 81 outputs: 80 PASS, 0 FAIL, 1 EXCLUDED (overnight_return_open)", "Probes: bar bump, return removal, single-bar knockout, same-slot session removal, future-bar bump; compared with frozen v2 and A2", None),
    (p1, "4.3.1 Step 5", "Policy P1: R1 bar stamped t usable at t+1 minute; R2 windows reset at session open, only the 20-session relative-volume baseline crosses sessions; R3 no LEGACY/RAW crossing; R4 overnight excluded", "Written after implementation; R1-R4 enforced by loader assertion, per-session construction, per-era loading, declaration", None),
    (ver1, "4.3.1 Step 5", "R1-R4 PASS; strict one-bar shift test FAIL (75/80, 73/80, 75/80 outputs)", "Mismatches only at clock-position edge rows", None),
    (diag, "4.3.1 Step 5", "Shift-test mismatches: partial90 outputs at slot W (original NaN, delayed finite); RAW relative_volume20 at slot 210 after the 2022-11-25 early close", "Frozen slot >= W rule; shift drops the last bar of each session", None),
    (p1a, "4.3.1 Step 5", "Addendum P1-A: original shift test labeled MIS-SPECIFIED and retained; replaced by identical values, available_at = t+2 min, point-in-time replay", "Written after the failure was seen; R1 concerns availability, not a shift of values", None),
    (ver2, "4.3.1 Step 5", "R1-R4 PASS; replacement delay test PASS on synthetic panel, RAW slice, LEGACY slice", "Original shift test retained and not counted", None),
    (c6, "4.3.1 Step 6", "TRAIN coverage of 80 detector outputs: 20 PASS, 60 BELOW (all in LEGACY); numerator = column's own finite values", "Amendment defines numerators only through 11 family proxies; numerator chosen by the repository owner", None),
    (cl431, "4.3.1", "Section 4.3.1 closed (SECTION_4_3_1_CLOSED)", "Steps 1-6 recorded; feature dictionary, amendments, hashes and limitations listed", None),
    (appr, "4.3.0", "Amendment 4.3.0-A1 approved, after 4.3.1 had used it", "A2 cites A1 by hash; approval is not ex ante; conflicts with A2/A3 not resolved", None),
    (a3, "4.3.2-4.3.9", "Amendment A3: 4.3.2/4.3.3 cited, no work; 4.3.4 TRAIN-median adjusted version for 36 scale features; 4.3.5 runs of 5+ identical closes; 4.3.6 yearly median/IQR; 4.3.7 primary 80% both eras, sensitivity all 80 on RAW; 4.3.8 |Spearman| > 0.95; 4.3.9 frozen matrix", "Fixed before 4.3.4-4.3.9 were run; prior 4.3.2/4.3.3 synthetic audit exists; pre-rebuild 4.4/4.6/4.7 results exist", None),
    (R / "sec4_3_4_slot_medians_RAW.csv", "4.3.4", "TRAIN median per slot for the 36 scale features, RAW", "A3 4.3.4; no slot with undefined or non-positive median", r49),
    (R / "sec4_3_4_slot_medians_LEGACY.csv", "4.3.4", "TRAIN median per slot for the 36 scale features, LEGACY", "A3 4.3.4; no slot with undefined or non-positive median", r49),
    (R / "sec4_3_5_stale_closes_by_year.csv", "4.3.5", "Flagged bars (5+ identical closes) by era and year: RAW 5, LEGACY 23,188", "A3 4.3.5; descriptive; shares against grid rows and observed bars", r49),
    (R / "sec4_3_5_stale_closes_by_slot.csv", "4.3.5", "Flagged bars by era and slot", "A3 4.3.5; descriptive", r49),
    (R / "sec4_3_6_yearly_median_iqr.csv", "4.3.6", "Yearly median and IQR: 116 columns by era and year (2,204 rows)", "A3 4.3.6; descriptive; no exclusions", r49),
    (R / "sec4_3_7_eligibility.json", "4.3.7", "Primary = 20 columns (80% in both eras); sensitivity = all 80 on RAW; overnight in neither", "A3 4.3.7; primary equals Step 6 PASS set", r49),
    (R / "sec4_3_8_redundancy.json", "4.3.8", "Primary keep 14 / drop 6; sensitivity (RAW) keep 58 / drop 22", "A3 4.3.8; |Spearman| > 0.95; shorter window, then higher coverage, then dictionary order", r49),
    (R / "sec4_3_9_frozen_matrix.csv", "4.3.9", "Frozen matrix, 80 rows, with primary and sensitivity views", "A3 4.3.9; one matrix, two views", r49),
    (r49, "4.3.4-4.3.9", "A3 run: 4.3.4 PASS, 4.3.5/4.3.6 descriptive, 4.3.7 PASS, 4.3.8 PASS, 4.3.9 PASS; overall PASS", "TRAIN only, RAW then LEGACY; coverage counts equal Step 6", None),
    (r5b, "4.3.5b", "LEGACY stale runs: 0 of 23,188 flagged bars have zero volume in any year; LEGACY has 0 zero-volume bars", "Post-hoc descriptive follow-up; not defined in A3", None),
    (n1, "4.3", "Note N1: adjusted columns join the candidate pool alongside raw (80 raw + 36 adjusted = 116); overnight_return_open is response-side only", "Written after the 4.3.4-4.3.9 run; supersedes two A3 sentences (adjusted 'not a separate candidate'; redundancy 'applies to raw columns')", None),
    (cl43, "4.3", "Section 4.3 closed (SECTION_4_3_CLOSED), scope 4.3.0-4.3.9", "Results by subsection, amendments, hashes, limitations, decisions not taken", None),
    (n2, "4.3.7 / 4.3.8", "Note N2: A3 4.3.7 and 4.3.8 applied unchanged to the 116-column pool; adjusted columns take dictionary positions 80-115 (raw wins ties)", "Written before the pool run; tie-break chosen by the repository owner", None),
    (R / "sec4_3_7_8_pool116_eligibility.json", "4.3.7", "Pool eligibility: primary 30 columns; sensitivity 116 on RAW", "N2; adjusted coverage equals raw coverage in both eras", r78),
    (R / "sec4_3_7_8_pool116_redundancy.json", "4.3.8", "Pool redundancy: primary keep 15 (14 raw, 1 adjusted) / drop 15; RAW sensitivity keep 68 (58 raw, 10 adjusted) / drop 48", "N2; no undefined correlations", r78),
    (R / "sec4_3_7_8_pool116_matrix.csv", "4.3.9", "Pool matrix, 116 rows, eligibility and redundancy outcome per set", "N2", r78),
    (r78, "4.3.7 / 4.3.8", "Pool run: 4.3.7 PASS, 4.3.8 PASS", "TRAIN only, RAW then LEGACY", None),
    (cladd, "4.3", "Closing report addendum: pool results added; closing report unchanged", "Pool-rule item under 'decisions not taken' done under N2", None),
]
for e in E: assert rel(e[0]) in tracked, rel(e[0])
rows = []
for f, sec, dec, why, dfile in E:
    rows.append((date_of(dfile or f), sec, dec, why, rel(f), sha(f)))
rows.sort(key=lambda r: r[0] if len(r[0]) > 10 else r[0] + "T00:00:00")

# limitations, verbatim from the documents' own lists
lim = []
def add_lim(path, key, label=None):
    d = load(path)
    for t in d[key] if isinstance(d[key], list) else [d[key]]:
        lim.append((rel(path), sha(path), t))
add_lim(cl431, "known_limitations"); add_lim(cl43, "known_limitations"); add_lim(cladd, "known_limitations")
add_lim(p1, "limits"); add_lim(appr, "not_resolved_by_this_approval"); add_lim(n1, "not_done")

# open items
audit_def = load(a3)["timing"]["prior_run_found_4_3_2_4_3_3"]["deferred_in_that_audit"]
audit_sha = load(a3)["timing"]["prior_run_found_4_3_2_4_3_3"]["sha256"]
ten = [
    ("Which below-floor outputs to keep, drop or re-window", [cl431, cl43, a3]),
    ("The overnight analysis (response side) and its specification", [cl431, cl43, a3, n1]),
    ("Reconciling A1's 60-minute lookback and 5-session embargo with A2/A3", [cl43, appr]),
    ("Any detector, scaler or HMM fit", [cl431, cl43, a3]),
    ("Legacy timing sensitivity (-1/0/+1 minute)", [cl431, cl43, v2]),
    (audit_def[0], [a3]), (audit_def[1], [a3]), (audit_def[2], [a3]), (audit_def[3], [a3]), (audit_def[4], [a3]),
]
a1_req = load(a1)["required_before_finalizing"]

L = ["# METHODS_LEDGER", "", f"Generated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} | repository HEAD before this commit `{head}` | scope: Section 4.3 (4.3.0-4.3.9)", "",
     "## 1. Chronology", "", "| Date (UTC) | Section | Decision | Rationale | File | SHA-256 |", "|---|---|---|---|---|---|"]
L += [f"| {fmt(d)} | {esc(s)} | {esc(dec)} | {esc(w)} | {esc(f)} | `{h}` |" for d, s, dec, w, f, h in rows]
L += ["", "## 2. Limitations (verbatim from the documents)", "", "| # | Limitation | Source | SHA-256 |", "|---|---|---|---|"]
L += [f"| {i} | {esc(t)} | {esc(f)} | `{h}` |" for i, (f, h, t) in enumerate(lim, 1)]
L += ["", "## 3. Open items for Section 5", "",
      "List of 10 derived from the repository: no document defines a list of 10 postponed items. Derived by merging the 'decisions not taken' and 'deferred' lists; confirmed by the repository owner in the working session.", "",
      "| # | Item | Status | Source file(s) | SHA-256 |", "|---|---|---|---|---|"]
for i, (item, srcs) in enumerate(ten, 1):
    if i >= 6:
        audit_f = FZ / "audit_4_3_2_4_3_3_report.json"
        assert sha(audit_f) == audit_sha, "audit report copy differs from the hash quoted in A3"
        files, hashes = f"{rel(a3)}; {rel(audit_f)} (deferred list)", f"`{sha(a3)}`; `{sha(audit_f)}`"
    else:
        files, hashes = "; ".join(rel(s) for s in srcs), "; ".join(f"`{sha(s)}`" for s in srcs)
    L.append(f"| {i} | {esc(item)} | open | {esc(files)} | {hashes} |")
L += ["", "### Other open items recorded in the documents", "", "| # | Item | Status | Source file | SHA-256 |", "|---|---|---|---|---|"]
for j, t in enumerate(a1_req, 1):
    L.append(f"| A1.{j} | {esc(t)} (A1 required_before_finalizing) | not verified | {esc(rel(a1))}; {esc(rel(appr))} | `{sha(a1)}`; `{sha(appr)}` |")
L += ["", "### Items open earlier and done since", "", "| Item | Status | Source file | SHA-256 |", "|---|---|---|---|",
      f"| Redundancy and eligibility rules for the 116-column pool | done | {rel(n2)}; {rel(r78)}; {rel(cladd)} | `{sha(n2)}`; `{sha(r78)}`; `{sha(cladd)}` |"]
out = ROOT / "METHODS_LEDGER.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
(ROOT / "METHODS_LEDGER.sha256").write_text(f"{sha(out)}  {out.name}\n", encoding="ascii")
print(out.name, sha(out), "| chronology rows:", len(rows), "| limitations:", len(lim), "| open items:", len(ten), "+", len(a1_req))
