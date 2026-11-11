#!/usr/bin/env python3
"""FOMC clock check (label-free timing check, 2026-11-11; on the user's instruction).

For each FOMC meeting with a stored release time (section5/results/h1c_schedule_times.json, status "time") that falls on a
TRAIN session (split manifest), take SPY's 1-minute log return |r| in the bars labelled release-2 .. release+2 minutes
(minute_index_in_session = minute_after_0930 + offset; only return-eligible bars) and report the median |r| per offset, per era.

Pre-stated: start-labelling is supported if the bar labelled at the release minute (offset 0) has the largest median.
(Under start labelling, the bar labelled 14:15 spans 14:15:00-14:16:00, so its return, close(14:15 bar)/close(14:14 bar), contains the
release; under end labelling it would end at the release and the jump would sit at offset +1.)

Label-free (A15 rule 6d): no detector, no regime model, no Section 5 outcome. Reads TRAIN sessions only, through
s5_eval_loader.load_development, then restricts to manifest TRAIN; no evaluation-period row is read. Writes results once.
"""
import json, hashlib, datetime
from pathlib import Path
import numpy as np, pandas as pd
import s5_eval_loader as EL

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
TIMES = HERE / "results" / "h1c_schedule_times.json"
MANIFEST = ROOT / "frozen_documents" / "section430_executable_split_manifest.csv"
OUT = HERE / "results" / "fomc_clock.json"
OFFSETS = (-2, -1, 0, 1, 2)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if OUT.exists(): raise SystemExit(f"{OUT} exists; never overwrite")
    meetings = {d: m for d, m in json.loads(TIMES.read_text(encoding="utf-8"))["meetings"].items() if m.get("status") == "time"}
    man = pd.read_csv(MANIFEST, dtype=str)
    res = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), script="section5/s5_fomc_clock.py", kind="LABEL_FREE",
               inputs={TIMES.name: sha(TIMES), MANIFEST.name: sha(MANIFEST)}, offsets=list(OFFSETS),
               rule="start-labelling supported if offset 0 has the largest median |r|", eras={})
    for era in ("LEGACY", "RAW"):
        train = set(man.loc[(man.provider_era == era) & (man.partition == "TRAIN"), "session_date"])
        days = sorted(d for d in meetings if d in train)
        df = EL.load_development(era, ["minute_index_in_session", "SPY_return_eligible", "SPY_log_return_1m"])
        df = df[df.session_date_ny.isin(set(days))]
        assert set(df.session_date_ny) <= train, "non-TRAIN session read"
        key = {(r.session_date_ny, int(r.minute_index_in_session)): r for r in df.itertuples(index=False)}
        per = {o: [] for o in OFFSETS}; n_days_used = 0
        for d in days:
            m0 = int(meetings[d]["minute_after_0930"]); got = False
            for o in OFFSETS:
                r = key.get((d, m0 + o))
                if r is not None and int(r.SPY_return_eligible) == 1 and np.isfinite(r.SPY_log_return_1m):
                    per[o].append(abs(float(r.SPY_log_return_1m))); got = True
            n_days_used += got
        med = {str(o): (float(np.median(per[o])) * 1e4 if per[o] else None) for o in OFFSETS}
        best = max((o for o in OFFSETS if per[o]), key=lambda o: np.median(per[o]))
        res["eras"][era] = dict(fomc_train_days=len(days), days_with_data=n_days_used, n_per_offset={str(o): len(per[o]) for o in OFFSETS},
                                median_abs_return_bp=med, mean_abs_return_bp={str(o): (float(np.mean(per[o])) * 1e4 if per[o] else None) for o in OFFSETS},
                                largest_median_offset=best, start_labelling_supported=bool(best == 0))
        del df, key
    OUT.write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
    print(json.dumps(res["eras"], indent=1))


if __name__ == "__main__":
    main()
