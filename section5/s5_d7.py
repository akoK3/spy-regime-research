#!/usr/bin/env python3
"""D7 (AMENDMENT_A19.md rule 2): do the main-run detectors respond to non-volatility changes? Variance-neutral liquidity / trend / momentum / jump injections after tau on the stable TEST
days of the 26 confirmatory folds, scored with the A17 saved fits (no refit; pickles verified against the A17 manifest) at the A17 fold-level A7 thresholds. Null = the same day and tau
unmodified. Positive control = a 5.6 variance splice of ratio 3 (permanent) on the same day and tau. 'Responds' = hit minus null >= 0.10 with a day-clustered 95% CI excluding 0.
Usage: s5_d7.py PROTOCOL_SHA256 [--check]      --check: guards + a smoke test on the contaminated RAW 3 fold (3 days; nothing written to results/d7/ckpt).
Exit codes: 0 done, 1 crash (retryable; resumes from results/d7/ckpt), 2 Ctrl+C, 3 guard refusal."""
import sys, os, json, time, pickle, math, datetime, traceback, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; OUT = RES / "d7"; CK = OUT / "ckpt"; A17 = RES / "a17"; LOG = RES / "d7_log.txt"
EXIT_OK, EXIT_CRASH, EXIT_STOP, EXIT_GUARD = 0, 1, 2, 3
SEED = 1907; NBOOT = 10000; WIN = 60; JUMP_SD = 6.0; RESPOND = 0.10; VR_BAND = (0.95, 1.05); NULL_MAX = 0.30; MIN_DAYS = 100; PC_RATIO = 3.0
LEVELS = {"liquidity": [("vol_x2", 2.0), ("vol_x0.5", 0.5)], "trend": [("t2", 2.0), ("t4", 4.0)], "momentum": [("rho0.2", 0.2), ("rho0.4", 0.4)], "jumps": [("jumps1", 1), ("jumps3", 3)]}
PRIMARY = {"liquidity": "vol_x2", "trend": "t4", "momentum": "rho0.4", "jumps": "jumps3"}                # A19 rule 2c
FAMILIES = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); H1_FAMILIES = FAMILIES[:3]
PX = ("open", "high", "low", "close")


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"; LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def keep_awake(on=True):
    try:
        import ctypes; ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception: pass


# ---------- injection (pure; A19 rule 2c)
def window_ok(p, g):
    J = np.arange(g, g + WIN + 2); return bool(J[-1] < len(p["close"]) and np.isfinite(p["close"][J]).all() and p["valid"][J[1:]].all() and np.isfinite(p["r"][J[1:]]).all())


def local_sd(r, g):
    x = np.abs(r[g - 59:g + 1]); pr = x[1:] * x[:-1]; pr = pr[np.isfinite(pr)]
    return float(np.sqrt(np.pi / 2 * pr.mean())) if len(pr) >= 30 and pr.mean() > 0 else float("nan")


def inject(p, g, kind, level, w, rng, sign):
    """Copy of the one-session panel p with the change after bar g. w = 1 / slot baseline of r^2 (A's units) per bar. Returns (panel, info). Variance-neutral: sum w r^2 over the 60
    bars after g equals the unmodified value (jumps: the non-jump bars are rescaled)."""
    q = {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in p.items()}; J = np.arange(g + 1, g + WIN + 1); r = p["r"][J].astype(float); wj = w[J]; S0 = float((wj * r * r).sum())
    if kind == "liquidity":
        q["volume"][g + 1:] = p["volume"][g + 1:] * level; return q, dict(vr=1.0, scale=1.0)
    jumps = np.zeros(WIN, bool)
    if kind == "trend":
        sd = r.std(ddof=1); x = r + (sign * level * sd / math.sqrt(WIN) - r.mean())
    elif kind == "momentum":
        x = r.copy()
        for k in range(1, WIN): x[k] = r[k] + level * x[k - 1]
    elif kind == "jumps":
        lsd = local_sd(p["r"], g)
        if not np.isfinite(lsd): return None, dict(vr=float("nan"), scale=float("nan"), why="local sd undefined")
        x = r.copy(); at = rng.choice(WIN, int(level), replace=False); jumps[at] = True; x[at] = r[at] + rng.choice([-1.0, 1.0], int(level)) * JUMP_SD * lsd
    else: raise ValueError(kind)
    sj = float((wj[jumps] * x[jumps] ** 2).sum()); sn = float((wj[~jumps] * x[~jumps] ** 2).sum()); c2 = (S0 - sj) / sn if sn > 0 else float("nan")
    c = math.sqrt(c2) if c2 > 0 else 1.0; x = np.where(jumps, x, c * x)                                            # infeasible rescale: left unscaled; the VR gate records it
    lo_, lc_ = np.log(p["open"]), np.log(p["close"]); lh_, ll_ = np.log(p["high"]), np.log(p["low"]); lc = lc_.copy(); lo = lo_.copy(); lh = lh_.copy(); ll = ll_.copy()
    lc[J] = lc_[g] + np.cumsum(x); lo[J] = lc[J - 1]
    up = np.maximum(lh_[J] - np.maximum(lo_[J], lc_[J]), 0); dn = np.maximum(np.minimum(lo_[J], lc_[J]) - ll_[J], 0)
    lh[J] = np.maximum(lo[J], lc[J]) + c * up; ll[J] = np.minimum(lo[J], lc[J]) - c * dn                      # wicks scaled like the returns
    A_ = np.arange(g + WIN + 1, len(lc)); sh = lc[g + WIN] - lc_[g + WIN]
    for a, b in ((lo, lo_), (lh, lh_), (ll, ll_), (lc, lc_)): a[A_] = b[A_] + sh
    for k, a in zip(PX, (lo, lh, ll, lc)): q[k] = np.exp(a)
    q["r"][J] = np.diff(lc[g:g + WIN + 1]); q["range"][J] = lh[J] - ll[J]
    rb = np.diff(np.log(q["close"][g:g + WIN + 1])); vr = float((wj * rb * rb).sum() / S0) if S0 > 0 else float("nan")       # from the rebuilt closes
    return q, dict(vr=vr, scale=c, c2=c2)


# ---------- statistics (A19 rule 2e)
def cluster_diff(y1, y0, clusters, nboot=NBOOT, seed=SEED):
    """Mean(y1) - mean(y0) over rows; percentile 95% CI by resampling clusters with replacement."""
    y1, y0 = np.asarray(y1, float), np.asarray(y0, float); u, inv = np.unique(np.asarray(clusters), return_inverse=True); n = np.bincount(inv, minlength=len(u)).astype(float)
    s1, s0 = np.bincount(inv, y1, len(u)), np.bincount(inv, y0, len(u)); est = float(s1.sum() / n.sum() - s0.sum() / n.sum())
    W = np.random.default_rng(seed).multinomial(len(u), np.full(len(u), 1 / len(u)), size=nboot).astype(float); N = W @ n
    bs = (W @ s1 - W @ s0) / N; lo, hi = np.percentile(bs, [2.5, 97.5])
    return dict(diff=est, ci95=[float(lo), float(hi)], rate1=float(s1.sum() / n.sum()), rate0=float(s0.sum() / n.sum()), n_rows=int(n.sum()), n_clusters=len(u), responds=bool(est >= RESPOND and lo > 0))


# ---------- one fold
def fold_unit(db, fold, models, thresholds, max_days=None):
    import s5_d2_stable as S, s5_d2 as D2, s5_fast as F, s5_lib as L, s5_eval as V, s5_a7 as B, s5_events as E
    c = db.c; d, dv, cols = c["d"], c["dv"], c["cols"]; stable, _ = S.stable_days(d, c["seg"]["test"], dv); bases = F.load_bases(d, db.era, cols)
    era_code = 0 if db.era == "LEGACY" else 1; out = dict(fold=fold, n_stable=len(stable), days=[], skipped=[])
    rows = {}; lab = ["null", "pc_ratio3"] + [f"{k}:{n}" for k, lv in LEVELS.items() for n, _ in lv]
    for i in (stable if max_days is None else stable[:max_days]):
        rng = np.random.default_rng((SEED, era_code, db.fold, int(i))); fa = int(d["first"][i]); p0 = L.sub_panel(d, [i]); g = None
        for _ in range(200):
            gg = int(rng.choice(V.TAU_SLOTS))
            if window_ok(p0, gg): g = gg; break
        if g is None: out["skipped"].append(dict(day=str(d["day"][fa]), why="no tau with a complete 61-bar window")); continue
        w = F.in_units_of_A(d, i, np.ones(390)); sign = 1.0 if i % 2 == 0 else -1.0; tau = int(p0["available"][g]); rec = dict(day=str(d["day"][fa]), i=int(i), g=g, vr={}, info={})
        pan = {"null": p0}
        pre = np.nanmean(dv[fa + 1:fa + g + 1]); rB2 = np.where(d["valid"][fa:fa + 390], d["r"][fa:fa + 390], np.nan) ** 2; post = np.nanmean(F.in_units_of_A(d, i, rB2)[g + 1:390])
        pan["pc_ratio3"], _ = D2.regime_panel(d, i, i, g, float(np.sqrt(PC_RATIO * pre / post)), None)                      # 5.6 permanent variance splice, B = A
        for kind, lv in LEVELS.items():
            for name, level in lv:
                q, info = inject(p0, g, kind, level, w, rng, sign); rec["vr"][f"{kind}:{name}"] = info["vr"]; rec["info"][f"{kind}:{name}"] = {k: v for k, v in info.items() if k != "vr"}
                if q is not None: pan[f"{kind}:{name}"] = q
        for k in lab:
            if k in pan: rows[(len(out["days"]), k)] = F.rows_from_panel(d, bases, pan[k], i, i, g, tau, cols)
        rec["tau"] = tau; out["days"].append(rec)
    hits = {}
    for fam in FAMILIES:
        for which in ("feature", "baseline"):
            m, sub = models[fam][which]; thr = thresholds[fam][which]; D = 1 + len(sub); keys = sorted(rows)
            qs = [c["mk"](c["to_des"](rows[k], rows[k]["iA"]), sub) for k in keys]; rs = V.run_filter(fam, m, qs, D); h = {}
            for k, q, r in zip(keys, qs, rs):
                tau = rows[k]["tau"]; h.setdefault(k[1], {})[k[0]] = bool(any(q["avail"][e["i_d"]] > tau and q["avail"][e["i_c"]] <= tau + WIN * E.MIN for e in (B.events(fam, r, q, thr) if q["n"] else [])))
            hits[f"{fam}|{which}"] = {lb: [v.get(j) for j in range(len(out["days"]))] for lb, v in h.items()}
    out["hits"] = hits; return out


# ---------- guards, models
def guards(token):
    import s5_guard as G, s5_contamination as C
    ph = G.verify_frozen_protocol(token); G.verify_completion(RES / "main_run" / G.COMPLETION, require_main=True); G.canonical_contamination()
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    C.check_registry(HERE); a17 = A17 / "a17_results.json"
    if not a17.exists(): raise PermissionError("A17 results missing")
    man = json.loads(a17.read_text(encoding="utf-8"))["models_manifest"]
    if len(man) != 136: raise PermissionError(f"A17 manifest has {len(man)} models, expected 136")
    log(f"D7 guards: protocol {ph[:16]}..., main record verified, canonical list, no lock, registry ok, A17 manifest 136 models"); return ph, man


def load_fold_models(fold, man):
    models, thr = {}, {}
    for fam in FAMILIES:
        name = f"{fold.replace('|', '_')}_{fam}.pkl"; p = A17 / "models" / name
        if not p.exists() or file_sha(p) != man[name]: raise PermissionError(f"A17 model {name} missing or its sha256 differs from the A17 manifest")
        o = pickle.loads(p.read_bytes()); ck = json.loads((A17 / "ckpt" / f"{fold.replace('|', '_')}_{fam}.json").read_text(encoding="utf-8"))
        models[fam] = dict(feature=(o["feature"], tuple(o["setup"]["features"])), baseline=(o["baseline"], ())); thr[fam] = {w: ck["thresholds"][w]["threshold"] for w in ("feature", "baseline")}
    return models, thr


# ---------- aggregate (A19 rules 2e-2g)
def aggregate(units):
    rows = [(u["fold"], dd) for u in units for dd in u["days"]]; cl = [f"{f.split('|')[0]}:{dd['day']}" for f, dd in rows]; res = dict(n_rows=len(rows), n_days=len(set(cl)), types={}, gates={})
    def col(key, lab): return [h for u in units for h in u["hits"][key].get(lab, [None] * len(u["days"]))]
    def pair(key, lab):
        a, b = np.array(col(key, lab), dtype=object), np.array(col(key, "null"), dtype=object); ok = np.array([x is not None and y is not None for x, y in zip(a, b)])
        return a[ok].astype(float), b[ok].astype(float), np.array(cl, dtype=object)[ok]
    labels = ["pc_ratio3"] + [f"{k}:{n}" for k, lv in LEVELS.items() for n, _ in lv]
    for lab in labels:
        e = {}
        for fam in FAMILIES:
            for which in ("feature", "baseline"): y1, y0, cc = pair(f"{fam}|{which}", lab); e[f"{fam}|{which}"] = cluster_diff(y1, y0, cc)
            f1, f0, cc = pair(f"{fam}|feature", lab); b1, b0, _ = pair(f"{fam}|baseline", lab); e[f"{fam}|feature_minus_baseline"] = cluster_diff(f1 - f0, b1 - b0, cc)
        if lab != "pc_ratio3": vr = np.array([dd["vr"][lab] for _, dd in rows], float); e["variance_neutral_share"] = float(np.mean((vr >= VR_BAND[0]) & (vr <= VR_BAND[1])))
        res["types"][lab] = e
    nulls = {f"{fam}|{w}": float(np.mean([x for x in col(f"{fam}|{w}", "null") if x is not None])) for fam in FAMILIES for w in ("feature", "baseline")}
    g2 = all(res["types"]["pc_ratio3"][f"{f}|feature"]["responds"] for f in H1_FAMILIES); g3 = all(nulls[f"{f}|{w}"] <= NULL_MAX for f in H1_FAMILIES for w in ("feature", "baseline")); g4 = res["n_days"] >= MIN_DAYS
    res["null_hit_rates"] = nulls; res["gates"] = dict(ii_positive_control=g2, iii_null_sanity=g3, iv_days=g4, n_days=res["n_days"])
    d8 = json.loads((RES / "d8" / "d8_results.json").read_text(encoding="utf-8"))["occurs"]; res["verdict"] = {}
    for kind, lev in PRIMARY.items():
        lab = f"{kind}:{lev}"; g1 = res["types"][lab]["variance_neutral_share"] >= 0.95; gates = g1 and g2 and g3 and g4
        resp = {f: res["types"][lab][f"{f}|feature"]["responds"] for f in H1_FAMILIES}; missed = gates and not any(resp.values())
        res["verdict"][kind] = dict(primary_level=lev, gate_i_variance_neutral=g1, gates_passed=gates, feature_responds=resp, missed=missed, d8_occurs=d8[kind], step2_trigger=bool(missed and d8[kind]))
    return res


def preflight(token, days=3):
    import s5_backend as BK
    ph, man = guards(token); db = BK.DataBackend("RAW", 3); t0 = time.time(); models, thr = load_fold_models("RAW|3", man)
    u = fold_unit(db, "RAW|3", models, thr, max_days=days); dt = (time.time() - t0) / 60
    vr = [v for dd in u["days"] for v in dd["vr"].values()]; bad = [v for v in vr if not (VR_BAND[0] <= v <= VR_BAND[1])]
    if len(u["days"]) < 1 or set(u["hits"]) != {f"{f}|{w}" for f in FAMILIES for w in ("feature", "baseline")}: raise RuntimeError(f"D7 smoke test incomplete: {len(u['days'])} days, {sorted(u['hits'])}")
    log(f"D7 preflight: RAW 3 (contaminated) {u['n_stable']} stable test days, {len(u['days'])} scored, {len(u['skipped'])} skipped; {len(vr)} injections, VR outside [0.95, 1.05]: {len(bad)} {bad[:3]}; "
        f"null hits (Gaussian feature) {u['hits']['gaussian_hmm|feature']['null']}; pc_ratio3 {u['hits']['gaussian_hmm|feature']['pc_ratio3']}; {dt:.1f} min (incl. load); nothing written to results/d7/ckpt")
    agg = aggregate([u]); log(f"D7 preflight: aggregate ran on {agg['n_days']} days (gates on this mini sample are not meaningful: {agg['gates']})")
    n = len(list(CK.glob("*.json"))) if CK.exists() else 0; log(f"D7 preflight: {n} of 26 D7 fold units already checkpointed"); return ph


def main():
    if len(sys.argv) < 2: print("usage: s5_d7.py PROTOCOL_SHA256 [--check]"); return EXIT_GUARD
    token, check = sys.argv[1], "--check" in sys.argv[2:]
    try:
        if check: preflight(token); log("D7 preflight passed (--check): D7 NOT started"); return EXIT_OK
        ph, man = guards(token)
    except (PermissionError, RuntimeError, AssertionError) as e: log(f"D7 REFUSED (not retryable): {type(e).__name__}: {e}"); return EXIT_GUARD
    import s5_main as MB, s5_guard as G
    tag = dict(d7_script=file_sha(__file__), a17_results=file_sha(A17 / "a17_results.json")); CK.mkdir(parents=True, exist_ok=True)
    keep_awake(True); t0 = time.time(); b = MB.MainBackend(ph); excluded, _ = G.excluded_folds(); folds = [f for f in b.folds() if f not in excluded]
    try:
        units = []
        for k, fold in enumerate(folds, 1):
            p = CK / f"{fold.replace('|', '_')}.json"
            if p.exists():
                u = json.loads(p.read_text(encoding="utf-8"))
                if u.get("tag") == tag: units.append(u); continue
            G.check_unlocked("D7"); t1 = time.time(); models, thr = load_fold_models(fold, man); u = fold_unit(b._b(fold), fold, models, thr); u["tag"] = tag
            tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, default=float), encoding="utf-8"); tmp.replace(p); units.append(u)
            log(f"D7 fold {k}/{len(folds)} {fold}: {len(u['days'])} days ({len(u['skipped'])} skipped); {(time.time() - t1) / 60:.1f} min")
        res = aggregate(units); res.update(label="D7 (AMENDMENT_A19.md rule 2)", amendment_sha256=file_sha(HERE.parent / "AMENDMENT_A19.md"), tag=tag, folds=folds, hours=(time.time() - t0) / 3600)
        (OUT / "d7_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); log(f"D7 DONE in {(time.time() - t0) / 3600:.2f} h; results/d7/d7_results.json written"); return EXIT_OK
    except PermissionError as e: log(f"D7 REFUSED (not retryable): {e}"); return EXIT_GUARD
    except KeyboardInterrupt: log("D7 STOPPED by the user (Ctrl+C); finished folds are checkpointed"); return EXIT_STOP
    except BaseException as e:
        log(f"D7 CRASH after {(time.time() - t0) / 60:.1f} min: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return EXIT_CRASH
    finally: keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
