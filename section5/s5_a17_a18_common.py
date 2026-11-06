#!/usr/bin/env python3
"""Shared code for A17 (reproduction, H1(c), post-hoc R=1-net H1(a), test QLIKE percent) and A18 (selection by one-step-ahead predictive log-likelihood). Not in the main-run code closure:
nothing here changes a main-run result. Functions take a fitted model or a fold backend; data access happens only through s5_backend."""
import os, json, math, hashlib, datetime
from pathlib import Path
import numpy as np
from scipy.special import gammaln, logsumexp

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; LOG = RES / "a17_a18_log.txt"
EXIT_OK, EXIT_CRASH, EXIT_STOP, EXIT_GUARD, EXIT_MISMATCH = 0, 1, 2, 3, 4
VOL_FAMILIES = ("rv", "downside", "abs_return", "intrabar_range")                       # A18 rule 3 (fixed before results)
NONVOL_FAMILIES = ("momentum", "return", "relative_volume", "close_location")


def log(msg, tag="py"):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [{tag} {os.getpid()}] {msg}"
    LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def keep_awake(on=True):
    try:
        import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception: pass


# ---------- exact comparison (A17 rule 1)
def same(a, b):
    """Exact equality after a JSON round trip; NaN equals NaN; ints and floats compare by value."""
    if isinstance(a, dict) and isinstance(b, dict): return a.keys() == b.keys() and all(same(a[k], b[k]) for k in a)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)): return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    if isinstance(a, float) and isinstance(b, float) and math.isnan(a) and math.isnan(b): return True
    return a == b


def roundtrip(x): return json.loads(json.dumps(x, default=float))


def diffs(a, b, path=""):
    if isinstance(a, dict) and isinstance(b, dict):
        return [d for k in sorted(set(a) | set(b)) for d in (diffs(a.get(k), b.get(k), f"{path}/{k}") if k in a and k in b else [f"{path}/{k}: key only on one side"])]
    return [] if same(a, b) else [f"{path}: reproduced {a!r} != stored {b!r}"]


# ---------- one-step-ahead predictive density of the return column (A18 rule 2)
def _norm_lp(x, mu, var): return -0.5 * (np.log(2 * np.pi * var) + (x - mu) ** 2 / var)


def _t_lp(x, mu, var, nu): return gammaln((nu + 1) / 2) - gammaln(nu / 2) - 0.5 * np.log(nu * np.pi * var) - (nu + 1) / 2 * np.log1p((x - mu) ** 2 / (nu * var))


def pred_logpdf(family, model, batch):
    """(S, T): log p(x0[t] | updates 0..t-1 of the same session) for 1 <= t < L with finite x0[t]; NaN elsewhere. x0 = column 0 (the deseasonalised 5-min return, preprocessed)."""
    X, L = batch["X"], batch["L"]; S, T, D = X.shape; x0 = X[:, :, 0]; z = np.where(np.isfinite(x0), x0, 0.0)
    act = np.arange(T)[None, :] < L[:, None]; ok = act & np.isfinite(x0); ok[:, 0] = False; out = np.full((S, T), np.nan)
    if T < 2: return out
    if family in ("gaussian_hmm", "student_t_hmm"):
        P = model.filter(batch); Pp = np.einsum("stk,kj->stj", P[:, :-1], model.A); mu, var = model.mu[:, 0], model.var[:, 0]
        lf = _t_lp(z[:, 1:, None], mu, var, model.nu) if family == "student_t_hmm" else _norm_lp(z[:, 1:, None], mu, var)
        lp = logsumexp(np.log(np.maximum(Pp, 1e-300)) + lf, axis=-1); out[:, 1:] = np.where(ok[:, 1:], lp, np.nan); return out
    if family == "hsmm": return _hsmm_pred(model, batch, z, ok, out)
    if family == "bocpd": return _bocpd_pred(model, batch, z, ok, out)
    raise ValueError(family)


def _hsmm_pred(model, batch, z, ok, out, return_pred_states=False):
    """Same recursion as s5_models.HSMM.filter; the one-step prediction is taken before the emission of step t."""
    logB = model._logB(batch["X"])[0]; S, T, K = logB.shape; Dm = model.Dmax; h, A = model.h, model.A; act = np.arange(T)[None, :] < batch["L"][:, None]
    B = np.exp(logB - logB.max(-1, keepdims=True)); mu, var = model.mu[:, 0], model.var[:, 0]; PP = np.zeros((S, T, K))
    prev = np.zeros((S, K, Dm)); prev[:, :, 0] = model.pi[None] * B[:, 0]; prev /= prev.sum((1, 2), keepdims=True)
    for t in range(1, T):
        leave = (prev * h[None]).sum(-1); new = np.zeros_like(prev); new[:, :, 0] = leave @ A; new[:, :, 1:] = prev[:, :, :-1] * (1 - h[None, :, :-1])
        pp = new.sum(-1); pp = pp / pp.sum(-1, keepdims=True); PP[:, t] = pp
        out[:, t] = np.where(ok[:, t], logsumexp(np.log(np.maximum(pp, 1e-300)) + _norm_lp(z[:, t, None], mu, var), axis=-1), np.nan)
        new = new * B[:, t][:, :, None]; ct = np.where(act[:, t], new.sum((1, 2)), 1.0); prev = np.where(act[:, t, None, None], new / ct[:, None, None], prev)
    return (out, PP) if return_pred_states else out


def _bocpd_pred(model, batch, z, ok, out, return_trace=False):
    """Same recursion as s5_models.BOCPD.filter; the predictive of x0[t] is the run-length posterior after t-1 mixed over each run length's Student-t predictive of column 0."""
    X, real, L = batch["X"], batch["real"], batch["L"]; S, T, D = X.shape; R = model.rmax + 1; H = 1.0 / model.lam; m0, k0, a0, b0 = model.prior
    mu = np.full((S, R, D), m0); ka = np.full((S, R, D), k0); al = np.full((S, R, D), a0); be = np.full((S, R, D), b0); P = np.zeros((S, R)); P[:, 0] = 1.0; rstar = np.zeros((S, T))
    for t in range(T):
        act = t < L; x = np.where(real[:, t, None], X[:, t], 0.0)[:, None, :]; rl = real[:, t]
        df = 2 * al; sc2 = be * (ka + 1) / (al * ka)
        lg = gammaln((df + 1) / 2) - gammaln(df / 2) - 0.5 * np.log(df * np.pi * sc2) - (df + 1) / 2 * np.log1p((x - mu) ** 2 / (df * sc2))
        if t >= 1:
            lg0 = gammaln((df[:, :, 0] + 1) / 2) - gammaln(df[:, :, 0] / 2) - 0.5 * np.log(df[:, :, 0] * np.pi * sc2[:, :, 0]) - (df[:, :, 0] + 1) / 2 * np.log1p((z[:, t, None] - mu[:, :, 0]) ** 2 / (df[:, :, 0] * sc2[:, :, 0]))
            out[:, t] = np.where(ok[:, t], logsumexp(np.log(np.maximum(P, 1e-300)) + lg0, axis=-1), np.nan)
        pred = np.exp(lg.sum(-1) - lg.sum(-1).max(-1, keepdims=True)); joint = P * np.where(rl[:, None], pred, 1.0); cp = joint.sum(-1) * H; grow = joint * (1 - H)
        newP = np.zeros_like(P); newP[:, 0] = cp; newP[:, 1:] = grow[:, :-1]; newP[:, -1] += grow[:, -1]; newP /= newP.sum(-1, keepdims=True)
        nk, nm, na, nb = ka + 1, (ka * mu + x) / (ka + 1), al + 0.5, be + ka * (x - mu) ** 2 / (2 * (ka + 1)); sel = rl[:, None, None]
        u_mu, u_ka, u_al, u_be = (np.where(sel, nm, mu), np.where(sel, nk, ka), np.where(sel, na, al), np.where(sel, nb, be))
        mu2 = np.concatenate([np.full((S, 1, D), m0), u_mu[:, :-1]], 1); ka2 = np.concatenate([np.full((S, 1, D), k0), u_ka[:, :-1]], 1)
        al2 = np.concatenate([np.full((S, 1, D), a0), u_al[:, :-1]], 1); be2 = np.concatenate([np.full((S, 1, D), b0), u_be[:, :-1]], 1); keep = act[:, None, None]
        mu, ka, al, be = (np.where(keep, mu2, mu), np.where(keep, ka2, ka), np.where(keep, al2, al), np.where(keep, be2, be)); P = np.where(act[:, None], newP, P); rstar[:, t] = P.argmax(-1)
    return (out, rstar) if return_trace else out


def mean_nll(family, model, seqs, D):
    import s5_lib as L
    lp = pred_logpdf(family, model, L.pad(seqs, D)); v = lp[np.isfinite(lp)]; return (float(-v.mean()) if len(v) else float("inf")), int(len(v))


# ---------- A17: fold-level A7 thresholds, alarms, placebo points
def a7_threshold(db, family, subset, params):
    import s5_eval as V, s5_a7 as B
    m = db.fit(family, tuple(subset), dict(params), 3); D = 1 + len(subset); qs = db.sequences("val", tuple(subset)); rs = V.run_filter(family, m, qs, D)
    lo, hi, tol = B.BOUNDS["bocpd" if family == "bocpd" else "hmm"]; rate = lambda thr: sum(len(B.events(family, r, q, thr)) for q, r in zip(qs, rs)) / len(qs)
    thr, info = B.bisect_threshold(rate, lo, hi, B.TARGET, tol); return dict(threshold=float(thr), info=info, validation_rate=float(rate(thr)), n_val=len(qs))


def test_alarms(db, family, subset, params, thr):
    """{session day: [[T_d minute, T_c minute], ...]} for every test session (minutes after 09:30 at availability = slot + 1)."""
    import s5_eval as V, s5_a7 as B
    m = db.fit(family, tuple(subset), dict(params), 3); D = 1 + len(subset); qs = db.sequences("test", tuple(subset)); rs = V.run_filter(family, m, qs, D); d = db.c["d"]; out = {}
    for q, r in zip(qs, rs):
        out[str(d["day"][d["first"][q["sess"]]])] = [[int(q["slots"][e["i_d"]]) + 1, int(q["slots"][e["i_c"]]) + 1] for e in (B.events(family, r, q, thr) if q["n"] else [])]
    return out


def placebo_specs(db, n_per_duration=50, seed=777):
    import s5_d2_stable as S, s5_a6 as A, s5_a7 as B
    c = db.c; stable, _ = S.stable_days(c["d"], c["seg"]["test"], c["dv"])
    return A.build_specs(c["d"], c["dv"], stable, np.random.default_rng(seed), 0, [(1.0, "up", du) for du in B.DURS], n_per_duration)


def placebo_points(db, family, model, subset, placebo_rows):
    """(x, y) points as in DataBackend._h1a_points with the break splices replaced by the R=1 placebo splices (x from the fold's H1(a) null splices)."""
    import s5_eval as V, s5_a7 as B, s5_sweep as W
    sp = db._splices(); null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA
    def run_(rl):
        qs = [db.c["mk"](r, tuple(subset)) for r in [db.c["to_des"](r, r["iA"]) for r in rl]]; rs = V.run_filter(family, model, qs, D)
        R_, real, av = W.stack(rs, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
    sw = (lambda a, b, c_, t: W.sweep_map(a, b, c_, grid, t)) if family == "bocpd" else (lambda a, b, c_, t: W.sweep_old_state(a, b, c_, grid, t))
    R_, re_, av_, _ = run_(null); cnt, _ = sw(R_, re_, av_, None); xs = cnt.mean(0); R_, re_, av_, t_ = run_(placebo_rows); _, h = sw(R_, re_, av_, t_)
    return list(zip(xs.tolist(), h.mean(0).tolist()))


class Capture:
    """Pass-through backend that keeps the raw score dict, so s5_run.score_fold (the genuine main-path code) can be reused."""
    def __init__(self, b): self._b = b; self.s = None
    def __getattr__(self, n): return getattr(self._b, n)
    def score(self, fold, family, setup): self.s = self._b.score(fold, family, setup); return self.s
