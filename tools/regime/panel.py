"""Minute-bar panel in the research layout (section4_3_1_candidates.load_development + step3.load_ohlc), built from raw 1-minute bars.

Conventions copied from the research data (checked against the RAW canonical panel by tools/acceptance_repro.py):
  * the grid is every regular-session minute of every NYSE session (390 minutes, 210 on early-close days), bar-start labels;
  * a bar is kept only if it passes the Section 3.4 validity rule: finite, positive prices, volume >= 0,
    High >= max(Open, Close), Low <= min(Open, Close); otherwise the minute counts as missing;
  * r = log(close / previous minute's close) within the session, NaN at the open or if either close is missing; valid = finite r;
  * available = bar start + 1 minute (policy P1: a bar stamped t is usable at t + 1 minute).
"""
import numpy as np

MIN = 60_000_000_000


def valid_bar(o, h, l, c, v):
    with np.errstate(invalid="ignore"):
        return (np.isfinite(o) & np.isfinite(h) & np.isfinite(l) & np.isfinite(c) & np.isfinite(v)
                & (o > 0) & (h > 0) & (l > 0) & (c > 0) & (v >= 0) & (h >= np.maximum(o, c)) & (l <= np.minimum(o, c)))


def build_panel(sessions, bars, upto_ns=None):
    """sessions: list of dict(day='YYYY-MM-DD', open_ns, close_ns) in time order (UTC ns).
    bars: dict with numpy arrays t (UTC ns, bar start), o, h, l, c, v (one symbol; any order; duplicates not allowed).
    upto_ns: keep only minutes whose bar is available (t + 1 min) at or before this time (live use); sessions entirely after it are dropped.
    Returns the panel dict (t, available, day, slot, r, valid, close, open, high, low, range, volume, first, end)."""
    ts, days, slots, firsts, ends = [], [], [], [], []; n = 0
    for s in sessions:
        m = int((s["close_ns"] - s["open_ns"]) // MIN)
        if upto_ns is not None: m = max(0, min(m, int((upto_ns - s["open_ns"]) // MIN)))
        if m <= 0: continue
        firsts.append(n); n += m; ends.append(n)
        ts.append(s["open_ns"] + MIN * np.arange(m, dtype=np.int64)); days.append(np.full(m, s["day"], dtype=object)); slots.append(np.arange(m))
    if not firsts:
        z = np.zeros(0)
        return dict(t=z.astype(np.int64), available=z.astype(np.int64), day=z.astype(str), slot=z.astype(int), r=z, valid=z.astype(bool), close=z, open=z, high=z, low=z,
                    range=z, volume=z, first=np.zeros(0, np.int64), end=np.zeros(0, np.int64))
    t = np.concatenate(ts); day = np.concatenate(days).astype(str); slot = np.concatenate(slots); first = np.array(firsts, np.int64); end = np.array(ends, np.int64)
    o, h, l, c, v = (np.full(n, np.nan) for _ in range(5))
    bt = np.asarray(bars.get("t", []), np.int64)
    if len(bt):
        if len(np.unique(bt)) != len(bt): raise ValueError("duplicate bar timestamps")
        order = np.argsort(t); pos = np.searchsorted(t[order], bt); pos = np.clip(pos, 0, n - 1); hit = t[order][pos] == bt
        j = order[pos[hit]]
        bo, bh, bl, bc, bv = (np.asarray(bars[k], float)[hit] for k in ("o", "h", "l", "c", "v"))
        ok = valid_bar(bo, bh, bl, bc, bv)
        j, bo, bh, bl, bc, bv = j[ok], bo[ok], bh[ok], bl[ok], bc[ok], bv[ok]
        o[j], h[j], l[j], c[j], v[j] = bo, bh, bl, bc, bv
    r = np.full(n, np.nan)
    prev = np.r_[np.nan, c[:-1]]; inner = slot > 0
    with np.errstate(invalid="ignore", divide="ignore"):
        ok = inner & np.isfinite(c) & np.isfinite(prev)
        r[ok] = np.log(c[ok] / prev[ok])
    with np.errstate(invalid="ignore", divide="ignore"):
        rg = np.log(h / l)
    return dict(t=t, available=t + MIN, day=day, slot=slot, r=r, valid=np.isfinite(r), close=c, open=o, high=h, low=l, range=rg, volume=v, first=first, end=end)
