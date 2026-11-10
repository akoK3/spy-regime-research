#!/usr/bin/env python3
"""Section 6 analysis (AMENDMENT_A28): H3 (tripwire) and H4 (confirmation), co-primary; secondary analyses of rules 5c and 7. H2 is not computed here (rule 2: unchanged).
Inputs: SPY break export (section5/results/breaks/: breaks.csv, sessions.json), the label-free coverage (section6/results/coverage/), the canonical panels through
section5/s5_eval_loader (development: load_development; joint evaluation: load_eval with section6=True, i.e. after the freeze, the lock, the finding-17 preflight and the
Section 6 fingerprint). Clock and windows: s6_lib (A28 1c, 4a). Every evaluation-period result carries the A26 label.
Period "development": the test segments of the uncontaminated folds (the break export covers exactly these). Period "joint": refused until the 5.13 outputs exist.
Usage: s6_run.py development DETECTOR [--nboot N]       DETECTOR = the A9 item 2 H2 primary detector chosen at the 5.12 freeze (rule 1b), or its H3/H4 fallback.
       s6_run.py joint DETECTOR FREEZE_PATH CONFIRM_TOKEN
Nothing here runs before the user says so; no freeze, no lock, no era calibration."""
import sys, json, csv, hashlib, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "section5"))
import s6_lib as L

BREAKS = ROOT / "section5" / "results" / "breaks"; COVER = HERE / "results" / "coverage" / "coverage_sessions.csv"; OUT = HERE / "results"
ASSETS = ("TLT", "HYG", "GOLD", "DOLLAR"); FAMILIES = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd")
LABEL_EVAL = "adaptive/exploratory (previously exposed period)"; Y2007 = "2007-04-11"


# ---------- data
class EraData:
    """One era: consecutive sessions of the panel span, (n, 390) returns per asset (NaN where not eligible), asset availability per session (coverage rule)."""
    def __init__(self, era, df, avail):
        self.era = era; self.days = sorted(df["session_date_ny"].unique()); self.ix = {d: i for i, d in enumerate(self.days)}; n = len(self.days)
        self.R = {}; si = df["session_date_ny"].map(self.ix).to_numpy(); mi = df["minute_index_in_session"].to_numpy()
        for a in ("SPY",) + ASSETS:
            X = np.full((n, L.N_MIN), np.nan); el = df[f"{a}_return_eligible"].to_numpy() == 1; X[si[el], mi[el]] = df[f"{a}_log_return_1m"].to_numpy()[el]; self.R[a] = X
        self.avail = {a: np.array([avail.get((era, d, a), False) for d in self.days]) for a in ASSETS}; self.drv = L.deseasonalised_rv(self.R["SPY"])


def load_era(era, period, freeze=None, token=None):
    import s5_eval_loader as EL, pandas as pd
    cols = [f"{a}_{k}" for a in ("SPY",) + ASSETS for k in ("return_eligible", "log_return_1m")]
    df = EL.load_development(era, cols) if period == "development" else EL.load_eval(era, cols, freeze, token, section6=True)
    cov = pd.read_csv(COVER) if period == "development" else None
    if cov is None: raise PermissionError("joint period: evaluation-period coverage must be computed through the guarded loader first")
    av = {(r.era, r.day, r.asset): bool(r.available) for r in cov.itertuples()}; return EraData(era, df, av)


def load_breaks(detector):
    rows = list(csv.DictReader(open(BREAKS / "breaks.csv", encoding="utf-8"))); sess = json.loads((BREAKS / "sessions.json").read_text(encoding="utf-8"))
    for x in rows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    return [x for x in rows if x["family"] == detector], sess


# ---------- units, candidates, placebos
def spy_vol(E, s, t): return L.safe_log(L.rv(E.R["SPY"][s], t - 60, t)[0])


def build(E, rows, sess, anchor="T0"):
    """Units of the era: confirmed and fizzled runs (all directions; the analyses filter), with day index, burn-in flag, gap, SPY vol at S. Candidates: SPY update times
    (every 5 minutes) of the sessions with detector output. alarms_by_day: confirmed T_c of the detector (all directions)."""
    days = sorted({d for f, v in sess.items() if f.startswith(E.era + "|") for d in v if d in E.ix}); units = []; alarms = {}
    for x in rows:
        if x["era"] != E.era or x["day"] not in E.ix: continue
        di = E.ix[x["day"]]
        if x["kind"] == "confirmed": alarms.setdefault(di, []).append(x["T0_min"])
        if x["kind"] not in ("confirmed", "fizzle"): continue
        gap = (x["T0_min"] - x["S_min"]) if (x["kind"] == "confirmed" and anchor == "T0") else 0
        units.append(dict(x, day_idx=di, era=E.era, S=x["S_min"], gap=gap, T=x["S_min"] + gap, vol=spy_vol(E, di, x["S_min"]), burn_in_ok=di >= L.BURN_IN))
    cd, cs = [], []
    for d in days:
        for s in range(L.STEP, L.N_MIN, L.STEP): cd.append(E.ix[d]); cs.append(s)
    cd = np.array(cd, int); cs = np.array(cs, int)
    cand = dict(day_idx=cd, S=cs, era=np.array([E.era] * len(cd)), vol=np.array([spy_vol(E, d, s) for d, s in zip(cd, cs)]))
    return units, cand, alarms


def attach_placebos(units, cand, alarms, seed=2028):
    for k, u in enumerate(units):
        h = int(hashlib.sha256(f"{seed}|{u['era']}|{u['day']}|{u['S']}|{u['kind']}".encode()).hexdigest()[:8], 16)
        ix = L.draw_placebos(u, cand, alarms, seed=h); u["placebos"] = [dict(day_idx=int(cand["day_idx"][i]), S=int(cand["S"][i]), gap=u["gap"], T=int(cand["S"][i]) + u["gap"]) for i in ix]
    return units


# ---------- per-asset quantities (offset: LEGACY SPY-clock offset in minutes, rule 7e: asset windows are read at SPY time + offset)
def h3_row(E, a, di, S, T, outcome, off=0):
    nxt = di + 1
    if not E.avail[a][di] or di < 1 or not E.avail[a][di - 1]: return None
    r = E.R[a][di]; ph = L.safe_log(L.rv(r, T - 60 + off, T + off)[0]); pd_ = L.safe_log(L.rv(E.R[a][di - 1], 0, L.N_MIN)[0]); ret = L.cumret(r, S + off, T + off)[0]
    if outcome == "next_day":
        if nxt >= len(E.days) or not E.avail[a][nxt]: return None
        y = L.safe_log(L.rv(E.R[a][nxt], 0, L.N_MIN)[0])
    else:
        if L.N_MIN - T < L.REST_MIN: return None
        y = L.safe_log(L.rv(r, T + off, L.N_MIN)[0])
    return dict(y=y, X=[ph, pd_, ret, abs(ret)])


def h3_test(E_by, units, a, outcome="next_day", nboot=L.NBOOT, off=0, seed=0):
    ys, Xs, bs, days, eras = [], [], [], [], []
    for u in units:
        E = E_by[u["era"]]; o = off if u["era"] == "LEGACY" else 0
        for b, (di, S, T) in [(1, (u["day_idx"], u["S"], u["T"]))] + [(0, (p["day_idx"], p["S"], p["T"])) for p in u["placebos"]]:
            r = h3_row(E, a, di, S, T, outcome, o)
            if r is None or not np.isfinite(r["y"]) or not np.isfinite(r["X"]).all(): continue
            ys.append(r["y"]); Xs.append(r["X"]); bs.append(b); days.append(E.days[di]); eras.append(u["era"])
    if not ys or sum(bs) < 5: return dict(n_breaks=int(sum(bs)), n_placebos=int(len(bs) - sum(bs)), gamma=None, p=None)
    y = np.array(ys); X = np.array(Xs); b = np.array(bs, float)
    g, p, nv = L.week_block_bootstrap(lambda ix: L.ols_gamma(y[ix], X[ix], b[ix]), days, eras, nboot, seed)
    return dict(n_breaks=int(b.sum()), n_placebos=int(len(b) - b.sum()), gamma=g, p=p, n_valid_resamples=nv)


def abs_ret(E, a, di, lo, hi, off=0):
    if not E.avail[a][di]: return np.nan
    v, n = L.cumret(E.R[a][di], lo + off, hi + off); return abs(v) if n else np.nan


def c_score(E_by, u, point, off=0):
    """C(t) of one unit at point S | T0 | T15 (A28 4a): placebo values are computed with the same window relative to each placebo's own S."""
    E = E_by[u["era"]]; o = off if u["era"] == "LEGACY" else 0; t = {"S": u["S"], "T0": u["T"], "T15": u["T"] + 15}[point]; lo, hi = L.window(point, u["S"], t)
    if hi > L.N_MIN: return np.nan
    ua = {a: abs_ret(E, a, u["day_idx"], lo, hi, o) for a in ASSETS}
    pa = {a: [abs_ret(E, a, p["day_idx"], lo - u["S"] + p["S"], hi - u["S"] + p["S"], o) for p in u["placebos"] if hi - u["S"] + p["S"] <= L.N_MIN] for a in ASSETS}
    return L.confirmation_score(ua, pa)


def spy_info(E, u, point):
    t = {"S": u["S"], "T0": u["T"], "T15": u["T"] + 15}[point]; r = E.R["SPY"][u["day_idx"]]
    ret = L.cumret(r, u["S"] - 15, u["S"])[0] if point == "S" else L.cumret(r, u["S"], t)[0]
    return [ret, L.safe_log(L.rv(r, t - 60, t)[0])]


def h4_test(E_by, units, point, label_fn, nboot=L.NBOOT, off=0, seed=0):
    X, c, y, days, eras = [], [], [], [], []
    for u in units:
        lab = label_fn(u)
        if not np.isfinite(lab): continue
        E = E_by[u["era"]]; X.append(spy_info(E, u, point)); c.append(c_score(E_by, u, point, off)); y.append(lab); days.append(u["day"]); eras.append(u["era"])
    if len(y) < 10: return dict(n=len(y), gain=None, p=None)
    X = np.array(X); c = np.array(c); y = np.array(y, float)
    g, p, nv = L.week_block_bootstrap(lambda ix: L.auc_gain(X[ix], c[ix], y[ix]), days, eras, nboot, seed)
    return dict(n=len(y), n_pos=int(np.nansum(y)), gain=g, p=p, n_valid_resamples=nv)


def real_fn(E_by, pct=L.REAL_PCT, horizon=1): return lambda u: L.real_label(E_by[u["era"]].drv, u["day_idx"], pct, horizon)


# ---------- the analyses
def primary(E_by, units, nboot, off=0, seed=0, subset=None):
    """The 6 primary tests (rule 5b): H3 next-day per asset (confirmed calm-to-stressed breaks), H4a (confirmed vs fizzled calm-to-stressed runs at S), H4b (real vs false at T = 0)."""
    keep = (lambda u: True) if subset is None else subset
    br = [u for u in units if u["kind"] == "confirmed" and u["direction"] == "calm_to_stressed" and u["burn_in_ok"] and keep(u)]
    runs = [u for u in units if u["kind"] in ("confirmed", "fizzle") and u["direction"] == "calm_to_stressed" and u["burn_in_ok"] and keep(u)]
    res = {f"H3_{a}": h3_test(E_by, br, a, "next_day", nboot, off, seed) for a in ASSETS}
    res["H4a"] = h4_test(E_by, runs, "S", lambda u: float(u["kind"] == "confirmed"), nboot, off, seed)
    res["H4b"] = h4_test(E_by, br, "T0", real_fn(E_by), nboot, off, seed)
    ps = [res[k]["p"] for k in res]; ok = [i for i, p in enumerate(ps) if p is not None and np.isfinite(p)]
    adj = L.holm([ps[i] for i in ok]) if ok else []
    for j, i in enumerate(ok): k = list(res)[i]; res[k]["p_holm"] = float(adj[j]); res[k]["reject_0.05"] = bool(adj[j] <= 0.05)
    return res, br, runs


def secondary(E_by, br, runs, units, nboot, seed=0):
    s = {}
    for a in ASSETS: s[f"H3_rest_of_day_{a}"] = h3_test(E_by, br, a, "rest_of_day", nboot, 0, seed)
    s["H4b_at_S"] = h4_test(E_by, br, "S", real_fn(E_by), nboot, 0, seed); s["H4b_at_T15"] = h4_test(E_by, br, "T15", real_fn(E_by), nboot, 0, seed)
    s["H4b_5day"] = h4_test(E_by, br, "T0", real_fn(E_by, horizon=5), nboot, 0, seed)
    for pc in (70, 90): s[f"H4b_pct{pc}"] = h4_test(E_by, br, "T0", real_fn(E_by, pct=pc), nboot, 0, seed)
    sc = [u for u in units if u["kind"] == "confirmed" and u["direction"] == "stressed_to_calm" and u["burn_in_ok"]]
    for a in ASSETS: s[f"H3_stressed_to_calm_{a}"] = h3_test(E_by, sc, a, "next_day", nboot, 0, seed)
    return s


def fed_flags(units):
    import s5_guard as G
    j, _ = G.contamination(); rel = j["h1c_event_release_minute_after_0930"]
    for u in units: m = rel.get(u["day"]); u["fed"] = m is not None and m <= u["S"] <= m + 60
    return units


def curve(E_by, br):
    """Rule 4g (descriptive): mean C and mean |return| per asset, break minus placebo, every 5 minutes from S to T + 15."""
    out = {}
    for k in range(0, 200, L.STEP):
        cs, diffs = [], {a: [] for a in ASSETS}
        for u in br:
            if k > u["gap"] + 15 or u["S"] + k > L.N_MIN: continue
            E = E_by[u["era"]]; t = u["S"] + k; cs.append(L.confirmation_score({a: abs_ret(E, a, u["day_idx"], u["S"], t) for a in ASSETS},
                                                                              {a: [abs_ret(E, a, p["day_idx"], p["S"], p["S"] + k) for p in u["placebos"]] for a in ASSETS}))
            for a in ASSETS:
                x = abs_ret(E, a, u["day_idx"], u["S"], t); pv = [abs_ret(E, a, p["day_idx"], p["S"], p["S"] + k) for p in u["placebos"]]
                if np.isfinite(x) and np.isfinite(pv).any(): diffs[a].append(x - np.nanmean(pv))
        if cs: out[k] = dict(n=len(cs), mean_C=float(np.nanmean(cs)), **{f"abs_ret_diff_{a}": (float(np.mean(diffs[a])) if diffs[a] else None) for a in ASSETS})
    return out


def taxonomy(E_by, br):
    """Rule 7b (E1, descriptive): per break, the sign of each available asset's return S -> T + 15 when |return| exceeds its placebo 90th percentile, else 0; pattern counts."""
    import collections
    pat = collections.Counter()
    for u in br:
        E = E_by[u["era"]]; key = []
        for a in ASSETS:
            if not E.avail[a][u["day_idx"]] or u["T"] + 15 > L.N_MIN: key.append("."); continue
            v = L.cumret(E.R[a][u["day_idx"]], u["S"], u["T"] + 15)[0]; pv = [abs_ret(E, a, p["day_idx"], p["S"], p["S"] + u["gap"] + 15) for p in u["placebos"]]; pv = [x for x in pv if np.isfinite(x)]
            key.append("0" if not pv or abs(v) <= np.percentile(pv, 90) else ("+" if v > 0 else "-"))
        pat["".join(key)] += 1
    return dict(order=list(ASSETS), legend="+/- moved beyond the placebo 90th percentile, 0 within, . unavailable", counts=dict(pat.most_common()))


def sanity(E_by, br, units, cand_by, alarms_by, nboot, n_sets=200, seed=7):
    """Rule 7d. (i) Fed breaks raise TLT rest-of-day RV above placebo (H3 rest-of-day, p < 0.05 passes). (ii) 200 sets of random times drawn like placebos replace the breaks
    (same era, slot and SPY-vol decile as each break, sessions before it, away from alarms); the share of p <= 0.05 for each of the 6 primary tests must be <= 0.10."""
    fed = [u for u in br if u.get("fed")]; pos = h3_test(E_by, fed, "TLT", "rest_of_day", nboot, 0, seed); rej = {k: 0 for k in [f"H3_{a}" for a in ASSETS] + ["H4a", "H4b"]}; n_done = 0
    sd = lambda *k: int(hashlib.sha256("|".join(map(str, k)).encode()).hexdigest()[:8], 16)
    for s in range(n_sets):
        fake = []
        for u in [x for x in units if x["burn_in_ok"] and x["direction"] == "calm_to_stressed"]:
            c = cand_by[u["era"]]; ix = L.draw_placebos(u, c, alarms_by[u["era"]], n=1, seed=sd("null", s, u["day"], u["S"], u["kind"]))
            if len(ix) == 0: continue
            i = int(ix[0]); fake.append(dict(u, day_idx=int(c["day_idx"][i]), day=E_by[u["era"]].days[int(c["day_idx"][i])], S=int(c["S"][i]), T=int(c["S"][i]) + u["gap"], vol=float(c["vol"][i])))
        for f in fake:
            c = cand_by[f["era"]]; f["placebos"] = [dict(day_idx=int(c["day_idx"][i]), S=int(c["S"][i]), gap=f["gap"], T=int(c["S"][i]) + f["gap"]) for i in L.draw_placebos(f, c, alarms_by[f["era"]], seed=sd("nullpl", s, f["day"], f["S"]))]
        res, _, _ = primary(E_by, fake, nboot, 0, seed + s); n_done += 1
        for k in rej: rej[k] += int(res[k]["p"] is not None and res[k]["p"] <= 0.05)
    rate = {k: v / max(n_done, 1) for k, v in rej.items()}
    return dict(positive_control=dict(pos, passed=bool(pos["p"] is not None and pos["p"] < 0.05)), null_control=dict(n_sets=n_done, rejection_rate=rate, passed=all(v <= 0.10 for v in rate.values())))


def counts(E_by, units):
    """Rule 6h: burn-in removals per era; breaks by number of available assets; (H3 sample sizes are in each test's n_breaks / n_placebos)."""
    out = {}
    for era, E in E_by.items():
        br = [u for u in units if u["era"] == era and u["kind"] == "confirmed" and u["direction"] == "calm_to_stressed"]
        nav = [int(sum(E.avail[a][u["day_idx"]] for a in ASSETS)) for u in br if u["burn_in_ok"]]
        out[era] = dict(confirmed_calm_to_stressed=len(br), removed_by_burn_in=sum(not u["burn_in_ok"] for u in br), by_n_available_assets={str(k): nav.count(k) for k in range(0, 5)},
                        fizzled_calm_to_stressed=sum(1 for u in units if u["era"] == era and u["kind"] == "fizzle" and u["direction"] == "calm_to_stressed"),
                        breaks_with_fewer_than_20_placebos=sum(1 for u in br if len(u.get("placebos", [])) < L.N_PLACEBO))
    return out


def analyse(E_by, rows, sess, nboot, detector, all_rows=None, null_sets=200):
    units, cand_by, alarms_by = [], {}, {}
    for era, E in E_by.items():
        u, c, al = build(E, rows, sess); units += attach_placebos(u, c, al); cand_by[era], alarms_by[era] = c, al
    fed_flags(units)
    res = dict(detector=detector, counts=counts(E_by, units))
    res["primary"], br, runs = primary(E_by, units, nboot)
    res["secondary"] = secondary(E_by, br, runs, units, nboot)
    res["sens_2007"] = primary(E_by, units, nboot, subset=lambda u: u["day"] >= Y2007)[0]
    if "LEGACY" in E_by: res["legacy_offsets"] = {str(o): primary(E_by, units, nboot, off=o)[0] for o in (-1, 1)}
    res["fed_split"] = dict(fed=primary(E_by, units, nboot, subset=lambda u: u.get("fed"))[0], non_fed=primary(E_by, units, nboot, subset=lambda u: not u.get("fed"))[0])
    res["curve"] = curve(E_by, br); res["taxonomy"] = taxonomy(E_by, br)
    if all_rows is not None:      # rule 7a: other detectors, and the alternative anchor T = 0 at S
        res["detector_dependence"] = {}
        for fam in FAMILIES:
            fr = [x for x in all_rows if x["family"] == fam]; uu = []
            for era, E in E_by.items(): u, c, al = build(E, fr, sess); uu += attach_placebos(u, c, al)
            fed_flags(uu); res["detector_dependence"][fam] = primary(E_by, uu, nboot)[0]
        uu = []
        for era, E in E_by.items(): u, c, al = build(E, rows, sess, anchor="S"); uu += attach_placebos(u, c, al)
        res["anchor_T0_at_S"] = primary(E_by, uu, nboot)[0]
    res["sanity"] = sanity(E_by, br, units, cand_by, alarms_by, nboot, null_sets)
    sec = [(k, v["p"]) for k, v in flatten_secondary(res) if v.get("p") is not None and np.isfinite(v["p"])]
    adj = L.bh([p for _, p in sec]) if sec else []; res["secondary_bh"] = {k: dict(p=p, p_bh=float(a), label="secondary") for (k, p), a in zip(sec, adj)}
    return res


def flatten_secondary(res):
    for k, v in res["secondary"].items(): yield k, v
    for grp in ("sens_2007", "fed_split", "legacy_offsets", "detector_dependence", "anchor_T0_at_S"):
        g = res.get(grp)
        if not g: continue
        if grp in ("sens_2007", "anchor_T0_at_S"): items = [(f"{grp}.{k}", v) for k, v in g.items()]
        else: items = [(f"{grp}.{a}.{k}", v) for a, sub in g.items() for k, v in sub.items()]
        for k, v in items: yield k, v


def main():
    if len(sys.argv) < 3: print(__doc__); return 3
    period, det = sys.argv[1], sys.argv[2]
    if det not in FAMILIES[:3]: print("DETECTOR must be an H1 family (gaussian_hmm, student_t_hmm, hsmm)"); return 3
    if period == "joint": print("joint evaluation: refused until the 5.12 freeze, the 5.13 outputs and the Section 6 fingerprint exist"); return 3
    nboot = int(sys.argv[sys.argv.index("--nboot") + 1]) if "--nboot" in sys.argv else L.NBOOT
    allrows = list(csv.DictReader(open(BREAKS / "breaks.csv", encoding="utf-8")))
    for x in allrows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    rows = [x for x in allrows if x["family"] == det]; sess = json.loads((BREAKS / "sessions.json").read_text(encoding="utf-8"))
    E_by = {era: load_era(era, period) for era in ("LEGACY", "RAW")}
    res = analyse(E_by, rows, sess, nboot, det, allrows)
    res.update(period=period, generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), nboot=nboot, amendment_sha256=hashlib.sha256((ROOT / "AMENDMENT_A28.md").read_bytes()).hexdigest())
    OUT.mkdir(parents=True, exist_ok=True); p = OUT / f"s6_{period}_{det}.json"; p.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); print(f"written {p}"); return 0


if __name__ == "__main__": sys.exit(main())
