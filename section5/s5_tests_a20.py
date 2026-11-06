#!/usr/bin/env python3
"""A20 unit tests (synthetic): __sadj-only scale pool, deseasonalised QLIKE target, MR2 wiring."""
import sys, json, time, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L

HERE = Path(__file__).resolve().parent


def sess(dv=True, seed=0):
    rng = np.random.default_rng(seed); n = 390; r = rng.normal(0, 1e-3, n); c = 400 * np.exp(np.cumsum(r))
    d = dict(first=np.array([0]), end=np.array([n]), close=c, open=np.r_[c[0], c[:-1]], valid=np.ones(n, bool), r=r, available=np.arange(n, dtype=np.int64), features={})
    if dv: d["dv"] = (r ** 2) / (1e-6 * (1 + np.arange(n) / n))
    return d


class TestA20(unittest.TestCase):
    def test_pool(self):
        p = L.a20_pool(L.pools()[0]); self.assertEqual(len(p), 13)
        self.assertFalse([c for c in p if L.stem_of(c) in L.SCALE_STEMS and not c.endswith("__sadj")]); self.assertEqual(sum(c.endswith("__sadj") for c in p), 6)
        self.assertTrue(L.assert_pool(p, "primary"))

    def test_target_deseasonalised(self):
        d = sess(); g = L.session_grid(d, 0, []); k = 3; s0 = g["slots"][k]
        self.assertAlmostEqual(g["tgt"][k], d["dv"][s0 + 1:s0 + 61].sum(), places=9); self.assertTrue(np.isnan(g["tgt"][-1]))
        self.assertTrue(np.isnan(L.session_grid(sess(dv=False), 0, [])["tgt"]).all())                          # no baseline, no target

    def test_backend_wiring(self):
        src = (HERE / "s5_backend.py").read_text(encoding="utf-8"); self.assertIn("cols = L.a20_pool(primary)", src); self.assertIn('d["dv"] = dv', src)
        import s5_mr2 as M, s5_contamination as C; MR, A, CM, D = M.configure()
        self.assertEqual((MR.OUT, A.MAIN, D.MAIN_DIR, D.A17), (M.MAIN2, M.MAIN2, M.MAIN2, M.MR2 / "a17")); self.assertEqual(C.REGISTRY["s5_mr2.py"], "MAIN_RUN"); self.assertTrue(C.check_registry(HERE))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a20.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
