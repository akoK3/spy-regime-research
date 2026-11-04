#!/usr/bin/env python3
"""A16 unit tests (re-audit after A15, audit 2 findings 16-21). No model is fitted and no market data read; the lock and patched paths live in temporary directories."""
import sys, json, time, tempfile, unittest, hashlib, inspect, shutil
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_guard as G, s5_run as RUN, s5_backend as BK, s5_era_threshold as ET, s5_main as MB, s5_contamination as C, s5_dry_run as DR

HERE = Path(__file__).resolve().parent
PH = G.frozen_protocol_hash()


class TempLock:
    """Points G.LOCK at a temporary file for the duration of a test."""
    def __enter__(self): self.td = tempfile.TemporaryDirectory(); self.orig = G.LOCK; G.LOCK = Path(self.td.name) / "ERA_CALIBRATION.lock"; return G.LOCK
    def __exit__(self, *a): G.LOCK = self.orig; self.td.cleanup()


def main_record(run_dir, **over):
    Path(run_dir).mkdir(parents=True, exist_ok=True); _, ch = G.canonical_contamination(); rec = dict(backend="main", folds=G.MAIN_FOLDS, families=["gaussian_hmm"], code_version=G.code_version(), checkpoint_version="x", protocol_sha256=PH,
                                                 contamination_sha256=ch, results_sha256="0" * 64); rec.update(over); return G.write_completion(run_dir, **rec)


def stub_era(era, completion):
    e = ET.EraBackend(era, completion, PH); e.final_thresholds = lambda *a: dict(threshold=1.0)
    e._ctx = dict(seg=dict(train=np.array([0, 1]), embargo=np.array([2]), val=np.array([3])), d=dict(day=np.array(["d0", "d1", "d2", "d3"]), first=np.array([0, 1, 2, 3]))); return e


class TestRule1CompletionRecord(unittest.TestCase):
    def test_run_all_writes_a_hash_checked_record(self):
        with tempfile.TemporaryDirectory() as td:
            s = RUN.run_all(DR.SyntheticBackend(n_legacy=3, n_raw=0), td, nboot=100); p = Path(td) / G.COMPLETION
            r = G.verify_completion(p, require_main=False); self.assertEqual((r["protocol_sha256"], r["code_version"], r["folds"]), (PH, s["code_version"], s["folds"]))
            with self.assertRaises(PermissionError): G.verify_completion(p, require_main=True)                                    # synthetic, not the main run over 34 folds
            p.write_text(p.read_text().replace('"backend": "synthetic"', '"backend": "main"'))
            with self.assertRaises(PermissionError): G.verify_completion(p, require_main=False)                                   # edited: sidecar no longer matches

    def test_era_backend_needs_a_valid_main_record(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError): ET.EraBackend("RAW", Path(td) / G.COMPLETION, PH)                           # no record
            with self.assertRaises(TypeError): ET.EraBackend("RAW")                                                               # cannot be built without one
            main_record(td, folds=G.MAIN_FOLDS[:-1])
            with self.assertRaises(PermissionError): ET.EraBackend("RAW", Path(td) / G.COMPLETION, PH)                           # not all 34 folds
            main_record(td, code_version="stale")
            with self.assertRaises(PermissionError): ET.EraBackend("RAW", Path(td) / G.COMPLETION, PH)                           # other code
            main_record(td); self.assertEqual(ET.EraBackend("RAW", Path(td) / G.COMPLETION, PH).era, "RAW")
            with self.assertRaises(PermissionError): ET.EraBackend("RAW", Path(td) / G.COMPLETION, "0" * 64)                     # wrong protocol token

    def test_no_completion_flag_left(self):
        self.assertFalse(hasattr(MB.MainBackend, "mark_scoring_complete")); self.assertIn("completion", inspect.signature(MB.MainBackend.era_thresholds).parameters)


class TestRule2CanonicalList(unittest.TestCase):
    def test_no_function_accepts_another_list(self):
        for f in (RUN.run_all, BK.DataBackend.__init__, MB.MainBackend.__init__, RUN.freeze_step, RUN.excluded_from_contamination): self.assertNotIn("contamination", inspect.signature(f).parameters)

    def test_protocol_states_the_list_hash(self):
        p, h = G.canonical_contamination(); self.assertEqual(h, G.sha(HERE / "results" / "contamination_list.json")); self.assertIn(f"contamination list sha256 `{h}`", G.PROTOCOL.read_text(encoding="utf-8"))

    def test_any_other_list_raises(self):
        orig = G.CONTAMINATION
        with tempfile.TemporaryDirectory() as td:
            try:
                q = Path(td) / "contamination_list.json"; j = json.loads(orig.read_text()); j["folds"][0]["excluded"] = True; q.write_text(json.dumps(j)); G.CONTAMINATION = q
                with self.assertRaises(RuntimeError): G.canonical_contamination()                                                  # no sidecar match
                G.write_side(q)
                with self.assertRaises(RuntimeError): G.canonical_contamination()                                                  # sidecar matches, protocol states another hash
                with self.assertRaises(RuntimeError): BK.DataBackend("RAW", 3)
                with self.assertRaises(RuntimeError): RUN.run_all(DR.SyntheticBackend(n_legacy=2, n_raw=0), Path(td) / "r", nboot=50)
            finally: G.CONTAMINATION = orig


class TestRule3Registry(unittest.TestCase):
    def test_loaders_added_by_a15_are_caught(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s5_a.py").write_text("ctx = BK.era_context('RAW')\n"); (Path(td) / "s5_b.py").write_text("rows = F.splice_batch(specs, 'RAW', cols, 4)\n")
            (Path(td) / "s5_c.py").write_text("pool = mp.Pool(4, initializer=D2._init, initargs=(cols,))\n"); (Path(td) / "s5_d.py").write_text("F._init('RAW', cols)\n")
            (Path(td) / "s5_e.py").write_text("def _init(self): pass\n")                                                           # an unrelated _init is not a loader
            self.assertEqual(C.unregistered(td), ["s5_a.py", "s5_b.py", "s5_c.py", "s5_d.py"])
        self.assertTrue(C.check_registry(HERE))


class TestRule4NoOverride(unittest.TestCase):
    def test_no_files_argument(self):
        self.assertNotIn("files", inspect.signature(RUN.run_all).parameters); self.assertNotIn("files", inspect.signature(G.code_version).parameters)


class TestRule5Lock(unittest.TestCase):
    def test_calibration_writes_lock_and_lock_blocks_scoring(self):
        with TempLock() as lock, tempfile.TemporaryDirectory() as td:
            b = DR.SyntheticBackend(n_legacy=2, n_raw=0); RUN.run_all(b, Path(td) / "run", nboot=50)                              # before the lock: computed
            main_record(Path(td) / "main"); e = stub_era("RAW", Path(td) / "main" / G.COMPLETION); self.assertFalse(lock.exists())
            e.calibrate("gaussian_hmm", dict(features=[], params=dict(K=3))); self.assertTrue(lock.exists()); self.assertEqual(json.loads(lock.read_text().splitlines()[0])["era"], "RAW")
            s = RUN.run_all(b, Path(td) / "run", nboot=50); self.assertEqual(s["checkpoint"]["misses"], 0)                          # reading existing checkpoints still works
            with self.assertRaises(PermissionError): RUN.run_all(b, Path(td) / "new_dir", nboot=50)                                # any unit to compute is refused
            fb = object.__new__(BK.DataBackend); fb.id = "RAW|3"
            with self.assertRaises(PermissionError): fb.score("RAW|3", "hsmm", {})
            with self.assertRaises(PermissionError): fb.objective("RAW|3", "hsmm")


class TestRule6ProtocolHash(unittest.TestCase):
    def test_checkpoints_depend_on_protocol(self):
        self.assertNotEqual(G.checkpoint_version("c", "p1"), G.checkpoint_version("c", "p2"))
        with tempfile.TemporaryDirectory() as td:
            s = RUN.run_all(DR.SyntheticBackend(n_legacy=2, n_raw=0), td, nboot=50); self.assertEqual(s["protocol_sha256"], PH)
            self.assertEqual(s["checkpoint_version"], G.checkpoint_version(s["code_version"], PH))

    def test_freeze_verifies_and_records_the_protocol(self):
        self.assertNotIn("protocol_hash", inspect.signature(RUN.freeze_step).parameters)
        b = DR.SyntheticBackend(n_legacy=2, n_raw=0)
        with tempfile.TemporaryDirectory() as td:
            s = RUN.run_all(b, Path(td) / "r", nboot=50)
            with self.assertRaises(PermissionError): RUN.freeze_step(b, dict(s, protocol_sha256="0" * 64), Path(td), ["A16"])
            class Bad(DR.SyntheticBackend): protocol_sha256 = "0" * 64
            with self.assertRaises(PermissionError): RUN.freeze_step(Bad(n_legacy=2, n_raw=0), s, Path(td), ["A16"])
            (Path(td) / "fz").mkdir(); _, doc = RUN.freeze_step(b, s, Path(td) / "fz", ["A16"]); self.assertEqual(doc["protocol_sha256"], PH)
            self.assertEqual(doc["completion_record_sha256"], G.sha(Path(td) / "r" / G.COMPLETION))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a16.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
