#!/usr/bin/env python3
"""H2 (AMENDMENT_A33). PRIMARY = protocol 5.0 H2 as pre-registered: per asset (TLT, HYG, gold, USD), the mean over confirmed calm-to-stressed SPY breaks of the signed
cumulative return over (T, T + 30], against a placebo distribution matched on time-of-day slot, era and SPY volatility decile (10,000 draws), two-sided, Holm across
the 4 assets (m = 4). Gaps filled as A33 rule 2 (G1-G11). Secondary (BH): (T - 30, T], +5, +15, +60, stressed-to-calm +30, and S2 (other detectors).
EXPLORATORY (A33 rule 4): the A32 deseasonalised |return| statistic with A31 placebos, specified after seeing the H3/H4/A30 development results; uncorrected.
E1 footprint taxonomy (A32 4c, descriptive); S1 covered by H4a and A30; E2 deferred.
Usage:
  s6_h2.py synth --tag TAG [--null-reps 200] [--effect-reps 40] [--draws 10000] [--workers 6]  (A33 rule 3; synthetic data only)
  s6_h2.py check TAG                                                                           (A33 rule 3c acceptance; exit 1 if any criterion fails)
  s6_h2.py power DETECTOR [--sims 200] [--draws 10000] [--workers 3]                            (A33 G11; break count only, no outcome read)
  s6_h2.py development DETECTOR [--nboot 9999]                                                 (A33 6b; refuses unless A28-A33 are ADOPTED)
No freeze, no O8, no era calibration, no evaluation-period read."""
import sys, json, csv, time, hashlib, datetime, collections
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R

ASSETS = R.ASSETS; PRIOR = 20; MIN_PRIOR = 10; MIN_PLACEBO = 10; PCT = 90; ALPHA1 = 0.05 / 4
WINDOWS = {"h5": (0, 5), "h15": (0, 15), "h30": (0, 30), "h60": (0, 60), "pre30": (-30, 0)}
AMENDMENTS = ("A28", "A29", "A30", "A31", "A32", "A33")
B50 = 10_000; POOL_SIM = 200; C_PLANT = dict(TLT=0.05, HYG=-0.05, GOLD=0.05, DOLLAR=0.0); D_GRID = (0.05, 0.1, 0.15, 0.2, 0.3, 0.4)      # A33 G1, G11, rule 3b


# ---------- A32 rule 2 (exploratory under A33 rule 4): deseasonalised |return|
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


# ---------- AMENDMENT_A33: H2 primary = protocol 5.0 (signed cumulative return, matched placebo distribution of 10,000 draws, two-sided)
def _cum(E, a, di, t0, t1):
    """Signed cumulative log return over (t0, t1] of session di (A28 1c clock); NaN if outside regular hours, asset unavailable or no data (A33 G8)."""
    if t0 < 0 or t1 > L.N_MIN or t1 <= t0 or not E.avail[a][di]: return np.nan
    _, N, C = _pref(E, a)
    return float(C[di, t1] - C[di, t0]) if N[di, t1] - N[di, t0] > 0 else np.nan


def p50_test(E_by, cand_by, brs, a, lo, hi, B=B50, seed=0):
    """A33 rules 1-2 for one asset and window (T + lo, T + hi]. M = mean over breaks of the signed cumulative return; each of B draws takes one placebo per break,
    uniform with replacement from its pool (same era, other sessions of the era, same 30-minute slot of T, same SPY prior-hour-RV decile at T with cut points from all
    candidates of the era; no alarm exclusion; window inside the session, asset available with data). Two-sided p = min(1, 2 min(P_lo, P_hi)), add-one (G1-G2)."""
    rng = np.random.default_rng(seed); msum = np.zeros(B); rs = []; pool_n = []; skipped = 0
    by_era = collections.defaultdict(list)
    for u in brs: by_era[u["era"]].append(u)
    for era, us in by_era.items():
        E = E_by[era]; c = cand_by[era]; cuts = L.decile_cuts(c["vol"])
        if cuts is None: skipped += len(us); continue
        cdz = np.where(np.isfinite(c["vol"]), np.searchsorted(cuts, c["vol"], side="right"), -1); cslot = (c["S"] - 1) // L.SLOT_MIN
        cr = np.array([_cum(E, a, d, s + lo, s + hi) for d, s in zip(c["day_idx"], c["S"])]); okc = np.isfinite(cr)
        groups = collections.defaultdict(list)
        for i in np.flatnonzero(okc & (cdz >= 0)): groups[(int(cslot[i]), int(cdz[i]))].append(i)
        groups = {k: np.array(v) for k, v in groups.items()}
        for u in us:
            r = _cum(E, a, u["day_idx"], u["T"] + lo, u["T"] + hi); dzv = L.decile(R.spy_vol(E, u["day_idx"], u["T"]), cuts)
            if not np.isfinite(r) or dzv is None: skipped += 1; continue
            g = groups.get((L.slot_of(u["T"]), dzv), np.array([], int)); g = g[c["day_idx"][g] != u["day_idx"]] if len(g) else g
            if len(g) == 0: skipped += 1; continue
            rs.append(r); pool_n.append(len(g)); msum += cr[g[rng.integers(0, len(g), B)]]
    n = len(rs); out = dict(n_breaks=n, n_skipped=skipped, window=[lo, hi], draws=B, mean_pool_size=(float(np.mean(pool_n)) if pool_n else None))
    if n < 5: return dict(out, M=None, p=None)
    M = float(np.mean(rs)); mb = msum / n; plo = (1 + np.sum(mb <= M)) / (B + 1); phi = (1 + np.sum(mb >= M)) / (B + 1)
    return dict(out, M=M, placebo_mean=float(mb.mean()), placebo_sd=float(mb.std(ddof=1)), p=float(min(1.0, 2 * min(plo, phi))), p_lo=float(plo), p_hi=float(phi))


def seed_of(*k): return int(hashlib.sha256("|".join(map(str, k)).encode()).hexdigest()[:8], 16)


def p50_primary(E_by, cand_by, brs, tag="primary", B=B50):
    return holm4({f"H2_{a}": p50_test(E_by, cand_by, brs, a, *WINDOWS["h30"], B, seed_of("p50", tag, a)) for a in ASSETS})


def units50(E_by, rows, sess):
    """A33 G4: confirmed breaks of the detector (no burn-in), by direction; candidate times per era (s6_run.build)."""
    c2s, s2c, cand_by = [], [], {}
    for era, E in E_by.items():
        u, c, _ = R.build(E, [x for x in rows if x["era"] == era], sess); cand_by[era] = c
        c2s += [x for x in u if x["role"] == "break" and x["direction"] == "calm_to_stressed"]; s2c += [x for x in u if x["role"] == "break" and x["direction"] == "stressed_to_calm"]
    return c2s, s2c, cand_by


# ---------- the development analysis
def units_for(E_by, rows, sess):
    units = []
    for era, E in E_by.items():
        u, c, al = R.build(E, [x for x in rows if x["era"] == era], sess); units += R.attach_placebos(u, c, al)
    return R.unit_lists(units)[0]


def analyse(E_by, rows, sess, nboot, detector, all_rows=None, B=B50):
    c2s, s2c, cand_by = units50(E_by, rows, sess)
    res = dict(detector=detector, label="H2 (AMENDMENT_A33: protocol 5.0 primary; development data)", n_breaks=len(c2s), n_breaks_by_era=dict(collections.Counter(u["era"] for u in c2s)))
    res["primary"] = p50_primary(E_by, cand_by, c2s, f"{detector}|primary", B)
    sec = {f"H2_{a}_{w}": p50_test(E_by, cand_by, c2s, a, *WINDOWS[w], B, seed_of("p50", detector, a, w)) for w in ("pre30", "h5", "h15", "h60") for a in ASSETS}
    sec.update({f"H2_stressed_to_calm_{a}_h30": p50_test(E_by, cand_by, s2c, a, *WINDOWS["h30"], B, seed_of("p50", detector, a, "s2c")) for a in ASSETS}); res["secondary"] = sec
    if all_rows is not None:      # A33 5b (S2, as A32 4b): the rule 1 test with every detector's breaks
        dep = {}
        for fam in R.FAMILIES:
            fc, _, fcand = units50(E_by, [x for x in all_rows if x["family"] == fam], sess); dep[fam] = p50_primary(E_by, fcand, fc, f"{fam}|dep", B)
        res["detector_dependence"] = dep; res["verdict_agreement"] = {fam: {a: dep[fam][f"H2_{a}"]["reject_0.05"] for a in ASSETS} for fam in dep}
    bh = [(k, v["p"]) for k, v in sec.items() if v.get("p") is not None]
    bh += [(f"S2.{fam}.{k}", v["p"]) for fam, d in res.get("detector_dependence", {}).items() if fam != detector for k, v in d.items() if v.get("p") is not None]
    adj = L.bh([p for _, p in bh]) if bh else []; res["secondary_bh"] = {k: dict(p=p, p_bh=float(q), label="secondary") for (k, p), q in zip(bh, adj)}
    br = units_for(E_by, rows, sess)      # A32 units (burn-in) and A31 placebos: exploratory statistic and E1
    res["exploratory_a32"] = dict(label="EXPLORATORY (A33 rule 4): A32 deseasonalised |return| statistic, specified after seeing the H3/H4/A30 development results; uncorrected, outside Holm and BH",
                                  n_breaks=len(br), tests={f"X_{a}_{w}": h2_test(E_by, br, a, *WINDOWS[w], (0 if w == "pre30" else nboot)) for w in ("h30", "h5", "h15", "h60", "pre30") for a in ASSETS})
    res["E1"] = e1(E_by, br); res["E2"] = "deferred to future work (A32 rule 4d, A33 rule 5d)"; res["S1"] = "covered by H4a (A31 rule 2) and A30 (A32 rule 4a, A33 rule 5a)"
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
    res.update(period="development", nboot_exploratory=nboot, draws_primary=B50, seconds=round(time.time() - t0, 1), generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    print(f"written {R.write_once(out, res)}"); return 0


# ---------- A33 rule 3: synthetic check of the rule 1 test
def replicate(args):
    import s6_synth_validation as V
    scenario, rep, B = args; t0 = time.time()
    rng = np.random.default_rng(seed_of("p50synth", scenario, rep)); E_by, rows_all, sess = {}, [], {}
    for era, n, start in (("LEGACY", 1500, "2004-01-02"), ("RAW", 450, "2022-03-07")):
        days, R_, avail, rows = V.gen_era(era, n, start, rng, "vol" if scenario == "effect" else scenario); E_by[era] = V.SynthEra(era, days, R_, avail); rows_all += rows; sess[f"{era}|0"] = days
    c2s, _, cand_by = units50(E_by, rows_all, sess); out = dict(scenario=scenario, rep=rep, n_breaks=len(c2s))
    if scenario == "effect":
        mu = {a: C_PLANT[a] * V.SIG[a] for a in ASSETS}
        for u in c2s:
            E = E_by[u["era"]]
            for a in ASSETS:
                if mu[a] and E.avail[a][u["day_idx"]] and u["T"] + 30 <= L.N_MIN: E.R[a][u["day_idx"], u["T"]:u["T"] + 30] += mu[a]
        for E in E_by.values(): E.__dict__.pop("_h2", None)
        out["targets"] = {a: 30 * mu[a] for a in ASSETS}
    res = p50_primary(E_by, cand_by, c2s, f"synth|{scenario}|{rep}", B)
    out["tests"] = {k: dict(G=v.get("M"), p=v.get("p"), p_holm=v.get("p_holm"), n=v.get("n_breaks")) for k, v in res.items()}; out["seconds"] = round(time.time() - t0, 1)
    return out


def summarise(reps):
    s = {}
    for sc in sorted({r["scenario"] for r in reps}):
        rr = [r for r in reps if r["scenario"] == sc]; d = dict(n_reps=len(rr), mean_breaks=float(np.mean([r["n_breaks"] for r in rr])), tests={})
        for a in ASSETS:
            k = f"H2_{a}"; ps = np.array([r["tests"][k]["p"] for r in rr if r["tests"][k]["p"] is not None], float); g = np.array([r["tests"][k]["G"] if r["tests"][k]["G"] is not None else np.nan for r in rr], float)
            t = dict(n=len(ps), reject_raw_0_05=float(np.mean(ps <= 0.05)) if len(ps) else None, reject_holm_0_05=float(np.mean([r["tests"][k]["p_holm"] is not None and r["tests"][k]["p_holm"] <= 0.05 for r in rr])), M_mean=float(np.nanmean(g)))
            if sc == "effect":
                tg = np.array([r["targets"][a] for r in rr], float); ok = np.isfinite(g)
                t.update(target_mean=float(np.mean(tg[ok])), bias=float(np.mean(g[ok] - tg[ok])), bias_se=float(np.std(g[ok] - tg[ok], ddof=1) / np.sqrt(ok.sum())))
            d["tests"][k] = t
        d["any_holm_reject"] = float(np.mean([any(r["tests"][f"H2_{a}"]["p_holm"] is not None and r["tests"][f"H2_{a}"]["p_holm"] <= 0.05 for a in ASSETS) for r in rr])); s[sc] = d
    return s


def synth(tag, nnull, neff, B, workers):
    out_p = R.OUT / f"h2_50_synth_{tag}.json"; part = R.OUT / f"h2_50_synth_reps_{tag}.jsonl"
    if out_p.exists(): print("result exists; written once"); return 3
    jobs = [(sc, i, B) for sc in ("indep", "vol") for i in range(nnull)] + [("effect", i, B) for i in range(neff)]; done = {}
    if part.exists():
        for line in part.read_text(encoding="utf-8").splitlines(): r = json.loads(line); done[(r["scenario"], r["rep"])] = r
    todo = [j for j in jobs if (j[0], j[1]) not in done]; t0 = time.time(); print(f"{len(todo)} replicates to run ({len(done)} done)", flush=True)
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers) as pool, open(part, "a", encoding="utf-8") as f:
        for k, r in enumerate(pool.imap_unordered(replicate, todo), 1):
            f.write(json.dumps(r) + "\n"); f.flush(); done[(r["scenario"], r["rep"])] = r
            if k % 20 == 0 or k == len(todo): print(f"{k}/{len(todo)} {time.time() - t0:.0f} s", flush=True)
    res = dict(label="A33 rule 3 synthetic check of the H2 primary test (protocol 5.0; synthetic data only)", draws=B, planted_c=C_PLANT, summary=summarise([done[(j[0], j[1])] for j in jobs]),
               generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    R.write_once(out_p, res); print(json.dumps(res["summary"], indent=1)); return 0


def evaluate(summary, lim=0.081):
    rows = []; add = lambda name, value, ok: rows.append(dict(criterion=name, value=value, passed=bool(ok)))
    for sc in ("indep", "vol"):
        for k, t in summary[sc]["tests"].items(): add(f"{sc}: {k} rejection <= {lim}", t["reject_raw_0_05"], t["reject_raw_0_05"] is not None and t["reject_raw_0_05"] <= lim)
    e = summary["effect"]["tests"]
    for a in ("TLT", "HYG", "GOLD"):
        t = e[f"H2_{a}"]; add(f"effect: H2_{a} |bias| <= max(2 SE, 0.10 x |target|)", [t["bias"], t["bias_se"], t["target_mean"]], abs(t["bias"]) <= max(2 * t["bias_se"], 0.10 * abs(t["target_mean"])))
    for a in ("TLT", "GOLD"): add(f"effect: H2_{a} rejection >= 0.80", e[f"H2_{a}"]["reject_raw_0_05"], e[f"H2_{a}"]["reject_raw_0_05"] >= 0.80)
    return rows


def check(tag):
    f = R.OUT / f"h2_50_synth_{tag}.json"
    if not f.exists(): print(f"missing {f}"); return 3
    rows = evaluate(json.loads(f.read_text(encoding="utf-8"))["summary"])
    for r in rows: print(("PASS " if r["passed"] else "FAIL ") + r["criterion"] + f"  value {r['value']}")
    ok = all(r["passed"] for r in rows); print("A33 rule 3 synthetic check:", "PASS" if ok else f"FAIL ({sum(not r['passed'] for r in rows)} of {len(rows)} criteria)")
    R.write_once(R.OUT / f"h2_50_synth_check_{tag}.json", dict(tag=tag, passed=ok, criteria=rows, synth_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), provenance=provenance()))
    return 0 if ok else 1


# ---------- A33 G11: power
def _ptask(t):
    delta, i, n, B = t; rng = np.random.default_rng(seed_of("p50power", delta, i, n))
    r = delta + rng.normal(0, 1, n); pools = rng.normal(0, 1, (n, POOL_SIM)); mb = pools[np.arange(n)[:, None], rng.integers(0, POOL_SIM, (n, B))].mean(0); M = r.mean()
    return delta, float(min(1.0, 2 * min((1 + np.sum(mb <= M)) / (B + 1), (1 + np.sum(mb >= M)) / (B + 1))))


def power(det, sims, B, workers):
    import s6_power as P
    out = R.OUT / f"h2_50_power_{det}.json"
    if out.exists(): print("result exists; written once"); return 3
    br, _ = P.structure(det); tasks = [(g, i, len(br), B) for g in D_GRID for i in range(sims)]
    if workers > 1:
        import multiprocessing as mp
        with mp.get_context("spawn").Pool(workers) as pool: res = pool.map(_ptask, tasks, chunksize=4)
    else: res = [_ptask(t) for t in tasks]
    pw = {str(g): float(np.mean([p <= ALPHA1 for gg, p in res if gg == g])) for g in D_GRID}
    o = dict(detector=det, label="A33 G11 H2 power (protocol 5.0 test; break count only; outcomes simulated)", n_breaks=len(br), sims=sims, draws=B, pool_size_simulated=POOL_SIM,
             alpha_first_holm_step=ALPHA1, two_sided=True, power=pw, mde_sd_units=next((g for g in D_GRID if pw[str(g)] >= 0.8), None),
             note="all development breaks with every asset available (an upper bound); delta in SD units of a break's 30-minute return",
             generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance())
    R.write_once(out, o); print(json.dumps(dict(power=pw, mde=o["mde_sd_units"]))); return 0


def main():
    a = sys.argv[1:]
    if not a: print(__doc__); return 3
    arg = lambda k, dflt: int(a[a.index(k) + 1]) if k in a else dflt
    if a[0] == "synth": return synth(a[a.index("--tag") + 1], arg("--null-reps", 200), arg("--effect-reps", 40), arg("--draws", B50), arg("--workers", 6))
    if a[0] == "check": return check(a[1])
    if a[0] == "power": return power(a[1], arg("--sims", 200), arg("--draws", B50), arg("--workers", 3))
    if a[0] == "development": return development(a[1], arg("--nboot", L.NBOOT))
    print(__doc__); return 3


if __name__ == "__main__": sys.exit(main())
