#!/usr/bin/env python3
"""D5 part B: 1-minute vs 5-minute grid, pure synthetic, Gaussian HMM / Student-t HMM / HSMM (K = 2, 3), the D4 old-state rule (P(old) < 1 - thr for 3 consecutive real
updates; 30-min refractory; first 2 updates silent), thresholds by the D4 'maxhit' rule (highest calibration hit rate subject to calibration null FA <= 10% of sessions).
Variance ratios 2, 3, 5, 10 (VARIANCE ratios). One underlying 390-minute iid series per session (Gaussian, or Student-t df 5 unit variance per minute); the 1-minute grid
uses the minutes (390 updates), the 5-minute grid uses sums of 5 consecutive minutes (78 updates), so both grids see the same process. Break at minute m = 5j, j uniform
20..60 (minutes 100-300); hit = confirmed alarm within 60 minutes of the break (60 updates at 1 minute, 12 at 5 minutes); tau = availability of the update before the break.
Models: 5-min grid fitted on 189 training sessions (14,742 updates, as D4); 1-min grid on 40 training sessions (15,600 updates, equal data), inputs z-scored with the pooled
training mean/sd of each grid. Counts per cell: 500 calibration nulls, 500 + 500 calibration breaks, 500 test nulls, 500 up + 500 down test breaks (separate seeds).
Timing: seconds to fit, and milliseconds per session to filter (cal + test sessions)."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_events as E

MIN = E.MIN; N = 500; RATIOS = [2, 3, 5, 10]; DTYPES = ["gaussian", "student_t5"]; GRIDS = ["5min", "1min"]
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm"]; KS = [2, 3]
GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.995, 0.999, 0.9999]


def minutes(rng, dtype, kind, R, j=None):
    sd = np.ones(390); m = None if j is None else 5 * j
    if kind == "stressed": sd[:] = np.sqrt(R)
    elif kind == "up": sd[m:] = np.sqrt(R)
    elif kind == "down": sd[:] = np.sqrt(R); sd[m:] = 1.0
    e = rng.standard_normal(390) if dtype == "gaussian" else rng.standard_t(5, 390) * np.sqrt(3.0 / 5.0)
    return e * sd


def to_grid(x1, grid): return x1[:, None] if grid == "1min" else x1.reshape(78, 5).sum(1)[:, None]


def seq(X, grid, j=None):
    n = len(X); step = 1 if grid == "1min" else 5
    return dict(sess=0, n=n, X=X, real=np.ones(n, bool), avail=(np.arange(n) + 1) * step * MIN, tgt=np.full(n, np.nan), slots=np.arange(n), start=0, grid_n=n, j=j)


def ev(res, q, thr): return E.detect_old_state(res["P"], q["real"], q["avail"], thr)[0]


def null_fa(rs, qs, thr): return float(np.mean([bool(ev(r, q, thr)) for r, q in zip(rs, qs)])), 20.0 * sum(len(ev(r, q, thr)) for r, q in zip(rs, qs)) / len(qs)


def brk(rs, qs, thr):
    h, dl = 0, []
    for r, q in zip(rs, qs):
        tau = q["j"] * 5 * MIN; e = [x for x in ev(r, q, thr) if tau <= q["avail"][x["i_c"]] <= tau + 60 * MIN]
        if e: h += 1; dl.append((q["avail"][e[0]["i_c"]] - tau) / MIN)
    return h / len(qs), (float(np.median(dl)) if dl else None)


def task(args):
    dtype, R, grid = args; di = DTYPES.index(dtype); out = {}
    rg = lambda role: np.random.default_rng([role, di, R, 31])
    r1 = rg(1); kinds = r1.choice(["calm", "stressed", "up", "down"], size=189, p=[.4, .2, .2, .2]); trx = [minutes(r1, dtype, k, R, int(r1.integers(20, 61))) for k in kinds]
    ntr = 189 if grid == "5min" else 40
    trg = [to_grid(x, grid) for x in trx[:ntr]]; mu, sdv = np.mean(np.concatenate(trg)), np.std(np.concatenate(trg)); z = lambda X: (X - mu) / sdv
    trs = [seq(z(X), grid) for X in trg]
    mkn = lambda role: (lambda g_: [seq(z(to_grid(minutes(g_, dtype, "calm", R), grid)), grid) for _ in range(N)])(rg(role))
    mkb = lambda role, kind: (lambda g_: [(lambda j: seq(z(to_grid(minutes(g_, dtype, kind, R, j), grid)), grid, j))(int(g_.integers(20, 61))) for _ in range(N)])(rg(role))
    sets = dict(cal=mkn(2), tn=mkn(3), cu=mkb(6, "up"), cd=mkb(7, "down"), tu=mkb(4, "up"), td=mkb(5, "down"))
    nsess = sum(len(v) for v in sets.values())
    for fam in FAMS:
        for K in KS:
            t0 = time.perf_counter(); m = V.make_model(fam, K=K, starts=1, seed=0, Dmax=(78 if grid == "5min" else 390)); m.fit(L.pad(trs, 1)); fit_s = time.perf_counter() - t0
            t0 = time.perf_counter(); rr = {k: V.run_filter(fam, m, v, 1) for k, v in sets.items()}; ms = 1000 * (time.perf_counter() - t0) / nsess
            feas = [g_ for g_ in GRID if null_fa(rr["cal"], sets["cal"], g_)[0] <= 0.10]
            ch = {g_: (brk(rr["cu"], sets["cu"], g_)[0] + brk(rr["cd"], sets["cd"], g_)[0]) / 2 for g_ in feas}
            thr_ok = max(feas, key=lambda g_: (ch[g_], -GRID.index(g_))) if feas else None; thr = thr_ok if thr_ok is not None else GRID[-1]
            fa, p20 = null_fa(rr["tn"], sets["tn"], thr); hu, du = brk(rr["tu"], sets["tu"], thr); hd, dd = brk(rr["td"], sets["td"], thr)
            out[f"{dtype}|R{R}|{grid}|{fam}|K={K}"] = dict(threshold=thr, calibration_feasible=thr_ok is not None, test_fa=fa, per20=p20, hit_up=hu, hit_down=hd, delay_up_min=du, delay_down_min=dd, fit_s=fit_s, filter_ms_per_session=ms)
    return out


def main():
    import multiprocessing as mp
    T0 = time.time(); res = {}
    jobs = [(d, R, g) for g in ("1min", "5min") for d in DTYPES for R in RATIOS]
    with mp.get_context("spawn").Pool(4) as pool:
        for o in pool.imap_unordered(task, jobs):
            res.update(o); print(f"[{(time.time()-T0)/60:5.1f} min] {len(res)} cells", flush=True)
    (L.HERE / "results" / "d5b_results.json").write_text(json.dumps(res, indent=1))


if __name__ == "__main__":
    main()
