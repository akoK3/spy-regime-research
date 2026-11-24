#!/usr/bin/env python3
"""Section 5 pilot: ONE fold (RAW, smallest outer block = fold 3), fixed a-priori feature sets (NO selection), timing per fit, splice-integrity tests on real data.
Uses TRAIN-partition sessions only (asserted). Checkpointed: rerunning resumes. Output: section5/results/pilot_results.json."""
import sys, json, time, platform, datetime
from pathlib import Path
import numpy as np
import scipy

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_models as M, s5_events as E, s5_eval as V

ERA, FOLD = "RAW", 3
SEED = 0
FIXED3 = ["rv5_strict__sadj", "relative_volume20", "intrabar_range_log__sadj"]     # a-priori timing set, NOT selected
FIXED6 = FIXED3 + ["downside5_strict__sadj", "momentum15_endpoint", "close_location_proxy"]
N_SPLICE = dict(val_break=24, val_null=24, test_break=24, test_null=24)
FAMILIES = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]
RES = L.HERE / "results"
T0 = time.time()
TIMINGS = []


def log(m):
    print(f"[{(time.time()-T0)/60:6.1f} min] {m}", flush=True)


def timed(label, fn, **meta):
    t = time.perf_counter(); out = fn(); dt = time.perf_counter() - t
    TIMINGS.append(dict(unit=label, seconds=round(dt, 4), **meta)); return out


def main():
    ck = L.Checkpoint(L.HERE / "cache" / "pilot_ckpt")
    primary, sens, _ = L.pools()
    L.assert_pool(primary, "primary"); L.assert_pool(FIXED6, "primary")
    cols = primary
    names = [L.RET_NAME] + cols
    d = timed("load_era_and_features", lambda: L.load_era(ERA, cols + ["lee_mykland_approx60"]), era=ERA)
    L.assert_single_era(d, ERA)
    seg = L.fold_segments(d, ERA, FOLD)
    log(f"fold {FOLD}: train {len(seg['train'])}, val {len(seg['val'])}, test {len(seg['test'])} sessions; days {d['day'][d['first'][seg['train'][0]]]}..{d['day'][d['first'][seg['test'][-1]]]}")
    rows = {k: [L.session_grid(d, i, cols) for i in seg[k]] for k in ("train", "val", "test")}
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
    lmcols = np.concatenate([d["features"]["lee_mykland_approx60"][d["first"][i]:d["end"][i]] for i in seg["train"]])
    lm = timed("lm_student_t_threshold", lambda: L.lm_student_t_threshold(lmcols))
    log(f"prep keeps {len(prep.keep)}/{len(names)}; LM t-threshold {lm['threshold']:.4f} (df {lm['df']:.2f})")

    def seqs(rowlist, subset):
        idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(n) for n in subset]
        out = []
        for r in rowlist:
            q = L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx])); out.append(q)
        return out

    variants = dict(base=[], f3=FIXED3, f6=FIXED6)
    D = {k: 1 + len(v) for k, v in variants.items()}
    result = dict(era=ERA, fold=FOLD, segments={k: len(seg[k]) for k in ("train", "val", "test")}, prep=prep.info, lm_t=lm, shares={}, fits={}, qlike={}, splice={}, seeds=dict(base=SEED), versions=dict(python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__))
    for v, sub in variants.items():
        result["shares"][v] = {k: L.shares(seqs(rows[k], sub)) for k in ("train", "val")}

    # ---- splice rows (features recomputed from the spliced series), shared by all families
    rng = np.random.default_rng(SEED + 100)
    vb, vn = V.sample_pairs(d, seg["val"], N_SPLICE["val_break"], N_SPLICE["val_null"], rng)
    tb, tn = V.sample_pairs(d, seg["test"], N_SPLICE["test_break"], N_SPLICE["test_null"], rng)
    splice_rows = {}
    for tag, lst in (("val_break", vb), ("val_null", vn), ("test_break", tb), ("test_null", tn)):
        out = []
        for j, sp in enumerate(lst):
            key = f"splice_row|{ERA}|{FOLD}|{sp['iA']}|{sp['iB']}|{sp['g']}"
            row = ck.run(key, lambda sp=sp: timed("splice_features_per_splice", lambda: V.splice_rows(d, sp["iA"], sp["iB"], sp["g"], cols), hist=20))
            out.append((sp, row))
        splice_rows[tag] = out
        log(f"splice rows {tag}: {len(out)}")

    # ---- fits and scoring
    for fam in FAMILIES:
        for v, sub in variants.items():
            Dv = D[v]; tr = seqs(rows["train"], sub); btr = L.pad(tr, Dv)
            lam_list = [12, 39, 78] if fam == "bocpd" else [None]
            key = f"fit|{ERA}|{FOLD}|{fam}|{v}|K3|lam39|start1|seed{SEED}"
            def fit1():
                m = V.make_model(fam, K=3, lam=39, starts=1, seed=SEED)
                t = time.perf_counter(); m.fit(btr); dt = time.perf_counter() - t
                return m, dt
            m, dt = ck.run(key, fit1)
            TIMINGS.append(dict(unit="fit", family=fam, variant=v, D=Dv, starts=1, K=3, lam=39, seconds=round(dt, 4), iterations=getattr(m, "fit_info", {}).get("iterations")))
            if fam != "bocpd" and v in ("base", "f3"):
                key3 = f"fit|{ERA}|{FOLD}|{fam}|{v}|K3|start3|seed{SEED}"
                def fit3():
                    m3 = V.make_model(fam, K=3, starts=3, seed=SEED)
                    t = time.perf_counter(); m3.fit(btr); return m3, time.perf_counter() - t
                m3, dt3 = ck.run(key3, fit3)
                TIMINGS.append(dict(unit="fit", family=fam, variant=v, D=Dv, starts=3, K=3, seconds=round(dt3, 4), iterations=m3.fit_info["iterations"]))
            if fam == "hsmm" and v == "base":
                def fit_k2():
                    mm = V.make_model("hsmm", K=2, starts=1, seed=SEED); t = time.perf_counter(); mm.fit(btr); return mm, time.perf_counter() - t
                _, dt2 = ck.run(f"fit|{ERA}|{FOLD}|hsmm|base|K2|start1|seed{SEED}", fit_k2)
                TIMINGS.append(dict(unit="fit", family="hsmm", variant="base", D=Dv, starts=1, K=2, seconds=round(dt2, 4)))
            if v == "f6": continue      # timing only
            va = seqs(rows["val"], sub)
            res_tr = timed("filter_train", lambda: V.run_filter(fam, m, tr, Dv), family=fam, variant=v, sessions=len(tr))
            res_va = timed("filter_val", lambda: V.run_filter(fam, m, va, Dv), family=fam, variant=v, sessions=len(va))
            vals = V.state_values(fam, res_tr, tr)
            ql, keys = V.qlike_series(fam, res_va, va, vals)
            result["qlike"].setdefault(fam, {})[v] = dict(mean_qlike_val=float(ql.mean()), n=int(len(ql)), values=[float(x) for x in vals])
            result["qlike"][fam][v + "_series"] = (ql, keys)
            if fam == "hsmm" or fam == "gaussian_hmm":
                result["fits"][f"{fam}_{v}"] = dict(loglik=float(m.loglik), var_ret=[float(x) for x in m.var[:, 0]], iterations=m.fit_info["iterations"])
            # splices: calibrate on validation, score the test splices once
            grid = V.thr_grid(fam)
            def spl_res(tag):
                lst = splice_rows[tag]; qs = [L.build_sequence(dict(r, X=prep.transform(r["X"])[:, [prep.keep.index(L.RET_NAME)] + [prep.keep.index(n) for n in sub]])) for _, r in lst]
                return qs, timed("filter_splices", lambda: V.run_filter(fam, m, qs, Dv), family=fam, variant=v, sessions=len(qs)), [r["tau"] for _, r in lst]
            qn, rn, _ = spl_res("val_null"); qb, rb, taub = spl_res("val_break")
            ns = V.score_splices(fam, rn, qn, None, False, grid); thr = V.choose_threshold(ns, grid)
            bs = V.score_splices(fam, rb, qb, taub, True, grid)
            entry = dict(threshold=thr, val_null_fa=ns[thr]["fa_rate"] if thr is not None else None, val_hit_rate=bs[thr]["hit_rate"] if thr is not None else None, val_delays_median=float(np.median(bs[thr]["delays"])) if thr is not None and bs[thr]["delays"] else None)
            if thr is not None:      # test splices scored once at the validation-chosen threshold
                qtn, rtn, _ = spl_res("test_null"); qtb, rtb, tautb = spl_res("test_break")
                tn_s = V.score_splices(fam, rtn, qtn, None, False, [thr]); tb_s = V.score_splices(fam, rtb, qtb, tautb, True, [thr])
                entry.update(test_fa=tn_s[thr]["fa_rate"], test_hit_rate=tb_s[thr]["hit_rate"], test_delays_n=len(tb_s[thr]["delays"]))
                dirs = []
                for (sp, row), q, rs in zip(splice_rows["test_break"], qtb, rtb):
                    for e in V.events_for(fam, rs, q, thr)[0]:
                        dirs.append(E.direction(row["r1"], q["slots"], e["i_d"], e["i_c"])[0])
                entry["test_direction_counts"] = {k: dirs.count(k) for k in set(dirs)}
            entry["abstention_skip_val_null"] = L.shares(qn)
            result["splice"].setdefault(fam, {})[v] = entry
            log(f"{fam}/{v}: fit {dt:.2f}s thr {thr} qlike_val {ql.mean():.4f}")
        # BOCPD lambda timing (filter is the whole cost)
        if fam == "bocpd":
            for lam in (12, 78):
                mm = V.make_model("bocpd", lam=lam); tr = seqs(rows["train"], FIXED3)
                timed("filter_train", lambda: V.run_filter("bocpd", mm, tr, D["f3"]), family="bocpd", variant="f3", lam=lam, sessions=len(tr))

    # Diebold-Mariano (feature f3 vs return-only), validation only, pilot
    for fam in FAMILIES:
        (lb, kb), (lf, kf) = result["qlike"][fam]["base_series"], result["qlike"][fam]["f3_series"]
        ab, af, common = V.align(lb, kb, lf, kf)
        result["qlike"][fam]["dm_val_f3_vs_base"] = dict(V.diebold_mariano(ab, af), common_bars=int(len(common)))
        result["qlike"][fam]["base_series"] = None; result["qlike"][fam]["f3_series"] = None

    # ---- splice integrity on real data (3 splices)
    result["integrity"] = integrity(d, seg, cols, ck)
    result["timings"] = TIMINGS
    result["checkpoint"] = dict(hits=ck.hits, misses=ck.misses)
    result["total_minutes"] = round((time.time() - T0) / 60, 2)
    RES.joinpath("pilot_results.json").write_text(json.dumps(result, indent=1, default=lambda o: o.tolist() if hasattr(o, "tolist") else str(o)), encoding="utf-8")
    log("done")


def integrity(d, seg, cols, ck):
    rng = np.random.default_rng(SEED + 7)
    out = []
    pairs = [sp for sp in V.sample_pairs(d, seg["val"], 30, 0, rng)[0] if not (sp["iA"] - 20 <= sp["iB"] <= sp["iA"] - 1)][:3]   # B outside A's 20-session history window
    assert len(pairs) == 3
    for sp in pairs:
        iA, iB, g = sp["iA"], sp["iB"], sp["g"]
        p, k, tau = V.make_splice(d, iA, iB, g); a = int(p["first"][k]); fa, fb = int(d["first"][iA]), int(d["first"][iB])
        chk = {}
        chk["price_continuous_at_tau"] = bool(p["close"][a + g] == d["close"][fa + g] and abs(np.log(p["close"][a + g + 1] / p["close"][a + g]) - np.log(d["close"][fb + g + 1] / d["close"][fb + g])) < 1e-12)
        ch = np.where(~np.isclose(p["close"][a:a + 390], d["close"][fa:fa + 390], rtol=0, atol=0, equal_nan=True))[0]
        chk["tau_exact_first_changed_bar_is_g_plus_1"] = bool(ch.min() == g + 1)
        chk["tau_is_availability_of_bar_g"] = bool(tau == d["available"][fa + g] == d["t"][fa + g + 1])
        chk["tau_in_11:00-14:30"] = bool(pd_minutes(d, fa, tau) >= 90 and pd_minutes(d, fa, tau) <= 300)
        base = V.splice_rows(d, iA, iB, g, cols)
        # (i) before tau the spliced features equal the native features of A (same code on the real panel)
        native = L.session_grid(d, iA, cols); pre = base["slots"] <= g
        chk["pre_tau_features_equal_A_native"] = bool(np.allclose(base["X"][pre], native["X"][pre], rtol=1e-9, atol=0, equal_nan=True))
        # (ii) B's pre-tau bars are irrelevant
        d2 = {k_: (v.copy() if isinstance(v, np.ndarray) else v) for k_, v in d.items()}
        for key in ("close", "open", "high", "low"): d2[key][fb:fb + g] *= 1.3
        d2["volume"][fb:fb + g] *= 7; d2["r"][fb + 1:fb + g] *= 1.5
        r2 = V.splice_rows(d2, iA, iB, g, cols)
        chk["B_pre_tau_changes_do_not_move_spliced_features"] = bool(np.array_equal(base["X"], r2["X"], equal_nan=True))
        # (iii) A's post-tau bars are irrelevant
        d3 = {k_: (v.copy() if isinstance(v, np.ndarray) else v) for k_, v in d.items()}
        for key in ("close", "open", "high", "low"): d3[key][fa + g + 1:fa + 390] *= 1.3
        d3["volume"][fa + g + 1:fa + 390] *= 7; d3["r"][fa + g + 2:fa + 390] *= 1.5
        r3 = V.splice_rows(d3, iA, iB, g, cols)
        chk["A_post_tau_changes_do_not_move_spliced_features"] = bool(np.array_equal(base["X"], r3["X"], equal_nan=True))
        # (iv) power: after tau the spliced features do differ from A's native features
        post = base["slots"] > g + 10
        chk["post_tau_features_differ_from_A_native"] = bool((~np.isclose(base["X"][post], native["X"][post], rtol=1e-6, atol=0, equal_nan=True)).any())
        chk["pass"] = all(v for v in chk.values())
        out.append(dict(iA=int(iA), iB=int(iB), g=int(g), kind=sp["kind"], checks=chk))
    return out


def pd_minutes(d, fa, tau):
    return int((tau - d["t"][fa]) // E.MIN)


if __name__ == "__main__":
    main()
