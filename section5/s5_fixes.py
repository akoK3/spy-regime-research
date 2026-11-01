#!/usr/bin/env python3
"""Pilot-fold (RAW fold 3) diagnosis of null-splice false alarms and test of proposed fixes. VALIDATION segment only: 100 break + 100 null splices from the
validation sessions; the fold's test segment is not used. No selection: fixed sets base / f3 / f6 (a priori), K=3, lambda=39, 1 start, seed 0.
Fixes: (a) causal slot deseasonalisation of the 5-min return, (b) thresholds above 0.99, (c) miss rule (delay censored at 60 min), (d) BOCPD persistence."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_models as M, s5_events as E, s5_eval as V, s5_fast as F, s5_pilot as P

WORKERS = 4
N = 100
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]
SETS = dict(base=[], f3=P.FIXED3, f6=P.FIXED6)
DIAG_THR = [0.9, 0.99]
CENSOR = 60.0


def tod_bin(slot_plus1):
    m = 9 * 60 + 30 + int(slot_plus1)       # clock minutes of availability
    return f"{m // 60:02d}:00-{m // 60 + 1:02d}:00" if m >= 10 * 60 else "09:30-10:00" if m < 10 * 60 else None


def main():
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    rows = {k: [L.session_grid(d, i, cols) for i in seg[k]] for k in ("train", "val")}
    Mx = F.ret5_matrix(d, cols)
    rng = np.random.default_rng(P.SEED + 300)
    br, nu = V.sample_pairs(d, seg["val"], N, N, rng)
    t = time.perf_counter(); srows = F.splice_batch(br + nu, "RAW", cols, WORKERS); log(f"{len(srows)} splices built with {WORKERS} workers in {time.perf_counter()-t:.0f}s")
    brows, nrows = srows[:N], srows[N:]
    ratio = []
    for r_ in brows:
        r1, g_ = r_["r1"], r_["g"]; a_, b_ = r1[:g_ + 1], r1[g_ + 1:]
        ratio.append(np.nanmean(b_ ** 2) / np.nanmean(a_ ** 2))
    variants = {}
    for v in ("raw", "des"):
        def xf(r, sess):
            return r["X"] if v == "raw" else F.deseason(r["X"], F.ret5_scale(Mx, sess))
        tr = [dict(r, X=xf(r, r["sess"])) for r in rows["train"]]
        prep = L.Prep().fit(np.vstack([r["X"] for r in tr]), names)
        variants[v] = dict(prep=prep, train=tr, brk=[dict(r, X=xf(r, r["iA"])) for r in brows], nul=[dict(r, X=xf(r, r["iA"])) for r in nrows],
                           val=[dict(r, X=xf(r, r["sess"])) for r in rows["val"]])
    log("variants prepared; deseason scale NaN share in train rows: %.4f" % np.mean([~np.isfinite(r["X"][:, 0]).all() for r in variants["des"]["train"]]))

    def seqs(rowlist, prep, subset):
        idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(n) for n in subset]
        return [L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx])) for r in rowlist]

    def fit_filter(fam, v, subset):
        vv = variants[v]; D = 1 + len(subset)
        tr = seqs(vv["train"], vv["prep"], subset); m = V.make_model(fam, K=3, lam=39, starts=1, seed=P.SEED); m.fit(L.pad(tr, D))
        qn, qb = seqs(vv["nul"], vv["prep"], subset), seqs(vv["brk"], vv["prep"], subset)
        return dict(qn=qn, qb=qb, rn=V.run_filter(fam, m, qn, D), rb=V.run_filter(fam, m, qb, D),
                    taub=[r["tau"] for r in vv["brk"]], taun=[r["tau"] for r in vv["nul"]], gn=[r["g"] for r in vv["nul"]], abst=L.shares(qn))

    out = dict(break_variance_ratio_post_over_pre_quantiles=[float(x) for x in np.nanquantile(ratio, [0.1, 0.25, 0.5, 0.75, 0.9])], break_kinds=[sp_["kind"] for sp_ in br[:2]], n_break=N, n_null=N, workers=WORKERS, diag={}, fixes={}, per_feature={}, sweep={})
    cache = {}
    # ---- 1. diagnosis (raw return, as piloted): null-splice false alarms by clock time, model and feature set
    for fam in FAMS:
        for sname, sub in SETS.items():
            cache[(fam, sname, "raw")] = fr = fit_filter(fam, "raw", sub)
            for thr in DIAG_THR:
                bins, before, after, nevent, nsess = {}, 0, 0, 0, 0
                for q, r, g in zip(fr["qn"], fr["rn"], fr["gn"]):
                    ev = V.events_for(fam, r, q, thr)[0]; nsess += bool(ev)
                    for e in ev:
                        b = tod_bin(q["slots"][e["i_d"]] + 1); bins[b] = bins.get(b, 0) + 1; nevent += 1
                        if q["slots"][e["i_d"]] <= g: before += 1
                        else: after += 1
                out["diag"][f"{fam}|{sname}|{thr}"] = dict(sessions_with_fa=int(nsess), fa_rate=nsess / len(fr["qn"]), events=nevent, events_by_clock_hour=bins, events_T_d_at_or_before_seam=before, events_T_d_after_seam=after)
        log(f"diag {fam}")
    for fam in FAMS:
        for feat in cols:
            fr = fit_filter(fam, "raw", [feat])
            out["per_feature"][f"{fam}|{feat}"] = {str(thr): float(np.mean([bool(V.events_for(fam, r, q, thr)[0]) for q, r in zip(fr["qn"], fr["rn"])])) for thr in DIAG_THR}
        log(f"per-feature {fam}")

    # ---- 2/3. fixes
    def evaluate(fam, fr, grid, pers):
        ns = V.score_splices(fam, fr["rn"], fr["qn"], None, False, grid, pers); thr = V.choose_threshold(ns, grid)
        if thr is None: return dict(threshold=None)
        bs = V.score_splices(fam, fr["rb"], fr["qb"], fr["taub"], True, [thr], pers)[thr]
        dl = bs["delays"]; cens = dl + [CENSOR] * (bs["n"] - len(dl))
        kinds = {}
        return dict(threshold=thr, null_fa=ns[thr]["fa_rate"], hit_rate=bs["hit_rate"], median_delay_hits_min=float(np.median(dl)) if dl else None,
                    median_delay_censored60_min=float(np.median(cens)), dropped_break=bs["dropped"])
    cfgs = [("piloted (raw, grid<=0.99)", "raw", False, False), ("b: extended grid", "raw", True, False), ("a: deseasonalised return", "des", False, False), ("a+b", "des", True, False),
            ("b+d: persistence", "raw", True, True), ("a+b+d", "des", True, True), ("d only (grid<=0.99)", "raw", False, True)]
    for fam in FAMS:
        for sname, sub in SETS.items():
            if sname == "f6" and fam == "bocpd": pass
            for label, v, ext, pers in cfgs:
                if pers and fam != "bocpd": continue
                key = (fam, sname, v)
                if key not in cache: cache[key] = fit_filter(fam, v, sub)
                if f"{fam}|{sname}|{v}" not in out["sweep"]:
                    g_ = V.thr_grid(fam, True); nsw = V.score_splices(fam, cache[key]["rn"], cache[key]["qn"], None, False, g_); bsw = V.score_splices(fam, cache[key]["rb"], cache[key]["qb"], cache[key]["taub"], True, g_)
                    nwin = V.score_splices(fam, cache[key]["rn"], cache[key]["qn"], cache[key]["taun"], True, g_)   # chance level: confirmed event in [tau, tau+60 min] of a NULL splice
                    out["sweep"][f"{fam}|{sname}|{v}"] = {str(t): dict(null_fa=nsw[t]["fa_rate"], hit_rate=bsw[t]["hit_rate"], null_window_rate=nwin[t]["hit_rate"]) for t in g_}
                out["fixes"][f"{fam}|{sname}|{label}"] = dict(evaluate(fam, cache[key], V.thr_grid(fam, ext), pers), abstained_share_null=cache[key]["abst"]["abstained_share"])
        log(f"fixes {fam}")
    out["minutes"] = round((time.time() - T0) / 60, 2)
    (L.HERE / "results" / "fixes_results.json").write_text(json.dumps(out, indent=1, default=str))
    log("done")


if __name__ == "__main__":
    main()
