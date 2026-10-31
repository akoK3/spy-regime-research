#!/usr/bin/env python3
"""Records for amendments A4 and A5: the G2 addendum (availability-check circularity), the A4 results report and the A5 results report.
Everything is read from files or checked live (F7 text checks, syntax checks, hash comparisons, the Step 3 formula check on the current code).
Closed reports are not edited. Refuses to overwrite."""
import ast, json, hashlib, datetime, re, sys
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
SRC = ROOT / "section431_step3_verification" / "prototype_sources"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def side(path, name):
    path.with_suffix(".sha256").write_text(f"{sha(path)}  {path.name}\n", encoding="ascii") if name == "single" else None


def write_pair(stem, doc, md_lines):
    jp, mp = R / f"{stem}.json", R / f"{stem}.md"
    assert not jp.exists(), f"{jp.name} exists; never overwrite"
    jp.write_bytes((json.dumps(doc, indent=2, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    mp.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    (R / f"{stem}.sha256").write_text(f"{sha(jp)}  {jp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    return jp


def now():
    n = datetime.datetime.now(datetime.timezone.utc)
    return n, n.strftime("%Y%m%dT%H%M%SZ"), pd.Timestamp(n).tz_convert("America/New_York").isoformat()


def main():
    a4, a5, audit = one("amendment_4_3_A4_2*.json"), one("amendment_4_3_A5_2*.json"), ROOT / "cold_audit_20261030.md"
    a4d = load(a4)
    out = {}

    # ---------------- G2 addendum (A5)
    text = (SRC / "section4_3_1_candidates.py").read_text(encoding="utf-8")
    fn = next(n for n in ast.walk(ast.parse(text)) if isinstance(n, ast.FunctionDef) and n.name == "load_development")
    seg = ast.get_source_segment(text, fn).splitlines()
    lines = [l.strip() for l in seg if "available" in l]
    cols = next(l for l in text.splitlines() if l.startswith("PANEL_COLUMNS"))
    v2 = load(FZ / "protocol_20261029T032641Z.json")
    p1 = load(one("policy_4_3_1_P1_2*.json"))
    r1 = next(r for r in p1["rules"] if r["id"] == "R1")
    circular = any("available_utc_assuming_minute_start" in l for l in lines) and any("t + MINUTE" in l for l in lines)
    n, stamp, ny = now()
    g2 = dict(status="SECTION_4_3_CLOSED (addendum; the closed reports are unchanged)", created_utc=n.isoformat(), created_america_new_york=ny,
              amends=[dict(file=one("section_4_3_closing_report_section4_2*.json").name, sha256=sha(one("section_4_3_closing_report_section4_2*.json"))), dict(file=one("policy_4_3_1_P1_2*.json").name, sha256=sha(one("policy_4_3_1_P1_2*.json")))],
              basis=dict(amendment_A5=dict(file=a5.name, sha256=sha(a5)), audit=dict(file=audit.name, sha256=sha(audit)), source=dict(file="section431_step3_verification/prototype_sources/section4_3_1_candidates.py", sha256=sha(SRC / "section4_3_1_candidates.py"))),
              finding="#11, availability check", circular_check_confirmed_from_source=circular,
              quoted_lines_of_load_development=lines, panel_columns_line=cols,
              facts=["The loader reads the availability column available_utc_assuming_minute_start and asserts that it equals the bar's minute-start stamp plus 60 seconds. The column name states the assumption it was built from, so the assertion tests the panel's own construction and cannot fail.",
                     f"Policy P1 R1 lists this assertion as its enforcement: '{r1['enforced_by']}'. The R1 evidence about availability therefore rests on the same assumption.",
                     f"The frozen protocol states the assumption as inherited: '{v2['clocks']['bar_label']}', and requires: '{v2['clocks']['legacy_sensitivity']}'.",
                     "RAW has no clock-sensitivity test; the LEGACY -1/0/+1 minute sensitivity is an open Section 5 item (ledger item 5).",
                     "Nothing in this repository tests the bar-label assumption against an independent clock."],
              no_code_or_data_change=True)
    lm = [f"# Addendum: the availability check is circular (A5 G2, audit #11)", "", "**SECTION_4_3_CLOSED** (unchanged; the closed reports are not edited)", "",
          f"Added {n.isoformat()} UTC ({ny} New York). A5 `{a5.name}` SHA-256 `{sha(a5)}`. Source `section4_3_1_candidates.py` SHA-256 `{sha(SRC / 'section4_3_1_candidates.py')}`.", "",
          "Lines of `load_development` that mention availability:", ""] + [f"    {l}" for l in lines] + ["", f"    {cols[:200]}", ""] + [f"- {f}" for f in g2["facts"]]
    out["G2"] = write_pair(f"section_4_3_closing_report_addendum_availability_{stamp}", g2, lm)

    # ---------------- live checks for F7 and the formula check
    def has(path, s): return s in (ROOT / path).read_text(encoding="utf-8")
    f7 = {
        "a_in_repository_inputs": has("step6_coverage.py", "frozen_documents") and not has("step6_coverage.py", 'ROOT / "section431_step2_final_audit"') and has("write_closing_report_4_3_1.py", 'FZ / "feature_family_eligibility_matrix.csv"') and not has("write_closing_report_4_3_1.py", 'ROOT / "section431_step2_final_audit"'),
        "b_own_temp_directory": has("step8_sections_4_3_4_to_4_3_9.py", "tempfile.gettempdir()") and not has("step8_sections_4_3_4_to_4_3_9.py", "scratchpad"),
        "c_overwrite_guards": all(has(f, "refuse_overwrite") for f in ("step3_all_in_one.py", "step4_extract_parameters.py", "step6_coverage.py", "step8_sections_4_3_4_to_4_3_9.py", "step10_pool116_eligibility_redundancy.py", "step11_a4_rerun_4_3_4_7_8.py", "step12_a4_prefix_isolation_rerun.py")),
        "d_computed_hash_check": not has("step8_sections_4_3_4_to_4_3_9.py", '"A3 hash verified": True'),
    }
    import subprocess
    tracked_py = subprocess.run(["git", "ls-files", "*.py"], cwd=ROOT, capture_output=True, text=True).stdout.split()
    tracked_py += [p.name for p in ROOT.glob("*.py") if p.name not in tracked_py and p.name.startswith(("write_a4_a5_records",))]  # this script, not yet tracked
    bad = []
    for name in tracked_py:
        try: compile((ROOT / name).read_text(encoding="utf-8"), name, "exec")
        except SyntaxError as e: bad.append(f"{name}: {e}")
    f7["scripts_compile"] = not bad
    v2h = (R / "step5_v2_final_sha256.txt").read_text().splitlines()
    mism = []
    for line in v2h:
        h, name = line.split(None, 1); name = name.strip()
        p = ROOT / name if (ROOT / name).exists() else R / name
        if sha(p) != h: mism.append(name)
    v1h = (R / "step5_final_sha256.txt").read_text().splitlines()
    v1mism = []
    for line in v1h:
        h, name = line.split(None, 1); name = name.strip()
        p = ROOT / name if (ROOT / name).exists() else R / name
        if sha(p) != h: v1mism.append(name)
    f7["e_step5_v2_hash_file_matches_current_files"] = not mism
    import step3_all_in_one as s
    fc = s.formula_all_outputs()

    # ---------------- A4 results report
    folds, cal = load(R / "a4_folds_check.json"), load(R / "a4_lm_threshold_calibration.json")
    rr, red = load(R / "a4_sec4_3_4_7_8_report.json"), load(R / "a4_sec4_3_8_redundancy.json")
    pi = load(R / "a4_prefix_isolation_report.json")
    add_audit = one("section_4_3_closing_report_addendum_audit_2*.json")
    st = rr["subsections"]
    s8 = st["4.3.8"]
    rv10 = "kept" if "rv10_strict" in red["primary"]["kept"] else ("dropped: redundant with " + red["primary"]["dropped"]["rv10_strict"][0]["kept_column"] if "rv10_strict" in red["primary"]["dropped"] else "not in the primary set")
    items = [
        ("1 F1 folds (#2)", "PASS" if folds["status"] == "PASS" else "FAIL", f"LEGACY {folds['per_era']['LEGACY']['folds']} folds, RAW {folds['per_era']['RAW']['folds']} folds from TRAIN only; sessions touching EMBARGO/EVALUATION_EXPOSED/EXCLUDED: {folds['per_era']['LEGACY']['sessions_touching_embargo_eval_excluded']} and {folds['per_era']['RAW']['sessions_touching_embargo_eval_excluded']}. The frozen v2 file had {folds['comparison_with_frozen_v2']['LEGACY']['frozen_v2_folds']} LEGACY folds ({folds['comparison_with_frozen_v2']['LEGACY']['frozen_v2_folds_with_a_window_after_TRAIN_end']} with a window after TRAIN) and {folds['comparison_with_frozen_v2']['RAW']['frozen_v2_folds']} RAW folds ({folds['comparison_with_frozen_v2']['RAW']['frozen_v2_folds_with_a_window_after_TRAIN_end']} with a window after TRAIN).", "a4_folds_check.json"),
        ("2 F2 seasonal baseline (#1): 4.3.4, 4.3.7, 4.3.8", "PASS" if rr["overall"] == "PASS" else "FAIL", f"4.3.4 {st['F2 4.3.4 causal baseline']['status']} (brute-force cells per era {st['F2 4.3.4 causal baseline']['checks']['RAW']['brute_force_cells']}, mismatches {len(st['F2 4.3.4 causal baseline']['checks']['RAW']['brute_force_mismatches']) + len(st['F2 4.3.4 causal baseline']['checks']['LEGACY']['brute_force_mismatches'])}); 4.3.7 {st['4.3.7']['status']}, primary pool {st['4.3.7']['primary_pool']}; 4.3.8 {s8['status']}: primary keep {s8['primary']['kept']} (raw {s8['primary']['kept_split']['raw']}, adjusted {s8['primary']['kept_split']['adjusted']}) / drop {s8['primary']['dropped']}; RAW sensitivity pool {s8['sensitivity_RAW']['pool']} keep {s8['sensitivity_RAW']['kept']} (raw {s8['sensitivity_RAW']['kept_split']['raw']}, adjusted {s8['sensitivity_RAW']['kept_split']['adjusted']}) / drop {s8['sensitivity_RAW']['dropped']}.", "a4_sec4_3_4_7_8_report.json"),
        ("3 F3 Lee-Mykland threshold (#5)", "PASS" if cal["check_second_seed_between_0_9_and_1_1_pct"] == "PASS" and fc["status"] == "PASS" else "FAIL", f"threshold {cal['threshold']} (95% CI {cal['ci95_rank_based'][0]:.4f} to {cal['ci95_rank_based'][1]:.4f}); false-alarm rate at the threshold {cal['false_alarm_rate_at_threshold']['seed_43105']:.4%} (seed 43105) and {cal['false_alarm_rate_at_threshold']['seed_43106']:.4%} (seed 43106); the old 5.4667 flags {cal['old_threshold_5_4667_false_alarm_rate_seed_43106']:.4%}. Step 3 formula check on the current code: {fc['status']}, {fc['formulas_verified']}/{fc['outputs_compared']}, independent simulated false-alarm rate {fc['lm_simulated_false_alarm_rate']:.4%}.", "a4_lm_threshold_calibration.json"),
        ("4 F4 tolerances and mid-session cuts (#8, #9)", pi["overall"], "; ".join(f"{t['item']}: {t['status']}" for t in pi["table"]) + f". Relative tolerance rtol 1e-9, atol 0. Run once per era in separate processes (each era with its own fixed seed) to limit memory; features were spilled to float64 files, float32 was not used because it would coarsen the tolerance.", "a4_prefix_isolation_report.json"),
        ("5 F5 protocol conflicts (#10)", "PASS" if st["F5 pool without diagnostics-only volume columns"]["status"] == "PASS" else "FAIL", f"raw_volume, log_raw_volume and raw_volume__sadj are out of the detector set; pool 78 raw + 35 adjusted = 113. The rv10 proposal is approved in amendment A5 (G5). In the A4 primary run rv10_strict is: {rv10}.", "a4_sec4_3_4_7_8_report.json"),
        ("6 F6 addendum for #3, #4, #6, #7", "PASS" if add_audit.exists() and (add_audit.with_name(add_audit.stem + ".sha256")).read_text().split()[0] == sha(add_audit) else "FAIL", f"{add_audit.name}; the closed reports are unchanged; every number is read from a file.", add_audit.name),
        ("7 F7 cleanup (#12)", "PASS" if all(f7.values()) else "FAIL", "; ".join(f"{k}: {'PASS' if v else 'FAIL'}" for k, v in f7.items()) + f". step5_final_sha256.txt (the v1 state) no longer matches: {v1mism}; step5_v2_final_sha256.txt matches all current files. The older file is left unedited.", "step5_v2_final_sha256.txt"),
    ]
    n2, stamp2, ny2 = now()
    a4doc = dict(created_utc=n2.isoformat(), created_america_new_york=ny2, amendment_A4=dict(file=a4.name, sha256=sha(a4)), audit=dict(file=audit.name, sha256=sha(audit)),
                 overall="PASS" if all(i[1] == "PASS" for i in items) else "FAIL", items=[dict(item=i[0], status=i[1], detail=i[2], evidence=i[3], evidence_sha256=sha(R / i[3]) if (R / i[3]).exists() else sha(ROOT / i[3])) for i in items],
                 history=["The first F2/F5 rerun was killed during the LEGACY feature pass (no outputs); a restart failed on this repository's own overwrite guard (a kept log matched its pattern, no analysis ran); the third attempt completed.",
                          "The first F4 attempt was stopped for low system memory; F4 was rerun per era with features spilled to disk.",
                          "A4 F7(e): step5_final_sha256.txt was left as the record of the v1 state.",
                          "The first evaluation of the F7 checks gave FAIL because of two defects in the checker, not in the code: it matched the old folder name in a text label instead of in path-building code, and it compiled an untracked unrelated file (test_431_additional_feasibility.py, with a byte-order mark). The checker was corrected (path-building code only; tracked scripts only) and the records regenerated. The A4 criterion 'each item is in place, the scripts compile, the hashes match' was not changed."],
                 not_addressed=a4d["not_addressed_in_this_pass"], step3_formula_check_current_code=dict(status=fc["status"], outputs=fc["outputs_compared"], verified=fc["formulas_verified"], lm_threshold=fc["lm_threshold"], lm_false_alarm_rate=fc["lm_simulated_false_alarm_rate"]))
    md = ["# A4 results report", "", f"Written {n2.isoformat()} UTC ({ny2} New York). A4 `{a4.name}` SHA-256 `{sha(a4)}`. Overall: **{a4doc['overall']}**.", "", "| Item | Status | Detail | Evidence |", "|---|---|---|---|"] + \
         [f"| {i[0]} | {i[1]} | {i[2].replace('|', '/')} | {i[3]} |" for i in items] + ["", "## History", ""] + [f"- {h}" for h in a4doc["history"]] + ["", "## Not addressed in this pass", ""] + [f"- {x}" for x in a4doc["not_addressed"]]
    out["A4"] = write_pair("a4_results_report", a4doc, md)

    # ---------------- A5 results report
    cut, jv, am = load(R / "a5_train_cutoffs.json"), load(R / "a5_jump_variation_redundancy.json"), load(R / "a5_amihud_adjustment_check.json")
    a5d = load(a5)
    g5 = a5d["items"]["G5_rv10_approval"]
    lv = am["ex_dividend_test"]; lev = am["price_levels"]
    a5items = [
        ("1 G1 TRAIN cutoffs", cut["status"], f"LEGACY {cut['per_era']['LEGACY']['train_first']} to {cut['per_era']['LEGACY']['train_last']} ({cut['per_era']['LEGACY']['train_sessions']} sessions); RAW {cut['per_era']['RAW']['train_first']} to {cut['per_era']['RAW']['train_last']} ({cut['per_era']['RAW']['train_sessions']} sessions); CONFIG equals the manifest in both eras. The manifest is a derived artifact, not an approved frozen document.", "a5_train_cutoffs.json"),
        ("2 G2 availability circularity", "PASS" if circular else "FAIL", f"Disclosed in {out['G2'].name} with the quoted lines of load_development.", out["G2"].name),
        ("3 G3 jump_variation scaling", jv["status"], f"Formula check on the current code {fc['status']} ({fc['formulas_verified']}/{fc['outputs_compared']}); bias check (mean of RV minus BV, simulated Gaussian windows): " + "; ".join(f"w={w}: unscaled {v['mean_RV_minus_unscaled_BV']}, scaled {v['mean_RV_minus_scaled_BV']}" for w, v in jv["bias_check"].items()) + f". RAW sensitivity redundancy: keep {jv['sensitivity_RAW']['kept']} / drop {jv['sensitivity_RAW']['dropped']} (before {jv['sensitivity_RAW']['before']['kept']} / {jv['sensitivity_RAW']['before']['dropped']}), newly kept {jv['sensitivity_RAW']['changes']['newly_kept'] or 'none'}, newly dropped {jv['sensitivity_RAW']['changes']['newly_dropped'] or 'none'}. Primary set: {jv['primary_set_status']}. F4 was not rerun for this change. Reading used: the scaling is applied to the bipower term inside jump_variation_w; the bipower_w column is unchanged.", "a5_jump_variation_redundancy.json"),
        ("4 G4 LEGACY dividend adjustment (report only)", "DONE (report only)", f"Rule-based reading: {am['reading_rule_result']}. Ex-dividend gap in the mean overnight return: LEGACY {lv['LEGACY']['gap_pct']}% (SE {lv['LEGACY']['se_pct']}%, {lv['LEGACY']['ex_dividend_sessions']} sessions, t {lv['LEGACY']['t']}); RAW {lv['RAW']['gap_pct']}% (SE {lv['RAW']['se_pct']}%, {lv['RAW']['ex_dividend_sessions']} sessions, t {lv['RAW']['t']}). The two gaps have opposite signs, and the ex-date approximation (third Friday of March, June, September, December) coincides with quarterly options expiration, so this test does not settle the question. Price levels: LEGACY first close {lev['LEGACY']['first_close']} on {lev['LEGACY']['first_session']}, last TRAIN close {lev['LEGACY']['last_close']}; junction ratio {am['junction']['ratio']} (first RAW Open {am['junction']['raw_first_open_2022_03_07']} over last LEGACY Close {am['junction']['legacy_last_close_2022_03_04']}), a normal one-day move. Inference, not established from the repository: a LEGACY close of about 62 on 2003-01-02, against a level near 90 recalled from general knowledge, and a junction ratio near 1 would both fit closes back-adjusted for dividends up to about March 2022; if so, amihud_w dollar volume is understated in early years. Nothing was changed.", "a5_amihud_adjustment_check.json"),
        ("5 G5 rv10 replaces rv15 in the tiers", "RECORDED (approved in A5)", f"Tiers after: {g5['tiers_after']}. Members still BELOW the floor: " + ", ".join(k for k, v in g5['facts']['members_of_the_amended_tiers_that_are_in_the_step6_table'].items() if v.startswith('BELOW')) + ". The frozen protocol is not edited.", a5.name),
    ]
    n3, stamp3, ny3 = now()
    a5doc = dict(created_utc=n3.isoformat(), created_america_new_york=ny3, amendment_A5=dict(file=a5.name, sha256=sha(a5)),
                 overall="PASS" if all(i[1] in ("PASS", "DONE (report only)", "RECORDED (approved in A5)") for i in a5items) else "FAIL",
                 items=[dict(item=i[0], status=i[1], detail=i[2], evidence=i[3], evidence_sha256=sha(R / i[3])) for i in a5items],
                 notes=["G4 reads one LEGACY price level (2022-03-04, EVALUATION_EXPOSED in the manifest) for the junction ratio; no return statistic from that period is computed.", "The external reference in G4 is general knowledge, not a repository file, and is unverified here."])
    md5 = ["# A5 results report", "", f"Written {n3.isoformat()} UTC ({ny3} New York). A5 `{a5.name}` SHA-256 `{sha(a5)}`. Overall: **{a5doc['overall']}**.", "", "| Item | Status | Detail | Evidence |", "|---|---|---|---|"] + \
          [f"| {i[0]} | {i[1]} | {i[2].replace('|', '/')} | {i[3]} |" for i in a5items] + ["", "## Notes", ""] + [f"- {x}" for x in a5doc["notes"]]
    out["A5"] = write_pair("a5_results_report", a5doc, md5)
    print({k: v.name for k, v in out.items()})
    print("A4:", a4doc["overall"], [(i[0][:12], i[1]) for i in items])
    print("A5:", a5doc["overall"], [(i[0][:12], i[1]) for i in a5items])
    print("F7 checks:", f7, "| step5 v1 mismatches:", v1mism)


if __name__ == "__main__":
    main()
