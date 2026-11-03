#!/usr/bin/env python3
"""Protocol 5.9 and 5.11: fold-level inference for H1 (paired block bootstrap over consecutive folds, block 3; Wilcoxon; sign consistency), intersection-union per family,
Holm and Benjamini-Hochberg, minimum detectable effect by simulation. Inputs are per-fold paired effects (positive = features better than the baseline). No data access."""
import numpy as np
from scipy import stats

BLOCK = 3


def block_bootstrap_p(x, block=BLOCK, nboot=10000, rng=None):
    """One-sided p for H0: mean(x) <= 0. Moving-block bootstrap (non-circular blocks of consecutive folds) of the centred fold effects; p = share of resampled means >= the
    observed mean, with the add-one correction."""
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    if n < 2: return float("nan")
    rng = rng or np.random.default_rng(0); b = max(1, min(block, n)); starts = np.arange(n - b + 1); nb = int(np.ceil(n / b)); xc = x - x.mean(); obs = x.mean()
    idx = (rng.choice(starts, (nboot, nb))[:, :, None] + np.arange(b)).reshape(nboot, -1)[:, :n]; m = xc[idx].mean(1)
    return float((1 + (m >= obs).sum()) / (nboot + 1))


def fold_tests(x, block=BLOCK, nboot=10000, seed=0):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; n = len(x)
    try: w = float(stats.wilcoxon(x, alternative="greater").pvalue) if n >= 1 and np.any(x != 0) else float("nan")
    except ValueError: w = float("nan")
    return dict(n_folds=n, mean=float(x.mean()) if n else float("nan"), p_block_bootstrap=block_bootstrap_p(x, block, nboot, np.random.default_rng(seed)), p_wilcoxon=w,
                sign_consistency=float((x > 0).mean()) if n else float("nan"))


def intersection_union(p_a, p_b):
    """IU test: the family is significant only if both components are, so its p-value is the larger one (NaN if either is missing)."""
    return float("nan") if not (np.isfinite(p_a) and np.isfinite(p_b)) else float(max(p_a, p_b))


def holm(pvals, alpha=0.05):
    """Holm step-down. pvals: dict name -> p (NaN = not evaluable: never rejected, not counted in m). Returns name -> dict(p, p_adj, reject)."""
    names = [k for k, v in pvals.items() if np.isfinite(v)]; m = len(names); order = sorted(names, key=lambda k: pvals[k]); out = {}; run = 0.0; stop = False
    for i, k in enumerate(order):
        run = max(run, min(1.0, (m - i) * pvals[k])); stop = stop or pvals[k] > alpha / (m - i); out[k] = dict(p=pvals[k], p_adj=run, reject=not stop)
    for k, v in pvals.items():
        if k not in out: out[k] = dict(p=v, p_adj=float("nan"), reject=False)
    return out


def benjamini_hochberg(pvals, q=0.05):
    names = [k for k, v in pvals.items() if np.isfinite(v)]; m = len(names); order = sorted(names, key=lambda k: pvals[k]); adj = {}; prev = 1.0
    for i in range(m - 1, -1, -1):
        k = order[i]; prev = min(prev, pvals[k] * m / (i + 1)); adj[k] = prev
    out = {k: dict(p=pvals[k], q_adj=adj[k], reject=adj[k] <= q) for k in names}
    for k, v in pvals.items():
        if k not in out: out[k] = dict(p=v, q_adj=float("nan"), reject=False)
    return out


def mde(sd, n_folds, alpha=0.05, power=0.8, nsim=400, nboot=500, block=BLOCK, grid=None, seed=0):
    """Minimum detectable mean effect: the smallest mean shift (grid in units of sd) at which the block-bootstrap test rejects at level alpha in at least `power` of simulated
    normal fold-effect samples (n_folds folds, standard deviation sd)."""
    rng = np.random.default_rng(seed); grid = grid or [round(g, 2) for g in np.arange(0.1, 2.01, 0.1)]
    for g in grid:
        rej = sum(block_bootstrap_p(rng.normal(g * sd, sd, n_folds), block, nboot, rng) <= alpha for _ in range(nsim))
        if rej / nsim >= power: return dict(mde_in_sd=g, mde=g * sd, power=rej / nsim)
    return dict(mde_in_sd=None, mde=None, power=None)
