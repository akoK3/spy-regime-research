#!/usr/bin/env python3
"""Vectorised threshold sweeps: the alarm state machines of s5_events.detect_old_state_logodds and s5_events.detect_bocpd_map evaluated for ALL thresholds and ALL sessions
at once (loop over the updates only). Returns, per (session, threshold), the number of confirmed alarms and whether one falls in [tau, tau + window].
Equality with the loop implementations is asserted in s5_tests.py."""
import numpy as np

MIN = 60 * 10 ** 9


def stack(res_list, seqs, key):
    """Padded arrays from per-session filter outputs: values (S,T[,K]), real (S,T) (False in padding), avail (S,T) (int64)."""
    S = len(seqs); T = max(max(q["n"] for q in seqs), 1); first = np.asarray(res_list[0][key]); shp = (S, T) + first.shape[1:]
    V = np.zeros(shp); real = np.zeros((S, T), bool); avail = np.zeros((S, T), np.int64)
    for k, (q, r) in enumerate(zip(seqs, res_list)):
        n = q["n"]
        if n: V[k, :n] = r[key][:n]; real[k, :n] = q["real"][:n]; avail[k, :n] = q["avail"][:n]
    return V, real, avail


def sweep_old_state(P, real, avail, thetas, taus=None, window=60 * MIN, run=3, warm=2, refractory=30 * MIN):
    S, T, K = P.shape; G = len(thetas); th = np.asarray(thetas, float)[None, :]
    cur = np.full((S, G), -1); cnt = np.zeros((S, G), int); ref = np.full((S, G), -1, np.int64)
    counts = np.zeros((S, G), int); hit = np.zeros((S, G), bool); argm = P.argmax(2); sidx = np.arange(S)[:, None]; kk = np.arange(K)[None, None, :]
    tau = None if taus is None else np.asarray(taus, np.int64)[:, None]
    for i in range(T):
        r = real[:, i][:, None]; a = avail[:, i][:, None]
        setcur = r & ((i < warm) | (a < ref) | (cur < 0)); cur = np.where(setcur, argm[:, i][:, None], cur)
        cnt = np.where(setcur | ~r, 0, cnt); active = r & ~setcur
        if not active.any(): continue
        curc = np.maximum(cur, 0); Pi = P[:, i, :]; po = Pi[sidx, curc]
        so = (Pi[:, None, :] * (kk != curc[:, :, None])).sum(2)
        with np.errstate(divide="ignore"):
            lo = np.where(po <= 0, np.inf, np.where(so <= 0, -np.inf, np.log(np.where(so > 0, so, 1.0)) - np.log(np.where(po > 0, po, 1.0))))
        cond = active & (lo > th); cnt = np.where(active, np.where(cond, cnt + 1, 0), cnt); fire = active & (cnt >= run)
        counts += fire
        if tau is not None: hit |= fire & (a >= tau) & (a <= tau + window)
        cur = np.where(fire, argm[:, i][:, None], cur); ref = np.where(fire, a + refractory, ref); cnt = np.where(fire, 0, cnt)
    return counts, hit


def sweep_map(rstar, real, avail, ms, taus=None, window=60 * MIN, hold=3, warm=2, refractory=30 * MIN):
    S, T = rstar.shape; G = len(ms); m = np.asarray(ms, float)[None, :]
    cand = np.zeros((S, G), bool); low = np.zeros((S, G)); cnt = np.zeros((S, G), int); ref = np.full((S, G), -1, np.int64)
    counts = np.zeros((S, G), int); hit = np.zeros((S, G), bool); prev = np.zeros(S); has = np.zeros(S, bool)
    tau = None if taus is None else np.asarray(taus, np.int64)[:, None]
    for i in range(T):
        r = real[:, i][:, None]; a = avail[:, i][:, None]; rs = rstar[:, i][:, None]
        cnt = np.where(~r & cand, 0, cnt)
        dropped = r & has[:, None] & (i >= warm) & ((prev[:, None] - rs) >= m)
        prev = np.where(real[:, i], rstar[:, i], prev); has = has | real[:, i]
        inref = a < ref; cand = np.where(r & inref, False, cand); proc = r & ~inref
        # candidate present
        has_c = proc & cand; restart = has_c & dropped; grow = has_c & ~dropped & (rs <= low + cnt + 1); fail = has_c & ~dropped & ~grow
        cnt = np.where(restart, 0, np.where(grow, cnt + 1, cnt)); low = np.where(restart, rs, low); cand = np.where(fail, False, cand)
        fire = grow & (cnt >= hold); counts += fire
        if tau is not None: hit |= fire & (a >= tau) & (a <= tau + window)
        ref = np.where(fire, a + refractory, ref); cand = np.where(fire, False, cand)
        # no candidate: a drop starts one
        start = proc & ~has_c & dropped; cand = np.where(start, True, cand); low = np.where(start, rs, low); cnt = np.where(start, 0, cnt)
    return counts, hit
