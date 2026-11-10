#!/usr/bin/env python3
"""A8 item 2: mechanical contamination list. Registry of every script that loads data, with the era/fold/segments it used (embargo sessions included: segments are taken
before the 5-session embargo drop), plus date-level exposures (D6 FOMC and shock dates). Folds whose post-embargo TEST segment intersects the list are excluded from confirmatory H1.
Session days per era come from section5/results/session_days.json (built once from the TRAIN panels by `build_days`).
Usage: s5_contamination.py build_days | list"""
import sys, re, json
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; ROOT = HERE.parent
FOLDS = ROOT / "section431_step3_all_in_one_results" / "a4_development_nested_folds_TRAIN.csv"
EMBARGO = 5
ALL = ("train", "val", "test"); RAW3 = [("RAW", 3, ALL)]; L29 = [("LEGACY", 29, ALL)]
# script -> list of (era, fold, segments touched). Scripts that define functions only, or whose era/fold comes from the caller, are 'LIBRARY' (touch nothing themselves).
REGISTRY = {
    "diag_pilot_fa.py": RAW3, "s5_a6.py": RAW3, "s5_a7.py": RAW3, "s5_a7_sweep.py": RAW3, "s5_bench.py": RAW3, "s5_cusum.py": RAW3, "s5_d2.py": RAW3, "s5_d2_stable.py": RAW3,
    "s5_d3.py": RAW3, "s5_d5c.py": RAW3, "s5_extreme.py": RAW3, "s5_fixes.py": RAW3, "s5_pilot.py": RAW3,
    "s5_legacy_pilot.py": L29, "s5_legacy_resume_check.py": L29,
    "s5_a8_gate.py": [("RAW", 3, ("train", "val")), ("LEGACY", 29, ("train", "val"))],      # validation days only; no test segment
    "s5_d6.py": "DESCRIPTIVE", "s5_d6_flash.py": "DESCRIPTIVE",   # A8.2: D6 ran no detector/model; its dates are not contamination
    "s5_lib.py": "LIBRARY", "s5_fast.py": "LIBRARY", "s5_contamination.py": "LIBRARY", "s5_tests.py": "LIBRARY",
    # A15 rule 3: scripts the earlier pattern missed, and backend-mediated loaders
    "s5_a8_gate_seeds.py": [("RAW", 3, ("train", "val")), ("LEGACY", 29, ("train", "val"))],      # A8.3, validation days only
    "s5_a8_loo.py": [("LEGACY", 29, ("train", "val"))],                                            # A8.4, validation days only
    "s5_machinery_run.py": RAW3 + L29, "s5_rehearsal.py": RAW3 + L29, "s5_a14_diag.py": [("RAW", 3, ("train",)), ("LEGACY", 29, ("train",))],
    "s5_backend.py": "LIBRARY", "s5_era_threshold.py": "LIBRARY", "s5_main.py": "MAIN_RUN", "s5_main_run.py": "MAIN_RUN",
    "s5_a17.py": "POST_MAIN_RUN", "s5_a18.py": "POST_MAIN_RUN", "s5_tests_a17_a18.py": "LIBRARY",      # A17 rule 6
    "s5_mr2.py": "MAIN_RUN",      # A20 rule 5: MR2 and its A17-style / D7 phases (preflight on the contaminated RAW 3 and LEGACY 29 only)
    "s5_d7_diag_raw3.py": RAW3,      # D7 diagnostic on the contaminated RAW 3 fold only (already excluded)
    "s5_step2.py": "POST_MAIN_RUN", "s5_tests_step2.py": "LIBRARY",
    "s5_a22.py": "POST_MAIN_RUN", "s5_tests_a22.py": "LIBRARY",      # A22: 5.11 power, 5.10 robustness on MR2, A18 rerun on A20 inputs (preflight on RAW 3 and LEGACY 29 only)
    "s5_a23.py": "POST_MAIN_RUN", "s5_tests_a23.py": "LIBRARY",      # A23: EXPLORATORY combined rv10_partial90__sadj + relative_volume20 model (preflight on RAW 3 and LEGACY 29 only)
    "s5_a24_clock.py": "POST_MAIN_RUN", "s5_tests_a24.py": "LIBRARY",      # A24: LEGACY clock -1/0/+1 min, H1(c) from stored alarms
    "s5_a25_delay.py": "POST_MAIN_RUN", "s5_tests_a25.py": "LIBRARY",      # A25: O9 M1 fix, LEGACY delay scored by data time used (preflight on LEGACY 29 only)
    "s5_a27_confirm.py": "POST_MAIN_RUN", "s5_tests_a27.py": "LIBRARY",      # A27: confirmation-count sensitivity, development folds only (preflight on RAW 3 / LEGACY 29)
    "s5_posthoc_a25_abs.py": "POST_MAIN_RUN",      # post hoc, descriptive: absolute H1(a) pAUC at the A25 delays (LEGACY confirmatory folds)
    "s5_break_export.py": "POST_MAIN_RUN", "s5_tests_freeze_prep.py": "LIBRARY",      # freeze prep: SPY break export of the development test segments (A28 inputs)
    "s5_amendment_manifest.py": "LIBRARY", "s5_eval_loader.py": "LIBRARY",      # freeze prep: A26 2b amendment list; guarded panel readers (development / evaluation)
    # FABLE_AUDIT M4 (2026-11-10): Section 6 (AMENDMENT_A28 / A29). Development data only through s5_eval_loader.load_development; evaluation only through load_eval after the freeze.
    "section6/s6_lib.py": "LIBRARY", "section6/s6_run.py": "POST_MAIN_RUN", "section6/s6_coverage.py": "LABEL_FREE", "section6/s6_power.py": "LABEL_FREE",
    "section6/s6_synth_validation.py": "LIBRARY", "section6/s6_fingerprint.py": "LIBRARY", "section6/s6_tests.py": "LIBRARY",
    "s5_power_observed_n.py": "POST_MAIN_RUN",      # O9 L1: H1(a) MDE with the observed 22 folds
    "s5_posthoc_grid_pauc.py": "POST_MAIN_RUN",      # post hoc, descriptive: absolute H1(a) pAUC feature and baseline, 1-min vs 5-min (A22 3g setups)
    "s5_d7_nan_diag.py": "LABEL_FREE",      # post hoc: why D7 (A21) found undefined variance ratios on 47 LEGACY days; no detector, no outcome
    "s5_preflight_data_hashes.py": "LABEL_FREE",      # audit-1 #17: SHA-256 of input data files against recorded hashes; no detector, no outcome
    "s5_d8c.py": "DESCRIPTIVE",      # A22 rule 1: D8c overlap breakdown, same status as D8      # A21 rule 3f: Step 2 for liquidity (preflight on RAW 3 and LEGACY 29 only)
    "s5_d7.py": "POST_MAIN_RUN", "s5_tests_d7.py": "LIBRARY",      # A19 rule 2h: test segments already scored by the main run
    "s5_d8b.py": "DESCRIPTIVE",      # A19.1: D8 sensitivity, same status as D8
    "s5_d8.py": "DESCRIPTIVE",      # A19 rule 1g: no detector, no model, no outcome; validation sessions already used by the main run
    "s5_tests_a11.py": "LIBRARY", "s5_tests_backend.py": "LIBRARY", "s5_tests_a15.py": "LIBRARY", "s5_tests_a16.py": "LIBRARY",
    # A15 rule 2: the first cold audit (section5_cold_audit.md; scripts in that audit's scratchpad, not in the repository)
    "cold_audit_1/x5_robust.py": [("LEGACY", 25, ("train", "val")), ("LEGACY", 29, ("train", "val")), ("RAW", 3, ("train", "val"))],   # detectors fitted and scored
    "cold_audit_1/x4_placebo.py": [("RAW", 3, ("train", "val")), ("LEGACY", 29, ("train", "val"))],
    "cold_audit_1/x3_events.py": [("RAW", 3, ("train", "val")), ("LEGACY", 29, ("train", "val"))],
    "cold_audit_1/x1_folds.py": "LABEL_FREE", "cold_audit_1/x1b.py": "LABEL_FREE", "cold_audit_1/x2_causal.py": "LABEL_FREE",     # counts, splice specs, features; no detector
}
# A15 rule 6d: LABEL_FREE = no detector or regime model, no outcome (counts, splice specs, feature or preprocessing computation); MAIN_RUN = the run the list protects.
NOT_TOUCHING = ("LIBRARY", "DESCRIPTIVE", "LABEL_FREE", "MAIN_RUN", "POST_MAIN_RUN")      # A17 rule 6: POST_MAIN_RUN = analyses of the main run's folds after the H1 fold scores
# A15 rule 3: data loading = these calls; a plain raw string, no control characters (the pattern before A15 held two backspace bytes and matched nothing).
DATA_LOAD = re.compile(r"\b(?:fold_segments|load_era|era_context|splice_batch|DataBackend|EraBackend|MainBackend|load_development|load_eval)\(|\b(?:D2|F|s5_d2|s5_fast)\._init\b|canonical_panel_|\bPANELS\b")      # A16 rule 3; FABLE_AUDIT M4 (2026-11-10): the guarded panel loaders and any direct reference to the canonical panels


SCAN = ((HERE, ""), (HERE.parent / "section6", "section6/"))      # FABLE_AUDIT M4: Section 6 scripts are scanned too (registry keys "section6/<name>")


def unregistered(folder=None, registry=REGISTRY):
    """Scripts (writer scripts excepted) that load data but are not in the registry: in `folder` if given (keys = file names), else in every SCAN folder."""
    scan = SCAN if folder is None else ((Path(folder), ""),)
    return sorted(pre + f.name for d, pre in scan if Path(d).exists() for f in Path(d).glob("*.py")
                  if not f.name.startswith("write_") and DATA_LOAD.search(f.read_text(encoding="utf-8", errors="ignore")) and pre + f.name not in registry)


def check_registry(folder=None, registry=REGISTRY):
    bad = unregistered(folder, registry)
    if bad: raise AssertionError(f"scripts load data but are not in the contamination registry: {bad}")
    return True
SHOCK_DAYS = ["2010-05-06", "2015-08-24", "2018-02-05"]


def folds_table():
    return pd.read_csv(FOLDS)


def segment_days(days, row, seg):
    a, b = {"train": ("inner_train_first", "inner_train_last"), "val": ("inner_validation_first", "inner_validation_last"), "test": ("outer_development_first", "outer_development_last")}[seg]
    return [x for x in days if str(row[a]) <= x <= str(row[b])]


def test_days_after_embargo(days, row):
    return segment_days(days, row, "test")[EMBARGO:]


def touched(days_by_era, fomc_days, registry=REGISTRY, ft=None):
    """-> {era: {day: [reasons]}}"""
    ft = folds_table() if ft is None else ft; out = {e: {} for e in days_by_era}
    for script, spec in registry.items():
        if spec in NOT_TOUCHING: continue
        for era, fold, segs in spec:
            row = ft[(ft.era == era) & (ft.fold == fold)].iloc[0]
            for s in segs:
                for x in segment_days(days_by_era[era], row, s): out[era].setdefault(x, []).append(f"{script}:{s}")
    return out


def exclusions(days_by_era, tch, ft=None):
    ft = folds_table() if ft is None else ft; res = []
    for _, row in ft.iterrows():
        e = row["era"]
        if e not in days_by_era: continue
        td = test_days_after_embargo(days_by_era[e], row); hit = [x for x in td if x in tch[e]]
        res.append(dict(era=e, fold=int(row["fold"]), test_sessions=len(td), touched_in_test=len(hit), excluded=bool(hit), by_registry_segments=len([x for x in hit if any(not r.startswith("s5_d6") for r in tch[e][x])])))
    return res


def fomc_days():
    j = json.loads((RES / "d6_fomc_dates.json").read_text()); return sorted(x for v in j["scheduled_meetings_with_statement"].values() for x in v)


def build_days():
    import s5_lib as L
    out = {}; bars = {}
    for era in ("LEGACY", "RAW"):
        d = L.load_era(era, ["return_1m"]); out[era] = [str(d["day"][i]) for i in d["first"]]; bars[era] = [int(d["end"][i] - d["first"][i]) for i in range(len(d["first"]))]; del d
    (RES / "session_days.json").write_text(json.dumps(out)); (RES / "session_bars.json").write_text(json.dumps(bars)); print({k: len(v) for k, v in out.items()})


def main():
    days = json.loads((RES / "session_days.json").read_text()); ft = folds_table(); tch = touched(days, fomc_days(), ft=ft); ex = exclusions(days, tch, ft)
    # same, without the D6 date exposures (registry segments only), for information
    reg_only = {k: v for k, v in REGISTRY.items() if v != "DATES"}; tch_reg = touched(days, [], reg_only, ft); ex_reg = exclusions(days, tch_reg, ft)
    fo = fomc_days(); bars = json.loads((RES / "session_bars.json").read_text()); ok_days = {e: {x for x, b in zip(days[e], bars[e]) if b == 390} for e in days}; ev = {}; seen = set(); unavailable = []
    rtp = RES / "h1c_schedule_times.json"; rtp = rtp if rtp.exists() else RES / "h1c_release_times.json"; rt = json.loads(rtp.read_text())["meetings"] if rtp.exists() else None          # A11 item 3 / A12 item 2: stated or documented release times; ambiguous meetings excluded
    for r in sorted(ex, key=lambda r: (r["era"], r["fold"])):
        if r["excluded"]: continue
        row = ft[(ft.era == r["era"]) & (ft.fold == r["fold"])].iloc[0]; cand = [x for x in test_days_after_embargo(days[r["era"]], row) if x in set(fo) and x in ok_days[r["era"]] and x not in seen]
        if rt is not None:
            unavailable += [x for x in cand if rt.get(x, {}).get("status") != "time"]; cand = [x for x in cand if rt.get(x, {}).get("status") == "time"]
        seen.update(cand); ev[f"{r['era']}{r['fold']}"] = cand
    minutes = {x: rt[x]["minute_after_0930"] for v in ev.values() for x in v} if rt is not None else None
    res = dict(h1c_eligible_events_per_fold=ev, n_h1c_events=sum(len(v) for v in ev.values()), h1c_event_release_minute_after_0930=minutes, h1c_excluded_release_time_unavailable=sorted(unavailable), n_h1c_excluded_release_time_unavailable=len(unavailable), rule="fold excluded from confirmatory H1 if its post-embargo test segment intersects a touched session (A8 item 2)", folds=ex, n_folds=len(ex), n_excluded=sum(e["excluded"] for e in ex),
               uncontaminated=[(e["era"], e["fold"]) for e in ex if not e["excluded"]],
               information_registry_segments_only_excluded=[(e["era"], e["fold"]) for e in ex_reg if e["excluded"]],
               touched_sessions={e: len(v) for e, v in tch.items()}, touched_detail={e: {k: sorted(set(r)) for k, r in v.items()} for e, v in tch.items()})
    (RES / "contamination_list.json").write_text(json.dumps(res, indent=1)); import s5_guard as G; G.write_side(RES / "contamination_list.json")      # A16 rule 2: sidecar; protocol 5.14 must state the hash
    print({k: v for k, v in res.items() if k != "touched_detail" and k != "folds"})


if __name__ == "__main__":
    {"build_days": build_days, "list": main}[sys.argv[1]]()
