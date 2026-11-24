#!/usr/bin/env python3
"""Freeze prep / Section 6 input (AMENDMENT_A28 rules 1b-1d, 4b, 6d): export of the SPY break events of every detector on the development test segments, SPY data only.
Per confirmatory fold (26; contaminated folds excluded) and family: the MR2 A17-style FEATURE model (pickles hash-checked) at its stored A7 threshold (0.2 alarms per session,
main event rule r = 3), filtered over the fold's test sessions. Every run of updates above threshold is exported:
  kind       confirmed (reached r = 3 updates: T_c) | fizzle (reset before r) | open_at_close (still open at the session end; A12 finding 15)
  S_min      availability of the first update of the run (T_d), minutes after 09:30 (the A17 alarm-record convention: update slot + 1)
  T0_min     availability of the confirming update (T_c); None unless confirmed.   end_min: the update that ended a fizzle (or the last update for open_at_close)
  direction  HMM/HSMM: states are ordered calm -> stressed by the variance of the 5-minute return (s5_models._order_by_return_variance); calm_to_stressed iff the state
             holding the most mass at T_c (confirmed) / at the last update of the run (fizzle) has a higher index than the old state.
             BOCPD: calm_to_stressed iff the predictive variance at that update exceeds the one at the update before S.
  size       HMM/HSMM: log(var_new / var_old) of the 5-minute return (model parameters); BOCPD: log of the same predictive-variance ratio.
  prior_calm_min   minutes from the start of the uninterrupted stretch of real updates before S whose most likely state was the lowest-variance state (HMM/HSMM) /
             most likely run length times 5 minutes at the update before S (BOCPD); 0 if the update before S was not calm.
  era, fold, family, day, threshold, old_state, new_state, K.
The loop replicates s5_events.detect_old_state_logodds / detect_bocpd_map exactly and records the runs those functions discard; every session's confirmed events are asserted
equal to theirs (else exit 4). No asset other than SPY is read; no outcome is computed. Definitions of size and prior calm are this script's (A28 does not define them).
Registry: POST_MAIN_RUN. Usage: s5_break_export.py PROTOCOL_SHA256 [--check]   (--check: unit tests + RAW 3 / LEGACY 29 into results/breaks_preflight/)
Output: results/breaks/breaks.csv, results/breaks/sessions.json (every test session scanned, per fold: the sessions with detector output), results/breaks/train_counts.json (counts by era, family, kind, direction and calendar week: the A28 rule 6d power inputs)."""
import sys, gc, json, time, datetime
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "breaks"; PRE = HERE / "results" / "breaks_preflight"; CHECK_FOLDS = ("RAW|3", "LEGACY|29")
WARM, RUN, REF_MIN = 2, 3, 30; MIN = 60 * 10 ** 9; STEP_MIN = 5


def runs_old_state(P, real, avail, theta, run=RUN, warm=WARM, refractory_min=REF_MIN):
    """detect_old_state_logodds with every run recorded: list of dict(i_d, i_end, kind, old, new). Confirmed runs are that function's events."""
    out = []; cur = None; cnt = 0; first = None; ref_until = -1
    def close(i_end, kind):
        out.append(dict(i_d=first, i_end=i_end, kind=kind, old=cur, new=int(np.argmax(P[i_end]))))
    for i in range(len(real)):
        if not real[i]:
            if cnt > 0: close(i - 1, "fizzle")
            cnt = 0; continue
        if i < warm or cur is None: cur = int(np.argmax(P[i])); cnt = 0; continue
        if avail[i] < ref_until:
            if cnt > 0: close(i - 1, "fizzle")
            cnt = 0; continue
        po = P[i, cur]; so = float(np.sum(np.delete(P[i], cur)))
        with np.errstate(divide="ignore"): lo = np.inf if po <= 0 else (-np.inf if so <= 0 else np.log(so) - np.log(po))
        if lo > theta:
            if cnt == 0: first = i
            cnt += 1
            if cnt >= run: close(i, "confirmed"); cur = int(np.argmax(P[i])); ref_until = avail[i] + refractory_min * MIN; cnt = 0
        else:
            if cnt > 0: close(i - 1, "fizzle")
            cnt = 0
    if cnt > 0: close(len(real) - 1, "open_at_close")
    return out


def runs_bocpd(rstar, real, avail, drop, hold=RUN, warm=WARM, refractory_min=REF_MIN):
    """detect_bocpd_map with every candidate recorded: list of dict(i_d, i_end, kind)."""
    out = []; cand = None; ref_until = -1; prev = None; last = None
    for i in range(len(real)):
        if not real[i]:
            if cand is not None: cand["count"] = 0
            continue
        r = rstar[i]; dropped = prev is not None and i >= warm and (prev - r) >= drop; prev = r
        if avail[i] < ref_until:
            if cand is not None: out.append(dict(i_d=cand["i_d"], i_end=last, kind="fizzle"))
            cand = None; last = i; continue
        if cand is not None:
            if dropped: out.append(dict(i_d=cand["i_d"], i_end=last, kind="fizzle")); cand = dict(i_d=i, low=r, count=0); last = i; continue
            if r <= cand["low"] + cand["count"] + 1:
                cand["count"] += 1
                if cand["count"] >= hold: out.append(dict(i_d=cand["i_d"], i_end=i, kind="confirmed")); ref_until = avail[i] + refractory_min * MIN; cand = None
            else: out.append(dict(i_d=cand["i_d"], i_end=i, kind="fizzle")); cand = None
            last = i; continue
        if dropped: cand = dict(i_d=i, low=r, count=0)
        last = i
    if cand is not None: out.append(dict(i_d=cand["i_d"], i_end=last, kind="open_at_close"))
    return out


def session_rows(fam, model, res, q, thr, day, meta):
    import s5_events as E
    if q["n"] == 0: return []
    real, av, sl = q["real"], q["avail"], q["slots"]; rows = []
    if fam == "bocpd":
        rs = res["rstar"]; vv = res["var"]; runs = runs_bocpd(rs, real, av, thr); ref = E.detect_bocpd_map(rs, real, av, thr)[0]
    else:
        P = res["P"]; runs = runs_old_state(P, real, av, thr); ref = E.detect_old_state_logodds(P, real, av, thr)[0]; v0 = np.asarray(model.var)[:, 0]; am = P.argmax(1)
    got = [(x["i_d"], x["i_end"]) for x in runs if x["kind"] == "confirmed"]
    if got != [(e["i_d"], e["i_c"]) for e in ref]: raise A.Mismatch(f"{meta['fold']} {fam} {day}: recorded confirmed runs {got} != detector events {[(e['i_d'], e['i_c']) for e in ref]}")
    prev_real = lambda i: next((j for j in range(i - 1, -1, -1) if real[j]), None)
    for x in runs:
        i, j = x["i_d"], x["i_end"]; p = prev_real(i)
        if fam == "bocpd":
            vb = float(vv[p]) if p is not None else np.nan; va = float(vv[j]); size = float(np.log(va / vb)) if p is not None and vb > 0 and va > 0 else None
            direction = None if size is None else ("calm_to_stressed" if size > 0 else "stressed_to_calm"); old = new = None
            calm = float(rs[p] * STEP_MIN) if p is not None else 0.0
        else:
            old, new = int(x["old"]), int(x["new"]); size = float(np.log(v0[new] / v0[old])); direction = "calm_to_stressed" if new > old else ("stressed_to_calm" if new < old else "same_state")
            k = p; first_calm = None
            while k is not None and am[k] == 0: first_calm = k; k = prev_real(k)
            calm = float((int(sl[i]) - int(sl[first_calm]))) if first_calm is not None else 0.0
        rows.append(dict(meta, family=fam, day=day, kind=x["kind"], S_min=int(sl[i]) + 1, T0_min=(int(sl[j]) + 1 if x["kind"] == "confirmed" else None), end_min=int(sl[j]) + 1,
                         direction=direction, size=size, prior_calm_min=calm, old_state=old, new_state=new, threshold=float(thr)))
    return rows


def fold_rows(db, fold, models, thr):
    import s5_eval as V
    d = db.c["d"]; era = fold.split("|")[0]; rows = []; days = None
    for fam in A.FAMILIES:
        m, sub = models[fam]["feature"]; qs = db.sequences("test", sub); rs = V.run_filter(fam, m, qs, 1 + len(sub)); th = thr[fam]["feature"]
        for q, r in zip(qs, rs): rows += session_rows(fam, m, r, q, th, str(d["day"][d["first"][q["sess"]]]), dict(fold=fold, era=era, K=getattr(m, "K", None)))
        days = sorted({str(d["day"][d["first"][q["sess"]]]) for q in qs})
        st = A.a17_record(fold, fam)["alarms"]["feature"]; mine = {}
        for x in rows:
            if x["family"] == fam and x["kind"] == "confirmed": mine.setdefault(x["day"], []).append([x["S_min"], x["T0_min"]])
        if {k: v for k, v in mine.items()} != {k: v for k, v in st.items() if v}: raise A.Mismatch(f"{fold} {fam}: exported confirmed alarms differ from the MR2 A17-style record")
        del rs
    return rows, days


def train_counts(rows):
    import collections
    c = collections.Counter(); wk = collections.defaultdict(set)
    for x in rows:
        y, w, _ = datetime.date.fromisoformat(x["day"]).isocalendar(); key = (x["era"], x["family"], x["kind"], x["direction"]); c[key] += 1; wk[key].add(f"{y}-W{w:02d}")
    return [dict(era=k[0], family=k[1], kind=k[2], direction=k[3], n=n, n_weeks=len(wk[k])) for k, n in sorted(c.items(), key=lambda z: tuple(str(t) for t in z[0]))]


def write_csv(p, rows):
    import csv
    p.parent.mkdir(parents=True, exist_ok=True); cols = ["fold", "era", "family", "day", "kind", "S_min", "T0_min", "end_min", "direction", "size", "prior_calm_min", "old_state", "new_state", "K", "threshold"]
    tmp = p.with_suffix(".tmp")
    with open(tmp, "w", newline="", encoding="utf-8") as f: w = csv.DictWriter(f, cols); w.writeheader(); w.writerows(rows)
    tmp.replace(p)


def run(token, folds=None, out_dir=OUT, backend=None):
    import s5_main as MB, s5_guard as G
    ph = A.guards(token); man = A.a17_manifest(); _, excluded, conf = A.folds_split(); folds = folds or conf
    tag = dict(script=A.file_sha(__file__), code_version=G.code_version(), protocol=ph, a17_results=A.file_sha(A.A17D / "a17_results.json")); b = backend or MB.MainBackend(ph); allrows = []; days_by = {}
    for k, fold in enumerate(folds, 1):
        p = out_dir / "ckpt" / f"{A.fkey(fold)}.json"; u = A.ck_get(p, tag)
        if u is None:
            t0 = time.time(); models, thr = A.load_models(fold, man); db = b._b(fold); rows, days = fold_rows(db, fold, models, thr); u = dict(fold=fold, rows=rows, days=days, tag=tag); A.write_json(p, u); del db; gc.collect()
            n = lambda kind: sum(1 for x in u["rows"] if x["kind"] == kind)
            A.log(f"breaks {k}/{len(folds)} {fold}: {n('confirmed')} confirmed (= MR2 alarm records), {n('fizzle')} fizzles, {n('open_at_close')} open at close; {(time.time() - t0) / 60:.1f} min")
        allrows += u["rows"]; days_by[fold] = u["days"]
    A.write_json(out_dir / "sessions.json", days_by)
    write_csv(out_dir / "breaks.csv", allrows); A.write_json(out_dir / "train_counts.json", dict(tag=tag, folds=list(folds), counts=train_counts(allrows), generated=datetime.datetime.now(datetime.timezone.utc).isoformat()))
    A.log(f"breaks DONE: {len(allrows)} runs over {len(folds)} folds -> {out_dir / 'breaks.csv'}"); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "breaks_log.txt"
    try:
        if "--check" in sys.argv[2:]:
            import unittest, s5_backend as BK
            r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_freeze_prep"))
            if not r.wasSuccessful(): raise RuntimeError("unit tests failed")
            class One:
                kind = "check"
                def __init__(s, db): s.db = db
                def __getattr__(s, n): return getattr(s.db, n)
                def _b(s, fold): return s.db
            for fold in CHECK_FOLDS:
                era, n = fold.split("|"); run(sys.argv[1], folds=[fold], out_dir=PRE / A.fkey(fold), backend=One(BK.DataBackend(era, int(n)))); gc.collect()
            return 0
        return run(sys.argv[1])
    except A.Mismatch as e: A.log(f"breaks MISMATCH (stop): {e}"); return 4
    except (PermissionError, RuntimeError) as e: A.log(f"breaks REFUSED: {e}"); return 3
    except KeyboardInterrupt: return 2
    except Exception as e:
        import traceback; A.log(f"breaks CRASH: {e!r}\n{traceback.format_exc()}"); return 1


if __name__ == "__main__": sys.exit(main())
