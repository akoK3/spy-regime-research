#!/usr/bin/env python3
"""A25 (AMENDMENT_A25.md): O9 M1 fix of the A22 LEGACY decision delay. Delayed alarms are scored by the data time they used: data times are never shifted.
  H1(a): hit iff T_d strictly after tau (unshifted) and T_c + delta <= tau + 60 min, i.e. the A7/A19.2 sweep on unshifted times with window 60 - delta; null counts unchanged.
  H1(c): T_c in [release, release + 60 - delta] (unshifted); reference rates with the same shortened window on non-FOMC sessions; stored MR2 A17-style alarms at 0.20.
Scope as A22 rule 3d: the 25 confirmatory LEGACY folds, MR2 A17-style models (pickles hash-checked), MR2 splices (seed 4242), RAW 0 unchanged; fold tests, IU and Holm as 5.9 / 5.11.
No refit. delta = 0 must reproduce the MR2 H1(a) fold effects and the MR2 A17-style H1(c) exactly, else exit 4. The A22 delay result is kept unchanged and reported beside.
Usage: s5_a25_delay.py PROTOCOL_SHA256 [--check]      --check: unit tests + delta 0 reproduction on LEGACY 29 (contaminated); writes only results/a25_preflight/.
Exit codes: 0 done, 1 crash (retryable; resumes from checkpoints), 2 Ctrl+C, 3 guard refusal or failed preflight, 4 reproduction mismatch (stop). No freeze, no era calibration."""
import sys, gc, json, time, datetime
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = HERE / "results" / "a25"; PRE = HERE / "results" / "a25_preflight"; DELAYS = (0, 5, 10); MIN_NS = A.MIN_NS
CHECK_FOLD = "LEGACY|29"


def guards(token):
    ph = A.guards(token); a = ROOT / "AMENDMENT_A25.md"
    if (ROOT / "AMENDMENT_A25.sha256").read_text().split()[0] != A.file_sha(a) or "Status: ADOPTED" not in a.read_text(encoding="utf-8"): raise PermissionError("AMENDMENT_A25.md not adopted or its sidecar differs")
    return ph


def tag_of(ph):
    import s5_guard as G
    return dict(a25_script=A.file_sha(__file__), a22_script=A.file_sha(HERE / "s5_a22.py"), a25=A.file_sha(ROOT / "AMENDMENT_A25.md"), code_version=G.code_version(), protocol=ph)


# ---------- H1(a)
def h1a_points_window(db, family, model, subset, deltas):
    """DataBackend._h1a_points with unshifted availability times and the hit window 60 - delta minutes (A25 rule 1a); delta 0 is the original computation. {delta: points}."""
    import s5_eval as V, s5_a7 as B, s5_sweep as W
    sp = db._splices(); null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
    D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA; to_des = db.c["to_des"]; mk = db.c["mk"]
    def run_(rl):
        qs = [mk(r, subset) for r in [to_des(r, r["iA"]) for r in rl]]; rs = V.run_filter(family, model, qs, D)
        R_, real, av = W.stack(rs, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
    sw = W.sweep_map if family == "bocpd" else W.sweep_old_state
    Rn, ren, avn, _ = run_(null); Rb, reb, avb, tb = run_(brk); cnt, _ = sw(Rn, ren, avn, grid, None); xs = cnt.mean(0).tolist(); out = {}
    for dl in deltas:
        _, h = sw(Rb, reb, avb, grid, tb, window=(60 - dl) * MIN_NS); out[dl] = list(zip(xs, h.mean(0).tolist()))
    return out


def delay_unit(db, fold, models, stored):
    import s5_h1 as H
    out = {}; n = db._splices()["n_stable"]; failed = db._splices()["why"] if (n >= 8 and not db._splices()["specs"]) else None
    for fam in A.FAMILIES:
        if n < 8 or failed: eff = {dl: H.h1a_fold_effect([], [], n, failed=failed)["effect"] for dl in DELAYS}
        else:
            (mf, sf), (mb, sb) = models[fam]["feature"], models[fam]["baseline"]; pf = h1a_points_window(db, fam, mf, sf, DELAYS); pb = h1a_points_window(db, fam, mb, sb, DELAYS)
            eff = {dl: H.h1a_fold_effect(pf[dl], pb[dl], n)["effect"] for dl in DELAYS}
        if not A.same(eff[0], stored[fam]): raise A.Mismatch(f"{fold} {fam}: delta 0 H1(a) {eff[0]!r} != MR2 {stored[fam]!r}")
        out[fam] = {str(dl): eff[dl] for dl in DELAYS}
    return out


# ---------- H1(c)
def h1c_window(alarms, deltas_by_fold=None, fams=A.FAMILIES):
    """H1(c) as s5_a22.h1c with unshifted T_c and the window [release, release + 60 - delta] (A25 rule 1a)."""
    import s5_h1c as HC, s5_guard as G
    j, _ = G.contamination(); ev = j["h1c_eligible_events_per_fold"]; mins = j["h1c_event_release_minute_after_0930"]; fomc = {x for v in ev.values() for x in v}; out = {}
    for fam in fams:
        hf, hb, rf, rb = [], [], [], []
        for key, dates in ev.items():
            era, n = ("LEGACY", key[6:]) if key.startswith("LEGACY") else ("RAW", key[3:]); fold = f"{era}|{int(n)}"; w = HC.WINDOW_MIN - (deltas_by_fold or {}).get(fold, 0)
            af, ab = alarms[(fold, fam)]["feature"], alarms[(fold, fam)]["baseline"]; nonf = [d for d in af if d not in fomc]
            for x in dates:
                m = mins[x]; hf.append(HC.hit([a[1] for a in af.get(x, [])], m, w)); hb.append(HC.hit([a[1] for a in ab.get(x, [])], m, w))
                rf.append(HC.reference_rate([[a[1] for a in af[d]] for d in nonf], m, w)); rb.append(HC.reference_rate([[a[1] for a in ab[d]] for d in nonf], m, w))
        out[fam] = HC.summarize(fam, hf, hb, float(np.mean(rf)), float(np.mean(rb)))
    return out


def h1c_all(conf, leg):
    alarms = {(f, fam): A.a17_record(f, fam)["alarms"] for f in conf for fam in A.FAMILIES}; ref = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]; out = {}
    for dl in DELAYS:
        out[str(dl)] = h1c_window(alarms, {f: dl for f in leg})
        if dl == 0 and not all(A.same({k: v for k, v in ref[f].items() if k != "events"}, out["0"][f]) for f in A.FAMILIES): raise A.Mismatch("delta 0 H1(c) does not reproduce the MR2 A17-style H1(c)")
    return out


# ---------- run
def run(token, folds=None, out_dir=OUT, backend=None):
    import s5_main as MB, s5_guard as G
    ph = guards(token); man = A.a17_manifest(); units = A.mr2_units(); _, excluded, conf = A.folds_split(); leg = [f for f in conf if f.startswith("LEGACY|")]; folds = folds or leg
    tag = tag_of(ph); b = backend or MB.MainBackend(ph); recs = {}; t00 = time.time()
    if folds == leg:
        hc = h1c_all(conf, leg); A.log("A25 H1(c) delta 0 reproduces MR2 exactly; diff (feature - baseline) at 0/5/10: " + "; ".join(f"{f.split('_')[0]} " + "/".join(f"{hc[str(dl)][f]['paired']['diff']:+.3f}" for dl in DELAYS) for f in A.FAMILIES))
    for k, fold in enumerate(folds, 1):
        p = out_dir / "ckpt" / f"{A.fkey(fold)}.json"; u = A.ck_get(p, tag)
        if u is None:
            G.check_unlocked("A25 delay"); t0 = time.time(); models, _ = A.load_models(fold, man); db = b._b(fold)
            u = dict(fold=fold, effects=delay_unit(db, fold, models, {fam: units[("score", fold, fam)]["a"] for fam in A.FAMILIES}), tag=tag); A.write_json(p, u); del db; gc.collect()
            A.log(f"A25 delay {k}/{len(folds)} {fold}: delta 0 reproduced exactly; H1(a) 0/5/10 " + ", ".join(f"{f.split('_')[0]} " + "/".join("NA" if u['effects'][f][str(dl)] is None else f"{u['effects'][f][str(dl)]:+.3f}" for dl in DELAYS) for f in A.FAMILIES) + f"; {(time.time() - t0) / 60:.1f} min")
        recs[fold] = u
    if folds != leg: return recs
    a22 = json.loads((A.OUT / "delay.json").read_text(encoding="utf-8"))
    res = dict(label="A25 LEGACY decision delay +5/+10 min scored by the data time used (AMENDMENT_A25.md; O9 M1 fix)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               amendment_sha256=A.file_sha(ROOT / "AMENDMENT_A25.md"), a22_delay_sha256=A.file_sha(A.OUT / "delay.json"), tag=tag, delays={}, reproduces_mr2_at_delta_0=True)
    eb = {(f, fam): units[("score", f, fam)]["b"] for f in conf for fam in A.FAMILIES}
    for dl in DELAYS:
        ea = {(f, fam): (recs[f]["effects"][fam][str(dl)] if f in recs else units[("score", f, fam)]["a"]) for f in conf for fam in A.FAMILIES}
        r = A.fam_results(ea, eb, conf, set()); res["delays"][str(dl)] = dict(confirmatory=r["family_results"], holm=r["holm"]["confirmatory"], h1c=hc[str(dl)],
                                                                               a22_superseded=dict(confirmatory=a22["delays"][str(dl)]["confirmatory"], h1c=a22["delays"][str(dl)]["h1c"]))
        A.log(f"A25 delay +{dl} min: {A.brief(r)}")
    summ = json.loads((A.MAIN2 / "run_summary.json").read_text(encoding="utf-8"))
    if not all(A.same(res["delays"]["0"]["confirmatory"][f]["all_folds_sensitivity"], summ["family_results"][f]["confirmatory"]) for f in A.FAMILIES): raise A.Mismatch("delta 0 fold tests differ from MR2 confirmatory")
    res["hours"] = (time.time() - t00) / 3600; A.write_json(out_dir / "delay_datatime.json", res); A.log(f"A25 DONE ({res['hours']:.2f} h); results/a25/delay_datatime.json"); return 0


def preflight(token):
    import unittest, s5_guard as G, s5_backend as BK
    ph = guards(token); excluded, _ = G.excluded_folds()
    if CHECK_FOLD not in excluded: raise PermissionError("preflight fold must be contaminated")
    r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_a25"))
    if not r.wasSuccessful(): raise RuntimeError(f"A25 unit tests failed: {len(r.failures)} failures, {len(r.errors)} errors")
    A.log(f"A25 preflight: guards ok, A25 ADOPTED and sidecar ok; {r.testsRun} unit tests pass")
    class One:
        kind = "check"
        def __init__(s, db): s.db = db
        def __getattr__(s, n): return getattr(s.db, n)
        def _b(s, fold): return s.db
    t0 = time.time(); era, n = CHECK_FOLD.split("|"); db = BK.DataBackend(era, int(n)); recs = run(token, folds=[CHECK_FOLD], out_dir=PRE, backend=One(db))
    A.write_json(PRE / "a25_preflight.json", dict(tests=r.testsRun, fold=CHECK_FOLD, effects=recs[CHECK_FOLD]["effects"], minutes=(time.time() - t0) / 60))
    A.log(f"A25 preflight PASSED: {CHECK_FOLD} delta 0 reproduces MR2 exactly; {(time.time() - t0) / 60:.1f} min"); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "a25_log.txt"
    try: return preflight(sys.argv[1]) if "--check" in sys.argv[2:] else run(sys.argv[1])
    except A.Mismatch as e: A.log(f"A25 MISMATCH (stop): {e}"); return 4
    except (PermissionError, RuntimeError) as e: A.log(f"A25 REFUSED: {e}"); return 3
    except KeyboardInterrupt: A.log("A25 interrupted"); return 2
    except Exception as e:
        import traceback; A.log(f"A25 CRASH: {e!r}\n{traceback.format_exc()}"); return 1


if __name__ == "__main__": sys.exit(main())
