#!/usr/bin/env python3
"""Re-computes ONLY the H1(a) sweep readout of the A7 pilot (same data, models, splices and seeds as s5_a7.py) with the vectorised sweeps of s5_sweep.py, stores the curves,
checks hit(0.2) >= hit(0.1), and compares every readout with the stored loop-based A7 values. No selection, no evaluation data."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_events as E, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_sweep as W

MIN = 60 * 10 ** 9


def main():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
    rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train",)}
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
    mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
    models = {}
    for fam in B.FAMS:
        for sname, sub in B.SETS.items():
            tr = [mk(r, sub) for r in rows["train"]]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=0, Dmax=78); m.fit(L.pad(tr, 1 + len(sub))); models[(fam, sname)] = (m, sub)
    stable_val, _ = S.stable_days(d, seg["val"], dv); stable_test, _ = S.stable_days(d, seg["test"], dv); rng = np.random.default_rng(4242)       # same order of draws as s5_a7.py
    sp_val = A.build_specs(d, dv, stable_val, rng, A.N_CAL_NULL, A.CAL_CELLS, A.N_CELL); cells_all = [(R, dr, du) for R in B.SIZES for dr in B.DIRS for du in B.DURS]
    sp_test = A.build_specs(d, dv, stable_test, rng, A.N_NULL, cells_all, A.N_CELL)
    with mp.get_context("spawn").Pool(4, initializer=D2._init, initargs=(cols,)) as pool: rows_all = pool.map(D2._work, sp_val + sp_test, chunksize=8)
    rv_rows, rt_rows = rows_all[:len(sp_val)], rows_all[len(sp_val):]; log(f"{len(rows_all)} splices built")
    group = lambda specs, rr: {c: [r for s_, r in zip(specs, rr) if s_["cell"] == c] for c in {s_["cell"] for s_ in specs}}
    gv, gt = group(sp_val, rv_rows), group(sp_test, rt_rows); des = lambda rl: [to_des(r, r["iA"]) for r in rl]
    stored = json.loads((L.HERE / "results" / "a7_pilot_results.json").read_text())["scoring"]; out = {}; t_sweep = {}; maxdiff = 0.0; viol = []
    for (fam, sname), (m, sub) in models.items():
        t0 = time.perf_counter(); D = 1 + len(sub); grid = B.MGRID if fam == "bocpd" else B.THETA
        def run(rl):
            qs = [mk(r, sub) for r in des(rl)]; rs = V.run_filter(fam, m, qs, D)
            if fam == "bocpd": R_, real, av = W.stack(rs, qs, "rstar")
            else: R_, real, av = W.stack(rs, qs, "P")
            return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
        sw = (lambda a, b, c, t: W.sweep_map(a, b, c, grid, t)) if fam == "bocpd" else (lambda a, b, c, t: W.sweep_old_state(a, b, c, grid, t))
        Rn, rn_, an, tn = run(gv["null"]); cnt, _ = sw(Rn, rn_, an, None); cal_null = (cnt > 0).mean(0)
        feas = [g for g in range(len(grid)) if cal_null[g] <= 0.10]; cb = np.zeros(len(grid))
        if feas:
            hits_d = []
            for dr in B.DIRS:
                rl = [r for c, v in gv.items() if c != "null" and c[1] == dr for r in v]; Rb, rb_, ab, tb = run(rl); _, h = sw(Rb, rb_, ab, tb); hits_d.append(h.mean(0))
            cb = np.mean(hits_d, axis=0)
        run2 = grid[max(feas, key=lambda g: (cb[g], -g))] if feas else None
        Rn, rn_, an, tn = run(gt["null"]); cnt, _ = sw(Rn, rn_, an, None); xs = cnt.mean(0)
        hits_cell = {}
        for c, v in gt.items():
            if c == "null": continue
            Rb, rb_, ab, tb = run(v); _, h = sw(Rb, rb_, ab, tb); hits_cell[c] = (h.sum(0), len(v))
        byratio = {}
        for Rr in B.SIZES + ["all"]:
            num = sum(h for c, (h, n) in hits_cell.items() if Rr == "all" or c[0] == Rr); den = sum(n for c, (h, n) in hits_cell.items() if Rr == "all" or c[0] == Rr)
            pts = list(zip(xs.tolist(), (num / den).tolist()))
            byratio[str(Rr)] = dict(pauc_0_0p5=A.pauc(pts), hit_at_alarm_rate_0p1=A.y_at(pts, 0.1), hit_at_alarm_rate_0p2=A.y_at(pts, 0.2), curve_x=xs.tolist(), curve_y=(num / den).tolist())
            if byratio[str(Rr)]["hit_at_alarm_rate_0p2"] < byratio[str(Rr)]["hit_at_alarm_rate_0p1"]: viol.append((fam, sname, Rr))
            o = stored[f"{fam}|{sname}"]["by_ratio"][str(Rr)]
            maxdiff = max(maxdiff, abs(o["pauc_0_0p5"] - byratio[str(Rr)]["pauc_0_0p5"]), abs(o["hit_at_alarm_rate_0p1"] - byratio[str(Rr)]["hit_at_alarm_rate_0p1"]), abs(o["hit_at_alarm_rate_0p2"] - byratio[str(Rr)]["hit_at_alarm_rate_0p2"]))
        out[f"{fam}|{sname}"] = dict(by_ratio=byratio, run2_threshold=(None if run2 is None else float(run2)), run2_matches_stored=bool(run2 == stored[f"{fam}|{sname}"]["run2_threshold"]))
        t_sweep[f"{fam}|{sname}"] = round(time.perf_counter() - t0, 2); log(f"{fam}|{sname} {t_sweep[f'{fam}|{sname}']}s")
    res = dict(scoring=out, sweep_seconds_per_detector=t_sweep, sweep_seconds_total=round(sum(t_sweep.values()), 1), max_abs_difference_vs_stored_loop_values=maxdiff, hit0p2_below_hit0p1=viol, minutes=round((time.time() - T0) / 60, 2))
    (L.HERE / "results" / "a7_readout_vectorised.json").write_text(json.dumps(res, indent=1, default=float)); log(f"maxdiff {maxdiff}, violations {viol}")


if __name__ == "__main__":
    main()
