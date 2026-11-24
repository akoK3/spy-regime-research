#!/usr/bin/env python3
"""Protocol 5.8: per-fold feature selection (greedy forward from the return-only model, fixed K=3 / lambda=39, 1 start; stop when the gain is under 1% or at 6 features;
then K/lambda tuning with 3 starts), and the final-setup aggregation for 5.13. Pure logic: the objective is injected (validation QLIKE and synthetic delay of a fitted model), so this
module touches no data. objective(subset: tuple, params: dict, starts: int) -> dict(qlike=float, delay=float)."""
from collections import Counter
import numpy as np

MAX_FEATS = 6; MIN_GAIN = 0.01; BASE_PARAMS = dict(K=3, lam=39)


class Budget:
    def __init__(self, n=None): self.n = n; self.used = 0

    def spend(self):
        if self.n is not None and self.used >= self.n: return False
        self.used += 1; return True


def _delay(r): return r["delay"] if np.isfinite(r["delay"]) else np.inf


def greedy_forward(candidates, objective, budget=None, max_feats=MAX_FEATS, min_gain=MIN_GAIN, params=BASE_PARAMS):
    """Returns dict(selected, trace, exhausted, base_qlike, final_qlike). The first model is the return-only model (empty subset). Each step adds the candidate with the lowest
    QLIKE (ties: lower delay, then dictionary order); a candidate is kept only if the relative QLIKE gain over the current model is at least min_gain. If the budget runs out,
    the best model so far is kept and `exhausted` is set."""
    budget = budget or Budget(None); cands = sorted(candidates)
    if not budget.spend(): return dict(selected=[], trace=[], exhausted=True, base_qlike=None, final_qlike=None)
    cur = objective((), params, 1); sel = []; trace = [dict(step=0, subset=[], qlike=cur["qlike"], delay=cur["delay"])]; exhausted = False
    while len(sel) < max_feats:
        best = None
        for c in cands:
            if c in sel: continue
            if not budget.spend(): exhausted = True; break
            r = objective(tuple(sel + [c]), params, 1); k = (r["qlike"], _delay(r))
            if best is None or k < best[0]: best = (k, c, r)       # candidates are visited in dictionary order, so equal keys keep the earlier name
        if best is None: break
        gain = (cur["qlike"] - best[2]["qlike"]) / abs(cur["qlike"]) if cur["qlike"] else 0.0
        if gain < min_gain: trace.append(dict(step=len(sel) + 1, rejected=best[1], gain=gain)); break
        sel.append(best[1]); cur = best[2]; trace.append(dict(step=len(sel), added=best[1], qlike=cur["qlike"], delay=cur["delay"], gain=gain))
        if exhausted: break
    return dict(selected=sel, trace=trace, exhausted=exhausted, base_qlike=trace[0]["qlike"], final_qlike=cur["qlike"])


def tune(selected, objective, grid, budget=None, starts=3):
    """grid: list of param dicts (K for the HMM/HSMM families, lam for BOCPD). Lowest QLIKE; ties: smaller parameter value, then delay."""
    budget = budget or Budget(None); best = None; exhausted = False
    for p in grid:
        if not budget.spend(): exhausted = True; break
        r = objective(tuple(selected), p, starts); k = (r["qlike"], tuple(sorted(p.items())), _delay(r))
        if best is None or k < best[0]: best = (k, p, r)
    return dict(params=best[1] if best else None, result=best[2] if best else None, exhausted=exhausted)


def final_setup(setups):
    """5.13 input from the per-fold setups [dict(features=[...], params=dict)]: feature count = median across folds (round half up), filled by selection frequency, ties by
    dictionary order; parameters = mode per key, ties to the smaller value."""
    n = int(np.floor(np.median([len(s["features"]) for s in setups]) + 0.5)); cnt = Counter(f for s in setups for f in s["features"])
    order = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0])); feats = [f for f, _ in order][:n]
    out = dict(n_features=n, features=feats, params=_mode_params([s["params"] for s in setups]), frequency=dict(sorted(cnt.items())))
    if any(s.get("base_params") for s in setups): out["base_params"] = _mode_params([s["base_params"] for s in setups if s.get("base_params")])      # A15 rule 1
    return out


def _mode_params(plist):
    """Mode per key across folds, ties to the smaller value."""
    par = {}
    for k in sorted({k for p in plist for k in p}):
        c = Counter(p[k] for p in plist if k in p); top = max(c.values()); par[k] = min(v for v, m in c.items() if m == top)
    return par
