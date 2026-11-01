#!/usr/bin/env python3
"""D3 test 1: implementation sanity on pure synthetic iid Gaussian data (no market data).
Grid sessions of 78 five-minute updates. Training set (189 sessions): iid N(0,1) in the calm regime and N(0,10) (10x variance) in the stressed regime, regimes
assigned per session as all-calm 40%, all-stressed 20%, calm->stressed switch 20%, stressed->calm switch 20% (switch time uniform over updates 20-60).
Test: 200 null sessions (all calm) and 200 break sessions per direction (calm until update J0=36, then 10x variance to the close; and the reverse).
Detectors: the pipeline's four families, K=3, lambda=39, 1 start, same event logic (hold 3, refractory 30 min, first 2 updates silent). Variants: D=1 (the return) and
D=4 (return + 3 independent N(0,1) noise features). tau = availability of update J0-1. Hit = T_c within 60 min of tau."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_events as E

T = 78; J0 = 36; MIN = E.MIN
THS = {"states": [0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 0.9999], "bocpd": [0.01, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5, 0.7, 0.9, 0.95, 0.99, 0.999]}


def session(rng, kind, D):
    sd = np.ones(T)
    if kind == "stressed": sd[:] = np.sqrt(10)
    elif kind == "up": sd[J0:] = np.sqrt(10)
    elif kind == "down": sd[:J0] = np.sqrt(10)
    elif kind == "rand_up": j = int(rng.integers(20, 61)); sd[j:] = np.sqrt(10)
    elif kind == "rand_down": j = int(rng.integers(20, 61)); sd[:j] = np.sqrt(10)
    X = rng.standard_normal((T, D)); X[:, 0] *= sd
    return X


def seq(X, k=0):
    return dict(sess=k, n=len(X), X=X, real=np.ones(len(X), bool), avail=(np.arange(len(X)) + 1) * 5 * MIN, tgt=np.full(len(X), np.nan), slots=4 + 5 * np.arange(len(X)), start=0, grid_n=len(X))


def main():
    out = {}
    for D in (1, 4):
        rng = np.random.default_rng(2024 + D)
        kinds = rng.choice(["calm", "stressed", "rand_up", "rand_down"], size=189, p=[.4, .2, .2, .2])
        tr = [seq(session(rng, "calm" if k == "calm" else k, D), i) for i, k in enumerate(kinds)]
        nulls = [seq(session(rng, "calm", D)) for _ in range(200)]
        ups = [seq(session(rng, "up", D)) for _ in range(200)]; downs = [seq(session(rng, "down", D)) for _ in range(200)]
        tau = (J0) * 5 * MIN        # availability of update J0-1 (0-based index J0-1 has avail (J0)*5 min)
        for fam in ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"):
            m = V.make_model(fam, K=3, lam=39, starts=1, seed=0); m.fit(L.pad(tr, D))
            run = lambda ss: V.run_filter(fam, m, ss, D)
            rn, ru, rd = run(nulls), run(ups), run(downs)
            grid = THS["bocpd" if fam == "bocpd" else "states"]
            res = {}
            for thr in grid:
                fa = np.mean([bool(V.events_for(fam, r, q, thr)[0]) for q, r in zip(nulls, rn)])
                row = dict(fa=float(fa))
                for name, ss, rr in (("up", ups, ru), ("down", downs, rd)):
                    dl = []
                    for q, r in zip(ss, rr):
                        ev = [e for e in V.events_for(fam, r, q, thr)[0] if tau <= q["avail"][e["i_c"]] <= tau + 60 * MIN]
                        if ev: dl.append((q["avail"][ev[0]["i_c"]] - tau) / MIN)
                    row[name] = dict(hit=len(dl) / len(ss), median_delay_min=float(np.median(dl)) if dl else None)
                res[str(thr)] = row
            out[f"{fam}|D={D}"] = res
            print(fam, D, " ".join(f"{t}:{v['fa']:.2f}/{v['up']['hit']:.2f}/{v['down']['hit']:.2f}" for t, v in res.items()), flush=True)
    # verdict: some threshold with FA <= 0.05 and hit >= 0.9 in both directions
    verdict = {}
    for k, res in out.items():
        ok = [t for t, v in res.items() if v["fa"] <= 0.05 and v["up"]["hit"] >= 0.9 and v["down"]["hit"] >= 0.9]
        verdict[k] = dict(passes=bool(ok), smallest_passing_threshold=ok[0] if ok else None)
    out["verdict"] = verdict
    (L.HERE / "results" / "d3_synth_results.json").write_text(json.dumps(out, indent=1)); print(json.dumps(verdict))


if __name__ == "__main__":
    main()
