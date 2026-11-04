#!/usr/bin/env python3
"""Unit tests for the A9 orchestration (s5_run) and the synthetic dry-run backend. Synthetic data only."""
import sys, json, time, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_run as RUN, s5_dry_run as DR, s5_h1 as H, s5_freeze as FZ


class TestRun(unittest.TestCase):
    def test_modules_do_not_import_data_loaders(self):
        for f in ("s5_run.py", "s5_select.py", "s5_stats.py", "s5_freeze.py", "s5_dry_run.py"):
            t = (Path(RUN.HERE) / f).read_text(encoding="utf-8"); self.assertNotIn("import s5_lib", t, f); self.assertNotIn("load_era", t.replace("never reads market data", ""), f)

    def test_checkpoint_key_includes_code_version(self):
        with tempfile.TemporaryDirectory() as td:
            a = RUN.Checkpoint(td, "v1"); n = []; fn = lambda: n.append(1) or {"x": 1}
            a.run("k", fn); a.run("k", fn); self.assertEqual(len(n), 1); self.assertEqual((a.hits, a.misses), (1, 1))
            b = RUN.Checkpoint(td, "v2"); b.run("k", fn); self.assertEqual(len(n), 2)                    # new code version: old unit not reused
            self.assertNotEqual(a.path("k"), b.path("k"))

    def test_code_version_changes_with_file_content(self):
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "a.py").write_text("x=1"); v1 = RUN.code_version(["a.py"], Path(td)); (Path(td) / "a.py").write_text("x=2"); self.assertNotEqual(v1, RUN.code_version(["a.py"], Path(td)))

    def test_excluded_from_contamination(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "c.json"; p.write_text(json.dumps(dict(folds=[dict(era="LEGACY", fold=1, excluded=True), dict(era="RAW", fold=0, excluded=False)])))
            self.assertEqual(RUN.excluded_from_contamination(p), {"LEGACY|1"})
        real = Path(RUN.HERE) / "results" / "contamination_list.json"
        if real.exists(): self.assertEqual(len(RUN.excluded_from_contamination(real)), 8)                # A15 rule 2: LEGACY 23 and 24 added

    def test_select_fold_finds_true_features_and_tunes(self):
        b = DR.SyntheticBackend(); s = RUN.select_fold(b, "LEGACY|0", "gaussian_hmm"); self.assertEqual(s["features"], ["f1", "f2"]); self.assertEqual(s["params"], dict(K=3)); self.assertFalse(s["budget_exhausted"])
        self.assertEqual(RUN.select_fold(b, "LEGACY|0", "hsmm")["features"], [])                     # null family: no feature passes the 1% gain rule
        self.assertTrue(RUN.select_fold(b, "LEGACY|0", "gaussian_hmm", budget=3)["budget_exhausted"])

    def test_score_fold_skips_h1a_on_few_stable_days_without_crashing(self):
        b = DR.SyntheticBackend(); st = dict(features=[], params={}, val_qlike=1.0); r = RUN.score_fold(b, "LEGACY|3", "gaussian_hmm", st)
        self.assertIsNone(r["a"]); self.assertIn("< 8", r["a_skipped"]); self.assertIsNotNone(r["b"]); r2 = RUN.score_fold(b, "LEGACY|4", "gaussian_hmm", st); self.assertIsNotNone(r2["a"])

    def test_full_synthetic_run_decisions_resume_and_exclusions(self):
        b = DR.SyntheticBackend(); exc = {"LEGACY|14", "RAW|2"}
        with tempfile.TemporaryDirectory() as td:
            cf = DR.contamination_file(Path(td) / "c.json", exc, b.folds()); s1 = RUN.run_all(b, Path(td) / "run", contamination=cf, nboot=1000); s2 = RUN.run_all(b, Path(td) / "run", contamination=cf, nboot=1000)
            self.assertEqual(s1["checkpoint"]["hits"], 0); self.assertEqual(s2["checkpoint"]["misses"], 0); self.assertEqual(s2["checkpoint"]["hits"], s1["checkpoint"]["misses"])    # resume
            c = s1["holm"]["confirmatory"]; self.assertTrue(c["gaussian_hmm"]["reject"] and c["student_t_hmm"]["reject"]); self.assertFalse(c["hsmm"]["reject"])
            self.assertTrue(c["bocpd"]["secondary"] and not c["bocpd"]["reject"])                       # BOCPD reported, outside Holm
            self.assertEqual(s1["family_results"]["hsmm"]["confirmatory"]["H1a"]["n_folds"], 20 - 2 - 2)   # 2 excluded, 2 skipped for few stable days
            self.assertEqual(s1["family_results"]["hsmm"]["all_folds_sensitivity"]["H1a"]["n_folds"], 20 - 2)
            self.assertEqual(set(s1["final_setups"]), {"LEGACY", "RAW"}); self.assertEqual(s1["skipped_h1a"]["hsmm"], ["LEGACY|3", "RAW|1"])
            with tempfile.TemporaryDirectory() as td2:
                p, doc = RUN.freeze_step(b, s1, Path(td2), "ph", ["A9"]); self.assertEqual(doc["h2_primary_detector"], "gaussian_hmm"); self.assertEqual(set(doc["h1_passing_families"]), {"gaussian_hmm", "student_t_hmm"})
                FZ.verify_freeze(p)
                with self.assertRaises(FileExistsError): RUN.freeze_step(b, s1, Path(td2), "ph", ["A9"])

    def test_code_change_invalidates_checkpoints_in_a_run(self):
        b = DR.SyntheticBackend(n_legacy=4, n_raw=0)
        with tempfile.TemporaryDirectory() as td:
            s1 = RUN.run_all(b, td, nboot=200, files=["s5_run.py"]); s2 = RUN.run_all(b, td, nboot=200, files=["s5_run.py", "s5_dry_run.py"])
            self.assertEqual(s2["checkpoint"]["hits"], 0); self.assertNotEqual(s1["code_version"], s2["code_version"])


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (Path(__file__).resolve().parent / "results" / "unit_tests_run.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
