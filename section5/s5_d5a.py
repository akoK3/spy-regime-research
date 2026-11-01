#!/usr/bin/env python3
"""D5 part A: BOCPD root cause. Synthetic only (one Gaussian feature, 78 updates, 10x variance up / down at update 40).
(1) Run-length posteriors of our implementation vs an independent reference built from Adams & MacKay (2007): the reference does not use the sequential
sufficient-statistic updates; each run-length hypothesis r is scored by the closed-form Normal-Gamma marginal likelihood of its segment,
p(x_t | segment) = ML(segment + x_t) / ML(segment), and the posterior recursion is written separately (loops, log-space ML via prefix sums).
Compared directly: maximum absolute difference of P(r_t | x_1:t) over all t and r, for priors and lambda 12/39/78.
(2) Detection with the D4 alarms (a) P(r<=2), (b) MAP run-length drop, (c) P(r<6) for each prior and lambda, Gaussian R=10, D4 'maxhit' calibration rule.
(3) Evidence asymmetry: analytic KL per update and the reference's response speed up vs down."""
import sys, json
from pathlib import Path
import numpy as np
from scipy.special import gammaln
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_models as M, s5_d4 as D

T = 78; J = 40; R = 10


def log_ml_segments(S1, S2, lo, hi, prior):
    """Closed-form log marginal likelihood of x[lo:hi] under Normal-Gamma(mu0,k0,a0,b0), from prefix sums S1, S2 (length T+1)."""
    mu0, k0, a0, b0 = prior; n = hi - lo
    if n == 0: return 0.0
    s1, s2 = S1[hi] - S1[lo], S2[hi] - S2[lo]; xb = s1 / n; ss = s2 - n * xb * xb
    kn, an = k0 + n, a0 + n / 2.0; bn = b0 + 0.5 * ss + k0 * n * (xb - mu0) ** 2 / (2.0 * kn)
    return gammaln(an) - gammaln(a0) + a0 * np.log(b0) - an * np.log(bn) + 0.5 * (np.log(k0) - np.log(kn)) - 0.5 * n * np.log(2 * np.pi)


def reference_posterior(x, lam, prior):
    """Adams & MacKay (2007) recursion with the marginal-likelihood predictive; returns list of arrays P(r_t | x_1:t), r = 0..t+1 (0-based t)."""
    H = 1.0 / lam; S1 = np.r_[0, np.cumsum(x)]; S2 = np.r_[0, np.cumsum(x * x)]; P = np.array([1.0]); out = []
    for t in range(len(x)):
        pred = np.array([np.exp(log_ml_segments(S1, S2, t - r, t + 1, prior) - log_ml_segments(S1, S2, t - r, t, prior)) for r in range(len(P))])
        grow = P * pred * (1 - H); cp = float((P * pred * H).sum())
        P = np.concatenate([[cp], grow]); P /= P.sum(); out.append(P.copy())
    return out


def main():
    out = {}
    rng = np.random.default_rng(555)
    kinds = rng.choice(["calm", "stressed", "up", "down"], size=189, p=[.4, .2, .2, .2])
    tr = [D.gen(rng, "gaussian", k, R, int(rng.integers(20, 61))) for k in kinds]; allx = np.concatenate(tr)
    mu, sd = allx.mean(), allx.std(); z = lambda X: (X - mu) / sd
    calm = np.concatenate([z(X) for X, k in zip(tr, kinds) if k == "calm"]); stressed = np.concatenate([z(X) for X, k in zip(tr, kinds) if k == "stressed"])
    vc, vs = float(calm.var()), float(stressed.var())
    priors = {"default (0,1,1,1)": (0.0, 1.0, 1.0, 1.0), f"beta0 = calm train variance ({vc:.2f})": (0.0, 1.0, 1.0, vc), f"beta0 = stressed train variance ({vs:.2f})": (0.0, 1.0, 1.0, vs),
              "tighter (0,1,3,2): mean variance 1, alpha0=3": (0.0, 1.0, 3.0, 2.0)}
    out["train_pooled_variance_in_z_units"] = 1.0; out["train_calm_var_z"] = vc; out["train_stressed_var_z"] = vs
    # ---- (1) posterior comparison
    rt = np.random.default_rng(777); sess = {"up": [z(D.gen(rt, "gaussian", "up", R, J))[:, 0] for _ in range(6)], "down": [z(D.gen(rt, "gaussian", "down", R, J))[:, 0] for _ in range(6)]}
    cmp = {}
    for pn, pr in priors.items():
        for lam in (12, 39, 78):
            md = 0.0
            for dname, xs in sess.items():
                bt = L.pad([D.seq(x[:, None]) for x in xs], 1); m = M.BOCPD(lam, prior=pr, keep_posterior=True); m.filter(bt)
                for k, x in enumerate(xs):
                    ref = reference_posterior(x, lam, pr)
                    for t in range(T):
                        ours = m.posterior[k, t]; r_ = ref[t]
                        md = max(md, float(np.abs(ours[:len(r_)] - r_).max()), float(ours[len(r_):].sum()))
            cmp[f"{pn}|lam={lam}"] = md
    out["max_abs_posterior_difference"] = cmp
    # ---- reference response speed (default prior, lam 39), up vs down
    resp = {}
    for dname, xs in sess.items():
        first = []
        for x in xs:
            ref = reference_posterior(x, 39, priors["default (0,1,1,1)"]); p3 = np.array([P_[:3].sum() for P_ in ref])
            hit = np.where(p3[J:] >= 0.5)[0]; first.append(int(hit[0]) if len(hit) else None)
        resp[dname] = first
    out["reference_updates_after_change_until_P(r<=2)>=0.5"] = resp
    out["analytic_KL_nats_per_update"] = dict(up_10x=0.5 * (R - 1 - np.log(R)), down_10x=0.5 * (1 / R - 1 + np.log(R)))
    # ---- (2) detection by prior and lambda (Gaussian, R=10, D4 maxhit rule)
    rg = lambda role: np.random.default_rng([role, 99, R])
    r1 = rg(2); cal = [D.seq(z(D.gen(r1, "gaussian", "calm", R))) for _ in range(500)]
    r2 = rg(3); tn = [D.seq(z(D.gen(r2, "gaussian", "calm", R))) for _ in range(500)]
    mk = lambda role, kind: (lambda g_: [(lambda j: D.seq(z(D.gen(g_, "gaussian", kind, R, j)), j=j))(int(g_.integers(20, 61))) for _ in range(500)])(rg(role))
    cu, cd, tu, td = mk(6, "up"), mk(7, "down"), mk(4, "up"), mk(5, "down")
    det = {}
    for pn, pr in priors.items():
        for lam in (12, 39, 78):
            m = M.BOCPD(lam, prior=pr); rr = {nm: V_run(m, ss) for nm, ss in (("cal", cal), ("tn", tn), ("tu", tu), ("td", td), ("cu", cu), ("cd", cd))}
            for kind, grid in (("a_pcp3", D.PROB_GRID), ("b_map", D.DROP_GRID), ("c_r_lt_6", D.PROB_GRID)):
                feas = [g_ for g_ in grid if D.null_stats(kind, rr["cal"], cal, g_)[0] <= 0.10]
                if not feas: det[f"{pn}|lam={lam}|{kind}"] = dict(feasible=False); continue
                ch = {g_: (D.break_stats(kind, rr["cu"], cu, g_)[0] + D.break_stats(kind, rr["cd"], cd, g_)[0]) / 2 for g_ in feas}
                thr = max(feas, key=lambda g_: (ch[g_], -grid.index(g_))); fa, p20 = D.null_stats(kind, rr["tn"], tn, thr)
                hu, du = D.break_stats(kind, rr["tu"], tu, thr); hd, dd = D.break_stats(kind, rr["td"], td, thr)
                det[f"{pn}|lam={lam}|{kind}"] = dict(feasible=True, threshold=thr, test_fa=fa, per20=p20, hit_up=hu, hit_down=hd, delay_up=du, delay_down=dd)
    out["detection_gaussian_R10"] = det
    (L.HERE / "results" / "d5a_results.json").write_text(json.dumps(out, indent=1, default=float))
    print("max abs posterior difference (all priors, lambdas):", max(cmp.values())); print(json.dumps(out["reference_updates_after_change_until_P(r<=2)>=0.5"]))
    for k, v in det.items():
        if v.get("feasible"): print(k, {a: (round(b, 2) if isinstance(b, float) else b) for a, b in v.items() if a in ("threshold", "test_fa", "hit_up", "hit_down")})


def V_run(m, seqs):
    import s5_eval as V
    return V.run_filter("bocpd", m, seqs, 1)


if __name__ == "__main__":
    main()
