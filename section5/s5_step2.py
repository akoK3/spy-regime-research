#!/usr/bin/env python3
"""Step 2 for liquidity (AMENDMENT_A21.md rule 3; A19 rule 3): the 5.8 machinery (greedy forward, 1% rule, at most 6 features, K/lambda tuning, return-only baseline tuned identically)
rerun on all 34 folds for the four families with the validation objective = QLIKE of the regime-conditional forecast of next-60-min deseasonalised volume (dvol, the D8 `adjust`);
pool = the A20 pool (13). Score (a): test-segment liquidity QLIKE, baseline minus features (fold tests as 5.9, BH across the 4 families). Score (b): D7 (A19-A19.3, A21 rule 1) on the
Step 2 fits, 26 confirmatory folds, A7 fold-level thresholds. Secondary; not H1; no freeze, no era calibration. Contamination POST_MAIN_RUN.
Usage: s5_step2.py PROTOCOL_SHA256 [--check]
  --check: unit tests + preflight on the contaminated RAW 3 and LEGACY 29 folds only: the A21 rule-1 D7 fold units on the MR2 fits, and the full Step 2 unit (selection, score (a),
  thresholds, D7 unit) for all four families; writes only to results/step2_preflight/.
Exit codes: 0 done, 1 crash (retryable; resumes from results/step2_liquidity/ckpt), 2 Ctrl+C, 3 guard refusal or failed preflight."""
import sys, os, gc, json, time, pickle, hashlib, datetime, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = RES / "step2_liquidity"; CK = OUT / "ckpt"; MODELS = OUT / "models"; PRE = RES / "step2_preflight"
LOG = RES / "a21_log.txt"; MR2_A17 = RES / "mr2" / "a17"; MAIN2 = RES / "main_run_2"
CONTAMINATED = ("RAW|3", "LEGACY|29"); FAMILIES = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); BH_Q = 0.05; NULL_MAX = 0.30; MIN_DAYS = 100; VR_OK = 0.95
EXIT_OK, EXIT_CRASH, EXIT_STOP, EXIT_GUARD = 0, 1, 2, 3


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"; LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def roundtrip(x): return json.loads(json.dumps(x, default=float))


# ---------- liquidity target (A21 rule 3c)
def dvol_of(d):
    """Deseasonalised 1-min volume: volume / median volume of the same slot over the previous 20 sessions (>= 10 finite), exactly the D8 construction."""
    import step11_a4_rerun_4_3_4_7_8 as pstep
    vol = np.where(np.isfinite(d["volume"]) & (d["volume"] >= 0), d["volume"].astype(float), np.nan); return pstep.adjust(vol, d["slot"], d["first"], d["end"])


def era_context_liq(era):
    """As s5_backend.era_context, except that session_grid's target source d['dv'] is dvol (target = (60/n) sum dvol over the next 60 bars). ctx['dv'] stays the deseasonalised
    variance (stable days and D7 injections use it)."""
    import s5_lib as L, s5_d2_stable as S
    primary, _, _ = L.pools(); cols = L.a20_pool(primary)
    d = L.load_era(era, cols + ["lee_mykland_approx60"]); dv = S.des_variance(d); d["dv"] = dvol_of(d)
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    return dict(era=era, d=d, dv=dv, cols=cols, native=native, Mx=Mx, target="dvol")


def _classes():
    import s5_backend as BK, s5_main as MB

    class LiqBackend(BK.DataBackend):
        kind = "step2_liquidity_fold"

        def _build(self):
            if self._shared is None: self._shared = era_context_liq(self.era)
            if self._shared.get("target") != "dvol": raise RuntimeError("Step 2 backend without the liquidity target")
            return super()._build()

    class LiqMain(MB.MainBackend):
        kind = "step2_liquidity"

        def _ctx(self, era):
            if self._era is None or self._era["era"] != era:
                self._cur = self._era_b = self._era = None; gc.collect(); self._era = era_context_liq(era)
            return self._era

        def _b(self, fold):
            if self._cur is None or self._cur.id != fold:
                era, n = fold.split("|"); self._cur = None; gc.collect()
                self._cur = LiqBackend(era, int(n), allowed=set(self.ids), protocol_sha256=self.protocol_sha256, shared=self._ctx(era))
            return self._cur
    return LiqBackend, LiqMain


# ---------- one (fold, family) unit
def unit(db, fold, fam, save_dir):
    import s5_run as RUN, s5_h1 as H, s5_eval as V, s5_a17_a18_common as CM

    class One:
        kind = "step2"
        def objective(s, f, fm): return db.objective(f, fm)
        def candidates(s, f): return db.candidates(f)
        def param_grid(s, fm): return db.param_grid(fm)
    t0 = time.time(); setup = roundtrip(RUN.select_fold(One(), fold, fam)); feats = tuple(setup["features"])
    mf, mb = db.fit(fam, feats, dict(setup["params"]), 3), db.fit(fam, (), dict(setup["base_params"]), 3)
    lf, kf = db.qlike_on(fam, mf, feats, "test"); lb, kb = db.qlike_on(fam, mb, (), "test"); b = H.h1b_fold_effect(lb, kb, lf, kf)
    lb_, lf_, _ = V.align(np.asarray(lb, float), np.asarray(kb), np.asarray(lf, float), np.asarray(kf)); ok = np.isfinite(lb_) & np.isfinite(lf_)
    q = dict(mean_base=float(lb_[ok].mean()), mean_feat=float(lf_[ok].mean()), n=int(ok.sum()), pct=float(100 * (lb_[ok].mean() - lf_[ok].mean()) / lb_[ok].mean())) if ok.any() else dict(n=0)
    tf, tb = CM.a7_threshold(db, fam, feats, setup["params"]), CM.a7_threshold(db, fam, (), setup["base_params"])
    p = Path(save_dir) / f"{fold.replace('|', '_')}_{fam}.pkl"; p.write_bytes(pickle.dumps(dict(feature=mf, baseline=mb, setup=setup), protocol=4))
    return roundtrip(dict(fold=fold, family=fam, setup=setup, b=b["effect"], b_skipped=b["skipped"], b_n=b["n"], dm=b["dm"], qlike_test=q, thresholds=dict(feature=tf, baseline=tb),
                          model_pickle_sha256=file_sha(p), minutes=(time.time() - t0) / 60))


def fold_models(fold, recs, model_dir):
    models, thr = {}, {}
    for fam in FAMILIES:
        p = Path(model_dir) / f"{fold.replace('|', '_')}_{fam}.pkl"; r = recs[fam]
        if not p.exists() or file_sha(p) != r["model_pickle_sha256"]: raise PermissionError(f"Step 2 model {p.name} missing or its sha256 differs from its unit record")
        o = pickle.loads(p.read_bytes()); models[fam] = dict(feature=(o["feature"], tuple(r["setup"]["features"])), baseline=(o["baseline"], ()))
        thr[fam] = {w: r["thresholds"][w]["threshold"] for w in ("feature", "baseline")}
    return models, thr


# ---------- aggregation (A21 rules 3d, 3e)
def step2_d7_verdict(agg):
    """A21 rule 3e: required gates (i) liquidity variance-neutral share, (iii) null <= 0.30 for every Step 2 model, (iv) >= 100 days; (ii) reported only."""
    vn = {lab: agg["types"][f"liquidity:{lab}"]["variance_neutral_share"] for lab in ("vol_x2", "vol_x0.5")}
    nulls = {f"{f}|{w}": agg["types"]["pc_ratio3"][f"{f}|{w}"]["rate0"] for f in FAMILIES for w in ("feature", "baseline")}
    g1, g3, g4 = vn["vol_x2"] >= VR_OK, all(v <= NULL_MAX for v in nulls.values()), agg["n_days"] >= MIN_DAYS
    pc = {pc: {f: agg["types"][pc][f"{f}|feature"]["responds"] for f in FAMILIES} for pc in ("pc_ratio3", "pc_ratio5.29")}
    resp = {f: dict(vol_x2=agg["types"]["liquidity:vol_x2"][f"{f}|feature"], vol_x0_5=agg["types"]["liquidity:vol_x0.5"][f"{f}|feature"]) for f in FAMILIES}
    return dict(gate_i_share=vn, gate_i=g1, gate_iii=g3, gate_iv=g4, null_hit_rates=nulls, n_days=agg["n_days"], gate_ii_reported_only=pc, gates_passed=bool(g1 and g3 and g4),
                responds_vol_x2={f: bool(g1 and g3 and g4 and resp[f]["vol_x2"]["responds"]) for f in FAMILIES}, gains=resp)


def aggregate(units, d7units, folds, excluded):
    import s5_stats as ST, s5_select as SEL, s5_d7 as D
    out = dict(families={}, folds=folds, excluded=sorted(excluded))
    for fam in FAMILIES:
        e = {f: units[(f, fam)]["b"] for f in folds}; res = {}
        for lab, keep in (("confirmatory", [f for f in folds if f not in excluded]), ("all_folds", folds)):
            x = [e[f] for f in keep if e[f] is not None]; t = ST.fold_tests(x, nboot=10000, seed=1)
            qs = [units[(f, fam)]["qlike_test"] for f in keep if units[(f, fam)]["qlike_test"].get("n")]
            pooled = 100 * (sum(q["mean_base"] * q["n"] for q in qs) - sum(q["mean_feat"] * q["n"] for q in qs)) / sum(q["mean_base"] * q["n"] for q in qs) if qs else float("nan")
            res[lab] = dict(tests=t, qlike_pct_median=float(np.median([q["pct"] for q in qs])) if qs else float("nan"), qlike_pct_pooled=float(pooled), skipped=[f for f in keep if e[f] is None])
        eras = sorted({f.split("|")[0] for f in folds})
        res["final_setups"] = {era: SEL.final_setup([units[(f, fam)]["setup"] for f in folds if f.startswith(era + "|")]) for era in eras}
        res["per_fold"] = {f: dict(features=units[(f, fam)]["setup"]["features"], params=units[(f, fam)]["setup"]["params"], base_params=units[(f, fam)]["setup"]["base_params"],
                                   b=e[f], qlike_pct=units[(f, fam)]["qlike_test"].get("pct")) for f in folds}
        out["families"][fam] = res
    for lab in ("confirmatory", "all_folds"):
        out[f"bh_{lab}"] = ST.benjamini_hochberg({fam: out["families"][fam][lab]["tests"]["p_block_bootstrap"] for fam in FAMILIES}, q=BH_Q)
    if d7units:
        agg = D.aggregate(d7units); out["d7"] = dict(aggregate=agg, verdict=step2_d7_verdict(agg), skipped=[dict(fold=u["fold"], **s) for u in d7units for s in u["skipped"]])
    return out


# ---------- guards
def guards(token):
    import s5_guard as G, s5_contamination as C
    ph = G.verify_frozen_protocol(token); G.canonical_contamination(); C.check_registry(HERE)
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    a21 = ROOT / "AMENDMENT_A21.md"
    if not a21.exists() or (ROOT / "AMENDMENT_A21.sha256").read_text().split()[0] != file_sha(a21): raise PermissionError("AMENDMENT_A21.md missing or its sidecar differs")
    if not (RES / "d8" / "d8_results.json").exists(): raise PermissionError("D8 results missing")
    return ph


def tag_of(ph):
    import s5_guard as G
    return dict(step2_script=file_sha(__file__), d7_script=file_sha(HERE / "s5_d7.py"), code_version=G.code_version(), protocol=ph, a21=file_sha(ROOT / "AMENDMENT_A21.md"))


# ---------- preflight (A21 rule 4)
def preflight(token):
    import unittest, s5_guard as G, s5_backend as BK, s5_d7 as D
    ph = guards(token); t0 = time.time()
    r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_step2"))
    if not r.wasSuccessful(): raise RuntimeError(f"Step 2 unit tests failed: {len(r.failures)} failures, {len(r.errors)} errors")
    log(f"A21 preflight: protocol {ph[:16]}... FROZEN, canonical list, no lock, registry ok, A21 sidecar ok; {r.testsRun} Step 2 unit tests pass")
    excluded, _ = G.excluded_folds()
    if not set(CONTAMINATED) <= excluded: raise PermissionError("preflight folds must be contaminated")
    PRE.mkdir(parents=True, exist_ok=True); (PRE / "models").mkdir(exist_ok=True); rep = dict(d7_a21={}, step2={})
    # (1) A21 rule 1 D7 units on the MR2 fits
    D.A17 = MR2_A17; man = json.loads((MR2_A17 / "a17_results.json").read_text(encoding="utf-8"))["models_manifest"]; d7u = []
    for fold in CONTAMINATED:
        era, n = fold.split("|"); db = BK.DataBackend(era, int(n)); models, thr = D.load_fold_models(fold, man); u = D.fold_unit(db, fold, models, thr); d7u.append(u)
        bad = [v for dd in u["days"] for v in dd["vr"].values() if not np.isfinite(v)]
        if bad or not u["days"]: raise RuntimeError(f"D7 (A21) preflight {fold}: {len(u['days'])} days kept, {len(bad)} undefined ratios left")
        rep["d7_a21"][fold] = dict(days=len(u["days"]), skipped=u["skipped"]); log(f"A21 preflight D7 (MR2 fits) {fold}: {len(u['days'])} days kept, {len(u['skipped'])} skipped {[s['why'] for s in u['skipped']]}; no undefined ratio left")
        del db; gc.collect()
    a = D.aggregate(d7u); rep["d7_a21"]["pooled"] = dict(gates=a["gates"], vn={k: v.get("variance_neutral_share") for k, v in a["types"].items()})
    log(f"A21 preflight D7 pooled ({a['n_days']} days): variance-neutral shares {rep['d7_a21']['pooled']['vn']}; gates {a['gates']}")
    # (2) Step 2 full unit
    LiqBackend, _ = _classes(); s2u = []
    for fold in CONTAMINATED:
        era, n = fold.split("|"); db = LiqBackend(era, int(n)); c = db.c
        tg = np.concatenate([q["tgt"] for q in db.sequences("val", ())]); tg = tg[np.isfinite(tg)]
        if not (len(tg) > 1000 and 20 < np.median(tg) < 200): raise RuntimeError(f"liquidity target implausible at {fold}: median {np.median(tg) if len(tg) else 'none'} (60 x mean dvol expected near 60)")
        if c["cols"] != __import__("s5_lib").a20_pool(__import__("s5_lib").pools()[0]): raise RuntimeError("Step 2 pool is not the A20 pool")
        recs = {}
        for fam in FAMILIES:
            rr = unit(db, fold, fam, PRE / "models"); recs[fam] = rr
            if rr["b"] is None or not np.isfinite(rr["b"]) or not rr["qlike_test"].get("n"): raise RuntimeError(f"Step 2 preflight {fold} {fam}: score (a) not evaluable: {rr['b_skipped']}")
            log(f"A21 preflight Step 2 {fold} {fam}: features {rr['setup']['features']} params {rr['setup']['params']} baseline {rr['setup']['base_params']}; liquidity QLIKE base-feat {rr['b']:+.4f} "
                f"({rr['qlike_test']['pct']:+.1f}%), DM p {(rr['dm'] or {}).get('p_one_sided')}; thresholds {rr['thresholds']['feature']['threshold']:.2f}/{rr['thresholds']['baseline']['threshold']:.2f}; {rr['minutes']:.1f} min")
        models, thr = fold_models(fold, recs, PRE / "models"); u = D.fold_unit(db, fold, models, thr); s2u.append(u)
        g = D.aggregate([u]); log(f"A21 preflight Step 2 D7 {fold} ({g['n_days']} days): liquidity x2 sweep gain (feature) " + ", ".join(f"{f.split('_')[0]} {g['types']['liquidity:vol_x2'][f + '|feature']['diff']:+.2f}" for f in FAMILIES))
        rep["step2"][fold] = dict(units=recs, d7_days=len(u["days"])); del db; gc.collect()
    v = step2_d7_verdict(D.aggregate(s2u)); rep["step2"]["d7_pooled"] = v
    log(f"A21 preflight Step 2 D7 pooled ({v['n_days']} days): gate i {v['gate_i_share']}, iii {v['gate_iii']}, iv {v['gate_iv']} (not evaluable on 2 folds); gains x2 " +
        ", ".join(f"{f.split('_')[0]} {v['gains'][f]['vol_x2']['diff']:+.2f}" for f in FAMILIES))
    (PRE / "step2_preflight.json").write_text(json.dumps(rep, indent=1, default=float), encoding="utf-8"); log(f"A21 preflight PASSED in {(time.time() - t0) / 60:.1f} min (written to results/step2_preflight/)")
    return ph


# ---------- the run
def run(token):
    import s5_guard as G, s5_d7 as D
    ph = guards(token); _, LiqMain = _classes(); tag = tag_of(ph); CK.mkdir(parents=True, exist_ok=True); MODELS.mkdir(parents=True, exist_ok=True)
    b = LiqMain(ph); excluded, _ = G.excluded_folds(); folds = b.folds(); units, d7units = {}, []; t0 = time.time()
    log(f"Step 2 (liquidity) start: {len(folds)} folds x {len(FAMILIES)} families, then D7 on {len(folds) - len(excluded)} confirmatory folds; tag {tag['step2_script'][:12]}/{tag['d7_script'][:12]}")
    for k, fold in enumerate(folds, 1):
        recs = {}
        for fam in FAMILIES:
            p = CK / f"{fold.replace('|', '_')}_{fam}.json"
            if p.exists():
                u = json.loads(p.read_text(encoding="utf-8"))
                if u.get("tag") == tag: recs[fam] = u; continue
            G.check_unlocked("Step 2"); u = unit(b._b(fold), fold, fam, MODELS); u["tag"] = tag
            tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, default=float), encoding="utf-8"); tmp.replace(p); recs[fam] = u
            log(f"Step 2 fold {k}/{len(folds)} {fold} {fam}: features {u['setup']['features']} params {u['setup']['params']} baseline {u['setup']['base_params']}; b {u['b']}; {u['minutes']:.1f} min")
        for fam in FAMILIES: units[(fold, fam)] = recs[fam]
        if fold in excluded: continue
        p = CK / f"d7_{fold.replace('|', '_')}.json"
        if p.exists():
            u = json.loads(p.read_text(encoding="utf-8"))
            if u.get("tag") == tag: d7units.append(u); continue
        t1 = time.time(); models, thr = fold_models(fold, recs, MODELS); u = D.fold_unit(b._b(fold), fold, models, thr); u["tag"] = tag
        tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, default=float), encoding="utf-8"); tmp.replace(p); d7units.append(u)
        log(f"Step 2 D7 {fold}: {len(u['days'])} days ({len(u['skipped'])} skipped); {(time.time() - t1) / 60:.1f} min")
    res = aggregate(units, d7units, folds, excluded); res.update(label="Step 2 liquidity (AMENDMENT_A21.md rule 3)", tag=tag, hours=(time.time() - t0) / 3600)
    (OUT / "step2_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    log(f"Step 2 DONE in {(time.time() - t0) / 3600:.2f} h; results/step2_liquidity/step2_results.json written; no freeze, no era calibration"); return EXIT_OK


def main():
    if len(sys.argv) < 2: print(__doc__); return EXIT_GUARD
    token, check = sys.argv[1], "--check" in sys.argv[2:]
    import s5_d7 as D
    D.LOG = LOG; D.MAIN_DIR = MAIN2; D.A17 = MR2_A17
    guard_errors = (PermissionError, RuntimeError, AssertionError) if check else (PermissionError,)          # in the run, only guard refusals are not retried
    try:
        D.keep_awake(True)
        if check: preflight(token); return EXIT_OK
        return run(token)
    except guard_errors as e: log(f"Step 2 {'preflight ' if check else ''}REFUSED: {type(e).__name__}: {e}"); return EXIT_GUARD
    except KeyboardInterrupt: log("Step 2 STOPPED by the user (Ctrl+C); finished units are checkpointed"); return EXIT_STOP
    except BaseException as e:
        log(f"Step 2 CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return EXIT_CRASH
    finally: D.keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
