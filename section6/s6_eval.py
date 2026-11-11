#!/usr/bin/env python3
"""AMENDMENT_A36: the joint evaluation driver. One run, in this order, after the 5.12 freeze (which includes the era calibration and its lock):
  0. guards: A28-A36 ADOPTED with matching sidecars; contamination registry; the freeze verifies and the token is its sha256; the evaluation FOMC list exists with
     its sidecar (rule 3c); the Section 6 fingerprint exists and equals the code on disk (rule 7c); the H2 and H3/H4 primary detectors are determined (rule 2d).
  1. Section 5 5.13 per era through s5_eval_label.run_confirmatory_labelled with s5_eval513.fit_fn / run_fn (rule 5): effects with intervals, no p; break export.
  2. label-free coverage of the evaluation sessions (rule 6a), before any break time or asset outcome is used there.
  3. Section 6 on the evaluation periods (rules 1, 2, 4, 6): H3/H4 (s6_run.analyse, evaluation=True), H2 (s6_h2.analyse, per_era=True), A34 parts.
Every result carries the A26 label and confirmatory = False; every evaluation read goes through s5_eval_loader (guard, access log). A finished step is not repeated
(outputs are written once); a 5.13 era whose one-shot marker exists without a result stops the driver.
Evaluation eras (rule 4b): each is preceded by the last 60 TRAIN sessions of its era as history (20-session medians, prior-day control, burn-in count); units,
candidate times, placebo draws, cut points, pools and alarms come from evaluation sessions only (4c). The embargo sessions are never read (1e).
Usage: s6_eval.py plan FREEZE_PATH                                  (no data read: prints the detectors and what would run)
       s6_eval.py run FREEZE_PATH CONFIRM_TOKEN [--workers N]      (CONFIRM_TOKEN = sha256 of the freeze file)
Nothing here runs before the user says so. The synthetic end-to-end run is s6_eval_synth.py."""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "section5"))
import s6_lib as L, s6_run as R

AMENDMENTS = ("A28", "A29", "A30", "A31", "A32", "A33", "A33_1", "A34", "A35", "A36"); ERAS = ("LEGACY", "RAW"); N_HIST = 60
S5RES = ROOT / "section5" / "results"; OUT = HERE / "results"; H1_ORDER = ("gaussian_hmm", "student_t_hmm", "hsmm")


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def log(msg): print(f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [s6_eval] {msg}", flush=True)
def label(res): return dict(res, period="evaluation", a26_label=R.LABEL_EVAL, confirmatory=False)


def provenance(freeze_path):
    import s6_fingerprint as FP, s5_amendment_manifest as AM, s5_eval513 as S513
    return dict(code=FP.current(), amendments=AM.manifest(AMENDMENTS), freeze_sha256=sha(freeze_path), fomc_list_sha256=sha(S513.FOMC_EVAL))


# ---------- detectors (A36 2d; A28 1b; A35 rule 3)
def a35_status(det, out=None):
    """The A35 rule 2 rerun of the 7d null control for one detector: (passed, reproduces); the file must equal its sidecar."""
    p = (out or OUT) / f"a35_null_control_{det}.json"; side = p.with_suffix(".sha256")
    if not p.exists() or not side.exists() or side.read_text().split()[0] != sha(p): raise PermissionError(f"{p.name} missing or differs from its sidecar: the A35 rule 2 rerun must exist before the evaluation")
    d = json.loads(p.read_text(encoding="utf-8")); return bool(d["passed"]), bool(d["reproduces_development_run"])


def h34_primary(fz, status=a35_status):
    """A28 1b: the H2 primary detector of the freeze, or (no family passes H1) the H1 family with the lowest median validation QLIKE, ties to the simpler model.
    A35 rule 3: a Gaussian HMM that failed the rerun is replaced by the HSMM (3a); an HSMM that failed stops the work (3d). Returns (detector, reason)."""
    det = fz.get("h2_primary_detector"); why = "the H2 primary detector of the freeze (A28 1b)"
    if det is None:
        q = fz.get("median_validation_qlike") or {}; c = [f for f in H1_ORDER if f in q and np.isfinite(q[f])]
        if not c: raise PermissionError("no H1 family with a median validation QLIKE in the freeze")
        det = sorted(c, key=lambda f: (q[f], H1_ORDER.index(f)))[0]; why = "no family passes H1: the H1 family with the lowest median validation QLIKE (A28 1b fallback)"
    for d in ("gaussian_hmm", "hsmm"):
        if not status(d)[1]: raise PermissionError(f"the A35 rerun of {d} does not reproduce the development run (A35 2d): work stops")
    if not status("hsmm")[0]: raise PermissionError("the HSMM failed the A35 rerun of the 7d null control: A28 7d applies as written, work stops and the user decides (A35 3d)")
    if det == "gaussian_hmm" and not status("gaussian_hmm")[0]: det = "hsmm"; why = "the Gaussian HMM failed the A35 rerun of the 7d null control: the HSMM is the H3/H4 primary (A35 3a)"
    return det, why


# ---------- evaluation coverage (A36 6a)
def coverage(freeze, token, out=None):
    """{(era, day, asset): available} for the evaluation sessions; computed once (label-free: no break time, alarm or outcome), written once with the label."""
    import s6_coverage as C, s5_eval_loader as EL
    p = (out or OUT) / "coverage_evaluation.json"
    if not p.exists():
        cols = [f"{a}_{k}" for a in C.ASSETS for k in ("return_eligible", "log_return_1m")] + [f"{a}_causal_flat_age_ge15_flag" for a in C.QUOTES]; rows = []
        for era in ERAS:
            df = EL.load_eval(era, cols, freeze, token, section6=True)
            for day, g in df.groupby("session_date_ny", sort=True):
                for a in C.ASSETS: m = C.session_metrics(g, a); rows.append(dict(era=era, day=str(day), asset=a, **m, available=C.available(m, a)))
            del df
        R.write_once(p, label(dict(label="A36 6a / A28 6b label-free coverage check, evaluation sessions", rule=dict(min_usable=C.MIN_USABLE, max_gap_min=C.MAX_GAP, max_stale_quotes=C.MAX_STALE),
                                   n_rows=len(rows), rows=rows, generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=provenance(freeze))))
    side = p.with_suffix(".sha256")
    if not side.exists() or side.read_text().split()[0] != sha(p): raise PermissionError("coverage_evaluation.json differs from its sidecar")
    return {(r["era"], r["day"], r["asset"]): bool(r["available"]) for r in json.loads(p.read_text(encoding="utf-8"))["rows"]}


# ---------- data: one evaluation era = 60 history sessions (TRAIN) + the evaluation sessions (A36 4b, 4c)
def eval_era(era, freeze, token, cov):
    import s5_eval_loader as EL
    dev = R.load_era(era, "development"); h = slice(len(dev.days) - N_HIST, len(dev.days)); hist = list(dev.days[h])
    cols = [f"{a}_{k}" for a in ("SPY",) + R.ASSETS for k in ("return_eligible", "log_return_1m")]
    df = EL.load_eval(era, cols, freeze, token, section6=True); av = {k: v for k, v in cov.items() if k[0] == era}; Ev = R.EraData(era, df, av); del df
    if len(hist) != N_HIST or not hist[-1] < Ev.days[0]: raise RuntimeError(f"{era}: history does not precede the evaluation sessions")
    for a in R.ASSETS:
        for d, ok in zip(hist, dev.avail[a][h]): av[(era, d, a)] = bool(ok)
    E = R.EraData.from_arrays(era, hist + list(Ev.days), {a: np.vstack([dev.R[a][h], Ev.R[a]]) for a in ("SPY",) + R.ASSETS}, av); E.n_history = N_HIST; return E


def breaks(s5res=None):
    """(rows, sessions) of the 5.13 break export (A36 5h) from the labelled per-era results."""
    import s5_eval_label as EV, s5_freeze as FZ
    d5 = s5res or S5RES; EV.verify_labelled(d5); rows, sess = [], {}
    for era in ERAS:
        d = json.loads((d5 / f"{FZ.EVAL_PREFIX}{era}.json").read_text(encoding="utf-8"))
        if d.get("kind") != "section5_513_evaluation" or d.get("era") != era: raise PermissionError(f"evaluation_{era}.json is not a 5.13 result of this driver")
        rows += d["breaks"]; sess[f"{era}|EVAL"] = d["sessions"]
    return rows, sess


def fed_fn_of(minutes):
    """A36 3d: S within the 60 minutes after the release on an evaluation FOMC day."""
    def f(units):
        for u in units: m = minutes.get(u["day"]); u["fed"] = m is not None and m <= u["S"] <= m + 60
        return units
    return f


def check_units(E_by, rows, sess):
    """A36 4c: every unit, candidate and placebo of the primary detector lies in an evaluation session (never in a history session)."""
    for era, E in E_by.items():
        u, c, al = R.build(E, [x for x in rows if x["era"] == era], sess); R.attach_placebos(u, c, al); n = E.n_history
        if (len(c["day_idx"]) and c["day_idx"].min() < n) or any(x["day_idx"] < n for x in u) or any(p["day_idx"] < n for x in u for p in x["placebos"]): raise RuntimeError(f"{era}: a unit, candidate or placebo lies in a history session")
    return True


# ---------- Section 6 on the evaluation periods
def section6(freeze, token, det34, det2, minutes, nboot=L.NBOOT, null_sets=200, workers=1, draws=None, out=None, s5res=None):
    import s6_h2 as H, s6_a34 as A34
    out = out or OUT; draws = draws or H.B50; targets = {"s6": out / f"s6_evaluation_{det34}.json", "a34": out / f"a34_evaluation_{det34}.json"}
    if det2 is not None: targets["h2"] = out / f"h2_evaluation_{det2}.json"
    if all(p.exists() for p in targets.values()): log("Section 6 evaluation outputs exist (written once)"); return targets
    cov = coverage(freeze, token, out); allrows, sess = breaks(s5res); E_by = {era: eval_era(era, freeze, token, cov) for era in ERAS}
    pick = lambda det: [x for x in allrows if x["family"] == det]; check_units(E_by, pick(det34), sess); stamp = lambda: datetime.datetime.now(datetime.timezone.utc).isoformat()
    common = dict(history_sessions_per_era=N_HIST, n_sessions={e: len(E.days) - N_HIST for e, E in E_by.items()}, provenance=provenance(freeze))
    if not targets["s6"].exists():
        res = R.analyse(E_by, pick(det34), sess, nboot, det34, allrows, null_sets=null_sets, workers=workers, fed_fn=fed_fn_of(minutes), evaluation=True)
        res.update(common, nboot=nboot, null_sets=null_sets, generated=stamp(), sanity_note="reported, not a gate, on the evaluation periods (A36 2c)")
        R.write_once(targets["s6"], label(res)); log(f"written {targets['s6'].name}")
    if det2 is not None and not targets["h2"].exists():
        res = H.analyse(E_by, pick(det2), sess, nboot, det2, allrows, B=draws, per_era=True); res.update(common, nboot_exploratory=nboot, draws_primary=draws, generated=stamp())
        res["label"] = "H2 (AMENDMENT_A33: protocol 5.0 primary; evaluation periods, A36)"; R.write_once(targets["h2"], label(res)); log(f"written {targets['h2'].name}")
    if not targets["a34"].exists():
        res = A34.analyse(E_by, pick(det34), sess, nboot, det34); res.update(common, nboot=nboot, generated=stamp()); R.write_once(targets["a34"], label(res)); log(f"written {targets['a34'].name}")
    return targets


# ---------- the driver
def guards(freeze, token=None):
    import s5_freeze as FZ, s5_eval_loader as EL, s5_eval513 as S513, s5_contamination as CT
    R.a29_guard(AMENDMENTS); CT.check_registry(); fz = FZ.verify_freeze(freeze)
    if token is not None and token != FZ.sha(freeze): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    minutes = S513.fomc_minutes(); EL.fingerprint_check(); det34, why = h34_primary(fz, lambda d: a35_status(d, OUT))
    return fz, minutes, fz.get("h2_primary_detector"), det34, why


def run(freeze, token, nboot=L.NBOOT, null_sets=200, workers=1, draws=None):
    import s5_freeze as FZ, s5_eval_label as EV, s5_eval513 as S513, s5_guard as G
    fz, minutes, det2, det34, why = guards(freeze, token); log(f"guards passed; H2 primary detector {det2}; H3/H4 primary detector {det34}: {why}")
    for era in ERAS:                                                                    # 1. Section 5 5.13 (A36 rule 5)
        res = S5RES / f"{FZ.EVAL_PREFIX}{era}.json"; marker = S5RES / f"{FZ.EVAL_PREFIX}{era}_RAN.marker"
        if res.exists(): log(f"5.13 {era}: result exists (one run per era)"); continue
        if marker.exists(): raise SystemExit(f"5.13 {era}: the one-shot marker exists without a result: that run started and did not finish; no re-run (5.13); the user decides")
        S513._AUTH[era] = (str(freeze), token); log(f"5.13 {era}: start")
        try: EV.run_confirmatory_labelled(freeze, S5RES, [era], S513.fit_fn, S513.run_fn, token)
        finally: S513._AUTH.pop(era, None)
        G.write_side(res); log(f"5.13 {era}: written {res.name}")
    EV.verify_labelled(S5RES)
    t = section6(freeze, token, det34, det2, minutes, nboot, null_sets, workers, draws)   # 2-3. coverage, then Section 6 (A36 rule 6)
    log("DONE: " + ", ".join(p.name for p in t.values())); return 0


def plan(freeze):
    fz, minutes, det2, det34, why = guards(freeze)
    print(json.dumps(dict(freeze=str(freeze), h2_primary_detector=det2, h34_primary_detector=det34, h34_reason=why, n_evaluation_fomc_days_with_time=len(minutes),
                          steps=["5.13 LEGACY", "5.13 RAW", "evaluation coverage", f"s6_evaluation_{det34}", f"h2_evaluation_{det2}", f"a34_evaluation_{det34}"]), indent=1)); return 0


def main():
    a = sys.argv[1:]
    if len(a) >= 2 and a[0] == "plan": return plan(Path(a[1]))
    if len(a) >= 3 and a[0] == "run": return run(Path(a[1]), a[2], workers=int(a[a.index("--workers") + 1]) if "--workers" in a else 1)
    print(__doc__); return 3


if __name__ == "__main__": sys.exit(main())
