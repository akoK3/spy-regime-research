#!/usr/bin/env python3
"""AMENDMENT_A36 rule 5: the Section 5 side of the joint evaluation driver (protocol 5.13), outside the frozen result-module closure (code version a0323ed24d68e896).
It supplies fit_fn and run_fn to s5_eval_label.run_confirmatory_labelled (which wraps the frozen s5_freeze.run_confirmatory). Closure functions are called, never edited.

Per era:
  panel      TRAIN span followed by the evaluation span (A36 4a); the 5 embargo sessions between them are never read (1e). The evaluation span is opened only after
             s5_eval_loader.authorise (the evaluation guard and the access log; 7d). Features and their causal 20-session baselines are computed on the joined panel
             by the Section 4 code (s5_lib.compute_features); no era-named cache is read or written (the Section 5 caches hold TRAIN rows only).
  models     AMENDMENT_A37: fitted at the 5.12 freeze by s5_freeze_models (TRAIN only) and hashed into the freeze; here they are only loaded and checked (load_frozen,
             preflight, before the one-shot marker). fit_fn hands over the loaded state; run_fn starts with the guarded evaluation read. Nothing is fitted here.
  thresholds feature model: the frozen era-level threshold. Baseline: the A11 threshold computed on TRAIN at the freeze (A37 1b). The feature threshold recomputed
             at the freeze is compared with the frozen value; a difference is reported, the frozen value is used.
  H1(a)      pAUC(features) - pAUC(baseline) on splices of the stable evaluation days (main-run builders, seed 4242); skipped under 8 stable days (5d).
  H1(b)      mean QLIKE(baseline) - mean QLIKE(features) on common decision bars, and as a percentage of the baseline (5e).
  H1(c)      hit rates in [release, release + 60 min] on evaluation FOMC days with a time and a full session; reference rates on the other sessions (5f).
  intervals  95% percentile, day-cluster bootstrap, 2,000 resamples, seed 513: stable days (a), sessions (b), events (c). No p-value, no fold test, no Holm (5g).
  breaks     every run above the frozen feature threshold on the evaluation sessions, with the s5_break_export fields; the sessions with detector output (5h).
Nothing here runs before the 5.12 freeze. No market data is read at import."""
import sys, json, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE))
FOMC_EVAL = HERE / "results" / "h1c_schedule_times_evaluation.json"
NBOOT = 2000; SEED = 513; MIN_STABLE = 8; FULL = 390
_AUTH = {}      # era -> (freeze_path, token) set by the driver before the labelled 5.13 entry calls fit_fn (the frozen runner passes only era, setup and thresholds)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


# ---------- panel (A36 4a, 1e, 7d)
def _load_span(era, first, last):
    """One span of the canonical SPY panel and ETF file, by the audited Section 4 loader (endpoints must be sessions of the file)."""
    import s5_lib as L
    s = L._step3(); _, _, p, e = s.CONFIG[era]; spec = dict(first_session=first, last_session=last, panel_file=str(s.file_path(p)), etf_file=str(s.file_path(e)))
    d = s.load_development(era, spec); d.update(s.load_ohlc(spec, d)); return d


def concat(a, b):
    """Two panel dicts in time order as one (rows of b after rows of a; session offsets re-based)."""
    n = len(a["t"]); out = {k: np.concatenate([v, b[k]]) for k, v in a.items() if isinstance(v, np.ndarray) and k not in ("first", "end") and v.shape[:1] == (n,)}
    out["first"] = np.r_[a["first"], b["first"] + n].astype(np.int64); out["end"] = np.r_[a["end"], b["end"] + n].astype(np.int64); out["era"] = a["era"]; return out


def partitions(era):
    """{session day: partition} of the era in the frozen split manifest."""
    import pandas as pd, s5_lib as L
    mf = pd.read_csv(L.FZ / "section430_executable_split_manifest.csv"); mf = mf[mf.provider_era == era]; return dict(zip(mf.session_date.astype(str), mf.partition))


def check_partitions(era, days, n_tr):
    """The first n_tr sessions are exactly the era's TRAIN sessions and the rest exactly its EVALUATION_EXPOSED sessions; no embargo or excluded session (A36 1e)."""
    part = partitions(era); tr = sorted(x for x, p in part.items() if p == "TRAIN"); ev = sorted(x for x, p in part.items() if p == "EVALUATION_EXPOSED")
    if list(days[:n_tr]) != tr or list(days[n_tr:]) != ev: raise PermissionError(f"{era}: the joined panel is not TRAIN followed by EVALUATION_EXPOSED of the split manifest")
    return True


def panel(era, freeze_path, token):
    """(d, n_train_sessions). The evaluation span is read only after the guard has allowed and logged it."""
    import s5_eval_loader as EL
    EL.check_dev_spans(); (f, l), (ef, el) = EL.DEV[era], EL.EVAL[era]
    EL.authorise(era, freeze_path, token, section6=False, what="5.13 panel: SPY canonical panel and ETF file, evaluation span")
    tr = _load_span(era, f, l); ev = _load_span(era, ef, el); d = concat(tr, ev); d["era"] = era; n_tr = len(tr["first"])
    check_partitions(era, [str(d["day"][i]) for i in d["first"]], n_tr); return d, n_tr


def context(era, d):
    """As s5_backend.era_context, from a panel dict already in memory: A20 pool, deseasonalised target, grid rows, splice bases. No cache file."""
    import s5_lib as L, s5_d2_stable as S, s5_fast as F
    primary, _, _ = L.pools(); cols = L.a20_pool(primary); bn = F.bases_for(cols)
    feats = L.compute_features(d, list(dict.fromkeys(cols + ["lee_mykland_approx60"] + bn)))
    d["features"] = {c: feats[c] for c in cols + ["lee_mykland_approx60"]}; dv = S.des_variance(d); d["dv"] = dv
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    return dict(era=era, d=d, dv=dv, cols=cols, native=native, Mx=Mx, bases={n: feats[n] for n in bn})


# ---------- backend over the joined panel
def _backend_class():
    import s5_backend as BK, s5_lib as L, s5_fast as F, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_d2 as D2, s5_eval as V, s5_sweep as W

    class EvalBackend(BK.DataBackend):
        """DataBackend over given session segments of a context. Differences from the closure class, all in overrides: no fold table, no TRAIN-only assertion (the
        caller checks the partitions), splice bases from the context instead of the era-named cache, no selection and no fold scoring."""
        kind = "evaluation"

        def __init__(self, era, ctx, seg, prep=None, models=None):
            """prep / models (AMENDMENT_A37 rule 2b): the frozen preprocessing and {(family, subset, ((param, value), ...)): model} of the freeze; with models given, fit()
            never fits."""
            if ctx["era"] != era: raise ValueError("context of another era")
            self.era, self.fold, self.id = era, -2, f"{era}|EVAL"; self.min_days = MIN_STABLE; self._shared = ctx; self._seg = seg; self._ctx = None; self._fits = {}; self._seqs = {}; self._splice = None
            self._prep = prep; self._frozen = models is not None
            for (fam, sub, par), m in (models or {}).items(): self._fits[(fam, tuple(sub), tuple(sorted(dict(par).items())), 3)] = m

        def fit(self, family, subset, params, starts):
            if self._frozen:
                key = (family, tuple(subset), tuple(sorted(dict(params).items())), starts)
                if key not in self._fits: raise PermissionError(f"no model is fitted on the evaluation path (A37 2b): {family} {tuple(subset)} {dict(params)} is not a frozen model")
                return self._fits[key]
            return super().fit(family, subset, params, starts)

        def _segments(self, d): return self._seg

        def _build(self):
            ctx = self._shared; d, dv, cols, native, Mx = ctx["d"], ctx["dv"], ctx["cols"], ctx["native"], ctx["Mx"]; names = [L.RET_NAME] + cols; seg = self._seg
            to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
            rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train", "val", "test")}
            prep = self._prep if self._prep is not None else L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)      # A37 2b: the frozen preprocessing
            mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
            return dict(d=d, seg=seg, dv=dv, cols=cols, names=names, rows=rows, prep=prep, mk=mk, to_des=to_des, used=set(map(int, np.r_[seg["train"], seg["val"], seg["test"]])), kept=set(prep.keep))

        def objective(self, fold, family): raise PermissionError("no selection on the evaluation path (5.13: no retuning)")
        def score(self, fold, family, setup): raise PermissionError("fold scoring is not used on the evaluation path")
        def era_thresholds(self, *a, **k): raise PermissionError("era thresholds come from the freeze")

        def _splices(self):
            if self._splice is None:
                c = self.c; stable, _ = S.stable_days(c["d"], c["seg"]["test"], c["dv"]); rng = np.random.default_rng(4242); cells = [(R_, dr, du) for R_ in B.SIZES for dr in B.DIRS for du in B.DURS]
                specs, why = A.build_specs_safe(c["d"], c["dv"], stable, rng, A.N_NULL, cells, A.N_CELL, min_days=self.min_days); rows = []
                if specs: D2._W.update(d=c["d"], cols=c["cols"], bases=self._shared["bases"], dv=c["dv"]); rows = [D2._work(s) for s in specs]
                self._splice = dict(n_stable=len(stable), specs=specs, rows=rows, why=why)
            return self._splice

        def h1a_matrices(self, family, model, subset):
            """As DataBackend._h1a_points before averaging: (null alarm counts (n_null, G), null days, break hits (n_break, G), break days); day = the splice's session A."""
            sp = self._splices(); null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
            D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA; to_des = self.c["to_des"]; mk = self.c["mk"]

            def run_(rl):
                qs = [mk(r, subset) for r in [to_des(r, r["iA"]) for r in rl]]; rs = V.run_filter(family, model, qs, D)
                R_, real, av = W.stack(rs, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
            sw = (lambda a, b, c_, t: W.sweep_map(a, b, c_, grid, t)) if family == "bocpd" else (lambda a, b, c_, t: W.sweep_old_state(a, b, c_, grid, t))
            R_, re_, av_, _ = run_(null); cnt, _ = sw(R_, re_, av_, None); R_, re_, av_, t_ = run_(brk); _, h = sw(R_, re_, av_, t_)
            return np.asarray(cnt, float), np.array([r["iA"] for r in null]), np.asarray(h, float), np.array([r["iA"] for r in brk])
    return EvalBackend


def segments(n_tr, n_all):
    """(full, calibration) segment dicts. full: train = every TRAIN session, test = every evaluation session. calibration (A11 item 1): fit / embargo / calibration of TRAIN."""
    import s5_era_threshold as ET
    fit, emb, cal = ET.era_split(n_tr); e = np.array([], int)
    return dict(train=np.arange(n_tr), val=e, test=np.arange(n_tr, n_all)), dict(train=fit, val=cal, test=e, embargo=emb)


# ---------- intervals (A36 5g): day-cluster bootstrap, percentile
def _weights(n_clusters, nboot=NBOOT, seed=SEED): return np.random.default_rng(seed).multinomial(n_clusters, np.full(n_clusters, 1.0 / n_clusters), size=nboot).astype(float)


def ci_mean_diff(y1, y0, clusters, nboot=NBOOT, seed=SEED):
    """mean(y1) - mean(y0) over paired rows; 95% percentile interval resampling clusters with replacement."""
    y1, y0 = np.asarray(y1, float), np.asarray(y0, float)
    if len(y1) == 0: return dict(effect=None, ci95=None, n=0, n_clusters=0)
    u, inv = np.unique(np.asarray(clusters), return_inverse=True); n = np.bincount(inv, minlength=len(u)).astype(float); s1, s0 = np.bincount(inv, y1, len(u)), np.bincount(inv, y0, len(u))
    W = _weights(len(u), nboot, seed); N = W @ n; bs = (W @ s1 - W @ s0) / N; lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(effect=float(s1.sum() / n.sum() - s0.sum() / n.sum()), ci95=[float(lo), float(hi)], n=int(n.sum()), n_clusters=int(len(u)), mean1=float(s1.sum() / n.sum()), mean0=float(s0.sum() / n.sum()))


def ci_pauc_diff(mf, mb, nboot=NBOOT, seed=SEED):
    """mf, mb: h1a_matrices of the feature and baseline models on the same splices. pAUC(feature) - pAUC(baseline) and its interval; stable days resampled jointly for
    the null and the break splices; a resample without a null or a break splice is left out (counted)."""
    import s5_a6 as A
    cf, dn, hf, db_ = mf; cb, _, hb, _ = mb
    pa = lambda c, h, wn, wb: A.pauc(list(zip(((wn @ c) / wn.sum()).tolist(), ((wb @ h) / wb.sum()).tolist())))
    one_n, one_b = np.ones(len(dn)), np.ones(len(db_)); est = pa(cf, hf, one_n, one_b) - pa(cb, hb, one_n, one_b)
    days = np.unique(np.r_[dn, db_]); idn = np.searchsorted(days, dn); idb = np.searchsorted(days, db_); W = _weights(len(days), nboot, seed); bs = []
    for w in W:
        wn, wb = w[idn], w[idb]
        if wn.sum() > 0 and wb.sum() > 0: bs.append(pa(cf, hf, wn, wb) - pa(cb, hb, wn, wb))
    lo, hi = np.percentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan)
    return dict(effect=float(est), ci95=[float(lo), float(hi)], n_null=int(len(dn)), n_break=int(len(db_)), n_stable_days_in_splices=int(len(days)), n_valid_resamples=len(bs))


# ---------- FOMC events (A36 3d)
def fomc_minutes(path=None):
    """{day: release minute after 09:30} of the evaluation FOMC list (sidecar checked); meetings without a time are left out."""
    p = Path(path or FOMC_EVAL); side = p.with_suffix(".sha256")
    if not p.exists() or not side.exists() or side.read_text().split()[0] != sha(p): raise PermissionError(f"evaluation FOMC release-time list missing or differs from its sidecar: {p.name} (A36 3c)")
    return {d: int(v["minute_after_0930"]) for d, v in json.loads(p.read_text(encoding="utf-8"))["meetings"].items() if v.get("status") == "time"}


def h1c(alarms_f, alarms_b, minutes, full_days):
    """alarms_*: {day: [[T_d, T_c], ...]} over the evaluation sessions. Events: FOMC days with a time and a full session. Effect = hit rate(features) - hit rate(baseline)."""
    import s5_h1c as HC
    ev = sorted(x for x in minutes if x in alarms_f and x in full_days); non = [x for x in alarms_f if x not in minutes]
    hf = [HC.hit([a[1] for a in alarms_f[x]], minutes[x]) for x in ev]; hb = [HC.hit([a[1] for a in alarms_b.get(x, [])], minutes[x]) for x in ev]
    ref = lambda al: float(np.mean([HC.reference_rate([[a[1] for a in al.get(d, [])] for d in non], minutes[x]) for x in ev])) if ev and non else None
    out = ci_mean_diff(np.array(hf, float), np.array(hb, float), np.arange(len(ev))) if ev else dict(effect=None, ci95=None, n=0, n_clusters=0)
    out.update(n_events=len(ev), events=[dict(date=x, release_minute=minutes[x], feature_hit=bool(a), baseline_hit=bool(b)) for x, a, b in zip(ev, hf, hb)],
               feature=dict(hit_rate=(float(np.mean(hf)) if ev else None), wilson95=list(HC.wilson(int(np.sum(hf)), len(hf))), reference_alarm_rate=ref(alarms_f)),
               baseline=dict(hit_rate=(float(np.mean(hb)) if ev else None), wilson95=list(HC.wilson(int(np.sum(hb)), len(hb))), reference_alarm_rate=ref(alarms_b)),
               feature_only=int(np.sum(np.array(hf, bool) & ~np.array(hb, bool))) if ev else 0, baseline_only=int(np.sum(~np.array(hf, bool) & np.array(hb, bool))) if ev else 0)
    return out


# ---------- fit_fn / run_fn of the 5.13 runner
def build_state(era, d, n_tr):
    """Context and the two backends of one era from a joined panel."""
    ctx = context(era, d); full, cal = segments(n_tr, len(d["first"])); EB = _backend_class()
    return dict(era=era, ctx=ctx, n_train=n_tr, full=EB(era, ctx, full), cal=EB(era, ctx, cal))


def calibrate(state, family, features, params):
    """A11 item 1 on TRAIN only: A7 threshold of (features, params) on the calibration sessions of the calibration backend."""
    r = state["cal"].final_thresholds(state["era"], family, dict(features=list(features), params=dict(params))); return float(r["threshold"]), float(r["validation_rate"])


_PRELOADED = {}      # era -> the state preflight() loaded and verified (AMENDMENT_A37 rule 3a: fit_fn only hands it over)


def load_frozen(era, fz, frozen_dir=None):
    """AMENDMENT_A37 rule 2a: the era's frozen model files, each checked against the freeze document (sha256), the manifest against its sidecar, every setup against the
    freeze's final setup; the feature-threshold reproduction recorded (frozen value used). No data is read, nothing is fitted. Returns dict(era, bundles={family: bundle})."""
    import pickle, s5_h1 as H, s5_freeze_models as FM
    rec = (fz.get("input_hashes") or {}).get("frozen_models")
    if not rec: raise PermissionError("the freeze document records no frozen models (A37 1e): the evaluation step cannot fit")
    d = Path(frozen_dir or FM.FROZEN_DIR); mp = FM.manifest_path(d); side = mp.with_suffix(".sha256")
    if not mp.exists() or not side.exists() or side.read_text().split()[0] != sha(mp) or sha(mp) != rec["manifest_sha256"]: raise PermissionError("frozen-model manifest missing or differs from the freeze (A37 2a)")
    out = {}
    for fam in H.FAMILIES:
        name = FM.file_name(era, fam); p = d / name
        if name not in rec["files"] or not p.exists() or sha(p) != rec["files"][name]: raise PermissionError(f"frozen model {name} missing or differs from the freeze (A37 2a)")
        b = pickle.loads(p.read_bytes()); s = fz["setups"][era][fam]; part = partitions(era); tr = sorted(x for x, q in part.items() if q == "TRAIN")
        if (b["n_train"], b["train_first"], b["train_last"]) != (len(tr), tr[0], tr[-1]): raise PermissionError(f"frozen model {name}: its TRAIN sessions differ from the split manifest (A37 1c)")
        if b["era"] != era or b["family"] != fam or list(b["features"]) != list(s["features"]) or dict(b["params"]) != dict(s["params"]) or dict(b["base_params"]) != dict(s.get("base_params") or s["params"]):
            raise PermissionError(f"frozen model {name}: its setup differs from the freeze's final setup (A37 2a)")
        thr_f = float(fz["thresholds"][era][fam]["threshold"]); b["thresholds"] = dict(b["thresholds"], feature_frozen=thr_f, frozen_threshold_reproduced=bool(abs(b["thresholds"]["feature_recomputed"] - thr_f) <= 1e-9))
        b["sha256"] = rec["files"][name]; out[fam] = b
    return dict(era=era, bundles=out)


def preflight(era, freeze_path, token, frozen_dir=None):
    """Everything that can fail before the one-shot marker (A37 rule 2a): freeze and token, frozen models, FOMC list, and the evaluation guard's checks without a read."""
    import s5_freeze as FZ, s5_eval_loader as EL
    fz = FZ.verify_freeze(freeze_path)
    if token != FZ.sha(freeze_path): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    st = load_frozen(era, fz, frozen_dir); fomc_minutes(); EL.precheck(era, freeze_path, token, section6=False); return st


def fit_fn(era, setup, thresholds):
    """5.13 fit under A37 rule 3a: the frozen runner has just written the marker. Nothing is fitted and nothing is read: the state preflight() loaded is handed over."""
    st = _PRELOADED.get(era)
    if st is None: raise PermissionError("no frozen models were loaded for this era before the marker (A37 2a; s5_eval513.preflight)")
    return st


def build_eval_state(era, d, n_tr, bundles):
    """Context of the joined panel and the evaluation backend holding the frozen preprocessing and models (A37 2b)."""
    ctx = context(era, d); full, _ = segments(n_tr, len(d["first"])); preps = {id(b["prep"]): b["prep"] for b in bundles.values()}
    models = {}
    for fam, b in bundles.items(): models[(fam, tuple(b["features"]), tuple(sorted(b["params"].items())))] = b["feature"]; models[(fam, (), tuple(sorted(b["base_params"].items())))] = b["baseline"]
    prep = next(iter(bundles.values()))["prep"]
    if any(p.keep != prep.keep or p.mu != prep.mu for p in preps.values()): raise PermissionError("the frozen models of one era carry different preprocessing")
    return dict(era=era, ctx=ctx, n_train=n_tr, full=_backend_class()(era, ctx, full, prep=prep, models=models))


def run_fn(era, st, setup, thresholds, minutes=None):
    """5.13 run on the evaluation sessions of one era: effects with intervals (no p), alarms, breaks. The result is labelled by the caller (s5_eval_label).
    A37 rule 3a: the first action is the guarded evaluation read; the models are the frozen ones (st from preflight); nothing is fitted."""
    import s5_h1 as H, s5_eval as V, s5_a6 as A, s5_a17_a18_common as CM, s5_break_export as BX
    if era not in _AUTH: raise PermissionError("the joint driver did not register the freeze for this era (s5_eval513._AUTH)")
    dd, n_tr = panel(era, *_AUTH[era])                                                   # the first evaluation-data read, right after the marker
    bundles = st["bundles"]; minutes = fomc_minutes() if minutes is None else minutes; est = build_eval_state(era, dd, n_tr, bundles)
    db = est["full"]; d = db.c["d"]; seg = db.c["seg"]; day = lambda i: str(d["day"][d["first"][int(i)]])
    ev_days = [day(i) for i in seg["test"]]; full_days = {day(i) for i in seg["test"] if int(d["end"][i] - d["first"][i]) == FULL}
    out = dict(kind="section5_513_evaluation", era=era, amendment="A36 rule 5 as amended by A37", n_train_sessions=int(n_tr), n_evaluation_sessions=len(ev_days), first_evaluation_day=ev_days[0], last_evaluation_day=ev_days[-1],
               statistics="effect sizes with 95% percentile day-cluster bootstrap intervals (2,000 resamples, seed 513); no p-value, no fold test, no Holm (A36 5g)",
               models="frozen at 5.12 and loaded, sha256 checked against the freeze (A37); nothing fitted on the evaluation path", families={}, breaks=[], sessions=sorted(ev_days))
    for fam in H.FAMILIES:
        b = bundles[fam]; mf, mb, feats = b["feature"], b["baseline"], tuple(b["features"]); thr_f = float(thresholds[fam]["threshold"]); thr_b = float(b["thresholds"]["baseline_a11"])
        m = dict(params=dict(b["params"]), base_params=dict(b["base_params"]))
        r = dict(features=list(feats), params=m["params"], base_params=m["base_params"], model_sha256=b["sha256"],
                 thresholds=dict(b["thresholds"], feature_frozen=thr_f, note="the frozen feature threshold is the one used; the baseline threshold was set by A11 on TRAIN at the freeze (A37 1b)"))
        lf, kf = db.qlike_on(fam, mf, feats, "test"); lb, kb = db.qlike_on(fam, mb, (), "test"); xb, xf, common = V.align(np.asarray(lb, float), np.asarray(kb), np.asarray(lf, float), np.asarray(kf))
        ok = np.isfinite(xb) & np.isfinite(xf); b = ci_mean_diff(xb[ok], xf[ok], (np.asarray(common)[ok] // 1000))
        r["H1b"] = dict(b, definition="mean QLIKE(baseline) - mean QLIKE(features), common decision bars; clusters = sessions", pct_of_baseline=(float(100 * b["effect"] / b["mean1"]) if b["effect"] is not None and b["mean1"] else None))
        sp = db._splices()
        if sp["n_stable"] < MIN_STABLE: r["H1a"] = dict(effect=None, ci95=None, skipped=f"{sp['n_stable']} < {MIN_STABLE} stable evaluation days", n_stable_days=sp["n_stable"])
        elif not sp["specs"]: r["H1a"] = dict(effect=None, ci95=None, failed=sp["why"] or "splice construction returned no specs", n_stable_days=sp["n_stable"])
        else:
            a = ci_pauc_diff(db.h1a_matrices(fam, mf, feats), db.h1a_matrices(fam, mb, ())); r["H1a"] = dict(a, definition="pAUC(features) - pAUC(baseline); clusters = stable days", n_stable_days=sp["n_stable"])
        al_f = CM.test_alarms(db, fam, feats, m["params"], thr_f); al_b = CM.test_alarms(db, fam, (), m["base_params"], thr_b)
        r["H1c"] = dict(h1c(al_f, al_b, minutes, full_days), definition="hit rate(features) - hit rate(baseline) in [release, release + 60 min]; clusters = events")
        r["alarms_per_session"] = dict(feature=float(np.mean([len(v) for v in al_f.values()])), baseline=float(np.mean([len(v) for v in al_b.values()])))
        r["flagged_fit"] = bool(any(x.fit_info.get("kept_fit_occupancy_ok", True) is False for x in (mf, mb) if hasattr(x, "fit_info")))
        qs = db.sequences("test", feats); rs = V.run_filter(fam, mf, qs, 1 + len(feats)); meta = dict(fold=f"{era}|EVAL", era=era, K=getattr(mf, "K", None))
        for q, x in zip(qs, rs): out["breaks"] += BX.session_rows(fam, mf, x, q, thr_f, day(q["sess"]), meta)
        out["families"][fam] = r
    out["n_breaks_by_family_kind"] = {f"{f}|{k}": sum(1 for x in out["breaks"] if x["family"] == f and x["kind"] == k) for f in H.FAMILIES for k in ("confirmed", "fizzle", "open_at_close")}
    return out
