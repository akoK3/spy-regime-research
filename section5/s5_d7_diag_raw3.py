#!/usr/bin/env python3
"""D7 diagnostic, RAW fold 3 only (contaminated), no amendment, no result changed. Why do the feature models not respond to a same-day variance splice?
(1) most-likely state (ranked by return variance within the fit) at the open, at tau and over the hour after tau, unmodified vs variance x3, feature vs baseline; alarm clock times on
unmodified test days (A17 fixed thresholds, stored); (2) Cramer's V between the filtered state and the hour of day on all RAW 3 test sessions; (3) the positive control repeated with the
__sadj versions of the selected features (models refitted on inner train for this diagnostic only). Writes section5/results/d7_diag_raw3.json."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_d7 as D, s5_backend as BK, s5_lib as L, s5_fast as F, s5_d2 as D2, s5_eval as V, s5_d2_stable as S, s5_sweep as W, s5_a7 as B

HERE = Path(__file__).resolve().parent; FAMS = D.H1_FAMILIES; HOURS = [(0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 360), (360, 391)]


def rank_of(model):
    o = np.argsort(model.var[:, 0]); r = np.empty_like(o); r[o] = np.arange(len(o)); return r                       # 0 = lowest return variance


def cramers_v(a, b):
    a, b = np.asarray(a), np.asarray(b); ua, ia = np.unique(a, return_inverse=True); ub, ib = np.unique(b, return_inverse=True)
    T = np.zeros((len(ua), len(ub))); np.add.at(T, (ia, ib), 1); E = T.sum(1, keepdims=True) * T.sum(0, keepdims=True) / T.sum()
    chi2 = ((T - E) ** 2 / np.where(E > 0, E, 1)).sum(); k = min(T.shape) - 1; return float(np.sqrt(chi2 / (T.sum() * k))) if k > 0 else float("nan")


def days_and_taus(d, stable):
    out = []
    for i in stable:
        rng = np.random.default_rng((D.SEED, 1, 3, int(i))); p0 = L.sub_panel(d, [i]); g = None
        for _ in range(200):
            gg = int(rng.choice(V.TAU_SLOTS))
            if D.window_ok(p0, gg): g = gg; break
        if g is not None: out.append((int(i), g, int(p0["available"][g])))
    return out


def splice_rows(d, dv, bases, cols, dt, ratios):
    rows = []
    for i, g, tau in dt:
        fa = int(d["first"][i]); pre = np.nanmean(dv[fa + 1:fa + g + 1]); rB2 = np.where(d["valid"][fa:fa + 390], d["r"][fa:fa + 390], np.nan) ** 2; post = np.nanmean(F.in_units_of_A(d, i, rB2)[g + 1:390])
        r = {"null": F.rows_from_panel(d, bases, L.sub_panel(d, [i]), i, i, g, tau, cols)}
        for R in ratios: r[R] = F.rows_from_panel(d, bases, D2.regime_panel(d, i, i, g, float(np.sqrt(R * pre / post)), None)[0], i, i, g, tau, cols)
        rows.append(r)
    return rows


def sweep_gain(fam, model, mk, to_des, sub, rows, dt, label):
    keys = [(j, k) for j in range(len(rows)) for k in ("null", label)]; qs = [mk(to_des(rows[j][k], dt[j][0]), sub) for j, k in keys]; rs = V.run_filter(fam, model, qs, 1 + len(sub))
    R_, re_, av_ = W.stack(rs, qs, "P"); cnt, hit = W.sweep_old_state(R_, re_, av_, B.THETA, np.array([dt[j][2] for j, _ in keys], np.int64)); sw = {"null_counts": [None] * len(rows), "null": [None] * len(rows), "x": [None] * len(rows)}
    for n, (j, k) in enumerate(keys):
        sw["null" if k == "null" else "x"][j] = "".join("1" if x else "0" for x in hit[n])
        if k == "null": sw["null_counts"][j] = cnt[n].tolist()
    a, b = D.sweep_day_values(dict(days=rows, sweep={"m": sw}), "m", "x"); return D.cluster_diff(a, b, [str(x[0]) for x in dt], nboot=10000)


def main():
    import s5_contamination as C; C.check_registry(HERE)
    man = json.loads((D.A17 / "a17_results.json").read_text(encoding="utf-8"))["models_manifest"]; db = BK.DataBackend("RAW", 3); models, thr = D.load_fold_models("RAW|3", man)
    c = db.c; d, dv, cols = c["d"], c["dv"], c["cols"]; stable, _ = S.stable_days(d, c["seg"]["test"], dv); bases = F.load_bases(d, "RAW", cols); dt = days_and_taus(d, stable)
    rows = splice_rows(d, dv, bases, cols, dt, [3.0]); out = dict(fold="RAW|3", n_days=len(dt), states={}, alarm_minutes={}, cramers_v={}, sadj={})
    # (1) states
    for fam in FAMS:
        for which in ("feature", "baseline"):
            m, sub = models[fam][which]; rk = rank_of(m); K = len(rk); res = {}
            for lab in ("null", 3.0):
                qs = [c["mk"](c["to_des"](r[lab], dt[j][0]), sub) for j, r in enumerate(rows)]; ps = V.run_filter(fam, m, qs, 1 + len(sub)); o, at, after = [], [], []
                for q, p, (i, g, tau) in zip(qs, ps, dt):
                    s = rk[p["P"].argmax(1)]; real = np.where(q["real"][:q["n"]])[0]; kt = int(np.searchsorted(q["avail"][:q["n"]], tau, side="right")) - 1; aft = (q["avail"][:q["n"]] > tau) & (q["avail"][:q["n"]] <= tau + 60 * 60 * 10 ** 9)
                    o.append(int(s[real[0]])); at.append(int(s[kt])); after.append(int(np.bincount(s[aft], minlength=K).argmax()))
                res["unmodified" if lab == "null" else "variance_x3"] = dict(open=np.bincount(o, minlength=K).tolist(), at_tau=np.bincount(at, minlength=K).tolist(), modal_after_tau=np.bincount(after, minlength=K).tolist(),
                                                                          after_equals_open=float(np.mean(np.array(after) == np.array(o))), open_is_highest=float(np.mean(np.array(o) == K - 1)), after_is_highest=float(np.mean(np.array(after) == K - 1)))
            out["states"][f"{fam}|{which}"] = dict(K=K, **res)
            ck = json.loads((D.A17 / "ckpt" / f"RAW_3_{fam}.json").read_text(encoding="utf-8")); mins = [a[1] for v in ck["alarms"][which].values() for a in v]
            out["alarm_minutes"][f"{fam}|{which}"] = dict(n=len(mins), per_hour=[int(sum(1 for x in mins if a <= x < b)) for a, b in HOURS])
    # (2) Cramer's V, all RAW 3 test sessions (unmodified)
    for fam in FAMS:
        for which in ("feature", "baseline"):
            m, sub = models[fam][which]; qs = db.sequences("test", sub); ps = V.run_filter(fam, m, qs, 1 + len(sub)); st, hr = [], []
            for q, p in zip(qs, ps):
                ok = q["real"][:q["n"]]; st += list(p["P"].argmax(1)[ok]); hr += list(np.searchsorted([b for _, b in HOURS], q["slots"][:q["n"]][ok], side="right"))
            out["cramers_v"][f"{fam}|{which}"] = cramers_v(st, hr)
    # (3) __sadj substitution (diagnostic refit on inner train)
    sadj = lambda x: x + "__sadj" if x + "__sadj" in L.pools()[0] else x
    for fam in FAMS:
        sub0 = models[fam]["feature"][1]; sub = tuple(sadj(x) for x in sub0); ncols = sorted(set(cols) | set(sub)); dd = L.load_era("RAW", ncols + ["lee_mykland_approx60"]); seg = L.fold_segments(dd, "RAW", 3)
        native = {i: L.session_grid(dd, i, list(sub)) for i in set(seg["train"].tolist()) | {x[0] for x in dt}}; Mx = np.full((len(dd["first"]), 78), np.nan)
        for i in range(len(dd["first"])): x = L.session_grid(dd, i, [])["X"][:, 0]; Mx[i, :len(x)] = x
        to_des = lambda r, i: dict(r, X=F.deseason(r["X"], F.ret5_scale(Mx, i))); names = [L.RET_NAME] + list(sub)
        prep = L.Prep().fit(np.vstack([to_des(native[i], i)["X"] for i in seg["train"]]), names); mk = lambda r, s_: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in s_]]))
        K = models[fam]["feature"][0].K; m = V.make_model(fam, K=K, lam=39, starts=3, seed=0, Dmax=78); m.fit(L.pad([mk(to_des(native[i], i), sub) for i in seg["train"]], 1 + len(sub)))
        rs_ = splice_rows(dd, S.des_variance(dd), F.load_bases(dd, "RAW", list(sub)), list(sub), dt, [3.0, 5.29])
        out["sadj"][fam] = dict(features=list(sub), x3=sweep_gain(fam, m, mk, to_des, sub, rs_, dt, 3.0), x5_29=sweep_gain(fam, m, mk, to_des, sub, rs_, dt, 5.29))
        m0, s0 = models[fam]["feature"]; out["sadj"][fam]["original_features_x3"] = sweep_gain(fam, m0, c["mk"], c["to_des"], s0, rows, dt, 3.0)
        print(fam, sub, {k: (round(v["diff"], 2), [round(x, 2) for x in v["ci95"]], v["responds"]) for k, v in out["sadj"][fam].items() if isinstance(v, dict)}, flush=True)
    (HERE / "results" / "d7_diag_raw3.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8"); print(json.dumps({k: out[k] for k in ("states", "alarm_minutes", "cramers_v")}))


if __name__ == "__main__":
    main()
