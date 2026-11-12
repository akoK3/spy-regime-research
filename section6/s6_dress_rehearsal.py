#!/usr/bin/env python3
"""PREFREEZE_AUDIT M3 dress rehearsal (user instruction 2026-11-11). DEVELOPMENT DATA ONLY: no evaluation-period row is read, and the real lock, freeze, frozen-model
directory, access log and fingerprint are never touched.
Per era, the real TRAIN sessions are split into a fake TRAIN (all but the last 125), 5 fake embargo sessions and a fake evaluation tail (the last 120). With the
span constants, the split map, the lock path and every output directory redirected to a temporary directory, the real code runs end to end:
  1. the freeze driver s5_freeze_run.freeze on the real main backend (MR2 completion record, MR2 final setups, era calibration by EraBackend on the main-run era
     context cut to the fake TRAIN), with the feature-parity check, the staged TRAIN refits of all four families, the threshold comparison and the move;
  2. a Section 6 fingerprint written into the temporary directory from the code on disk;
  3. the joint driver s6_eval.run: 5.13 for both eras through the labelled entry (preflight -> marker -> fit_fn -> run_fn with the real loaders, check_partitions,
     the Section 4 invariants, the frozen models, the break export, the JSON write), the evaluation coverage, H3/H4, H2, the A34 parts;
  4. the A38 entry (s5_a38.run) on the RAW fake evaluation tail, with the 2026-11-11 HF Raw and Clean files.
The evaluation FOMC list is the development schedule restricted to the fake evaluation days. EraData for the Section 6 history is cut to the fake TRAIN.
Recorded: each stage's outcome and time, the main process's peak memory, the checks below. Output (written once): section6/results/dress_rehearsal.json.
Usage: s6_dress_rehearsal.py [--smoke] [--keep] | --a38-only TEMP_DIR   (--smoke: RAW only, a 30-session tail, few resamples: a plumbing test)"""
import sys, json, time, shutil, tempfile, datetime, traceback, gc, ctypes
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(ROOT / "section5"))
TAIL = 120; EMB = 5


def peak_mb():
    try:
        class PMC(ctypes.Structure):
            _fields_ = [("cb", ctypes.c_ulong), ("PageFaultCount", ctypes.c_ulong), ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t), ("QuotaPagedPoolUsage", ctypes.c_size_t), ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                        ("QuotaNonPagedPoolUsage", ctypes.c_size_t), ("PagefileUsage", ctypes.c_size_t), ("PeakPagefileUsage", ctypes.c_size_t)]
        k32, ps = ctypes.windll.kernel32, ctypes.windll.psapi; k32.GetCurrentProcess.restype = ctypes.c_void_p
        ps.GetProcessMemoryInfo.argtypes = [ctypes.c_void_p, ctypes.POINTER(PMC), ctypes.c_ulong]; c = PMC(); c.cb = ctypes.sizeof(PMC)
        ps.GetProcessMemoryInfo(k32.GetCurrentProcess(), ctypes.byref(c), c.cb); return round(c.PeakWorkingSetSize / 2 ** 20)
    except Exception: return None


def slice_ctx(ctx, n):
    """The first n sessions of a main-run era context (features and targets are causal, so a prefix equals a computation on the prefix)."""
    d = ctx["d"]; N = len(d["t"]); cut = int(d["end"][n - 1]); dd = {}
    for k, v in d.items():
        if k in ("first", "end"): dd[k] = np.asarray(v)[:n]
        elif k == "features": dd[k] = {c: np.asarray(x)[:cut] for c, x in v.items()}
        elif isinstance(v, np.ndarray) and v.shape[:1] == (N,): dd[k] = v[:cut]
        else: dd[k] = v
    out = dict(ctx, d=dd, dv=np.asarray(ctx["dv"])[:cut], native=ctx["native"][:n], Mx=np.asarray(ctx["Mx"])[:n])
    if "bases" in ctx: out["bases"] = {c: np.asarray(x)[:cut] for c, x in ctx["bases"].items()}
    return out


def run(smoke=False, keep=False):
    import s5_eval_loader as EL, s5_eval513 as S513, s5_freeze_models as FM, s5_freeze_run as FR, s5_guard as G, s5_amendment_manifest as AM, s5_main as MB, s5_backend as BK
    import s5_a38 as A38, s5_freeze as FZ, s5_eval_label as EV, s6_run as R, s6_eval as S6E, s6_fingerprint as FPM
    eras = ("RAW",) if smoke else ("LEGACY", "RAW"); tail = 30 if smoke else TAIL
    real = dict(lock=G.LOCK, freeze=ROOT / "section5" / "results" / FR.FREEZE_NAME, frozen=FM.FROZEN_DIR, log=EL.ACCESS_LOG, fp=EL.FINGERPRINT)
    before = {k: Path(v).exists() for k, v in real.items()}
    td = Path(tempfile.mkdtemp(prefix="dress_rehearsal_")); s5res = td / "s5_results"; s6out = td / "s6_results"
    for p in (s5res, s6out): p.mkdir()
    stages = {}; checks = {}; t00 = time.time()
    split = {}
    for era in ("LEGACY", "RAW"):
        tr = sorted(x for x, q in S513.partitions(era).items() if q == "TRAIN"); split[era] = dict(train=tr[:-(tail + EMB)], embargo=tr[-(tail + EMB):-tail], eval=tr[-tail:])
    part = {era: {**{d: "TRAIN" for d in s["train"]}, **{d: "EMBARGO" for d in s["embargo"]}, **{d: "EVALUATION_EXPOSED" for d in s["eval"]}} for era, s in split.items()}
    dev_real, eval_real = dict(EL.DEV), dict(EL.EVAL)
    fake_dev = {e: (s["train"][0], s["train"][-1]) for e, s in split.items()}; fake_eval = {e: (s["eval"][0], s["eval"][-1]) for e, s in split.items()}
    assert all(fake_eval[e][1] <= dev_real[e][1] and fake_eval[e][0] > fake_dev[e][1] for e in fake_eval), "the fake evaluation tail must lie inside the real TRAIN span"
    sched = json.loads((ROOT / "section5" / "results" / "h1c_schedule_times.json").read_text(encoding="utf-8")); meet = sched.get("meetings") or sched
    fomc = td / "fomc_fake_eval.json"; fomc.write_text(json.dumps(dict(source="development schedule (h1c_schedule_times.json) restricted to the fake evaluation days", meetings={d: v for d, v in meet.items() if any(d in split[e]["eval"] for e in eras)})))
    G.write_side(fomc)
    for det in ("gaussian_hmm", "hsmm"):
        for suf in (".json", ".sha256"): shutil.copy(HERE / "results" / f"a35_null_control_{det}{suf}", s6out / f"a35_null_control_{det}{suf}")
    saved = dict(G=G.LOCK, EL=(EL.LOCK, EL.DEV, EL.EVAL, EL.check_dev_spans, EL.FINGERPRINT, EL.ACCESS_LOG, list(EL.EVAL_READS), EL.A38_RESULTS), S513=(S513.partitions, S513.FOMC_EVAL),
                 FM=FM.FROZEN_DIR, S6E=(S6E.S5RES, S6E.OUT, S6E.ERAS), R=R.load_era, FR=FR.ERAS)
    load_era0 = R.load_era
    def load_era_cut(era, period, *a, **k):
        E = load_era0(era, period, *a, **k); n = sum(1 for x in E.days if x <= fake_dev[era][1])
        F = R.EraData.__new__(R.EraData); F.era = E.era; F.days = list(E.days[:n]); F.ix = {d: i for i, d in enumerate(F.days)}; F.R = {a_: v[:n] for a_, v in E.R.items()}
        F.avail = {a_: v[:n] for a_, v in E.avail.items()}; F.drv = E.drv[:n]; return F
    lock = td / "ERA_CALIBRATION.lock"; fp = td / "s6_fingerprint.json"
    try:
        G.LOCK = lock; EL.LOCK = lock; EL.DEV = {**dev_real, **fake_dev}; EL.EVAL = {**eval_real, **fake_eval}; EL.check_dev_spans = lambda: True
        EL.FINGERPRINT = fp; EL.ACCESS_LOG = td / "eval_access_log.txt"; EL.EVAL_READS[:] = []; EL.A38_RESULTS = s5res
        S513.partitions = lambda era: part[era]; S513.FOMC_EVAL = fomc; FM.FROZEN_DIR = td / "frozen_models"; S6E.S5RES = s5res; S6E.OUT = s6out; S6E.ERAS = eras; FR.ERAS = eras
        R.load_era = load_era_cut
        assert G.LOCK != real["lock"] and EL.LOCK == lock and FM.FROZEN_DIR != real["frozen"] and EL.ACCESS_LOG != real["log"]
        # ---- 1. the freeze driver, on the real main backend with its era context cut to the fake TRAIN
        t0 = time.time(); summ = FR.load_summary()
        if smoke: summ = dict(summ, final_setups={e: summ["final_setups"][e] for e in eras})
        mb = MB.MainBackend(G.frozen_protocol_hash()); nfake = {e: len(split[e]["train"]) for e in eras}
        def _ctx(era, _mb=mb):
            if _mb._era is None or _mb._era["era"] != era:
                _mb._cur = _mb._era_b = _mb._era = None; gc.collect(); full = BK.era_context(era); _mb._era = slice_ctx(full, nfake[era]); del full; gc.collect()
            return _mb._era
        mb._ctx = _ctx
        fzp, doc, flog = FR.freeze(mb, summ, s5res, AM.freeze_ready(), frozen_dir=td / "frozen_models", staging=s5res / FR.STAGING_NAME)
        stages["freeze"] = dict(ok=True, seconds=round(time.time() - t0, 1), record={k: flog.get(k) for k in ("feature_parity", "threshold_comparison", "staging", "fit_seconds", "h2_primary_detector", "h1_passing_families")}, peak_mb=peak_mb())
        checks["freeze_written_with_models"] = bool(doc["input_hashes"].get("frozen_models")) and (td / "frozen_models" / FM.MANIFEST_NAME).exists() and not (s5res / FR.STAGING_NAME).exists()
        checks["lock_written_in_temp_only"] = lock.exists()
        token = FZ.sha(fzp); mb._era = mb._cur = mb._era_b = None; gc.collect()
        # ---- 2. Section 6 fingerprint (temporary)
        fp.write_text(json.dumps(dict(FPM.current(), created_utc="dress rehearsal"), indent=1)); G.write_side(fp)
        # ---- 3. the joint driver
        t0 = time.time(); nboot, null_sets, draws, workers = ((199, 2, 500, 2) if smoke else (9999, 200, 10000, 3))
        S6E.run(fzp, token, nboot=nboot, null_sets=null_sets, workers=workers, draws=draws)
        stages["joint_driver"] = dict(ok=True, seconds=round(time.time() - t0, 1), nboot=nboot, null_sets=null_sets, draws=draws, workers=workers, peak_mb=peak_mb())
        res5 = {e: json.loads((s5res / f"{FZ.EVAL_PREFIX}{e}.json").read_text(encoding="utf-8")) for e in eras}
        checks["513_results_labelled"] = all(v.get("a26_label") == EV.LABEL and v.get("confirmatory") is False for v in res5.values())
        checks["513_sessions_equal_fake_tail"] = all(v["sessions"] == split[e]["eval"] and v["n_train_sessions"] == len(split[e]["train"]) for e, v in res5.items())
        checks["frozen_thresholds_reproduced"] = {e: {f: v["families"][f]["thresholds"]["frozen_threshold_reproduced"] for f in v["families"]} for e, v in res5.items()}
        checks["section6_outputs"] = sorted(p.name for p in s6out.glob("*_evaluation_*.json")) + (["coverage_evaluation.json"] if (s6out / "coverage_evaluation.json").exists() else [])
        s6 = json.loads(next(s6out.glob("s6_evaluation_*.json")).read_text(encoding="utf-8")); checks["alerts"] = s6.get("alerts"); checks["positive_control"] = s6["sanity"]["positive_control"]
        summary513 = {e: {f: {k: (v["families"][f][k].get("effect"), v["families"][f][k].get("ci95"), v["families"][f][k].get("skipped")) for k in ("H1a", "H1b", "H1c")} for f in v["families"]} for e, v in res5.items()}
        # ---- 4. the A38 entry on the RAW fake tail
        t0 = time.time(); A38.run(fzp, token, res=s5res, nboot=(199 if smoke else 2000))
        a38 = json.loads((s5res / A38.RESULT_NAME).read_text(encoding="utf-8"))
        stages["a38"] = dict(ok=True, seconds=round(time.time() - t0, 1), peak_mb=peak_mb())
        checks["a38_labelled"] = a38.get("a26_label") == EV.LABEL and a38.get("confirmatory") is False
        a38s = {f: dict(reading=v["reading"], H1b_delta=v["H1b"]["delta"], H1a_delta=(v["H1a"].get("delta"))) for f, v in a38["primary_rule1"]["by_family"].items()}
        log = EL.ACCESS_LOG.read_text(encoding="utf-8"); checks["access_log"] = dict(allowed=log.count(" ALLOWED "), allowed_a38=log.count("ALLOWED A38"), refused=log.count("REFUSED"))
        ok = True; err = None
    except BaseException as e:
        ok = False; err = "".join(traceback.format_exception(e))[-4000:]; summary513 = None; a38s = None
    finally:
        G.LOCK = saved["G"]; EL.LOCK, EL.DEV, EL.EVAL, EL.check_dev_spans, EL.FINGERPRINT, EL.ACCESS_LOG = saved["EL"][:6]; EL.EVAL_READS[:] = saved["EL"][6]; EL.A38_RESULTS = saved["EL"][7]
        S513.partitions, S513.FOMC_EVAL = saved["S513"]; S513._AUTH.clear(); S513._PRELOADED.clear(); FM.FROZEN_DIR = saved["FM"]; S6E.S5RES, S6E.OUT, S6E.ERAS = saved["S6E"]; R.load_era = saved["R"]; FR.ERAS = saved["FR"]
    after = {k: Path(v).exists() for k, v in real.items()}; checks["real_paths_untouched"] = before == after
    out = dict(label="PREFREEZE_AUDIT M3 dress rehearsal: DEVELOPMENT DATA ONLY (fake evaluation tails inside TRAIN); nothing real frozen, locked or read from an evaluation period",
               smoke=smoke, eras=list(eras), split={e: dict(fake_train=[s["train"][0], s["train"][-1], len(s["train"])], fake_embargo=s["embargo"], fake_eval=[s["eval"][0], s["eval"][-1], len(s["eval"])]) for e, s in split.items() if e in eras},
               passed=bool(ok and checks.get("real_paths_untouched") and checks.get("freeze_written_with_models") and checks.get("513_results_labelled") and checks.get("a38_labelled")),
               error=err, stages=stages, checks=checks, results_513=summary513, a38=a38s, seconds=round(time.time() - t00, 1), peak_mb_main_process=peak_mb(), temp_dir=(str(td) if (keep or not ok) else None),
               generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), code=FPM.current())
    if ok and not keep: shutil.rmtree(td, ignore_errors=True)
    return out


A38_OLD_SHA = "23610a4a4a375bbaf9398e3a96bc43c875352e949563a3fddee52448c5b73f5d"      # AMENDMENT_A38.md before its note of 2026-11-12 (the hash the rehearsal's temporary freeze records)


def run_a38_only(td):
    """Rerun ONLY the A38 stage of a failed full rehearsal (user order 2026-11-11, after A38 note N1-N4), in its kept temporary folder, with the same redirections.
    Two temporary-folder substitutions, both disclosed in the output: (1) the temporary Section 6 fingerprint is rewritten for the current code (s5_a38.py changed after
    the rehearsal wrote it; in the real order the fingerprint is written after this change); (2) the amendment-list check compares against the temporary freeze's list,
    allowed only if the sole difference is AMENDMENT_A38's hash (old = the text before the note, new = ADOPTED with a matching sidecar). The crashed run's Clean marker is
    renamed, not deleted (in a real run it would block a second Clean read, by design)."""
    import s5_eval_loader as EL, s5_eval513 as S513, s5_freeze_models as FM, s5_guard as G, s5_amendment_manifest as AM, s5_a38 as A38, s5_freeze as FZ, s5_eval_label as EV, s6_fingerprint as FPM
    td = Path(td); s5res = td / "s5_results"; fzp = s5res / "section5_freeze.json"; eras = ("LEGACY", "RAW"); tail = TAIL
    for q in (fzp, s5res / f"{FZ.EVAL_PREFIX}RAW.json", s5res / "a38" / "raw.pkl", td / "ERA_CALIBRATION.lock", td / "frozen_models"):
        if not Path(q).exists(): raise SystemExit(f"{q} missing: not a kept full-rehearsal folder")
    if (s5res / A38.RESULT_NAME).exists(): raise SystemExit("A38 result already exists in the temporary folder")
    real = dict(lock=G.LOCK, freeze=ROOT / "section5" / "results" / "section5_freeze.json", frozen=FM.FROZEN_DIR, log=EL.ACCESS_LOG, fp=EL.FINGERPRINT)
    before = {k: Path(v).exists() for k, v in real.items()}
    split = {}
    for era in eras:
        tr = sorted(x for x, q in S513.partitions(era).items() if q == "TRAIN"); split[era] = dict(train=tr[:-(tail + EMB)], embargo=tr[-(tail + EMB):-tail], eval=tr[-tail:])
    part = {era: {**{d: "TRAIN" for d in s["train"]}, **{d: "EMBARGO" for d in s["embargo"]}, **{d: "EVALUATION_EXPOSED" for d in s["eval"]}} for era, s in split.items()}
    dev_real, eval_real = dict(EL.DEV), dict(EL.EVAL)
    fake_dev = {e: (s["train"][0], s["train"][-1]) for e, s in split.items()}; fake_eval = {e: (s["eval"][0], s["eval"][-1]) for e, s in split.items()}
    fz = json.loads(fzp.read_text(encoding="utf-8")); now = AM.freeze_ready()
    diff = [(a.get("amendment"), a.get("sha256"), b.get("sha256")) for a, b in zip(fz["amendments"], now) if a != b]
    a38now = AM.manifest(("A38",))[0]
    if len(fz["amendments"]) != len(now) or [x[0] for x in diff] != ["A38"] or diff[0][1] != A38_OLD_SHA or not (a38now["status"] == "ADOPTED" and a38now["sidecar_matches"]):
        raise SystemExit(f"amendment lists differ beyond the A38 note: {diff}")
    subs = dict(fingerprint_rewritten=True, amendment_list_substituted=dict(A38_in_temp_freeze=A38_OLD_SHA, A38_now=a38now["sha256"]))
    mk = A38.marker("clean", s5res); renamed = None
    if mk.exists(): renamed = mk.with_name(mk.name + ".crashed_run_2026-11-11"); mk.rename(renamed)
    subs["crashed_clean_marker_renamed_to"] = renamed.name if renamed else None
    fp = td / "s6_fingerprint.json"; fp.write_text(json.dumps(dict(FPM.current(), created_utc="dress rehearsal (A38-only rerun)"), indent=1)); G.write_side(fp)
    saved = dict(G=G.LOCK, EL=(EL.LOCK, EL.DEV, EL.EVAL, EL.check_dev_spans, EL.FINGERPRINT, EL.ACCESS_LOG, list(EL.EVAL_READS), EL.A38_RESULTS), S513=(S513.partitions, S513.FOMC_EVAL),
                 FM=FM.FROZEN_DIR, AM=AM.freeze_ready)
    lock = td / "ERA_CALIBRATION.lock"; t0 = time.time(); checks = {}
    try:
        G.LOCK = lock; EL.LOCK = lock; EL.DEV = {**dev_real, **fake_dev}; EL.EVAL = {**eval_real, **fake_eval}; EL.check_dev_spans = lambda: True
        EL.FINGERPRINT = fp; EL.ACCESS_LOG = td / "eval_access_log.txt"; EL.EVAL_READS[:] = []; EL.A38_RESULTS = s5res
        S513.partitions = lambda era: part[era]; S513.FOMC_EVAL = td / "fomc_fake_eval.json"; FM.FROZEN_DIR = td / "frozen_models"
        AM.freeze_ready = lambda *a, **k: fz["amendments"]
        assert G.LOCK != real["lock"] and FM.FROZEN_DIR != real["frozen"] and EL.ACCESS_LOG != real["log"]
        log0 = EL.ACCESS_LOG.read_text(encoding="utf-8")
        A38.run(fzp, FZ.sha(fzp), res=s5res, nboot=2000)
        a38 = json.loads((s5res / A38.RESULT_NAME).read_text(encoding="utf-8")); fam = a38["primary_rule1"]["by_family"]
        checks["a38_labelled"] = a38.get("a26_label") == EV.LABEL and a38.get("confirmatory") is False
        checks["h1a_evaluated"] = {f: v["H1a"].get("delta") is not None for f, v in fam.items()}
        checks["splice_drop"] = a38["primary_rule1"].get("splice_drop_note_N3")
        checks["n_stable_days"] = a38["primary_rule1"].get("n_stable_days")
        checks["by_family"] = {f: dict(reading=v["reading"], H1a=v["H1a"], H1b_delta=v["H1b"]["delta"], H1b_n_common_bars=v["H1b"]["n_common_bars"]) for f, v in fam.items()}
        checks["secondary_rule2"] = {f: v["label"] for f, v in a38["secondary_rule2"].items()}
        new = EL.ACCESS_LOG.read_text(encoding="utf-8")[len(log0):]; checks["access_log_this_run"] = dict(allowed_a38=new.count("ALLOWED A38"), refused=new.count("REFUSED"))
        ok = True; err = None
    except BaseException as e:
        ok = False; err = "".join(traceback.format_exception(e))[-4000:]
    finally:
        G.LOCK = saved["G"]; EL.LOCK, EL.DEV, EL.EVAL, EL.check_dev_spans, EL.FINGERPRINT, EL.ACCESS_LOG = saved["EL"][:6]; EL.EVAL_READS[:] = saved["EL"][6]; EL.A38_RESULTS = saved["EL"][7]
        S513.partitions, S513.FOMC_EVAL = saved["S513"]; S513._AUTH.clear(); S513._PRELOADED.clear(); FM.FROZEN_DIR = saved["FM"]; AM.freeze_ready = saved["AM"]
    after = {k: Path(v).exists() for k, v in real.items()}; checks["real_paths_untouched"] = before == after
    passed = bool(ok and checks.get("a38_labelled") and checks.get("real_paths_untouched") and checks.get("h1a_evaluated") and all(checks["h1a_evaluated"].values()))
    return dict(label="Dress rehearsal, A38 stage only (DEVELOPMENT DATA ONLY; fake RAW evaluation tail inside TRAIN), after AMENDMENT_A38 note N1-N4", temp_dir=str(td),
                passed=passed, error=err, seconds=round(time.time() - t0, 1), substitutions=subs, checks=checks, peak_mb_main_process=peak_mb(),
                generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), code=FPM.current())


def main():
    import s5_guard as G
    a = sys.argv[1:]
    if a[:1] == ["--a38-only"]:
        out_p = HERE / "results" / "dress_rehearsal_a38.json"
        if out_p.exists(): print("result exists; written once"); return 3
        res = run_a38_only(a[1]); out_p.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); G.write_side(out_p)
        print(json.dumps({k: res[k] for k in ("passed", "error", "seconds")}, indent=1, default=str)[:5000]); return 0 if res["passed"] else 1
    smoke = "--smoke" in a; out_p = HERE / "results" / ("dress_rehearsal_smoke.json" if smoke else "dress_rehearsal.json")
    if out_p.exists(): print("result exists; written once"); return 3
    res = run(smoke=smoke, keep="--keep" in a)
    out_p.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); G.write_side(out_p)
    print(json.dumps({k: res[k] for k in ("passed", "error", "seconds", "peak_mb_main_process", "temp_dir")}, indent=1, default=str)[:5000]); return 0 if res["passed"] else 1


if __name__ == "__main__": sys.exit(main())
