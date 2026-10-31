#!/usr/bin/env python3
"""Dated, hashed note 4.3-N2: A3's 4.3.7 and 4.3.8 rules applied unchanged to the 116-column pool. Written BEFORE the pool run."""
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
    assert not list(R.glob("note_4_3_N2_2*.json")), "note exists; never overwrite"
    a3_f, n1_f = one("amendment_4_3_A3_2*.json"), one("note_4_3_N1_2*.json")
    a3 = json.loads(a3_f.read_text(encoding="utf-8"))
    scale = a3["feature_classes"]["scale_adjusted"]
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "note": "4.3-N2 A3 rules 4.3.7 and 4.3.8 applied unchanged to the 116-column pool",
        "created_utc": now.isoformat(), "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "WRITTEN_BEFORE_THE_116_COLUMN_POOL_RUN",
        "statement": "Note N1 said a redundancy rule for the 116-column pool needed a dated rule before it was run. This is that rule, fixed before the run. Nothing about the pool has been computed when this is written.",
        "cites": {"A3": {"file": a3_f.name, "sha256": sha(a3_f)}, "N1": {"file": n1_f.name, "sha256": sha(n1_f)},
                  "4.3.4-4.3.9 report": {"file": "sec4_3_4_to_4_3_9_report.json", "sha256": sha(R / "sec4_3_4_to_4_3_9_report.json")}},
        "rule": {
            "pool": "the 80 raw columns plus the 36 adjusted columns (<name>__sadj), 116 in all; overnight_return_open in neither set.",
            "4.3.7": "A3 unchanged, applied to each of the 116 columns by its own coverage (finite TRAIN rows over all TRAIN grid rows, percent rounded to 3 decimals, as in Step 6). Primary = at least 80% in both eras. Sensitivity = all 116 on RAW. The result is compared with N1's statement that an adjusted column inherits its raw column's eligibility, and any difference is reported.",
            "4.3.8": "A3 unchanged: Spearman on TRAIN rows, pairwise-complete and re-ranked per pair, per era; redundant if |rho| > 0.95 in either era (primary set) or in RAW (sensitivity set); columns are processed in priority order and kept unless redundant with a column already kept.",
            "priority": "(1) shorter window = the raw column's Step 4 lookback in bars (an adjusted column has its raw column's window); (2) higher coverage = the lower of the two eras' coverage in the primary set and the RAW coverage in the sensitivity set, each column by its own coverage; (3) position.",
            "position_of_adjusted_columns": "Decided by the repository owner in the working session on this date: raw wins ties. Raw columns keep their A3 dictionary positions 0-79; the adjusted columns take positions 80-115 in the order of A3's scale-feature list. This is the only element not already in A3.",
            "adjusted_scale_feature_order": scale,
        },
        "outputs_promised": "primary and RAW-sensitivity counts (pool size, kept, dropped, split raw/adjusted), hashed, added to the closing report as an addendum without editing the closed report.",
    }
    path = R / f"note_4_3_N2_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"])


if __name__ == "__main__":
    main()
