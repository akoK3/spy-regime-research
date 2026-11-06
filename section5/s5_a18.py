#!/usr/bin/env python3
"""A18 (pre-registered sensitivity): 5.8 selection rerun with the objective = mean negative one-step-ahead predictive log-likelihood of the next 5-min SPY return on validation; everything
else identical (greedy, 1% rule, tuning, baseline tuning, scoring, tests). Runs through s5_run.run_all with a backend of kind 'a18-<script hash>' (its completion record can never verify as main).
Usage: s5_a18.py PROTOCOL_SHA256 [--check]      --check: guards + objective and selection smoke test on the contaminated RAW 3 fold (nothing written to results/a18).
Exit codes: 0 done, 1 crash (retryable; resumes from checkpoints), 2 Ctrl+C, 3 guard refusal."""
import sys, json, time, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_a17_a18_common as CM, s5_backend as BK, s5_main as MB
from s5_a17_a18_common import log

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "a18"; RUN_DIR = OUT / "run"
KIND = "a18-" + CM.file_sha(__file__)[:8] + CM.file_sha(CM.__file__)[:8]                           # checkpoint keys change with this script or the shared code


class A18Fold(BK.DataBackend):
    kind = KIND

    def objective(self, fold, family):
        import s5_guard as G
        self._chk(fold); G.check_unlocked("selection")
        def f(subset, params, starts):
            m = self.fit(family, subset, params, starts); nll, n = CM.mean_nll(family, m, self.sequences("val", subset), 1 + len(subset))
            return dict(qlike=nll, delay=float("nan"), n_scored=n)                                      # 'qlike' is the slot s5_select minimises: here it holds the A18 NLL
        return f


class A18Main(MB.MainBackend):
    kind = KIND

    def _b(self, fold):
        if self._cur is None or self._cur.id != fold:
            import gc
            era, n = fold.split("|"); self._cur = None; gc.collect(); self._cur = A18Fold(era, int(n), allowed=set(self.ids), protocol_sha256=self.protocol_sha256, shared=self._ctx(era))
        return self._cur


class Logged:
    def __init__(self, b): self._b = b; self._seen = []; self._t0 = None
    def __getattr__(self, n): return getattr(self._b, n)
    def _fold(self, fold):
        if fold not in self._seen: self._seen.append(fold); log(f"A18 fold {len(self._seen)}/34 {fold}: start")
    def objective(self, fold, family): self._fold(fold); self._t0 = time.time(); return self._b.objective(fold, family)
    def score(self, fold, family, setup):
        self._fold(fold); sel = f"selection {(time.time() - self._t0) / 60:.1f} min" if self._t0 else "selection from checkpoint"; self._t0 = None; t0 = time.time(); r = self._b.score(fold, family, setup)
        log(f"  A18 {fold} {family}: {sel}; features {setup['features']} params {setup['params']} baseline {setup['base_params']}; scoring {(time.time() - t0) / 60:.1f} min"); return r


def guards(token):
    import s5_guard as G, s5_contamination as C
    ph = G.verify_frozen_protocol(token); G.verify_completion(HERE / "results" / "main_run" / G.COMPLETION, require_main=True); G.canonical_contamination()
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    C.check_registry(HERE); log(f"A18 guards: protocol {ph[:16]}..., main record verified, canonical list, no lock, registry ok; backend kind {KIND}"); return ph


def preflight(token):
    import s5_run as RUN, s5_lib as L
    ph = guards(token); OUT.mkdir(parents=True, exist_ok=True); db = A18Fold("RAW", 3); t0 = time.time()
    for fam in ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"):
        f = db.objective("RAW|3", fam); r0 = f((), dict(K=3, lam=39), 1); c = db.candidates("RAW|3")[0]; r1 = f((c,), dict(K=3, lam=39), 1)
        if not (np.isfinite(r0["qlike"]) and np.isfinite(r1["qlike"]) and r0["n_scored"] > 1000): raise RuntimeError(f"A18 objective not finite for {fam}: {r0} {r1}")
        log(f"A18 preflight: RAW 3 {fam}: NLL return-only {r0['qlike']:.4f} ({r0['n_scored']} bars), + {c} {r1['qlike']:.4f}")
    class One:
        kind = "check"
        def objective(self, fold, family): return db.objective(fold, family)
        def candidates(self, fold): return db.candidates(fold)
        def param_grid(self, family): return db.param_grid(family)
        def score(self, fold, family, setup): return db.score(fold, family, setup)
    st = RUN.select_fold(One(), "RAW|3", "gaussian_hmm"); sc = RUN.score_fold(One(), "RAW|3", "gaussian_hmm", st)
    log(f"A18 preflight: RAW 3 Gaussian HMM selection {st['features']} K={st['params']} baseline {st['base_params']}; H1(a) {sc['a']}, H1(b) {sc['b']}; {(time.time() - t0) / 60:.1f} min; nothing written to results/a18")
    n = len(list((RUN_DIR / "ckpt").glob("*.json"))) if (RUN_DIR / "ckpt").exists() else 0; log(f"A18 preflight: {n} of 272 A18 checkpoint units exist for any version")
    return ph


def analyse(summ):
    import s5_h1 as H, s5_guard as G, s5_posthoc_main as PH
    per = summ["_per_fold"]; folds = summ["folds"]; excluded = set(summ["excluded"]); main = {}
    for p in (HERE / "results" / "main_run" / "ckpt").glob("*.json"):
        c = json.loads(p.read_text(encoding="utf-8")); k = c["key"].split("|")
        if k[0] == "select": main[(f"{k[3]}|{k[4]}", k[5])] = c["value"]["features"]
    out = dict(label="A18 pre-registered sensitivity (selection by one-step-ahead predictive log-likelihood)", d1={}, nonvol_share={}, h1={})
    for fam in H.FAMILIES:
        sets = {f: per[fam][f]["setup"]["features"] for f in folds}; fams = {f: [PH.family_of(c) for c in s] for f, s in sets.items()}
        nonvol = lambda fs: any(x in CM.NONVOL_FAMILIES for x in fs); mainf = {f: [PH.family_of(c) for c in main[(f, fam)]] for f in folds}
        from collections import Counter
        out["d1"][fam] = dict(mean_features=float(np.mean([len(s) for s in sets.values()])), folds_with_no_feature=sum(1 for s in sets.values() if not s),
                              feature_frequency=dict(Counter(c for s in sets.values() for c in s).most_common()), family_frequency_folds=dict(Counter(x for fs in fams.values() for x in set(fs)).most_common()),
                              same_family_coselection_folds=dict(Counter(x for fs in fams.values() for x, n in Counter(fs).items() if n >= 2).most_common()),
                              same_features_as_main_run_folds=sum(1 for f in folds if sorted(sets[f]) == sorted(main[(f, fam)])), per_fold=sets)
        out["nonvol_share"][fam] = dict(all_folds=sum(nonvol(fams[f]) for f in folds) / len(folds), confirmatory=sum(nonvol(fams[f]) for f in folds if f not in excluded) / sum(1 for f in folds if f not in excluded),
                                        main_run_all_folds=sum(nonvol(mainf[f]) for f in folds) / len(folds))
        out["h1"][fam] = {w: dict(H1a=summ["family_results"][fam][w]["H1a"], H1b=summ["family_results"][fam][w]["H1b"], p_iu=summ["family_results"][fam][w]["p_iu"], holm=summ["holm"][w][fam]) for w in ("confirmatory", "all_folds_sensitivity")}
    return out


def main():
    if len(sys.argv) < 2: print("usage: s5_a18.py PROTOCOL_SHA256 [--check]"); return CM.EXIT_GUARD
    token, check = sys.argv[1], "--check" in sys.argv[2:]
    try:
        if check: preflight(token); log("A18 preflight passed (--check): A18 NOT started"); return CM.EXIT_OK
        ph = guards(token)
    except (PermissionError, RuntimeError, AssertionError) as e: log(f"A18 REFUSED (not retryable): {type(e).__name__}: {e}"); return CM.EXIT_GUARD
    import s5_run as RUN
    CM.keep_awake(True); t0 = time.time(); log(f"A18 start (resumes from checkpoints in {RUN_DIR})")
    try:
        summ = RUN.run_all(Logged(A18Main(ph)), RUN_DIR); res = analyse(summ); res.update(kind=KIND, completion_record=summ["completion_record"], hours=(time.time() - t0) / 3600)
        (OUT / "a18_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); log(f"A18 DONE in {(time.time() - t0) / 3600:.2f} h; results/a18/a18_results.json written"); return CM.EXIT_OK
    except PermissionError as e: log(f"A18 REFUSED (not retryable): {e}"); return CM.EXIT_GUARD
    except KeyboardInterrupt: log("A18 STOPPED by the user (Ctrl+C); finished units are checkpointed"); return CM.EXIT_STOP
    except BaseException as e:
        log(f"A18 CRASH after {(time.time() - t0) / 60:.1f} min: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return CM.EXIT_CRASH
    finally: CM.keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
