#!/usr/bin/env python3
"""Diagnostic, RAW fold 3, VALIDATION only (no test segment, no selection): (1) SPY variance ratio after/before tau for break vs null splices;
(2) FA / hit table with extreme splices: calm = bottom volatility decile, stressed = top decile of the validation sessions (session realized variance)."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P

N = 100; THS = [0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 0.9999]
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = dict(base=[], f3=P.FIXED3, f6=P.FIXED6)


def ratios(rows):
    out = {"session": [], "w60": []}
    for r in rows:
        r1, g = r["r1"], r["g"]; sq = r1 ** 2
        out["session"].append(np.nanmean(sq[g + 1:]) / np.nanmean(sq[:g + 1]))
        out["w60"].append(np.nanmean(sq[g + 1:g + 61]) / np.nanmean(sq[max(0, g - 59):g + 1]))
    return {k: np.array(v) for k, v in out.items()}


def q(x): return [round(float(v), 2) for v in np.nanquantile(x, [.1, .25, .5, .75, .9])]


def main():
    primary, _, _ = L.pools(); cols = primary; names = [L.RET_NAME] + cols
    d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    rows = {k: [L.session_grid(d, i, cols) for i in seg[k]] for k in ("train", "val")}
    rng = np.random.default_rng(P.SEED + 300); br_t, nu = V.sample_pairs(d, seg["val"], N, N, rng)      # identical to the earlier run: terciles + null
    rv, vol, n = V.session_stats(d, seg["val"]); fin = np.array([np.isfinite(d["close"][int(d["first"][i]):int(d["end"][i])]).mean() for i in seg["val"]])
    ok = (n == 390) & (fin >= 0.98); s = np.asarray(seg["val"])[ok]; rvv = rv[ok]
    lo, hi = np.quantile(rvv, .1), np.quantile(rvv, .9); calm, stressed = s[rvv <= lo], s[rvv >= hi]
    print("eligible", len(s), "calm decile", len(calm), "stressed decile", len(stressed), flush=True)
    r2 = np.random.default_rng(P.SEED + 400); br_d = []
    for k in range(N):
        up = k % 2 == 0
        for _ in range(100):
            A = int(r2.choice(calm if up else stressed)); B = int(r2.choice(stressed if up else calm)); g = int(r2.choice(V.TAU_SLOTS))
            fa, fb = int(d["first"][A]), int(d["first"][B])
            if np.isfinite(d["close"][[fa + g, fb + g, fb + g + 1]]).all() and d["valid"][fb + g + 1] and d["valid"][fb + g]: break
        br_d.append(dict(iA=A, iB=B, g=g, kind="calm_to_stressed" if up else "stressed_to_calm"))
    rows_all = F.splice_batch(br_t + br_d + nu, "RAW", cols, 4)
    bt, bd, nr = rows_all[:N], rows_all[N:2 * N], rows_all[2 * N:]
    out = {"ratio": {}, "sweep": {}}
    for name, rr, sp in (("break_tercile", bt, br_t), ("break_decile", bd, br_d), ("null", nr, nu)):
        R = ratios(rr); kinds = np.array([x["kind"] for x in sp])
        out["ratio"][name] = {k: dict(all=q(v), **{kd: q(v[kinds == kd]) for kd in ("calm_to_stressed", "stressed_to_calm") if (kinds == kd).any()}) for k, v in R.items()}
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
    for fam in FAMS:
        for sname, sub in SETS.items():
            idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(x) for x in sub]
            mk = lambda r: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx]))
            tr = [mk(r) for r in rows["train"]]; m = V.make_model(fam, K=3, lam=39, starts=1, seed=P.SEED); m.fit(L.pad(tr, len(idx)))
            qn = [mk(r) for r in nr]; rn = V.run_filter(fam, m, qn, len(idx)); ns = V.score_splices(fam, rn, qn, None, False, THS)
            for lab, rr in (("tercile", bt), ("decile", bd)):
                qb = [mk(r) for r in rr]; rb = V.run_filter(fam, m, qb, len(idx)); bs = V.score_splices(fam, rb, qb, [r["tau"] for r in rr], True, THS)
                out["sweep"][f"{fam}|{sname}|{lab}"] = {str(t): dict(fa=ns[t]["fa_rate"], hit=bs[t]["hit_rate"]) for t in THS}
    (L.HERE / "results" / "extreme_results.json").write_text(json.dumps(out, indent=1))
    print(json.dumps(out["ratio"], indent=0)); 
    for k, v in out["sweep"].items(): print(k, " ".join(f"{t}:{x['fa']:.2f}/{x['hit']:.2f}" for t, x in v.items()))


if __name__ == "__main__":
    main()
