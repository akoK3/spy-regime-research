#!/usr/bin/env python3
"""D7 unit tests on synthetic panels (A19 rule 2): injections, variance neutrality, price reconstruction, the cluster-bootstrap decision rule, registry."""
import sys, json, time, math, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_d7 as D, s5_contamination as C

HERE = Path(__file__).resolve().parent


def panel(seed=0, n=390):
    rng = np.random.default_rng(seed); r = rng.normal(0, 1e-3, n); r[0] = np.nan; lc = np.log(400) + np.nancumsum(np.r_[0, r[1:]]); c = np.exp(lc)
    o = np.r_[c[0], c[:-1]]; h = np.maximum(o, c) * np.exp(np.abs(rng.normal(0, 3e-4, n))); l = np.minimum(o, c) * np.exp(-np.abs(rng.normal(0, 3e-4, n)))
    return dict(open=o, high=h, low=l, close=c, r=r, valid=np.r_[False, np.ones(n - 1, bool)], range=np.log(h / l), volume=rng.integers(1000, 5000, n).astype(float), available=np.arange(n, dtype=np.int64) * 60 + 60)


class TestInject(unittest.TestCase):
    g = 150

    def run_(self, kind, level, seed=1):
        p = panel(); w = np.random.default_rng(9).uniform(0.5, 2, 390); q, info = D.inject(p, self.g, kind, level, w, np.random.default_rng(seed), 1.0); return p, q, info, w

    def test_variance_neutral_and_prices(self):
        J = np.arange(self.g + 1, self.g + 61)
        for kind, lv in D.LEVELS.items():
            for _, level in lv:
                p, q, info, w = self.run_(kind, level)
                if (kind, level) == ("jumps", 3): self.assertGreater(info["vr"], D.VR_BAND[1]); continue      # 3 x 6 local sd exceeds the window's variance: infeasible, recorded by gate (i)
                self.assertAlmostEqual(info["vr"], 1.0, places=9, msg=kind)
                self.assertTrue(np.allclose(np.diff(np.log(q["close"][self.g:])), np.r_[q["r"][J], p["r"][self.g + 61:]], rtol=1e-9, atol=1e-15), kind)      # returns after the window unchanged
                self.assertTrue(np.array_equal(q["close"][:self.g + 1], p["close"][:self.g + 1]))                                                                       # nothing before tau changes
                self.assertTrue((q["high"] >= np.maximum(q["open"], q["close"]) * (1 - 1e-12)).all() and (q["low"] <= np.minimum(q["open"], q["close"]) * (1 + 1e-12)).all(), kind)
                if kind != "liquidity": self.assertTrue(np.array_equal(q["volume"], p["volume"]))

    def test_trend_t_statistic(self):
        _, q, _, _ = self.run_("trend", 4.0); x = q["r"][self.g + 1:self.g + 61]; self.assertAlmostEqual(math.sqrt(60) * x.mean() / x.std(ddof=1), 4.0, places=9)

    def test_momentum_autocorrelation(self):
        acs = []
        for s in range(30):
            p = panel(s); q, _ = D.inject(p, self.g, "momentum", 0.4, np.ones(390), np.random.default_rng(s), 1.0); x = q["r"][self.g + 1:self.g + 61]; acs.append(np.corrcoef(x[:-1], x[1:])[0, 1])
        self.assertGreater(np.mean(acs), 0.25)

    def test_jumps_and_liquidity(self):
        p, q, info, _ = self.run_("jumps", 3); lsd = D.local_sd(p["r"], self.g); x = q["r"][self.g + 1:self.g + 61]
        self.assertEqual(int((np.abs(x) > 3 * lsd).sum()), 3); self.assertEqual(info["scale"], 1.0); self.assertLess(info["c2"], 0)
        p, q, info, _ = self.run_("jumps", 1); self.assertLess(info["scale"], 1.0); self.assertAlmostEqual(info["vr"], 1.0, places=9)
        p, q, info, _ = self.run_("liquidity", 0.5); self.assertTrue(np.allclose(q["volume"][self.g + 1:], 0.5 * p["volume"][self.g + 1:])); self.assertTrue(np.array_equal(q["volume"][:self.g + 1], p["volume"][:self.g + 1]))
        self.assertTrue(np.array_equal(q["close"], p["close"]))


class TestRule(unittest.TestCase):
    def test_responds_rule(self):
        rng = np.random.default_rng(0); cl = np.repeat(np.arange(150), 2); y0 = rng.random(300) < 0.1
        r = D.cluster_diff(y0 | (rng.random(300) < 0.3), y0, cl, nboot=2000); self.assertTrue(r["responds"]); self.assertGreater(r["ci95"][0], 0)
        r = D.cluster_diff(y0 | (rng.random(300) < 0.05), y0, cl, nboot=2000); self.assertFalse(r["responds"])
        r = D.cluster_diff(y0, y0, cl, nboot=2000); self.assertEqual(r["diff"], 0.0); self.assertFalse(r["responds"])

    def test_clustering_widens_ci(self):
        rng = np.random.default_rng(1); a = (rng.random(100) < 0.4).astype(float); b = (rng.random(100) < 0.2).astype(float)
        one = D.cluster_diff(np.repeat(a, 1), np.repeat(b, 1), np.arange(100), nboot=4000); dup = D.cluster_diff(np.repeat(a, 4), np.repeat(b, 4), np.repeat(np.arange(100), 4), nboot=4000)
        self.assertAlmostEqual(one["diff"], dup["diff"]); self.assertAlmostEqual(dup["ci95"][1] - dup["ci95"][0], one["ci95"][1] - one["ci95"][0], delta=0.03)      # duplicates add no information

    def test_registry(self):
        self.assertEqual(C.REGISTRY["s5_d7.py"], "POST_MAIN_RUN"); self.assertTrue(C.check_registry(HERE))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_d7.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
