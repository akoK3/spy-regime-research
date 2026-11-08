#!/usr/bin/env python3
"""A23 tests: forced inputs are in the A20 pool; the liquidity target equals s5_lib.session_grid's target built from dvol; registry; code version unchanged."""
import sys, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_a23 as M, s5_lib as L, s5_contamination as C


class TestA23(unittest.TestCase):
    def test_inputs(self): self.assertTrue(set(M.FEATS) <= set(L.a20_pool(L.pools()[0])))

    def test_liq_target(self):
        rng = np.random.default_rng(0); n = 390; c = np.exp(np.cumsum(rng.normal(0, 1e-3, n))) * 400; x = rng.gamma(2, 0.5, n); x[rng.random(n) < 0.05] = np.nan
        d = dict(first=np.array([0]), end=np.array([n]), close=c, open=np.r_[c[0], c[:-1]], valid=np.ones(n, bool), available=np.arange(n) * 60, features={}, dv=x)
        g = L.session_grid(d, 0, []); q = dict(sess=0, slots=g["slots"])
        np.testing.assert_array_equal(M.liq_target(d, x, q), g["tgt"])

    def test_registry(self):
        import s5_guard as G
        self.assertEqual(C.REGISTRY["s5_a23.py"], "POST_MAIN_RUN"); self.assertTrue(C.check_registry(M.HERE)); self.assertEqual(G.code_version(), "a0323ed24d68e896")


if __name__ == "__main__": unittest.main()
