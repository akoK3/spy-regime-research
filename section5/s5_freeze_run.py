#!/usr/bin/env python3
"""The 5.12 freeze, the single sanctioned entry (PREFREEZE_AUDIT H1, M1, M2; AMENDMENT_A37 rule 1). Outside the code-version closure (a0323ed24d68e896); closure
functions are called, never edited. No other script may call s5_run.freeze_step( directly (s5_tests_freeze_run: only this driver, the definition, the temp-dir
rehearsals and the unit tests).

freeze(backend, summ, results_dir, amendments, frozen_dir, staging) does, in order:
  1. prechecks before anything is fitted (M1): no freeze and no evaluation output exists; the amendment list equals s5_amendment_manifest.freeze_ready(); the
     completion record verifies; the protocol, contamination-list, code-version and fold checks of s5_run.freeze_step; a final setup for every era and family;
  2. feature parity (M2): the 5.13 feature path against the main-run era context on each era's TRAIN span (s5_feature_parity); any difference stops;
  3. the TRAIN refits into a STAGING directory (A37 1b; s5_freeze_models.write_models). A staged set that verifies (manifest sidecar, file hashes, setups, code
     version, TRAIN sessions) is reused, never refitted, so a failed freeze can be retried; an unverifiable staging set is discarded and refitted;
  4. s5_run.freeze_step through a backend wrapper that adds the staged models' hashes to the input hashes (A37 1e) and compares every era threshold with the
     threshold recomputed on the 5.13 path at the fit (M2): a difference above the bisection tolerance stops BEFORE the freeze document is written. The era
     calibration (and its lock) happens inside freeze_step, as before; it does not refuse on a retry;
  5. only after the freeze document exists: the staging directory is moved to the frozen-model directory, its hashes are checked against the freeze document,
     and s5_eval513.load_frozen must succeed for both eras. If the freeze exists and the models are still staged (a crash between 4 and 5), a rerun completes 5.
  6. a record of the run (parity, threshold comparison, staging reuse, timings), written once next to the freeze.
Usage: s5_freeze_run.py check                 (no fit, no write: the prechecks and the expected detectors)
       s5_freeze_run.py run --confirm FREEZE    (the real freeze; NOT run before the user says so)"""
import sys, os, json, time, shutil, pickle, hashlib, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
RESULTS = HERE / "results"; MR2 = RESULTS / "main_run_2"; FREEZE_NAME = "section5_freeze.json"; RECORD_NAME = "freeze_run_record.json"; STAGING_NAME = "frozen_models.staging"
ERAS = ("LEGACY", "RAW")


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load_summary(run_dir=MR2):
    """The MR2 run summary (pinned: main_run_2), with its run_dir pointing at the directory it was read from."""
    run_dir = Path(run_dir); s = json.loads((run_dir / "run_summary.json").read_text(encoding="utf-8"))
    if Path(s["run_dir"]).resolve() != run_dir.resolve(): raise PermissionError(f"run summary's run_dir {s['run_dir']} is not {run_dir}")
    if not s.get("complete"): raise PermissionError("the main run is not complete")
    return s


def prechecks(backend, summ, results_dir, amendments):
    import s5_guard as G, s5_freeze as FZ, s5_amendment_manifest as AM, s5_h1 as H
    rd = Path(results_dir)
    if (rd / FREEZE_NAME).exists(): raise FileExistsError(f"{FREEZE_NAME} exists")
    if list(rd.glob(FZ.EVAL_PREFIX + "*")): raise RuntimeError("evaluation output exists; the freeze must precede it (5.12)")
    if amendments != AM.freeze_ready(): raise PermissionError("the amendment list passed differs from s5_amendment_manifest.freeze_ready()")
    rec_path = Path(summ["run_dir"]) / G.COMPLETION; rec = G.verify_completion(rec_path, require_main=(getattr(backend, "kind", None) == "main")); ph = G.frozen_protocol_hash(); _, ch = G.canonical_contamination()
    if rec["protocol_sha256"] != ph or summ.get("protocol_sha256") != ph or getattr(backend, "protocol_sha256", ph) != ph: raise PermissionError("protocol hash of run, backend and FROZEN protocol differ (A16 rule 6)")
    if rec["contamination_sha256"] != ch or summ.get("contamination_sha256") != ch: raise PermissionError("the run used another contamination list (A16 rule 2)")
    if rec["code_version"] != summ.get("code_version") or rec["folds"] != summ.get("folds"): raise PermissionError("run summary does not match its completion record")
    if rec["code_version"] != G.code_version(): raise PermissionError("the completion record's code version differs from the code on disk")
    missing = [f"{e}/{f}" for e in ERAS for f in H.FAMILIES if f not in (summ.get("final_setups") or {}).get(e, {})]
    if missing: raise PermissionError(f"no final setup for {missing}")
    return rec_path


def staged(staging, setups):
    """(record, {era: {family: feature threshold recomputed at the fit}}) if the staging directory holds a complete, verifiable set for these setups; else None."""
    import s5_freeze_models as FM, s5_guard as G, s5_eval513 as S513
    try: rec = FM.frozen_hashes(staging)
    except Exception: return None
    rc = {}; cv = G.code_version()
    for era in sorted(setups):
        part = S513.partitions(era); tr = sorted(x for x, q in part.items() if q == "TRAIN"); rc[era] = {}
        for fam, s in setups[era].items():
            name = FM.file_name(era, fam); p = Path(staging) / name
            if name not in rec["files"] or not p.exists() or sha(p) != rec["files"][name]: return None
            b = pickle.loads(p.read_bytes())
            if (b["era"], b["family"], list(b["features"]), dict(b["params"]), dict(b["base_params"])) != (era, fam, list(s["features"]), dict(s["params"]), dict(s.get("base_params") or s["params"])): return None
            if b.get("code_version") != cv or (b["n_train"], b["train_first"], b["train_last"]) != (len(tr), tr[0], tr[-1]): return None
            rc[era][fam] = float(b["thresholds"]["feature_recomputed"])
    return rec, rc


def stage(staging, setups, log):
    """Reuse a verifiable staging set; otherwise discard it and fit (A37 1b) into staging."""
    import s5_freeze_models as FM
    st = staged(staging, setups)
    if st is not None: log["staging"] = "reused (verified; no refit)"; return st
    if Path(staging).exists(): shutil.rmtree(staging); log["staging_discarded"] = True
    t0 = time.time(); FM.write_models(setups, staging); log["fit_seconds"] = round(time.time() - t0, 1); log["staging"] = "fitted"
    st = staged(staging, setups)
    if st is None: raise RuntimeError("the staged models do not verify right after the fit")
    return st


def _checked_backend(backend, models, recomputed, rows):
    import s5_freeze_models as FM, s5_a7 as B

    class CheckedFreezeBackend(FM.FreezeBackend):
        """FreezeBackend (A37 1e) that compares each era threshold with the 5.13-path recomputation before freeze_step can write (PREFREEZE_AUDIT M2)."""
        def era_thresholds(self, era, family, setup, completion):
            r = self._b.era_thresholds(era, family, setup, completion); tol = B.BOUNDS["bocpd" if family == "bocpd" else "hmm"][2]
            thr, rc = float(r["threshold"]), float(recomputed[era][family]); diff = abs(thr - rc)
            rows.append(dict(era=era, family=family, era_threshold=thr, recomputed_513_path=rc, abs_diff=diff, tolerance=tol, ok=bool(diff <= tol)))
            if diff > tol: raise PermissionError(f"{era}/{family}: era threshold {thr} differs from the 5.13-path recomputation {rc} by {diff} > {tol}: freeze stopped before writing")
            return r
    return CheckedFreezeBackend(backend, models)


def promote(staging, final, doc):
    """Move the staged models to the frozen-model directory and check them against the freeze document; load_frozen must succeed for both eras."""
    import s5_freeze_models as FM, s5_eval513 as S513
    final = Path(final)
    if final.exists() and any(final.iterdir()): raise FileExistsError(f"{final} is not empty")
    if final.exists(): final.rmdir()
    final.parent.mkdir(parents=True, exist_ok=True); os.replace(staging, final)
    rec = doc["input_hashes"]["frozen_models"]; now = FM.frozen_hashes(final)
    if now["manifest_sha256"] != rec["manifest_sha256"] or now["files"] != rec["files"]: raise PermissionError("the moved models differ from the freeze document")
    for era in ERAS: S513.load_frozen(era, doc, final)
    return True


def freeze(backend, summ, results_dir, amendments, frozen_dir=None, staging=None, parity=True):
    """Returns (freeze path, doc, record). See the module docstring for the order."""
    import s5_freeze as FZ, s5_freeze_models as FM, s5_run as RUN, s5_feature_parity as FP, s5_eval513 as S513, s5_eval_loader as EL, s5_guard as G
    rd = Path(results_dir); final = Path(frozen_dir or FM.FROZEN_DIR); staging = Path(staging or rd / STAGING_NAME); fzp = rd / FREEZE_NAME; t0 = time.time()
    if fzp.exists():      # step 5 after a crash between the freeze document and the move
        try: doc = FZ.verify_freeze(fzp)
        except Exception as e: raise FileExistsError(f"{FREEZE_NAME} exists and does not verify ({e}): the user decides")
        rec = (doc.get("input_hashes") or {}).get("frozen_models")
        if rec and final.exists():
            try:
                if FM.frozen_hashes(final)["manifest_sha256"] == rec["manifest_sha256"]: raise FileExistsError("the freeze is complete (document and frozen models)")
            except PermissionError: pass
        if rec and staging.exists() and FM.frozen_hashes(staging)["manifest_sha256"] == rec["manifest_sha256"]:
            promote(staging, final, doc); return fzp, doc, dict(resumed="models moved after an interrupted freeze")
        raise PermissionError("a freeze exists but its models are neither in place nor staged: the user decides")
    log = dict(kind="freeze_run_record", started=datetime.datetime.now(datetime.timezone.utc).isoformat()); rows = []
    rec_path = prechecks(backend, summ, rd, amendments); log["completion_record_sha256"] = sha(rec_path); setups = summ["final_setups"]
    if parity:
        log["feature_parity"] = {}
        for era in ERAS:
            EL.check_dev_spans(); r = FP.parity(era, ctx_main=backend._ctx(era) if hasattr(backend, "_ctx") else None); log["feature_parity"][era] = dict(passed=r["passed"], failed=[k for k, v in r["fields"].items() if not v["equal"]], sessions=r["sessions"])
            if not r["passed"]: raise PermissionError(f"{era}: the 5.13 feature path differs from the main-run era context (PREFREEZE_AUDIT M2): {log['feature_parity'][era]}")
    models, recomputed = stage(staging, setups, log)
    fz_path, doc = RUN.freeze_step(_checked_backend(backend, models, recomputed, rows), summ, rd, amendments)
    log["threshold_comparison"] = rows; promote(staging, final, doc)
    log.update(freeze_sha256=sha(fz_path), frozen_models_manifest_sha256=doc["input_hashes"]["frozen_models"]["manifest_sha256"], h2_primary_detector=doc.get("h2_primary_detector"),
               h1_passing_families=doc.get("h1_passing_families"), seconds=round(time.time() - t0, 1), finished=datetime.datetime.now(datetime.timezone.utc).isoformat())
    rp = rd / RECORD_NAME
    if not rp.exists(): rp.write_text(json.dumps(log, indent=1, default=float), encoding="utf-8"); G.write_side(rp)
    return fz_path, doc, log


def check():
    """No fit, no write: the prechecks against MR2 and the expected detectors."""
    import s5_main as MB, s5_guard as G, s5_amendment_manifest as AM, s5_freeze as FZ
    summ = load_summary(); b = MB.MainBackend(G.frozen_protocol_hash()); prechecks(b, summ, RESULTS, AM.freeze_ready())
    passing = [f for f, v in summ["holm"]["confirmatory"].items() if v.get("reject") and not v.get("secondary")]
    print(json.dumps(dict(prechecks="passed", h1_passing=passing, h2_primary_expected=FZ.h2_primary(passing, summ["median_validation_qlike"]), lock_exists=G.LOCK.exists()), indent=1)); return 0


def main():
    a = sys.argv[1:]
    if a[:1] == ["check"]: return check()
    if a[:1] == ["run"] and "--confirm" in a and a[a.index("--confirm") + 1] == FREEZE_NAME:
        import s5_main as MB, s5_guard as G, s5_amendment_manifest as AM
        summ = load_summary(); b = MB.MainBackend(G.frozen_protocol_hash()); p, doc, log = freeze(b, summ, RESULTS, AM.freeze_ready()); print(f"written {p}"); return 0
    print(__doc__); return 3


if __name__ == "__main__": sys.exit(main())
