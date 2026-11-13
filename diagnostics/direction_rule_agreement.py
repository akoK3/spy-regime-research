#!/usr/bin/env python3
"""Descriptive, development data only (user order 2026-11-12): the protocol 5.5 direction rule (s5_events.direction: ratio of mean squared SPY 1-min returns over
(T_d, T_c] vs the 60 one-minute bars ending at T_d's bar; > 1 = calm-to-stressed; None if < 30 valid reference bars) applied to the confirmed calm-to-stressed breaks of
the break export (A28 1b labels: entry into a higher-variance state), Gaussian HMM and HSMM. Reads results/breaks/breaks.csv and the development panels (s5_lib.load_era,
TRAIN span only, no feature columns); no model, no evaluation data, no outcome. Not a result module; changes nothing. Output: section5/results/direction_rule_agreement.json"""
import sys, json, csv, collections, datetime
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; S5 = ROOT / "section5"; sys.path.insert(0, str(S5)); sys.path.insert(0, str(ROOT))
import s5_lib as L, s5_events as E
OUT = S5 / "results" / "direction_rule_agreement.json"; FAMS = ("gaussian_hmm", "hsmm")


def main():
    if OUT.exists(): print("exists; written once"); return 3
    rows = [r for r in csv.DictReader(open(S5 / "results" / "breaks" / "breaks.csv", encoding="utf-8"))
            if r["family"] in FAMS and r["kind"] == "confirmed" and r["direction"] == "calm_to_stressed"]
    recs = []
    for era in sorted({r["era"] for r in rows}):
        d = L.load_era(era, []); first = np.asarray(d["first"]); end = np.asarray(d["end"])
        idx = {str(d["day"][int(a)]): i for i, a in enumerate(first)}
        for r in (x for x in rows if x["era"] == era):
            i = idx[r["day"]]; a, b = int(first[i]), int(end[i]); r1 = np.where(d["valid"][a:b], d["r"][a:b], np.nan)
            sd, sc = int(r["S_min"]) - 1, int(r["T0_min"]) - 1          # export: S_min / T0_min = update slot + 1
            lab, ratio = E.direction(r1, np.array([sd, sc]), 0, 1)
            recs.append(dict(era=era, family=r["family"], day=r["day"], S_min=int(r["S_min"]), T0_min=int(r["T0_min"]), old_state=int(r["old_state"]),
                             new_state=int(r["new_state"]), rule55=lab, ratio=ratio))
        del d
    def summ(sel):
        c = collections.Counter(x["rule55"] for x in sel); n = len(sel); ev = [x for x in sel if x["rule55"] is not None]
        agree = sum(x["rule55"] == "calm_to_stressed" for x in ev)
        rat = np.array([x["ratio"] for x in ev], float)
        return dict(n=n, rule55_calm_to_stressed=c.get("calm_to_stressed", 0), rule55_stressed_to_calm=c.get("stressed_to_calm", 0), rule55_undefined=c.get(None, 0),
                    agreement_of_defined=(agree / len(ev) if ev else None), ratio_quartiles=(np.quantile(rat, [.25, .5, .75]).round(3).tolist() if len(rat) else None))
    out = dict(label="DESCRIPTIVE, development data only; not part of any hypothesis test", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               rule="protocol 5.5 via s5_events.direction (per-minute means; reference = 60 one-minute bars ending at T_d's bar; None if < 30 valid reference bars)",
               all=summ(recs), by_family={f: summ([x for x in recs if x["family"] == f]) for f in FAMS},
               by_family_era={f"{f}|{e}": summ([x for x in recs if x["family"] == f and x["era"] == e]) for f in FAMS for e in ("LEGACY", "RAW")},
               by_family_old_state={f"{f}|old{s}": summ([x for x in recs if x["family"] == f and x["old_state"] == s]) for f in FAMS for s in range(4)},
               undefined_why="fewer than 30 valid 1-min bars before T_d (e.g. S within the first 30 minutes) or no valid bar in (T_d, T_c]", records=recs)
    OUT.write_text(json.dumps(out, indent=1), encoding="utf-8"); print(json.dumps({k: out[k] for k in ("all", "by_family", "by_family_era")}, indent=1)); return 0


if __name__ == "__main__": sys.exit(main())
