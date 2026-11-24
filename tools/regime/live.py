"""The one function the live engine, replay and the acceptance test all call to evaluate a session prefix."""
import numpy as np

from . import core, panel as PN

MIN = PN.MIN


def due_slots(open_ns, close_ns, now_ns, grace_ns=0):
    """Grid slots (4, 9, ...) of a session whose decision bar is available (slot start + 1 min) plus grace at now_ns."""
    m = int((close_ns - open_ns) // MIN); g = np.arange(4, m, 5)
    return [int(x) for x in g if open_ns + (x + 1) * MIN + grace_ns <= now_ns]


def evaluate_at(sessions, bars, upto_ns, bundle=None):
    """sessions: the causal history (at least core.BASELINE_SESSIONS earlier sessions) followed by the session being evaluated.
    bars: SPY 1-min bars (dict of arrays t, o, h, l, c, v). Only minutes available at upto_ns enter.
    Returns (result dict from core.run_sessions for the last session or None, n_prior_sessions)."""
    d = PN.build_panel(sessions, bars, upto_ns)
    if len(d["first"]) == 0 or str(d["day"][d["first"][-1]]) != sessions[-1]["day"]: return None, len(d["first"])
    i = len(d["first"]) - 1
    return core.run_sessions(d, [i], bundle, batch=False)[0], i
