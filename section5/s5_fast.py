#!/usr/bin/env python3
"""Faster, equivalent splice features (features of the spliced session computed on that session alone; relative_volume20 and __sadj baselines
patched in from A's 20 previous sessions), causal deseasonalisation of the 5-min return, and a process pool for splices.
Equivalence with s5_eval.splice_rows (21-session recomputation) is checked in s5_fixes.py (rtol 1e-9)."""
import numpy as np
import s5_lib as L
import s5_eval as V

_G = {}


def bases_for(cols):
    return sorted({c[:-6] for c in cols if c.endswith("__sadj")})


def load_bases(d, era, cols):
    cf = L.CACHE / f"{era}_bases.npz"
    names = bases_for(cols)
    have = dict(np.load(cf)) if cf.exists() else {}
    need = [n for n in names if n not in have]
    if need:
        have.update(L.compute_features(d, need)); np.savez(cf, **have)
    return {n: have[n] for n in names}


def splice_rows_fast(d, bases, iA, iB, g, cols, hist=20):
    import step11_a4_rerun_4_3_4_7_8 as pstep
    import section4_3_1_candidates as c431
    p, k, tau = V.make_splice(d, iA, iB, g, hist=0)       # the spliced session alone
    want = sorted({c for c in cols if not c.endswith("__sadj") and c != "relative_volume20"} | set(bases))
    flat = L.compute_features(p, want)
    lo = max(0, iA - hist); hs = list(range(lo, iA))
    idx = np.concatenate([np.arange(d["first"][i], d["end"][i]) for i in hs]) if hs else np.zeros(0, int)
    lens = [int(d["end"][i] - d["first"][i]) for i in hs] + [int(p["end"][0] - p["first"][0])]
    first = np.r_[0, np.cumsum(lens)[:-1]].astype(np.int64); end = first + np.array(lens)
    slot = np.concatenate([d["slot"][idx], p["slot"]])
    a, b = int(first[-1]), int(end[-1])
    feats = {}
    vol = np.concatenate([d["volume"][idx], p["volume"]])
    rel, _, _ = c431.relative_volume(dict(first=first, end=end, slot=slot, volume=vol, r=vol))
    for c in cols:
        if c == "relative_volume20": feats[c] = rel[a:b]
        elif c.endswith("__sadj"):
            base = c[:-6]; x = np.concatenate([bases[base][idx], flat[base]])
            feats[c] = pstep.adjust(x, slot, first, end)[a:b]
        else: feats[c] = flat[c]
    p["features"] = feats
    row = L.session_grid(p, 0, cols)
    row["tau"] = tau; row["g"] = int(g); row["iA"] = int(iA); row["iB"] = int(iB)
    row["r1"] = np.where(p["valid"][0:b - a], p["r"][0:b - a], np.nan)
    return row


# ---------- causal deseasonalisation of the 5-minute return ----------
def ret5_matrix(d, cols):
    """sessions x 78 grid slots of the raw 5-min return."""
    S = len(d["first"]); M = np.full((S, 78), np.nan)
    for i in range(S):
        x = L.session_grid(d, i, [])["X"][:, 0]; M[i, :len(x)] = x
    return M


def ret5_scale(M, i, window=20, min_count=10):
    """Per grid slot: median of |ret5| over the previous `window` sessions (>= min_count finite), NaN otherwise or if <= 0. Past sessions only."""
    prev = np.abs(M[max(0, i - window):i]); n = np.isfinite(prev).sum(0)
    med = np.full(M.shape[1], np.nan); good = n >= min_count
    if good.any(): med[good] = np.nanmedian(prev[:, good], axis=0)
    med[~(med > 0)] = np.nan
    return med


def deseason(X, scale):
    """Replace column 0 (ret5) by ret5 / slot scale (grid slot k = row index)."""
    X = X.copy(); X[:, 0] = X[:, 0] / scale[:len(X)]
    return X


# ---------- process pool ----------
def _init(era, cols):
    d = L.load_era(era, cols); _G["d"] = d; _G["cols"] = cols; _G["bases"] = load_bases(d, era, cols)


def _work(sp):
    return splice_rows_fast(_G["d"], _G["bases"], sp["iA"], sp["iB"], sp["g"], _G["cols"])


def splice_batch(specs, era, cols, workers):
    if workers <= 1:
        _init(era, cols); return [_work(s) for s in specs]
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers, initializer=_init, initargs=(era, cols)) as pool:
        return pool.map(_work, specs, chunksize=max(1, len(specs) // (workers * 4)))
