#!/usr/bin/env python3
"""A8 item 5: H1(c), secondary. Scoring functions only (not run on real data under A8).
Times are minutes after 09:30 ET of the availability of a confirmed alarm; FOMC statement at 14:00 = minute 270; window [270, 330] (14:00-15:00 inclusive)."""
import json
import numpy as np
from scipy import stats

EVENT_MIN = 270; WINDOW_MIN = 60


def hit(alarm_minutes, event=EVENT_MIN, window=WINDOW_MIN):
    """True if any confirmed alarm has availability in [event, event + window]."""
    a = np.asarray(alarm_minutes, float)
    return bool(a.size and np.any((a >= event) & (a <= event + window)))


def assign_events(fomc_days, folds_days):
    """Each FOMC date counts once, in the earliest qualifying fold. folds_days: ordered dict fold -> set of eligible (uncontaminated, 390-bar) test dates."""
    out = {f: [] for f in folds_days}; done = set()
    for f, days in folds_days.items():
        for x in sorted(set(fomc_days) & set(days)):
            if x not in done: out[f].append(x); done.add(x)
    return out


def wilson(k, n, z=1.959964):
    if n == 0: return (float("nan"), float("nan"))
    p = k / n; den = 1 + z * z / n; c = (p + z * z / (2 * n)) / den; h = z * np.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return (float(max(0.0, c - h)), float(min(1.0, c + h)))


def paired_sign(hit_f3, hit_base):
    """Exact two-sided sign test on discordant events (f3 minus base). Returns dict."""
    a = np.asarray(hit_f3, bool); b = np.asarray(hit_base, bool); n10 = int((a & ~b).sum()); n01 = int((~a & b).sum()); nd = n10 + n01
    p = float(stats.binomtest(n10, nd, 0.5).pvalue) if nd else 1.0
    return dict(n_events=int(len(a)), f3_only=n10, base_only=n01, both=int((a & b).sum()), neither=int((~a & ~b).sum()), p_two_sided=p, diff=float(a.mean() - b.mean()) if len(a) else float("nan"))


def reference_rate(alarm_minutes_by_session, event=EVENT_MIN, window=WINDOW_MIN):
    """Share of non-FOMC test sessions with a confirmed alarm in the same clock window."""
    h = [hit(a, event, window) for a in alarm_minutes_by_session]; return float(np.mean(h)) if h else float("nan")


def summarize(family, hits_f3, hits_base, ref_f3, ref_base):
    return dict(family=family, f3=dict(hit_rate=float(np.mean(hits_f3)) if len(hits_f3) else float("nan"), wilson95=wilson(int(np.sum(hits_f3)), len(hits_f3)), reference_alarm_rate=ref_f3),
                base=dict(hit_rate=float(np.mean(hits_base)) if len(hits_base) else float("nan"), wilson95=wilson(int(np.sum(hits_base)), len(hits_base)), reference_alarm_rate=ref_base),
                paired=paired_sign(hits_f3, hits_base), multiplicity="none (secondary, outside the Holm families of A6 item 4)")
