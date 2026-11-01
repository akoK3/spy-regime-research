#!/usr/bin/env python3
"""Section 5.6 synthetic splices, thresholds, QLIKE and Diebold-Mariano. Everything here uses a fold's inner-train-fitted objects and the fold's own segments."""
import time
import numpy as np
from scipy import stats

import s5_lib as L
import s5_models as M
import s5_events as E

TAU_SLOTS = np.arange(94, 300, 5)          # grid bars stamped 11:04 ... 14:29 (availability 11:05 ... 14:30)
HIT_WINDOW_MIN = 60
STATE_THR = [round(x, 2) for x in list(np.arange(0.50, 0.96, 0.05))] + [0.99]
BOCPD_THR = [round(x, 2) for x in list(np.arange(0.05, 0.96, 0.05))] + [0.99]
EXTRA_THR = [0.995, 0.999, 0.9995, 0.9999]      # proposed extension (A6 draft)


def thr_grid(family, extended=False):
    g = BOCPD_THR if family == "bocpd" else STATE_THR
    return g + EXTRA_THR if extended else g


def make_model(family, K=3, lam=39, starts=1, seed=0, Dmax=78):
    if family == "gaussian_hmm": return M.GaussianHMM(K, starts, seed=seed)
    if family == "student_t_hmm": return M.StudentTHMM(K, starts, seed=seed)
    if family == "hsmm": return M.HSMM(K, starts, seed=seed, Dmax=Dmax)
    if family == "bocpd": return M.BOCPD(lam)
    raise ValueError(family)


# ---------- splices ----------
def make_splice(d, iA, iB, g, hist=20):
    """Mini panel = hist native sessions before A, then the spliced session: A's bars up to and including slot g, B's bars after, B's prices
    multiplied by close_A[g] / close_B[g] so the price path is continuous at tau. Clock times (t, available, day, slot) are A's. Returns the panel, the
    index of the spliced session and tau = availability time (ns) of A's bar g."""
    lo = max(0, iA - hist)
    sess = list(range(lo, iA)) + [iA]
    p = L.sub_panel(d, sess)
    a, b = int(p["first"][-1]), int(p["end"][-1]); m = b - a
    ib = int(d["first"][iB]); assert int(d["end"][iB] - d["first"][iB]) == m, "A and B need the same number of bars"
    assert g + 1 < m
    cA, cB = d["close"][int(d["first"][iA]) + g], d["close"][ib + g]
    assert np.isfinite(cA) and np.isfinite(cB) and cA > 0 and cB > 0
    sc = cA / cB
    j = np.arange(g + 1, m)
    for k in ("open", "high", "low", "close"): p[k][a + j] = d[k][ib + j] * sc
    p["volume"][a + j] = d["volume"][ib + j]; p["range"][a + j] = d["range"][ib + j]
    p["r"][a + j] = d["r"][ib + j]
    p["valid"][a + j] = d["valid"][ib + j]; p["valid"][a + g + 1] = d["valid"][ib + g + 1] and d["valid"][ib + g]
    p["r"][a + g + 1] = d["r"][ib + g + 1] if p["valid"][a + g + 1] else np.nan
    tau = int(p["available"][a + g])
    return p, len(sess) - 1, tau


def splice_rows(d, iA, iB, g, cols, hist=20):
    """Features recomputed from the spliced series only; returns the raw decision-grid row of the spliced session."""
    p, k, tau = make_splice(d, iA, iB, g, hist)
    p["features"] = L.compute_features(p, cols_to_names(cols))
    row = L.session_grid(p, k, cols)
    row["tau"] = tau; row["g"] = int(g)
    a, b = int(p["first"][k]), int(p["end"][k])
    row["r1"] = np.where(p["valid"][a:b], p["r"][a:b], np.nan)
    return row


def cols_to_names(cols):
    return list(cols)


def session_stats(d, sess):
    rv, vol, n = [], [], []
    for i in sess:
        a, b = int(d["first"][i]), int(d["end"][i]); r = np.where(d["valid"][a:b], d["r"][a:b], np.nan)
        rv.append(np.nansum(r ** 2)); vol.append(np.nansum(d["volume"][a:b])); n.append(b - a)
    return np.array(rv), np.array(vol), np.array(n)


def tercile(x):
    q = np.quantile(x, [1 / 3, 2 / 3]); return np.digitize(x, q)


def sample_pairs(d, sess, n_break, n_null, rng, full=390):
    """Break pairs (half calm-to-stressed, half stressed-to-calm; calm/stressed = lowest/highest volatility tercile of the segment) and null pairs
    (A, B different sessions in the same volatility AND volume tercile). Full-length sessions only. tau slot drawn from TAU_SLOTS."""
    def drawg(A, B):
        """tau slot with finite prices at bars g and g+1 in both sessions (a splice needs a price to rescale at g)."""
        for _ in range(200):
            g = int(rng.choice(TAU_SLOTS)); fa, fb = int(d["first"][A]), int(d["first"][B])
            if np.isfinite(d["close"][[fa + g, fb + g, fb + g + 1]]).all() and d["valid"][fb + g + 1] and d["valid"][fb + g]: return g
        return None
    sess = np.asarray(sess); rv, vol, n = session_stats(d, sess)
    fin = np.array([np.isfinite(d["close"][int(d["first"][i]):int(d["end"][i])]).mean() for i in sess])
    ok = (n == full) & (fin >= 0.98); s, rv, vol = sess[ok], rv[ok], vol[ok]   # full-length sessions with at least 98% finite closes
    tv, tq = tercile(rv), tercile(vol)
    calm, stressed = s[tv == 0], s[tv == 2]
    breaks = []
    for k in range(n_break):
        up = k % 2 == 0
        for _ in range(100):
            A = rng.choice(calm if up else stressed); B = rng.choice(stressed if up else calm); g = drawg(A, B)
            if g is not None: break
        else: raise RuntimeError("no usable break pair")
        breaks.append(dict(iA=int(A), iB=int(B), g=g, kind="calm_to_stressed" if up else "stressed_to_calm"))
    cells = [np.where((tv == a) & (tq == b))[0] for a in range(3) for b in range(3)]
    cells = [c for c in cells if len(c) >= 2]
    nulls = []
    for k in range(n_null):
        for _ in range(100):
            c = cells[int(rng.integers(len(cells)))]; A, B = rng.choice(c, 2, replace=False); g = drawg(s[A], s[B])
            if g is not None: break
        else: raise RuntimeError("no usable null pair")
        nulls.append(dict(iA=int(s[A]), iB=int(s[B]), g=g, kind="null"))
    return breaks, nulls


# ---------- model outputs ----------
def run_filter(family, model, seqs, D):
    """Causal filtered output per sequence: states -> (n,K) probabilities; bocpd -> dict(pcp, var)."""
    batch = L.pad(seqs, D)
    out = model.filter(batch)
    res = []
    for k, q in enumerate(seqs):
        n = q["n"]
        res.append(dict(pcp=out[k, :n, 0], var=out[k, :n, 2], pers=out[k, :n, 3]) if family == "bocpd" else dict(P=out[k, :n]))
    return res


def events_for(family, res, seq, thr, persistence=False):
    if seq["n"] == 0: return [], 0
    if family == "bocpd": return E.detect_bocpd(res["pcp"], seq["real"], seq["avail"], thr, pers=res["pers"] if persistence else None)
    return E.detect_states(res["P"], seq["real"], seq["avail"], thr)


def score_splices(family, res_list, seqs, taus, is_break, grid, persistence=False):
    """For each threshold: false-alarm rate (null) or hit rate / delays in minutes (break)."""
    out = {}
    for thr in grid:
        fa, hits, delays, dropped = 0, 0, [], 0
        for res, q, tau in zip(res_list, seqs, taus if taus is not None else [None] * len(seqs)):
            ev, dr = events_for(family, res, q, thr, persistence); dropped += dr
            if is_break:
                good = [e for e in ev if tau <= q["avail"][e["i_c"]] <= tau + HIT_WINDOW_MIN * E.MIN]
                if good: hits += 1; delays.append((q["avail"][good[0]["i_c"]] - tau) / E.MIN)
            else:
                fa += int(len(ev) > 0)
        n = len(seqs)
        out[thr] = dict(n=n, fa_rate=fa / n, hit_rate=hits / n, delays=delays, dropped=dropped)
    return out


def choose_threshold(null_scores, grid, max_fa=1 / 20):
    """Smallest threshold with at most 1 false alarm per 20 null sessions on validation; None if no grid value qualifies."""
    for thr in grid:
        if null_scores[thr]["fa_rate"] <= max_fa: return thr
    return None


# ---------- QLIKE ----------
def qlike_loss(tgt, pred):
    ratio = tgt / pred
    return ratio - np.log(ratio) - 1.0


def state_values(family, res_list, seqs):
    """Regime-conditional values fitted on inner-train outputs: states -> posterior-weighted mean future 60-min variance per state;
    bocpd -> two regimes weighted by P(cp within 3) and 1 - P(cp within 3)."""
    tg = [q["tgt"] for q in seqs]
    if family == "bocpd":
        w1 = np.concatenate([r["pcp"] for r in res_list]); t = np.concatenate(tg); ok = np.isfinite(t)
        w1, t = w1[ok], t[ok]
        return np.array([(w1 * t).sum() / max(w1.sum(), 1e-12), ((1 - w1) * t).sum() / max((1 - w1).sum(), 1e-12)])
    P = np.concatenate([r["P"] for r in res_list]); t = np.concatenate(tg); ok = np.isfinite(t)
    P, t = P[ok], t[ok]
    return (P * t[:, None]).sum(0) / np.maximum(P.sum(0), 1e-12)


def forecasts(family, res, values):
    if family == "bocpd": return res["pcp"] * values[0] + (1 - res["pcp"]) * values[1]
    return res["P"] @ values


def qlike_series(family, res_list, seqs, values):
    """Per-decision-bar QLIKE on bars with a target (bars at or before 15:00, 12:00 on early closes: guaranteed by the 60-bar horizon)."""
    L_, K_ = [], []
    for r, q in zip(res_list, seqs):
        if q["n"] == 0: continue
        f = forecasts(family, r, values); t = q["tgt"]; ok = np.isfinite(t) & np.isfinite(f) & (f > 0)
        L_.append(qlike_loss(t[ok], f[ok])); K_.append(q["sess"] * 1000 + q["slots"][ok])
    return (np.concatenate(L_), np.concatenate(K_)) if L_ else (np.zeros(0), np.zeros(0, int))   # loss, key = session*1000 + slot


def align(loss_a, key_a, loss_b, key_b):
    """Restrict two loss series to the decision bars both models scored (same session and slot), in time order."""
    oa, ob = np.argsort(key_a), np.argsort(key_b); ka, kb = key_a[oa], key_b[ob]
    common = np.intersect1d(ka, kb)
    return loss_a[oa][np.searchsorted(ka, common)], loss_b[ob][np.searchsorted(kb, common)], common


def diebold_mariano(loss_base, loss_feat, lag=12):
    """Newey-West HAC DM test on the loss differential base - feat (positive = feature model better); lag 12 = the 60-minute horizon in 5-minute steps."""
    d = np.asarray(loss_base) - np.asarray(loss_feat); n = len(d)
    if n < 30: return dict(n=n, mean_diff=float(d.mean()) if n else np.nan, stat=np.nan, p_one_sided=np.nan)
    dc = d - d.mean(); lrv = (dc ** 2).mean()
    for k in range(1, lag + 1): lrv += 2 * (1 - k / (lag + 1)) * (dc[k:] * dc[:-k]).mean()
    stat = d.mean() / np.sqrt(max(lrv, 1e-300) / n)
    return dict(n=n, mean_diff=float(d.mean()), stat=float(stat), p_one_sided=float(1 - stats.norm.cdf(stat)))
