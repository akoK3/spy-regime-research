#!/usr/bin/env python3
"""Unit tests for AMENDMENT_A37: the freeze-time model record (FreezeBackend, manifest), load_frozen checks (hash, setup, TRAIN sessions, record present), the
evaluation backend refusing any fit, fit_fn handing over the preloaded state only, the guard's precheck (no read, no ALLOWED), the positive-control alert, and the
freeze refusals. Temporary files and stand-in objects only; no market data is read and no model is fitted."""
import sys, json, pickle, tempfile, unittest
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_eval as S6E, s5_eval513 as S513, s5_freeze_models as FM, s5_eval_loader as EL, s5_guard as G

FAMS = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); TR = ["2018-12-19", "2018-12-20", "2018-12-21"]


class Prep:
    def __init__(self): self.keep = ["ret5", "f1"]; self.mu = {"ret5": 0.0, "f1": 1.0}


def fake_freeze_dir(td, era="LEGACY"):
    """Bundles in the shape s5_freeze_models writes (stand-in models), a manifest with sidecar, and the freeze fields load_frozen reads."""
    d = Path(td) / "fm"; d.mkdir(); files = {}; setups, thr = {era: {}}, {era: {}}
    for f in FAMS:
        par = dict(lam=39) if f == "bocpd" else dict(K=2); s = dict(features=["f1"], params=par, base_params=par); setups[era][f] = s; thr[era][f] = dict(threshold=1.5)
        b = dict(era=era, family=f, setup=s, features=["f1"], params=par, base_params=par, feature=f"model:{f}:feat", baseline=f"model:{f}:base", prep=Prep(),
                 thresholds=dict(baseline_a11=2.0, baseline_calibration_rate=0.2, feature_recomputed=1.5, feature_recomputed_rate=0.2), n_train=3, train_first=TR[0], train_last=TR[-1])
        p = d / FM.file_name(era, f); p.write_bytes(pickle.dumps(b)); files[p.name] = FM.sha(p)
    mp = FM.manifest_path(d); mp.write_text(json.dumps(dict(files=files))); G.write_side(mp)
    return d, dict(setups=setups, thresholds=thr, input_hashes=dict(other="x", frozen_models=FM.frozen_hashes(d)))


class TestFreezeRecord(unittest.TestCase):
    def setUp(self): self._p = S513.partitions; S513.partitions = lambda era: {**{x: "TRAIN" for x in TR}, "2019-01-02": "EVALUATION_EXPOSED"}
    def tearDown(self): S513.partitions = self._p

    def test_freeze_backend_delegates_and_adds_models(self):
        class B:
            kind = "main"; protocol_sha256 = "ph"
            def input_hashes(self): return dict(panel="h")
            def era_thresholds(self, *a): return "thr"
        w = FM.FreezeBackend(B(), dict(manifest_sha256="m", files={}))
        self.assertEqual((w.kind, w.protocol_sha256, w.era_thresholds(1)), ("main", "ph", "thr")); self.assertEqual(w.input_hashes(), dict(panel="h", frozen_models=dict(manifest_sha256="m", files={})))

    def test_load_frozen_ok_and_reproduction(self):
        with tempfile.TemporaryDirectory() as td:
            d, fz = fake_freeze_dir(td); st = S513.load_frozen("LEGACY", fz, d)
            self.assertEqual(sorted(st["bundles"]), sorted(FAMS)); b = st["bundles"]["hsmm"]
            self.assertTrue(b["thresholds"]["frozen_threshold_reproduced"]); self.assertEqual(b["thresholds"]["feature_frozen"], 1.5); self.assertEqual(b["sha256"], fz["input_hashes"]["frozen_models"]["files"]["LEGACY_hsmm.pkl"])
            fz["thresholds"]["LEGACY"]["hsmm"]["threshold"] = 1.6; self.assertFalse(S513.load_frozen("LEGACY", fz, d)["bundles"]["hsmm"]["thresholds"]["frozen_threshold_reproduced"])   # reported, not refused

    def test_load_frozen_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            d, fz = fake_freeze_dir(td)
            with self.assertRaisesRegex(PermissionError, "no frozen models"): S513.load_frozen("LEGACY", dict(fz, input_hashes=dict(other="x")), d)
            p = d / "LEGACY_hsmm.pkl"; orig = p.read_bytes(); p.write_bytes(orig + b"x")
            with self.assertRaisesRegex(PermissionError, "LEGACY_hsmm.pkl missing or differs"): S513.load_frozen("LEGACY", fz, d)
            p.write_bytes(orig); fz2 = json.loads(json.dumps(dict(setups=fz["setups"], thresholds=fz["thresholds"]))); fz2["input_hashes"] = fz["input_hashes"]; fz2["setups"]["LEGACY"]["gaussian_hmm"]["params"] = dict(K=3)
            with self.assertRaisesRegex(PermissionError, "setup differs"): S513.load_frozen("LEGACY", fz2, d)
            S513.partitions = lambda era: {**{x: "TRAIN" for x in TR + ["2018-12-24"]}}
            with self.assertRaisesRegex(PermissionError, "TRAIN sessions differ"): S513.load_frozen("LEGACY", fz, d)
            mp = FM.manifest_path(d); mp.write_text(mp.read_text() + " ")
            with self.assertRaisesRegex(PermissionError, "manifest"): S513.load_frozen("LEGACY", fz, d)

    def test_write_models_written_once_and_freeze_refusals(self):
        with tempfile.TemporaryDirectory() as td:
            d = Path(td); FM.manifest_path(d).write_text("{}")
            with self.assertRaises(FileExistsError): FM.write_models({}, d)
            r = d / "res"; r.mkdir(); (r / "section5_freeze.json").write_text("{}")
            with self.assertRaises(FileExistsError): FM.freeze_with_models(None, {}, r, [])
            (r / "section5_freeze.json").unlink(); (r / "evaluation_RAW.json").write_text("{}")
            with self.assertRaises(RuntimeError): FM.freeze_with_models(None, {}, r, [])


class TestEvaluationStep(unittest.TestCase):
    def test_backend_refuses_any_fit(self):
        EB = S513._backend_class(); seg = dict(train=np.arange(2), val=np.array([], int), test=np.arange(2, 3))
        b = EB("LEGACY", dict(era="LEGACY"), seg, prep=Prep(), models={("hsmm", ("f1",), (("K", 2),)): "FROZEN"})
        self.assertEqual(b.fit("hsmm", ["f1"], dict(K=2), 3), "FROZEN")
        for args in (("hsmm", ["f1"], dict(K=3), 3), ("hsmm", (), dict(K=2), 3), ("gaussian_hmm", ["f1"], dict(K=2), 3), ("hsmm", ["f1"], dict(K=2), 1)):
            with self.assertRaisesRegex(PermissionError, "A37 2b"): b.fit(*args)

    def test_fit_fn_hands_over_only(self):
        S513._PRELOADED.clear()
        with self.assertRaisesRegex(PermissionError, "before the marker"): S513.fit_fn("RAW", {}, {})
        st = dict(bundles={}); S513._PRELOADED["RAW"] = st
        try: self.assertIs(S513.fit_fn("RAW", {}, {}), st)
        finally: S513._PRELOADED.clear()
        S513._AUTH.clear()
        with self.assertRaisesRegex(PermissionError, "did not register"): S513.run_fn("RAW", st, {}, {})       # the run starts with the guarded read, which needs the driver

    def test_precheck_reads_nothing(self):
        saved = (EL.ACCESS_LOG, list(EL.EVAL_READS))
        with tempfile.TemporaryDirectory() as td:
            try:
                EL.ACCESS_LOG = Path(td) / "log.txt"
                with self.assertRaises(Exception): EL.precheck("RAW", Path(td) / "no_freeze.json", "x")
                t = EL.ACCESS_LOG.read_text(); self.assertIn("PRECHECK era=RAW", t); self.assertIn("PRECHECK FAILED", t); self.assertNotIn("ALLOWED", t); self.assertNotIn("REQUEST", t)
                self.assertEqual(EL.EVAL_READS, saved[1])
            finally: EL.ACCESS_LOG = saved[0]; EL.EVAL_READS[:] = saved[1]


class TestAlertsAndLists(unittest.TestCase):
    def test_alerts(self):
        ok = dict(sanity=dict(positive_control=dict(p=0.001, passed=True, gamma=0.5, n_breaks=12)))
        self.assertEqual(S6E.alerts_of(ok), [])
        a = S6E.alerts_of(dict(sanity=dict(positive_control=dict(p=0.2, passed=False, gamma=0.1, n_breaks=12)))); self.assertEqual((a[0]["level"], a[0]["status"]), ("ALERT", "FAILED"))
        a = S6E.alerts_of(dict(sanity=dict(positive_control=dict(p=None, passed=False, n_breaks=2)))); self.assertEqual(a[0]["status"], "not evaluable")
        self.assertEqual(S6E.alerts_of({})[0]["status"], "not evaluable")
        r = dict(alerts=a, **ok); self.assertEqual(list(S6E.label(r))[0], "alerts")                                # first key of the written file

    def test_lists(self):
        import s5_amendment_manifest as AM, s6_fingerprint as FPM, s5_contamination as CT
        self.assertIn("A37", AM.AMENDMENTS); self.assertEqual(S6E.AMENDMENTS[-1], "A37"); self.assertIn("s5_freeze_models.py", FPM.HELPERS); self.assertTrue(CT.check_registry())


if __name__ == "__main__": unittest.main()
