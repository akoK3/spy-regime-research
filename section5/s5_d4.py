#!/usr/bin/env python3
"""Diagnostic D4: pure synthetic power study with the frozen detector code and the D4 event rules. No market data.
Data: 78-update sessions of iid noise, Gaussian or Student-t (df 5, unit variance), variance ratio R in {2,3,5,10} at a random update j in 20..60, both directions
(up: sd 1 -> sqrt(R); down: sd sqrt(R) -> 1). Seeds: training (role 1), calibration nulls (2), test nulls (3), test up (4), test down (5); thresholds chosen on the
calibration seeds only, frozen, then scored on the test seeds (500 null, 500 up, 500 down per cell).
One model per (family, K, data type, R), fitted on 189 training sessions of the same R (40% calm, 20% stressed, 20% up, 20% down); inputs z-scored with the pooled
training mean/sd. Hit = confirmed alarm (T_c) within 12 updates after the break (break at update j; tau = availability of update j-1). Failures are recorded, nothing
is excluded. Two selection rules are computed from the same fits: 'smallest' = smallest grid value with calibration-null session false-alarm share <= 0.10 (run 1);
'maxhit' = among grid values with calibration false-alarm share <= 0.10, the one with the highest calibration hit rate (500 calibration up + 500 calibration down sessions, seeds 6 and 7), ties to the smallest (run 2). A detector with no feasible calibration threshold uses the strictest grid value and is flagged."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_events as E

T = 78; MIN = E.MIN; NTRAIN = 189; NCAL = 500; NTEST = 500; HIT_UPDATES = 12
RATIOS = [2, 3, 5, 10]; DTYPES = ["gaussian", "student_t5"]
HMM_GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.995, 0.999, 0.9999]
PROB_GRID = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99, 0.999]
DROP_GRID = [1, 2, 3, 5, 8, 12, 20, 30]
DETECTORS = [(f"{fam}|K={K}", fam, dict(K=K), "hmm", HMM_GRID) for fam in ("gaussian_hmm", "student_t_hmm", "hsmm") for K in (2, 3, 4)] + \
            [(f"bocpd|lam={lam}|{a}", "bocpd", dict(lam=lam), a, DROP_GRID if a == "b_map" else PROB_GRID) for lam in (12, 39, 78) for a in ("a_pcp3", "b_map", "c_r_lt_6")]


def gen(rng, dtype, kind, R, j=None):
    sd = np.ones(T)
    if kind == "stressed": sd[:] = np.sqrt(R)
    elif kind == "up": sd[j:] = np.sqrt(R)
    elif kind == "down": sd[:] = np.sqrt(R); sd[j:] = 1.0
    e = rng.standard_normal(T) if dtype == "gaussian" else rng.standard_t(5, T) * np.sqrt(3.0 / 5.0)
    return (e * sd)[:, None]


def seq(X, j=None, k=0):
    return dict(sess=k, n=len(X), X=X, real=np.ones(len(X), bool), avail=(np.arange(len(X)) + 1) * 5 * MIN, tgt=np.full(len(X), np.nan), slots=4 + 5 * np.arange(len(X)), start=0, grid_n=len(X), j=j)


def events(kind, r, q, thr):
    if kind == "hmm": return E.detect_old_state(r["P"], q["real"], q["avail"], thr)[0]
    if kind == "a_pcp3": return E.detect_bocpd(r["pcp"], q["real"], q["avail"], thr)[0]
    if kind == "c_r_lt_6": return E.detect_bocpd(r["pers"], q["real"], q["avail"], thr)[0]
    if kind == "b_map": return E.detect_bocpd_map(r["rstar"], q["real"], q["avail"], thr)[0]
    raise ValueError(kind)


def null_stats(kind, res, seqs, thr):
    evs = [events(kind, r, q, thr) for q, r in zip(seqs, res)]
    return float(np.mean([bool(e) for e in evs])), 20.0 * sum(len(e) for e in evs) / len(evs)


def break_stats(kind, res, seqs, thr):
    hits, dl = 0, []
    for q, r in zip(seqs, res):
        tau = q["j"] * 5 * MIN; ev = [e for e in events(kind, r, q, thr) if tau <= q["avail"][e["i_c"]] <= tau + HIT_UPDATES * 5 * MIN]
        if ev: hits += 1; dl.append((q["avail"][ev[0]["i_c"]] - tau) / MIN)
    return hits / len(seqs), (float(np.median(dl)) if dl else None)


def task(args):
    dtype, R = args; di = DTYPES.index(dtype); out = {}
    rng = lambda role: np.random.default_rng([role, di, R])
    r1 = rng(1); kinds = r1.choice(["calm", "stressed", "up", "down"], size=NTRAIN, p=[.4, .2, .2, .2]); tr = [gen(r1, dtype, k, R, int(r1.integers(20, 61))) for k in kinds]
    mu, sdv = np.mean(np.concatenate(tr)), np.std(np.concatenate(tr)); z = lambda X: (X - mu) / sdv
    trs = [seq(z(X), k=i) for i, X in enumerate(tr)]
    r2 = rng(2); cal = [seq(z(gen(r2, dtype, "calm", R))) for _ in range(NCAL)]
    r3 = rng(3); tn = [seq(z(gen(r3, dtype, "calm", R))) for _ in range(NTEST)]
    r6 = rng(6); r7 = rng(7); cu = []; cd = []
    for _ in range(NCAL):
        j = int(r6.integers(20, 61)); cu.append(seq(z(gen(r6, dtype, "up", R, j)), j=j))
        j = int(r7.integers(20, 61)); cd.append(seq(z(gen(r7, dtype, "down", R, j)), j=j))
    r4 = rng(4); tu = []; r5 = rng(5); td = []
    for _ in range(NTEST):
        j = int(r4.integers(20, 61)); tu.append(seq(z(gen(r4, dtype, "up", R, j)), j=j))
        j = int(r5.integers(20, 61)); td.append(seq(z(gen(r5, dtype, "down", R, j)), j=j))
    models = {}
    for name, fam, par, kind, grid in DETECTORS:
        mk = (fam, tuple(sorted(par.items())))
        if mk not in models:
            t0 = time.perf_counter(); m = V.make_model(fam, K=par.get("K", 3), lam=par.get("lam", 39), starts=1, seed=0); m.fit(L.pad(trs, 1)); fit_s = time.perf_counter() - t0
            models[mk] = (m, {nm: V.run_filter(fam, m, ss, 1) for nm, ss in (("cal", cal), ("tn", tn), ("tu", tu), ("td", td), ("cu", cu), ("cd", cd))}, fit_s)
        m, rr, fit_s = models[mk]
        feas = [g_ for g_ in grid if null_stats(kind, rr["cal"], cal, g_)[0] <= 0.10]
        calhit = {g_: (break_stats(kind, rr["cu"], cu, g_)[0] + break_stats(kind, rr["cd"], cd, g_)[0]) / 2 for g_ in feas}
        for rule in ("smallest", "maxhit"):
            if rule == "smallest": thr_ok = feas[0] if feas else None
            else: thr_ok = max(feas, key=lambda g_: (calhit[g_], -grid.index(g_))) if feas else None
            thr = thr_ok if thr_ok is not None else grid[-1]
            cal_fa = null_stats(kind, rr["cal"], cal, thr)[0]; fa, per20 = null_stats(kind, rr["tn"], tn, thr)
            hu, du = break_stats(kind, rr["tu"], tu, thr); hd, dd = break_stats(kind, rr["td"], td, thr)
            out[f"{rule}|{dtype}|R{R}|{name}"] = dict(threshold=thr, calibration_feasible=thr_ok is not None, cal_fa=cal_fa, cal_hit=calhit.get(thr), test_fa=fa, test_alarms_per20=per20, hit_up=hu, hit_down=hd, delay_up_min=du, delay_down_min=dd, fit_s=fit_s)
    return out


def main():
    import multiprocessing as mp
    T0 = time.time(); res = {}
    with mp.get_context("spawn").Pool(4) as pool:
        for o in pool.imap_unordered(task, [(d, R) for d in DTYPES for R in RATIOS]):
            res.update(o); print(f"[{(time.time()-T0)/60:5.1f} min] cells {len(res)}", flush=True)
    (L.HERE / "results" / "d4_results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
