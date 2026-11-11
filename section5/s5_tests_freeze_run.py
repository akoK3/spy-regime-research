#!/usr/bin/env python3
"""Tests for the single freeze driver (PREFREEZE_AUDIT H1, M1, M2). No market data: the composition s5_freeze_run.freeze -> staged s5_freeze_models.write_models ->
s5_run.freeze_step (unchanged) -> move is rehearsed in a temporary directory with a stub main backend and stub model bundles."""
import sys, re, json, shutil, tempfile, unittest
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(HERE))
import s5_freeze_run as FR, s5_freeze_models as FM, s5_guard as G, s5_amendment_manifest as AM, s5_eval513 as S513, s5_feature_parity as FP, s5_freeze as FZ

CALL = re.compile(r"\bfreeze_step\s*\(")
ALLOWED = {"section5/s5_run.py", "section5/s5_freeze_run.py", "section5/s5_dry_run.py", "section5/s5_machinery_run.py", "section5/s5_rehearsal.py",      # definition, the driver, temp-dir rehearsals
           "section5/s5_main.py"}      # docstring text only; s5_main.py is in the frozen result-module closure and cannot be edited (code version a0323ed24d68e896)
FAMS = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); DAYS = ["2010-01-04", "2010-01-05", "2010-01-06"]


def direct_callers():
    out = []
    for d, pre in ((HERE, "section5/"), (ROOT / "section6", "section6/"), (ROOT, "")):
        for f in Path(d).glob("*.py"):
            k = pre + f.name
            if k in ALLOWED or re.match(r"(section5/|section6/)?s[56]_tests_", k): continue
            if CALL.search(f.read_text(encoding="utf-8", errors="ignore")): out.append(k)
    return sorted(out)


class TestNoDirectFreezeStep(unittest.TestCase):
    def test_only_the_driver_calls_freeze_step(self):
        self.assertEqual(direct_callers(), [])                    # PREFREEZE_AUDIT H1: a new direct call anywhere fails this test

    def test_freeze_with_models_delegates(self):
        self.assertIn("s5_freeze_run", Path(FM.__file__).read_text(encoding="utf-8").split("def freeze_with_models")[1][:600])


class Env:
    """Temporary results directory, stub completion record, stub main backend and stub bundles; restores every patched name."""
    def __init__(self, td):
        self.td = Path(td); self.rd = self.td / "results"; self.rd.mkdir(); self.run = self.td / "run"; self.run.mkdir(); (self.run / G.COMPLETION).write_text("{}")
        self.final = self.td / "frozen_models"; self.staging = self.rd / FR.STAGING_NAME; self.fits = 0; self.saved = {}
        setups = {e: {f: dict(features=["x"], params=dict(K=2), base_params=dict(K=2)) for f in FAMS} for e in FR.ERAS}
        self.summ = dict(run_dir=str(self.run), protocol_sha256="ph", contamination_sha256="ch", code_version=G.code_version(), folds=["a"], final_setups=setups,
                         holm=dict(confirmatory={"gaussian_hmm": dict(reject=True), "hsmm": dict(reject=True), "student_t_hmm": dict(reject=False), "bocpd": dict(reject=False, secondary=True)}),
                         median_validation_qlike=dict(gaussian_hmm=0.21, student_t_hmm=0.20, hsmm=0.22, bocpd=0.3), failed_h1a={})
        self.amend = [dict(amendment="A21", status="ADOPTED")]

    def __enter__(self):
        s = self; sv = s.saved
        sv["G"] = (G.verify_completion, G.frozen_protocol_hash, G.canonical_contamination); sv["AM"] = AM.freeze_ready; sv["S513"] = S513.partitions; sv["FM"] = (FM.fit_bundles, FM.FROZEN_DIR); sv["FP"] = FP.parity
        G.verify_completion = lambda p, require_main=False: dict(protocol_sha256="ph", contamination_sha256="ch", code_version=G.code_version(), folds=["a"])
        G.frozen_protocol_hash = lambda: "ph"; G.canonical_contamination = lambda: (None, "ch"); AM.freeze_ready = lambda: s.amend; S513.partitions = lambda era: {d: "TRAIN" for d in DAYS}
        FP.parity = lambda era, ctx_main=None, ctx_513=None: dict(passed=True, fields={}, sessions={})
        def fb(era, setups_era):
            s.fits += 1
            return {f: dict(era=era, family=f, setup=v, features=list(v["features"]), params=dict(v["params"]), base_params=dict(v["base_params"]), feature="m", baseline="b", prep=None,
                            thresholds=dict(baseline_a11=1.0, baseline_calibration_rate=0.2, feature_recomputed=2.0, feature_recomputed_rate=0.2), code_version=G.code_version(),
                            n_train=len(DAYS), train_first=DAYS[0], train_last=DAYS[-1]) for f, v in setups_era.items()}
        FM.fit_bundles = fb; FM.FROZEN_DIR = s.final; return s

    def __exit__(self, *a):
        sv = self.saved; G.verify_completion, G.frozen_protocol_hash, G.canonical_contamination = sv["G"]; AM.freeze_ready = sv["AM"]; S513.partitions = sv["S513"]
        FM.fit_bundles, FM.FROZEN_DIR = sv["FM"]; FP.parity = sv["FP"]

    def freeze(self, backend, **k): return FR.freeze(backend, self.summ, self.rd, self.amend, frozen_dir=self.final, staging=self.staging, **k)


class StubBackend:
    kind = "stub"; protocol_sha256 = "ph"
    def __init__(self, fail_after=None, thr=2.0): self.n = 0; self.fail_after = fail_after; self.thr = thr
    def era_thresholds(self, era, family, setup, completion):
        self.n += 1
        if self.fail_after is not None and self.n > self.fail_after: raise RuntimeError("simulated crash in the era calibration")
        return dict(threshold=self.thr, rule="stub")
    def input_hashes(self): return dict(stub="n/a")
    def _ctx(self, era): return None


class TestAtomicFreeze(unittest.TestCase):
    def test_crash_then_retry_reuses_staged_models(self):
        with tempfile.TemporaryDirectory() as td, Env(td) as e:
            with self.assertRaises(RuntimeError): e.freeze(StubBackend(fail_after=3))
            self.assertFalse((e.rd / FR.FREEZE_NAME).exists()); self.assertTrue((e.staging / FM.MANIFEST_NAME).exists()); self.assertEqual(e.fits, 2)
            p, doc, log = e.freeze(StubBackend())                                                    # retry: no refit, freeze written, models moved
            self.assertEqual(e.fits, 2); self.assertEqual(log["staging"], "reused (verified; no refit)"); self.assertFalse(e.staging.exists())
            self.assertEqual(doc["input_hashes"]["frozen_models"]["manifest_sha256"], FM.frozen_hashes(e.final)["manifest_sha256"])
            self.assertTrue(all(r["ok"] for r in log["threshold_comparison"])); self.assertEqual(len(log["threshold_comparison"]), 8)
            for era in FR.ERAS: S513.load_frozen(era, doc, e.final)
            with self.assertRaises(FileExistsError): e.freeze(StubBackend())                        # complete: refused

    def test_threshold_mismatch_stops_before_the_document(self):
        with tempfile.TemporaryDirectory() as td, Env(td) as e:
            with self.assertRaises(PermissionError): e.freeze(StubBackend(thr=2.5))
            self.assertFalse((e.rd / FR.FREEZE_NAME).exists()); self.assertFalse(e.final.exists())

    def test_prechecks_before_any_fit(self):
        with tempfile.TemporaryDirectory() as td, Env(td) as e:
            with self.assertRaises(PermissionError): FR.freeze(StubBackend(), e.summ, e.rd, [dict(amendment="other")], frozen_dir=e.final, staging=e.staging)
            with self.assertRaises(PermissionError): FR.freeze(StubBackend(), dict(e.summ, protocol_sha256="xx"), e.rd, e.amend, frozen_dir=e.final, staging=e.staging)
            FP.parity = lambda era, ctx_main=None, ctx_513=None: dict(passed=False, fields={"dv": dict(equal=False)}, sessions={})
            with self.assertRaises(PermissionError): e.freeze(StubBackend())
            self.assertEqual(e.fits, 0); self.assertFalse(e.staging.exists())

    def test_interrupted_move_is_completed_by_a_rerun(self):
        with tempfile.TemporaryDirectory() as td, Env(td) as e:
            pr = FR.promote; FR.promote = lambda *a: (_ for _ in ()).throw(OSError("simulated crash before the move"))
            try:
                with self.assertRaises(OSError): e.freeze(StubBackend())
            finally: FR.promote = pr
            self.assertTrue((e.rd / FR.FREEZE_NAME).exists()); self.assertTrue(e.staging.exists()); self.assertFalse(e.final.exists())
            p, doc, log = e.freeze(StubBackend()); self.assertIn("resumed", log); self.assertTrue((e.final / FM.MANIFEST_NAME).exists())

    def test_unverifiable_staging_is_refitted(self):
        with tempfile.TemporaryDirectory() as td, Env(td) as e:
            e.staging.mkdir(parents=True); (e.staging / "junk.pkl").write_bytes(b"x")
            p, doc, log = e.freeze(StubBackend()); self.assertTrue(log.get("staging_discarded")); self.assertEqual(e.fits, 2)


if __name__ == "__main__": unittest.main()
