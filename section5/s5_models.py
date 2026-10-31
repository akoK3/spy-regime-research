#!/usr/bin/env python3
"""Section 5.4 model families, vectorised across sessions: Gaussian HMM (diagonal), Student-t HMM (hidden scales), HSMM (explicit durations), BOCPD (Normal-Gamma).
Every model: fit(batch) on inner-train sequences; filter(batch) -> causal filtered regime probabilities (S,T,K).
A skipped update (all-NaN row) is a transition-only step (HMM), a hazard-only step (HSMM duration advances, BOCPD statistics unchanged)."""
import numpy as np
from scipy.special import gammaln, digamma, logsumexp
from scipy.optimize import brentq

VAR_FLOOR = 1e-6
VERSIONS = dict(numpy=np.__version__)


def _kmeans(Xr, K, rng, iters=10):
    n = len(Xr)
    c = [Xr[rng.integers(n)]]
    for _ in range(1, K):
        d2 = np.min(((Xr[:, None, :] - np.array(c)[None]) ** 2).sum(-1), axis=1)
        p = d2 / d2.sum() if d2.sum() > 0 else np.full(n, 1.0 / n)
        c.append(Xr[rng.choice(n, p=p)])
    c = np.array(c)
    for _ in range(iters):
        lab = ((Xr[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
        for k in range(K):
            if (lab == k).any(): c[k] = Xr[lab == k].mean(0)
    lab = ((Xr[:, None, :] - c[None]) ** 2).sum(-1).argmin(1)
    return c, lab


def _gauss_logpdf(X, mu, var):
    """X (S,T,D) (NaN allowed), mu/var (K,D) -> (S,T,K); rows with any NaN get 0 (no information)."""
    miss = ~np.isfinite(X).all(-1)
    Z = np.where(np.isfinite(X), X, 0.0)
    d = (Z[:, :, None, :] - mu[None, None]) ** 2 / var[None, None]
    lp = -0.5 * (d + np.log(2 * np.pi * var)[None, None]).sum(-1)
    lp[miss] = 0.0
    return lp, d.sum(-1), miss


def _order_by_return_variance(var):
    return np.argsort(var[:, 0], kind="stable")  # column 0 is the 5-minute return: states ordered calm -> stressed


class _HMMBase:
    """Forward-backward in log-normalised form for batches of sequences with a mask of padded steps."""

    def _fb(self, logB, L, pi, A):
        S, T, K = logB.shape
        act = np.arange(T)[None, :] < L[:, None]
        B = np.exp(logB - logB.max(-1, keepdims=True)); shift = logB.max(-1)
        alpha = np.zeros((S, T, K)); c = np.ones((S, T))
        a = pi[None] * B[:, 0]; c[:, 0] = a.sum(-1); alpha[:, 0] = a / c[:, 0:1]
        for t in range(1, T):
            a = (alpha[:, t - 1] @ A) * B[:, t]
            ct = a.sum(-1); ct = np.where(act[:, t], ct, 1.0)
            a = np.where(act[:, t:t + 1], a / ct[:, None], alpha[:, t - 1])
            alpha[:, t] = a; c[:, t] = ct
        beta = np.ones((S, T, K))
        for t in range(T - 2, -1, -1):
            b = (beta[:, t + 1] * B[:, t + 1]) @ A.T
            b = b / c[:, t + 1:t + 2]
            beta[:, t] = np.where(act[:, t + 1:t + 2], b, 1.0)
        gamma = alpha * beta; gamma /= gamma.sum(-1, keepdims=True)
        gamma = np.where(act[:, :, None], gamma, 0.0)
        xi = np.zeros((K, K))
        for t in range(1, T):
            w = act[:, t]
            if not w.any(): break
            x = alpha[w, t - 1][:, :, None] * A[None] * (B[w, t] * beta[w, t])[:, None, :] / c[w, t][:, None, None]
            xi += x.sum(0)
        ll = float((np.log(c) + shift)[act].sum())
        return alpha, gamma, xi, ll, act

    def filter(self, batch):
        logB = self._logB(batch["X"])[0]
        S, T, K = logB.shape; L = batch["L"]
        act = np.arange(T)[None, :] < L[:, None]
        B = np.exp(logB - logB.max(-1, keepdims=True)); P = np.zeros((S, T, K))
        a = self.pi[None] * B[:, 0]; P[:, 0] = a / a.sum(-1, keepdims=True)
        for t in range(1, T):
            a = (P[:, t - 1] @ self.A) * B[:, t]; a /= a.sum(-1, keepdims=True)
            P[:, t] = np.where(act[:, t:t + 1], a, P[:, t - 1])
        return P


class GaussianHMM(_HMMBase):
    name = "gaussian_hmm"

    def __init__(self, K=3, starts=3, iters=200, tol=1e-4, seed=0):
        self.K, self.starts, self.iters, self.tol, self.seed = K, starts, iters, tol, seed

    def _logB(self, X):
        return _gauss_logpdf(X, self.mu, self.var)

    def _init(self, batch, rng):
        Xr = batch["X"][batch["real"]]
        mu, lab = _kmeans(Xr, self.K, rng)
        var = np.array([Xr[lab == k].var(0) if (lab == k).sum() > 2 else Xr.var(0) for k in range(self.K)]) + VAR_FLOOR
        self.mu, self.var = mu, np.maximum(var, VAR_FLOOR)
        self.pi = np.full(self.K, 1.0 / self.K); self.A = np.full((self.K, self.K), 0.1 / max(self.K - 1, 1)) + np.eye(self.K) * (0.9 - 0.1 / max(self.K - 1, 1))
        self.A /= self.A.sum(1, keepdims=True)

    def _mstep_emission(self, batch, gamma, extra=None):
        X = np.where(batch["real"][:, :, None], batch["X"], 0.0); W = gamma * batch["real"][:, :, None]
        if extra is not None: W = W * extra
        sw = W.sum((0, 1)) + 1e-12
        mu = np.einsum("stk,std->kd", W, X) / sw[:, None]
        var = np.einsum("stk,stkd->kd", W, (X[:, :, None, :] - mu[None, None]) ** 2) / sw[:, None]
        return mu, np.maximum(var, VAR_FLOOR)

    def _em_step(self, batch):
        logB = self._logB(batch["X"])[0]
        _, gamma, xi, ll, act = self._fb(logB, batch["L"], self.pi, self.A)
        self.pi = gamma[:, 0].sum(0) + 1e-12; self.pi /= self.pi.sum()
        self.A = xi + 1e-12; self.A /= self.A.sum(1, keepdims=True)
        self.mu, self.var = self._mstep_emission(batch, gamma)
        return ll

    def fit(self, batch):
        best = None; self.fit_info = dict(iterations=[], restarts=0)
        for s in range(self.starts):
            rng = np.random.default_rng(self.seed * 1000 + s)
            self._init(batch, rng); prev = -np.inf; it = 0
            for it in range(1, self.iters + 1):
                ll = self._em_step(batch)
                if np.isfinite(prev) and abs(ll - prev) < self.tol * max(1.0, abs(prev)): break
                prev = ll
            self.fit_info["iterations"].append(it)
            if best is None or ll > best[0]: best = (ll, self._state())
        self._load(best[1]); self.loglik = best[0]; self._reorder()
        return self

    def _state(self):
        return {k: np.array(getattr(self, k)) for k in ("pi", "A", "mu", "var") if hasattr(self, k)} | ({"nu": np.array(self.nu)} if hasattr(self, "nu") else {})

    def _load(self, s):
        for k, v in s.items(): setattr(self, k, v.copy())

    def _reorder(self):
        o = _order_by_return_variance(self.var)
        self.pi, self.mu, self.var, self.A = self.pi[o], self.mu[o], self.var[o], self.A[np.ix_(o, o)]
        if hasattr(self, "nu"): self.nu = self.nu[o]


class StudentTHMM(GaussianHMM):
    """Multivariate diagonal-scale Student-t per state with hidden Gamma scale u: x | z=k, u ~ N(mu_k, var_k / u), u ~ Gamma(nu_k/2, nu_k/2). EM; df in [2.1, 30]."""
    name = "student_t_hmm"
    NU_LO, NU_HI = 2.1, 30.0

    def _logB(self, X):
        miss = ~np.isfinite(X).all(-1); D = X.shape[-1]
        Z = np.where(np.isfinite(X), X, 0.0)
        d = (((Z[:, :, None, :] - self.mu[None, None]) ** 2) / self.var[None, None]).sum(-1)
        nu = self.nu[None, None]
        lp = gammaln((nu + D) / 2) - gammaln(nu / 2) - D / 2 * np.log(nu * np.pi) - 0.5 * np.log(self.var).sum(-1)[None, None] - (nu + D) / 2 * np.log1p(d / nu)
        lp[miss] = 0.0
        return lp, d, miss

    def _init(self, batch, rng):
        super()._init(batch, rng); self.nu = np.full(self.K, 8.0)

    def _em_step(self, batch):
        logB, d, miss = self._logB(batch["X"])
        _, gamma, xi, ll, act = self._fb(logB, batch["L"], self.pi, self.A)
        D = batch["D"]; nu = self.nu[None, None]
        u = (nu + D) / (nu + d)
        Elogu = digamma((nu + D) / 2) - np.log((nu + D) / 2) + np.log(u)  # E[log u | x, z]
        self.pi = gamma[:, 0].sum(0) + 1e-12; self.pi /= self.pi.sum()
        self.A = xi + 1e-12; self.A /= self.A.sum(1, keepdims=True)
        X = np.where(batch["real"][:, :, None], batch["X"], 0.0); W = gamma * batch["real"][:, :, None]
        Wu = W * u
        sw, swu = W.sum((0, 1)) + 1e-12, Wu.sum((0, 1)) + 1e-12
        self.mu = np.einsum("stk,std->kd", Wu, X) / swu[:, None]
        self.var = np.maximum(np.einsum("stk,stkd->kd", Wu, (X[:, :, None, :] - self.mu[None, None]) ** 2) / sw[:, None], VAR_FLOOR)
        for k in range(self.K):
            c = (W[:, :, k] * (Elogu[:, :, k] - u[:, :, k])).sum() / sw[k]
            f = lambda v: -digamma(v / 2) + np.log(v / 2) + 1 + c  # c already carries the old-nu terms of E[log u]
            lo, hi = self.NU_LO, self.NU_HI
            self.nu[k] = lo if f(lo) < 0 else (hi if f(hi) > 0 else brentq(f, lo, hi))
        self._occ = W.sum((0, 1)) / max(W.sum(), 1e-12)
        return ll

    def fit(self, batch):
        best = None; self.fit_info = dict(iterations=[], restarts=0)
        for s in range(self.starts):
            for attempt in range(10):  # restart (new initialisation) if a state is under 1% occupancy
                rng = np.random.default_rng(self.seed * 1000 + s * 17 + attempt)
                self._init(batch, rng); prev = -np.inf
                for it in range(1, self.iters + 1):
                    ll = self._em_step(batch)
                    if np.isfinite(prev) and abs(ll - prev) < self.tol * max(1.0, abs(prev)): break
                    prev = ll
                if (self._occ >= 0.01).all(): break
                self.fit_info["restarts"] += 1
            self.fit_info["iterations"].append(it)
            if best is None or ll > best[0]: best = (ll, self._state())
        self._load(best[1]); self.loglik = best[0]; self._reorder()
        return self


class HSMM:
    """Hidden semi-Markov model, K states, free-form duration pmf by EM (via the discrete hazard h_k(d)), Gaussian diagonal emissions.
    Expanded-state forward-backward over (state, elapsed duration). Duration counted in grid intervals (skips included), capped at Dmax and
    right-censored at the session end. Reset: initial state distribution with duration 1."""
    name = "hsmm"

    def __init__(self, K=2, starts=3, iters=200, tol=1e-4, seed=0, Dmax=78):
        self.K, self.starts, self.iters, self.tol, self.seed, self.Dmax = K, starts, iters, tol, seed, Dmax

    def _logB(self, X):
        return _gauss_logpdf(X, self.mu, self.var)

    def _init(self, batch, rng):
        Xr = batch["X"][batch["real"]]; mu, lab = _kmeans(Xr, self.K, rng)
        self.mu = mu; self.var = np.maximum(np.array([Xr[lab == k].var(0) if (lab == k).sum() > 2 else Xr.var(0) for k in range(self.K)]), VAR_FLOOR)
        self.pi = np.full(self.K, 1.0 / self.K)
        self.A = (np.ones((self.K, self.K)) - np.eye(self.K)); self.A /= self.A.sum(1, keepdims=True)
        self.h = np.full((self.K, self.Dmax), 0.1); self.h[:, -1] = 1.0

    def _fb(self, logB, L):
        S, T, K = logB.shape; Dm = self.Dmax; h, A = self.h, self.A
        act = np.arange(T)[None, :] < L[:, None]
        B = np.exp(logB - logB.max(-1, keepdims=True)); shift = logB.max(-1)
        al = np.zeros((S, T, K, Dm)); c = np.ones((S, T))

        def step(prev):
            leave = (prev * h[None]).sum(-1)                       # (S,K)
            new = np.zeros_like(prev)
            new[:, :, 0] = leave @ A
            new[:, :, 1:] = prev[:, :, :-1] * (1 - h[None, :, :-1])
            return new
        a0 = np.zeros((S, K, Dm)); a0[:, :, 0] = self.pi[None] * B[:, 0]; c[:, 0] = a0.sum((1, 2)); al[:, 0] = a0 / c[:, 0, None, None]
        for t in range(1, T):
            a = step(al[:, t - 1]) * B[:, t][:, :, None]
            ct = np.where(act[:, t], a.sum((1, 2)), 1.0)
            al[:, t] = np.where(act[:, t, None, None], a / ct[:, None, None], al[:, t - 1]); c[:, t] = ct
        be = np.ones((S, T, K, Dm))
        for t in range(T - 2, -1, -1):
            nb = B[:, t + 1]                                         # (S,K)
            bj0 = nb * be[:, t + 1][:, :, 0]                         # (S,K): emission * beta of entering state j at duration 1
            enter = bj0 @ A.T                                        # (S,K): sum_j A[k,j] b_j beta_j1
            cont = np.zeros((S, K, Dm)); cont[:, :, :-1] = nb[:, :, None] * be[:, t + 1][:, :, 1:]
            b = h[None] * enter[:, :, None] + (1 - h[None]) * cont
            b = b / c[:, t + 1, None, None]
            be[:, t] = np.where(act[:, t + 1, None, None], b, 1.0)
        return al, be, c, shift, act, B

    def _em_step(self, batch):
        logB = self._logB(batch["X"])[0]
        al, be, c, shift, act, B = self._fb(logB, batch["L"])
        S, T, K, Dm = al.shape; h, A = self.h, self.A
        gam = (al * be).sum(-1); gam /= gam.sum(-1, keepdims=True); gam = np.where(act[:, :, None], gam, 0.0)
        leave_c = np.zeros((K, Dm)); stay_c = np.zeros((K, Dm)); xiA = np.zeros((K, K))
        for t in range(T - 1):
            w = act[:, t + 1]
            if not w.any(): break
            nb = B[w, t + 1]; bn = be[w, t + 1]; cc = c[w, t + 1][:, None, None]; a = al[w, t]
            bj0 = nb * bn[:, :, 0]
            enter = bj0 @ A.T
            lv = a * h[None] * enter[:, :, None] / cc
            leave_c += lv.sum(0)
            st = np.zeros_like(a); st[:, :, :-1] = a[:, :, :-1] * (1 - h[None, :, :-1]) * nb[:, :, None] * bn[:, :, 1:] / cc
            stay_c += st.sum(0)
            xiA += (((a * h[None]).sum(-1) / c[w, t + 1][:, None])[:, :, None] * A[None] * bj0[:, None, :]).sum(0)
        h0 = (leave_c.sum() + 1e-9) / (leave_c.sum() + stay_c.sum() + 1e-9)
        self.h = (leave_c + 0.5 * h0) / (leave_c + stay_c + 0.5); self.h[:, -1] = 1.0
        self.h = np.clip(self.h, 1e-6, 1.0)
        np.fill_diagonal(xiA, 0.0); self.A = xiA + 1e-12; np.fill_diagonal(self.A, 0.0); self.A /= self.A.sum(1, keepdims=True)
        self.pi = gam[:, 0].sum(0) + 1e-12; self.pi /= self.pi.sum()
        X = np.where(batch["real"][:, :, None], batch["X"], 0.0); W = gam * batch["real"][:, :, None]; sw = W.sum((0, 1)) + 1e-12
        self.mu = np.einsum("stk,std->kd", W, X) / sw[:, None]
        self.var = np.maximum(np.einsum("stk,stkd->kd", W, (X[:, :, None, :] - self.mu[None, None]) ** 2) / sw[:, None], VAR_FLOOR)
        return float((np.log(c) + shift)[act].sum())

    def fit(self, batch):
        best = None; self.fit_info = dict(iterations=[], restarts=0)
        for s in range(self.starts):
            self._init(batch, np.random.default_rng(self.seed * 1000 + s)); prev = -np.inf
            for it in range(1, self.iters + 1):
                ll = self._em_step(batch)
                if np.isfinite(prev) and abs(ll - prev) < self.tol * max(1.0, abs(prev)): break
                prev = ll
            self.fit_info["iterations"].append(it)
            if best is None or ll > best[0]: best = (ll, {k: getattr(self, k).copy() for k in ("pi", "A", "mu", "var", "h")})
        for k, v in best[1].items(): setattr(self, k, v)
        self.loglik = best[0]
        o = _order_by_return_variance(self.var)
        self.pi, self.mu, self.var, self.h, self.A = self.pi[o], self.mu[o], self.var[o], self.h[o], self.A[np.ix_(o, o)]
        return self

    def filter(self, batch):
        logB = self._logB(batch["X"])[0]
        al = self._fb(logB, batch["L"])[0]
        return al.sum(-1)


class BOCPD:
    """Bayesian online changepoint detection, independent Normal-Gamma per feature (Student-t predictive), constant hazard 1/lambda, run length truncated at 200.
    Prior (standardised data): mu0=0, kappa0=1, alpha0=1, beta0=1. Output per update: P(changepoint within the last 3 updates) = P(run length <= 2)."""
    name = "bocpd"

    def __init__(self, lam=39, rmax=200, prior=(0.0, 1.0, 1.0, 1.0)):
        self.lam, self.rmax, self.prior = lam, rmax, prior

    def fit(self, batch):
        self.fit_info = dict(iterations=[], restarts=0)
        return self

    def filter(self, batch):
        X, real, L = batch["X"], batch["real"], batch["L"]
        S, T, D = X.shape; R = self.rmax + 1; H = 1.0 / self.lam
        m0, k0, a0, b0 = self.prior
        mu = np.full((S, R, D), m0); ka = np.full((S, R, D), k0); al = np.full((S, R, D), a0); be = np.full((S, R, D), b0)
        P = np.zeros((S, R)); P[:, 0] = 1.0
        out = np.zeros((S, T, 3)); out[:, :, 0] = 0.0
        pm = np.zeros((S, T))
        for t in range(T):
            act = t < L
            x = np.where(real[:, t, None], X[:, t], 0.0)[:, None, :]
            rl = real[:, t]
            # predictive for run-length hypotheses
            df = 2 * al; sc2 = be * (ka + 1) / (al * ka)
            lg = gammaln((df + 1) / 2) - gammaln(df / 2) - 0.5 * np.log(df * np.pi * sc2) - (df + 1) / 2 * np.log1p((x - mu) ** 2 / (df * sc2))
            pred = np.exp(lg.sum(-1) - lg.sum(-1).max(-1, keepdims=True))
            joint = P * np.where(rl[:, None], pred, 1.0)          # skip: no evidence, hazard only
            cp = joint.sum(-1) * H
            grow = joint * (1 - H)
            newP = np.zeros_like(P); newP[:, 0] = cp; newP[:, 1:] = grow[:, :-1]; newP[:, -1] += grow[:, -1]
            newP /= newP.sum(-1, keepdims=True)
            # statistics: shift by one; updated with x on real updates, unchanged on skips
            nk, nm, na, nb = ka + 1, (ka * mu + x) / (ka + 1), al + 0.5, be + ka * (x - mu) ** 2 / (2 * (ka + 1))
            sel = rl[:, None, None]
            u_mu, u_ka, u_al, u_be = (np.where(sel, nm, mu), np.where(sel, nk, ka), np.where(sel, na, al), np.where(sel, nb, be))
            mu2 = np.concatenate([np.full((S, 1, D), m0), u_mu[:, :-1]], 1); ka2 = np.concatenate([np.full((S, 1, D), k0), u_ka[:, :-1]], 1)
            al2 = np.concatenate([np.full((S, 1, D), a0), u_al[:, :-1]], 1); be2 = np.concatenate([np.full((S, 1, D), b0), u_be[:, :-1]], 1)
            keep = act[:, None, None]
            mu, ka, al, be = (np.where(keep, mu2, mu), np.where(keep, ka2, ka), np.where(keep, al2, al), np.where(keep, be2, be))
            P = np.where(act[:, None], newP, P)
            out[:, t, 0] = P[:, :3].sum(-1)
            out[:, t, 1] = (P * np.arange(R)[None]).sum(-1)
            # posterior-mean variance of the return dimension (column 0) mixed over run lengths
            out[:, t, 2] = (P * (be[:, :, 0] / np.maximum(al[:, :, 0] - 1, 0.5))).sum(-1)
        return out   # (S,T,3): P(cp within 3), E[run length], mixed variance of column 0
