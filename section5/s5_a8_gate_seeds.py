#!/usr/bin/env python3
"""A8.3: repeat the A8.2 gate (P1 inside the day-level 95% bootstrap interval of P2) over many seeds. Models fitted once per fold; fresh N1, P1, P2 per seed. Validation sessions only.
Usage: s5_a8_gate_seeds.py ERA FOLD SEED_FIRST SEED_LAST. Results appended per seed to results/a8_3_gate_<ERA><FOLD>.jsonl (resumes by skipping done seeds)."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_sweep as W, s5_a8_gate as G


def main(era, fold, s0, s1):
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True)
    out_f = L.HERE / "results" / f"a8_3_gate_{era}{fold}.jsonl"; done = {json.loads(l)["seed"] for l in out_f.read_text().splitlines()} if out_f.exists() else set()
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
    stable, _ = S.stable_days(d, seg["val"], dv); stable_arr = np.array(stable); D2._W.update(d=d, cols=cols, bases=F.load_bases(d, era, cols), dv=dv); log(f"fits done; stable validation days {len(stable)}")
    des = lambda rl: [to_des(r, r["iA"]) for r in rl]; nd = len(stable); dayidx = {int(x): k for k, x in enumerate(stable)}; cfg = [(1.0, "up", du) for du in B.DURS]
    for seed in range(s0, s1 + 1):
        if seed in done: continue
        rng = np.random.default_rng(seed); n1 = G.null_specs(d, dv, stable, rng, G.N1)
        p1 = A.build_specs(d, dv, stable, rng, 0, cfg, G.NP // len(B.DURS)); p2 = A.build_specs(d, dv, stable, np.random.default_rng(seed + 500000), 0, cfg, G.NP // len(B.DURS))
        rows1, rowsP1, rowsP2 = ([D2._work(s) for s in x] for x in (n1, p1, p2)); brng = np.random.default_rng(seed + 1); res = {}
        cl = np.array([dayidx[int(r["iA"])] for r in rowsP2])
        for (fam, sname), (m, sub) in models.items():
            D = 1 + len(sub); grid = B.MGRID if fam == "bocpd" else B.THETA
            def run_(rl):
                qs = [mk(r, sub) for r in des(rl)]; rs = V.run_filter(fam, m, qs, D); R_, real, av = W.stack(rs, qs, "rstar" if fam == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
            sw = (lambda a, b, c, t: W.sweep_map(a, b, c, grid, t)) if fam == "bocpd" else (lambda a, b, c, t: W.sweep_old_state(a, b, c, grid, t))
            R_, re_, av_, _ = run_(rows1); cnt, _ = sw(R_, re_, av_, None); xs = cnt.mean(0)
            R_, re_, av_, t_ = run_(rowsP1); _, h1 = sw(R_, re_, av_, t_)
            R_, re_, av_, t_ = run_(rowsP2); _, h2 = sw(R_, re_, av_, t_)
            pa = lambda y: A.pauc(list(zip(xs.tolist(), np.asarray(y).tolist())))
            p_1, p_2 = pa(h1.mean(0)), pa(h2.mean(0)); boot = []
            for _ in range(G.NBOOT):
                w = np.bincount(brng.integers(0, nd, nd), minlength=nd)[cl].astype(float)
                if w.sum(): boot.append(pa((w @ h2) / w.sum()))
            lo, hi = np.quantile(boot, [0.025, 0.975]); res[f"{fam}|{sname}"] = dict(p1=p_1, p2=p_2, ci=[float(lo), float(hi)], outside=bool(not (lo <= p_1 <= hi)))
        with open(out_f, "a") as f: f.write(json.dumps(dict(seed=seed, era=era, fold=fold, stable_days=nd, detectors=res), default=float) + "\n")
        log(f"seed {seed} done; outside: {[k for k, v in res.items() if v['outside']]}")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), int(sys.argv[4]))
