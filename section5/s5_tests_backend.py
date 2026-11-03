#!/usr/bin/env python3
"""Unit tests for the A10 backend guards (no data loaded)."""
import sys, json, time, tempfile, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_backend as BK


class TestGuards(unittest.TestCase):
    def test_clean_and_unlisted_folds_refused(self):
        for era, f in (("RAW", 0), ("LEGACY", 5), ("LEGACY", 26), ("RAW", 4)):
            with self.assertRaises(PermissionError, msg=f"{era}{f}"): BK.DataBackend(era, f)

    def test_allowed_set_is_exactly_the_two_contaminated_folds_and_both_are_excluded(self):
        self.assertEqual(BK.ALLOWED_MACHINERY, {"RAW|3", "LEGACY|29"})
        cl = json.loads((BK.HERE / "results" / "contamination_list.json").read_text()); ex = {f"{x['era']}|{x['fold']}": x["excluded"] for x in cl["folds"]}
        self.assertTrue(all(ex[k] for k in BK.ALLOWED_MACHINERY))

    def test_allowed_fold_must_be_on_the_contaminated_list(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"; p.write_text(json.dumps(dict(folds=[dict(era="RAW", fold=3, excluded=False)])))
            with self.assertRaises(PermissionError): BK.DataBackend("RAW", 3, contamination=p)
            p.write_text(json.dumps(dict(folds=[dict(era="RAW", fold=3, excluded=True)]))); b = BK.DataBackend("RAW", 3, contamination=p); self.assertEqual(b.folds(), ["RAW|3"])

    def test_backend_refuses_other_fold_ids_and_has_the_interface(self):
        b = BK.DataBackend("RAW", 3)
        for m in ("folds", "candidates", "param_grid", "objective", "score", "final_thresholds", "input_hashes"): self.assertTrue(callable(getattr(b, m)))
        with self.assertRaises(PermissionError): b.candidates("RAW|0")
        with self.assertRaises(PermissionError): b.objective("LEGACY|29", "hsmm")
        with self.assertRaises(PermissionError): b.score("RAW|2", "hsmm", {})
        self.assertEqual(b.param_grid("bocpd"), [dict(lam=12), dict(lam=39), dict(lam=78)]); self.assertEqual(b.param_grid("hsmm"), [dict(K=2), dict(K=3), dict(K=4)])
        self.assertIsNone(b._ctx)                                                         # nothing loaded until used

    def test_input_hashes_cover_protocol_and_amendments(self):
        h = BK.DataBackend("RAW", 3).input_hashes(); self.assertIn("SECTION5_PROTOCOL.md", h); self.assertIn("AMENDMENT_A10.md", h); self.assertIn("folds_csv", h)


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (Path(__file__).resolve().parent / "results" / "unit_tests_backend.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
