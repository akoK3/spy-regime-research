#!/usr/bin/env python3
"""Section 6 analysis (AMENDMENT_A28; H4 statistic and rule 3c diagnostic per AMENDMENT_A29): H3 (tripwire) and H4 (confirmation), co-primary; secondary analyses of rules 5c and 7. H2 is not computed here (rule 2: unchanged).
Inputs: SPY break export (section5/results/breaks/: breaks.csv, sessions.json), the label-free coverage (section6/results/coverage/), the canonical panels through
section5/s5_eval_loader (development: load_development; joint evaluation: load_eval with section6=True, i.e. after the freeze, the lock, the finding-17 preflight and the
Section 6 fingerprint). Clock and windows: s6_lib (A28 1c, 4a). Every evaluation-period result carries the A26 label.
Period "development": the test segments of the uncontaminated folds (the break export covers exactly these). Period "joint": refused until the 5.13 outputs exist.
Usage: s6_run.py development DETECTOR [--nboot N] [--workers N]     DETECTOR = the A9 item 2 H2 primary detector chosen at the 5.12 freeze (rule 1b), or its H3/H4 fallback.
       s6_run.py joint DETECTOR FREEZE_PATH CONFIRM_TOKEN
The development run refuses to start unless AMENDMENT_A29 is ADOPTED and equals its sidecar (A29 4b).
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

    @classmethod
    def from_arrays(cls, era, days, R, avail):
        E = cls.__new__(cls); E.era = era; E.days = list(days); E.ix = {d: i for i, d in enumerate(E.days)}; E.R = dict(R)
        E.avail = {a: np.array([avail.get((era, d, a), False) for d in E.days]) for a in ASSETS}; E.drv = L.deseasonalised_rv(E.R["SPY"]); return E


def era_cache_code():
    """Hash of the code that turns panel rows into EraData arrays (finding 14 key component)."""
    return hashlib.sha256(b"".join((d / f).read_bytes() for d, f in ((HERE, "s6_run.py"), (HERE, "s6_lib.py"), (ROOT / "section5", "s5_eval_loader.py")))).hexdigest()


def load_era(era, period, freeze=None, token=None, cache=True):
    """Development EraData. Return matrices are cached through s6_lib.Cache (finding 14: key = column | code hash | panel hash), so a changed panel or
    changed code never gives a stale hit. The joint period is refused before any read (FABLE_AUDIT L4)."""
    if period != "development": raise PermissionError("joint period: evaluation-period coverage must be computed through the guarded loader first")
    import s5_eval_loader as EL, pandas as pd
    cov = pd.read_csv(COVER); av = {(r.era, r.day, r.asset): bool(r.available) for r in cov.itertuples()}
    C = L.Cache(HERE / "cache"); code = era_cache_code(); panel = hashlib.sha256(Path(EL.PANELS[era]).read_bytes()).hexdigest()
    names = [f"{era}|days"] + [f"{era}|{a}|R" for a in ("SPY",) + ASSETS]; got = {n: C.get(n, code, panel) for n in names} if cache else {}
    if cache and all(v is not None for v in got.values()):
        return EraData.from_arrays(era, [str(d) for d in got[f"{era}|days"]], {a: got[f"{era}|{a}|R"] for a in ("SPY",) + ASSETS}, av)
    cols = [f"{a}_{k}" for a in ("SPY",) + ASSETS for k in ("return_eligible", "log_return_1m")]
    E = EraData(era, EL.load_development(era, cols), av)
    if cache:
        C.put(f"{era}|days", code, panel, np.array(E.days))
        for a in ("SPY",) + ASSETS: C.put(f"{era}|{a}|R", code, panel, E.R[a])
    return E


def load_breaks(detector):
    rows = list(csv.DictReader(open(BREAKS / "breaks.csv", encoding="utf-8"))); sess = json.loads((BREAKS / "sessions.json").read_text(encoding="utf-8"))
    for x in rows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    return [x for x in rows if x["family"] == detector], sess


# ---------- units, candidates, placebos
def spy_vol(E, s, t): return L.safe_log(L.rv(E.R["SPY"][s], t - 60, t)[0])


def is_calm_start(x): return str(x.get("old_state")) == "0"      # AMENDMENT_A31 2a: the detector's reference state at S is the lowest-variance state (HMM / HSMM)


def build(E, rows, sess, anchor="T0"):
    """Units of the era, each with a role. role "break": every confirmed run (all directions; H3 / H4b filter calm-to-stressed), gap = T_c - S (anchor T0) or 0 (anchor S).
    role "h4a" (AMENDMENT_A31 rule 2): every streak start S in a calm state, any outcome (confirmed, fizzle, open at close), gap 0, label afterward.
    Candidates: SPY update times (every 5 minutes) of the sessions with detector output. alarms_by_day: confirmed T_c of the detector (all directions)."""
    days = sorted({d for f, v in sess.items() if f.startswith(E.era + "|") for d in v if d in E.ix}); units = []; alarms = {}
    for x in rows:
        if x["era"] != E.era or x["day"] not in E.ix: continue
        di = E.ix[x["day"]]
        if x["kind"] == "confirmed": alarms.setdefault(di, []).append(x["T0_min"])
        base = dict(x, day_idx=di, era=E.era, S=x["S_min"], vol=spy_vol(E, di, x["S_min"]), burn_in_ok=di >= L.BURN_IN)
        if x["kind"] == "confirmed":
            gap = (x["T0_min"] - x["S_min"]) if anchor == "T0" else 0; units.append(dict(base, role="break", gap=gap, T=x["S_min"] + gap))
        if is_calm_start(x) and x["kind"] in ("confirmed", "fizzle", "open_at_close"): units.append(dict(base, role="h4a", gap=0, T=x["S_min"]))
    cd, cs = [], []
    for d in days:
        for s in range(L.STEP, L.N_MIN, L.STEP): cd.append(E.ix[d]); cs.append(s)
    cd = np.array(cd, int); cs = np.array(cs, int)
    cand = dict(day_idx=cd, S=cs, era=np.array([E.era] * len(cd)), vol=np.array([spy_vol(E, d, s) for d, s in zip(cd, cs)]))
    return units, cand, alarms


def attach_placebos(units, cand, alarms, seed=2028):
    for k, u in enumerate(units):
        h = int(hashlib.sha256(f"{seed}|{u['era']}|{u['day']}|{u['S']}|{u['kind']}|{u.get('role')}".encode()).hexdigest()[:8], 16)
        ix = L.draw_placebos(u, cand, alarms, seed=h); u["placebos"] = [dict(day_idx=int(cand["day_idx"][i]), S=int(cand["S"][i]), gap=u["gap"], T=int(cand["S"][i]) + u["gap"]) for i in ix]
    return units


# ---------- per-asset quantities (offset: LEGACY SPY-clock offset in minutes, rule 7e: asset windows are read at SPY time + offset)
def h3_row(E, a, di, S, T, outcome, off=0, ph_end="T"):
    """ph_end "T": prior-hour control over (T - 60, T] (A28 3b); "S": over (S - 60, S] (A29 3c, descriptive diagnostic)."""
    nxt = di + 1
    if not E.avail[a][di] or di < 1 or not E.avail[a][di - 1]: return None
    e = T if ph_end == "T" else S
    r = E.R[a][di]; ph = L.safe_log(L.rv(r, e - 60 + off, e + off)[0]); pd_ = L.safe_log(L.rv(E.R[a][di - 1], 0, L.N_MIN)[0]); ret = L.cumret(r, S + off, T + off)[0]
    if outcome == "next_day":
        if nxt >= len(E.days) or not E.avail[a][nxt]: return None
        y = L.safe_log(L.rv(E.R[a][nxt], 0, L.N_MIN)[0])
    else:
        if L.N_MIN - T < L.REST_MIN: return None
        y = L.safe_log(L.rv(r, T + off, L.N_MIN)[0])
    return dict(y=y, X=[ph, pd_, ret, abs(ret)])


def h3_test(E_by, units, a, outcome="next_day", nboot=L.NBOOT, off=0, seed=0, ph_end="T"):
    ys, Xs, bs, days, eras = [], [], [], [], []
    for u in units:
        E = E_by[u["era"]]; o = off if u["era"] == "LEGACY" else 0
        for b, (di, S, T) in [(1, (u["day_idx"], u["S"], u["T"]))] + [(0, (p["day_idx"], p["S"], p["T"])) for p in u["placebos"]]:
            r = h3_row(E, a, di, S, T, outcome, o, ph_end)
            if r is None or not np.isfinite(r["y"]) or not np.isfinite(r["X"]).all(): continue
            ys.append(r["y"]); Xs.append(r["X"]); bs.append(b); days.append(E.days[di]); eras.append(u["era"])
    if not ys or sum(bs) < 5: return dict(n_breaks=int(sum(bs)), n_placebos=int(len(bs) - sum(bs)), gamma=None, p=None)
    y = np.array(ys); X = np.array(Xs); b = np.array(bs, float)
    if nboot == 0: return dict(n_breaks=int(b.sum()), n_placebos=int(len(b) - b.sum()), gamma=L.ols_gamma(y, X, b), p=None, label="descriptive, not tested")
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
    X = np.array(X); c = np.array(c); y = np.array(y, float); folds = L.cv_folds(days, eras)        # A29 1a: folds fixed on the original weeks; resampled rows keep them (1d)
    g, p, nv = L.week_block_bootstrap(lambda ix: L.auc_gain_cv(X[ix], c[ix], y[ix], folds[ix]), days, eras, nboot, seed)
    _, a1, a0 = L.auc_gain_cv(X, c, y, folds, parts=True)
    return dict(n=len(y), n_pos=int(np.nansum(y)), gain=g, p=p, n_valid_resamples=nv, statistic="A29 out-of-fold AUC gain (5 week folds, per-fold AUC, weighted mean)",
                oof_auc_with_C=a1, oof_auc_spy_only=a0, gain_in_sample_descriptive=L.auc_gain(X, c, y))      # A29 1g: descriptive


def real_fn(E_by, pct=L.REAL_PCT, horizon=1): return lambda u: L.real_label(E_by[u["era"]].drv, u["day_idx"], pct, horizon)


# ---------- the analyses
def unit_lists(units, subset=None):
    """(H3 / H4b breaks, H4a units), burn-in passed, optionally restricted by a SUBSETS key or a predicate."""
    keep = SUBSETS[subset] if isinstance(subset, str) else ((lambda u: True) if subset is None else subset)
    br = [u for u in units if u.get("role", "break") == "break" and u["kind"] == "confirmed" and u["direction"] == "calm_to_stressed" and u["burn_in_ok"] and keep(u)]
    return br, [u for u in units if u.get("role") == "h4a" and u["burn_in_ok"] and keep(u)]


def primary(E_by, units, nboot, off=0, seed=0, subset=None):
    """The 6 primary tests (A28 5b): H3 next-day per asset (confirmed calm-to-stressed breaks), H4a (A31 rule 2: every calm-state streak start, label = confirms),
    H4b (real vs false at T = 0). subset: None or a key of SUBSETS (picklable for the worker pool)."""
    br, runs = unit_lists(units, subset)
    res = {f"H3_{a}": h3_test(E_by, br, a, "next_day", nboot, off, seed) for a in ASSETS}
    res["H4a"] = h4_test(E_by, runs, "S", lambda u: float(u["kind"] == "confirmed"), nboot, off, seed)
    res["H4b"] = h4_test(E_by, br, "T0", real_fn(E_by), nboot, off, seed)
    holm_family(res)
    return res, br, runs


PRIMARY = tuple(f"H3_{a}" for a in ASSETS) + ("H4a", "H4b")
SUBSETS = {"y2007": lambda u: u["day"] >= Y2007, "fed": lambda u: bool(u.get("fed")), "non_fed": lambda u: not u.get("fed")}


# ---------- worker pool (development run): workers hold E_by once; tasks are primary() calls and A28 7d null sets
_W = {}


def _winit(E_by, extra):
    _W["E"] = E_by; _W.update(extra)


def _wtask(t):
    kind = t[0]
    if kind == "primary":
        _, units, nboot, off, seed, subset = t; return primary(_W["E"], units, nboot, off, seed, subset)[0]
    if kind == "null":
        _, s = t; return null_set(_W["E"], _W["units"], _W["cand_by"], _W["alarms_by"], _W["nboot"], s, _W["seed"])
    raise ValueError(kind)


def run_tasks(E_by, tasks, workers=1, extra=None):
    """Runs tasks in order (workers <= 1) or in a spawn pool whose workers receive E_by once; results in task order."""
    if workers <= 1:
        _winit(E_by, extra or {}); return [_wtask(t) for t in tasks]
    import multiprocessing as mp
    with mp.get_context("spawn").Pool(workers, initializer=_winit, initargs=(E_by, extra or {})) as pool: return pool.map(_wtask, tasks, chunksize=1)


def holm_family(res):
    """A28 5b: the family is always the 6 primary tests (m = 6). A test that is not evaluable enters with p = 1 and is never rejected (A15 rule 6a; FABLE_AUDIT M2)."""
    used = [res[k]["p"] if res[k].get("p") is not None and np.isfinite(res[k]["p"]) else 1.0 for k in PRIMARY]; adj = L.holm(used)
    for k, pu, a in zip(PRIMARY, used, adj):
        ev = res[k].get("p") is not None and np.isfinite(res[k]["p"])
        res[k].update(p_used=float(pu), evaluable=bool(ev), holm_m=len(PRIMARY), p_holm=float(a), **{"reject_0.05": bool(ev and a <= 0.05)})
    return res


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


def null_set(E_by, units, cand_by, alarms_by, nboot, s, seed=7):
    """One A28 7d(ii) null set: every unit (breaks and H4a units, burn-in passed) replaced by one time drawn like its placebos; placebos drawn for it by the rule in force.
    Returns {test: rejected at 0.05}."""
    sd = lambda *k: int(hashlib.sha256("|".join(map(str, k)).encode()).hexdigest()[:8], 16); fake = []
    for u in [x for x in units if x["burn_in_ok"] and (x.get("role") == "h4a" or x["direction"] == "calm_to_stressed")]:
        c = cand_by[u["era"]]; ix = L.draw_placebos(u, c, alarms_by[u["era"]], n=1, seed=sd("null", s, u["day"], u["S"], u["kind"], u.get("role")))
        if len(ix) == 0: continue
        i = int(ix[0]); fake.append(dict(u, day_idx=int(c["day_idx"][i]), day=E_by[u["era"]].days[int(c["day_idx"][i])], S=int(c["S"][i]), T=int(c["S"][i]) + u["gap"], vol=float(c["vol"][i])))
    for f in fake:
        c = cand_by[f["era"]]; f["placebos"] = [dict(day_idx=int(c["day_idx"][i]), S=int(c["S"][i]), gap=f["gap"], T=int(c["S"][i]) + f["gap"]) for i in L.draw_placebos(f, c, alarms_by[f["era"]], seed=sd("nullpl", s, f["day"], f["S"], f.get("role")))]
    res, _, _ = primary(E_by, fake, nboot, 0, seed + s)
    return {k: bool(res[k]["p"] is not None and res[k]["p"] <= 0.05) for k in PRIMARY}


def sanity(E_by, br, units, cand_by, alarms_by, nboot, n_sets=200, seed=7, workers=1):
    """A28 7d. (i) Fed breaks raise TLT rest-of-day RV above placebo (H3 rest-of-day, p < 0.05 passes). (ii) n_sets null sets (null_set); the share of p <= 0.05 for each
    of the 6 primary tests must be <= 0.10."""
    fed = [u for u in br if u.get("fed")]; pos = h3_test(E_by, fed, "TLT", "rest_of_day", nboot, 0, seed)
    out = run_tasks(E_by, [("null", s) for s in range(n_sets)], workers, dict(units=units, cand_by=cand_by, alarms_by=alarms_by, nboot=nboot, seed=seed))
    rate = {k: float(np.mean([o[k] for o in out])) if out else None for k in PRIMARY}
    return dict(positive_control=dict(pos, passed=bool(pos["p"] is not None and pos["p"] < 0.05)), null_control=dict(n_sets=len(out), rejection_rate=rate, passed=bool(out) and all(v <= 0.10 for v in rate.values())))


def placebo_filter_control(E_by, br, cand_by, nboot, seed=31, reference="matched_no_alarm_filter"):
    """AMENDMENT_A31 rule 3 (revised 2026-11-10): per asset, the H3 next-day regression (A28 3b controls) of filtered placebos (1) against 20 times per unit drawn
    with the same placebo matching but no alarm condition (0); delta with its two-sided 95% basic week-block bootstrap interval; flagged when the interval excludes 0.
    A check: outside Holm and BH; never stops the run.
    reference="random" (A31 3e, descriptive only): the comparison set is 20 fully unfiltered random times per unit; delta and interval reported, never flagged (flag None)."""
    flagged = reference == "matched_no_alarm_filter"
    out = {}; rnd = {}
    for u in br:
        h = int(hashlib.sha256(f"rand|{u['era']}|{u['day']}|{u['S']}".encode()).hexdigest()[:8], 16); c = cand_by[u["era"]]
        ix = L.draw_random_times(u, c, seed=h) if reference == "random" else L.draw_placebos(u, c, {}, seed=h, rule="none")
        rnd[id(u)] = [(int(c["day_idx"][i]), int(c["S"][i]), int(c["S"][i]) + u["gap"]) for i in ix]
    for a in ASSETS:
        ys, Xs, bs, days, eras = [], [], [], [], []
        for u in br:
            E = E_by[u["era"]]
            for b, (di, S, T) in [(1, (p["day_idx"], p["S"], p["T"])) for p in u["placebos"]] + [(0, x) for x in rnd[id(u)]]:
                r = h3_row(E, a, di, S, T, "next_day")
                if r is None or not np.isfinite(r["y"]) or not np.isfinite(r["X"]).all(): continue
                ys.append(r["y"]); Xs.append(r["X"]); bs.append(b); days.append(E.days[di]); eras.append(u["era"])
        if sum(bs) < 5 or len(bs) - sum(bs) < 5: out[a] = dict(delta=None, ci95=None, interval_excludes_0=None, flag=None, n_filtered=int(sum(bs)), n_reference=int(len(bs) - sum(bs))); continue
        y = np.array(ys); X = np.array(Xs); b = np.array(bs, float)
        t, lo, hi, nv = L.week_block_ci(lambda ix: L.ols_gamma(y[ix], X[ix], b[ix]), days, eras, nboot, seed)
        ex = bool(np.isfinite(lo) and (lo > 0 or hi < 0))
        out[a] = dict(delta=t, ci95=[lo, hi], interval_excludes_0=ex, flag=(ex if flagged else None), n_filtered=int(b.sum()), n_reference=int(len(b) - b.sum()), n_valid_resamples=nv)
    lab = ("A31 rule 3 placebo-filter null control: filtered vs matched without the alarm exclusion (check; outside Holm and BH)" if flagged
           else "A31 rule 3e: filtered vs fully unfiltered random times (descriptive only; never flagged; outside Holm and BH)")
    return dict(label=lab, reference=reference, by_asset=out, any_flag=(any(bool(v.get("flag")) for v in out.values()) if flagged else None))


A30_PCT = 90; A30_MIN_PLACEBO = 10; A30_BEFORE = 30; A30_AFTER = 60; A30_QS = (10, 25, 50, 75, 90)


def first_exceedance(E, a, di, S, T, ref):
    """AMENDMENT_A30 rule 2 for one window: ref = list of (day_idx, S) of the reference times (placebos). Bars of 5 minutes aligned to S over [S - 30, T + 60]
    (rule 1c); per bar, |cumulative log return| against the 90th percentile of the same bar relative to each reference S (bars inside the session only; >= 10 values).
    Returns (bar end of the first exceedance or None, number of evaluable bars)."""
    nev = 0
    for end in range(S - A30_BEFORE + L.STEP, T + A30_AFTER + 1, L.STEP):
        x = abs_ret(E, a, di, end - L.STEP, end)
        pv = [abs_ret(E, a, d, end - L.STEP - S + s, end - S + s) for d, s in ref if 0 <= end - L.STEP - S + s and end - S + s <= L.N_MIN]
        pv = [v for v in pv if np.isfinite(v)]
        if len(pv) < A30_MIN_PLACEBO or not np.isfinite(x): continue
        nev += 1
        if x > np.percentile(pv, A30_PCT): return end, nev
    return None, nev


def _a30_summary(recs):
    """recs: per window dict(fed, t={asset: bar end or None or "na"}, S, T). Rule 3a-3b quantities."""
    out = dict(n_windows=len(recs), by_asset={})
    for a in ASSETS:
        ev = [r for r in recs if r["t"][a] != "na"]; hit = [r for r in ev if r["t"][a] is not None]
        dS = np.array([r["t"][a] - r["S"] for r in hit], float); dT = np.array([r["t"][a] - r["T"] for r in hit], float)
        q = lambda v: (dict(mean=float(v.mean()), **{f"p{k}": float(np.percentile(v, k)) for k in A30_QS}) if len(v) else None)
        out["by_asset"][a] = dict(n_evaluated=len(ev), n_unavailable=len(recs) - len(ev), n_with_exceedance=len(hit), share_with_exceedance=(len(hit) / len(ev) if ev else None),
                                  rel_S=q(dS), rel_T=q(dT), counts_rel_S={str(int(k)): int(n) for k, n in zip(*np.unique(dS, return_counts=True))} if len(dS) else {},
                                  counts_rel_T={str(int(k)): int(n) for k, n in zip(*np.unique(dT, return_counts=True))} if len(dT) else {},
                                  share_spy_S_first=(float(np.mean([r["t"][a] is None or r["t"][a] > r["S"] for r in ev])) if ev else None))
    allav = [r for r in recs if any(r["t"][a] != "na" for a in ASSETS)]
    out["share_spy_S_first_all_available_assets"] = float(np.mean([all(r["t"][a] is None or r["t"][a] > r["S"] for a in ASSETS if r["t"][a] != "na") for r in allav])) if allav else None
    out["n_windows_with_any_available_asset"] = len(allav)
    return out


def lead_lag(E_by, br):
    """AMENDMENT_A30 (descriptive, secondary, no test, outside Holm and BH): for each confirmed calm-to-stressed break (burn-in passed), per asset the first 5-minute bar in
    [S - 30, T + 60] whose |return| exceeds its placebo 90th percentile; distributions relative to S and T, the share of breaks where SPY's S comes first (t_a > S or no
    exceedance), all, Fed and non-Fed (rule 3c); the chance reference (rule 3d): each placebo against the unit's other placebos. Regular hours only: a break whose window
    starts before 09:30 or crosses the close is skipped (rule 1b). LEGACY offset 0 (rule 1d)."""
    recs, chance, skipped = [], [], 0
    for u in br:
        S, T = u["S"], u["T"]
        if S - A30_BEFORE < 0 or T + A30_AFTER > L.N_MIN: skipped += 1; continue
        E = E_by[u["era"]]; di = u["day_idx"]; pls = [(p["day_idx"], p["S"]) for p in u.get("placebos", [])]
        t = {a: (first_exceedance(E, a, di, S, T, pls)[0] if E.avail[a][di] else "na") for a in ASSETS}
        recs.append(dict(fed=bool(u.get("fed")), t=t, S=S, T=T))
        for j, (pd_, ps) in enumerate(pls):
            if ps - A30_BEFORE < 0 or ps + (T - S) + A30_AFTER > L.N_MIN: continue
            others = pls[:j] + pls[j + 1:]
            tc = {a: (first_exceedance(E, a, pd_, ps, ps + (T - S), others)[0] if E.avail[a][pd_] else "na") for a in ASSETS}
            chance.append(dict(fed=bool(u.get("fed")), t=tc, S=ps, T=ps + (T - S)))
    split = lambda rr: dict(all=_a30_summary(rr), fed=_a30_summary([r for r in rr if r["fed"]]), non_fed=_a30_summary([r for r in rr if not r["fed"]]))
    return dict(label="AMENDMENT_A30 lead-lag description (descriptive, secondary; no test; outside Holm and BH)", assets=list(ASSETS), n_breaks=len(br),
                skipped_window_outside_regular_hours=skipped, breaks=split(recs), chance_reference_placebos=split(chance),
                definitions=dict(window_min=[-A30_BEFORE, "T+60"], bar_min=L.STEP, pct=A30_PCT, min_placebo_values=A30_MIN_PLACEBO, spy_first="t_a > S or no exceedance; a bar ending at or before S counts as the asset first"))


def counts(E_by, units):
    """Rule 6h: burn-in removals per era; breaks by number of available assets; (H3 sample sizes are in each test's n_breaks / n_placebos)."""
    out = {}
    for era, E in E_by.items():
        br = [u for u in units if u["era"] == era and u.get("role", "break") == "break" and u["kind"] == "confirmed" and u["direction"] == "calm_to_stressed"]
        h4 = [u for u in units if u["era"] == era and u.get("role") == "h4a"]
        nav = [int(sum(E.avail[a][u["day_idx"]] for a in ASSETS)) for u in br if u["burn_in_ok"]]
        out[era] = dict(confirmed_calm_to_stressed=len(br), removed_by_burn_in=sum(not u["burn_in_ok"] for u in br), by_n_available_assets={str(k): nav.count(k) for k in range(0, 5)},
                        h4a_calm_streak_starts={k: sum(1 for u in h4 if u["kind"] == k and u["burn_in_ok"]) for k in ("confirmed", "fizzle", "open_at_close")},
                        h4a_removed_by_burn_in=sum(not u["burn_in_ok"] for u in h4),
                        breaks_with_fewer_than_20_placebos=sum(1 for u in br if len(u.get("placebos", [])) < L.N_PLACEBO))
    return out


def analyse(E_by, rows, sess, nboot, detector, all_rows=None, null_sets=200, workers=1):
    units, cand_by, alarms_by = [], {}, {}
    for era, E in E_by.items():
        u, c, al = build(E, rows, sess); units += attach_placebos(u, c, al); cand_by[era], alarms_by[era] = c, al
    fed_flags(units)
    res = dict(detector=detector, counts=counts(E_by, units))
    tasks = [("primary", units, nboot, 0, 0, None), ("primary", units, nboot, 0, 0, "y2007"), ("primary", units, nboot, 0, 0, "fed"), ("primary", units, nboot, 0, 0, "non_fed")]
    if "LEGACY" in E_by: tasks += [("primary", units, nboot, o, 0, None) for o in (-1, 1)]
    fams = []
    if all_rows is not None:      # rule 7a: other detectors, and the alternative anchor T = 0 at S
        for fam in FAMILIES:
            fr = [x for x in all_rows if x["family"] == fam]; uu = []
            for era, E in E_by.items(): u, c, al = build(E, fr, sess); uu += attach_placebos(u, c, al)
            fed_flags(uu); tasks.append(("primary", uu, nboot, 0, 0, None)); fams.append(fam)
        uu = []
        for era, E in E_by.items(): u, c, al = build(E, rows, sess, anchor="S"); uu += attach_placebos(u, c, al)
        tasks.append(("primary", uu, nboot, 0, 0, None))
    out = run_tasks(E_by, tasks, workers); k = 0
    res["primary"] = out[k]; k += 1; res["sens_2007"] = out[k]; k += 1; res["fed_split"] = dict(fed=out[k], non_fed=out[k + 1]); k += 2
    if "LEGACY" in E_by: res["legacy_offsets"] = {"-1": out[k], "1": out[k + 1]}; k += 2
    if all_rows is not None:
        res["detector_dependence"] = {f: out[k + j] for j, f in enumerate(fams)}; k += len(fams); res["anchor_T0_at_S"] = out[k]; k += 1
    br, runs = unit_lists(units)
    res["secondary"] = secondary(E_by, br, runs, units, nboot)
    res["curve"] = curve(E_by, br); res["taxonomy"] = taxonomy(E_by, br)
    res["h3_prior_hour_before_S"] = {a: h3_test(E_by, br, a, "next_day", 0, ph_end="S") for a in ASSETS}      # A29 3c: descriptive, not tested
    res["placebo_filter_control"] = placebo_filter_control(E_by, br, cand_by, nboot)                          # A31 rule 3 (revised): matched without the alarm exclusion
    res["placebo_filter_unfiltered_descriptive"] = placebo_filter_control(E_by, br, cand_by, nboot, reference="random")      # A31 3e: descriptive only
    res["a30_lead_lag"] = lead_lag(E_by, br)                                                                 # A30: descriptive, secondary, no Holm
    res["sanity"] = sanity(E_by, br, units, cand_by, alarms_by, nboot, null_sets, workers=workers)
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


SECTION6_AMENDMENTS = ("A28", "A29", "A30", "A31")      # the amendments a Section 6 result depends on; recorded in every output (FABLE_AUDIT M3)
REQUIRED_ADOPTED = ("A28", "A29", "A30", "A31")         # A29 4b, A30 5c, A31 5c: the development run waits for all four


def a29_guard(names=REQUIRED_ADOPTED):
    """Refuses unless every amendment in `names` is ADOPTED (manifest regex, not a substring test) and equals its sidecar."""
    import s5_amendment_manifest as AM
    bad = [f"{e['amendment']}: " + ("missing" if not e["present"] else f"{e['status']}, sidecar {'matches' if e['sidecar_matches'] else 'missing or differs'}")
           for e in AM.manifest(names) if not (e["present"] and e["status"] == "ADOPTED" and e["sidecar_matches"])]
    if bad: raise SystemExit("the Section 6 run is held until these amendments are ADOPTED and equal their sidecars: " + "; ".join(bad))


def provenance():
    """Code and amendment record written into every Section 6 output (FABLE_AUDIT M3): sha256 of every Section 6 script and helper, the code version, the amendment manifest."""
    import s6_fingerprint as FP, s5_amendment_manifest as AM
    return dict(code=FP.current(), amendments=AM.manifest(SECTION6_AMENDMENTS))


def write_once(path, obj):
    """Writes a result with a sha256 sidecar; refuses to overwrite an existing result (FABLE_AUDIT M3); refuses an evaluation-period result without the A26 label (A34 3a)."""
    path = Path(path)
    if isinstance(obj, dict) and obj.get("period") not in (None, "development") and not (obj.get("a26_label") == LABEL_EVAL and obj.get("confirmatory") is False):
        raise PermissionError(f"{path.name}: an evaluation-period result must carry a26_label = {LABEL_EVAL!r} and confirmatory = False (AMENDMENT_A34 rule 3a, A26 1d)")
    if path.exists(): raise SystemExit(f"{path} exists: Section 6 results are written once; move it aside with a ledger row to rerun")
    path.parent.mkdir(parents=True, exist_ok=True); path.write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8")
    path.with_suffix(".sha256").write_text(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n", encoding="ascii"); return path


def main():
    if len(sys.argv) < 3: print(__doc__); return 3
    period, det = sys.argv[1], sys.argv[2]
    if det not in FAMILIES[:3]: print("DETECTOR must be an H1 family (gaussian_hmm, student_t_hmm, hsmm)"); return 3
    a29_guard()
    if (OUT / f"s6_{period}_{det}.json").exists(): print("result exists; written once"); return 3
    if period == "joint": print("joint evaluation: refused until the 5.12 freeze, the 5.13 outputs and the Section 6 fingerprint exist"); return 3
    nboot = int(sys.argv[sys.argv.index("--nboot") + 1]) if "--nboot" in sys.argv else L.NBOOT
    allrows = list(csv.DictReader(open(BREAKS / "breaks.csv", encoding="utf-8")))
    for x in allrows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    rows = [x for x in allrows if x["family"] == det]; sess = json.loads((BREAKS / "sessions.json").read_text(encoding="utf-8"))
    E_by = {era: load_era(era, period) for era in ("LEGACY", "RAW")}
    workers = int(sys.argv[sys.argv.index("--workers") + 1]) if "--workers" in sys.argv else 1
    res = analyse(E_by, rows, sess, nboot, det, allrows, workers=workers)
    res.update(period=period, generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), nboot=nboot, provenance=provenance())
    p = write_once(OUT / f"s6_{period}_{det}.json", res); print(f"written {p}"); return 0


if __name__ == "__main__": sys.exit(main())
