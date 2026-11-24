"""Frozen detector pipeline: panel -> rv10_partial90__sadj -> 5-minute decision grid -> filtered HMM probabilities -> alarms.

Every numerical step is a research function from the verified vendored copies (regime.frozen_loader.modules()):
  section4_3_1_candidates.construct      rv10_partial90 (1-min returns, 10-minute window, at least 9 of 10 returns)
  step11.adjust                          __sadj: / median of the same minute slot over the previous 20 sessions (>= 10 finite)
  s5_lib.session_grid / build_sequence   grid slots 4, 9, ... (5 min), availability = bar start + 1 min (policy P1)
  s5_fast.ret5_scale / deseason          5-minute return / median |ret5| of the same grid slot over the previous 20 sessions
  frozen Prep.transform                  log, winsorize, z-score with the TRAIN parameters stored in the model file
  s5_models.GaussianHMM.filter           causal filtered state probabilities
  s5_events.detect_old_state_logodds     alarm rule: log-odds > 16.98211669921875 on 3 consecutive real updates; first 2
                                         updates never alarm; 30-minute refractory; a run open at the close is dropped
  s5_break_export.runs_old_state         the same loop, also listing runs that fizzled (display / acceptance only)
This module only wires them together, as section5/s5_eval513.py does on the evaluation path.
"""
import numpy as np

from . import frozen_loader as FL

COL = "rv10_partial90__sadj"
BASELINE_SESSIONS = 20          # causal baselines look back exactly 20 sessions (step11.WINDOW, s5_fast.ret5_scale window)


def compute_sadj(d):
    """s5_lib.compute_features(d, ['rv10_partial90__sadj']) restricted to the one column."""
    m = FL.modules()
    flat, _ = m["candidates"].construct(d)
    return m["step11"].adjust(np.asarray(flat["rv10_partial90"], float), d["slot"], d["first"], d["end"])


def run_sessions(d, sessions, bundle=None, sadj=None, batch=True):
    """Detector output for the session indices `sessions` of panel d (earlier sessions of d serve as the causal history).
    Returns one dict per session: day, slots, avail (ns), real, P (n,K), state, ret5_des, sadj (grid values before Prep),
    events [dict(i_d, i_c, S_min, T0_min)], runs [dict(kind, S_min, T0_min, end_min, old, new)]."""
    m = FL.modules(); L, F, E, BX = m["lib"], m["fast"], m["events"], m["breaks"]
    if bundle is None: bundle, _ = FL.load_bundle()
    prep, model, thr = bundle["prep"], bundle["feature"], FL.THRESHOLD
    if sadj is None: sadj = compute_sadj(d)
    dd = dict(d); dd.pop("dv", None); dd["features"] = {COL: sadj}
    last = max(sessions) if len(sessions) else -1
    native = [L.session_grid(dd, i, [COL]) for i in range(last + 1)]
    Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    names = prep.names; keep = [prep.keep.index(L.RET_NAME), prep.keep.index(COL)]
    seqs, raw = [], []
    for i in sessions:
        r = native[i]; X = F.deseason(r["X"], F.ret5_scale(Mx, i))            # s5_eval513 to_des
        Xf = np.full((len(X), len(names)), np.nan); Xf[:, names.index(L.RET_NAME)] = X[:, 0]; Xf[:, names.index(COL)] = X[:, 1]
        seqs.append(L.build_sequence(dict(r, X=prep.transform(Xf)[:, keep]))); raw.append(X)
    if batch and seqs:
        out = model.filter(L.pad(seqs, 2)); Ps = [out[k, :q["n"]] for k, q in enumerate(seqs)]
    else:
        Ps = [model.filter(L.pad([q], 2))[0, :q["n"]] for q in seqs]
    res = []
    for i, q, P, X in zip(sessions, seqs, Ps, raw):
        g = native[i]["slots"]
        day = str(d["day"][d["first"][i]]); n = q["n"]; sl = q["slots"]
        ev = E.detect_old_state_logodds(P, q["real"], q["avail"], thr)[0] if n else []
        runs = BX.runs_old_state(P, q["real"], q["avail"], thr) if n else []
        s0 = q["start"] or 0
        res.append(dict(
            day=day, sess=int(i), start=q["start"], grid_n=q["grid_n"], slots=np.asarray(sl), avail=np.asarray(q["avail"]), real=np.asarray(q["real"]), P=np.asarray(P),
            state=(np.asarray(P).argmax(1) if n else np.zeros(0, int)), ret5_des=X[s0:s0 + n, 0] if n else np.zeros(0), sadj=X[s0:s0 + n, 1] if n else np.zeros(0),
            grid_sadj=X[:, 1], grid_ret5_des=X[:, 0], grid_slots=np.asarray(g), grid_avail=np.asarray(native[i]["avail"]),
            events=[dict(i_d=int(e["i_d"]), i_c=int(e["i_c"]), S_min=int(sl[e["i_d"]]) + 1, T0_min=int(sl[e["i_c"]]) + 1) for e in ev],
            runs=[dict(kind=x["kind"], S_min=int(sl[x["i_d"]]) + 1, T0_min=(int(sl[x["i_end"]]) + 1 if x["kind"] == "confirmed" else None), end_min=int(sl[x["i_end"]]) + 1,
                       old=int(x["old"]), new=int(x["new"])) for x in runs]))
    return res
