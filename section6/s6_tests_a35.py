#!/usr/bin/env python3
"""Unit tests for AMENDMENT_A35 (rule 1: H4 p on valid resamples only; rule 2: the null-control rerun's summary and consequence) and for the FABLE_REAUDIT M3
label guards (evaluation read flag, labelled 5.13 entry, direct-caller scan). Synthetic arrays and temporary files only."""
import sys, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_a35 as A


def days_of(n): return [str(pd.Timestamp("2010-01-04") + pd.Timedelta(days=int(k))).split()[0] for k in range(n)]


class TestValidOnlyP(unittest.TestCase):
    def test_divisor_is_valid_count(self):
        rng = np.random.default_rng(0); n = 300; x = rng.normal(0.02, 1, n); d = days_of(n); e = ["LEGACY"] * n; calls = [0]

        def stat(ix):
            calls[0] += 1
            return np.nan if calls[0] > 1 and calls[0] % 4 == 0 else float(x[ix].mean())      # every 4th resample is invalid; the first call is the statistic itself
        t, p, nv, p_all = L.week_block_bootstrap(stat, d, e, 999, 3, valid_only=True)
        self.assertLess(nv, 999); self.assertGreater(nv, 700); exceed = round(p_all * 1000 - 1)
        self.assertAlmostEqual(p, (1 + exceed) / (nv + 1)); self.assertGreater(p, p_all)            # A35 1a: divisor V + 1, not B + 1
        calls[0] = 0; t2, p2, nv2 = L.week_block_bootstrap(stat, d, e, 999, 3)                       # default unchanged: the earlier convention, 3 values
        self.assertEqual((t2, nv2), (t, nv)); self.assertAlmostEqual(p2, p_all)

    def test_no_invalid_resample_same_p(self):
        rng = np.random.default_rng(1); n = 200; x = rng.normal(0, 1, n); d = days_of(n); e = ["LEGACY"] * n
        _, p, nv, p_all = L.week_block_bootstrap(lambda ix: float(x[ix].mean()), d, e, 499, 2, valid_only=True); self.assertEqual(nv, 499); self.assertEqual(p, p_all)
        t, p, nv, p_all = L.week_block_bootstrap(lambda ix: np.nan, d, e, 49, 2, valid_only=True); self.assertTrue(np.isnan(p)); self.assertEqual(nv, 0)

    def test_all_resamples_invalid_is_not_evaluable(self):
        calls = [0]

        def stat(ix): calls[0] += 1; return 0.1 if calls[0] == 1 else np.nan
        t, p, nv, p_all = L.week_block_bootstrap(stat, days_of(50), ["LEGACY"] * 50, 20, 1, valid_only=True); self.assertEqual(nv, 0); self.assertTrue(np.isnan(p))   # A35 1b
        res = {k: dict(p=0.5) for k in R.PRIMARY}; res["H4b"] = dict(p=None); R.holm_family(res); self.assertEqual(res["H4b"]["p_used"], 1.0); self.assertFalse(res["H4b"]["evaluable"])

    def test_h4_test_reports_both(self):
        rng = np.random.default_rng(2); n = 120; d = days_of(n)

        class E: R = {"SPY": rng.normal(0, 1e-3, (n, 390))}
        units = [dict(era="LEGACY", day=d[i], day_idx=i, S=100, T=110, gap=10, placebos=[]) for i in range(n)]; lab = rng.integers(0, 2, n)
        saved = R.c_score
        try:
            R.c_score = lambda E_by, u, point, off=0: float(rng.random())
            r = R.h4_test({"LEGACY": E}, units, "T0", lambda u: float(lab[u["day_idx"]]), nboot=99)
        finally: R.c_score = saved
        self.assertIn("p_a29_1d_descriptive", r); self.assertIn("A35", r["statistic"]); self.assertGreaterEqual(r["p"], r["p_a29_1d_descriptive"])
        self.assertAlmostEqual(r["p"], (r["p_a29_1d_descriptive"] * 100) / (r["n_valid_resamples"] + 1))

    def test_amendment_lists(self):
        import s5_amendment_manifest as AM
        self.assertIn("A35", R.REQUIRED_ADOPTED); self.assertIn("A35", R.SECTION6_AMENDMENTS); self.assertIn("A35", AM.AMENDMENTS); self.assertEqual(A.AMENDMENTS[-1], "A35")


class TestRerunSummary(unittest.TestCase):
    def sets(self, n_rej_valid, n_rej_old, test="H4b"):
        s = {i: {k: dict(p=0.5, p_a29_1d=0.5) for k in R.PRIMARY} for i in range(A.N_SETS)}
        for i in range(n_rej_valid): s[i][test]["p"] = 0.04
        for i in range(n_rej_old): s[i][test]["p_a29_1d"] = 0.04
        return s

    def stored(self, n_old, test="H4b"): return dict(n_sets=200, rejection_rate={k: (n_old / 200 if k == test else 0.0) for k in R.PRIMARY})

    def test_consequences(self):
        r = A.summarise("gaussian_hmm", self.sets(21, 21), self.stored(21)); self.assertFalse(r["passed"]); self.assertTrue(r["reproduces_development_run"])
        self.assertTrue(r["consequence"].startswith("A35 3a")); self.assertEqual(r["tests_over_limit"], ["H4b"])
        r = A.summarise("gaussian_hmm", self.sets(20, 21), self.stored(21)); self.assertTrue(r["passed"]); self.assertTrue(r["consequence"].startswith("A35 3c"))   # 0.10 exactly passes ("at most")
        r = A.summarise("hsmm", self.sets(21, 21), self.stored(21)); self.assertTrue(r["consequence"].startswith("A35 3d"))
        r = A.summarise("hsmm", self.sets(16, 16), self.stored(16)); self.assertTrue(r["passed"]); self.assertEqual(r["consequence"], "the HSMM passes")
        r = A.summarise("gaussian_hmm", self.sets(5, 20), self.stored(21)); self.assertFalse(r["reproduces_development_run"]); self.assertTrue(r["consequence"].startswith("A35 2d"))

    def test_null_set_detail_shape(self):
        import inspect
        self.assertEqual(inspect.signature(R.null_set).parameters["detail"].default, False); self.assertEqual(inspect.signature(R.null_set).parameters["seed"].default, A.SEED)
        self.assertEqual((A.N_SETS, A.LIMIT), (200, 0.10))


class TestLabelGuards(unittest.TestCase):
    """FABLE_REAUDIT M3."""
    def test_write_once_requires_label_after_any_evaluation_read(self):
        import s5_eval_loader as EL
        saved = list(EL.EVAL_READS)
        try:
            with tempfile.TemporaryDirectory() as td:
                self.assertTrue(R.write_once(Path(td) / "a.json", dict(period="development")).exists())                      # no evaluation read: as before
                EL.EVAL_READS.append(("RAW", True))
                with self.assertRaises(PermissionError): R.write_once(Path(td) / "b.json", dict(period="development", x=1))   # a mislabelled period no longer passes
                with self.assertRaises(PermissionError): R.write_once(Path(td) / "c.json", dict(x=1))                          # nor a result with no period
                with self.assertRaises(PermissionError): R.write_once(Path(td) / "d.json", [1, 2])
                self.assertTrue(R.write_once(Path(td) / "e.json", dict(period="joint", a26_label=R.LABEL_EVAL, confirmatory=False)).exists())
        finally: EL.EVAL_READS[:] = saved

    def test_direct_callers_scan(self):
        import s5_eval_label as EV
        self.assertEqual(EV.direct_callers(), []); self.assertTrue(EV.ready())
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "driver.py").write_text("import s5_freeze as FZ\nFZ.run_confirmatory" + "(1, 2, 3, 4, 5, 6)\n"); (Path(td) / "ok.py").write_text("EV.run_confirmatory_labelled(1)\n")
            self.assertEqual(EV.direct_callers(scan=((Path(td), "x/"),)), ["x/driver.py"])

    def test_section5_read_needs_labelled_entry(self):
        import s5_eval_loader as EL, s5_eval_label as EV
        self.assertFalse(EV.ACTIVE)
        with self.assertRaisesRegex(PermissionError, "run_confirmatory_labelled"): EL.eval_guard("RAW", "missing_freeze.json", "x")
        seen = []; import s5_freeze as FZ; saved = FZ.run_confirmatory
        try:
            FZ.run_confirmatory = lambda fp, rd, eras, fit, run, tok: (seen.append(EV.ACTIVE), run("RAW", None, None, None))[1]
            with tempfile.TemporaryDirectory() as td: out = EV.run_confirmatory_labelled("f", td, ["RAW"], None, lambda *a: (1, 2), "t")
        finally: FZ.run_confirmatory = saved
        self.assertEqual(seen, [True]); self.assertFalse(EV.ACTIVE); self.assertEqual(out["value"], (1, 2)); self.assertEqual(out["a26_label"], EV.LABEL)    # L8: a non-dict result is wrapped, not refused


if __name__ == "__main__": unittest.main()
