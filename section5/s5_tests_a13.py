#!/usr/bin/env python3
"""A13 unit tests: EM tolerance per observation (cap 500), cap reporting, and the ledger rule (every new row has WHY and EVIDENCE)."""
import sys, json, time, tempfile, shutil, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_models as M, s5_ledger as LED

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
SEQ = [-1000.0, -900.0, -899.96, -899.958, -899.9575]


def stub(m, seq):
    it = iter(seq + [seq[-1]] * 1000); m._init = lambda *a: None; m._em_step = lambda b: next(it); m._state = lambda: {}; m._load = lambda s: None; m._reorder = lambda: None; return m


def batch(n): return {"real": np.ones((1, n), bool)}


class TestEMPerObservation(unittest.TestCase):
    def test_defaults_are_1e_minus_6_per_observation_and_cap_500(self):
        for m in (M.GaussianHMM(2), M.StudentTHMM(2), M.HSMM(2)): self.assertEqual((m.tol, m.iters), (1e-6, 500), type(m).__name__)

    def test_threshold_scales_with_the_number_of_observations(self):
        # |dll| / N < 1e-6: with N = 1000 the threshold is 1e-3 and the change of 5e-4 at iteration 5 converges; with N = 100 the threshold is 1e-4 and it does not (stops at the first zero change, iteration 6)
        m = stub(M.GaussianHMM(2, 1), SEQ); m.fit(batch(1000)); self.assertEqual((m.fit_info["iterations"], m.fit_info["converged"], m.fit_info["n_obs"]), ([5], [True], 1000))
        m = stub(M.GaussianHMM(2, 1), SEQ); m.fit(batch(100)); self.assertEqual((m.fit_info["iterations"], m.fit_info["converged"], m.fit_info["n_obs"]), ([6], [True], 100))
        t = stub(M.StudentTHMM(2, 1), SEQ); t._occ = np.array([.5, .5]); t.fit(batch(1000)); self.assertEqual(t.fit_info["iterations"], [5])
        h = M.HSMM(2, 1); it = iter(SEQ + [SEQ[-1]] * 1000); h._init = lambda *a: None; h._em_step = lambda b: next(it)
        h.pi = np.array([.5, .5]); h.A = np.eye(2); h.mu = np.zeros((2, 1)); h.var = np.ones((2, 1)); h.h = np.ones((2, 5)); h.fit(batch(1000)); self.assertEqual(h.fit_info["iterations"], [5])

    def test_only_real_updates_count_and_cap_is_reported(self):
        b = {"real": np.array([[True] * 300 + [False] * 700])}; m = stub(M.GaussianHMM(2, 1), SEQ); m.fit(b); self.assertEqual(m.fit_info["n_obs"], 300)
        c = stub(M.GaussianHMM(2, 1, iters=500), [-1000.0 + i for i in range(1000)]); c.fit(batch(1000)); self.assertEqual((c.fit_info["iterations"], c.fit_info["converged"], c.fit_info["cap"]), ([500], [False], 500))

    def test_real_gaussian_fit_converges_before_the_cap_and_records_it(self):
        rng = np.random.default_rng(0); z = np.cumsum(rng.random((20, 80)) < 0.05, axis=1) % 2; X = (rng.normal(0, 1, (20, 80, 1)) * np.where(z, 3.0, 1.0)[:, :, None])
        bt = dict(X=X, real=np.ones((20, 80), bool), L=np.full(20, 80), S=20, T=80, D=1); m = M.GaussianHMM(2, 2, seed=0).fit(bt)
        self.assertEqual(m.fit_info["n_obs"], 1600); self.assertTrue(all(m.fit_info["converged"])); self.assertTrue(all(i < 500 for i in m.fit_info["iterations"]))


class TestLedgerRule(unittest.TestCase):
    def test_new_rows_require_why_and_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            led = Path(td) / "L.md"; shutil.copyfile(ROOT / "METHODS_LEDGER.md", led)
            for kw in (dict(why="", evidence="e"), dict(why="w", evidence=""), dict(why="  ", evidence="e")):
                with self.assertRaises(SystemExit): LED.add("AMENDMENT_A13.md", "k", "d", ledger=led, **kw)
            before = led.read_text(encoding="utf-8"); LED.add("AMENDMENT_A13.md", "Amendment", "decision text", "reason text", "audit finding 6; A12_MACHINERY_REPORT.md", ledger=led)
            t = led.read_text(encoding="utf-8"); self.assertIn(LED.MARK2, t); self.assertTrue(t.startswith(before.rstrip("\n")[:2000]))                    # earlier rows untouched
            last = t.rstrip("\n").split("\n")[-1]; cells = [c.strip() for c in last.strip("|").split("|")]
            self.assertEqual(len(cells), 7); self.assertEqual((cells[3], cells[4]), ("reason text", "audit finding 6; A12_MACHINERY_REPORT.md")); self.assertIn("AMENDMENT_A13.md", cells[5])
            LED.add("AMENDMENT_A13.md", "k2", "d2", "w2", "e2", ledger=led); self.assertEqual(led.read_text(encoding="utf-8").count(LED.MARK2), 1)               # one second table, rows appended

    def test_live_ledger_sidecar_matches(self):
        side = (ROOT / "METHODS_LEDGER.sha256").read_text().split()[0]; import hashlib
        self.assertEqual(side, hashlib.sha256((ROOT / "METHODS_LEDGER.md").read_bytes()).hexdigest())


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a13.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
