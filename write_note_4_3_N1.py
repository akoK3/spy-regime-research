#!/usr/bin/env python3
"""Dated, hashed note 4.3-N1: candidate pool and the role of overnight_return_open. Written after 4.3.4-4.3.9 were run."""
import json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
R = ROOT / "section431_step3_all_in_one_results"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def one(pattern):
    files = sorted(R.glob(pattern))
    assert len(files) == 1, pattern
    return files[0]


def main():
    assert not list(R.glob("note_4_3_N1_2*.json")), "note exists; never overwrite"
    a3_f = one("amendment_4_3_A3_2*.json")
    a3 = json.loads(a3_f.read_text(encoding="utf-8"))
    rep = json.loads((R / "sec4_3_4_to_4_3_9_report.json").read_text(encoding="utf-8"))
    scale, primary = a3["feature_classes"]["scale_adjusted"], a3["eligibility_sets"]["primary_20"]
    assert rep["subsections"]["4.3.4"]["checks"]["slots_with_undefined_median_per_feature"] == {"RAW": {}, "LEGACY": {}}
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "note": "4.3-N1 candidate pool and the role of overnight_return_open",
        "created_utc": now.isoformat(), "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "WRITTEN_AFTER_SECTIONS_4_3_4_TO_4_3_9_WERE_RUN",
        "statement": "This note was written after the 4.3.4-4.3.9 run and records two decisions. Because it changes two sentences of amendment A3, it acts as the dated amendment that A3 requires for any change.",
        "cites": {"A3": {"file": a3_f.name, "sha256": sha(a3_f)}, "A2": {"file": one("amendment_4_3_1_A2_*.json").name, "sha256": sha(one("amendment_4_3_1_A2_*.json"))},
                  "4.3.4-4.3.9 report": {"file": "sec4_3_4_to_4_3_9_report.json", "sha256": sha(R / "sec4_3_4_to_4_3_9_report.json")},
                  "4.3.7 eligibility": {"file": "sec4_3_7_eligibility.json", "sha256": sha(R / "sec4_3_7_eligibility.json")},
                  "4.3.8 redundancy": {"file": "sec4_3_8_redundancy.json", "sha256": sha(R / "sec4_3_8_redundancy.json")}},
        "decisions": {
            "1_candidate_pool": {
                "rule": "The adjusted columns (<name>__sadj) join the candidate pool alongside their raw columns. The pool is the 80 raw columns plus the 36 adjusted columns, 116 in all.",
                "adjusted_columns": [n + "__sadj" for n in scale],
                "eligibility": f"An adjusted column inherits the eligibility of its raw column. 4.3.4 found no slot with an undefined or non-positive median in either era, so adjusted coverage equals raw coverage. {len(set(primary) & set(scale))} of the 20 primary columns are scale features, so their adjusted versions are primary-eligible.",
                "supersedes_in_A3": ["rules.4.3.7_eligibility.adjusted_columns: 'an adjusted column follows the eligibility of its raw column and is not a separate candidate' (now: it follows the eligibility but is a separate candidate)",
                                     "rules.4.3.8_redundancy.applies_to: 'raw columns of each eligibility set separately'"],
            },
            "2_overnight": {
                "rule": "overnight_return_open is response-side only: it may appear only on the response side (as an outcome or label variable) of the later overnight analysis, and never as a detector input, feature, scaler input or HMM input. This restates and keeps the A2 exclusion.",
            },
        },
        "not_done": [
            "No eligibility or redundancy statistic was computed for the 116-column pool. The 4.3.7 and 4.3.8 outputs stay exactly as produced, on the 80 raw columns.",
            "Raw/adjusted pairs were not correlated here; any redundancy rule for the 116-column pool needs a new dated rule before it is run.",
            "The overnight analysis is still not specified.",
        ],
        "unchanged": ["all formulas, thresholds and classifications", "the 80 raw detector columns and their frozen matrix"],
    }
    path = R / f"note_4_3_N1_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"])


if __name__ == "__main__":
    main()
