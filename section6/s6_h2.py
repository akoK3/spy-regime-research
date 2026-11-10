#!/usr/bin/env python3
"""H2 per AMENDMENT_A32: per asset, mean deseasonalised |return| over (T, T + h] after confirmed calm-to-stressed SPY breaks minus the break's A31 placebos; one-sided
week-block bootstrap within era (A28 3c); primary h = 30 with its own Holm family of 4 (m = 4 always); secondary h = 5, 15, 60 and S2 (other detectors) under BH;
descriptive (T - 30, T]; E1 footprint taxonomy (descriptive); S1 covered by H4a and A30; E2 deferred (rule 4d).
Units and placebos: s6_run.build / attach_placebos / unit_lists (A28 1, A31 rule 1), unchanged. Data: development only, through s6_run.load_era.
Usage:
  s6_h2.py synth --tag TAG [--null-reps 200] [--effect-reps 40] [--nboot 999] [--workers 6]   (A32 5a; synthetic data only)
  s6_h2.py check TAG                                                                          (A32 5a acceptance; exit 1 if any criterion fails)
  s6_h2.py power DETECTOR [--sims 200] [--nboot 999] [--workers 3]                              (A32 5b; break structure only, no outcome read)
  s6_h2.py development DETECTOR [--nboot 9999]                                                (A32 6b; refuses unless A28-A32 are ADOPTED)
No freeze, no O8, no era calibration, no evaluation-period read."""
import sys, json, csv, time, hashlib, datetime, collections
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R

ASSETS = R.ASSETS; PRIOR = 20; MIN_PRIOR = 10; MIN_PLACEBO = 10; PCT = 90; ALPHA1 = 0.05 / 4
WINDOWS = {"h5": (0, 5), "h15": (0, 15), "h30": (0, 30), "h60": (0, 60), "pre30": (-30, 0)}
AMENDMENTS = ("A28", "A29", "A30", "A31", "A32")
K_PLANT = dict(TLT=1.3, HYG=1.15, GOLD=1.3, DOLLAR=1.0); WEEK_SD = 0.3; D_GRID = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4)


# ---------- A32 rule 2: deseasonalised |return|
def _pref(E, a):
    """Per-asset prefix sums over minutes (width 391): squared returns, counts, returns (NaN as 0). Cached on E; drop E._h2 after changing E.R."""
    c = E.__dict__.setdefault("_h2", {})
    if a not in c:
        X = E.R[a]; ok = np.isfinite(X); z = np.where(ok, X, 0.0); pad = lambda M: np.concatenate([np.zeros((len(M), 1), M.dtype), np.cumsum(M, 1)], 1)
        c[a] = (pad(z ** 2), pad(ok.astype(np.int64)), pad(z))
    return c[a]


def dz(E, a, di, t0, t1):
    """|r| / sqrt(m) over (t0, t1] of session di; m = median realised variance over the same window in the asset's previous 20 sessions with data (>= 10). NaN if undefined."""
    if t0 < 0 or t1 > L.N_MIN or t1 <= t0 or not E.avail[a][di]: return np.nan
    Q, N, C = _pref(E, a)
    if N[di, t1] - N[di, t0] == 0: return np.nan
    rows = np.arange(max(0, di - PRIOR), di); rows = rows[E.avail[a][rows] & ((N[rows, t1] - N[rows, t0]) > 0)]
    if len(rows) < MIN_PRIOR: return np.nan
    m = float(np.median(Q[rows, t1] - Q[rows, t0]))
    return abs(float(C[di, t1] - C[di, t0])) / np.sqrt(m) if m > 0 else np.nan


def contrib(E_by, u, a, lo, hi):
    """A32 2c: d(break) - mean d(placebos), window (T + lo, T + hi]; NaN unless d(break) is defined and >= 10 placebo values exist."""
    E = E_by[u["era"]]; db = dz(E, a, u["day_idx"], u["T"] + lo, u["T"] + hi)
    if not np.isfinite(db): return np.nan, np.nan, np.nan
    pv = np.array([dz(E, a, p["day_idx"], p["T"] + lo, p["T"] + hi) for p in u.get("placebos", [])], float); pv = pv[np.isfinite(pv)]
    if len(pv) < MIN_PLACEBO: return np.nan, np.nan, np.nan
    return db - pv.mean(), db, pv.mean()


def h2_test(E_by, br, a, lo, hi, nboot=L.NBOOT, seed=0):
    """A32 3a-3b: G = mean contribution over breaks; one-sided centred week-block bootstrap (s6_lib.week_block_bootstrap; breaks resampled with their placebos)."""
    c, db, dp, days, eras = [], [], [], [], []
    for u in br:
        x, b, p = contrib(E_by, u, a, lo, hi)
        if np.isfinite(x): c.append(x); db.append(b); dp.append(p); days.append(u["day"]); eras.append(u["era"])
    out = dict(n_breaks=len(c), window=[lo, hi], mean_d_break=(float(np.mean(db)) if db else None), mean_d_placebo=(float(np.mean(dp)) if dp else None))
    if len(c) < 5: return dict(out, G=None, p=None)
    c = np.array(c)
    if nboot == 0: return dict(out, G=float(c.mean()), p=None, label="descriptive, not tested")
    g, p, nv = L.week_block_bootstrap(lambda ix: float(c[ix].mean()), days, eras, nboot, seed)
    return dict(out, G=g, p=p, n_valid_resamples=nv)


def holm4(res):
    """H2's own Holm family (5.11): m = 4 always; a non-evaluable test enters with p = 1 (A15 rule 6a)."""
    keys = [f"H2_{a}" for a in ASSETS]; used = [res[k]["p"] if res[k].get("p") is not None and np.isfinite(res[k]["p"]) else 1.0 for k in keys]; adj = L.holm(used)
    for k, pu, q in zip(keys, used, adj):
        ev = res[k].get("p") is not None and np.isfinite(res[k]["p"]); res[k].update(p_used=float(pu), evaluable=bool(ev), holm_m=4, p_holm=float(q), **{"reject_0.05": bool(ev and q <= 0.05)})
    return res


def h2_primary(E_by, br, nboot=L.NBOOT, seed=0):
    return holm4({f"H2_{a}": h2_test(E_by, br, a, *WINDOWS["h30"], nboot, seed) for a in ASSETS})


# ---------- A32 rule 4c: E1 footprint taxonomy
def move(E, a, di, t0, t1, ref):
    """+1 / -1 if |r| over (t0, t1] exceeds the 90th percentile of |r| over the reference windows (>= 10 values), 0 if not; None if not evaluable."""
    if t1 > L.N_MIN or not E.avail[a][di]: return None
    _, N, C = _pref(E, a)
    if N[di, t1] - N[di, t0] == 0: return None
    pv = [abs(C[d, b] - C[d, s]) for d, s, b in ref if b <= L.N_MIN and E.avail[a][d] and N[d, b] - N[d, s] > 0]
    if len(pv) < MIN_PLACEBO: return None
    r = float(C[di, t1] - C[di, t0]); return (1 if r > 0 else -1) if abs(r) > np.percentile(pv, PCT) else 0


def classify(m):
    t, h, u = m.get("TLT"), m.get("HYG"), m.get("DOLLAR")
    if t == 1 and h == -1: return "flight_to_safety"
    if h == -1: return "credit_stress"
    if u == 1: return "dollar_driven"
    if all(v in (0, None) for v in m.values()): return "spy_only"
    return "other"


CATS = ("flight_to_safety", "credit_stress", "dollar_driven", "spy_only", "other")


def e1(E_by, br, h=30):
    cb, cp = collections.Counter(), collections.Counter(); skipped = dict(window_past_close=0, tlt_or_hyg_not_evaluable=0)
    for u in br:
        E = E_by[u["era"]]; T = u["T"]
        if T + h > L.N_MIN: skipped["window_past_close"] += 1; continue
        ref = [(p["day_idx"], p["T"], p["T"] + h) for p in u.get("placebos", [])]
        m = {a: move(E, a, u["day_idx"], T, T + h, ref) for a in ASSETS}
        if m["TLT"] is None or m["HYG"] is None: skipped["tlt_or_hyg_not_evaluable"] += 1; continue
        cb[classify(m)] += 1
        for j, (d, s, b) in enumerate(ref):
            if b > L.N_MIN: continue
            mp = {a: move(E, a, d, s, b, ref[:j] + ref[j + 1:]) for a in ASSETS}
            if mp["TLT"] is None or mp["HYG"] is None: continue
            cp[classify(mp)] += 1
    nb, npl = sum(cb.values()), sum(cp.values())
    return dict(label="A32 rule 4c E1 footprint taxonomy (descriptive; Cieslak and Pang)", window=[0, h], n_breaks=nb, n_placebos=npl, skipped=skipped,
                breaks={k: dict(n=cb[k], share=(cb[k] / nb if nb else None)) for k in CATS}, placebos={k: dict(n=cp[k], share=(cp[k] / npl if npl else None)) for k in CATS})


# ---------- the development analysis
def units_for(E_by, rows, sess):
    units = []
    for era, E in E_by.items():
        u, c, al = R.build(E, [x for x in rows if x["era"] == era], sess); units += R.attach_placebos(u, c, al)
    return R.unit_lists(units)[0]


def analyse(E_by, rows, sess, nboot, detector, all_rows=None):
    br = units_for(E_by, rows, sess)
    res = dict(detector=detector, label="AMENDMENT_A32 H2 (development data)", n_breaks=len(br), n_breaks_by_era=dict(collections.Counter(u["era"] for u in br)))
    res["primary"] = h2_primary(E_by, br, nboot)
    res["secondary"] = {f"H2_{a}_{w}": h2_test(E_by, br, a, *WINDOWS[w], nboot) for w in ("h5", "h15", "h60") for a in ASSETS}
    res["descriptive_pre30"] = {a: h2_test(E_by, br, a, *WINDOWS["pre30"], 0) for a in ASSETS}
    if all_rows is not None:      # A32 4b (S2): every detector of the break export
        dep = {}
        for fam in R.FAMILIES: dep[fam] = h2_primary(E_by, units_for(E_by, [x for x in all_rows if x["family"] == fam], sess), nboot)
        res["detector_dependence"] = dep
        res["verdict_agreement"] = {fam: {a: dep[fam][f"H2_{a}"]["reject_0.05"] for a in ASSETS} for fam in dep}
    sec = [(k, v["p"]) for k, v in res["secondary"].items() if v.get("p") is not None and np.isfinite(v["p"])]
    sec += [(f"S2.{fam}.{k}", v["p"]) for fam, d in res.get("detector_dependence", {}).items() if fam != detector for k, v in d.items() if v.get("p") is not None and np.isfinite(v["p"])]
    adj = L.bh([p for _, p in sec]) if sec else []; res["secondary_bh"] = {k: dict(p=p, p_bh=float(q), label="secondary") for (k, p), q in zip(sec, adj)}
    res["E1"] = e1(E_by, br); res["E2"] = "deferred to future work (A32 rule 4d)"; res["S1"] = "covered by H4a (A31 rule 2) and A30 (A32 rule 4a)"
    return res


def provenance():
    import s6_fingerprint as FP, s5_amendment_manifest as AM
    return dict(code=FP.current(), amendments=AM.manifest(AMENDMENTS))


def development(det, nboot):
    if det not in R.FAMILIES[:3]: print("DETECTOR must be gaussian_hmm, student_t_hmm or hsmm"); return 3
    R.a29_guard(AMENDMENTS)
    out = R.OUT / f"h2_development_{det}.json"
    if out.exists(): print("result exists; written once"); return 3
    allrows = list(csv.DictReader(open(R.BREAKS / "breaks.csv", encoding="utf-8")))
    for x in allrows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    sess = json.loads((R.BREAKS / "sessions.json").read_text(encoding="utf-8"))
    E_by = {era: R.load_era(era, "development") for era in ("LEGACY", "RAW")}; t0 = time.time()
    res = analyse(E_by, [x for x in allrows if x["family"] == det], sess, nboot, det, allrows)
    res.update(period="development", nboot=nboot, seconds=round(time.time() - t0, 1), generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    print(f"written {R.write_once(out, res)}"); return 0


# ---------- A32 rule 5a: synthetic check
def replicate(args):
    import s6_synth_validation as V
    scenario, rep, nboot = args; t0 = time.time()
    rng = np.random.default_rng(int(hashlib.sha256(f"h2synth|{scenario}|{rep}".encode()).hexdigest()[:8], 16)); E_by, rows_all, sess = {}, [], {}
    for era, n, start in (("LEGACY", 1500, "2004-01-02"), ("RAW", 450, "2022-03-07")):
        days, R_, avail, rows = V.gen_era(era, n, start, rng, "vol" if scenario == "effect" else scenario); E_by[era] = V.SynthEra(era, days, R_, avail); rows_all += rows; sess[f"{era}|0"] = days
    br = units_for(E_by, rows_all, sess); out = dict(scenario=scenario, rep=rep, n_breaks=len(br))
    if scenario == "effect":
        base = {a: np.array([dz(E_by[u["era"]], a, u["day_idx"], u["T"], u["T"] + 30) for u in br]) for a in ASSETS}
        for u in br:
            E = E_by[u["era"]]
            for a in ASSETS:
                if K_PLANT[a] != 1.0 and E.avail[a][u["day_idx"]] and u["T"] + 30 <= L.N_MIN: E.R[a][u["day_idx"], u["T"]:u["T"] + 30] *= K_PLANT[a]
        for E in E_by.values(): E.__dict__.pop("_h2", None)
        used = {a: np.array([np.isfinite(contrib(E_by, u, a, 0, 30)[0]) for u in br], bool) for a in ASSETS}
        out["targets"] = {a: float((K_PLANT[a] - 1.0) * np.nanmean(base[a][used[a]])) if used[a].any() else None for a in ASSETS}
    res = h2_primary(E_by, br, nboot, seed=rep)
    out["tests"] = {k: dict(G=v.get("G"), p=v.get("p"), p_holm=v.get("p_holm"), n=v.get("n_breaks")) for k, v in res.items()}; out["seconds"] = round(time.time() - t0, 1)
    return out


def summarise(reps):
    s = {}
    for sc in sorted({r["scenario"] for r in reps}):
        rr = [r for r in reps if r["scenario"] == sc]; d = dict(n_reps=len(rr), mean_breaks=float(np.mean([r["n_breaks"] for r in rr])), tests={})
        for a in ASSETS:
            k = f"H2_{a}"; ps = np.array([r["tests"][k]["p"] for r in rr if r["tests"][k]["p"] is not None], float); g = np.array([r["tests"][k]["G"] if r["tests"][k]["G"] is not None else np.nan for r in rr], float)
            t = dict(n=len(ps), reject_raw_0_05=float(np.mean(ps <= 0.05)) if len(ps) else None, reject_holm_0_05=float(np.mean([r["tests"][k]["p_holm"] is not None and r["tests"][k]["p_holm"] <= 0.05 for r in rr])), G_mean=float(np.nanmean(g)))
            if sc == "effect":
                tg = np.array([r["targets"][a] if r["targets"][a] is not None else np.nan for r in rr], float); ok = np.isfinite(g) & np.isfinite(tg)
                t.update(planted_k=K_PLANT[a], target_mean=float(np.mean(tg[ok])), bias=float(np.mean(g[ok] - tg[ok])), bias_se=float(np.std(g[ok] - tg[ok], ddof=1) / np.sqrt(ok.sum())))
            d["tests"][k] = t
        d["any_holm_reject"] = float(np.mean([any(r["tests"][f"H2_{a}"]["p_holm"] is not None and r["tests"][f"H2_{a}"]["p_holm"] <= 0.05 for a in ASSETS) for r in rr])); s[sc] = d
    return s


def synth(tag, nnull, neff, nboot, workers):
    out_p = R.OUT / f"h2_synth_{tag}.json"; part = R.OUT / f"h2_synth_reps_{tag}.jsonl"
    if out_p.exists(): print("result exists; written once"); return 3
    jobs = [(sc, i, nboot) for sc in ("indep", "vol") for i in range(nnull)] + [("effect", i, nboot) for i in range(neff)]; done = {}
    if part.exists():
        for line in part.read_text(encoding="utf-8").splitlines(): r = json.loads(line); done[(r["scenario"], r["rep"])] = r
    todo = [j for j in jobs if (j[0], j[1]) not in done]; t0 = time.time(); print(f"{len(todo)} replicates to run ({len(done)} done)", flush=True)
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers) as pool, open(part, "a", encoding="utf-8") as f:
        for k, r in enumerate(pool.imap_unordered(replicate, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); done[(r["scenario"], r["rep"])] = r
            if k % 20 == 0 or k == len(todo): print(f"{k}/{len(todo)} {time.time() - t0:.0f} s", flush=True)
    res = dict(label="A32 rule 5a H2 synthetic check (synthetic data only)", nboot=nboot, planted_k=K_PLANT, summary=summarise([done[(j[0], j[1])] for j in jobs]),
               generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    R.write_once(out_p, res); print(json.dumps(res["summary"], indent=1)); return 0


def evaluate(summary, lim=0.081):
    rows = []; add = lambda name, value, ok: rows.append(dict(criterion=name, value=value, passed=bool(ok)))
    for sc in ("indep", "vol"):
        for k, t in summary[sc]["tests"].items(): add(f"{sc}: {k} rejection <= {lim}", t["reject_raw_0_05"], t["reject_raw_0_05"] is not None and t["reject_raw_0_05"] <= lim)
    e = summary["effect"]["tests"]
    for a in ("TLT", "HYG", "GOLD"):
        t = e[f"H2_{a}"]; add(f"effect: H2_{a} |bias| <= max(2 SE, 0.10 x target)", [t["bias"], t["bias_se"], t["target_mean"]], abs(t["bias"]) <= max(2 * t["bias_se"], 0.10 * abs(t["target_mean"])))
    for a in ("TLT", "GOLD"): add(f"effect: H2_{a} rejection >= 0.80", e[f"H2_{a}"]["reject_raw_0_05"], e[f"H2_{a}"]["reject_raw_0_05"] >= 0.80)
    return rows


def check(tag):
    f = R.OUT / f"h2_synth_{tag}.json"
    if not f.exists(): print(f"missing {f}"); return 3
    rows = evaluate(json.loads(f.read_text(encoding="utf-8"))["summary"])
    for r in rows: print(("PASS " if r["passed"] else "FAIL ") + r["criterion"] + f"  value {r['value']}")
    ok = all(r["passed"] for r in rows); print("A32 rule 5a synthetic check:", "PASS" if ok else f"FAIL ({sum(not r['passed'] for r in rows)} of {len(rows)} criteria)")
    R.write_once(R.OUT / f"h2_synth_check_{tag}.json", dict(tag=tag, passed=ok, criteria=rows, synth_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), provenance=provenance()))
    return 0 if ok else 1


# ---------- A32 rule 5b: power
def _ptask(t):
    delta, i, br, nboot = t; rng = np.random.default_rng(int(hashlib.sha256(f"h2power|{delta}|{i}".encode()).hexdigest()[:8], 16))
    days = [d for d, _ in br]; eras = [e for _, e in br]; wk = {w: rng.normal(0, WEEK_SD) for w in {L.week_of(d) for d in days}}
    c = delta + np.array([wk[L.week_of(d)] for d in days]) + rng.normal(0, 1, len(days))
    return delta, L.week_block_bootstrap(lambda ix: float(c[ix].mean()), days, eras, nboot, int(rng.integers(1 << 30)))[1]


def power(det, sims, nboot, workers):
    import s6_power as P
    out = R.OUT / f"h2_power_{det}.json"
    if out.exists(): print("result exists; written once"); return 3
    br, _ = P.structure(det); tasks = [(g, i, br, nboot) for g in D_GRID for i in range(sims)]
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(workers) as pool: res = pool.map(_ptask, tasks, chunksize=4)
    else: res = [_ptask(t) for t in tasks]
    pw = {str(g): float(np.mean([p <= ALPHA1 for gg, p in res if gg == g])) for g in D_GRID}
    o = dict(detector=det, label="A32 rule 5b H2 power (break structure only; outcomes simulated)", n_breaks=len(br), n_weeks=len({L.week_of(d) for d, _ in br}), sims=sims, nboot=nboot,
             alpha_first_holm_step=ALPHA1, week_sd=WEEK_SD, power=pw, mde_sd_units=next((g for g in D_GRID if pw[str(g)] >= 0.8), None), note="all development breaks, all assets available: an upper bound",
             generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    R.write_once(out, o); print(json.dumps(dict(power=pw, mde=o["mde_sd_units"]))); return 0


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return 3
    arg = lambda k, dflt: int(a[a.index(k) + 1]) if k in a else dflt
    if a[0] == "synth": return synth(a[a.index("--tag") + 1], arg("--null-reps", 200), arg("--effect-reps", 40), arg("--nboot", 999), arg("--workers", 6))
    if a[0] == "check": return check(a[1])
    if a[0] == "power": return power(a[1], arg("--sims", 200), arg("--nboot", 999), arg("--workers", 3))
    if a[0] == "development": return development(a[1], arg("--nboot", L.NBOOT))
    print(__doc__); return 3


if __name__ == "__main__": sys.exit(main())
