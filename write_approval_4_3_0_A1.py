#!/usr/bin/env python3
"""Record a dated, hashed approval of amendment 4.3.0-A1, stated as given after 4.3.1 had already used it."""
import json, hashlib, subprocess, datetime
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


def main():
    assert not list(R.glob("approval_4_3_0_A1_2*.json")), "an approval record exists; never overwrite"
    a1 = FZ / "protocol_amendment_4_3_0_A1_20261029T034121Z.json"
    assert sha(a1) == (FZ / (a1.stem + ".sha256")).read_text().split()[0] == "a57d55ccc760c2359d2d5d14c12d52a3fb1ba29a1bd3e222a71e6284886724ae"
    a1d = json.loads(a1.read_text(encoding="utf-8"))
    a2, closing = one("amendment_4_3_1_A2_*.json"), one("section_4_3_1_closing_report_2*.json")
    assert a1d["amendment"] == "4.3.0-A1" and "requires audit and explicit approval" in a1d["status"]
    assert json.loads(a2.read_text(encoding="utf-8"))["basis"]["amendment_proposal_A1"]["sha256"] == sha(a1)
    name = subprocess.run(["git", "config", "user.name"], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = {
        "record": "approval of amendment 4.3.0-A1",
        "created_utc": now.isoformat(),
        "created_america_new_york": pd.Timestamp(now).tz_convert("America/New_York").isoformat(),
        "status": "APPROVED_AFTER_USE",
        "approver": f"the repository owner (git user.name: {name}), by instruction in the working session on this date",
        "approved_document": {"file": a1.name, "sha256": sha(a1), "amendment": a1d["amendment"], "created_utc": a1d["created_utc"],
                              "status_before": a1d["status"]},
        "approved_after_use": {
            "statement": "This approval was given after Section 4.3.1 had used amendment 4.3.0-A1 as a basis. It is not an ex-ante approval and does not make A1 preregistered; A1 itself states 'Do not claim this amendment was preregistered before earlier experiments'.",
            "documented_use_before_approval": [
                {"document": a2.name, "sha256": sha(a2), "use": "cites A1 by hash as its basis and replaces A1's max_feature_lookback_minutes (60) with the A2 cap for detector features"},
                {"document": closing.name, "sha256": sha(closing), "use": "lists A1 as an unapproved proposal; that report is unchanged and its status line is superseded by this record"},
            ],
            "not_found": "No other 4.3.1 step is recorded as having applied A1's embargo, refit or evaluation terms.",
        },
        "scope": "A1 as written, including its embargo (5 sessions), refit policy (frozen), endpoints and legacy evaluation proposal (2019-01-02..2022-03-04, still 'RETROSPECTIVE / PREVIOUSLY EXPOSED').",
        "not_resolved_by_this_approval": [
            "A1 declares max_feature_lookback_minutes = 60 while A2 caps detector features at 60 prior return-bars (Step 4 lookback limit 61); the two are not reconciled here.",
            "A1's 5-session embargo does not cover the 20-session relative-volume history of relative_volume20 and log_relative_volume20.",
            "No leakage audit was run as part of this approval, although A1 says the embargo must not be assumed sufficient without one.",
            "A1's own 'required_before_finalizing' items are not verified by this record: " + "; ".join(a1d["required_before_finalizing"]),
        ],
        "unchanged": ["amendment file and its hash", "the closing report and its hash", "all features, thresholds and classifications"],
    }
    path = R / f"approval_4_3_0_A1_{now.strftime('%Y%m%dT%H%M%SZ')}.json"
    data = (json.dumps(doc, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    digest = hashlib.sha256(data).hexdigest()
    path.with_suffix(".sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    print(path.name, "\nSHA-256:", digest, "\ncreated_utc:", doc["created_utc"])


if __name__ == "__main__":
    main()
