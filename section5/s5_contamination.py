#!/usr/bin/env python3
"""A8 item 2: mechanical contamination list. Registry of every script that loads data, with the era/fold/segments it used (embargo sessions included: segments are taken
before the 5-session embargo drop), plus date-level exposures (D6 FOMC and shock dates). Folds whose post-embargo TEST segment intersects the list are excluded from confirmatory H1.
Session days per era come from section5/results/session_days.json (built once from the TRAIN panels by `build_days`).
Usage: s5_contamination.py build_days | list"""
import sys, json
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
    "s5_d6.py": "DATES", "s5_d6_flash.py": "DATES",
    "s5_lib.py": "LIBRARY", "s5_fast.py": "LIBRARY", "s5_contamination.py": "LIBRARY", "s5_tests.py": "LIBRARY",
}
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
        if spec == "LIBRARY": continue
        if spec == "DATES":
            for x in list(fomc_days) + SHOCK_DAYS:
                for e, ds in days_by_era.items():
                    if x in set(ds): out[e].setdefault(x, []).append(script)
            continue
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
    out = {}
    for era in ("LEGACY", "RAW"):
        d = L.load_era(era, ["return_1m"]); out[era] = [str(d["day"][i]) for i in d["first"]]; del d
    (RES / "session_days.json").write_text(json.dumps(out)); print({k: len(v) for k, v in out.items()})


def main():
    days = json.loads((RES / "session_days.json").read_text()); ft = folds_table(); tch = touched(days, fomc_days(), ft=ft); ex = exclusions(days, tch, ft)
    # same, without the D6 date exposures (registry segments only), for information
    reg_only = {k: v for k, v in REGISTRY.items() if v != "DATES"}; tch_reg = touched(days, [], reg_only, ft); ex_reg = exclusions(days, tch_reg, ft)
    res = dict(rule="fold excluded from confirmatory H1 if its post-embargo test segment intersects a touched session (A8 item 2)", folds=ex, n_folds=len(ex), n_excluded=sum(e["excluded"] for e in ex),
               uncontaminated=[(e["era"], e["fold"]) for e in ex if not e["excluded"]],
               information_registry_segments_only_excluded=[(e["era"], e["fold"]) for e in ex_reg if e["excluded"]],
               touched_sessions={e: len(v) for e, v in tch.items()}, touched_detail={e: {k: sorted(set(r)) for k, r in v.items()} for e, v in tch.items()})
    (RES / "contamination_list.json").write_text(json.dumps(res, indent=1)); print({k: v for k, v in res.items() if k != "touched_detail" and k != "folds"})


if __name__ == "__main__":
    {"build_days": build_days, "list": main}[sys.argv[1]]()
