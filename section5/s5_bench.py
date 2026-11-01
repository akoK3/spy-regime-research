#!/usr/bin/env python3
"""Benchmarks (RAW fold 3, TRAIN data only): fast vs slow splice features (equivalence + time), process-pool speedup for splices and for model fits."""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V, s5_fast as F, s5_pilot as P

_B = {}


def _initfit():
    primary, _, _ = L.pools(); d = L.load_era("RAW", primary + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    rows = [L.session_grid(d, i, primary) for i in seg["train"]]; names = [L.RET_NAME] + primary
    prep = L.Prep().fit(np.vstack([r["X"] for r in rows]), names)
    idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(n) for n in P.FIXED3]
    seqs = [L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx])) for r in rows]
    _B["b"] = L.pad(seqs, len(idx))


def _fit(job):
    fam, seed = job; t = time.perf_counter(); V.make_model(fam, K=3, starts=1, seed=seed).fit(_B["b"]); return time.perf_counter() - t


def main():
    import multiprocessing as mp
    primary, _, _ = L.pools(); d = L.load_era("RAW", primary + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    bases = F.load_bases(d, "RAW", primary)
    rng = np.random.default_rng(5); br, nu = V.sample_pairs(d, seg["val"], 40, 40, rng); specs = br + nu
    out = {}
    # equivalence + serial timing (6 splices)
    eq = []; ts, tf = [], []
    for sp in specs[:6]:
        t = time.perf_counter(); slow = V.splice_rows(d, sp["iA"], sp["iB"], sp["g"], primary); ts.append(time.perf_counter() - t)
        t = time.perf_counter(); fast = F.splice_rows_fast(d, bases, sp["iA"], sp["iB"], sp["g"], primary); tf.append(time.perf_counter() - t)
        eq.append(bool(np.allclose(slow["X"], fast["X"], rtol=1e-9, atol=0, equal_nan=True) and np.array_equal(slow["avail"], fast["avail"]) and slow["tau"] == fast["tau"]
                       and np.array_equal(slow["tgt"], fast["tgt"], equal_nan=True)))
    out["equivalence_fast_vs_slow"] = dict(splices=len(eq), all_equal=all(eq), slow_s=float(np.mean(ts)), fast_s=float(np.mean(tf)))
    print(out["equivalence_fast_vs_slow"], flush=True)
    # pool speedup, splices (fast path)
    sp_t = {}
    for w in (1, 4):
        t = time.perf_counter(); rows = F.splice_batch(specs[:64], "RAW", primary, w); sp_t[w] = time.perf_counter() - t; print("splice workers", w, sp_t[w], flush=True)
    out["splice_pool_seconds_for_64"] = sp_t
    # pool speedup, fits (HSMM, 16 jobs)
    jobs = [("hsmm", s) for s in range(16)]; ft = {}
    for w in (1, 4):
        t = time.perf_counter()
        if w == 1:
            _initfit(); [_fit(j) for j in jobs]
        else:
            with mp.get_context("spawn").Pool(w, initializer=_initfit) as pool: pool.map(_fit, jobs, chunksize=1)
        ft[w] = time.perf_counter() - t; print("fit workers", w, ft[w], flush=True)
    out["fit_pool_seconds_for_16_hsmm_incl_init"] = ft
    import os; out["logical_cores"] = os.cpu_count()
    (L.HERE / "results" / "bench_results.json").write_text(json.dumps(out, indent=1))


if __name__ == "__main__":
    main()
