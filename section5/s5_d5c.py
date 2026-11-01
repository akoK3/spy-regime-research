#!/usr/bin/env python3
"""D5 part C: real-noise check. RAW fold 3, VALIDATION stable-day null splices of D2 (identical sampling, 400 nulls). Return-only detectors (D = 1) at both grids:
5-minute return (ret5, 78 updates) and 1-minute return (390 updates). Models are fitted on real inner-train returns (5-min: all 189 train sessions; 1-min: the last 40
train sessions, equal data), z-scored with the train mean/sd; thresholds are those calibrated on SYNTHETIC data in part B (R = 3 and R = 10, Gaussian and Student-t df 5)
for the same grid / family / K. Output: share of null sessions with any confirmed alarm (FA per session) and alarms per 20 sessions. No features, no deseasonalisation
(raw returns, as the D2 return-only detectors)."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_events as E, s5_pilot as P, s5_d2 as D2, s5_d2_stable as S

FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm"]; KS = [2, 3]


def main():
    b = json.loads((L.HERE / "results" / "d5b_results.json").read_text())
    d = L.load_era("RAW", ["return_1m"]); seg = L.fold_segments(d, "RAW", 3); dv = S.des_variance(d)
    stable = json.loads((L.HERE / "results" / "d2_stable_days.json").read_text())["stable"]; rng = np.random.default_rng(P.SEED + 500)
    rv, _, _ = V.session_stats(d, stable); tv = V.tercile(rv); stable = np.array(stable); specs = []
    for _ in range(D2.N_NULL):                                   # identical to s5_d2.py / s5_d3.py
        for _t in range(200):
            c = np.where(tv == int(rng.integers(3)))[0]
            if len(c) < 2: continue
            A, B = rng.choice(c, 2, replace=False); A, B = int(stable[A]), int(stable[B]); g = int(rng.choice(V.TAU_SLOTS))
            if D2.finite_ok(d, A, B, g, None): break
        specs.append((A, B, g))
    # null sessions: spliced panels without features
    nul5, nul1 = [], []
    for A, B, g in specs:
        p, k, tau = V.make_splice(d, A, B, g, hist=0)
        row = L.session_grid(p, 0, []); x5 = row["X"][:, :1]; nul5.append(dict(slots=row["slots"], avail=row["avail"], X=x5, tgt=np.full(len(x5), np.nan)))
        r1 = np.where(p["valid"], p["r"], np.nan)[:, None]; nul1.append(dict(slots=np.arange(390), avail=p["available"][:390], X=r1, tgt=np.full(390, np.nan)))
    # train sessions
    tr5 = [L.session_grid(d, i, [])["X"][:, :1] for i in seg["train"]]
    tr1 = [np.where(d["valid"][int(d["first"][i]):int(d["end"][i])], d["r"][int(d["first"][i]):int(d["end"][i])], np.nan)[:, None] for i in seg["train"][-40:]]
    out = {}
    for grid, trx, nul in (("5min", tr5, nul5), ("1min", tr1, nul1)):
        allx = np.concatenate(trx); mu, sd = np.nanmean(allx), np.nanstd(allx); z = lambda X: (X - mu) / sd
        mk = lambda X, a, s: L.build_sequence(dict(sess=0, slots=s, avail=a, X=z(X), tgt=np.full(len(X), np.nan)))
        trs = [mk(X, (np.arange(len(X)) + 1) * 60 * 10 ** 9, np.arange(len(X))) for X in trx]
        qn = [mk(r["X"], r["avail"], r["slots"]) for r in nul]
        for fam in FAMS:
            for K in KS:
                m = V.make_model(fam, K=K, starts=1, seed=0, Dmax=(78 if grid == "5min" else 390)); m.fit(L.pad(trs, 1)); rn = V.run_filter(fam, m, qn, 1)
                for dt in ("gaussian", "student_t5"):
                    for R in (3, 10):
                        thr = b[f"{dt}|R{R}|{grid}|{fam}|K={K}"]["threshold"]
                        evs = [E.detect_old_state(r["P"], q["real"], q["avail"], thr)[0] for r, q in zip(rn, qn)]
                        out[f"{grid}|{fam}|K={K}|{dt}|R{R}"] = dict(threshold=thr, real_fa=float(np.mean([bool(e) for e in evs])), per20=20.0 * sum(len(e) for e in evs) / len(evs))
        print(grid, "done", flush=True)
    (L.HERE / "results" / "d5c_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
