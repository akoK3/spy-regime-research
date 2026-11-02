#!/usr/bin/env python3
"""A8 item 1 gate: zero-size (R = 1) breaks must score within the 95% bootstrap interval of null splices, for every detector. Validation sessions of one fold only; A7 machinery
(K=3, lambda=39, fixed base/f3 sets, deseasonalised inputs); no test segment, no selection, no evaluation data. Usage: s5_a8_gate.py ERA FOLD SEED"""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_sweep as W

N1, N2, NP = 200, 200, 200; NBOOT = 2000


def null_specs(d, dv, stable, rng, n):
    """Null splices as in A6 build_specs, with tau restricted to the slots break splices use (<= G_MAX), so N2 and the placebo are comparable."""
    stable = np.array(stable); rv, _, _ = V.session_stats(d, stable); tv = V.tercile(rv); taus = [t for t in V.TAU_SLOTS if t <= D2.G_MAX]; out = []
    for _ in range(n):
        for _t in range(200):
            c = np.where(tv == int(rng.integers(3)))[0]
            if len(c) < 2: continue
            a, b = rng.choice(c, 2, replace=False); a, b = int(stable[a]), int(stable[b]); g = int(rng.choice(taus))
            if D2.finite_ok(d, a, b, g, None): break
        else: raise RuntimeError("null pair")
        out.append(dict(kind="plain", cell="null", iA=a, iB=b, g=g))
    return out


def main(era, fold, seed):
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era(era, cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, era, fold); dv = S.des_variance(d)
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
    rows_tr = [to_des(native[i], i) for i in seg["train"]]; prep = L.Prep().fit(np.vstack([r["X"] for r in rows_tr]), names)
    mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
    models = {}
    for fam in B.FAMS:
        for sname, sub in B.SETS.items():
            m = V.make_model(fam, K=3, lam=39, starts=1, seed=0, Dmax=78); m.fit(L.pad([mk(r, sub) for r in rows_tr], 1 + len(sub))); models[(fam, sname)] = (m, sub)
    log("fits done")
    stable, _ = S.stable_days(d, seg["val"], dv); rng = np.random.default_rng(seed)
    n1 = null_specs(d, dv, stable, rng, N1); n2 = null_specs(d, dv, stable, rng, N2)
    pl = A.build_specs(d, dv, stable, rng, 0, [(1.0, "up", du) for du in B.DURS], NP // len(B.DURS))
    pl2 = A.build_specs(d, dv, stable, np.random.default_rng(seed + 2), 0, [(1.0, "up", du) for du in B.DURS], NP // len(B.DURS))   # A8.1: independent placebo set P2
    D2._W.update(d=d, cols=cols, bases=F.load_bases(d, era, cols), dv=dv)
    rows1, rows2, rowsp, rowsp2 = ([D2._work(s) for s in x] for x in (n1, n2, pl, pl2)); log(f"{len(n1)+len(n2)+len(pl)} splices built; stable validation days {len(stable)}")
    des = lambda rl: [to_des(r, r["iA"]) for r in rl]; out = {}; brng = np.random.default_rng(seed + 1)
    for (fam, sname), (m, sub) in models.items():
        D = 1 + len(sub); grid = B.MGRID if fam == "bocpd" else B.THETA
        def run_(rl):
            qs = [mk(r, sub) for r in des(rl)]; rs = V.run_filter(fam, m, qs, D); R_, real, av = W.stack(rs, qs, "rstar" if fam == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
        sw = (lambda a, b, c, t: W.sweep_map(a, b, c, grid, t)) if fam == "bocpd" else (lambda a, b, c, t: W.sweep_old_state(a, b, c, grid, t))
        R_, re_, av_, _ = run_(rows1); cnt, _ = sw(R_, re_, av_, None); xs = cnt.mean(0)
        R_, re_, av_, t_ = run_(rows2); _, h2 = sw(R_, re_, av_, t_)
        R_, re_, av_, t_ = run_(rowsp); _, hp = sw(R_, re_, av_, t_)
        R_, re_, av_, t_ = run_(rowsp2); _, hp2 = sw(R_, re_, av_, t_)
        pa = lambda y: A.pauc(list(zip(xs.tolist(), np.asarray(y).tolist())))
        p_null, p_pl, p_pl2 = pa(h2.mean(0)), pa(hp.mean(0)), pa(hp2.mean(0))
        boot = np.array([pa(hp2[brng.integers(0, len(hp2), len(hp2))].mean(0)) for _ in range(NBOOT)]); lo, hi = np.quantile(boot, [0.025, 0.975])   # A8.1: reference = P2
        bootn = np.array([pa(h2[brng.integers(0, len(h2), len(h2))].mean(0)) for _ in range(NBOOT)]); lon, hin = np.quantile(bootn, [0.025, 0.975])  # old rule, information only
        out[f"{fam}|{sname}"] = dict(pauc_null=p_null, pauc_placebo=p_pl, pauc_placebo2=p_pl2, placebo2_ci=[float(lo), float(hi)], inside=bool(lo <= p_pl <= hi), null_ci=[float(lon), float(hin)], inside_vs_null_info_only=bool(lon <= p_pl <= hin), hit0p2_null=A.y_at(list(zip(xs.tolist(), h2.mean(0).tolist())), 0.2),
                                     hit0p2_placebo=A.y_at(list(zip(xs.tolist(), hp.mean(0).tolist())), 0.2), smallest_x=float(xs.min()))
        log(f"{fam}|{sname} P2 {p_pl2:.3f} [{lo:.3f},{hi:.3f}] P1 {p_pl:.3f} null {p_null:.3f} inside={out[f'{fam}|{sname}']['inside']}")
    diff = {f"{fam}": dict(placebo2=out[f"{fam}|f3"]["pauc_placebo2"] - out[f"{fam}|base"]["pauc_placebo2"], null=out[f"{fam}|f3"]["pauc_null"] - out[f"{fam}|base"]["pauc_null"], placebo=out[f"{fam}|f3"]["pauc_placebo"] - out[f"{fam}|base"]["pauc_placebo"]) for fam in B.FAMS}
    def shifts(rl):
        res = []
        for r in rl:
            X = np.abs(r["X"]); pre = r["slots"] <= r["g"]; post = ~pre
            with np.errstate(all="ignore"): res.append(np.log(np.nanmean(X[post], 0) / np.nanmean(X[pre], 0)))
        a = np.array(res); a[~np.isfinite(a)] = np.nan; return np.nanmedian(a, 0)
    sn, sp_ = shifts(rows2), shifts(rowsp)
    res = dict(rule="A8.1: P1 inside 95% bootstrap interval of P2", era=era, fold=fold, seed=seed, stable_validation_days=len(stable), n=dict(N1=len(n1), N2=len(n2), placebo=len(pl), placebo2=len(pl2)), detectors=out, all_inside=all(v["inside"] for v in out.values()),
               pauc_f3_minus_base=diff, feature_shift_median_log_ratio_after_over_before=dict(names=names, null=sn.tolist(), placebo=sp_.tolist()), minutes=round((time.time() - T0) / 60, 1))
    (L.HERE / "results" / f"a8_1_gate_{era}{fold}_seed{seed}.json").write_text(json.dumps(res, indent=1, default=float)); log(f"GATE all_inside={res['all_inside']}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]))
