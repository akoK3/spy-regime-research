#!/usr/bin/env python3
"""Write amendment A5 (cold audit #11 and the rv10 approval), dated and hashed BEFORE any A5 item is run.
Reads only saved documents; runs no analysis. Refuses to overwrite."""
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
    assert not list(R.glob("amendment_4_3_A5_2*.json")), "A5 exists; never overwrite"
    assert not list(R.glob("a5_*")), "A5 outputs exist; A5 must be written before its items are run"
    cov = {c["column"]: c for c in load(R / "step6_coverage_TRAIN.json")["columns"]}
    v2 = load(FZ / "protocol_20261029T032641Z.json")
    old_tiers = v2["comparison_tiers"]
    new_tiers = {t: [{"rv15_strict": "rv10_strict", "rv15_partial90": "rv10_partial90"}.get(c, c) for c in cols] for t, cols in old_tiers.items()}
    members = sorted({c for cols in new_tiers.values() for c in cols})
    below = {c: cov[c]["status"] + f" (LEGACY {cov[c]['LEGACY_pct']}%, RAW {cov[c]['RAW_pct']}%)" for c in members if c in cov}
    red = load(R / "sec4_3_8_redundancy.json")
    rv10 = {c: ("kept" if c in red["primary"]["kept"] else f"dropped: redundant with {red['primary']['dropped'][c][0]['kept_column']}" if c in red["primary"]["dropped"] else "not in the primary set") for c in ("rv10_strict", "rv10_partial90")}
    cited = {"cold_audit": ROOT / "cold_audit_20261030.md", "A4": one("amendment_4_3_A4_2*.json"), "A2": one("amendment_4_3_1_A2_*.json"), "frozen_protocol_v2": FZ / "protocol_20261029T032641Z.json",
             "split_manifest": FZ / "section430_executable_split_manifest.csv", "A1": FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json",
             "step6_coverage": R / "step6_coverage_TRAIN.json", "A3_run_redundancy": R / "sec4_3_8_redundancy.json", "section431_additions": ROOT / "section431_step3_verification" / "prototype_sources" / "section431_additions.py",
             "section4_3_1_candidates": ROOT / "section431_step3_verification" / "prototype_sources" / "section4_3_1_candidates.py"}
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "amendment": "4.3-A5 audit item 11 and the rv10 approval",
        "created_utc": now.isoformat(), "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "FIXES_AND_DECISIONS_FIXED_BEFORE_THEY_ARE_RUN",
        "statement": "Each item, its reason and its pass criteria are fixed here before any A5 item is run. Reasons are those of cold_audit_20261030.md, item 11. The approval in G5 is a decision of the repository owner given on this date. No frozen document is edited.",
        "cites": {k: {"file": p.name, "sha256": sha(p)} for k, p in cited.items()},
        "items": {
            "G1_train_cutoffs": {
                "audit": "#11, TRAIN cutoffs", "item": 1,
                "reason": "The TRAIN cutoffs 2018-12-21 (LEGACY) and 2024-12-23 (RAW) are hardcoded in step3_all_in_one.py (CONFIG) and appear in no frozen document.",
                "rule": "Record, from the manifest copy (partition == TRAIN, per era): first session, last session, number of sessions, and the dates of the EMBARGO sessions and the first EVALUATION_EXPOSED session. Assert that CONFIG in step3_all_in_one.py equals the manifest's TRAIN first and last sessions.",
                "limit": "The manifest is a derived artifact of 4.3.0, not a frozen document. A1 lists 'version and hash the final approved protocol and executable split manifest' among its items required before finalizing, and that item is not verified. The record shows where the dates come from; it does not approve the manifest.",
                "output": "a5_train_cutoffs.json", "pass": "the recorded dates equal CONFIG in both eras",
            },
            "G2_availability_circularity": {
                "audit": "#11, availability check", "item": 2, "kind": "disclosure only",
                "reason": "section4_3_1_candidates.py (load_development) asserts available == t + 60 s, but the availability column is available_utc_assuming_minute_start, built from the same minute-start assumption, so the check cannot fail. RAW has no clock-sensitivity test, and the frozen protocol's legacy -1/0/+1 minute sensitivity is still open.",
                "rule": "Quote the loader lines and the column name from the source file in the A5 addendum, with the open sensitivity item. No code or data change.",
                "pass": "the addendum quotes the lines from the file",
            },
            "G3_jump_variation": {
                "audit": "#11, jump_variation", "item": 3,
                "reason": "jump_variation_w subtracts a bipower term built from w-1 adjacent products from a realized variance of w squared returns. Without jumps, E[RV] = w*sigma^2 and E[unscaled BV] = (w-1)*sigma^2, so the output is biased upward by about one bar's variance.",
                "supersedes": "the jump_variation_w definition in A2 (and in the closing-report dictionary).",
                "rule": "jump_variation_w = max(0, sum of r_i^2 over the w returns - (w/(w-1)) * (pi/2) * sum over the w-1 adjacent pairs of |r_i||r_(i-1)|). The bipower_w column keeps its definition (the unscaled (pi/2) sum over w-1 pairs); only the bipower term inside jump_variation_w is scaled (reading stated by the assistant, to be confirmed).",
                "code": "section431_additions.py (construct_additions) and the oracle in step3_all_in_one.py.",
                "reruns": "the Step 3 formula check on the synthetic panel; the 4.3.8 redundancy outcome for the RAW sensitivity pool, recomputing every pair that involves jump_variation_w or jump_variation_w__sadj and keeping all other pairs from the A4 rerun; the primary set is checked for membership of those columns.",
                "bias_check": "On 200,000 simulated Gaussian no-jump windows per w in {15, 30, 60}: mean(RV - unscaled BV) is within 0.05 of 1.0 sigma^2 and mean(RV - scaled BV) is within 0.05 of 0.",
                "not_rerun": "the prefix and isolation tests of F4 are not rerun for this change.",
                "pass": "formula check PASS; bias check holds; redundancy outcome recomputed and reported",
            },
            "G4_amihud_adjustment_check": {
                "audit": "#11, amihud", "item": 4, "kind": "report only",
                "reason": "If LEGACY closes are back-adjusted for dividends, their price level embeds later dividends and the dollar volume in amihud_w is understated in early years. The audit could not confirm this from tracked files; the frozen protocol says LEGACY has 'inherited adjustment/cleaning' and RAW has 'no further dividend scaling'.",
                "rule": "Two checks, fixed now. (a) Ex-dividend test: approximate SPY ex-dividend dates as the third Friday of March, June, September and December (the previous session if that Friday is not a session). Per era, compute the mean overnight log return (first-bar Open / previous session's last Close) on those dates minus the mean on all other sessions, with a Welch standard error. An unadjusted series shows a gap of about minus the dividend yield for the quarter (roughly 0.3% to 0.5%); a fully adjusted series shows about 0. RAW is the unadjusted reference. (b) Junction: the ratio of the first RAW Open (2022-03-07) to the last LEGACY Close (2022-03-04). Also record the first and last LEGACY close levels.",
                "output": "a5_amihud_adjustment_check.json and .md",
                "constraints": "Report only: no data, formula, threshold or classification is changed. The conclusion is stated as an inference with its numbers.",
                "pass": "the report exists with the numbers of both checks and a plain statement of what they show",
            },
            "G5_rv10_approval": {
                "audit": "#10", "item": 5, "decision": "APPROVED by the repository owner on this date",
                "rule": "In the frozen comparison tiers, rv15_strict is replaced by rv10_strict and rv15_partial90 by rv10_partial90. Nothing else changes: downside15_strict, rv60_strict, rv60_partial90 and rv60_sampled5_exact stay in their tiers. Tier names are kept.",
                "tiers_before": old_tiers, "tiers_after": new_tiers,
                "facts": {"members_of_the_amended_tiers_that_are_in_the_step6_table": below,
                          "rv10_outcome_in_the_A3_primary_redundancy_run": rv10,
                          "consequence": "With only this replacement, every amended tier still contains at least one column that is BELOW the 80% floor (downside15_strict in core15; rv60_strict, rv60_partial90, rv60_sampled5_exact in the 60-minute tiers), so no tier is made fully primary-eligible. The A4 rerun's outcome for rv10_strict is recorded in the A4 results report."},
                "frozen_protocol": "not edited; this amendment supersedes its comparison_tiers entry for the replaced columns.",
            },
        },
        "order": "G1, G3 (code and formula check), G3 redundancy, G4, then the A5 results report and addendum. Each result is reported PASS or FAIL against the criteria above; the criteria are not changed after a run.",
    }
    path = R / f"amendment_4_3_A5_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"])
    print(json.dumps(doc["items"]["G5_rv10_approval"]["facts"], indent=1))


if __name__ == "__main__":
    main()
