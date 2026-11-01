#!/usr/bin/env python3
"""Machinery pilot under Amendment A7 (AMENDMENT_A7.md): same design as s5_a6.py (RAW fold 3, fixed a-priori sets, K = 3, lambda = 39, no selection, no evaluation data),
with continuous thresholds: HMM/HSMM theta (log-odds) in [0, 30], BOCPD drop size m in [1, 80]; Section 6 thresholds by bisection to 0.2 alarms/session on real validation
sessions; the H1(a) curve sweeps theta in steps of 0.25 and m in steps of 1; the D4 run-2 rule enumerates the same sweep. Machinery outputs, not evidence."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A

FAMS = A.FAMS; SETS = A.SETS; SIZES = A.SIZES; DIRS = A.DIRS; DURS = A.DURS
THETA = [round(x, 2) for x in np.arange(0.0, 30.0001, 0.25)]; MGRID = [float(m) for m in range(1, 81)]
BOUNDS = dict(hmm=(0.0, 30.0, 1e-3), bocpd=(1.0, 80.0, 0.5)); TARGET = 0.2


def bisect_threshold(rate_fn, lo, hi, target, tol):
    """Smallest-effort bisection: returns (value, info) with rate(value) <= target as close to it as the tolerance allows; rate is non-increasing in the value."""
    if rate_fn(hi) > target: return hi, "FLAG: strictest bound still above target"
    if rate_fn(lo) <= target: return lo, "FLAG: loosest bound already at or below target"
    while hi - lo > tol:
        mid = 0.5 * (lo + hi)
        if rate_fn(mid) <= target: hi = mid
        else: lo = mid
    return hi, "ok"


def events(fam, res, q, thr):
    if fam == "bocpd": return E.detect_bocpd_map(res["rstar"], q["real"], q["avail"], thr)[0]
    return E.detect_old_state_logodds(res["P"], q["real"], q["avail"], thr)[0]


def main():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True); out = dict(checks={}, calibration={}, scoring={}); TIMES = A.TIMES
    primary, sens, sens_all = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    with A.stage("load_and_features"):
        d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
        native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
        for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    with A.stage("exclusions"):
        ex = {}
        def chk(name, fn):
            try: fn(); ex[name] = "PASS"
            except AssertionError as e: ex[name] = f"FAIL: {e}"
        chk("primary pool = 19", lambda: (L.assert_pool(primary, "primary"), len(primary) == 19 or (_ for _ in ()).throw(AssertionError(len(primary)))))
        chk("sensitivity pool = 80 (83 - 3 jump_variation__sadj)", lambda: (L.assert_pool(sens, "sensitivity"), (len(sens) == 80 and len(sens_all) == 83) or (_ for _ in ()).throw(AssertionError((len(sens), len(sens_all))))))
        chk("fixed sets inside the primary pool", lambda: (L.assert_pool(P.FIXED3, "primary"), L.assert_pool(P.FIXED6, "primary")))
        chk("no overnight / raw_volume / log_raw_volume / raw_volume__sadj / response asset / LM flag in model inputs", lambda: L.assert_pool(names[1:], "primary"))
        chk("all sessions used are TRAIN partition, RAW era", lambda: (L.assert_train_only("RAW", [d["day"][d["first"][i]] for i in np.r_[seg["train"], seg["val"], seg["test"]]]), L.assert_single_era(d, "RAW")))
        for bad in ("overnight_return_open", "raw_volume", "log_raw_volume", "raw_volume__sadj", "tlt_return_1m", "lee_mykland_jump60", "jump_variation_15__sadj"):
            try: L.assert_pool(primary + [bad], "primary"); ex[f"negative control {bad}"] = "FAIL: not rejected"
            except AssertionError: ex[f"negative control {bad}"] = "PASS"
        out["checks"]["exclusions"] = ex
    to_des = lambda r, sess: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
    rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train", "val", "test")}
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
    mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
    models = {}
    with A.stage("fit_all"):
        for fam in FAMS:
            for sname, sub in SETS.items():
                tr = [mk(r, sub) for r in rows["train"]]; t0 = time.perf_counter()
                m = V.make_model(fam, K=3, lam=39, starts=1, seed=0, Dmax=78); m.fit(L.pad(tr, 1 + len(sub))); models[(fam, sname)] = (m, sub, time.perf_counter() - t0)
    out["fit_seconds"] = {f"{k[0]}|{k[1]}": round(v[2], 3) for k, v in models.items()}
    with A.stage("causal_timing"):
        ct = {}; i5 = int(seg["val"][5])
        ct["deseason scale ignores later sessions"] = "PASS" if np.array_equal(F.ret5_scale(Mx, i5), F.ret5_scale(np.vstack([Mx[:i5], np.full((len(Mx) - i5, 78), 1e9)]), i5)) else "FAIL"
        ct["deseason scale = scale on truncated history"] = "PASS" if np.array_equal(F.ret5_scale(Mx, i5), F.ret5_scale(Mx[:i5], i5), equal_nan=True) else "FAIL"
        pre_bad = []
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"][:6]]; D = 1 + len(sub); full = V.run_filter(fam, m, qs, D)
            cut = [dict(q, n=q["n"] // 2, X=q["X"][:q["n"] // 2], real=q["real"][:q["n"] // 2], avail=q["avail"][:q["n"] // 2], slots=q["slots"][:q["n"] // 2], tgt=q["tgt"][:q["n"] // 2]) for q in qs]
            part = V.run_filter(fam, m, cut, D); key = "pcp" if fam == "bocpd" else "P"
            for a, b, q in zip(full, part, cut):
                if not np.allclose(a[key][:q["n"]], b[key][:q["n"]], rtol=1e-12, atol=1e-14): pre_bad.append(f"{fam}|{sname}")
        ct["filtered output at update t independent of later updates (4 families x 2 sets)"] = "PASS" if not pre_bad else f"FAIL: {sorted(set(pre_bad))}"
        bad_t = n_ev = 0
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"]]; res = V.run_filter(fam, m, qs, 1 + len(sub)); thr = 2.2 if fam != "bocpd" else 3.0
            for q, r, i in zip(qs, res, seg["val"]):
                a = int(d["first"][i])
                for e in events(fam, r, q, thr):
                    n_ev += 1
                    if not (q["avail"][e["i_c"]] == d["t"][a + q["slots"][e["i_c"]]] + 60 * 10 ** 9 and e["i_c"] - e["i_d"] >= (2 if fam != "bocpd" else 3) and q["avail"][e["i_d"]] < q["avail"][e["i_c"]]): bad_t += 1
        ct[f"alarm time = bar stamp + 1 min, T_c after T_d by >= hold ({n_ev} events checked)"] = "PASS" if bad_t == 0 else f"FAIL: {bad_t}"
        pi = P.integrity(d, seg, cols, L.Checkpoint(L.HERE / "cache" / "a6_ckpt")); ct["splice integrity on real data (3 splices, 8 checks each)"] = "PASS" if all(x["checks"]["pass"] for x in pi) else "FAIL"
        out["checks"]["causal_timing"] = ct
    log("exclusions and timing checks done")
    # ---------------- Section 6: bisection on real validation sessions
    with A.stage("section6_bisection"):
        for (fam, sname), (m, sub, _) in models.items():
            D = 1 + len(sub); kind = "bocpd" if fam == "bocpd" else "hmm"; lo, hi, tol = BOUNDS[kind]
            qv = [mk(r, sub) for r in rows["val"]]; rv_ = V.run_filter(fam, m, qv, D); qt = [mk(r, sub) for r in rows["test"]]; rt_ = V.run_filter(fam, m, qt, D)
            calls = [0]
            def rate(thr, qs=qv, rs=rv_, fam=fam): calls[0] += 1; return sum(len(events(fam, r, q, thr)) for q, r in zip(qs, rs)) / len(qs)
            thr, info = bisect_threshold(rate, lo, hi, TARGET, tol); vr = rate(thr); tr_ = sum(len(events(fam, r, q, thr)) for q, r in zip(qt, rt_)) / len(qt)
            out["calibration"][f"{fam}|{sname}"] = dict(threshold=thr, info=info, validation_rate=vr, test_rate_realized=tr_, target=TARGET, rate_evaluations=calls[0],
                                                      equivalent_probability_threshold=(1 / (1 + float(np.exp(-thr))) if kind == "hmm" else None), n_val=len(qv), n_test=len(qt))
    log("section 6 bisection done")
    # ---------------- stable-day splices and H1(a) sweep
    stable_val, _ = S.stable_days(d, seg["val"], dv); stable_test, _ = S.stable_days(d, seg["test"], dv)
    out["stable_days"] = dict(validation=len(stable_val), test=len(stable_test), evaluable=len(stable_test) >= 8)
    rng = np.random.default_rng(4242)
    sp_val = A.build_specs(d, dv, stable_val, rng, A.N_CAL_NULL, A.CAL_CELLS, A.N_CELL); cells_all = [(R, dr, du) for R in SIZES for dr in DIRS for du in DURS]
    sp_test = A.build_specs(d, dv, stable_test, rng, A.N_NULL, cells_all, A.N_CELL)
    with A.stage("build_splices"):
        with mp.get_context("spawn").Pool(4, initializer=D2._init, initargs=(cols,)) as pool: rows_all = pool.map(D2._work, sp_val + sp_test, chunksize=8)
    rv_rows, rt_rows = rows_all[:len(sp_val)], rows_all[len(sp_val):]; log(f"{len(rows_all)} splices built")
    group = lambda specs, rr: {c: [r for s_, r in zip(specs, rr) if s_["cell"] == c] for c in {s_["cell"] for s_ in specs}}
    gv, gt = group(sp_val, rv_rows), group(sp_test, rt_rows); des = lambda rl: [to_des(r, r["iA"]) for r in rl]
    hit = lambda fam, res, qs, taus, thr: [any(t <= q["avail"][e["i_c"]] <= t + 3600 * 10 ** 9 for e in events(fam, r, q, thr)) for r, q, t in zip(res, qs, taus)]
    with A.stage("h1a_sweep"):
        for (fam, sname), (m, sub, _) in models.items():
            D = 1 + len(sub); grid = MGRID if fam == "bocpd" else THETA
            def filt(rl): qs = [mk(r, sub) for r in des(rl)]; return qs, V.run_filter(fam, m, qs, D), [r["tau"] for r in rl]
            qn, rn, _ = filt(gv["null"]); cal_null = {g_: float(np.mean([bool(events(fam, r, q, g_)) for q, r in zip(qn, rn)])) for g_ in grid}
            feas = [g_ for g_ in grid if cal_null[g_] <= 0.10]; cb = {}
            if feas:
                fc = {dr: filt([r for c, v in gv.items() if c != "null" and c[1] == dr for r in v]) for dr in DIRS}
                for g_ in feas: cb[g_] = float(np.mean([np.mean(hit(fam, fc[dr][1], fc[dr][0], fc[dr][2], g_)) for dr in DIRS]))
            run2 = max(feas, key=lambda g_: (cb[g_], -grid.index(g_))) if feas else None
            qn, rn, _ = filt(gt["null"]); xs = {g_: sum(len(events(fam, r, q, g_)) for q, r in zip(qn, rn)) / len(qn) for g_ in grid}
            fl = {c: filt(v) for c, v in gt.items() if c != "null"}; hitmat = {g_: {c: float(np.sum(hit(fam, r_, q_, t_, g_))) for c, (q_, r_, t_) in fl.items()} for g_ in grid}
            byratio = {}
            for R in SIZES + ["all"]:
                pts = []; n_b = sum(len(v[0]) for c, v in fl.items() if R == "all" or c[0] == R)
                for g_ in grid: pts.append((xs[g_], sum(h for c, h in hitmat[g_].items() if R == "all" or c[0] == R) / n_b))
                byratio[str(R)] = dict(pauc_0_0p5=A.pauc(pts), hit_at_alarm_rate_0p1=A.y_at(pts, 0.1), hit_at_alarm_rate_0p2=A.y_at(pts, 0.2), n_breaks=n_b)
            ks = list(xs)
            out["scoring"][f"{fam}|{sname}"] = dict(by_ratio=byratio, run2_threshold=run2, run2_feasible=run2 is not None, null_alarm_rate_strictest=xs[ks[-1]], null_alarm_rate_loosest=xs[ks[0]],
                                                    smallest_null_alarm_rate_in_sweep=min(xs.values()), x_values_in_0_0p5=sum(1 for v in xs.values() if v <= 0.5))
            log(f"swept {fam}|{sname}")
    out["scoring_difference_f3_minus_base_pauc_all"] = {fam: out["scoring"][f"{fam}|f3"]["by_ratio"]["all"]["pauc_0_0p5"] - out["scoring"][f"{fam}|base"]["by_ratio"]["all"]["pauc_0_0p5"] for fam in FAMS}
    out["stage_seconds"] = TIMES; out["total_minutes"] = round((time.time() - T0) / 60, 2)
    (L.HERE / "results" / "a7_pilot_results.json").write_text(json.dumps(out, indent=1, default=float)); log("done")


if __name__ == "__main__":
    main()
