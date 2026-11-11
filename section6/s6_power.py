#!/usr/bin/env python3
"""AMENDMENT_A28 rule 6d: power check from SPY break counts only. Reads section5/results/breaks/breaks.csv (SPY detector output on the development test segments) for one
detector: the confirmed calm-to-stressed breaks (after the 60-session burn-in is not knowable without the panel's session index: all breaks are used, an upper bound),
the fizzled calm-to-stressed runs, and their calendar-week / era structure. No asset outcome is read; outcomes are simulated:
  H3: y = gamma * break + u_week + e, u_week ~ N(0, 0.3^2), e ~ N(0, 1), 20 placebos per break on the same week structure; gamma in residual-SD units.
  H4: label ~ Bernoulli(logistic(a + b * C)), C = share of 4 assets beyond their placebo 90th percentile, simulated as Binomial(4, 0.1)/4 under no effect, base rate 0.3;
      the AUC gain of adding C is the effect size reported for each b; under AMENDMENT_A29 rule 1 it is the out-of-fold gain (5 calendar-week folds within era).
Each simulated data set is tested exactly as in s6_run (week-block bootstrap within era, centred, add-one) with NBOOT_POWER resamples. Power = share of data sets with p below
the first Holm step (0.05 / 6); H4 uses the AMENDMENT_A29 out-of-fold statistic and the AMENDMENT_A31 H4a units. The minimum detectable effect is the smallest grid value with power >= 0.80. Assumptions (the 0.3 week SD, the 0.3 base rate) are this
script's, stated here before any development result.  Usage: s6_power.py DETECTOR [--sims N] [--nboot N] [--workers N]   Output: section6/results/power_DETECTOR.json"""
import sys, csv, json, datetime, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE))
import s6_lib as L

BREAKS = ROOT / "section5" / "results" / "breaks" / "breaks.csv"; ALPHA1 = 0.05 / 6; WEEK_SD = 0.3; BASE = 0.3; NBOOT_POWER = 999; SIMS = 200
G_GRID = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6); B_GRID = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def structure(detector, path=BREAKS):
    """H3 / H4b: confirmed calm-to-stressed breaks. H4a (AMENDMENT_A31 rule 2): every calm-state streak start (old_state 0), any outcome. (day, era) pairs."""
    rows = [x for x in csv.DictReader(open(path, encoding="utf-8")) if x["family"] == detector]
    br = [(x["day"], x["era"]) for x in rows if x["kind"] == "confirmed" and x["direction"] == "calm_to_stressed"]
    h4a = [(x["day"], x["era"]) for x in rows if str(x.get("old_state")) == "0" and x["kind"] in ("confirmed", "fizzle", "open_at_close")]; return br, h4a


def _task(t):
    """One simulated data set (worker-pool task); its seed is fixed by (test, grid value, simulation index)."""
    name, g, i, units, nboot = t; rng = np.random.default_rng(int(hashlib.sha256(f"power|{name}|{g}|{i}".encode()).hexdigest()[:8], 16))
    return (name, g, sim_h3(units, g, rng, nboot), None) if name == "H3" else (name, g) + sim_h4(units, g, rng, nboot)


def sim_h3(br, gamma, rng, nboot):
    days, eras, b = [], [], []
    for d, e in br: days += [d] * (1 + L.N_PLACEBO); eras += [e] * (1 + L.N_PLACEBO); b += [1] + [0] * L.N_PLACEBO
    b = np.array(b, float); wk = {w: rng.normal(0, WEEK_SD) for w in {L.week_of(d) for d in days}}
    y = gamma * b + np.array([wk[L.week_of(d)] for d in days]) + rng.normal(0, 1, len(b)); X = rng.normal(0, 1, (len(b), 4))
    return L.week_block_bootstrap(lambda ix: L.ols_gamma(y[ix], X[ix], b[ix]), days, eras, nboot, int(rng.integers(1 << 30)))[1]


def sim_h4(units, beta, rng, nboot):
    days = [d for d, _ in units]; eras = [e for _, e in units]; n = len(units)
    C = rng.binomial(4, 0.1, n) / 4; X = rng.normal(0, 1, (n, 2)); a = np.log(BASE / (1 - BASE)) - beta * C.mean(); y = (rng.random(n) < 1 / (1 + np.exp(-(a + beta * C + 0.3 * X[:, 0])))).astype(float)
    folds = L.cv_folds(days, eras)
    g, p, _, _ = L.week_block_bootstrap(lambda ix: L.auc_gain_cv(X[ix], C[ix], y[ix], folds[ix]), days, eras, nboot, int(rng.integers(1 << 30)), valid_only=True); return p, g      # AMENDMENT_A35 rule 1 (1f: power not rerun)


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    det = sys.argv[1]; sims = int(sys.argv[sys.argv.index("--sims") + 1]) if "--sims" in sys.argv else SIMS; nboot = int(sys.argv[sys.argv.index("--nboot") + 1]) if "--nboot" in sys.argv else NBOOT_POWER
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 1
    br, h4a = structure(det); res = dict(detector=det, n_breaks=len(br), n_h4a_units=len(h4a), n_weeks=len({L.week_of(d) for d, _ in br}), alpha_first_holm_step=ALPHA1, sims=sims, nboot=nboot,
                                         h4a_units="A31 rule 2: every calm-state streak start (old_state 0), any outcome", note="all development breaks, no burn-in: an upper bound on the sample")
    tasks = [("H3", g, i, br, nboot) for g in G_GRID for i in range(sims)] + [(n, b, i, u, nboot) for n, u in (("H4a", h4a), ("H4b", br)) for b in B_GRID for i in range(sims)]
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(workers) as pool: out = pool.map(_task, tasks, chunksize=4)
    else: out = [_task(t) for t in tasks]
    res["H3"] = {str(g): float(np.mean([p <= ALPHA1 for n, gg, p, _ in out if n == "H3" and gg == g])) for g in G_GRID}
    for name in ("H4a", "H4b"):
        res[name] = {str(b): dict(power=float(np.mean([p <= ALPHA1 for n, bb, p, _ in out if n == name and bb == b])), mean_auc_gain=float(np.nanmean([gn for n, bb, _, gn in out if n == name and bb == b]))) for b in B_GRID}
    res["mde"] = dict(H3_gamma_sd_units=next((g for g in G_GRID if res["H3"][str(g)] >= 0.8), None),
                      **{f"{k}_auc_gain": next((res[k][str(b)]["mean_auc_gain"] for b in B_GRID if res[k][str(b)]["power"] >= 0.8), None) for k in ("H4a", "H4b")})
    res.update(generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), breaks_sha256=hashlib.sha256(BREAKS.read_bytes()).hexdigest(), assumptions=dict(week_sd=WEEK_SD, base_rate=BASE))
    import s6_run as R
    res["provenance"] = R.provenance(); R.write_once(HERE / "results" / f"power_{det}.json", res); print(json.dumps(res["mde"])); return 0


if __name__ == "__main__": sys.exit(main())
