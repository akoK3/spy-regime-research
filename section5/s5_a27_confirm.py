#!/usr/bin/env python3
"""A27 (AMENDMENT_A27.md): confirmation-count sensitivity. The confirmation count r (HMM/HSMM `run`, BOCPD `hold`) takes 1, 2, 3, 4; everything else in the event rule is unchanged.
Per r: thresholds recalibrated by the A7 bisection to 0.2 confirmed alarms per session on each fold's real validation sessions (feature and baseline separately); H1(a) from the
A7/A19.2 sweep with confirmation count r (null axis from the same sweep); fold tests, IU and Holm as 5.9 / 5.11 (H1(b) is the MR2 value: it does not depend on the event rule);
H1(c) at the recalibrated thresholds on the test segments; test alarms per session; minutes from first detection (T_d) to confirmation (T_c).
Saved MR2 A17-style models only (pickles hash-checked), no refit. Development folds only: the 26 confirmatory folds; no evaluation-period session is read.
r is passed as a parameter to the existing functions (s5_events.detect_old_state_logodds run=, detect_bocpd_map hold=, s5_sweep run= / hold=); no closure module changes.
r = 3 must reproduce the MR2 H1(a) fold effects, the A17 thresholds, the stored test alarms and the A17-style H1(c) exactly, else exit 4.
Usage: s5_a27_confirm.py PROTOCOL_SHA256 [--check]      --check: unit tests + r = 3 reproduction on RAW 3 and LEGACY 29 (contaminated) + timing; writes only results/a27_preflight/.
Exit codes: 0 done, 1 crash (retryable; resumes from per-fold checkpoints), 2 Ctrl+C, 3 guard refusal or failed preflight, 4 reproduction mismatch (stop). No freeze, no era calibration."""
import sys, gc, json, time, datetime
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = HERE / "results" / "a27"; PRE = HERE / "results" / "a27_preflight"
RS = (1, 2, 3, 4); MAIN_R = 3; TARGET = 0.20; CHECK_FOLDS = ("RAW|3", "LEGACY|29")


def guards(token):
    ph = A.guards(token); a = ROOT / "AMENDMENT_A27.md"
    if (ROOT / "AMENDMENT_A27.sha256").read_text().split()[0] != A.file_sha(a) or "Status: ADOPTED" not in a.read_text(encoding="utf-8"): raise PermissionError("AMENDMENT_A27.md not adopted or its sidecar differs")
    return ph


def tag_of(ph):
    import s5_guard as G
    return dict(a27_script=A.file_sha(__file__), a22_script=A.file_sha(HERE / "s5_a22.py"), a27=A.file_sha(ROOT / "AMENDMENT_A27.md"), code_version=G.code_version(), protocol=ph)


# ---------- event rule with confirmation count r (parameters of the existing functions)
def events_r(fam, res, q, thr, r):
    import s5_events as E
    if fam == "bocpd": return E.detect_bocpd_map(res["rstar"], q["real"], q["avail"], thr, hold=r)[0]
    return E.detect_old_state_logodds(res["P"], q["real"], q["avail"], thr, run=r)[0]


def sweep_r(fam, R, real, av, grid, taus, r):
    import s5_sweep as W
    return W.sweep_map(R, real, av, grid, taus, hold=r) if fam == "bocpd" else W.sweep_old_state(R, real, av, grid, taus, run=r)


def alarm_record(fam, qs, rs, thr, r, d):
    """{day: [[T_d, T_c], ...]} in minutes after 09:30 + 1 (the A17 record format: slot of the update + 1)."""
    return {str(d["day"][d["first"][q["sess"]]]): [[int(q["slots"][e["i_d"]]) + 1, int(q["slots"][e["i_c"]]) + 1] for e in (events_r(fam, res, q, thr, r) if q["n"] else [])] for q, res in zip(qs, rs)}


# ---------- one fold
def thresholds_unit(db, fold, models, thr_stored, stored_alarms):
    """Per family, model (feature / baseline) and r: threshold (A7 bisection to 0.2 on validation with count r), validation rate, test alarms, test rate. r = 3 must equal MR2."""
    import s5_eval as V, s5_a7 as B
    d = db.c["d"]; out = {}
    for fam in A.FAMILIES:
        out[fam] = {}
        for w in ("feature", "baseline"):
            m, sub = models[fam][w]; D = 1 + len(sub); qv = db.sequences("val", sub); rv = V.run_filter(fam, m, qv, D); lo, hi, tol = B.BOUNDS["bocpd" if fam == "bocpd" else "hmm"]
            qt = db.sequences("test", sub); rt = V.run_filter(fam, m, qt, D); rec = {}
            for r in RS:
                rate = lambda th, r=r: sum(len(events_r(fam, x, q, th, r)) for q, x in zip(qv, rv)) / len(qv)
                th, info = B.bisect_threshold(rate, lo, hi, TARGET, tol); al = alarm_record(fam, qt, rt, th, r, d)
                rec[str(r)] = dict(threshold=float(th), info=info, validation_rate=float(rate(th)), test_rate=float(sum(len(v) for v in al.values()) / len(qt)), n_test=len(qt), alarms=al)
            if rec[str(MAIN_R)]["threshold"] != thr_stored[fam][w]: raise A.Mismatch(f"{fold} {fam} {w}: r = 3 threshold {rec['3']['threshold']!r} != MR2 A17 {thr_stored[fam][w]!r}")
            if not A.same(rec[str(MAIN_R)]["alarms"], stored_alarms[fam][w]): raise A.Mismatch(f"{fold} {fam} {w}: r = 3 test alarms differ from the MR2 A17-style record")
            out[fam][w] = rec; del rv, rt
    return out


def h1a_points_r(db, family, model, subset):
    """DataBackend._h1a_points with confirmation count r for each r in RS: {r: points}. The null alarm axis comes from the same sweep (count r)."""
    import s5_eval as V, s5_a7 as B, s5_sweep as W
    sp = db._splices(); null = [x for s, x in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [x for s, x in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
    D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA; to_des = db.c["to_des"]; mk = db.c["mk"]
    def run_(rl):
        qs = [mk(x, subset) for x in [to_des(x, x["iA"]) for x in rl]]; res = V.run_filter(family, model, qs, D)
        R_, real, av = W.stack(res, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([x["tau"] for x in rl], np.int64)
    Rn, ren, avn, _ = run_(null); Rb, reb, avb, tb = run_(brk); out = {}
    for r in RS:
        cnt, _ = sweep_r(family, Rn, ren, avn, grid, None, r); _, h = sweep_r(family, Rb, reb, avb, grid, tb, r); out[r] = list(zip(cnt.mean(0).tolist(), h.mean(0).tolist()))
    return out


def h1a_unit(db, fold, models, stored):
    import s5_h1 as H, s5_a6 as A6
    sp = db._splices(); n = sp["n_stable"]; failed = sp["why"] if (n >= 8 and not sp["specs"]) else None; out = {}
    for fam in A.FAMILIES:
        if n < 8 or failed: eff = {r: H.h1a_fold_effect([], [], n, failed=failed)["effect"] for r in RS}; pa = {r: None for r in RS}
        else:
            (mf, sf), (mb, sb) = models[fam]["feature"], models[fam]["baseline"]; pf = h1a_points_r(db, fam, mf, sf); pb = h1a_points_r(db, fam, mb, sb)
            eff = {r: H.h1a_fold_effect(pf[r], pb[r], n)["effect"] for r in RS}; pa = {r: dict(feature=float(A6.pauc(pf[r])), baseline=float(A6.pauc(pb[r]))) for r in RS}
        if not A.same(eff[MAIN_R], stored[fam]): raise A.Mismatch(f"{fold} {fam}: r = 3 H1(a) {eff[MAIN_R]!r} != MR2 {stored[fam]!r}")
        out[fam] = dict(effect={str(r): eff[r] for r in RS}, pauc={str(r): pa[r] for r in RS})
    return out


# ---------- aggregate
def delays_min(alarms):
    return [c - dd for v in alarms.values() for dd, c in v]


def aggregate(recs, conf, units):
    import s5_guard as G
    eb = {(f, fam): units[("score", f, fam)]["b"] for f in conf for fam in A.FAMILIES}; a17 = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]; out = {}
    for r in RS:
        k = str(r); ea = {(f, fam): recs[f]["h1a"][fam]["effect"][k] for f in conf for fam in A.FAMILIES}; fr = A.fam_results(ea, eb, conf, set())
        al = {(f, fam): {w: recs[f]["thr"][fam][w][k]["alarms"] for w in ("feature", "baseline")} for f in conf for fam in A.FAMILIES}; hc = A.h1c(al)
        if r == MAIN_R and not all(A.same({x: v for x, v in a17[f].items() if x != "events"}, hc[f]) for f in A.FAMILIES): raise A.Mismatch("r = 3 H1(c) differs from the MR2 A17-style H1(c)")
        rates = {fam: {w: dict(median_test_rate=float(np.median([recs[f]["thr"][fam][w][k]["test_rate"] for f in conf])), mean_test_rate=float(np.mean([recs[f]["thr"][fam][w][k]["test_rate"] for f in conf])),
                               median_threshold=float(np.median([recs[f]["thr"][fam][w][k]["threshold"] for f in conf])), flagged=[f for f in conf if recs[f]["thr"][fam][w][k]["info"] != "ok"],
                               n_test_alarms=int(sum(sum(len(v) for v in recs[f]["thr"][fam][w][k]["alarms"].values()) for f in conf)))
                     for w in ("feature", "baseline")} for fam in A.FAMILIES}
        dl = {fam: {w: (lambda x: dict(n=len(x), median=float(np.median(x)) if x else None, mean=float(np.mean(x)) if x else None, p90=float(np.percentile(x, 90)) if x else None))(
              [m for f in conf for m in delays_min(recs[f]["thr"][fam][w][k]["alarms"])]) for w in ("feature", "baseline")} for fam in A.FAMILIES}
        pm = {fam: {w: (lambda x: float(np.mean(x)) if x else None)([recs[f]["h1a"][fam]["pauc"][k][w] for f in conf if recs[f]["h1a"][fam]["pauc"][k] is not None]) for w in ("feature", "baseline")} for fam in A.FAMILIES}
        out[k] = dict(confirmatory=fr["family_results"], holm=fr["holm"]["confirmatory"], h1c=hc, test_alarms=rates, detection_to_confirmation_min=dl, mean_pauc=pm)
        A.log(f"A27 r = {r}: {A.brief(fr)}; H1(c) diff " + ", ".join(f"{f.split('_')[0]} {hc[f]['paired']['diff']:+.3f}" for f in A.FAMILIES))
    summ = json.loads((A.MAIN2 / "run_summary.json").read_text(encoding="utf-8"))
    if not all(A.same(out[str(MAIN_R)]["confirmatory"][f]["all_folds_sensitivity"], summ["family_results"][f]["confirmatory"]) for f in A.FAMILIES): raise A.Mismatch("r = 3 fold tests differ from MR2 confirmatory")
    return out


# ---------- run
def run(token, folds=None, out_dir=OUT, backend=None):
    import s5_main as MB, s5_guard as G
    ph = guards(token); man = A.a17_manifest(); units = A.mr2_units(); _, excluded, conf = A.folds_split()
    if len(conf) != 26: raise PermissionError(f"{len(conf)} confirmatory folds, expected 26")
    folds = folds or conf; tag = tag_of(ph); b = backend or MB.MainBackend(ph); recs = {}; t00 = time.time()
    for k, fold in enumerate(folds, 1):
        p = out_dir / "ckpt" / f"{A.fkey(fold)}.json"; u = A.ck_get(p, tag)
        if u is None:
            G.check_unlocked("A27 confirmation count"); t0 = time.time(); models, thr = A.load_models(fold, man); db = b._b(fold)
            st = {fam: A.a17_record(fold, fam)["alarms"] for fam in A.FAMILIES}
            u = dict(fold=fold, thr=thresholds_unit(db, fold, models, thr, st), h1a=h1a_unit(db, fold, models, {fam: units[("score", fold, fam)]["a"] for fam in A.FAMILIES}), tag=tag, minutes=None)
            u["minutes"] = (time.time() - t0) / 60; A.write_json(p, u); del db; gc.collect()
            A.log(f"A27 {k}/{len(folds)} {fold}: r = 3 reproduced exactly; H1(a) r 1/2/3/4 " + ", ".join(f"{f.split('_')[0]} " + "/".join("NA" if u['h1a'][f]['effect'][str(r)] is None else f"{u['h1a'][f]['effect'][str(r)]:+.3f}" for r in RS) for f in A.FAMILIES)
                  + "; feature thr " + ", ".join(f"{f.split('_')[0]} " + "/".join(f"{u['thr'][f]['feature'][str(r)]['threshold']:.2f}" for r in RS) for f in A.FAMILIES) + f"; {u['minutes']:.1f} min")
        recs[fold] = u
    if folds != conf: return recs
    res = dict(label="A27 confirmation-count sensitivity r = 1, 2, 3, 4 (AMENDMENT_A27.md); secondary; main rule r = 3 unchanged", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               amendment_sha256=A.file_sha(ROOT / "AMENDMENT_A27.md"), tag=tag, folds=conf, by_r=aggregate(recs, conf, units), reproduces_mr2_at_r3=True)
    res["hours"] = (time.time() - t00) / 3600; A.write_json(out_dir / "confirm_count.json", res); A.log(f"A27 DONE ({res['hours']:.2f} h); results/a27/confirm_count.json"); return 0


def preflight(token):
    import unittest, s5_guard as G, s5_backend as BK
    ph = guards(token); excluded, _ = G.excluded_folds()
    if not set(CHECK_FOLDS) <= excluded: raise PermissionError("preflight folds must be contaminated")
    r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_a27"))
    if not r.wasSuccessful(): raise RuntimeError(f"A27 unit tests failed: {len(r.failures)} failures, {len(r.errors)} errors")
    A.log(f"A27 preflight: guards ok, A27 ADOPTED and sidecar ok; {r.testsRun} unit tests pass")
    class One:
        kind = "check"
        def __init__(s, db): s.db = db
        def __getattr__(s, n): return getattr(s.db, n)
        def _b(s, fold): return s.db
    rep = {}
    for fold in CHECK_FOLDS:
        t0 = time.time(); era, n = fold.split("|"); db = BK.DataBackend(era, int(n)); recs = run(token, folds=[fold], out_dir=PRE, backend=One(db))
        rep[fold] = dict(minutes=(time.time() - t0) / 60, h1a=recs[fold]["h1a"], thresholds={f: {w: {k: v["threshold"] for k, v in recs[fold]["thr"][f][w].items()} for w in ("feature", "baseline")} for f in A.FAMILIES})
        A.log(f"A27 preflight {fold}: r = 3 reproduces MR2 exactly; {rep[fold]['minutes']:.1f} min"); del db; gc.collect()
    proj = float(np.mean([v["minutes"] for v in rep.values()])) * 26 / 60
    A.write_json(PRE / "a27_preflight.json", dict(tests=r.testsRun, folds=rep, projected_hours_26_folds=proj)); A.log(f"A27 preflight PASSED; projected {proj:.1f} h for 26 folds"); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "a27_log.txt"
    try: return preflight(sys.argv[1]) if "--check" in sys.argv[2:] else run(sys.argv[1])
    except A.Mismatch as e: A.log(f"A27 MISMATCH (stop): {e}"); return 4
    except (PermissionError, RuntimeError) as e: A.log(f"A27 REFUSED: {e}"); return 3
    except KeyboardInterrupt: A.log("A27 interrupted"); return 2
    except Exception as e:
        import traceback; A.log(f"A27 CRASH: {e!r}\n{traceback.format_exc()}"); return 1


if __name__ == "__main__": sys.exit(main())
