#!/usr/bin/env python3
"""Section 6 synthetic validation (user request 2026-11-09, item 5; rerun under AMENDMENT_A29 rule 2 with the out-of-fold H4 statistic: --tag a29). Synthetic data only: no panel, break file or asset outcome is read.
Each replicate builds a synthetic LEGACY era (1,500 sessions from 2004) and RAW era (450 sessions from 2022) of one-minute returns for SPY and the four assets, synthetic
detector runs, and passes them through the real Section 6 code: s6_run.build -> attach_placebos -> primary (the 6-test Holm family: H3 next-day per asset, H4a, H4b),
with the week-block bootstrap of s6_lib. Nothing in s6_lib / s6_run is changed or monkey-patched.

Data generator (per era): daily log-volatility h = AR(1) (phi 0.9) with a factor shared by SPY and the assets (loading 0.6) plus a calendar-week shock; one-minute
returns = Student-t(5), scaled to sd sigma_asset * exp(h) * U-shape(minute); coverage like the real panel (assets unavailable in the first 20% of LEGACY, DOLLAR only in
its last 10%; 5% random unavailable sessions elsewhere); unavailable sessions are NaN. Runs: per session one run with probability p_run, S on the 5-minute grid of
15..330, confirmed with probability 0.55 (T = S + 10), else fizzled; calm_to_stressed with probability 0.75.
  null "indep":  p_run = 0.3 for every session.
  null "vol":    p_run = 0.3 * exp(h_SPY - mean) capped at 0.9: runs cluster on high-volatility days (the confounding the placebo matching and controls must absorb).
Planted effects, on top of the "vol" generator, in two separate scenarios (an H4 move inside the hour before T also enters H3's prior-hour RV control, so planting
both in one data set biases H3 by design; observed in the smoke test, H3 gamma came out negative):
  effect_h3: the next session's returns of asset a are multiplied by exp(gamma_a / 2) after every confirmed calm-to-stressed break (burn-in passed), so its log RV rises by
      gamma_a: TLT 0.30, HYG 0.15, GOLD 0.30, DOLLAR 0.00 (DOLLAR: planted null inside the effect scenario).
  effect_h4: a share q = 0.4 of the confirmed calm-to-stressed breaks (z = 1) get, in every available asset, one 40-sd one-minute move (15 sd left C < 1 for about 40% of planted units, because placebo sessions can be up to ~3x more volatile) in the 15 minutes before S (C at S) and one
      inside (S, T] (C at T = 0), and the next session's SPY returns times 3 (a real break by the 4d label). Fizzles never get moves.
  Target sizes: H4a / H4b target = the AUC gain (s6_lib.auc_gain, the same function and the same SPY covariates and labels of the replicate) of the ORACLE score: C = 1
  for planted units, a draw from the replicate's own non-planted C values otherwise; mean over 50 draws. It shows what the test should estimate if C is computed
  correctly; the covariate-only model's in-sample AUC and the SPY information in the real-break label are then the same in target and estimate. Also reported:
  AUC(oracle) - 0.5 (no covariates). H3 target = gamma_a times (1 - the share of placebo rows whose next session
  was also scaled), the attenuation from placebos sharing a scaled session.
Output: section6/results/synth_validation[_TAG].json (+ _reps[_TAG].jsonl).  Usage: s6_synth_validation.py [--null-reps N] [--effect-reps N] [--nboot N] [--workers N] [--tag TAG]"""
import sys, json, time, datetime, hashlib
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R

ASSETS = R.ASSETS; SIG = dict(SPY=1.0e-3, TLT=0.6e-3, HYG=0.4e-3, GOLD=0.8e-3, DOLLAR=0.3e-3)
GAMMA = dict(TLT=0.30, HYG=0.15, GOLD=0.30, DOLLAR=0.00); Q = 0.4; JUMP_SD = 40.0; SPY_NEXT = 3.0
U = 1.0 + 0.8 * ((np.arange(L.N_MIN) - 195) / 195.0) ** 2; U /= np.sqrt(np.mean(U ** 2))


class SynthEra(R.EraData):
    def __init__(self, era, days, R_, avail):
        self.era = era; self.days = days; self.ix = {d: i for i, d in enumerate(days)}; self.R = R_; self.avail = avail; self.drv = L.deseasonalised_rv(self.R["SPY"])


def gen_era(era, n, start, rng, scenario):
    days = [str(d.date()) for d in pd.bdate_range(start, periods=n)]; wk = np.array([L.week_of(d) for d in days]); uw, wi = np.unique(wk, return_inverse=True)
    wshock = rng.normal(0, 0.25, len(uw))[wi]; common = np.zeros(n); e = rng.normal(0, 0.3, n)
    for t in range(1, n): common[t] = 0.9 * common[t - 1] + e[t]
    H = {}
    for a in ("SPY",) + ASSETS:
        idio = np.zeros(n); ei = rng.normal(0, 0.2, n)
        for t in range(1, n): idio[t] = 0.9 * idio[t - 1] + ei[t]
        H[a] = 0.6 * common + idio + 0.6 * wshock
    R_ = {a: (rng.standard_t(5, (n, L.N_MIN)) / np.sqrt(5 / 3)) * (SIG[a] * np.exp(H[a]))[:, None] * U[None, :] for a in ("SPY",) + ASSETS}
    avail = {}
    for a in ASSETS:
        av = rng.random(n) > 0.05
        if era == "LEGACY": av[: int(0.2 * n)] = False
        if era == "LEGACY" and a == "DOLLAR": av[: int(0.9 * n)] = False
        avail[a] = av; R_[a][~av] = np.nan
    if scenario == "indep": p = np.full(n, 0.3)
    else: p = np.minimum(0.3 * np.exp(H["SPY"] - H["SPY"].mean()), 0.9)
    rows = []
    for i in np.flatnonzero(rng.random(n) < p):
        S = int(rng.integers(3, 67)) * 5; conf = rng.random() < 0.55; dirn = "calm_to_stressed" if rng.random() < 0.75 else "stressed_to_calm"
        rows.append(dict(fold=f"{era}|0", era=era, family="synth", day=days[i], kind="confirmed" if conf else "fizzle", S_min=S, T0_min=S + 10 if conf else None, end_min=S + 5, direction=dirn))
    return days, R_, avail, rows


def plant(E, rows, rng, scenario):
    """Effects of the 'effect' scenario, written into E.R before the pipeline runs; returns the planted flags per (era, day, S, kind)."""
    z = {}; scaled = {a: set() for a in ASSETS}
    if not scenario.startswith("effect"): return z, scaled
    br = [x for x in rows if x["kind"] == "confirmed" and x["direction"] == "calm_to_stressed" and E.ix[x["day"]] >= L.BURN_IN]
    for x in br:
        di = E.ix[x["day"]]; S = x["S_min"]; T = x["T0_min"]
        if scenario == "effect_h3" and di + 1 < len(E.days):
            for a in ASSETS:
                if GAMMA[a] and (di + 1) not in scaled[a]: E.R[a][di + 1] *= np.exp(GAMMA[a] / 2); scaled[a].add(di + 1)
        if scenario != "effect_h4": continue
        zz = rng.random() < Q; z[(E.era, x["day"], S, "confirmed")] = zz
        if zz:
            for a in ASSETS:
                if not E.avail[a][di]: continue
                sd = np.nanstd(E.R[a][di]); E.R[a][di, int(rng.integers(S - 15, S))] += rng.choice([-1, 1]) * JUMP_SD * sd; E.R[a][di, int(rng.integers(S, T))] += rng.choice([-1, 1]) * JUMP_SD * sd
            if di + 1 < len(E.days): E.R["SPY"][di + 1] *= SPY_NEXT
    E.drv = L.deseasonalised_rv(E.R["SPY"])
    return z, scaled


def oracle_gain(zs, labels, f0, X, rng, draws=50, folds=None):
    """Target: the H4 statistic of s6_run.h4_test (A29: out-of-fold auc_gain_cv on the same week folds; A28: in-sample auc_gain) of the oracle score, oracle = 1 if z else
    a draw from F0 (the replicate's own non-planted C values); mean over draws. Also AUC(oracle) - 0.5."""
    zs = np.asarray(zs, bool); y = np.asarray(labels, float); f0 = np.asarray(f0, float); f0 = f0[np.isfinite(f0)]; X = np.asarray(X, float)
    gain = (lambda c: L.auc_gain(X, c, y)) if folds is None else (lambda c: L.auc_gain_cv(X, c, y, folds))
    if len(f0) == 0 or len(np.unique(y)) < 2: return np.nan, np.nan
    if not zs.any(): return 0.0, 0.0
    o = [np.where(zs, 1.0, rng.choice(f0, len(zs))) for _ in range(draws)]
    return float(np.nanmean([gain(c) for c in o])), float(np.mean([L.auc(c, y) for c in o]) - 0.5)


def replicate(args):
    scenario, rep, nboot = args; t0 = time.time()
    seed = int(hashlib.sha256(f"synth|{scenario}|{rep}".encode()).hexdigest()[:8], 16); rng = np.random.default_rng(seed)
    E_by, rows_all, sess, zmap, scaled_by = {}, [], {}, {}, {}
    for era, n, start in (("LEGACY", 1500, "2004-01-02"), ("RAW", 450, "2022-03-07")):
        days, R_, avail, rows = gen_era(era, n, start, rng, scenario); E = SynthEra(era, days, R_, avail)
        z, sc = plant(E, rows, rng, scenario); zmap.update(z); scaled_by[era] = sc; E_by[era] = E; rows_all += rows; sess[f"{era}|0"] = days
    units = []
    for era, E in E_by.items():
        u, c, al = R.build(E, [x for x in rows_all if x["era"] == era], sess); units += R.attach_placebos(u, c, al)
    for u in units: u["fed"] = False
    res, br, runs = R.primary(E_by, units, nboot, seed=rep)
    out = dict(scenario=scenario, rep=rep, seconds=None, n_breaks=len(br), n_runs=len(runs), tests={k: dict(est=(v.get("gamma") if k.startswith("H3") else v.get("gain")), p=v.get("p"), p_holm=v.get("p_holm"), est_in_sample=v.get("gain_in_sample_descriptive")) for k, v in res.items()})
    if scenario.startswith("effect"):
        tg = {}
        for a in ASSETS:     # H3 attenuation: placebo rows whose next session was scaled
            pl = [(u["era"], p["day_idx"] + 1) for u in br for p in u["placebos"] if E_by[u["era"]].avail[a][p["day_idx"]]]
            share = float(np.mean([d in scaled_by[e][a] for e, d in pl])) if pl else np.nan; g = GAMMA[a] if scenario == "effect_h3" else 0.0; tg[f"H3_{a}"] = dict(planted=g, placebo_scaled_share=share, target=g * (1 - share))
        key = lambda u: (u["era"], u["day"], u["S"], u["kind"])
        for name, us, point, lab in (("H4a", runs, "S", lambda u: float(u["kind"] == "confirmed")), ("H4b", br, "T0", R.real_fn(E_by))):
            zs, ys, cs, Xs, ds, es = [], [], [], [], [], []
            for u in us:
                l = lab(u); c = R.c_score(E_by, u, point); x = R.spy_info(E_by[u["era"]], u, point)
                if np.isfinite(l) and np.isfinite(c) and np.isfinite(x).all(): zs.append(bool(zmap.get(key(u), False))); ys.append(l); cs.append(c); Xs.append(x); ds.append(u["day"]); es.append(u["era"])
            f0 = [c for c, zz in zip(cs, zs) if not zz]; c1 = [c for c, zz in zip(cs, zs) if zz]; t, t0_ = oracle_gain(zs, ys, f0, Xs, rng, folds=L.cv_folds(ds, es))
            tg[name] = dict(target=t, oracle_auc_minus_half=t0_, share_planted_with_C1=float(np.mean(np.isclose(c1, 1.0))) if c1 else None,
                            label_rate_planted=float(np.mean([y for y, zz in zip(ys, zs) if zz])) if c1 else None, label_rate_other=float(np.mean([y for y, zz in zip(ys, zs) if not zz])))
        out["targets"] = tg
    out["seconds"] = round(time.time() - t0, 1); return out


def summarise(reps):
    s = {}
    for sc in sorted({r["scenario"] for r in reps}):
        rr = [r for r in reps if r["scenario"] == sc]; d = dict(n_reps=len(rr), mean_breaks=float(np.mean([r["n_breaks"] for r in rr])), mean_runs=float(np.mean([r["n_runs"] for r in rr])), tests={})
        for k in rr[0]["tests"]:
            ps = np.array([r["tests"][k]["p"] for r in rr if r["tests"][k]["p"] is not None], float); est = np.array([r["tests"][k]["est"] for r in rr if r["tests"][k]["est"] is not None], float)
            t = dict(n=len(ps), reject_raw_0_05=float(np.mean(ps <= 0.05)) if len(ps) else None, reject_holm_0_05=float(np.mean([r["tests"][k].get("p_holm") is not None and r["tests"][k]["p_holm"] <= 0.05 for r in rr])),
                     mc_se=float(np.sqrt(0.05 * 0.95 / max(len(ps), 1))), est_mean=float(est.mean()) if len(est) else None, est_sd=float(est.std(ddof=1)) if len(est) > 1 else None,
                     est_in_sample_mean=float(np.nanmean([r["tests"][k]["est_in_sample"] for r in rr if r["tests"][k].get("est_in_sample") is not None])) if any(r["tests"][k].get("est_in_sample") is not None for r in rr) else None)
            if sc.startswith("effect"):
                tg = np.array([r["targets"][k]["target"] for r in rr], float); t.update(target_mean=float(np.nanmean(tg)), bias=float(np.nanmean(est - tg[: len(est)])) if len(est) == len(tg) else None,
                                                                                        bias_se=float(np.nanstd(est - tg, ddof=1) / np.sqrt(len(est))) if len(est) == len(tg) and len(est) > 1 else None)
                for extra in ("planted", "placebo_scaled_share", "oracle_auc_minus_half", "share_planted_with_C1", "label_rate_planted", "label_rate_other"):
                    v = [r["targets"][k].get(extra) for r in rr if r["targets"][k].get(extra) is not None]
                    if v: t[extra] = float(np.mean(v))
            d["tests"][k] = t
        d["family_wise_any_holm_reject"] = float(np.mean([any(r["tests"][k].get("p_holm") is not None and r["tests"][k]["p_holm"] <= 0.05 for k in r["tests"]) for r in rr]))
        s[sc] = d
    return s


def main():
    arg = lambda k, dflt: int(sys.argv[sys.argv.index(k) + 1]) if k in sys.argv else dflt
    nnull, neff, nboot, workers = arg("--null-reps", 200), arg("--effect-reps", 40), arg("--nboot", 999), arg("--workers", 4)
    jobs = [(sc, i, nboot) for sc in ("indep", "vol") for i in range(nnull)] + [(sc, i, nboot) for sc in ("effect_h3", "effect_h4") for i in range(neff)]
    tag = ("_" + sys.argv[sys.argv.index("--tag") + 1]) if "--tag" in sys.argv else ""
    out_p = HERE / "results" / f"synth_validation{tag}.json"; out_p.parent.mkdir(exist_ok=True); part = HERE / "results" / f"synth_validation_reps{tag}.jsonl"
    done = {}
    if part.exists():
        for line in part.read_text(encoding="utf-8").splitlines():
            r = json.loads(line); done[(r["scenario"], r["rep"])] = r
    todo = [j for j in jobs if (j[0], j[1]) not in done]; t0 = time.time(); print(f"{len(todo)} replicates to run ({len(done)} done); nboot {nboot}; workers {workers}", flush=True)
    import multiprocessing as mp
    with mp.Pool(workers) as pool, open(part, "a", encoding="utf-8") as f:
        for k, r in enumerate(pool.imap_unordered(replicate, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); done[(r["scenario"], r["rep"])] = r
            if k % 10 == 0 or k == len(todo): print(f"{k}/{len(todo)} {time.time() - t0:.0f} s", flush=True)
    reps = [done[(j[0], j[1])] for j in jobs]
    res = dict(label="Section 6 synthetic validation (synthetic data only; s6_run.primary as on disk; H4 statistic per AMENDMENT_A29 rule 1 when tagged a29)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), nboot=nboot,
               planted=dict(gamma=GAMMA, q=Q, jump_sd=JUMP_SD, spy_next_day_factor=SPY_NEXT), code_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in (HERE / "s6_lib.py", HERE / "s6_run.py", Path(__file__))},
               summary=summarise(reps))
    res["provenance"] = R.provenance(); R.write_once(out_p, res); print(json.dumps(res["summary"], indent=1)); return 0


if __name__ == "__main__": sys.exit(main())
