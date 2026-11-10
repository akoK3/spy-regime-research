#!/usr/bin/env python3
"""Section 6 library (AMENDMENT_A28). Pure functions; no data is read here. Outside the Section 5 code-version closure (A28 rule 6f): nothing in s5_lib, s5_run, s5_backend
or any other closure module is imported or changed.
Clock (A28 1c): times are minutes after 09:30 at which a value is AVAILABLE. A one-minute bar with minute_index_in_session i (stamped 09:30 + i) is available at i + 1;
the panel's return at index i is the return into bar i. "Returns available at t" = indices i with i + 1 <= t. A session has 390 indices (0..389; index 0 has no return).
Cold audit 2 fixes, in this file: finding 12 (bootstrap blocks never cross the era boundary: week_block_bootstrap resamples calendar weeks within each era separately) and
finding 14 (caches keyed by column name, feature-code hash and panel hash: Cache)."""
import json, hashlib, datetime
from pathlib import Path
import numpy as np

N_MIN = 390; STEP = 5; SLOT_MIN = 30; N_PLACEBO = 20; MIN_GAP_ALARM = 60; BURN_IN = 60; CONF_PCT = 90; REAL_PCT = 80; PRIOR_N = 20; REST_MIN = 30; NBOOT = 9999


# ---------- finding 14: versioned cache
class Cache:
    """Key = sha256(column name | feature-code hash | panel hash): a change of the code that computes a column or of the panel it reads gives a new key (never a stale hit)."""
    def __init__(self, folder): self.dir = Path(folder); self.dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(column, code_sha, panel_sha): return hashlib.sha256(f"{column}|{code_sha}|{panel_sha}".encode()).hexdigest()

    def get(self, column, code_sha, panel_sha):
        p = self.dir / f"{self.key(column, code_sha, panel_sha)}.npz"
        if not p.exists(): return None
        z = np.load(p, allow_pickle=False)
        if str(z["column"]) != column or str(z["code_sha"]) != code_sha or str(z["panel_sha"]) != panel_sha: return None
        return z["values"]

    def put(self, column, code_sha, panel_sha, values):
        p = self.dir / f"{self.key(column, code_sha, panel_sha)}.npz"; tmp = p.with_name(p.stem + ".tmp.npz")
        np.savez(tmp, values=np.asarray(values), column=column, code_sha=code_sha, panel_sha=panel_sha); tmp.replace(p); return p


# ---------- finding 12: week-block bootstrap within era
def week_of(day): y, w, _ = datetime.date.fromisoformat(day).isocalendar(); return f"{y}-W{w:02d}"


def week_blocks(days, eras):
    """{era: [array of row indices of each calendar week]}; a block never holds rows of two eras."""
    out = {}
    for i, (d, e) in enumerate(zip(days, eras)): out.setdefault(e, {}).setdefault(week_of(d), []).append(i)
    return {e: [np.array(v) for _, v in sorted(w.items())] for e, w in out.items()}


def week_block_bootstrap(stat_fn, days, eras, nboot=NBOOT, seed=0):
    """Centred one-sided bootstrap p for H0: statistic <= 0 (add-one): p = (1 + #{T*_b - T >= T}) / (B + 1). Each resample draws, within each era separately, as many
    calendar weeks as that era has, with replacement; stat_fn(row_index_array) -> float (NaN resamples count as not exceeding). Returns (T, p, n_valid)."""
    blocks = week_blocks(days, eras); t = float(stat_fn(np.arange(len(days))))
    if not np.isfinite(t): return t, np.nan, 0
    rng = np.random.default_rng(seed); exceed = 0; nv = 0
    for _ in range(nboot):
        idx = np.concatenate([np.concatenate([bl[j] for j in rng.integers(0, len(bl), len(bl))]) for e, bl in sorted(blocks.items())])
        s = stat_fn(idx)
        if np.isfinite(s): nv += 1; exceed += (s - t) >= t
    return t, (1 + exceed) / (nboot + 1), nv


# ---------- realised volatility on the availability clock
def rv(ret, lo, hi):
    """Sum of squared returns available in (lo, hi] (indices i with lo < i + 1 <= hi), NaN-skipping; (rv, n_used)."""
    a = max(int(lo), 0); b = min(int(hi), N_MIN); seg = ret[a:b] if b > a else ret[:0]; ok = np.isfinite(seg); return float(np.sum(seg[ok] ** 2)), int(ok.sum())


def cumret(ret, lo, hi):
    a = max(int(lo), 0); b = min(int(hi), N_MIN); seg = ret[a:b] if b > a else ret[:0]; ok = np.isfinite(seg); return float(np.sum(seg[ok])), int(ok.sum())


def safe_log(x, floor=1e-12): return float(np.log(x)) if np.isfinite(x) and x > floor else np.nan


# ---------- deseasonalised SPY RV and the real-break label (A28 4d)
def deseasonalised_rv(R):
    """R: (n_sessions, 390) one-minute returns of consecutive sessions. Session value = mean over its minutes of r^2 / (causal median of r^2 at that minute over the
    previous 20 sessions) x 390; minutes with an undefined median (fewer than 20 previous sessions or all-NaN) are left out. NaN when no minute is usable."""
    R2 = R ** 2; n = len(R); out = np.full(n, np.nan)
    for s in range(PRIOR_N, n):
        med = np.nanmedian(R2[s - PRIOR_N:s], axis=0) if np.isfinite(R2[s - PRIOR_N:s]).any() else np.full(N_MIN, np.nan)
        ok = np.isfinite(R2[s]) & np.isfinite(med) & (med > 0)
        if ok.any(): out[s] = float(np.mean(R2[s][ok] / med[ok]) * N_MIN)
    return out


def real_label(drv, s, pct=REAL_PCT, horizon=1):
    """1 if the mean deseasonalised RV of sessions s+1..s+horizon exceeds the pct-th percentile of the 20 sessions before the labelled session (s-19..s, the break
    session included: all known at the break session's close); NaN if any of them is missing."""
    if s - PRIOR_N + 1 < 0 or s + horizon >= len(drv): return np.nan
    prior = drv[s - PRIOR_N + 1:s + 1]; nxt = drv[s + 1:s + 1 + horizon]
    if not (np.isfinite(prior).all() and np.isfinite(nxt).all()): return np.nan
    return float(np.mean(nxt) > np.percentile(prior, pct))


# ---------- placebos (A28 1d)
def slot_of(t): return int((t - 1) // SLOT_MIN)


def decile_cuts(values):
    v = np.asarray(values, float); v = v[np.isfinite(v)]; return np.percentile(v, np.arange(10, 100, 10)) if len(v) >= 10 else None


def decile(x, cuts): return None if cuts is None or not np.isfinite(x) else int(np.searchsorted(cuts, x, side="right"))


def draw_placebos(unit, cand, alarms_by_day, n=N_PLACEBO, seed=0):
    """unit: dict(day_idx, era, S, gap, vol) for one break or run; cand: dict of arrays (day_idx, era, S, vol) of every candidate time (SPY update times of sessions with
    detector output). Eligible: same era, session strictly before the unit's session, same 30-minute slot of S, same SPY prior-hour-RV decile with cut points from the
    candidates of sessions before the unit's session only, S + gap within the session, and more than 60 minutes from every confirmed alarm (T_c) of that session.
    Returns up to n candidate indices (fewer only if fewer are eligible), drawn without replacement with a seed fixed per unit."""
    before = (cand["era"] == unit["era"]) & (cand["day_idx"] < unit["day_idx"])
    cuts = decile_cuts(cand["vol"][before]); dz = decile(unit["vol"], cuts)
    if dz is None: return np.array([], int)
    cd = np.searchsorted(cuts, cand["vol"], side="right")
    ok = before & ((cand["S"] - 1) // SLOT_MIN == slot_of(unit["S"])) & (cd == dz) & np.isfinite(cand["vol"]) & (cand["S"] + unit["gap"] <= N_MIN)
    idx = np.flatnonzero(ok)
    if len(idx) == 0: return idx
    far = np.array([all(abs(cand["S"][i] - a) > MIN_GAP_ALARM and abs(cand["S"][i] + unit["gap"] - a) > MIN_GAP_ALARM for a in alarms_by_day.get(int(cand["day_idx"][i]), ())) for i in idx], bool)
    idx = idx[far]; rng = np.random.default_rng(seed)
    return np.sort(rng.choice(idx, size=min(n, len(idx)), replace=False)) if len(idx) else idx


# ---------- confirmation score (A28 4a)
def window(point, S, t):
    """At S: the 15 minutes before S; at T = 0 and T + 15: from S to t."""
    return (S - 15, S) if point == "S" else (S, t)


def confirmation_score(unit_abs, placebo_abs, pct=CONF_PCT):
    """unit_abs: {asset: |own return| of the unit (NaN = asset not available)}; placebo_abs: {asset: array over the unit's placebos}. Share of AVAILABLE assets (no minimum)
    whose value exceeds the pct-th percentile of its placebos; NaN when no asset is available or no placebo value exists."""
    k = n = 0
    for a, x in unit_abs.items():
        pv = np.asarray(placebo_abs.get(a, []), float); pv = pv[np.isfinite(pv)]
        if not np.isfinite(x) or len(pv) == 0: continue
        n += 1; k += x > np.percentile(pv, pct)
    return k / n if n else np.nan


# ---------- H3 regression and H4 logistic AUC gain
def ols_gamma(y, X, b):
    """OLS of y on [1, X, b]; returns the coefficient of b (NaN if singular or degenerate)."""
    Z = np.column_stack([np.ones(len(y)), X, b]); ok = np.isfinite(Z).all(1) & np.isfinite(y)
    if ok.sum() < Z.shape[1] + 2 or np.ptp(b[ok]) == 0: return np.nan
    coef, *_ = np.linalg.lstsq(Z[ok], y[ok], rcond=None); return float(coef[-1])


def auc(score, label):
    s = np.asarray(score, float); l = np.asarray(label, float); ok = np.isfinite(s) & np.isfinite(l); s, l = s[ok], l[ok]; n1 = (l == 1).sum(); n0 = (l == 0).sum()
    if n1 == 0 or n0 == 0: return np.nan
    from scipy.stats import rankdata
    r = rankdata(s); return float((r[l == 1].sum() - n1 * (n1 + 1) / 2) / (n1 * n0))


def logit_fit(X, y, ridge=1e-6, iters=50):
    Z = np.column_stack([np.ones(len(y)), X]); w = np.zeros(Z.shape[1])
    for _ in range(iters):
        p = 1 / (1 + np.exp(-np.clip(Z @ w, -30, 30))); W = p * (1 - p); H = Z.T @ (Z * W[:, None]) + ridge * np.eye(Z.shape[1]); g = Z.T @ (y - p) - ridge * w
        step = np.linalg.solve(H, g); w += step
        if np.max(np.abs(step)) < 1e-8: break
    return w, Z @ w


def auc_gain(X, c, y):
    """In-sample AUC of the logistic model on [X, c] minus that on X (A28 4e; descriptive only under A29 1e)."""
    ok = np.isfinite(X).all(1) & np.isfinite(c) & np.isfinite(y)
    if ok.sum() < 10 or len(np.unique(y[ok])) < 2: return np.nan
    _, e0 = logit_fit(X[ok], y[ok]); _, e1 = logit_fit(np.column_stack([X[ok], c[ok]]), y[ok]); return auc(e1, y[ok]) - auc(e0, y[ok])


K_FOLDS = 5


def cv_folds(days, eras, k=K_FOLDS):
    """A29 1a: within each era, the calendar weeks holding rows, in date order, split into k contiguous blocks of as equal a number of weeks as possible; fold j = block j
    of every era. Returns an int array (fold of each row); every row of a week gets the same fold."""
    f = np.empty(len(days), int); wk = [week_of(d) for d in days]
    for e in sorted(set(eras)):
        weeks = sorted({w for w, ee in zip(wk, eras) if ee == e}); m = {w: int(j * k // len(weeks)) for j, w in enumerate(weeks)}
        for i, (w, ee) in enumerate(zip(wk, eras)):
            if ee == e: f[i] = m[w]
    return f


def auc_gain_cv(X, c, y, folds, k=K_FOLDS, parts=False):
    """A29 1b-1c: both logistic models fitted on the other folds and evaluated on each fold; AUC of the pooled out-of-fold linear predictors with c minus without c.
    NaN when a fold is empty or a training set holds one label class only. parts=True: (gain, OOF AUC with c, OOF AUC without c), fold means (A29 1g)."""
    X = np.asarray(X, float); c = np.asarray(c, float); y = np.asarray(y, float); folds = np.asarray(folds)
    ok = np.isfinite(X).all(1) & np.isfinite(c) & np.isfinite(y); X, c, y, folds = X[ok], c[ok], y[ok], folds[ok]
    nan = (np.nan, np.nan, np.nan) if parts else np.nan
    if len(y) < 10 or len(np.unique(y)) < 2: return nan
    Xc = np.column_stack([X, c]); a1s, a0s = [], []; e0 = np.empty(len(y)); e1 = np.empty(len(y)); d, wt = [], []
    for j in range(k):
        te = folds == j; tr = ~te
        if not te.any() or len(np.unique(y[tr])) < 2: return nan
        w0, _ = logit_fit(X[tr], y[tr]); w1, _ = logit_fit(Xc[tr], y[tr])
        e0[te] = np.column_stack([np.ones(te.sum()), X[te]]) @ w0; e1[te] = np.column_stack([np.ones(te.sum()), Xc[te]]) @ w1
        if POOL_OOF: continue
        a1, a0 = auc(e1[te], y[te]), auc(e0[te], y[te])
        if np.isfinite(a1) and np.isfinite(a0): d.append(a1 - a0); a1s.append(a1); a0s.append(a0); wt.append(te.sum())
    if POOL_OOF: g = auc(e1, y) - auc(e0, y); return (g, auc(e1, y), auc(e0, y)) if parts else g
    if not d: return nan
    g = float(np.average(d, weights=wt)); return (g, float(np.average(a1s, weights=wt)), float(np.average(a0s, weights=wt))) if parts else g


POOL_OOF = False      # A29 1c: AUC within each fold, mean weighted by units per fold. True = the first draft (pooled out-of-fold predictors), kept for the record


# ---------- multiplicity
def holm(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p); adj = np.empty(m); run = 0.0
    for k, i in enumerate(o): run = max(run, min(1.0, (m - k) * p[i])); adj[i] = run
    return adj


def bh(p):
    p = np.asarray(p, float); m = len(p); o = np.argsort(p)[::-1]; adj = np.empty(m); run = 1.0
    for k, i in enumerate(o): run = min(run, p[i] * m / (m - k)); adj[i] = run
    return adj
