#!/usr/bin/env python3
"""Diagnostic D2 (RAW fold 3, VALIDATION sessions only; same frozen detectors and fixed feature sets as the pilot; no selection; no evaluation data).
Stable days are defined in s5_d2_stable.py before any detector runs. Null = splice of two stable days of the same volatility tercile. Breaks = stable-day splices
whose post-tau segment (B's bars with 1-min returns, ranges and price excursions scaled by f, volume unchanged) has a deseasonalised variance equal to R x the
pre-tau variance of A (R in 1.5,2,3,5,10 up; 1/R down), permanent (to the close) or a temporary sandwich of 30/60/120 min after which A's own path continues
(price-continuous). Hit = confirmed (T_c) within 60 min of tau (also for sandwiches, whether or not the sandwich has ended by T_c)."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E, s5_d2_stable as S

SIZES = [1.5, 2, 3, 5, 10]; DURS = [None, 30, 60, 120]; DIRS = ["up", "down"]
N_CELL = 24; N_NULL = 400; N_OLD = 100
THS = [0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 0.9999]
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = dict(base=[], f3=P.FIXED3, f6=P.FIXED6)
G_MAX = 264                                              # so that g + 120 + 1 <= 389 for every duration
_W = {}


def finite_ok(d, iA, iB, g, e):
    fa, fb = int(d["first"][iA]), int(d["first"][iB])
    idx = [fa + g, fb + g, fb + g + 1] + ([fb + e, fa + e, fa + e + 1] if e is not None else [])
    ok = np.isfinite(d["close"][idx]).all() and d["valid"][fb + g + 1] and d["valid"][fb + g]
    if e is not None: ok = ok and d["valid"][fa + e + 1] and d["valid"][fa + e]
    return bool(ok)


def regime_panel(d, iA, iB, g, f, dur):
    p = L.sub_panel(d, [iA]); m = 390; fa, fb = int(d["first"][iA]), int(d["first"][iB])
    A = {k: d[k][fa:fa + m].copy() for k in ("open", "high", "low", "close", "volume", "range", "r", "valid")}
    B = {k: d[k][fb:fb + m] for k in ("open", "high", "low", "close", "volume", "range", "r", "valid")}
    e = m - 1 if dur is None else g + dur
    j = np.arange(g + 1, e + 1); base = np.log(A["close"][g]); ref = np.log(B["close"][g])
    for k in ("open", "high", "low", "close"): p[k][j] = np.exp(base + f * (np.log(B[k][j]) - ref))
    p["r"][j] = f * B["r"][j]; p["range"][j] = f * B["range"][j]; p["volume"][j] = B["volume"][j]
    p["valid"][j] = B["valid"][j]; p["valid"][g + 1] = bool(B["valid"][g + 1] and B["valid"][g])
    if dur is not None:
        j2 = np.arange(e + 1, m); sh = np.log(p["close"][e]) - np.log(A["close"][e])
        for k in ("open", "high", "low", "close"): p[k][j2] = np.exp(np.log(A[k][j2]) + sh)
        for k in ("r", "range", "volume", "valid"): p[k][j2] = A[k][j2]
        p["valid"][e + 1] = bool(A["valid"][e + 1] and A["valid"][e])
    return p, int(p["available"][g])


def _init(cols):
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); _W.update(d=d, cols=cols, bases=F.load_bases(d, "RAW", cols), dv=S.des_variance(d))


def _work(sp):
    d, cols = _W["d"], _W["cols"]
    if sp["kind"] == "plain": return F.splice_rows_fast(d, _W["bases"], sp["iA"], sp["iB"], sp["g"], cols)
    p, tau = regime_panel(d, sp["iA"], sp["iB"], sp["g"], sp["f"], sp["dur"])
    return F.rows_from_panel(d, _W["bases"], p, sp["iA"], sp["iB"], sp["g"], tau, cols)


def wilson(k, n, z=1.96):
    ph = k / n; den = 1 + z * z / n; c = (ph + z * z / (2 * n)) / den; h = z * np.sqrt(ph * (1 - ph) / n + z * z / (4 * n * n)) / den
    return max(0.0, c - h), min(1.0, c + h)


def main():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
    stable = json.loads((L.HERE / "results" / "d2_stable_days.json").read_text())["stable"]
    assert set(stable) <= set(seg["val"].tolist()), "stable days must be validation sessions"
    rng = np.random.default_rng(P.SEED + 500)
    rv, _, _ = V.session_stats(d, stable); tv = V.tercile(rv); stable = np.array(stable)
    # ---- specs
    specs = []
    for _ in range(N_NULL):
        for _t in range(200):
            c = np.where(tv == int(rng.integers(3)))[0]
            if len(c) < 2: continue
            A, B = rng.choice(c, 2, replace=False); A, B = int(stable[A]), int(stable[B]); g = int(rng.choice(V.TAU_SLOTS))
            if finite_ok(d, A, B, g, None): break
        else: raise RuntimeError("null pair")
        specs.append(dict(kind="plain", cell="null", iA=A, iB=B, g=g))
    for R in SIZES:
        for dr in DIRS:
            for du in DURS:
                for _ in range(N_CELL):
                    for _t in range(500):
                        A, B = (int(x) for x in rng.choice(stable, 2, replace=False)); g = int(rng.choice([t for t in V.TAU_SLOTS if t <= G_MAX])); e = None if du is None else g + du
                        if finite_ok(d, A, B, g, e): break
                    else: raise RuntimeError("break pair")
                    fa, fb = int(d["first"][A]), int(d["first"][B]); last = 389 if du is None else g + du
                    pre = np.nanmean(dv[fa + 1:fa + g + 1]); post = np.nanmean(dv[fb + g + 1:fb + last + 1]); tgt = R if dr == "up" else 1.0 / R
                    f = float(np.sqrt(tgt * pre / post)); specs.append(dict(kind="regime", cell=(R, dr, du), iA=A, iB=B, g=g, f=f, dur=du, f2=f * f, r60=float(f * f * np.nanmean(dv[fb + g + 1:fb + g + 61]) / pre)))
    r_old = np.random.default_rng(P.SEED + 300); old_b, old_n = V.sample_pairs(d, seg["val"], N_OLD, N_OLD, r_old)       # the earlier tercile test (identical sampling)
    for sp in old_b + old_n: sp["kind"] = "plain"; sp["cell"] = "old_break" if sp in old_b else "old_null"
    allsp = specs + old_b + old_n
    t = time.perf_counter()
    with mp.get_context("spawn").Pool(4, initializer=_init, initargs=(cols,)) as pool: allrows = pool.map(_work, allsp, chunksize=8)
    log(f"{len(allsp)} rows built in {time.perf_counter()-t:.0f}s")
    # ---- construction checks on real panels
    checks = []
    for sp in [s_ for s_ in specs if s_["kind"] == "regime"][::97][:8]:
        p, tau = regime_panel(d, sp["iA"], sp["iB"], sp["g"], sp["f"], sp["dur"]); g = sp["g"]; fa = int(d["first"][sp["iA"]]); fb = int(d["first"][sp["iB"]])
        last = 389 if sp["dur"] is None else g + sp["dur"]
        c1 = bool(p["close"][g] == d["close"][fa + g]); c2 = bool(np.isclose(np.log(p["close"][g + 1] / p["close"][g]), sp["f"] * d["r"][fb + g + 1], rtol=1e-9, atol=1e-14))
        dvA = dv[fa:fa + 390]; pre = np.nanmean(dvA[1:g + 1]); postsc = sp["f"] ** 2 * np.nanmean(dv[fb + g + 1:fb + last + 1]); c3 = bool(np.isclose(postsc / pre, sp["f2"] * 0 + (sp["cell"][0] if sp["cell"][1] == "up" else 1 / sp["cell"][0]), rtol=1e-9))
        c4 = True
        if sp["dur"] is not None:
            e = g + sp["dur"]; c4 = bool(np.isclose(np.log(p["close"][e + 1] / p["close"][e]), d["r"][fa + e + 1], rtol=1e-9, atol=1e-14) and np.isclose(np.log(p["close"][389] / p["close"][e]), np.log(d["close"][fa + 389] / d["close"][fa + e]), rtol=1e-9, atol=1e-14))
        checks.append(dict(cell=str(sp["cell"]), price_at_g_unchanged=c1, return_across_tau_is_f_times_B=c2, deseasonalised_variance_ratio_equals_target=c3, sandwich_tail_continuous=c4))
    log("construction checks: " + str(all(all(v for k, v in c.items() if k != "cell") for c in checks)))
    # ---- detectors (frozen: pilot fits) and scoring
    rows_tr = [L.session_grid(d, i, cols) for i in seg["train"]]; prep = L.Prep().fit(np.vstack([r["X"] for r in rows_tr]), names)
    cellrows = {}
    for sp, r in zip(allsp, allrows): cellrows.setdefault(sp["cell"], []).append(r)
    out = dict(stable_days=[int(x) for x in stable], n_cell=N_CELL, n_null=N_NULL, n_old=N_OLD, construction_checks=checks, f2_quantiles={}, fa={}, hit={}, old={})
    for (R, dr, du), _ in [(k, v) for k, v in cellrows.items() if isinstance(k, tuple)]:
        out["f2_quantiles"][f"{R}|{dr}|{du}"] = [round(float(x), 2) for x in np.quantile([s_["f2"] for s_ in specs if s_["cell"] == (R, dr, du)], [.1, .5, .9])]
    out["realized_first60_ratio_median"] = {f"{k[0]}|{k[1]}|{k[2]}": round(float(np.median([s_["r60"] for s_ in specs if s_["cell"] == k])), 2) for k in cellrows if isinstance(k, tuple)}
    for fam in FAMS:
        for sname, sub in SETS.items():
            idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]
            mk = lambda r, idx=idx: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx]))
            tr = [mk(r) for r in rows_tr]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=P.SEED); m.fit(L.pad(tr, len(idx)))
            filt = {}
            for cell, rl in cellrows.items():
                qn = [mk(r) for r in rl]; filt[cell] = (qn, V.run_filter(fam, m, qn, len(idx)), [r["tau"] for r in rl])
            for thr in THS:
                key = f"{fam}|{sname}|{thr}"
                for lab, cell in (("stable_null", "null"), ("old_null", "old_null")):
                    qn, rn, _ = filt[cell]; k = sum(bool(V.events_for(fam, r_, q_, thr)[0]) for q_, r_ in zip(qn, rn)); lo, hi = wilson(k, len(qn))
                    out["fa"].setdefault(key, {})[lab] = dict(k=k, n=len(qn), per20=20 * k / len(qn), ci95_per20=[20 * lo, 20 * hi])
                h = {}
                for cell, (qb, rb, taus) in filt.items():
                    if cell in ("null", "old_null"): continue
                    c = 0; dl = []
                    for q_, r_, tau in zip(qb, rb, taus):
                        ev = [e for e in V.events_for(fam, r_, q_, thr)[0] if tau <= q_["avail"][e["i_c"]] <= tau + 60 * E.MIN]
                        if ev: c += 1; dl.append((q_["avail"][ev[0]["i_c"]] - tau) / E.MIN)
                    h["old_break" if cell == "old_break" else f"{cell[0]}|{cell[1]}|{cell[2]}"] = dict(hit=c / len(qb), n=len(qb), median_delay_hits=float(np.median(dl)) if dl else None, n_hits=c)
                out["hit"][key] = h
        log(f"{fam} scored")
    (L.HERE / "results" / "d2_results.json").write_text(json.dumps(out, indent=1, default=str)); log("done")


if __name__ == "__main__":
    main()
