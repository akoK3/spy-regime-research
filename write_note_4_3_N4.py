#!/usr/bin/env python3
"""Dated, hashed note 4.3-N4: the final Section 4 pass after the re-audit. Written BEFORE the fixes are applied.
Reads only saved documents; changes nothing else. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"
FZ = ROOT / "frozen_documents"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def load(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def main():
    assert not list(R.glob("note_4_3_N4_2*.json")), "N4 exists; never overwrite"
    assert not list(R.glob("n4_*")), "N4 outputs exist; N4 must be written before its fixes are run"
    p1 = one("policy_4_3_1_P1_2*.json")
    r2 = next(r for r in load(p1)["rules"] if r["id"] == "R2")
    v2 = load(FZ / "protocol_20261029T032641Z.json")
    a1 = load(FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json")
    cut = load(R / "a5_train_cutoffs.json")
    a4red, g3c, elig = load(R / "a4_sec4_3_8_redundancy.json"), load(R / "a5_jump_variation_redundancy_corrected.json"), load(R / "a4_sec4_3_7_eligibility.json")
    status = lambda c: ("kept" if c in a4red["primary"]["kept"] else "dropped" if c in a4red["primary"]["dropped"] else "not in the primary pool", "kept" if c in g3c["kept"] else "dropped" if c in g3c["dropped"] else "not in the sensitivity pool")
    swap = {"rv15_strict": "rv10_strict", "rv15_partial90": "rv10_partial90"}
    tiers = {t: [dict(column=swap.get(c, c), primary=status(swap.get(c, c))[0], raw_sensitivity=status(swap.get(c, c))[1]) for c in cols] for t, cols in v2["comparison_tiers"].items()}
    cited = {"reaudit": ROOT / "reaudit_20261031.md", "cold_audit": ROOT / "cold_audit_20261030.md", "P1": p1, "A1": FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json",
             "A4": one("amendment_4_3_A4_2*.json"), "A5": one("amendment_4_3_A5_2*.json"), "N1": one("note_4_3_N1_2*.json"), "N2": one("note_4_3_N2_2*.json"), "N3": one("note_4_3_N3_2*.json"),
             "frozen_protocol_v2": FZ / "protocol_20261029T032641Z.json", "split_manifest": FZ / "section430_executable_split_manifest.csv", "train_cutoffs": R / "a5_train_cutoffs.json",
             "matrix_4_3_9_current": R / "a4_sec4_3_9_frozen_matrix.csv", "regeneration_report": R / "a4_sec4_3_6_9_report.json", "first_attempt_report": R / "a4_first_attempt_sec4_3_6_9_report.json"}
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "note": "4.3-N4 final Section 4 pass after the re-audit",
        "created_utc": now.isoformat(), "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "WRITTEN_BEFORE_THE_FIXES_ARE_APPLIED",
        "statement": "Fixed before any of the fixes below is applied. The reasons are the re-audit's findings (reaudit_20261031.md, at repository HEAD 9025958). Closed reports and frozen files are not edited; corrections go into addenda and new versions.",
        "cites": {k: {"file": p.name, "sha256": sha(p)} for k, p in cited.items()},
        "decisions": {
            "D1_P1_R2_amended": {
                "reaudit": "new #1", "amends": "policy P1, rule R2 (the P1 file is not edited)",
                "p1_r2_text_superseded": r2["rule"],
                "reason": "P1 R2 says relative volume is the only cross-session value and that no other detector output uses data from another session. All 35 __sadj columns cross sessions (A4 F2), six of them in the kept primary set, and nothing recorded the contradiction.",
                "new_r2": "Every window resets at the session open: a feature at slot j uses only bars of the same session at slots <= j, so the first W bars of a session are NaN. Cross-session values are allowed only as causal past-session baselines: the value for session k may use sessions earlier than k of the same era, and no later session. There are two kinds: the relative-volume baseline of relative_volume20 and log_relative_volume20 (median of positive volumes at the same slot over the previous 20 sessions, at least 10 required) and the seasonal baseline of the __sadj columns (A4 F2: median of the finite raw values at the same slot over the previous 20 sessions, at least 10 required). relative_volume20__sadj chains the two, so its first defined session is the 20th and its reach is 40 sessions. No other detector output uses data from another session.",
                "post_embargo_behavior": "After the embargo the same rolling past-only rule applies unchanged. The window is always the previous 20 sessions of the same era in date order; partition labels do not change it, so the first evaluation sessions draw on embargo and late TRAIN sessions. No statistic is fitted on evaluation data and no baseline is carried across the era boundary.",
                "scope_limit": "This settles the rule for causal baselines only. The remainder of open item 3 (A1's 60-minute lookback for within-session windows against the A2 cap) stays open.",
            },
            "D2_tier_redefinition_deferred": {
                "reaudit": "new #3", "amends": "amendment A5, item G5",
                "decision": "The replacement of rv15 by rv10 in the comparison tiers (A5 G5) is deferred to Section 5 and is not in force in Section 4. The approval of 2026-10-31 stays on record as history. The tier redefinition becomes a Section 5 open item.",
                "reason": "The swap made no tier usable. rv10_strict, now in core15 and strict60, is dropped in both selection sets.",
                "facts_from_files_amended_tiers": tiers,
            },
            "D3_A1_versus_TRAIN_end": {
                "reaudit": "new #10",
                "conflict": f"A1 says: '{a1['provider_training_limitation']}'. RAW TRAIN ends {cut['per_era']['RAW']['train_last']} and the {len(cut['per_era']['RAW']['embargo_sessions'])} sessions {cut['per_era']['RAW']['embargo_sessions'][0]} to {cut['per_era']['RAW']['embargo_sessions'][-1]} are EMBARGO in the manifest. A5 G1 recorded the cutoffs but did not flag this sentence.",
                "reconciliation": "A1's 'through 2024-12-31' describes the frozen development span of the RAW era. The training span is RAW TRAIN, 2022-03-07 to 2024-12-23. The five embargo sessions 2024-12-24 to 2024-12-31 are inside the development span and outside training, as A1's own embargo rule requires. For LEGACY the training span is TRAIN, 2003-01-02 to 2018-12-21, and 2019-01-02 onward is evaluation under A1. Where a document and the manifest differ on a training end date, the manifest's TRAIN end governs.",
                "limit": "The manifest is a derived artifact and is not approved (A1's manifest item is unverified).",
            },
            "D4_matrix_regeneration": {
                "reaudit": "new #4",
                "statement": "The 4.3.6 and 4.3.9 regeneration (steps 15 and 16) was run without a pre-run document, although A4 said these outputs were not regenerated in that pass and the regenerated report's freeze line requires a new dated amendment for any change. After the first matrix failed its coverage cross-check, the check was reworded to allow the three jump_variation__sadj differences. The failed matrix was not kept, so its recorded hash cannot be verified.",
                "authorization_after_the_fact": "This note is the dated amendment for the matrix. The matrix of the regeneration report stands as the base; the correction of D5/L5 is issued as a new version (v2) beside it. Neither the base matrix nor the 4.3.6 file is edited.",
            },
        },
        "fixes": {
            "L5_warmup": {"reaudit": "new #5", "rule": "relative_volume20__sadj has warmup session 20 (not 10), lookback 20 + 20 = 40 sessions, and a minimum-observation text that names both baselines. A v2 matrix with its primary and sensitivity views is written beside the base matrix; the builders use v2. Check: the first-defined session of relative_volume20__sadj computed from the data in the 4.3.6 file is session 20 in both eras.", "pass": "v2 differs from the base matrix only in the fields of that row; the data check holds"},
            "L6_hash_lists": {"reaudit": "new #6", "rule": "A dated check compares every hash list in the results folder with the current files. Each mismatch is listed with the commit that last changed the file. The old lists are not edited. The addendum also states which steps were and were not rerun in full on the current code.", "pass": "the check file exists and lists every mismatch"},
            "L7_paths": {"reaudit": "new #7", "rule": "The six scripts named by the re-audit read in-repository copies (frozen_documents/). REPORT.md and section431_panel_audit.json, not yet in the repository, are copied with hashes verified identical. A scan finds no OneDrive path in any tracked script.", "pass": "the scan finds no hit and the copies are identical"},
            "L11_housekeeping": {"reaudit": "new #11", "rule": "audit_and_freeze.py and amend_protocol.py are copied into frozen_documents/ with hashes equal to those recorded in the frozen protocol. .gitignore entries for scripts that do not exist are removed. The order in which F6 ran before F4 is recorded.", "order_fact": "A4 stated the order F7, F3, F1, F2+F5, F4, F6. F6 (the audit addendum) was written before F4 had run, because F4 was stopped for low memory and rerun later. No record said so.", "pass": "the files exist with matching hashes and .gitignore lists only existing scripts"},
        },
        "disclosures_to_write": ["new #2: jump_variation_w is still biased upward (the clipped feature, not RV - BV)", "new #4: the matrix regeneration without a pre-run amendment (D4)", "audit #5: the Lee-Mykland threshold was calibrated for Gaussian returns; the false-alarm rate under fat tails and on real data is not controlled", "audit #6: visibility_ok in the replay is true by construction", "audit #7: two repeated copies of the false sentence in the ledger and in SECTION4_COMPLETE.md now carry a pointer to the correction"],
        "closing": "After the fixes a final record marks SECTION_4_CLOSED. Its scope is Section 4 as recorded in this repository (4.3.0 to 4.3.9 with A4, A5 and N1 to N4). The 4.1 and 4.2 text was not provided and stays a marked placeholder. The open items for Section 5 are not resolved by closing.",
        "not_addressed_in_this_pass": ["re-audit new #8 (F4 hashed step 3 only; the G3 change also touched section431_additions.py)", "re-audit new #9 (the bipower_w reading of A5 G3 was never confirmed)", "audit #3: selection inside folds (remains a Section 5 open item)", "audit #4: no Section 5 open item exists for era-crossing decisions", "audit #8: ATOL=1e-10 remains in step3_all_in_one.py", "the rest of the re-audit's 'disclosed and still open' items"],
    }
    path = R / f"note_4_3_N4_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"])


if __name__ == "__main__":
    main()
