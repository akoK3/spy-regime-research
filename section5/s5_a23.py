#!/usr/bin/env python3
"""A23 (AMENDMENT_A23.md), EXPLORATORY: combined volatility + volume model. Inputs forced: the deseasonalised 5-min return + rv10_partial90__sadj + relative_volume20 (A20 pool and
preprocessing). Per fold and family: K/lambda tuned as 5.8 (s5_select.tune, MR2 validation QLIKE, 3 starts, seed 0); return-only baseline tuned identically (must equal the MR2
baseline); H1(a)/H1(b) scored exactly as MR2 (s5_run.score_fold); A7 fold thresholds at 0.20; test alarms (H1(c)); test liquidity QLIKE (Step 2 dvol target, secondary); then D7 on the
26 confirmatory folds. Reproduction checks (A23 rule 1e): baseline K/lambda, A7 threshold and test QLIKE mean equal the MR2 A17-style record; for MR2 units with exactly these two
features and the same K/lambda, H1(a) and H1(b) equal MR2. A mismatch stops (exit 4). No confirmatory claim; no freeze, no era calibration. Contamination POST_MAIN_RUN.
Usage: s5_a23.py PROTOCOL_SHA256 [--check]      --check: unit tests + full units and D7 on the contaminated RAW 3 and LEGACY 29 (written only to results/a23_preflight/).
Exit codes: 0 done, 1 crash (retryable; resumes from checkpoints), 2 Ctrl+C, 3 guard refusal or failed preflight, 4 reproduction mismatch."""
import sys, os, gc, json, time, datetime, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = HERE / "results" / "a23"; PRE = HERE / "results" / "a23_preflight"; LOGF = HERE / "results" / "a23_log.txt"
FEATS = ("rv10_partial90__sadj", "relative_volume20"); FAMILIES = A.FAMILIES; CONTAMINATED = A.CONTAMINATED; HORIZON = 60; MIN_TGT = 50


def guards(token):
    ph = A.guards(token); a = ROOT / "AMENDMENT_A23.md"
    if (ROOT / "AMENDMENT_A23.sha256").read_text().split()[0] != A.file_sha(a) or "Status: ADOPTED" not in a.read_text(encoding="utf-8"): raise PermissionError("AMENDMENT_A23.md not adopted or its sidecar differs")
    return ph


def tag_of(ph):
    import s5_guard as G
    return dict(a23_script=A.file_sha(__file__), a22_script=A.file_sha(A.__file__), d7_script=A.file_sha(HERE / "s5_d7.py"), a23=A.file_sha(ROOT / "AMENDMENT_A23.md"), code_version=G.code_version(), protocol=ph)


# ---------- liquidity QLIKE (A23 rule 2c; Step 2 target)
def liq_target(d, dvol, q):
    """Next-60-bar deseasonalised volume target for the bars of sequence q, exactly as s5_lib.session_grid builds its target from d['dv'] (Step 2: d['dv'] = dvol)."""
    import s5_lib as L
    a, b = int(d["first"][q["sess"]]), int(d["end"][q["sess"]]); m = b - a; x = dvol[a:b]; t = np.full(len(q["slots"]), np.nan)
    for k, s0 in enumerate(q["slots"]):
        if s0 + HORIZON <= m - 1:
            w = x[s0 + 1:s0 + 1 + HORIZON]; n = np.isfinite(w).sum()
            if n >= MIN_TGT: t[k] = max(np.nansum(w) * HORIZON / n, L.QLIKE_FLOOR)
    return t


def liq_qlike(db, fam, model, sub):
    import s5_eval as V, s5_step2 as S2
    c = db.c
    if "dvol" not in c: c["dvol"] = S2.dvol_of(c["d"])
    sw = lambda qs: [dict(q, tgt=liq_target(c["d"], c["dvol"], q)) for q in qs]; D = 1 + len(sub)
    tr = sw(db.sequences("train", sub)); te = sw(db.sequences("test", sub)); values = V.state_values(fam, V.run_filter(fam, model, tr, D), tr)
    return V.qlike_series(fam, V.run_filter(fam, model, te, D), te, values)


# ---------- one (fold, family) unit
def unit(db, fold, fam, mr2_select, mr2_score, a17, mr2_model):
    import s5_select as SEL, s5_run as RUN, s5_h1 as H, s5_eval as V, s5_a17_a18_common as CM
    t0 = time.time(); missing = [x for x in FEATS if x not in db.c["kept"]]
    if missing: return dict(fold=fold, family=fam, evaluable=False, why=f"dropped by inner-train preprocessing: {missing}")
    obj = db.objective(fold, fam); grid = db.param_grid(fam); t = SEL.tune(FEATS, obj, grid); tb = SEL.tune((), obj, grid)
    setup = dict(features=list(FEATS), params=t["params"], base_params=tb["params"], val_qlike=t["result"]["qlike"], base_val_qlike=tb["result"]["qlike"])
    if A.roundtrip(tb["params"]) != A.roundtrip(mr2_select["base_params"]): raise A.Mismatch(f"{fold} {fam}: baseline K/lambda {tb['params']} != MR2 {mr2_select['base_params']}")
    sc = A.roundtrip(RUN.score_fold(db, fold, fam, setup)); same_setup = sorted(mr2_select["features"]) == sorted(FEATS) and A.roundtrip(mr2_select["params"]) == A.roundtrip(setup["params"])
    if same_setup and not (A.same(sc["a"], mr2_score["a"]) and A.same(sc["b"], mr2_score["b"])): raise A.Mismatch(f"{fold} {fam}: same setup as MR2 but H1 effects differ ({sc['a']}, {sc['b']}) vs ({mr2_score['a']}, {mr2_score['b']})")
    tf, tbh = CM.a7_threshold(db, fam, FEATS, setup["params"]), CM.a7_threshold(db, fam, (), setup["base_params"])
    if tbh["threshold"] != a17["thresholds"]["baseline"]["threshold"]: raise A.Mismatch(f"{fold} {fam}: baseline threshold {tbh['threshold']!r} != MR2 {a17['thresholds']['baseline']['threshold']!r}")
    mf, mb = db.fit(fam, FEATS, dict(setup["params"]), 3), db.fit(fam, (), dict(setup["base_params"]), 3)
    lb, kb = db.qlike_on(fam, mb, (), "test"); lf, kf = db.qlike_on(fam, mf, FEATS, "test")
    lb_, lf_, _ = V.align(np.asarray(lb, float), np.asarray(kb), np.asarray(lf, float), np.asarray(kf)); ok = np.isfinite(lb_) & np.isfinite(lf_)
    q = dict(mean_base=float(lb_[ok].mean()), mean_feat=float(lf_[ok].mean()), n=int(ok.sum()), pct=float(100 * (lb_[ok].mean() - lf_[ok].mean()) / lb_[ok].mean())) if ok.any() else dict(n=0)
    mm, ms = mr2_model                                                                                       # A17 computes mean_base on the bars common to MR2's feature model: rebuild that exactly
    lm, km = db.qlike_on(fam, mm, ms, "test"); xb, xm, _ = V.align(np.asarray(lb, float), np.asarray(kb), np.asarray(lm, float), np.asarray(km)); okm = np.isfinite(xb) & np.isfinite(xm)
    base17 = float(xb[okm].mean()) if okm.any() else None
    if not (A.same(base17, a17["qlike_test"]["mean_base"]) and int(okm.sum()) == a17["qlike_test"]["n"]): raise A.Mismatch(f"{fold} {fam}: baseline test QLIKE mean on MR2's bars {base17!r} (n {int(okm.sum())}) != MR2 {a17['qlike_test']['mean_base']!r} (n {a17['qlike_test']['n']})")
    alarms = dict(feature=CM.test_alarms(db, fam, FEATS, setup["params"], tf["threshold"]), baseline=CM.test_alarms(db, fam, (), setup["base_params"], tbh["threshold"]))
    if not A.same(alarms["baseline"], a17["alarms"]["baseline"]): raise A.Mismatch(f"{fold} {fam}: baseline test alarms differ from the MR2 A17-style record")
    llb, lkb = liq_qlike(db, fam, mb, ()); llf, lkf = liq_qlike(db, fam, mf, FEATS); lq = H.h1b_fold_effect(llb, lkb, llf, lkf)
    return A.roundtrip(dict(fold=fold, family=fam, evaluable=True, setup=setup, score=sc, same_setup_as_mr2=same_setup, mr2=dict(features=mr2_select["features"], params=mr2_select["params"], a=mr2_score["a"], b=mr2_score["b"]),
                            thresholds=dict(feature=tf, baseline=tbh), qlike_test=q, alarms=alarms, liquidity_qlike=dict(b=lq["effect"], n=lq["n"], dm=lq["dm"]), minutes=(time.time() - t0) / 60))


def fold_models(db, recs):
    models, thr = {}, {}
    for fam in FAMILIES:
        r = recs[fam]; models[fam] = dict(feature=(db.fit(fam, FEATS, dict(r["setup"]["params"]), 3), FEATS), baseline=(db.fit(fam, (), dict(r["setup"]["base_params"]), 3), ()))
        thr[fam] = {w: r["thresholds"][w]["threshold"] for w in ("feature", "baseline")}
    return models, thr


def d7_summary(agg):
    import s5_step2 as S2
    v = S2.step2_d7_verdict(agg); keys = ("liquidity:vol_x2", "liquidity:vol_x0.5", "pc_ratio3", "pc_ratio5.29", "jumps:jumps2x5sd", "trend:t4", "momentum:rho0.4")
    return dict(verdict_liquidity=v, outcomes={k: {f"{f}|{w}": agg["types"][k][f"{f}|{w}"] for f in FAMILIES for w in ("feature", "baseline", "feature_minus_baseline")} for k in keys})


# ---------- run
def run(token, folds=None, out=OUT, check=False):
    import s5_guard as G, s5_main as MB, s5_backend as BK, s5_d7 as D
    ph = guards(token); tag = tag_of(ph); units = A.mr2_units(); folds_all, excluded, conf = A.folds_split(); folds = folds or folds_all
    b = None if check else MB.MainBackend(ph); man = A.a17_manifest(); recs, d7u = {}, []; t0 = time.time(); A.log(f"A23 start: {len(folds)} folds x {len(FAMILIES)} families, inputs {FEATS} forced; tag {tag['a23_script'][:12]}")
    for k, fold in enumerate(folds, 1):
        era, n = fold.split("|"); db = BK.DataBackend(era, int(n)) if check else b._b(fold); rr = {}
        for fam in FAMILIES:
            p = out / "ckpt" / f"{A.fkey(fold)}_{fam}.json"; u = A.ck_get(p, tag)
            if u is None:
                G.check_unlocked("A23"); u = unit(db, fold, fam, units[("select", fold, fam)], units[("score", fold, fam)], A.a17_record(fold, fam), A.load_models(fold, man)[0][fam]["feature"]); u["tag"] = tag; A.write_json(p, u)
                A.log(f"A23 {k}/{len(folds)} {fold} {fam}: " + (f"K/lam {u['setup']['params']} (MR2 {u['mr2']['features']} {u['mr2']['params']}); H1(a) {u['score']['a']} (MR2 {u['mr2']['a']}), H1(b) {u['score']['b']:+.4f} (MR2 {u['mr2']['b']:+.4f}); "
                      f"liquidity QLIKE b {u['liquidity_qlike']['b']}; thr {u['thresholds']['feature']['threshold']:.2f}; {u['minutes']:.1f} min" if u["evaluable"] else f"NOT EVALUABLE: {u['why']}"))
            rr[fam] = u
        recs.update({(fold, fam): rr[fam] for fam in FAMILIES})
        if (fold in excluded and not check) or not all(rr[f]["evaluable"] for f in FAMILIES): continue
        p = out / "ckpt" / f"d7_{A.fkey(fold)}.json"; u = A.ck_get(p, tag)
        if u is None:
            G.check_unlocked("A23 D7"); t1 = time.time(); models, thr = fold_models(db, rr); u = D.fold_unit(db, fold, models, thr); u["tag"] = tag; A.write_json(p, u)
            A.log(f"A23 D7 {fold}: {len(u['days'])} days ({len(u['skipped'])} skipped); {(time.time() - t1) / 60:.1f} min")
        d7u.append(u)
        if check: del db; gc.collect()
    if check:
        agg = D.aggregate(d7u); A.write_json(out / "a23_preflight.json", dict(units={f"{f}|{fam}": {k: v for k, v in recs[(f, fam)].items() if k != "alarms"} for f, fam in recs}, d7=d7_summary(agg)))
        A.log(f"A23 preflight D7 pooled ({agg['n_days']} days): liquidity x2 gain (feature) " + ", ".join(f"{f.split('_')[0]} {agg['types']['liquidity:vol_x2'][f + '|feature']['diff']:+.2f}" for f in FAMILIES)
              + "; pc x3 " + ", ".join(f"{f.split('_')[0]} {agg['types']['pc_ratio3'][f + '|feature']['diff']:+.2f}" for f in FAMILIES)); return 0
    ev = lambda fam, f, c: recs[(f, fam)]["score"][c] if recs[(f, fam)]["evaluable"] else None
    ea = {(f, fam): ev(fam, f, "a") for f in folds for fam in FAMILIES}; eb = {(f, fam): ev(fam, f, "b") for f in folds for fam in FAMILIES}; h1 = A.fam_results(ea, eb, folds, excluded)
    al = {(f, fam): recs[(f, fam)]["alarms"] for f in conf for fam in FAMILIES if recs[(f, fam)]["evaluable"]}
    agg = D.aggregate(d7u)
    res = dict(label="A23 EXPLORATORY combined volatility + volume model (rv10_partial90__sadj + relative_volume20 forced); no confirmatory claim", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), tag=tag,
               h1=h1, h1c=A.h1c(al) if len(al) == len(conf) * len(FAMILIES) else "not computed: a unit not evaluable",
               liquidity_qlike={fam: dict(median_b_confirmatory=float(np.median([recs[(f, fam)]["liquidity_qlike"]["b"] for f in conf if recs[(f, fam)]["evaluable"] and recs[(f, fam)]["liquidity_qlike"]["b"] is not None])),
                                         positive_folds=sum(1 for f in conf if recs[(f, fam)]["evaluable"] and (recs[(f, fam)]["liquidity_qlike"]["b"] or 0) > 0)) for fam in FAMILIES},
               per_fold={f"{f}|{fam}": {k: v for k, v in recs[(f, fam)].items() if k not in ("alarms", "tag")} for f in folds for fam in FAMILIES}, d7=d7_summary(agg), d7_aggregate=agg,
               d7_skipped=[dict(fold=u["fold"], **s) for u in d7u for s in u["skipped"]], comparison_sources=dict(mr2_d7_a21=A.file_sha(A.D7A21), step2=A.file_sha(A.S2)), hours=(time.time() - t0) / 3600)
    A.write_json(out / "a23_results.json", res)
    A.log("A23 DONE: confirmatory " + "; ".join(f"{f.split('_')[0]} a {h1['family_results'][f]['confirmatory']['H1a']['mean']:+.4f} b {h1['family_results'][f]['confirmatory']['H1b']['mean']:+.4f} p_iu {h1['family_results'][f]['confirmatory']['p_iu']:.4f} holm {'R' if h1['holm']['confirmatory'][f]['reject'] else '-'}" for f in FAMILIES)
          + "; D7 liquidity x2 responds " + str(res["d7"]["verdict_liquidity"]["responds_vol_x2"]) + f"; {res['hours']:.2f} h; no freeze, no era calibration"); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    token, check = sys.argv[1], "--check" in sys.argv[2:]; A.LOG = LOGF
    import s5_d7 as D
    try:
        D.keep_awake(True)
        if check:
            import unittest
            guards(token); r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_a23"))
            if not r.wasSuccessful(): raise RuntimeError("A23 unit tests failed")
            A.log(f"A23 preflight: {r.testsRun} unit tests pass"); run(token, folds=list(CONTAMINATED), out=PRE, check=True); A.log("A23 preflight PASSED (written to results/a23_preflight/)"); return 0
        return run(token)
    except A.Mismatch as e: A.log(f"A23 REPRODUCTION MISMATCH (stop): {e}"); return 4
    except (PermissionError,) + ((RuntimeError, AssertionError) if check else ()) as e: A.log(f"A23 REFUSED: {type(e).__name__}: {e}"); return 3
    except KeyboardInterrupt: A.log("A23 STOPPED by the user (Ctrl+C); finished units are checkpointed"); return 2
    except BaseException as e:
        A.log(f"A23 CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): A.log("  | " + l)
        return 1
    finally: D.keep_awake(False)


if __name__ == "__main__": sys.exit(main())
