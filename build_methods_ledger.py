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
    if Path(p).suffix != ".json":  # no own timestamp: the date of the commit that added the file
        out = subprocess.run(["git", "log", "--diff-filter=A", "--format=%aI", "--", rel(p)], cwd=ROOT, capture_output=True, text=True).stdout.split()
        return out[-1]
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
cold = ROOT / "cold_audit_20261030.md"
a4, a5, n3 = g("amendment_4_3_A4_2*.json"), g("amendment_4_3_A5_2*.json"), g("note_4_3_N3_2*.json")
a4res, a5res = R / "a4_results_report.json", R / "a5_results_report.json"
f1chk, cal, a4rep, a4red, a4pi = R / "a4_folds_check.json", R / "a4_lm_threshold_calibration.json", R / "a4_sec4_3_4_7_8_report.json", R / "a4_sec4_3_8_redundancy.json", R / "a4_prefix_isolation_report.json"
cladd_audit, cladd_avail = g("section_4_3_closing_report_addendum_audit_2*.json"), g("section_4_3_closing_report_addendum_availability_2*.json")
cut5, jv5, am5 = R / "a5_train_cutoffs.json", R / "a5_jump_variation_redundancy.json", R / "a5_amihud_adjustment_check.json"
reg69, yearly, mat9, g3c = R / "a4_sec4_3_6_9_report.json", R / "a4_sec4_3_6_yearly_median_iqr.csv", R / "a4_sec4_3_9_frozen_matrix.csv", R / "a5_jump_variation_redundancy_corrected.json"
reaudit, n4, addr = ROOT / "reaudit_20261031.md", g("note_4_3_N4_2*.json"), g("section_4_3_closing_report_addendum_reaudit_2*.json")
mat9v2, n4chk, final_close = R / "a4_sec4_3_9_frozen_matrix_v2.csv", R / "n4_checks.json", g("section_4_final_closing_2*.json")
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
    (cold, "audit", "Cold audit of the repository: 12 findings, 3 high (look-ahead in the __sadj columns, frozen folds overlapping evaluation, features selected outside the folds)", "Audit text as received; the fixes follow in A4 and A5", None),
    (a4, "4.3 A4", "Amendment A4: F1 TRAIN-only folds; F2 causal 20-session seasonal baseline; F3 simulated Lee-Mykland threshold; F4 relative tolerance with mid-session cuts; F5 raw_volume, log_raw_volume and raw_volume__sadj diagnostics-only; F6 addendum; F7 cleanup", "Reasons are the audit findings #1, #2, #3, #4, #5, #6, #7, #8, #9, #10, #12; written before the fixes were run", None),
    (f1chk, "4.3 A4 F1", "Folds regenerated from TRAIN sessions only: 30 LEGACY, 4 RAW; no fold touches an embargo, evaluation or excluded session", "The frozen v2 folds (36 LEGACY, 4 RAW) had 7 LEGACY folds and 1 RAW fold with a window after TRAIN", None),
    (cal, "4.3 A4 F3", "Lee-Mykland threshold 4.6113 from 200,000 simulated no-jump sessions (95% CI 4.5998 to 4.6245), replacing 5.4667", "The old threshold flagged 0.07% of no-jump sessions against the design 1%; second-seed false-alarm rate 1.04%", None),
    (a4rep, "4.3.4 / 4.3.7 / 4.3.8 A4", "Rerun with the causal seasonal baseline and the 113-column pool (78 raw + 35 adjusted): primary pool 27, keep 19 / drop 8; RAW sensitivity pool 113, keep 83 / drop 30", "A4 F2 and F5; the 4.3.4 checks pass on 105,000 brute-force cells per era", None),
    (a4red, "4.3.8 A4", "Redundancy outcome under A4 (113-column pool)", "A3 and N2 rules unchanged; adjusted columns take positions 80 and up; raw wins ties", a4rep),
    (a4pi, "4.3.1 A4 F4", "Prefix and isolation rerun with relative tolerance (rtol 1e-9, atol 0) and mid-session cuts: PASS in RAW and LEGACY; the power check detects all 81 features", "Audit #8 and #9; run per era with features spilled to float64 files", None),
    (cladd_audit, "4.3", "Addendum: audit #3, #4, #6 disclosed and #7 corrected; closed reports unchanged", "Features selected on all of TRAIN; era-crossing decisions; two of three delay checks cannot fail; the builder built LEGACY 2019-2022 and the RAW embargo days", None),
    (a5, "4.3 A5", "Amendment A5: G1 record the TRAIN cutoffs; G2 disclose the circular availability check; G3 scale the bipower term of jump_variation by w/(w-1); G4 Amihud adjustment check (report only); G5 rv10 replaces rv15 in the comparison tiers", "Audit item 11 and the repository owner's approval of rv10; written before the items were run", None),
    (cut5, "4.3 A5 G1", "TRAIN cutoffs recorded from the manifest: LEGACY 2003-01-02 to 2018-12-21, RAW 2022-03-07 to 2024-12-23; equal to CONFIG in step 3", "The dates were hardcoded and in no frozen document; the manifest is a derived artifact, not approved", None),
    (jv5, "4.3.8 A5 G3", "jump_variation_w: bipower term scaled by w/(w-1); bias check passes; RAW sensitivity redundancy unchanged (keep 83 / drop 30)", "The unscaled output was biased upward by about one bar-variance without jumps", None),
    (am5, "4.3 A5 G4", "LEGACY dividend-adjustment check: rule-based reading inconclusive; price levels suggest back-adjustment (inference)", "Report only; ex-dividend gaps have opposite signs (LEGACY +0.31%, RAW -0.74%)", None),
    (n3, "4.3 N3", "Note N3: LEGACY closes appear dividend-adjusted; Section 5 must normalize Amihud (amihud_15, amihud_30, amihud_60 and their __sadj versions) per fold, fitted on training rows only", "Follows from the A5 G4 inference; requirement set by the repository owner", None),
    (cladd_avail, "4.3", "Addendum: the availability check is circular; P1 R1's availability evidence rests on it", "Audit #11; no code or data change", None),
    (a4res, "4.3 A4", "A4 results report: all seven items PASS", "Checks run live; the first F7 evaluation failed on two checker defects, corrected and recorded", None),
    (a5res, "4.3 A5", "A5 results report: G1 PASS, G2 PASS, G3 PASS, G4 report only, G5 recorded", "See the report", None),
    (n3, "4.3 N3", "(see the N3 row above)", "", None),
    (g3c, "4.3.8 A5 G3 correction", "G3 redundancy repeated with the coverage of the current data: RAW sensitivity outcome unchanged (keep 83 / drop 30); jump_variation_15/30/60__sadj RAW coverage fell from 86.8 / 80.6 / 72.3% to 55.8 / 61.2 / 61.5%", "Step 13 ranked columns with the A4-run coverage; after the w/(w-1) scaling about half of the jump_variation values are exactly 0, so the adjusted versions are undefined where the baseline median is 0", None),
    (yearly, "4.3.6 A4", "4.3.6 regenerated for the 113-column pool: 2,147 rows (19 era-years x 113 columns), descriptive", "A4 definitions (causal seasonal baseline) and A5 jump_variation; TRAIN only", reg69),
    (mat9, "4.3.9 A4", "4.3.9 frozen matrix regenerated: 113 rows, primary view 27 rows (keep 19 / drop 8), sensitivity view 113 rows (keep 83 / drop 30)", "Outcomes from the A4 rerun (primary) and the corrected A5 G3 rerun (RAW sensitivity); coverage recomputed from the 4.3.6 data", reg69),
    (reg69, "4.3.6 / 4.3.9 A4", "4.3.6 and 4.3.9 regeneration report: 4.3.9 PASS on all checks", "The first matrix failed the coverage cross-check (A5 G3 side effect); rebuilt from the kept 4.3.6 file", None),
    (reaudit, "audit", "Re-audit at HEAD 9025958: of the 12 earlier findings 6 resolved, 3 disclosed, 3 mixed; 11 new problems, none High", "Audit text as received; the final Section 4 pass follows in N4", None),
    (n4, "4.3 N4", "Note N4: D1 P1 R2 amended (causal past-session baselines allowed; same rolling past-only rule after the embargo); D2 rv10 tier redefinition deferred to Section 5; D3 A1 'through 2024-12-31' read as the development span, the manifest TRAIN end governs training; D4 matrix regeneration recorded; fix rules for the lows", "Written before the fixes; reasons are the re-audit's new #1, #3, #4, #5, #6, #7, #10, #11", None),
    (mat9v2, "4.3.9 N4 L5", "4.3.9 frozen matrix v2: relative_volume20__sadj warmup corrected to session 20, reach 40 sessions; only that row differs from the base matrix", "Data check: first defined session is 10 for relative_volume20 and 20 for relative_volume20__sadj in both eras", n4chk),
    (addr, "4.3", "Addendum: re-audit disclosures (jump_variation still biased, matrix regenerated without an amendment, Lee-Mykland fat tails, visibility_ok by construction, stale sentences) and the lows fixed (warmup, hash lists, paths, housekeeping)", "Facts computed or read from files; the closed reports are unchanged", None),
    (n4chk, "4.3 N4", "N4 checks: L5, L6, L7, L11 PASS; 8 hash-list mismatches and 10 reports older than a producing script listed", "Old hash lists are not edited", None),
    (final_close, "4", "Section 4 final closing record: SECTION_4_CLOSED", "Scope 4.3.0-4.3.9 with A1 to A5 and N1 to N4; 4.1/4.2 text not provided; Section 5 open items not resolved", None),
]
E = [e for e in E if e[2] != "(see the N3 row above)"]
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
_aud = load(cladd_audit)
for _x in _aud["disclosures"]:
    lim.append((rel(cladd_audit), sha(cladd_audit), f"{_x['finding']} {_x['statement']} " + " ".join(_x["facts"])))
lim.append((rel(cladd_audit), sha(cladd_audit), f"{_aud['correction']['finding']} {_aud['correction']['statement']} Corrected statement: {_aud['correction']['corrected_statement']}"))
add_lim(cladd_avail, "facts"); add_lim(a4res, "history"); add_lim(a4res, "not_addressed"); add_lim(a5res, "notes"); add_lim(n3, "not_done")
_g4 = next(i for i in load(a5res)["items"] if i["item"].startswith("4 G4"))
lim.append((rel(a5res), sha(a5res), "G4: " + _g4["detail"]))
lim.append((rel(a5res), sha(a5res), "G3: " + next(i for i in load(a5res)["items"] if i["item"].startswith("3 G3"))["detail"]))
_g3c = load(g3c)
lim.append((rel(g3c), sha(g3c), "G3 correction: " + _g3c["reason"]))
lim.append((rel(g3c), sha(g3c), f"Share of exactly-zero values among finite RAW values after the A5 scaling: {_g3c['share_of_exactly_zero_values_among_finite_RAW']}. RAW coverage changes: " + "; ".join(f"{k} {v['A4_run']} -> {v['now']}" for k, v in _g3c["coverage_changes_RAW"].items())))
add_lim(reg69, "history")
_ra = load(addr)
for _x in _ra["disclosures"]:
    lim.append((rel(addr), sha(addr), f"{_x['finding']} {_x['statement']} " + " ".join(f.strip() for f in _x["facts"])))
add_lim(n4, "not_addressed_in_this_pass")
# the false sentence of the closed report is kept verbatim but is marked as superseded
lim = [(f, h, (t + f" [SUPERSEDED: false as worded; corrected in Correction #7 of {cladd_audit.name}]") if "never in an audited or analysed span" in t else t) for f, h, t in lim]

# open items
audit_def = load(a3)["timing"]["prior_run_found_4_3_2_4_3_3"]["deferred_in_that_audit"]
audit_sha = load(a3)["timing"]["prior_run_found_4_3_2_4_3_3"]["sha256"]
ten = [
    ("Which below-floor outputs to keep, drop or re-window", [cl431, cl43, a3]),
    ("The overnight analysis (response side) and its specification", [cl431, cl43, a3, n1]),
    ("Reconciling A1's 60-minute lookback and 5-session embargo with A2/A3 (N4 D1 settles the rule for cross-session baselines; the within-session lookback part remains)", [cl43, appr, n4]),
    ("Any detector, scaler or HMM fit", [cl431, cl43, a3]),
    ("Legacy timing sensitivity (-1/0/+1 minute)", [cl431, cl43, v2]),
    (audit_def[0], [a3]), (audit_def[1], [a3]), (audit_def[2], [a3]), (audit_def[3], [a3]), (audit_def[4], [a3]),
]
a1_req = load(a1)["required_before_finalizing"]

L = ["# METHODS_LEDGER", "", f"Generated {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%SZ')} | repository HEAD before this commit `{head}` | scope: Section 4.3 (4.3.0-4.3.9) | status: SECTION_4_CLOSED (record `{final_close.name}`, SHA-256 `{sha(final_close)}`)", "",
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
added = [
    ("Normalize amihud_15, amihud_30, amihud_60 and their __sadj versions per fold in Section 5, fitting any statistic on the fold's training rows only (LEGACY closes appear dividend-adjusted)", [n3, a5res, am5]),
    ("Independent confirmation of the dividend-adjustment status of the LEGACY closes (A5 G4 was an inference)", [am5, a5res]),
    ("Recompute the 4.3.7 and 4.3.8 selection inside each fold (audit #3 disclosure; the A4 selection is still on all of TRAIN)", [cladd_audit, a4res]),
    ("Decide the treatment of jump_variation_w and jump_variation_w__sadj after the A5 scaling: about half of the raw values are exactly 0 and the adjusted versions lost coverage (RAW 55.8 to 61.5%)", [g3c, reg69]),
    ("Audit #9: the look-ahead probe in step4_extract_parameters.py (last session only, 6 bars ahead)", [a4res]),
    ("Redefine the comparison tiers in Section 5 (N4 D2 defers the A5 G5 rv10 swap): the rv15 members are below the floor, rv10_strict is dropped in both selection sets, no amended tier is complete in the primary set, and in the RAW sensitivity set only sampled60 keeps every member", [n4, a5, a5res]),
    ("Re-audit new #8: F4 ran on an earlier step 3 hash and the G3 change also touched section431_additions.py; the F4 report hashes only step 3", [reaudit, n4]),
    ("Re-audit new #9: the bipower_w reading of A5 G3 (scale only the term inside jump_variation_w) was never confirmed", [reaudit, n4, a5]),
    ("Audit #4: no Section 5 item existed for the era-crossing decisions (coverage and redundancy combine the two eras in one decision)", [cladd_audit, reaudit]),
    ("Audit #8 residual: ATOL=1e-10 remains in step3_all_in_one.py, so Step 3 itself keeps the absolute-tolerance blind spot", [reaudit, n4]),
]
L += ["", "### Open items added after the list of 10 was derived", "", "| # | Item | Status | Source file(s) | SHA-256 |", "|---|---|---|---|---|"]
for j, (item, srcs) in enumerate(added, 1):
    L.append(f"| N.{j} | {esc(item)} | open | {esc('; '.join(rel(s) for s in srcs))} | {'; '.join('`' + sha(s) + '`' for s in srcs)} |")
L += ["", "### Other open items recorded in the documents", "", "| # | Item | Status | Source file | SHA-256 |", "|---|---|---|---|---|"]
for j, t in enumerate(a1_req, 1):
    L.append(f"| A1.{j} | {esc(t)} (A1 required_before_finalizing) | not verified | {esc(rel(a1))}; {esc(rel(appr))} | `{sha(a1)}`; `{sha(appr)}` |")
L += ["", "### Items open earlier and done since", "", "| Item | Status | Source file | SHA-256 |", "|---|---|---|---|",
      f"| Redundancy and eligibility rules for the 116-column pool | done (superseded by the A4 rerun on the 113-column pool) | {rel(n2)}; {rel(r78)}; {rel(cladd)} | `{sha(n2)}`; `{sha(r78)}`; `{sha(cladd)}` |"]
for _item, _status, _srcs in (
    ("Frozen folds overlapping the evaluation block (audit #2): regenerated from TRAIN only", "done", [f1chk, a4]),
    ("Lee-Mykland threshold on the wrong scale (audit #5): calibrated by simulation", "done", [cal, a4]),
    ("Seasonal adjustment using later years (audit #1): causal 20-session baseline", "done", [a4rep, a4]),
    ("Prefix and isolation tolerance and cut positions (audit #8, #9 prefix/isolation part)", "done", [a4pi, a4]),
    ("raw_volume diagnostics-only conflict (audit #10): raw_volume, log_raw_volume, raw_volume__sadj out of the detector set", "done", [a4rep, a4]),
    ("rv10 in place of rv15 in the comparison tiers (audit #10)", "approved (tiers still contain below-floor members)", [a5]),
    ("TRAIN cutoffs in no frozen document (audit #11)", "recorded (manifest is a derived artifact)", [cut5, a5]),
    ("jump_variation upward bias (audit #11)", "done", [jv5, a5]),
    ("Disclosures #3, #4, #6, #7 and the availability-check circularity (audit #11)", "done", [cladd_audit, cladd_avail]),
    ("Reproducibility and record-keeping gaps (audit #12)", "done", [a4res]),
    ("4.3.6 adjusted rows and the 4.3.9 matrix under the A4 seasonal definition", "done (regenerated for the 113-column pool)", [yearly, mat9, reg69]),
    ("A5 G3 redundancy ranked with stale coverage", "corrected (same outcome)", [g3c]),
    ("P1 R2 contradicted by the causal baselines (re-audit new #1)", "done (R2 amended by N4 D1; the P1 file is not edited)", [n4]),
    ("A1 'through 2024-12-31' versus the RAW TRAIN end (re-audit new #10)", "reconciled (N4 D3: the manifest TRAIN end governs training)", [n4, cut5]),
    ("Warmup of relative_volume20__sadj (re-audit new #5)", "done (matrix v2)", [mat9v2, n4chk]),
    ("Hash lists, absolute paths, housekeeping (re-audit new #6, #7, #11)", "done (checks in N4 checks; old lists not edited)", [n4chk, addr]),
    ("Disclosures: jump_variation bias, matrix regeneration, Lee-Mykland fat tails, visibility_ok, stale sentences", "done", [addr]),
):
    L.append(f"| {esc(_item)} | {_status} | {esc('; '.join(rel(s) for s in _srcs))} | {'; '.join('`' + sha(s) + '`' for s in _srcs)} |")
out = ROOT / "METHODS_LEDGER.md"
out.write_text("\n".join(L) + "\n", encoding="utf-8")
(ROOT / "METHODS_LEDGER.sha256").write_text(f"{sha(out)}  {out.name}\n", encoding="ascii")
print(out.name, sha(out), "| chronology rows:", len(rows), "| limitations:", len(lim), "| open items:", len(ten), "+", len(a1_req))
