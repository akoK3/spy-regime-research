#!/usr/bin/env python3
"""Diagnostic D3 tests 2-4 (RAW fold 3, VALIDATION sessions only; same frozen detectors and fixed feature sets; no selection; no evaluation data).
mode 'raw'  = inputs as in D2 (identical splices: same seeds as s5_d2.py).
mode 'des'  = all inputs deseasonalised: the 5-min return and momentum15_endpoint are divided by the causal slot scale (median |x| of the same grid slot over the
              previous 20 sessions, >= 10 finite; NaN scale = skipped update); the other inputs are already relative to a causal slot baseline (__sadj, relative_volume20)
              or bounded (close_location_proxy). Spliced sessions use session A's history.
Extra, labelled as not the protocol rule: for HMM/HSMM the 'mass' rule (s5_events.detect_states_mass) next to the protocol 'state' rule."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E, s5_d2 as D2, s5_d2_stable as S

THS = [0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 0.9999]; THS_B = [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]
FAMS = D2.FAMS; SETS = D2.SETS; SIZES = D2.SIZES; DIRS = D2.DIRS; DURS = D2.DURS
BINS = ["09:30-10:00", "10:00-11:00", "11:00-12:00", "12:00-13:00", "13:00-14:00", "14:00-15:00", "15:00-16:00"]


def hour_bin(slot):
    m = 9 * 60 + 30 + int(slot) + 1
    return 0 if m < 600 else min(6, m // 60 - 9)


def events(fam, rule, res, q, thr):
    if fam != "bocpd" and rule == "mass": return E.detect_states_mass(res["P"], q["real"], q["avail"], thr)
    return V.events_for(fam, res, q, thr)


def q4(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]
    return [round(float(v), 4) for v in np.quantile(x, [.5, .9, .99, .999])] if len(x) else []


def cramers(counts):
    n = counts.sum(); r = counts.sum(1, keepdims=True); c = counts.sum(0, keepdims=True); keep = (r[:, 0] > 0); counts = counts[keep]; r = r[keep]
    c = counts.sum(0, keepdims=True); cols = c[0] > 0; counts, c = counts[:, cols], c[:, cols]
    ex = r * c / n; chi = ((counts - ex) ** 2 / ex).sum(); k = min(counts.shape) - 1
    p = counts / n; pr = p.sum(1, keepdims=True); pc = p.sum(0, keepdims=True)
    mi = np.nansum(p * np.log(p / (pr * pc))); hs = -np.nansum(pr * np.log(pr))
    return float(np.sqrt(chi / (n * k))) if k > 0 else 0.0, float(mi / hs) if hs > 0 else 0.0


def main():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
    stable = json.loads((L.HERE / "results" / "d2_stable_days.json").read_text())["stable"]; rng = np.random.default_rng(P.SEED + 500)
    rv, _, _ = V.session_stats(d, stable); tv = V.tercile(rv); stable = np.array(stable); specs = []
    for _ in range(D2.N_NULL):                                   # identical sampling to s5_d2.py
        for _t in range(200):
            c = np.where(tv == int(rng.integers(3)))[0]
            if len(c) < 2: continue
            A, B = rng.choice(c, 2, replace=False); A, B = int(stable[A]), int(stable[B]); g = int(rng.choice(V.TAU_SLOTS))
            if D2.finite_ok(d, A, B, g, None): break
        specs.append(dict(kind="plain", cell="null", iA=A, iB=B, g=g))
    for R in SIZES:
        for dr in DIRS:
            for du in DURS:
                for _ in range(D2.N_CELL):
                    for _t in range(500):
                        A, B = (int(x) for x in rng.choice(stable, 2, replace=False)); g = int(rng.choice([t for t in V.TAU_SLOTS if t <= D2.G_MAX])); e = None if du is None else g + du
                        if D2.finite_ok(d, A, B, g, e): break
                    fa, fb = int(d["first"][A]), int(d["first"][B]); last = 389 if du is None else g + du
                    pre = np.nanmean(dv[fa + 1:fa + g + 1]); post = np.nanmean(dv[fb + g + 1:fb + last + 1]); tgt = R if dr == "up" else 1.0 / R
                    specs.append(dict(kind="regime", cell=(R, dr, du), iA=A, iB=B, g=g, f=float(np.sqrt(tgt * pre / post)), dur=du))
    allsp = specs
    with mp.get_context("spawn").Pool(4, initializer=D2._init, initargs=(cols,)) as pool: allrows = pool.map(D2._work, allsp, chunksize=8)
    log(f"{len(allsp)} rows built")
    # native grid matrices for the causal slot scales
    S_ = len(d["first"]); native = [L.session_grid(d, i, cols) for i in range(S_)]; jm = 1 + cols.index("momentum15_endpoint")
    Mret = np.full((S_, 78), np.nan); Mmom = np.full((S_, 78), np.nan)
    for i, r in enumerate(native): Mret[i, :len(r["X"])] = r["X"][:, 0]; Mmom[i, :len(r["X"])] = r["X"][:, jm]

    def to_mode(r, sess, mode):
        if mode == "raw": return r
        X = r["X"].copy(); n = len(X)
        X[:, 0] = X[:, 0] / F.ret5_scale(Mret, sess)[:n]; X[:, jm] = X[:, jm] / F.ret5_scale(Mmom, sess)[:n]
        return dict(r, X=X)
    rows_tr_native = [native[i] for i in seg["train"]]
    cellrows = {}
    for sp, r in zip(allsp, allrows): cellrows.setdefault(sp["cell"], []).append(r)
    out = {"raw": {}, "des": {}}
    for mode in ("raw", "des"):
        o = out[mode] = dict(fa={}, hit={}, bocpd_low={}, pcp={}, occupancy={})
        tr_rows = [to_mode(r, r["sess"], mode) for r in rows_tr_native]
        prep = L.Prep().fit(np.vstack([r["X"] for r in tr_rows]), names)
        for fam in FAMS:
            for sname, sub in SETS.items():
                idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]
                mk = lambda r, idx=idx: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx]))
                tr = [mk(r) for r in tr_rows]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=P.SEED); m.fit(L.pad(tr, len(idx)))
                if fam != "bocpd":      # ---- test 2: state occupancy by time of day (train sessions, filtered argmax)
                    rt = V.run_filter(fam, m, tr, len(idx)); K = rt[0]["P"].shape[1]; cnt = np.zeros((K, 7))
                    for q_, r_ in zip(tr, rt):
                        am = r_["P"].argmax(1)
                        for sl, st_, rl in zip(q_["slots"], am, q_["real"]):
                            if rl: cnt[st_, hour_bin(sl)] += 1
                    v, nmi = cramers(cnt)
                    o["occupancy"][f"{fam}|{sname}"] = dict(cramers_v=v, nmi=nmi, state_var_ret=[float(x) for x in m.var[:, 0]], share_by_bin=[[round(float(x), 3) for x in row / np.maximum(cnt.sum(0), 1)] for row in cnt], bin_counts=[int(x) for x in cnt.sum(0)])
                filt = {}
                for cell, rl in cellrows.items():
                    rr = []
                    for r in rl: rr.append(to_mode(r, r["iA"], mode))
                    qn = [mk(r) for r in rr]; filt[cell] = (qn, V.run_filter(fam, m, qn, len(idx)), [r["tau"] for r in rr])
                rules = ("state", "mass") if fam != "bocpd" else ("state",)
                grid = THS + (THS_B if fam == "bocpd" else [])
                for rule in rules:
                    for thr in grid:
                        key = f"{fam}|{sname}|{rule}|{thr}"
                        qn, rn, _ = filt["null"]; k = sum(bool(events(fam, rule, r_, q_, thr)[0]) for q_, r_ in zip(qn, rn)); lo, hi = D2.wilson(k, len(qn))
                        o["fa"][key] = dict(k=k, n=len(qn), per20=20 * k / len(qn), ci95_per20=[20 * lo, 20 * hi]); h = {}
                        for cell, (qb, rb, taus) in filt.items():
                            if cell == "null": continue
                            c = 0
                            for q_, r_, tau in zip(qb, rb, taus):
                                c += any(tau <= q_["avail"][e["i_c"]] <= tau + 60 * E.MIN for e in events(fam, rule, r_, q_, thr)[0])
                            h[f"{cell[0]}|{cell[1]}|{cell[2]}"] = dict(hit=c / len(qb), n=len(qb), n_hits=c)
                        o["hit"][key] = h
                if fam == "bocpd":     # ---- test 4: changepoint-probability quantiles, null vs break
                    qn, rn, _ = filt["null"]; pooled_n = np.concatenate([r_["pcp"][2:] for r_ in rn]); max_n = [r_["pcp"][2:].max() for r_ in rn if len(r_["pcp"]) > 2]
                    brk = {"all": [], "R>=3": []}; mx = {"all": [], "R>=3": []}
                    for cell, (qb, rb, taus) in filt.items():
                        if cell == "null" or cell[2] is not None: continue
                        for q_, r_, tau in zip(qb, rb, taus):
                            w = (q_["avail"] >= tau) & (q_["avail"] <= tau + 60 * E.MIN) & (np.arange(len(q_["avail"])) >= 2)
                            if w.any():
                                brk["all"].append(r_["pcp"][w]); mx["all"].append(r_["pcp"][w].max())
                                if cell[0] >= 3: brk["R>=3"].append(r_["pcp"][w]); mx["R>=3"].append(r_["pcp"][w].max())
                    o["pcp"][sname] = dict(null_pooled_q50_90_99_999=q4(pooled_n), null_session_max_q50_90_99_999=q4(max_n),
                                           break_perm_window_pooled_all=q4(np.concatenate(brk["all"])), break_perm_window_session_max_all=q4(mx["all"]),
                                           break_perm_window_pooled_R_ge_3=q4(np.concatenate(brk["R>=3"])), break_perm_window_session_max_R_ge_3=q4(mx["R>=3"]))
        log(f"mode {mode} done")
    (L.HERE / "results" / "d3_results.json").write_text(json.dumps(out, indent=1, default=str)); log("done")


if __name__ == "__main__":
    main()
