#!/usr/bin/env python3
"""POST HOC benchmark (user order 2026-11-17): do the regime detectors beat simple volatility rules outside the model family? DEVELOPMENT folds only; run after the
5.12 freeze and the evaluation; changes no verdict and no frozen, MR2 or evaluation result; reads no evaluation-period data (DataBackend asserts TRAIN sessions only).
Writes only to section5/results/posthoc_benchmark/.

Benchmarks (f = rv10_partial90__sadj, the raw cached column value at the decision update, before the model preprocessing; past data only):
  B1  (primary)   s_t = |log(f_t / mean of f over the previous 60 minutes)|. "Previous 60 minutes" = the real decision updates j < t of the same session with
                  avail_j >= avail_t - 60 min (at most the 12 previous 5-min updates), f_j > 0; at least 2 such values, else s_t = NaN. s_t = NaN also if f_t <= 0.
  B1b (secondary) s_t = f_t (one-sided level rule).
  Alarm logic: s5_events.detect_old_state_logodds with the detector's log-odds replaced by s_t and nothing else: run of 3 consecutive real updates with s > theta
  (T_d = first, T_c = third), skips reset the count, no alarm on the first 2 updates (warm), the first real update starts the session, 30-min refractory period
  after T_c, a run open at the close is dropped. NaN s counts as "not above". Implemented as a scalar loop (events_scalar) and a vectorised sweep (sweep_scalar)
  mirroring s5_sweep.sweep_old_state; both are checked against the existing machinery in `check` (embedding s into a K-state P whose old state never changes).
  Updates, availability and real/skip flags are those of the fold's sequence for the subset (rv10_partial90__sadj,) built by the fold backend (DataBackend.c['mk']).
  Threshold: s5_a7.bisect_threshold to s5_a7.TARGET = 0.2 confirmed alarms per real validation session of the fold; bounds B1 [0, 8], B1b [0, 40], tol 1e-3.
  H1(a) curve: the same splices (DataBackend._splices, seed 4242), the same hit rule (T_d strictly after tau, T_c within 60 min) and s5_a6.pauc over null alarm
  rate 0-0.5; threshold grids (scale-specific, fixed here): B1 0..8 step 0.01 (801 values), B1b 0..40 step 0.02 (2001 values).
  H1(c): the fold's real test sessions at the fold threshold; the 98 eligible FOMC events and release minutes of the canonical contamination file; s5_h1c.hit
  (T_c minute = slot + 1 in [release, release + 60]); reference rate on the fold's non-FOMC test sessions (as s5_a17.aggregate).
  B2 (HAR): target = the existing next-60-min deseasonalised variance target (q['tgt'], A20 rule 2). Regressors at decision slot s0 of session i, from d['dv']
  (deseasonalised squared 1-min returns, causal): RVh = 60 * mean of dv over bars max(0, s0-59)..s0 of the session (>= 5 finite); RVd = 60 * mean of dv over
  session i-1 (>= 30 finite); RVw = mean of RVd over sessions i-1..i-5 (all 5 defined). OLS with intercept on the fold's inner-train decision bars (finite target
  and regressors). Forecast floored at s5_lib.QLIKE_FLOOR (1e-10; the target's own floor); scored with s5_eval.qlike_loss on the fold's test bars, key
  session*1000 + slot as s5_eval.qlike_series.
Comparison per fold and family (gaussian_hmm, student_t_hmm, hsmm, bocpd; the saved MR2 A17-style models, sha256-checked):
  H1(a)  pAUC(MR2 feature model) - pAUC(B1)  [and - pAUC(B1b)]; folds with < 8 stable test days are skipped as in MR2.
  H1(b)  mean QLIKE(HAR) - mean QLIKE(MR2 feature model) on their common bars (s5_eval.align); positive = detector better.
  Statistics: s5_h1.family_result (block-bootstrap p, 10,000 resamples, seed 0 / 1; sign consistency = share of folds > 0), confirmatory (26 folds) and all 34.
Reproduction (exit 4 on mismatch): per fold and family, pAUC(feature) - pAUC(baseline) recomputed with DataBackend._h1a_points must equal the MR2 unit 'a'
exactly, and h1b_fold_effect of the recomputed test losses must equal MR2 'b' and 'b_n' exactly; the feature pAUC is also compared with
posthoc_absolute_detection/units (reported).
Usage: posthoc_benchmark.py check                 synthetic checks only (no real data)
       posthoc_benchmark.py run WORKER NWORKERS     folds i with i % NWORKERS == WORKER; resumable, one JSON per fold; stops (exit 5) if the first fold
                                                    projects the worker beyond 180 min
       posthoc_benchmark.py combine                 posthoc_benchmark.json (+ .sha256) and BENCHMARK_FACTS.md, once
Exit codes: 0 done, 1 crash, 3 guard, 4 reproduction mismatch, 5 runtime projection over 3 h, 6 synthetic check failed."""
import sys, os, json, time, gc, hashlib, datetime, traceback
from pathlib import Path
import numpy as np

OUT = Path(__file__).resolve().parent; ROOT = OUT.parent.parent.parent; S5 = ROOT / "section5"; sys.path.insert(0, str(S5))
RES = S5 / "results"; UNITS = OUT / "units"; LOG = OUT / "log.txt"; FINAL = OUT / "posthoc_benchmark.json"; FACTS = OUT / "BENCHMARK_FACTS.md"; CHECK = OUT / "synthetic_check.json"
FAMS = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); CODE_VERSION = "a0323ed24d68e896"; FEAT = "rv10_partial90__sadj"
MIN = 60 * 10 ** 9; RUN, WARM, REFR = 3, 2, 30 * MIN
GRIDS = dict(B1=np.round(np.arange(0.0, 8.0 + 1e-9, 0.01), 2), B1b=np.round(np.arange(0.0, 40.0 + 1e-9, 0.02), 2))
BOUNDS = dict(B1=(0.0, 8.0, 1e-3), B1b=(0.0, 40.0, 1e-3)); MAX_MIN = 180.0
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


# ---------------------------------------------------------------- scores and alarm machinery
def score(f, real, avail, kind):
    """B1 / B1b score per update of one sequence (NaN = not above any threshold)."""
    f = np.asarray(f, float); n = len(f); s = np.full(n, np.nan); good = np.asarray(real, bool) & np.isfinite(f) & (f > 0)
    for i in range(n):
        if not good[i]: continue
        if kind == "B1b": s[i] = f[i]; continue
        j = [k for k in range(max(0, i - 12), i) if good[k] and avail[k] >= avail[i] - 60 * MIN]
        if len(j) >= 2: s[i] = abs(np.log(f[i] / np.mean(f[j])))
    return s


def events_scalar(s, real, avail, theta, run=RUN, warm=WARM, refractory=REFR):
    """s5_events.detect_old_state_logodds with lo replaced by s (no state, so no re-basing)."""
    events = []; started = False; cnt = 0; first = None; ref_until = -1
    for i in range(len(real)):
        if not real[i]: cnt = 0; continue
        if i < warm or not started: started = True; cnt = 0; continue
        if avail[i] < ref_until: cnt = 0; continue
        if s[i] > theta:                                   # NaN -> False
            if cnt == 0: first = i
            cnt += 1
            if cnt >= run: events.append(dict(i_d=first, i_c=i, state=-6)); ref_until = avail[i] + refractory; cnt = 0
        else: cnt = 0
    return events, int(cnt > 0)


def stack(svals, seqs):
    S = len(seqs); T = max([q["n"] for q in seqs] + [1]); V = np.full((S, T), np.nan); real = np.zeros((S, T), bool); avail = np.zeros((S, T), np.int64)
    for k, (q, s) in enumerate(zip(seqs, svals)):
        n = q["n"]
        if n: V[k, :n] = s[:n]; real[k, :n] = q["real"][:n]; avail[k, :n] = q["avail"][:n]
    return V, real, avail


def sweep_scalar(V, real, avail, thetas, taus=None, window=60 * MIN, run=RUN, warm=WARM, refractory=REFR):
    """s5_sweep.sweep_old_state with the log-odds replaced by the scalar score V (S, T)."""
    S, T = V.shape; G = len(thetas); th = np.asarray(thetas, float)[None, :]
    started = np.zeros((S, 1), bool); cnt = np.zeros((S, G), int); ref = np.full((S, G), -1, np.int64); fa = np.zeros((S, G), np.int64)
    counts = np.zeros((S, G), int); hit = np.zeros((S, G), bool); tau = None if taus is None else np.asarray(taus, np.int64)[:, None]
    for i in range(T):
        r = real[:, i][:, None]; a = avail[:, i][:, None]; pad = a == 0
        setcur = r & ((i < warm) | ~started); started = started | setcur
        inref = r & ~setcur & (a < ref)
        cnt = np.where(setcur | inref | (~r & ~pad), 0, cnt); active = r & ~setcur & ~inref
        if not active.any(): continue
        with np.errstate(invalid="ignore"): above = V[:, i][:, None] > th
        cond = active & above; fa = np.where(cond & (cnt == 0), a, fa); cnt = np.where(active, np.where(cond, cnt + 1, 0), cnt); fire = active & (cnt >= run)
        counts += fire
        if tau is not None: hit |= fire & (fa > tau) & (a <= tau + window)
        ref = np.where(fire, a + refractory, ref); cnt = np.where(fire, 0, cnt)
    return counts, hit


def calibrate(seqs, svals, kind):
    import s5_a7 as B
    lo, hi, tol = BOUNDS[kind]; rate = lambda thr: sum(len(events_scalar(s, q["real"], q["avail"], thr)[0]) for q, s in zip(seqs, svals)) / len(seqs)
    thr, info = B.bisect_threshold(rate, lo, hi, B.TARGET, tol); return dict(threshold=float(thr), info=info, validation_rate=float(rate(thr)), n_val=len(seqs))


def points(null_V, brk_V, kind):
    import s5_a6 as A
    cnt, _ = sweep_scalar(*null_V, GRIDS[kind]); xs = cnt.mean(0); _, h = sweep_scalar(*brk_V[:3], GRIDS[kind], brk_V[3]); pts = list(zip(xs.tolist(), h.mean(0).tolist()))
    return pts, float(A.pauc(pts))


# ---------------------------------------------------------------- HAR
def har_design(d, dv, rows):
    """Rows of (key, target, RVh, RVd, RVw) for every decision slot of the given native rows; NaN where undefined."""
    first, end = d["first"], d["end"]; rvd_cache = {}
    def rvd(i):
        if i not in rvd_cache:
            if i < 0: rvd_cache[i] = np.nan
            else:
                x = dv[int(first[i]):int(end[i])]; x = x[np.isfinite(x)]; rvd_cache[i] = 60.0 * float(x.mean()) if len(x) >= 30 else np.nan
        return rvd_cache[i]
    K, Y, Xs = [], [], []
    for r in rows:
        i = int(r["sess"]); a = int(first[i]); x1 = dv[a:int(end[i])]; dd = rvd(i - 1); ww = [rvd(i - k) for k in range(1, 6)]; w = float(np.mean(ww)) if all(np.isfinite(ww)) else np.nan
        for k, s0 in enumerate(r["slots"]):
            h = x1[max(0, int(s0) - 59):int(s0) + 1]; h = h[np.isfinite(h)]; rh = 60.0 * float(h.mean()) if len(h) >= 5 else np.nan
            K.append(i * 1000 + int(s0)); Y.append(r["tgt"][k]); Xs.append((rh, dd, w))
    return np.array(K, np.int64), np.array(Y, float), np.array(Xs, float)


def har_fit(Y, X):
    ok = np.isfinite(Y) & np.isfinite(X).all(1); Z = np.column_stack([np.ones(ok.sum()), X[ok]]); beta, *_ = np.linalg.lstsq(Z, Y[ok], rcond=None)
    return beta, int(ok.sum())


def har_losses(beta, K, Y, X):
    import s5_eval as V, s5_lib as L
    ok = np.isfinite(Y) & np.isfinite(X).all(1); f = np.column_stack([np.ones(len(X)), X]) @ beta; floored = int((ok & (f < L.QLIKE_FLOOR)).sum()); f = np.maximum(f, L.QLIKE_FLOOR)
    return V.qlike_loss(Y[ok], f[ok]), K[ok], floored


# ---------------------------------------------------------------- synthetic checks (no real data)
def synth_sessions(n, rng, ratio=None, tau_min=180):
    """390 one-minute returns per session, sigma 1e-3 (x sqrt(ratio) from minute tau_min on); f = 10-bar RV at grid slots 9, 14, ..., 389 (slot 4 lacks 10 bars),
    divided by its null expectation sqrt(10) * 1e-3 so that f is near 1 like the real __sadj column (a ratio to the slot median)."""
    out = []
    for _ in range(n):
        sd = np.full(390, 1e-3)
        if ratio: sd[tau_min:] *= np.sqrt(ratio)
        r = rng.standard_normal(390) * sd; slots = np.arange(9, 390, 5); f = np.array([np.sqrt((r[s - 9:s + 1] ** 2).sum()) for s in slots]) / (np.sqrt(10) * 1e-3)
        out.append(dict(n=len(slots), real=np.ones(len(slots), bool), avail=((slots + 1) * MIN).astype(np.int64), slots=slots, f=f, tau=int(tau_min * MIN)))
    return out


def check():
    import s5_events as E, s5_sweep as W, s5_a7 as B
    rng = np.random.default_rng(20261117); res = dict(label="POST HOC benchmark: synthetic checks (simulated data only)", checks={}); ok = True
    val, nul = synth_sessions(300, rng), synth_sessions(300, rng); brk = {R: synth_sessions(300, rng, R) for R in (3, 10)}
    for q in val + nul + [x for v in brk.values() for x in v]:
        if rng.random() < 0.3: q["real"] = q["real"].copy(); q["real"][rng.integers(0, q["n"])] = False        # some skipped updates
    for kind in ("B1", "B1b"):
        sv = [score(q["f"], q["real"], q["avail"], kind) for q in val]; cal = calibrate(val, sv, kind)
        sn = [score(q["f"], q["real"], q["avail"], kind) for q in nul]; null_rate = sum(len(events_scalar(s, q["real"], q["avail"], cal["threshold"])[0]) for q, s in zip(nul, sn)) / len(nul)
        hits = {}
        for R, qs in brk.items():
            sb = [score(q["f"], q["real"], q["avail"], kind) for q in qs]
            hits[R] = float(np.mean([E.hit_in_window(events_scalar(s, q["real"], q["avail"], cal["threshold"])[0], q["avail"], q["tau"]) for q, s in zip(qs, sb)]))
        plac = float(np.mean([E.hit_in_window(events_scalar(s, q["real"], q["avail"], cal["threshold"])[0], q["avail"], q["tau"]) for q, s in zip(nul, sn)]))
        c = dict(threshold=cal, null_test_alarm_rate=null_rate, hit60_ratio3=hits[3], hit60_ratio10=hits[10], hit60_null_placebo=plac,
                 pass_rate=bool(0.12 <= null_rate <= 0.30), pass_detect=bool(hits[10] >= 0.5 and hits[10] > plac + 0.2))
        ok &= c["pass_rate"] and c["pass_detect"]; res["checks"][kind] = c
    # machinery equivalence: loop vs sweep (all grid thresholds), loop vs detect_old_state_logodds and sweep vs sweep_old_state on an embedded P
    qs = nul[:150] + brk[10][:150]; sv = [score(q["f"], q["real"], q["avail"], "B1") for q in qs]; Vv, re_, av = stack(sv, qs); taus = np.array([q["tau"] for q in qs], np.int64)
    th = GRIDS["B1"][::10]; cnt, hit = sweep_scalar(Vv, re_, av, th, taus)
    loop_cnt = np.array([[len(events_scalar(s, q["real"], q["avail"], t)[0]) for t in th] for q, s in zip(qs, sv)])
    loop_hit = np.array([[E.hit_in_window(events_scalar(s, q["real"], q["avail"], t)[0], q["avail"], q["tau"]) for t in th] for q, s in zip(qs, sv)])
    K = 60; sc = np.clip(np.nan_to_num(Vv, nan=-1.0), -1.0, 3.5); po = 1 / (1 + np.exp(sc)); P = np.concatenate([po[..., None], np.repeat(((1 - po) / (K - 1))[..., None], K - 1, -1)], -1)
    assert (P.argmax(-1) == 0).all()
    th2 = [t for t in th if t <= 3.0]; e_cnt = np.array([[len(E.detect_old_state_logodds(P[k, :q["n"]], q["real"], q["avail"], t)[0]) for t in th2] for k, q in enumerate(qs)])
    w_cnt, w_hit = W.sweep_old_state(P, re_, av, th2, taus)
    m = len(th2); eq = dict(sweep_vs_loop_counts=bool((cnt == loop_cnt).all()), sweep_vs_loop_hits=bool((hit == loop_hit).all()),
                            loop_vs_detect_old_state_logodds=bool((loop_cnt[:, :m] == e_cnt).all()), sweep_vs_sweep_old_state=bool((cnt[:, :m] == w_cnt).all() and (hit[:, :m] == w_hit).all()),
                            thresholds=len(th), embedded_thresholds=m, sessions=len(qs))
    ok &= all(v for k, v in eq.items() if isinstance(v, bool)); res["checks"]["machinery_equivalence"] = eq
    # HAR: OLS recovers the coefficients of a simulated HAR process
    n = 5000; X = np.abs(rng.standard_normal((n, 3))) + 0.5; beta0 = np.array([0.1, 0.4, 0.3, 0.2]); Y = beta0[0] + X @ beta0[1:] + 0.01 * rng.standard_normal(n)
    b, nn = har_fit(Y, X); res["checks"]["har_ols"] = dict(beta=b.tolist(), true=beta0.tolist(), passed=bool(np.allclose(b, beta0, atol=0.01))); ok &= res["checks"]["har_ols"]["passed"]
    res["passed"] = bool(ok); res["script_sha256"] = sha(__file__); CHECK.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(json.dumps(res, indent=1, default=float))
    return 0 if ok else 6


# ---------------------------------------------------------------- real development folds
def guards():
    import s5_guard as G, s5_lib as L
    cv = G.code_version()
    if cv != CODE_VERSION: raise PermissionError(f"code version {cv} != {CODE_VERSION}")
    if not CHECK.exists() or not json.loads(CHECK.read_text(encoding="utf-8")).get("passed"): raise PermissionError("synthetic check missing or failed")
    if json.loads(CHECK.read_text(encoding="utf-8"))["script_sha256"] != sha(__file__): raise PermissionError("synthetic check was run with another version of this script")
    return G.frozen_protocol_hash(), {e: sha(L.CACHE / f"{e}_features.npz") for e in ("LEGACY", "RAW")}


def seqs_and_scores(db, rows, kinds=("B1", "B1b")):
    c = db.c; j = c["names"].index(FEAT); out = []
    for r in rows:
        q = c["mk"](r, (FEAT,)); f = r["X"][q["start"]:, j] if q["n"] else np.zeros(0)
        out.append((q, {k: score(f, q["real"], q["avail"], k) for k in kinds}))
    return out


def run(worker, nw):
    import s5_guard as G, s5_backend as BK, s5_a22 as A22, s5_a6 as A6, s5_h1 as H, s5_h1c as HC
    ph, cache0 = guards(); man = A22.a17_manifest(); mr2 = A22.mr2_units(); excluded, _ = G.excluded_folds(); UNITS.mkdir(parents=True, exist_ok=True)
    j, _ = G.contamination(); ev = j["h1c_eligible_events_per_fold"]; mins = j["h1c_event_release_minute_after_0930"]
    folds = [f for i, f in enumerate(G.MAIN_FOLDS) if i % nw == worker]; t_start = time.time(); done_here = 0
    log(f"worker {worker}/{nw}: start; code version {CODE_VERSION}; script {sha(__file__)[:16]}; {len(folds)} folds")
    ctx = None
    for fold in folds:
        p = UNITS / f"{fold.replace('|', '_')}.json"
        if p.exists(): continue
        era, n = fold.split("|"); t0 = time.time()
        if ctx is None or ctx["era"] != era: ctx = None; gc.collect(); ctx = BK.era_context(era)
        db = BK.DataBackend(era, int(n), allowed=set(G.MAIN_FOLDS), protocol_sha256=ph, shared=ctx); c = db.c
        models, _ = A22.load_models(fold, man); sp = db._splices(); n_st = sp["n_stable"]
        u = dict(fold=fold, confirmatory=fold not in excluded, n_stable_test=n_st, benchmarks={}, families={})
        # B1 / B1b: thresholds on validation, splice curves, FOMC on test
        val = seqs_and_scores(db, c["rows"]["val"]); test = seqs_and_scores(db, c["rows"]["test"]); d = c["d"]
        key = "LEGACY" + n if era == "LEGACY" else "RAW" + n; fomc_days = set(x for v in ev.values() for x in v); my_ev = ev.get(key, [])
        h1a_ok = n_st >= H.MIN_STABLE_TEST_DAYS and bool(sp["specs"])
        if h1a_ok:
            to_des = c["to_des"]; null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
            sn = seqs_and_scores(db, [to_des(r, r["iA"]) for r in null]); sb = seqs_and_scores(db, [to_des(r, r["iA"]) for r in brk]); taus = np.array([r["tau"] for r in brk], np.int64)
        for kind in ("B1", "B1b"):
            cal = calibrate([q for q, _ in val], [s[kind] for _, s in val], kind); thr = cal["threshold"]; b = dict(threshold=cal)
            al = {str(d["day"][d["first"][q["sess"]]]): [int(q["slots"][e["i_c"]]) + 1 for e in (events_scalar(s[kind], q["real"], q["avail"], thr)[0] if q["n"] else [])] for q, s in test}
            b["test_alarms_per_session"] = float(np.mean([len(v) for v in al.values()]))
            nonf = [dd for dd in al if dd not in fomc_days]
            b["fomc"] = [dict(date=x, release_minute=mins[x], hit=HC.hit(al.get(x, []), mins[x]), reference_rate=HC.reference_rate([al[dd] for dd in nonf], mins[x])) for x in my_ev]
            if h1a_ok:
                pts, pa = points(stack([s[kind] for _, s in sn], [q for q, _ in sn]), stack([s[kind] for _, s in sb], [q for q, _ in sb]) + (taus,), kind); b["pauc"] = pa
                b["null_alarm_range"] = [min(x for x, _ in pts), max(x for x, _ in pts)]
            else: b["pauc"] = None
            u["benchmarks"][kind] = b
        # HAR
        Ktr, Ytr, Xtr = har_design(d, c["dv"], c["rows"]["train"]); beta, ntr = har_fit(Ytr, Xtr); Kte, Yte, Xte = har_design(d, c["dv"], c["rows"]["test"])
        lh, kh, floored = har_losses(beta, Kte, Yte, Xte); u["benchmarks"]["HAR"] = dict(beta=beta.tolist(), n_train=ntr, n_test=int(len(lh)), floored=floored, mean_qlike=float(lh.mean()))
        # MR2 detectors: reproduction, then the comparisons
        absu = UNITS.parent.parent / "posthoc_absolute_detection" / "units" / f"{fold.replace('|', '_')}.json"; absu = json.loads(absu.read_text(encoding="utf-8")) if absu.exists() else None
        for fam in FAMS:
            (mf, sf), (mb, _) = models[fam]["feature"], models[fam]["baseline"]; st = mr2[("score", fold, fam)]; r = dict(subset=list(sf))
            lf, kf = db.qlike_on(fam, mf, sf, "test"); lb, kb = db.qlike_on(fam, mb, (), "test"); hb = H.h1b_fold_effect(lb, kb, lf, kf)
            if not (A22.same(hb["effect"], st["b"]) and hb["n"] == st["b_n"]): log(f"MISMATCH {fold} {fam} H1(b): {hb['effect']!r}/{hb['n']} != MR2 {st['b']!r}/{st['b_n']}"); return 4
            import s5_eval as V
            a_h, a_d, common = V.align(lh, kh, np.asarray(lf, float), np.asarray(kf)); okk = np.isfinite(a_h) & np.isfinite(a_d)
            r["h1b_vs_HAR"] = dict(effect=float(a_h[okk].mean() - a_d[okk].mean()), n=int(okk.sum()), mean_HAR=float(a_h[okk].mean()), mean_detector=float(a_d[okk].mean()),
                                   pct_of_HAR=float(100 * (a_h[okk].mean() - a_d[okk].mean()) / a_h[okk].mean()), dm=V.diebold_mariano(a_h[okk], a_d[okk], 12), mr2_b=st["b"])
            if h1a_ok:
                pf_pts, pb_pts = db._h1a_points(fam, mf, sf), db._h1a_points(fam, mb, ()); pf, pb = float(A6.pauc(pf_pts)), float(A6.pauc(pb_pts))
                eff = H.h1a_fold_effect(pf_pts, pb_pts, n_st)["effect"]
                if not (A22.same(pf - pb, st["a"]) and A22.same(eff, st["a"])): log(f"MISMATCH {fold} {fam} H1(a): {pf - pb!r}/{eff!r} != MR2 {st['a']!r}"); return 4
                r.update(pauc_feature=pf, pauc_baseline=pb, mr2_a=st["a"], abs_unit_feature_pauc_equal=(None if absu is None or "feature" not in absu["families"][fam] else A22.same(pf, absu["families"][fam]["feature"]["pauc"])),
                         h1a_vs_B1=pf - u["benchmarks"]["B1"]["pauc"], h1a_vs_B1b=pf - u["benchmarks"]["B1b"]["pauc"])
            else: r.update(pauc_feature=None, h1a_vs_B1=None, h1a_vs_B1b=None, h1a_skipped=f"{n_st} stable test days" if n_st < H.MIN_STABLE_TEST_DAYS else (sp["why"] or "no specs"))
            u["families"][fam] = r
        u["minutes"] = (time.time() - t0) / 60; done_here += 1
        tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, default=float), encoding="utf-8"); tmp.replace(p)
        log(f"{fold}: {n_st} stable days; pAUC B1 {u['benchmarks']['B1']['pauc']}, B1b {u['benchmarks']['B1b']['pauc']}; HAR QLIKE {u['benchmarks']['HAR']['mean_qlike']:.4f}; "
            + ", ".join(f"{f.split('_')[0]} pAUC {u['families'][f]['pauc_feature']} QLIKE {u['families'][f]['h1b_vs_HAR']['mean_detector']:.4f}" for f in FAMS) + f"; reproduction ok; {u['minutes']:.1f} min")
        del db; gc.collect()
        if done_here == 1:
            proj = u["minutes"] * len([f for f in folds if not (UNITS / f"{f.replace('|', '_')}.json").exists()]) + (time.time() - t_start) / 60
            log(f"worker {worker}: projected worker total {proj:.0f} min")
            if proj > MAX_MIN: log(f"worker {worker}: STOP, projection {proj:.0f} min > {MAX_MIN:.0f} min (exit 5)"); return 5
    _, cache1 = guards(); log(f"worker {worker}/{nw}: DONE; feature caches unchanged: {cache1 == cache0}"); return 0


# ---------------------------------------------------------------- combine
def combine():
    import s5_guard as G, s5_h1 as H, s5_h1c as HC
    if FINAL.exists(): print("exists; written once"); return 3
    files = sorted(UNITS.glob("*.json")); us = {json.loads(p.read_text(encoding="utf-8"))["fold"]: json.loads(p.read_text(encoding="utf-8")) for p in files}
    if len(us) != 34: print(f"{len(us)} units, expected 34"); return 3
    folds = list(G.MAIN_FOLDS); excluded, _ = G.excluded_folds(); a17 = json.loads((RES / "mr2" / "a17" / "a17_results.json").read_text(encoding="utf-8"))
    conf = [f for f in folds if f not in excluded]; mean = lambda xs: (float(np.mean(xs)) if xs else None)
    comp = {}
    for fam in FAMS:
        fr = {}
        for bm in ("B1", "B1b"):
            ea = [us[f]["families"][fam]["h1a_vs_" + bm] for f in folds]; eb = [us[f]["families"][fam]["h1b_vs_HAR"]["effect"] for f in folds]
            fr[bm] = H.family_result(ea, eb, folds, excluded, 10000, 0)
        comp[fam] = dict(h1a_vs_B1=dict(confirmatory=fr["B1"]["confirmatory"]["H1a"], all_folds=fr["B1"]["all_folds_sensitivity"]["H1a"]),
                         h1a_vs_B1b=dict(confirmatory=fr["B1b"]["confirmatory"]["H1a"], all_folds=fr["B1b"]["all_folds_sensitivity"]["H1a"]),
                         h1b_vs_HAR=dict(confirmatory=fr["B1"]["confirmatory"]["H1b"], all_folds=fr["B1"]["all_folds_sensitivity"]["H1b"]),
                         p_iu_vs_B1_HAR=dict(confirmatory=fr["B1"]["confirmatory"]["p_iu"], all_folds=fr["B1"]["all_folds_sensitivity"]["p_iu"]),
                         per_fold={f: dict(h1a_vs_B1=us[f]["families"][fam]["h1a_vs_B1"], h1a_vs_B1b=us[f]["families"][fam]["h1a_vs_B1b"], h1b_vs_HAR=us[f]["families"][fam]["h1b_vs_HAR"]["effect"]) for f in folds})
    absol = {}
    for scope, sel in (("confirmatory", conf), ("all_folds", folds)):
        a = {}
        for bm in ("B1", "B1b"):
            v = [us[f]["benchmarks"][bm]["pauc"] for f in sel if us[f]["benchmarks"][bm]["pauc"] is not None]
            a[bm] = dict(pauc_mean=mean(v), n_folds=len(v), threshold_median=float(np.median([us[f]["benchmarks"][bm]["threshold"]["threshold"] for f in sel])),
                         test_alarms_per_session_mean=mean([us[f]["benchmarks"][bm]["test_alarms_per_session"] for f in sel]),
                         thresholds_flagged=[f for f in sel if us[f]["benchmarks"][bm]["threshold"]["info"] != "ok"])
        a["HAR"] = dict(mean_qlike_fold_mean=mean([us[f]["benchmarks"]["HAR"]["mean_qlike"] for f in sel]), floored_total=int(sum(us[f]["benchmarks"]["HAR"]["floored"] for f in sel)))
        for fam in FAMS:
            pf = [us[f]["families"][fam]["pauc_feature"] for f in sel if us[f]["families"][fam]["pauc_feature"] is not None]
            pb = [us[f]["families"][fam]["pauc_baseline"] for f in sel if us[f]["families"][fam].get("pauc_baseline") is not None]
            hb = [us[f]["families"][fam]["h1b_vs_HAR"] for f in sel]
            a[fam] = dict(pauc_feature_mean=mean(pf), pauc_baseline_mean=mean(pb), n_folds_pauc=len(pf), qlike_detector_fold_mean=mean([x["mean_detector"] for x in hb]),
                          qlike_HAR_same_bars_fold_mean=mean([x["mean_HAR"] for x in hb]), qlike_pct_of_HAR_median=float(np.median([x["pct_of_HAR"] for x in hb])))
        absol[scope] = a
    fomc = {}
    for bm in ("B1", "B1b"):
        evs = [dict(e, fold=f) for f in folds for e in us[f]["benchmarks"][bm]["fomc"]]; hits = [e["hit"] for e in evs]
        fomc[bm] = dict(n_events=len(evs), hit_rate=mean([float(h) for h in hits]), wilson95=HC.wilson(int(sum(hits)), len(hits)), reference_alarm_rate=mean([e["reference_rate"] for e in evs]))
        bydate = {e["date"]: e["hit"] for e in evs}
        for fam in FAMS:
            de = a17["h1c"][fam]["events"]; hf = [bool(e["feature_hit"]) for e in de]; hbm = [bool(bydate[e["date"]]) for e in de]
            fomc[bm].setdefault("vs_detector", {})[fam] = dict(detector_hit_rate=a17["h1c"][fam]["f3"]["hit_rate"], benchmark_hit_rate=mean([float(x) for x in hbm]),
                                                              paired_detector_minus_benchmark=HC.paired_sign(hf, hbm))
    repro = dict(all_h1a_reproduced=True, all_h1b_reproduced=True, abs_unit_feature_pauc_equal={fam: [us[f]["families"][fam].get("abs_unit_feature_pauc_equal") for f in folds] for fam in FAMS})
    res = dict(label="POST HOC benchmark (user order 2026-11-17): MR2 detectors vs simple volatility rules (B1 threshold rule, B1b level rule) and HAR, development folds only. "
                     "Changes no verdict and no frozen, MR2 or evaluation result. Effects are detector minus benchmark (H1(a): pAUC; H1(b): QLIKE(HAR) - QLIKE(detector)), positive = detector better.",
               code_version=G.code_version(), script_sha256=sha(__file__), synthetic_check_sha256=sha(CHECK), units_sha256={p.name: sha(p) for p in files},
               comparison=comp, absolute=absol, fomc=fomc, reproduction=repro, har_beta_per_fold={f: us[f]["benchmarks"]["HAR"]["beta"] for f in folds},
               benchmark_pauc_per_fold={bm: {f: us[f]["benchmarks"][bm]["pauc"] for f in folds} for bm in ("B1", "B1b")},
               minutes=sum(u.get("minutes", 0) for u in us.values()), generated=datetime.datetime.now(datetime.timezone.utc).isoformat())
    FINAL.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); FINAL.with_suffix(".sha256").write_text(f"{sha(FINAL)}  {FINAL.name}\n", encoding="ascii")
    print(json.dumps(dict(comparison={k: {kk: vv for kk, vv in v.items() if kk != "per_fold"} for k, v in comp.items()}, absolute=absol, fomc=fomc), indent=1, default=float)); return 0


if __name__ == "__main__":
    try:
        if sys.argv[1:2] == ["check"]: sys.exit(check())
        if sys.argv[1:2] == ["run"]: sys.exit(run(int(sys.argv[2]), int(sys.argv[3])))
        if sys.argv[1:2] == ["combine"]: sys.exit(combine())
        print(__doc__); sys.exit(3)
    except PermissionError as e: log(f"REFUSED: {e}"); sys.exit(3)
    except SystemExit: raise
    except BaseException as e:
        log(f"CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        sys.exit(1)
