#!/usr/bin/env python3
"""Dated, hashed note 4.3-N3: the Amihud finding of A5 G4 and the requirement that Section 5 normalizes Amihud per fold."""
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
    assert not list(R.glob("note_4_3_N3_2*.json")), "note exists; never overwrite"
    a5, am, res = one("amendment_4_3_A5_2*.json"), R / "a5_amihud_adjustment_check.json", R / "a5_results_report.json"
    amd, resd = json.loads(am.read_text(encoding="utf-8")), json.loads(res.read_text(encoding="utf-8"))
    g4 = next(i for i in resd["items"] if i["item"].startswith("4 G4"))
    pool = pd.read_csv(R / "a4_sec4_3_pool_matrix.csv")
    cols = pool[pool.column.str.startswith("amihud_")][["column", "coverage_LEGACY_pct", "coverage_RAW_pct", "primary_eligible", "primary_outcome", "sensitivity_outcome"]]
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "note": "4.3-N3 Amihud: LEGACY prices appear dividend-adjusted; Section 5 normalizes Amihud per fold",
        "created_utc": now.isoformat(), "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "WRITTEN_AFTER_THE_A5_G4_REPORT",
        "cites": {"A5": {"file": a5.name, "sha256": sha(a5)}, "A5_G4_report": {"file": am.name, "sha256": sha(am)}, "A5_results_report": {"file": res.name, "sha256": sha(res)},
                  "frozen_protocol_v2": {"file": "protocol_20261029T032641Z.json", "sha256": sha(ROOT / "frozen_documents" / "protocol_20261029T032641Z.json")}},
        "finding": {
            "statement": "LEGACY closes appear to be back-adjusted for dividends. This is an inference, not an established fact.",
            "evidence_in_the_repository": f"A5 G4: first LEGACY close {amd['price_levels']['LEGACY']['first_close']} on {amd['price_levels']['LEGACY']['first_session']}; junction ratio {amd['junction']['ratio']}; the fixed ex-dividend reading rule gave '{amd['reading_rule_result']}' (LEGACY gap {amd['ex_dividend_test']['LEGACY']['gap_pct']}%, RAW gap {amd['ex_dividend_test']['RAW']['gap_pct']}%).",
            "evidence_outside_the_repository": amd["external_reference_not_from_the_repository"],
            "consequence": amd["consequence_for_amihud"],
            "g4_detail": g4["detail"],
        },
        "requirement": {
            "text": "Section 5 must normalize Amihud (amihud_15, amihud_30, amihud_60 and their __sadj versions) per fold. Any normalizing statistic is fitted on the training rows of that fold only, as the frozen protocol requires for fold fit statistics.",
            "fold_fit_rule_quoted": json.loads((ROOT / "frozen_documents" / "protocol_20261029T032641Z.json").read_text(encoding="utf-8"))["nested_development"]["rule"],
            "decided_by": "the repository owner, in the working session on this date",
            "method": "Not specified here; to be specified in Section 5.",
        },
        "columns": cols.to_dict(orient="records"),
        "not_done": ["No Amihud column, formula, threshold or classification was changed.", "The adjustment status of the LEGACY closes is not independently confirmed.", "RAW closes are described by the frozen protocol as having no further dividend scaling; this was not tested."],
    }
    path = R / f"note_4_3_N3_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest)


if __name__ == "__main__":
    main()
