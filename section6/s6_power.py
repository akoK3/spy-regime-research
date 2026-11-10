#!/usr/bin/env python3
"""AMENDMENT_A28 rule 6d: power check from SPY break counts only. Reads section5/results/breaks/breaks.csv (SPY detector output on the development test segments) for one
detector: the confirmed calm-to-stressed breaks (after the 60-session burn-in is not knowable without the panel's session index: all breaks are used, an upper bound),
the fizzled calm-to-stressed runs, and their calendar-week / era structure. No asset outcome is read; outcomes are simulated:
  H3: y = gamma * break + u_week + e, u_week ~ N(0, 0.3^2), e ~ N(0, 1), 20 placebos per break on the same week structure; gamma in residual-SD units.
  H4: label ~ Bernoulli(logistic(a + b * C)), C = share of 4 assets beyond their placebo 90th percentile, simulated as Binomial(4, 0.1)/4 under no effect, base rate 0.3;
      the AUC gain of adding C is the effect size reported for each b; under AMENDMENT_A29 rule 1 it is the out-of-fold gain (5 calendar-week folds within era).
Each simulated data set is tested exactly as in s6_run (week-block bootstrap within era, centred, add-one) with NBOOT_POWER resamples. Power = share of data sets with p below
the first Holm step (0.05 / 6). The minimum detectable effect is the smallest grid value with power >= 0.80. Assumptions (the 0.3 week SD, the 0.3 base rate) are this
script's, stated here before any development result.  Usage: s6_power.py DETECTOR [--sims N] [--nboot N]   Output: section6/results/power_DETECTOR.json"""
import sys, csv, json, datetime, hashlib
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE))
import s6_lib as L

BREAKS = ROOT / "section5" / "results" / "breaks" / "breaks.csv"; ALPHA1 = 0.05 / 6; WEEK_SD = 0.3; BASE = 0.3; NBOOT_POWER = 999; SIMS = 200
G_GRID = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.6); B_GRID = (0.5, 1.0, 1.5, 2.0, 3.0, 4.0)


def structure(detector, path=BREAKS):
    rows = [x for x in csv.DictReader(open(path, encoding="utf-8")) if x["family"] == detector and x["direction"] == "calm_to_stressed"]
    br = [(x["day"], x["era"]) for x in rows if x["kind"] == "confirmed"]; fz = [(x["day"], x["era"]) for x in rows if x["kind"] == "fizzle"]; return br, fz


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
    g, p, _ = L.week_block_bootstrap(lambda ix: L.auc_gain_cv(X[ix], C[ix], y[ix], folds[ix]), days, eras, nboot, int(rng.integers(1 << 30))); return p, g


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    det = sys.argv[1]; sims = int(sys.argv[sys.argv.index("--sims") + 1]) if "--sims" in sys.argv else SIMS; nboot = int(sys.argv[sys.argv.index("--nboot") + 1]) if "--nboot" in sys.argv else NBOOT_POWER
    br, fz = structure(det); rng = np.random.default_rng(6); res = dict(detector=det, n_breaks=len(br), n_fizzles=len(fz), n_weeks=len({L.week_of(d) for d, _ in br}), alpha_first_holm_step=ALPHA1, sims=sims, nboot=nboot)
    res["H3"] = {str(g): float(np.mean([sim_h3(br, g, rng, nboot) <= ALPHA1 for _ in range(sims)])) for g in G_GRID}
    for name, units in (("H4a", br + fz), ("H4b", br)):
        out = {}
        for b in B_GRID:
            r = [sim_h4(units, b, rng, nboot) for _ in range(sims)]; out[str(b)] = dict(power=float(np.mean([p <= ALPHA1 for p, _ in r])), mean_auc_gain=float(np.nanmean([g for _, g in r])))
        res[name] = out
    res["mde"] = dict(H3_gamma_sd_units=next((g for g in G_GRID if res["H3"][str(g)] >= 0.8), None),
                      **{f"{k}_auc_gain": next((res[k][str(b)]["mean_auc_gain"] for b in B_GRID if res[k][str(b)]["power"] >= 0.8), None) for k in ("H4a", "H4b")})
    res.update(generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), breaks_sha256=hashlib.sha256(BREAKS.read_bytes()).hexdigest(), assumptions=dict(week_sd=WEEK_SD, base_rate=BASE))
    (HERE / "results").mkdir(exist_ok=True); (HERE / "results" / f"power_{det}.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res["mde"])); return 0


if __name__ == "__main__": sys.exit(main())
