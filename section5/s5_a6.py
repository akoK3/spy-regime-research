#!/usr/bin/env python3
"""Machinery pilot under Amendment A6 (AMENDMENT_A6.md): RAW fold 3, fixed a-priori feature sets (base = deseasonalized 5-min return; f3 = + rv5_strict__sadj,
relative_volume20, intrabar_range_log__sadj), K = 3, 1 start, seed 0, BOCPD lambda 39. No selection, no evaluation-period data, no protocol change from performance.
Stages: exclusions, causal timing, Section 6 threshold calibration (real validation sessions -> 0.2 alarms/session, realized on test sessions), BOCPD secondary
threshold (D4 run-2 rule on validation stable-day splices), H1(a) synthetic scoring (hit vs alarm-rate curve, partial area 0-0.5, by variance ratio) on the fold's
test stable-day splices. Numbers are machinery outputs, not evidence."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P, s5_events as E, s5_models as M, s5_d2 as D2, s5_d2_stable as S

FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = dict(base=[], f3=P.FIXED3)
HMM_GRID = [0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.995, 0.999, 0.9999]; DROP_GRID = [1, 2, 3, 5, 8, 12, 20, 30]
SIZES = [1.5, 2, 3, 5, 10]; DIRS = ["up", "down"]; DURS = [None, 30, 60, 120]; N_CELL = 24; N_NULL = 400; TARGET_RATE = 0.2
CAL_CELLS = [(R, dr, None) for R in (3, 5, 10) for dr in DIRS]; N_CAL_NULL = 200
TIMES = {}


def pauc(points, xmax=0.5):
    """Partial area under y(x) = highest y reached at alarm rate <= x, x in [0, xmax], divided by xmax."""
    pts = sorted(points); cur = max([y for x, y in pts if x <= 0] + [0.0]); prev = 0.0; area = 0.0
    for x, y in pts:
        if x <= 0: continue
        if x > xmax: break
        area += cur * (x - prev); prev = x; cur = max(cur, y)
    return (area + cur * (xmax - prev)) / xmax


def y_at(points, x0):
    return max([y for x, y in points if x <= x0] + [0.0])


def choose_rate_threshold(rates, grid, target=TARGET_RATE):
    """A6 item 3: among grid values with validation alarm rate <= target, the one with the highest rate (ties to the stricter); strictest value + flag if none."""
    ok = [g for g in grid if rates[g] <= target]
    if not ok: return grid[-1], True
    return max(ok, key=lambda g: (rates[g], grid.index(g))), False


def events(fam, res, q, thr):
    if fam == "bocpd": return E.detect_bocpd_map(res["rstar"], q["real"], q["avail"], thr)[0]
    return E.detect_old_state(res["P"], q["real"], q["avail"], thr)[0]


def build_specs(d, dv, stable, rng, n_null, cells, n_cell):
    stable = np.array(stable); rv, _, _ = V.session_stats(d, stable); tv = V.tercile(rv); specs = []
    for _ in range(n_null):
        for _t in range(200):
            c = np.where(tv == int(rng.integers(3)))[0]
            if len(c) < 2: continue
            A, B = rng.choice(c, 2, replace=False); A, B = int(stable[A]), int(stable[B]); g = int(rng.choice(V.TAU_SLOTS))
            if D2.finite_ok(d, A, B, g, None): break
        else: raise RuntimeError("null pair")
        specs.append(dict(kind="plain", cell="null", iA=A, iB=B, g=g))
    for (R, dr, du) in cells:
        for _ in range(n_cell):
            for _t in range(500):
                A, B = (int(x) for x in rng.choice(stable, 2, replace=False)); g = int(rng.choice([t for t in V.TAU_SLOTS if t <= D2.G_MAX])); e = None if du is None else g + du
                if D2.finite_ok(d, A, B, g, e): break
            else: raise RuntimeError("break pair")
            fa, fb = int(d["first"][A]), int(d["first"][B]); last = 389 if du is None else g + du
            pre = np.nanmean(dv[fa + 1:fa + g + 1]); post = np.nanmean(dv[fb + g + 1:fb + last + 1]); tgt = R if dr == "up" else 1.0 / R
            specs.append(dict(kind="regime", cell=(R, dr, du), iA=A, iB=B, g=g, f=float(np.sqrt(tgt * pre / post)), dur=du))
    return specs


def stage(name):
    class C:
        def __enter__(s): s.t = time.perf_counter()
        def __exit__(s, *a): TIMES[name] = round(time.perf_counter() - s.t, 2)
    return C()


def main():
    import multiprocessing as mp
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True); out = dict(checks={}, calibration={}, scoring={})
    primary, sens, sens_all = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    with stage("load_and_features"):
        d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
        native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
        for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    # ---------------- exclusions
    with stage("exclusions"):
        ex = {}
        def chk(name, fn):
            try: fn(); ex[name] = "PASS"
            except AssertionError as e: ex[name] = f"FAIL: {e}"
        chk("primary pool = 19, assert_pool primary", lambda: (L.assert_pool(primary, "primary"), (len(primary) == 19) or (_ for _ in ()).throw(AssertionError(len(primary)))))
        chk("sensitivity pool = 80 (83 - 3 jump_variation__sadj)", lambda: (L.assert_pool(sens, "sensitivity"), (len(sens) == 80 and len(sens_all) == 83 and set(sens_all) - set(sens) == {"jump_variation_15__sadj", "jump_variation_30__sadj", "jump_variation_60__sadj"}) or (_ for _ in ()).throw(AssertionError((len(sens), len(sens_all))))))
        chk("fixed sets inside the primary pool", lambda: (L.assert_pool(P.FIXED3, "primary"), L.assert_pool(P.FIXED6, "primary")))
        chk("no overnight / raw_volume / log_raw_volume / raw_volume__sadj / response asset / LM flag in model inputs", lambda: L.assert_pool(names[1:], "primary"))
        chk("all sessions used are TRAIN partition, RAW era", lambda: (L.assert_train_only("RAW", [d["day"][d["first"][i]] for i in np.r_[seg["train"], seg["val"], seg["test"]]]), L.assert_single_era(d, "RAW")))
        chk("embargo: 5 sessions between segments", lambda: (seg["train"].max() + 5 < seg["val"].min() or (_ for _ in ()).throw(AssertionError("train/val")), seg["val"].max() + 5 < seg["test"].min() or (_ for _ in ()).throw(AssertionError("val/test"))))
        for bad in ("overnight_return_open", "raw_volume", "log_raw_volume", "raw_volume__sadj", "tlt_return_1m", "lee_mykland_jump60", "jump_variation_15__sadj"):
            try: L.assert_pool(primary + [bad], "primary"); ex[f"negative control {bad}"] = "FAIL: not rejected"
            except AssertionError: ex[f"negative control {bad}"] = "PASS"
        out["checks"]["exclusions"] = ex
    # ---------------- inputs
    def to_des(r, sess): return dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, sess)))
    rows = {k: [to_des(native[i], i) for i in seg[k]] for k in ("train", "val", "test")}
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
    mk = lambda r, sub: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]]))
    models = {}
    with stage("fit_all"):
        for fam in FAMS:
            for sname, sub in SETS.items():
                tr = [mk(r, sub) for r in rows["train"]]; t0 = time.perf_counter()
                m = V.make_model(fam, K=3, lam=39, starts=1, seed=0, Dmax=78); m.fit(L.pad(tr, 1 + len(sub))); models[(fam, sname)] = (m, sub, time.perf_counter() - t0)
    out["fit_seconds"] = {f"{k[0]}|{k[1]}": round(v[2], 3) for k, v in models.items()}
    # ---------------- causal timing
    with stage("causal_timing"):
        ct = {}
        sc_full = F.ret5_scale(Mx, int(seg["val"][5])); ct["deseason scale ignores later sessions"] = "PASS" if np.array_equal(sc_full, F.ret5_scale(np.vstack([Mx[:int(seg['val'][5])], np.full((len(Mx) - int(seg['val'][5]), 78), 1e9)]), int(seg["val"][5]))) else "FAIL"
        sc_trunc = F.ret5_scale(Mx[:int(seg["val"][5])], int(seg["val"][5])); ct["deseason scale = scale on truncated history"] = "PASS" if np.array_equal(sc_full, sc_trunc, equal_nan=True) else "FAIL"
        pre_bad = []
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"][:6]]; D = 1 + len(sub); full = V.run_filter(fam, m, qs, D)
            cut = [dict(q, n=q["n"] // 2, X=q["X"][:q["n"] // 2], real=q["real"][:q["n"] // 2], avail=q["avail"][:q["n"] // 2], slots=q["slots"][:q["n"] // 2], tgt=q["tgt"][:q["n"] // 2]) for q in qs]
            part = V.run_filter(fam, m, cut, D); key = "pcp" if fam == "bocpd" else "P"
            for a, b, q in zip(full, part, cut):
                if not np.allclose(a[key][:q["n"]], b[key][:q["n"]], rtol=1e-12, atol=1e-14): pre_bad.append(f"{fam}|{sname}")
        ct["filtered output at update t independent of later updates (prefix invariance, 4 families x 2 sets)"] = "PASS" if not pre_bad else f"FAIL: {sorted(set(pre_bad))}"
        bad_t = 0; n_ev = 0
        for (fam, sname), (m, sub, _) in models.items():
            qs = [mk(r, sub) for r in rows["val"]]; res = V.run_filter(fam, m, qs, 1 + len(sub)); thr = 0.9 if fam != "bocpd" else 3
            for q, r, i in zip(qs, res, seg["val"]):
                a = int(d["first"][i])
                for e in events(fam, r, q, thr):
                    n_ev += 1
                    if not (q["avail"][e["i_c"]] == d["t"][a + q["slots"][e["i_c"]]] + 60 * 10 ** 9 and e["i_c"] - e["i_d"] >= (2 if fam != "bocpd" else 3) and q["avail"][e["i_d"]] < q["avail"][e["i_c"]]): bad_t += 1
        ct[f"alarm time = bar stamp + 1 min, T_c after T_d by >= hold ({n_ev} events checked)"] = "PASS" if bad_t == 0 else f"FAIL: {bad_t}"
        pi = P.integrity(d, seg, cols, L.Checkpoint(L.HERE / "cache" / "a6_ckpt")); ct["splice integrity on real data (3 splices, 8 checks each)"] = "PASS" if all(x["checks"]["pass"] for x in pi) else "FAIL"
        out["checks"]["causal_timing"] = ct
    log("exclusions and timing checks done")
    # ---------------- Section 6 threshold calibration on real validation sessions
    with stage("section6_calibration"):
        for (fam, sname), (m, sub, _) in models.items():
            D = 1 + len(sub); grid = DROP_GRID if fam == "bocpd" else HMM_GRID
            qv = [mk(r, sub) for r in rows["val"]]; rv_ = V.run_filter(fam, m, qv, D); qt = [mk(r, sub) for r in rows["test"]]; rt_ = V.run_filter(fam, m, qt, D)
            rate = lambda qs, rs, g_: sum(len(events(fam, r, q, g_)) for q, r in zip(qs, rs)) / len(qs)
            vr = {g_: rate(qv, rv_, g_) for g_ in grid}; thr, flag = choose_rate_threshold(vr, grid)
            out["calibration"][f"{fam}|{sname}"] = dict(threshold=thr, flagged_no_feasible=flag, validation_rate=vr[thr], test_rate_realized=rate(qt, rt_, thr), target=TARGET_RATE, validation_rates_by_threshold={str(k): round(v, 3) for k, v in vr.items()})
    log("section 6 calibration done")
    # ---------------- stable-day splices
    stable_val, _ = S.stable_days(d, seg["val"], dv); stable_test, info_t = S.stable_days(d, seg["test"], dv)
    out["stable_days"] = dict(validation=len(stable_val), test=len(stable_test), evaluable=len(stable_test) >= 8)
    rng = np.random.default_rng(4242)
    sp_val = build_specs(d, dv, stable_val, rng, N_CAL_NULL, CAL_CELLS, N_CELL)
    cells_all = [(R, dr, du) for R in SIZES for dr in DIRS for du in DURS]
    sp_test = build_specs(d, dv, stable_test, rng, N_NULL, cells_all, N_CELL)
    with stage("build_splices"):
        with mp.get_context("spawn").Pool(4, initializer=D2._init, initargs=(cols,)) as pool: rows_all = pool.map(D2._work, sp_val + sp_test, chunksize=8)
    rv_rows, rt_rows = rows_all[:len(sp_val)], rows_all[len(sp_val):]
    log(f"{len(rows_all)} splices built")
    group = lambda specs, rr: {c: [r for s_, r in zip(specs, rr) if s_["cell"] == c] for c in {s_["cell"] for s_ in specs}}
    gv, gt = group(sp_val, rv_rows), group(sp_test, rt_rows)
    des = lambda rl: [to_des(r, r["iA"]) for r in rl]
    # ---------------- BOCPD threshold by the D4 run-2 rule (validation stable-day splices), then scoring on test splices
    def hits(fam, res, qs, taus, thr): return float(np.mean([any(t <= q["avail"][e["i_c"]] <= t + 60 * 60 * 10 ** 9 for e in events(fam, r, q, thr)) for r, q, t in zip(res, qs, taus)]))
    with stage("h1a_scoring"):
        for (fam, sname), (m, sub, _) in models.items():
            D = 1 + len(sub); grid = DROP_GRID if fam == "bocpd" else HMM_GRID
            def filt(rl): qs = [mk(r, sub) for r in des(rl)]; return qs, V.run_filter(fam, m, qs, D), [r["tau"] for r in rl]
            # calibration splices (validation): run-2 rule
            qn, rn, _ = filt(gv["null"]); cal_null = {g_: float(np.mean([bool(events(fam, r, q, g_)) for q, r in zip(qn, rn)])) for g_ in grid}
            feas = [g_ for g_ in grid if cal_null[g_] <= 0.10]; cb = {}
            for g_ in feas:
                ys = []
                for dr in DIRS:
                    rl = [r for c, v in gv.items() if c != "null" and c[1] == dr for r in v]; q_, r_, t_ = filt(rl); ys.append(hits(fam, r_, q_, t_, g_))
                cb[g_] = float(np.mean(ys))
            run2 = max(feas, key=lambda g_: (cb[g_], -grid.index(g_))) if feas else None
            # test curve
            qn, rn, _ = filt(gt["null"]); xs = {g_: sum(len(events(fam, r, q, g_)) for q, r in zip(qn, rn)) / len(qn) for g_ in grid}
            byratio = {}; allpts = []
            fl = {c: filt(v) for c, v in gt.items() if c != "null"}
            for R in SIZES + ["all"]:
                pts = []
                for g_ in grid:
                    num = den = 0
                    for c, (q_, r_, t_) in fl.items():
                        if R == "all" or c[0] == R:
                            num += sum(any(t <= q["avail"][e["i_c"]] <= t + 3600 * 10 ** 9 for e in events(fam, r, q, g_)) for r, q, t in zip(r_, q_, t_)); den += len(q_)
                    pts.append((xs[g_], num / den))
                byratio[str(R)] = dict(pauc_0_0p5=pauc(pts), hit_at_alarm_rate_0p1=y_at(pts, 0.1), max_alarm_rate_in_grid=max(xs.values()), n_breaks=sum(len(v[0]) for c, v in fl.items() if R == "all" or c[0] == R))
            out["scoring"][f"{fam}|{sname}"] = dict(by_ratio=byratio, run2_threshold=run2, run2_feasible=run2 is not None, alarm_rate_by_threshold={str(g_): round(v, 3) for g_, v in xs.items()})
            log(f"scored {fam}|{sname}")
    out["scoring_difference_f3_minus_base_pauc_all"] = {fam: out["scoring"][f"{fam}|f3"]["by_ratio"]["all"]["pauc_0_0p5"] - out["scoring"][f"{fam}|base"]["by_ratio"]["all"]["pauc_0_0p5"] for fam in FAMS}
    out["stage_seconds"] = TIMES; out["total_minutes"] = round((time.time() - T0) / 60, 2)
    (L.HERE / "results" / "a6_pilot_results.json").write_text(json.dumps(out, indent=1, default=float)); log("done")


if __name__ == "__main__":
    main()
