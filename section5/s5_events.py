#!/usr/bin/env python3
"""Section 5.5 event logic: T_d (detection), T_c (confirmation), refractory, direction rule. Operates on one session's filtered output.
Choices made where the protocol text is silent are listed in PILOT_REPORT.md (section 'Choices')."""
import numpy as np

MIN = 60 * 10 ** 9          # nanoseconds per minute
HOLD = 3                    # consecutive real updates
WARM = 2                    # no alarms on the first 2 updates
REFRACTORY_MIN = 30


def detect_states(P, real, avail, thr, hold=HOLD, warm=WARM, refractory_min=REFRACTORY_MIN):
    """HMM/HSMM. P (n,K) filtered state probabilities, real (n,) bool, avail (n,) ns. Returns (events, dropped).
    event = dict(i_d, i_c, state). T_d = first real update (index >= warm) at which a state other than the current one has P >= thr.
    T_c = the `hold`-th consecutive real update after T_d at which that state still has argmax and P >= thr; a skip resets the count to 0;
    a different qualifying state restarts the candidate; anything else cancels it. After T_c: refractory period in which no T_d is raised."""
    n = len(real); events = []; dropped = 0
    cur = None; cand = None; ref_until = -1
    for i in range(n):
        if not real[i]:
            if cand is not None: cand["count"] = 0
            continue
        s = int(np.argmax(P[i])); p = float(P[i, s])
        if i < warm:
            cur = s; continue
        if avail[i] < ref_until:
            cur = s; cand = None; continue
        if cand is not None:
            if s == cand["state"] and p >= thr:
                cand["count"] += 1
                if cand["count"] >= hold:
                    events.append(dict(i_d=cand["i_d"], i_c=i, state=s)); cur = s; ref_until = avail[i] + refractory_min * MIN; cand = None
                continue
            cand = None   # cancelled; may immediately start a new candidate below
        if cur is None: cur = s
        if s != cur and p >= thr:
            cand = dict(state=s, i_d=i, count=0)
        elif p >= thr:
            cur = s
    if cand is not None: dropped += 1
    return events, dropped


def detect_bocpd(pcp, real, avail, thr, hold=HOLD, warm=WARM, refractory_min=REFRACTORY_MIN, pers=None, pers_thr=None):
    """BOCPD. pcp (n,) = P(changepoint within 3 updates). Alarm = rising edge of pcp >= thr at a real update with index >= warm (the previous real
    update must be below thr; updates before `warm` count as below). T_d = alarm. T_c = the `hold`-th consecutive real update after T_d with no new
    alarm; a skip resets the count to 0; a new alarm restarts the candidate.
    Optional persistence rule (proposed fix, off by default): at the would-be T_c the run-length posterior must still be short,
    pers[i] = P(run length <= hold + 2) >= pers_thr (default thr); otherwise the candidate is cancelled."""
    n = len(real); events = []; dropped = 0; cand = None; ref_until = -1; prev_below = True
    for i in range(n):
        if not real[i]:
            if cand is not None: cand["count"] = 0
            continue
        above = bool(pcp[i] >= thr)
        alarm = above and prev_below and i >= warm
        prev_below = not above
        if avail[i] < ref_until:
            cand = None; continue
        if cand is not None:
            if alarm:
                cand = dict(i_d=i, count=0)
            else:
                cand["count"] += 1
                if cand["count"] >= hold:
                    if pers is not None and not pers[i] >= (thr if pers_thr is None else pers_thr): cand = None
                    else: events.append(dict(i_d=cand["i_d"], i_c=i, state=-1)); ref_until = avail[i] + refractory_min * MIN; cand = None
            continue
        if alarm: cand = dict(i_d=i, count=0)
    if cand is not None: dropped += 1
    return events, dropped


def direction(r1, slots, i_d, i_c, min_pre=30):
    """Direction rule at T_c. r1: the session's 1-min returns (NaN invalid) by slot. Bars available in (T_d, T_c] have slots slot_d+1 .. slot_c;
    the reference is the 60 one-minute bars ending at the bar of T_d. Ratio of mean squared returns; > 1 = calm-to-stressed. None if fewer than min_pre reference bars."""
    sd, sc = int(slots[i_d]), int(slots[i_c])
    inn = r1[sd + 1:sc + 1]; pre = r1[max(0, sd - 59):sd + 1]
    inn, pre = inn[np.isfinite(inn)], pre[np.isfinite(pre)]
    if len(inn) == 0 or len(pre) < min_pre or (pre ** 2).mean() == 0: return None, None
    ratio = float((inn ** 2).mean() / (pre ** 2).mean())
    return ("calm_to_stressed" if ratio > 1 else "stressed_to_calm"), ratio
