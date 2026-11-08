#!/usr/bin/env python3
"""A24 (AMENDMENT_A24.md): LEGACY clock -1/0/+1 minute sensitivity of H1(c). Every alarm availability T_c of the 25 confirmatory LEGACY folds is moved by c minutes (feature and
baseline models alike; RAW 0 unchanged); H1(c) as A17 (98 events, [release, release + 60 min], reference rates on non-FOMC sessions with the same shifted alarms). Alarms: MR2 A17-style
test alarms at the 0.20 target (primary), A22 alarms at 0.15 / 0.25 (secondary). No model, no data. c = 0 must reproduce the stored H1(c) exactly, else exit 4.
H1(a), H1(b), D7, D8 and the thresholds are invariant to a common clock offset (A24 rule 1a) and are not recomputed.
Usage: s5_a24_clock.py PROTOCOL_SHA256 [--check]      --check: unit tests + the computation on the stored records of LEGACY 29 (contaminated); writes only results/a24_preflight/."""
import sys, json, datetime, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = HERE / "results" / "a24"; PRE = HERE / "results" / "a24_preflight"; OFFSETS = (-1, 0, 1); TARGETS = ("0.15", "0.20", "0.25")


def event_hits(alarms, fam, offset_by_fold):
    """Per event (fold, date): feature and baseline hit, as s5_a22.h1c / s5_a17.aggregate."""
    import s5_h1c as HC, s5_guard as G
    j, _ = G.contamination(); ev = j["h1c_eligible_events_per_fold"]; mins = j["h1c_event_release_minute_after_0930"]; out = {}
    for key, dates in ev.items():
        era, n = ("LEGACY", key[6:]) if key.startswith("LEGACY") else ("RAW", key[3:]); fold = f"{era}|{int(n)}"; c = offset_by_fold.get(fold, 0)
        for x in dates:
            out[(fold, x)] = tuple(HC.hit([a[1] + c for a in alarms[(fold, fam)][w].get(x, [])], mins[x]) for w in ("feature", "baseline"))
    return out


def alarms_at(target, conf):
    if target == "0.20": return {(f, fam): A.a17_record(f, fam)["alarms"] for f in conf for fam in A.FAMILIES}
    u = {f: json.loads((A.OUT / "thresholds" / "ckpt" / f"{A.fkey(f)}.json").read_text(encoding="utf-8")) for f in conf}
    return {(f, fam): {w: u[f]["units"][fam][w][target]["alarms"] for w in ("feature", "baseline")} for f in conf for fam in A.FAMILIES}


def guards(token):
    ph = A.guards(token); a = ROOT / "AMENDMENT_A24.md"
    if (ROOT / "AMENDMENT_A24.sha256").read_text().split()[0] != A.file_sha(a) or "Status: ADOPTED" not in a.read_text(encoding="utf-8"): raise PermissionError("AMENDMENT_A24.md not adopted or its sidecar differs")
    return ph


def run(token):
    ph = guards(token); _, _, conf = A.folds_split(); leg = [f for f in conf if f.startswith("LEGACY|")]
    ref20 = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]; thr = json.loads((A.OUT / "thresholds.json").read_text(encoding="utf-8"))["targets"]
    res = dict(label="A24 LEGACY clock -1/0/+1 min: H1(c) (AMENDMENT_A24.md)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment_sha256=A.file_sha(ROOT / "AMENDMENT_A24.md"),
               invariant="H1(a), H1(b), D7, D8 and A7 thresholds are invariant to a common LEGACY clock offset (rule 1a); not recomputed", targets={})
    for tg in TARGETS:
        al = alarms_at(tg, conf); res["targets"][tg] = {}
        for c in OFFSETS:
            r = A.h1c(al, {f: c for f in leg}); res["targets"][tg][str(c)] = r
            if c == 0:
                ref = {f: {k: v for k, v in ref20[f].items() if k != "events"} for f in A.FAMILIES} if tg == "0.20" else thr[tg]["h1c"]
                if not all(A.same(ref[f], r[f]) for f in A.FAMILIES): raise A.Mismatch(f"clock 0 at target {tg} does not reproduce the stored H1(c)")
        h0 = {fam: event_hits(al, fam, {}) for fam in A.FAMILIES}
        res["targets"][tg]["changed_events"] = {str(c): {fam: dict(collections.Counter(("feature" if i == 0 else "baseline") + (" gained" if b[i] else " lost") for k, b in event_hits(al, fam, {f: c for f in leg}).items() for i in (0, 1) if b[i] != h0[fam][k][i])) for fam in A.FAMILIES} for c in (-1, 1)}
    res["reproduces_at_0"] = True; A.write_json(OUT / "clock.json", res)
    for tg in TARGETS:
        A.log(f"A24 clock target {tg}: H1(c) diff (feature - baseline) at -1/0/+1: " + "; ".join(f"{f.split('_')[0]} " + "/".join(f"{res['targets'][tg][str(c)][f]['paired']['diff']:+.3f}" for c in OFFSETS) for f in A.FAMILIES))
    return 0


def preflight(token):
    import unittest
    guards(token); r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_a24"))
    if not r.wasSuccessful(): raise RuntimeError("A24 unit tests failed")
    al = {("LEGACY|29", fam): A.a17_record("LEGACY|29", fam)["alarms"] for fam in A.FAMILIES}; n = sum(len(v) for fam in A.FAMILIES for w in ("feature", "baseline") for v in al[("LEGACY|29", fam)][w].values())
    A.write_json(PRE / "a24_preflight.json", dict(tests=r.testsRun, legacy29_alarms=n, note="LEGACY 29 has no eligible H1(c) event (contaminated); stored alarms read and shifted only"))
    A.log(f"A24 preflight: {r.testsRun} unit tests pass; LEGACY 29 stored alarms read ({n}); no eligible events on contaminated folds"); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "a24_log.txt"
    try: return preflight(sys.argv[1]) if "--check" in sys.argv[2:] else run(sys.argv[1])
    except A.Mismatch as e: A.log(f"A24 MISMATCH (stop): {e}"); return 4
    except (PermissionError, RuntimeError) as e: A.log(f"A24 REFUSED: {e}"); return 3


if __name__ == "__main__": sys.exit(main())
