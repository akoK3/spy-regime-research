#!/usr/bin/env python3
"""A4 F1: regenerate the nested development folds from TRAIN sessions only, per era, with the same protocol rules as
audit_and_freeze.py lines 149-166 (frozen v2 nested_development): outer blocks start at TRAIN session 252 and advance 126;
a block with fewer than 63 sessions is dropped as a terminal fragment; inner train 189 + inner validation 63 sessions just before
the outer block. Asserts that no fold touches an EMBARGO, EVALUATION_EXPOSED or EXCLUDED session. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"
MANIFEST_SHA = "e87c0f9c2be93a052cd371d408072723b98f5ebf165c70bc9d94a2f70eb346ae"
FOLD_CSV, FRAG_JSON, CHECK_JSON = R / "a4_development_nested_folds_TRAIN.csv", R / "a4_development_terminal_fragments_TRAIN.json", R / "a4_folds_check.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not any(p.exists() for p in (FOLD_CSV, FRAG_JSON, CHECK_JSON)), "fold outputs exist; never overwrite"
    assert sha(FZ / "section430_executable_split_manifest.csv") == MANIFEST_SHA
    man = pd.read_csv(FZ / "section430_executable_split_manifest.csv", dtype=str)
    folds, fragments, checks = [], [], {}
    for era in ("LEGACY", "RAW"):
        m = man[man.provider_era == era].sort_values("session_date").reset_index(drop=True)
        train_pos = m.index[m.partition == "TRAIN"]
        assert (train_pos == range(train_pos[0], train_pos[0] + len(train_pos))).all(), f"{era}: TRAIN sessions are not one contiguous block"
        days = m.loc[train_pos, "session_date"].tolist()
        pos = {d: i for i, d in enumerate(days)}
        era_folds = []
        for k, outer_start in enumerate(range(252, len(days), 126)):
            outer_end = min(outer_start + 126, len(days))
            if outer_end - outer_start < 63:
                fragments.append(dict(era=era, first_session=days[outer_start], last_session=days[-1], sessions=outer_end - outer_start, action="excluded_terminal_outer_fragment"))
                continue
            a = outer_start - 252
            era_folds.append(dict(era=era, fold=k, inner_train_first=days[a], inner_train_last=days[a + 188], inner_validation_first=days[a + 189], inner_validation_last=days[outer_start - 1],
                                  outer_development_first=days[outer_start], outer_development_last=days[outer_end - 1], inner_train_sessions=189, inner_validation_sessions=63, outer_sessions=outer_end - outer_start))
        # assertions
        non_train = set(m.loc[m.partition != "TRAIN", "session_date"])
        covered = set()
        for f in era_folds:
            for lo, hi in (("inner_train_first", "inner_train_last"), ("inner_validation_first", "inner_validation_last"), ("outer_development_first", "outer_development_last")):
                covered |= set(days[pos[f[lo]]:pos[f[hi]] + 1])
            assert pos[f["inner_train_last"]] + 1 == pos[f["inner_validation_first"]] and pos[f["inner_validation_last"]] + 1 == pos[f["outer_development_first"]]
            assert pos[f["inner_train_last"]] - pos[f["inner_train_first"]] + 1 == 189 and pos[f["inner_validation_last"]] - pos[f["inner_validation_first"]] + 1 == 63
            assert pos[f["outer_development_last"]] - pos[f["outer_development_first"]] + 1 == f["outer_sessions"]
        assert not (covered & non_train), f"{era}: folds touch non-TRAIN sessions"
        outers = [(pos[f["outer_development_first"]], pos[f["outer_development_last"]]) for f in era_folds]
        assert all(outers[i][1] + 1 == outers[i + 1][0] for i in range(len(outers) - 1)), "outer blocks are not contiguous"
        part_counts = m.groupby("partition").size().to_dict()
        checks[era] = dict(train_sessions=len(days), manifest_partitions=part_counts, folds=len(era_folds), last_outer_block_sessions=era_folds[-1]["outer_sessions"],
                           sessions_covered_by_folds=len(covered), sessions_touching_embargo_eval_excluded=len(covered & non_train), first_train=days[0], last_train=days[-1])
        folds += era_folds
    expect = {"LEGACY": (30, 116), "RAW": (4, 75)}
    for era, (n, last) in expect.items():
        assert checks[era]["folds"] == n and checks[era]["last_outer_block_sessions"] == last, f"{era}: fold counts differ from the expected {n} folds / last block {last}"
    assert not fragments, "unexpected terminal fragment"
    # comparison with the frozen v2 folds (superseded for use)
    old = pd.read_csv(FZ / "development_nested_folds_frozen_v2.csv")
    train_last = {e: checks[e]["last_train"] for e in checks}
    comparison = {}
    for era in checks:
        o = old[old.era == era]
        comparison[era] = dict(frozen_v2_folds=len(o), new_folds=checks[era]["folds"],
                               frozen_v2_folds_with_a_window_after_TRAIN_end=int((o[["inner_train_last", "inner_validation_last", "outer_development_last"]].max(axis=1) > train_last[era]).sum()),
                               frozen_v2_last_outer_date=o.outer_development_last.max(), train_last_date=train_last[era])
    pd.DataFrame(folds).to_csv(FOLD_CSV, index=False)
    FRAG_JSON.write_text(json.dumps(fragments, indent=2) + "\n", encoding="utf-8")
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A4 F1", manifest_sha256=MANIFEST_SHA, per_era=checks, comparison_with_frozen_v2=comparison,
               assertions="all held: every fold session is TRAIN; no fold touches EMBARGO/EVALUATION_EXPOSED/EXCLUDED; windows contiguous; counts as expected",
               outputs={FOLD_CSV.name: sha(FOLD_CSV), FRAG_JSON.name: sha(FRAG_JSON)}, status="PASS")
    CHECK_JSON.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    CHECK_JSON.with_suffix(".sha256").write_text(f"{sha(CHECK_JSON)}  {CHECK_JSON.name}\n", encoding="ascii")
    print(json.dumps({"per_era": checks, "comparison_with_frozen_v2": comparison}, indent=1))


if __name__ == "__main__":
    main()
