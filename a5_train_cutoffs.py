#!/usr/bin/env python3
"""A5 G1: record the TRAIN cutoff dates from the split manifest and assert that CONFIG in step3_all_in_one.py equals them.
Writes a5_train_cutoffs.json (+ .sha256). Refuses to overwrite."""
import sys, json, hashlib, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

FZ = ROOT / "frozen_documents"
OUT = s.OUT / "a5_train_cutoffs.json"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    assert not OUT.exists(), "exists; never overwrite"
    mf = FZ / "section430_executable_split_manifest.csv"
    man = pd.read_csv(mf, dtype=str)
    per_era, ok = {}, True
    for era in ("LEGACY", "RAW"):
        m = man[man.provider_era == era].sort_values("session_date")
        d = lambda p: m[m.partition == p].session_date.tolist()
        tr = d("TRAIN")
        cfg_first, cfg_last = s.CONFIG[era][0], s.CONFIG[era][1]
        match = (cfg_first == tr[0] and cfg_last == tr[-1])
        ok &= match
        per_era[era] = dict(train_first=tr[0], train_last=tr[-1], train_sessions=len(tr), embargo_sessions=d("EMBARGO"), first_evaluation_exposed=d("EVALUATION_EXPOSED")[0] if d("EVALUATION_EXPOSED") else None,
                            evaluation_exposed_sessions=len(d("EVALUATION_EXPOSED")), excluded_sessions=d("EXCLUDED"),
                            step3_CONFIG=dict(first=cfg_first, last=cfg_last), CONFIG_equals_manifest=match)
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A5 G1", manifest=mf.name, manifest_sha256=sha(mf), per_era=per_era,
               limit="The manifest is a derived artifact of 4.3.0, not a frozen document; A1's 'version and hash the final approved protocol and executable split manifest' is not verified. This record shows where the dates come from; it does not approve the manifest.",
               status="PASS" if ok else "FAIL")
    OUT.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
    print(json.dumps(doc, indent=1))


if __name__ == "__main__":
    main()
