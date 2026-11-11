#!/usr/bin/env python3
"""AMENDMENT_A36 rule 7a and AMENDMENT_A37 rule 5b: synthetic end-to-end run of the joint evaluation driver. SYNTHETIC DATA ONLY: no market file is opened, no evaluation-period row is read.
Everything the driver touches is redirected to a temporary directory for the duration of the run and restored afterwards:
  - generated panels: per era a "TRAIN" block ending at the real TRAIN end and an "evaluation" block starting at the real evaluation start (so the real span
    constants and the guard are exercised unchanged); SPY with volatility regimes; four assets that co-move with SPY volatility; an asset that starts late;
  - s5_eval513._load_span / partitions -> the generated Section 5 panel dicts and their partitions; s5_eval_loader.PANELS -> generated canonical panels;
  - the freeze: s5_freeze.build_freeze / write_freeze with setups of one feature, thresholds calibrated on the generated TRAIN block alone by the A11 rule
    (so the driver's recomputation on the joined panel must reproduce them: a check that evaluation rows do not leak into TRAIN quantities);
  - the lock, the data-hash preflight, the access log, the fingerprint, the FOMC list, the A35 rerun records and every output directory.
The real amendment manifest, contamination registry, label module and guards run as they are.
Checks: both 5.13 results and the three Section 6 results exist, carry the A26 label and confirmatory = False; no p-value in the 5.13 results; the frozen
thresholds are reproduced; no unit, candidate or placebo lies in a history session; the access log holds an ALLOWED line per read; a second run does nothing;
the real evaluation access log does not exist afterwards.
A37 checks: the models are fitted at the freeze (s5_freeze_models, TRAIN only) and hashed into the freeze document before any evaluation read; no model is fitted
during the evaluation step; the era's marker exists at its first evaluation read; a tampered model file is refused before any marker; the alerts field is first.
Usage: s6_eval_synth.py [--train 190] [--eval 110] [--nboot 49] [--null-sets 3] [--draws 500] [--keep DIR]
Output (written once): section6/results/a37_synth_e2e.json (a summary of the synthetic run; no market data). a36_synth_e2e.json is the A36 run, kept."""
import sys, json, gzip, time, shutil, hashlib, tempfile, datetime
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "section5"))
MIN_NS = 60_000_000_000; ASSETS = ("TLT", "HYG", "GOLD", "DOLLAR")


def calendar(n_train, n_eval, dev_last, eval_first):
    tr = [str(x.date()) for x in pd.bdate_range(end=dev_last, periods=n_train)]; ev = [str(x.date()) for x in pd.bdate_range(start=eval_first, periods=n_eval)]; return tr, ev


def gen_spy(days, rng):
    """(n, 390) one-minute log returns (index 0 NaN: no return into the opening bar), per-session volatility with slow regimes and some intraday breaks."""
    n = len(days); lv = np.zeros(n); x = 0.0
    for i in range(n): x = 0.9 * x + rng.normal(0, 0.18); lv[i] = x
    stress = rng.random(n) < 0.10; sig = 6e-4 * np.exp(lv) * np.where(stress, 2.2, 1.0); R_ = rng.normal(0, 1, (n, 390)) * sig[:, None]
    for i in np.flatnonzero(rng.random(n) < 0.35):
        t0 = int(rng.integers(60, 300)); R_[i, t0:] *= float(rng.choice([2.0, 2.5, 3.0]))
    R_[:, 0] = np.nan; return R_


def panel_dict(era, days, R_, rng):
    """A panel dict in the form of the audited Section 4 loader (load_development + load_ohlc)."""
    n = len(days); N = n * 390; day = np.repeat(np.array(days), 390); slot = np.tile(np.arange(390), n); first = np.arange(0, N, 390, dtype=np.int64); end = first + 390
    start = np.array([pd.Timestamp(d + " 09:30", tz="America/New_York").tz_convert("UTC").value for d in days], np.int64); t = (start[:, None] + np.arange(390)[None, :] * MIN_NS).ravel()
    steps = np.where(np.isfinite(R_), R_, 0.0); logp = np.log(100.0) + np.cumsum(rng.normal(0, 0.004, n))[:, None] + np.cumsum(steps, 1)
    close = np.exp(logp).ravel(); r = np.full(N, np.nan); valid = slot > 0; r[valid] = np.log(close[valid] / close[np.flatnonzero(valid) - 1])
    up, dn = np.abs(rng.normal(0, 3e-4, N)), np.abs(rng.normal(0, 3e-4, N)); high, low = close * np.exp(up), close * np.exp(-dn); open_ = close * np.exp(rng.normal(0, 2e-4, N))
    return dict(era=era, t=t, available=t + MIN_NS, day=day, slot=slot, r=r, valid=valid, close=close, range=np.log(high / low), volume=rng.lognormal(7, 0.5, N), first=first, end=end, open=open_, high=high, low=low)


def canonical(era, days, R_, rng, dollar_from):
    """A canonical one-minute panel (the columns Section 6 reads): SPY and four assets whose volatility follows SPY's; DOLLAR not eligible before day index dollar_from."""
    n = len(days); spy_sd = np.nanstd(R_, axis=1); scale = spy_sd / np.median(spy_sd); cols = {}
    start = [pd.Timestamp(d + " 09:30", tz="America/New_York").tz_convert("UTC") for d in days]
    cols["utc_minute_start_assumed"] = [(s + pd.Timedelta(minutes=int(m))).strftime("%Y-%m-%dT%H:%M:%SZ") for s in start for m in range(390)]
    cols["available_utc_assuming_minute_start"] = [(s + pd.Timedelta(minutes=int(m) + 1)).strftime("%Y-%m-%dT%H:%M:%SZ") for s in start for m in range(390)]
    cols["session_date_ny"] = np.repeat(np.array(days), 390); cols["minute_index_in_session"] = np.tile(np.arange(390), n)
    el = np.ones((n, 390), int); el[:, 0] = 0; cols["SPY_return_eligible"] = el.ravel(); cols["SPY_log_return_1m"] = np.where(el == 1, R_, np.nan).ravel()
    for a, s0 in zip(ASSETS, (4e-4, 3e-4, 5e-4, 2e-4)):
        X = rng.normal(0, 1, (n, 390)) * s0 * (0.5 + 0.5 * scale)[:, None] + 0.15 * np.where(np.isfinite(R_), R_, 0.0) * (-1 if a in ("TLT", "GOLD") else 1); e = el.copy()
        if a == "DOLLAR": e[:dollar_from] = 0
        cols[f"{a}_return_eligible"] = e.ravel(); cols[f"{a}_log_return_1m"] = np.where(e == 1, X, np.nan).ravel()
    for a in ("GOLD", "DOLLAR"): cols[f"{a}_causal_flat_age_ge15_flag"] = np.zeros(n * 390, int)
    return pd.DataFrame(cols)


def run(n_train=190, n_eval=110, nboot=49, null_sets=3, draws=500, keep=None, seed=36):
    import s5_eval_loader as EL, s5_eval513 as S513, s5_eval_label as EV, s5_freeze as FZ, s5_amendment_manifest as AM, s5_h1 as H, s5_guard as G
    import s6_run as R, s6_eval as S6E, s6_fingerprint as FPM, s5_freeze_models as FM, s5_eval as V5
    real_log = EL.ACCESS_LOG; real_log_existed = real_log.exists(); t0 = time.time(); td = Path(keep) if keep else Path(tempfile.mkdtemp(prefix="a36_synth_")); td.mkdir(parents=True, exist_ok=True)
    s5res = td / "s5_results"; s6out = td / "s6_results"; s6here = td / "s6_here"
    for p in (s5res, s6out, s6here): p.mkdir(exist_ok=True)
    rng = np.random.default_rng(seed); spans, parts, dicts, days_by, panels = {}, {}, {}, {}, {}; cov_rows = []
    for era in S6E.ERAS:
        tr, ev = calendar(n_train, n_eval, EL.DEV[era][1], EL.EVAL[era][0]); days_by[era] = (tr, ev); Rs = gen_spy(tr + ev, rng)
        dicts[era] = dict(train=panel_dict(era, tr, Rs[:n_train], rng), eval=panel_dict(era, ev, Rs[n_train:], rng)); parts[era] = {**{d: "TRAIN" for d in tr}, **{d: "EVALUATION_EXPOSED" for d in ev}}
        df = canonical(era, tr + ev, Rs, rng, dollar_from=n_train // 2); p = td / f"canonical_{era}.csv.gz"; df.to_csv(p, index=False, compression="gzip"); panels[era] = p; del df
        cov_rows += [dict(era=era, day=d, asset=a, available=(a != "DOLLAR" or i >= n_train // 2)) for i, d in enumerate(tr) for a in ("SPY",) + ASSETS]
    cover = td / "coverage_sessions.csv"; pd.DataFrame(cov_rows).to_csv(cover, index=False)
    for f in ("s6_run.py", "s6_lib.py"): shutil.copy(HERE / f, s6here / f)
    fomc = td / "h1c_schedule_times_evaluation.json"; meetings = {d: dict(status="time", time_et="14:00", minute_after_0930=270, basis="synthetic") for era in S6E.ERAS for d in days_by[era][1][10::17]}
    fomc.write_text(json.dumps(dict(source="SYNTHETIC", meetings=meetings))); G.write_side(fomc)
    for det in ("gaussian_hmm", "hsmm"):
        p = s6out / f"a35_null_control_{det}.json"; p.write_text(json.dumps(dict(detector=det, passed=True, reproduces_development_run=True, SYNTHETIC=True))); G.write_side(p)
    lock = td / "ERA_CALIBRATION.lock"; fp = td / "s6_fingerprint.json"
    saved = dict(EL=(EL.PANELS, EL.LOCK, EL._preflight, EL.FINGERPRINT, EL.ACCESS_LOG, list(EL.EVAL_READS)), S513=(S513._load_span, S513.partitions, S513.FOMC_EVAL), S6E=(S6E.S5RES, S6E.OUT), R=(R.COVER, R.HERE),
                 A37=(FM.FROZEN_DIR, V5.make_model, EL.authorise))
    fits = [0]; reads = []
    checks = {}; summary = {}
    try:
        EL.PANELS = panels; EL.LOCK = lock; EL._preflight = lambda: 0; EL.FINGERPRINT = fp; EL.ACCESS_LOG = td / "eval_access_log.txt"; EL.EVAL_READS[:] = []
        S513._load_span = lambda era, first, last: {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in dicts[era]["train" if first == EL.DEV[era][0] else "eval"].items()}; S513.partitions = lambda era: parts[era]; S513.FOMC_EVAL = fomc      # a fresh panel dict per read, as the real loader
        S6E.S5RES = s5res; S6E.OUT = s6out; R.COVER = cover; R.HERE = s6here; FM.FROZEN_DIR = td / "frozen_models"
        mk0 = V5.make_model; V5.make_model = lambda *a, **k: (fits.__setitem__(0, fits[0] + 1), mk0(*a, **k))[1]           # counts every model fit
        au0 = EL.authorise
        def au(era, freeze_path, token, section6=False, what=""):
            reads.append(dict(era=era, section6=bool(section6), marker=(s5res / f"evaluation_{era}_RAN.marker").exists(), fits=fits[0])); return au0(era, freeze_path, token, section6, what)
        EL.authorise = au
        # ---- "freeze": setups of one feature; thresholds by the A11 rule on the generated TRAIN block alone
        setups, thr = {}, {}
        for era in S6E.ERAS:
            st = S513.build_state(era, {k: (v.copy() if isinstance(v, np.ndarray) else v) for k, v in dicts[era]["train"].items()}, n_train); feat = sorted(x for x in st["ctx"]["cols"] if x in st["cal"].c["kept"])[0]
            setups[era], thr[era] = {}, {}
            for fam in H.FAMILIES:
                par = dict(lam=39) if fam == "bocpd" else dict(K=2); setups[era][fam] = dict(n_features=1, features=[feat], params=par, base_params=par)
                t, rate = S513.calibrate(st, fam, [feat], par); thr[era][fam] = dict(threshold=t, validation_rate=rate, rule="A7 on the synthetic calibration sessions")
            del st
        # ---- A37 rule 1: the TRAIN refits at the freeze, hashed into the freeze document through the backend wrapper
        models = FM.write_models(setups)
        class Stub:
            kind = "synthetic"
            def input_hashes(self): return dict(synthetic="n/a")
        ih = FM.FreezeBackend(Stub(), models).input_hashes(); fits_at_freeze = fits[0]
        checks["models_hashed_into_freeze_before_any_read"] = len(ih["frozen_models"]["files"]) == 8 and not reads and not EL.EVAL_READS and fits_at_freeze >= 16
        verdicts = {f: dict(p=0.01, p_adj=0.03, reject=(f in ("gaussian_hmm", "hsmm"))) for f in H.H1_FAMILIES}; verdicts["bocpd"] = dict(p=0.5, reject=False, secondary=True)
        doc = FZ.build_freeze(setups, thr, ih, verdicts, dict(gaussian_hmm=1.0, student_t_hmm=1.2, hsmm=1.1, bocpd=1.3), "synthetic-protocol-hash", AM.freeze_ready())
        fz = FZ.write_freeze(doc, s5res); token = FZ.sha(fz); lock.write_text("synthetic\n")
        fp.write_text(json.dumps(dict(FPM.current(), created_utc="synthetic"), indent=1)); G.write_side(fp)
        checks["refused_without_token"] = _refused(lambda: S6E.run(fz, "0" * 64, nboot, null_sets, 1, draws))
        pk = FM.FROZEN_DIR / FM.file_name("LEGACY", "gaussian_hmm"); orig = pk.read_bytes(); pk.write_bytes(orig + b"x")                 # A37 5b: tampered model file
        checks["tampered_model_refused_before_marker"] = _refused(lambda: S6E.run(fz, token, nboot, null_sets, 1, draws)) and not list(s5res.glob("*_RAN.marker")) and not reads
        pk.write_bytes(orig); fits[0] = 0
        # ---- the driver, as it will run
        S6E.run(fz, token, nboot=nboot, null_sets=null_sets, workers=1, draws=draws); log_text = EL.ACCESS_LOG.read_text(encoding="utf-8"); n_reads = len(EL.EVAL_READS)
        S6E.run(fz, token, nboot=nboot, null_sets=null_sets, workers=1, draws=draws)                                   # second run: every step finds its output
        checks["second_run_reads_nothing_new"] = len(EL.EVAL_READS) == n_reads
        checks["no_model_fitted_during_evaluation"] = fits[0] == 0
        s5r = [r for r in reads if not r["section6"]]; checks["marker_exists_at_first_evaluation_read"] = len(s5r) == 2 and all(r["marker"] and r["fits"] == 0 for r in s5r)
        res5 = {era: json.loads((s5res / f"evaluation_{era}.json").read_text(encoding="utf-8")) for era in S6E.ERAS}
        det34 = "gaussian_hmm"; s6 = json.loads((s6out / f"s6_evaluation_{det34}.json").read_text(encoding="utf-8")); h2 = json.loads((s6out / f"h2_evaluation_{det34}.json").read_text(encoding="utf-8"))
        a34 = json.loads((s6out / f"a34_evaluation_{det34}.json").read_text(encoding="utf-8")); cov = json.loads((s6out / "coverage_evaluation.json").read_text(encoding="utf-8"))
        lab = lambda d: d.get("a26_label") == R.LABEL_EVAL and d.get("confirmatory") is False and d.get("period") == "evaluation"
        checks["all_results_labelled"] = all(lab(d) for d in list(res5.values()) + [s6, h2, a34, cov])
        checks["sidecars"] = all(p.with_suffix(".sha256").read_text().split()[0] == hashlib.sha256(p.read_bytes()).hexdigest() for p in list(s6out.glob("*_evaluation_*.json")) + [s6out / "coverage_evaluation.json"] + [s5res / f"evaluation_{e}.json" for e in S6E.ERAS])
        checks["no_p_value_in_513"] = not any("p_two_sided" in json.dumps(v) or '"p":' in json.dumps(v["families"]) or "holm" in json.dumps(v["families"]).lower() for v in res5.values())
        checks["frozen_thresholds_reproduced"] = all(v["families"][f]["thresholds"]["frozen_threshold_reproduced"] for v in res5.values() for f in H.FAMILIES)
        checks["evaluation_used_the_frozen_model_files"] = all(v["families"][f]["model_sha256"] == models["files"][FM.file_name(e, f)] for e, v in res5.items() for f in H.FAMILIES)
        checks["alerts_field_first"] = list(s6)[0] == "alerts" and isinstance(s6["alerts"], list)
        checks["breaks_in_evaluation_sessions_only"] = all(x["day"] in set(days_by[v["era"]][1]) for v in res5.values() for x in v["breaks"])
        checks["evaluation_sessions_complete"] = all(v["sessions"] == sorted(days_by[e][1]) and v["n_train_sessions"] == n_train for e, v in res5.items())
        checks["access_log_allowed_per_read"] = log_text.count(" ALLOWED ") == n_reads and n_reads >= 6
        checks["s6_evaluation_shape"] = "by_era" in s6 and "sens_2007" not in s6 and set(s6["by_era"]) == set(S6E.ERAS) and s6["primary"]["H3_TLT"]["holm_m"] == 6 and "bocpd" in s6["detector_dependence"]
        checks["h2_evaluation_shape"] = "by_era" in h2 and h2["primary"]["H2_TLT"]["holm_m"] == 4 and "bocpd" in h2["detector_dependence"]
        checks["marker_blocks_second_513"] = _refused(lambda: EV.run_confirmatory_labelled(fz, s5res, ["LEGACY"], S513.fit_fn, S513.run_fn, token))
        checks["unlabelled_write_refused_after_reads"] = _refused(lambda: R.write_once(td / "unlabelled.json", dict(period="development")))
        fams = {e: {f: {k: (v["families"][f][k].get("effect"), v["families"][f][k].get("ci95"), v["families"][f][k].get("skipped")) for k in ("H1a", "H1b", "H1c")} for f in H.FAMILIES} for e, v in res5.items()}
        summary = dict(n_train=n_train, n_eval=n_eval, nboot=nboot, null_sets=null_sets, draws=draws, evaluation_reads=n_reads, breaks={e: v["n_breaks_by_family_kind"] for e, v in res5.items()},
                       section5_effects=fams, s6_primary={k: dict(n=v.get("n_breaks", v.get("n")), p=v.get("p")) for k, v in s6["primary"].items()}, s6_counts=s6["counts"],
                       h2_primary={k: dict(n=v.get("n_breaks"), p=v.get("p")) for k, v in h2["primary"].items()}, coverage_rows=cov["n_rows"], access_log_lines=len(log_text.splitlines()),
                       model_fits_at_freeze=fits_at_freeze, evaluation_reads_detail=reads, alerts=s6["alerts"], positive_control=s6["sanity"]["positive_control"])
    finally:
        EL.PANELS, EL.LOCK, EL._preflight, EL.FINGERPRINT, EL.ACCESS_LOG = saved["EL"][:5]; EL.EVAL_READS[:] = saved["EL"][5]
        S513._load_span, S513.partitions, S513.FOMC_EVAL = saved["S513"]; S513._AUTH.clear(); S513._PRELOADED.clear(); S6E.S5RES, S6E.OUT = saved["S6E"]; R.COVER, R.HERE = saved["R"]
        FM.FROZEN_DIR, V5.make_model, EL.authorise = saved["A37"]
        if not keep: shutil.rmtree(td, ignore_errors=True)
    checks["real_access_log_untouched"] = real_log.exists() == real_log_existed
    return dict(label="AMENDMENT_A36 rule 7a / AMENDMENT_A37 rule 5b synthetic end-to-end run of the joint evaluation driver (SYNTHETIC DATA ONLY; no market file, no evaluation-period row)", SYNTHETIC=True,
                passed=bool(checks) and all(checks.values()), checks=checks, summary=summary, seconds=round(time.time() - t0, 1), generated=datetime.datetime.now(datetime.timezone.utc).isoformat())


def _refused(fn):
    try: fn()
    except (PermissionError, RuntimeError, SystemExit): return True
    return False


def main():
    import s6_run as R, s6_eval as S6E
    a = sys.argv[1:]; arg = lambda k, dflt: int(a[a.index(k) + 1]) if k in a else dflt; out = HERE / "results" / "a37_synth_e2e.json"
    if out.exists(): print("result exists; written once"); return 3
    res = run(arg("--train", 190), arg("--eval", 110), arg("--nboot", 49), arg("--null-sets", 3), arg("--draws", 500), keep=(a[a.index("--keep") + 1] if "--keep" in a else None))
    for k, v in res["checks"].items(): print(("PASS " if v else "FAIL ") + k)
    print(json.dumps(res["summary"], indent=1, default=float)[:3000])
    if res["passed"]: res["provenance"] = R.provenance(); res["provenance"]["amendments_evaluation_path"] = list(S6E.AMENDMENTS); R.write_once(out, res); print(f"written {out}")
    return 0 if res["passed"] else 1


if __name__ == "__main__": sys.exit(main())
