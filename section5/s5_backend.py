#!/usr/bin/env python3
"""A10/A15: data backend for s5_run.py, one fold per instance. Real features, fitted models, splices. Guards: only folds listed in `allowed` (default ALLOWED_MACHINERY, the contaminated
RAW 3 and LEGACY 29); a fold that is not on the contamination list (a clean fold) is served only with the sha256 of the FROZEN protocol (A15 rule 5b). Models are fitted on the fold's
inner train; the era panel is read whole for the 20-session deseasonalising and splice baselines (past sessions only).
Selection (5.8) uses the fold's inner train and validation only; the test segment is read by score() only, after selection. Era-level thresholds (A11) are not served here (A15 rule 5c)."""
import sys, re, json, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_guard as G, s5_events as E, s5_lib as L, s5_eval as V, s5_fast as F, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_sweep as W

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
ALLOWED_MACHINERY = {"RAW|3", "LEGACY|29"}
HMM_GRID = [dict(K=2), dict(K=3), dict(K=4)]; HSMM_GRID = [dict(K=2), dict(K=3)]      # A11 item 2: 5.4 gives HSMM K 2-3; HMM families K 2-4
BOCPD_GRID = [dict(lam=12), dict(lam=39), dict(lam=78)]
TARGET = B.TARGET; BOUNDS = B.BOUNDS
sha = G.sha; verify_frozen_protocol = G.verify_frozen_protocol            # A16: guards live in s5_guard (fixed paths)


def era_context(era):
    """Era panel, primary columns, deseasonalising matrix and raw grid rows of every session (shared by the fold backends of one era)."""
    primary, _, _ = L.pools(); cols = primary
    d = L.load_era(era, cols + ["lee_mykland_approx60"]); dv = S.des_variance(d)
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    return dict(era=era, d=d, dv=dv, cols=cols, native=native, Mx=Mx)


def freeze_input_hashes():
    """A15 rule 6c: sha256 of the protocol, every amendment it integrates, the cited inputs, the folds CSV, the split manifest, the contamination list (canonical, A16 rule 2), the
    H1(c) times and the LEGACY and RAW panel and SPY ETF files."""
    G.canonical_contamination(); t = G.PROTOCOL.read_text(encoding="utf-8"); out = {"SECTION5_PROTOCOL.md": sha(G.PROTOCOL)}
    for f in sorted(set(re.findall(r"`(AMENDMENT_A[0-9_]+\.md)`", t))): out[f] = sha(ROOT / f)
    for f in sorted(set(re.findall(r"`(section431_step3_all_in_one_results/[^`]+)`", t))): out[f] = sha(ROOT / f)
    out["folds_csv"] = sha(L.R / "a4_development_nested_folds_TRAIN.csv"); out["split_manifest"] = sha(L.FZ / "section430_executable_split_manifest.csv")
    for q in (G.CONTAMINATION, HERE / "results" / "h1c_schedule_times.json"): out[f"section5/results/{q.name}"] = sha(q)
    s = L._step3()
    for era in ("LEGACY", "RAW"):
        _, _, pf, ef = s.CONFIG[era]
        for k, x in (("panel", pf), ("etf", ef)): fp = Path(s.file_path(x)); out[f"{era}_{k}:{fp.name}"] = sha(fp)
    return out


class DataBackend:
    kind = "data_fold"

    def __init__(self, era, fold, allowed=ALLOWED_MACHINERY, min_days=8, protocol_sha256=None, shared=None):
        self.era, self.fold, self.id = era, int(fold), f"{era}|{int(fold)}"; self.min_days = min_days
        if self.id not in allowed: raise PermissionError(f"{self.id} is not an allowed fold {sorted(allowed)}")
        excluded, _ = G.excluded_folds()                                                    # A16 rule 2: the canonical, hash-checked list only
        if self.id not in excluded:
            if protocol_sha256 is None: raise PermissionError(f"{self.id} is a clean fold (not on the contaminated list); machinery checks use contaminated folds only, the main run needs the frozen protocol hash")
            verify_frozen_protocol(protocol_sha256)
        if shared is not None and shared["era"] != era: raise ValueError("shared era context of another era")
        self._shared = shared; self._ctx = None; self._fits = {}; self._seqs = {}; self._splice = None

    # ---- context (lazy, once per fold)
    @property
    def c(self):
        if self._ctx is None: self._ctx = self._build()
        return self._ctx

    def _build(self):
        ctx = self._shared if self._shared is not None else era_context(self.era)
        d, dv, cols, native, Mx = ctx["d"], ctx["dv"], ctx["cols"], ctx["native"], ctx["Mx"]; names = [L.RET_NAME] + cols; seg = self._segments(d)
        to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
        rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train", "val", "test")}
        prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
        mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
        used = set(map(int, np.r_[seg["train"], seg["val"], seg["test"]])); L.assert_train_only(self.era, [d["day"][d["first"][i]] for i in sorted(used)])
        return dict(d=d, seg=seg, dv=dv, cols=cols, names=names, rows=rows, prep=prep, mk=mk, to_des=to_des, used=used, kept=set(prep.keep))

    def _segments(self, d): return L.fold_segments(d, self.era, self.fold)

    def sequences(self, split, subset):
        key = (split, tuple(subset))
        if key not in self._seqs: self._seqs[key] = [self.c["mk"](r, subset) for r in self.c["rows"][split]]
        return self._seqs[key]

    # ---- models
    def fit(self, family, subset, params, starts):
        key = (family, tuple(subset), tuple(sorted(params.items())), starts)
        if key not in self._fits:
            m = V.make_model(family, K=params.get("K", 3), lam=params.get("lam", 39), starts=starts, seed=0, Dmax=78); D = 1 + len(subset); m.fit(L.pad(self.sequences("train", subset), D)); self._fits[key] = m
        return self._fits[key]

    def qlike_on(self, family, model, subset, split):
        D = 1 + len(subset); tr = self.sequences("train", subset); values = V.state_values(family, V.run_filter(family, model, tr, D), tr)
        qs = self.sequences(split, subset); loss, key = V.qlike_series(family, V.run_filter(family, model, qs, D), qs, values); return loss, key

    # ---- backend interface
    def folds(self): return [self.id]
    def candidates(self, fold): self._chk(fold); return sorted(x for x in self.c["cols"] if x in self.c["kept"])
    def param_grid(self, family): return BOCPD_GRID if family == "bocpd" else HSMM_GRID if family == "hsmm" else HMM_GRID

    def _chk(self, fold):
        if fold != self.id: raise PermissionError(f"backend for {self.id} asked for {fold}")

    def objective(self, fold, family):
        self._chk(fold); G.check_unlocked("selection")                                       # A16 rule 5
        def f(subset, params, starts):
            m = self.fit(family, subset, params, starts); loss, _ = self.qlike_on(family, m, subset, "val"); loss = loss[np.isfinite(loss)]
            return dict(qlike=float(loss.mean()) if len(loss) else float("inf"), delay=float("nan"))       # delay not computed during search (A10 item 1)
        return f

    def _splices(self):
        if self._splice is None:
            c = self.c; stable, _ = S.stable_days(c["d"], c["seg"]["test"], c["dv"]); rng = np.random.default_rng(4242); cells = [(R, dr, du) for R in B.SIZES for dr in B.DIRS for du in B.DURS]
            specs, why = A.build_specs_safe(c["d"], c["dv"], stable, rng, A.N_NULL, cells, A.N_CELL, min_days=self.min_days)
            rows = []
            if specs: D2._W.update(d=c["d"], cols=c["cols"], bases=F.load_bases(c["d"], self.era, c["cols"]), dv=c["dv"]); rows = [D2._work(s) for s in specs]
            self._splice = dict(n_stable=len(stable), specs=specs, rows=rows, why=why)
        return self._splice

    def _h1a_points(self, family, model, subset):
        sp = self._splices(); null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
        D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA; to_des = self.c["to_des"]; mk = self.c["mk"]
        def run_(rl):
            qs = [mk(r, subset) for r in [to_des(r, r["iA"]) for r in rl]]; rs = V.run_filter(family, model, qs, D)
            R_, real, av = W.stack(rs, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
        sw = (lambda a, b, c_, t: W.sweep_map(a, b, c_, grid, t)) if family == "bocpd" else (lambda a, b, c_, t: W.sweep_old_state(a, b, c_, grid, t))
        R_, re_, av_, _ = run_(null); cnt, _ = sw(R_, re_, av_, None); xs = cnt.mean(0)
        R_, re_, av_, t_ = run_(brk); _, h = sw(R_, re_, av_, t_)
        return list(zip(xs.tolist(), h.mean(0).tolist()))

    def score(self, fold, family, setup):
        self._chk(fold); G.check_unlocked("scoring"); sp = self._splices(); feats = tuple(setup["features"]); params = dict(setup["params"])
        mf, mb = self.fit(family, feats, params, 3), self.fit(family, (), dict(setup["base_params"]), 3)      # A15 rule 1: the baseline with its own tuned K/lambda
        lf, kf = self.qlike_on(family, mf, feats, "test"); lb, kb = self.qlike_on(family, mb, (), "test"); failed = None
        if sp["n_stable"] >= self.min_days and sp["specs"]: pf, pb = self._h1a_points(family, mf, feats), self._h1a_points(family, mb, ())
        else:
            pf, pb = [], []
            if sp["n_stable"] >= self.min_days: failed = sp["why"] or "splice construction returned no specs"      # A15 rule 6b: a failure, not a skip
        flagged = any(m.fit_info.get("kept_fit_occupancy_ok", True) is False for m in (mf, mb) if hasattr(m, "fit_info"))      # A14.2: a kept Student-t fit with a state under 1%
        return dict(points_feat=pf, points_base=pb, n_stable_test=sp["n_stable"], loss_base=lb, key_base=kb, loss_feat=lf, key_feat=kf, val_qlike=setup["val_qlike"], flagged_fit=flagged, h1a_failed=failed)

    def final_thresholds(self, era, family, setup):
        """A7 rule on this fold's real validation sessions for the given (era-level final) setup; the era-level numeric threshold for 5.13 is not defined by A6-A10 (open)."""
        feats = tuple(setup["features"]); m = self.fit(family, feats, dict(setup["params"]), 3); D = 1 + len(feats); qs = self.sequences("val", feats); rs = V.run_filter(family, m, qs, D)
        kind = "bocpd" if family == "bocpd" else "hmm"; lo, hi, tol = BOUNDS[kind]; rate = lambda thr: sum(len(B.events(family, r, q, thr)) for q, r in zip(qs, rs)) / len(qs)
        thr, info = B.bisect_threshold(rate, lo, hi, TARGET, tol)
        det = (lambda r, q: E.detect_bocpd_map(r["rstar"], q["real"], q["avail"], thr)) if family == "bocpd" else (lambda r, q: E.detect_old_state_logodds(r["P"], q["real"], q["avail"], thr))
        open_share = float(np.mean([det(r, q)[1] for q, r in zip(qs, rs)]))          # A12 finding 15: sessions that end with an unconfirmed candidate
        return dict(rule="A7: bisection to 0.2 alarms per session on real validation sessions", fold=self.id, threshold=thr, validation_rate=rate(thr), open_candidate_share_at_close=open_share, numeric_era_threshold="see A11 for the era-level rule")

    def era_thresholds(self, era, family, setup, completion=None):
        raise PermissionError("era-level thresholds (A11) come only from MainBackend after a complete run (A15 rule 5c)")

    def input_hashes(self): return freeze_input_hashes()
