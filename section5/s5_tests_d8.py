#!/usr/bin/env python3
"""D8 unit tests on synthetic data (A19 rule 1)."""
import sys, json, time, unittest
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_d8 as D, s5_contamination as C

HERE = Path(__file__).resolve().parent


def iid_frame(n=400, seed=1):
    rng = np.random.default_rng(seed); recs = []
    for k in range(n):
        r = rng.normal(0, 1, 390); recs += [dict(w, sess=k) for w in D.windows(r, r ** 2, np.ones(390), np.zeros(390))]
    return pd.DataFrame(recs)


class TestD8(unittest.TestCase):
    def test_iid_large_shares_near_one_percent(self):
        s = D.summarise(iid_frame())["large_shares"]
        self.assertLess(abs(s["trend"]["large"] - 0.01), 0.006); self.assertLess(abs(s["momentum"]["large"] - 0.01), 0.006)
        self.assertEqual(s["liquidity"]["large"], 0.0); self.assertEqual(s["jumps"]["large"], 0.0)

    def test_injected_changes_are_seen(self):
        rng = np.random.default_rng(2); r = rng.normal(0, 1, 390); r[120:180] += 0.8; vol = np.ones(390); vol[120:180] = 3; j = np.zeros(390); j[150] = 1
        w = {x["s"]: x for x in D.windows(r, r ** 2, vol, j)}[120]
        self.assertGreater(w["dt"], D.LARGE["trend"]); self.assertAlmostEqual(w["VOL"], 3.0); self.assertEqual(w["dJ"], 1.0)
        e = np.zeros(390); e[0] = rng.normal(); x = rng.normal(0, 1, 390)
        for t in range(1, 390): e[t] = (0.7 * e[t - 1] if 120 <= t < 180 else 0) + x[t]
        self.assertGreater({y["s"]: y for y in D.windows(e, e ** 2, np.ones(390), np.zeros(390))}[120]["drho"], D.LARGE["momentum"])

    def test_missing_bars_skip_window(self):
        r = np.random.default_rng(3).normal(0, 1, 390); r[60:120] = np.nan; self.assertNotIn(60, {x["s"] for x in D.windows(r, r ** 2, np.ones(390), np.zeros(390))})

    def test_registered_descriptive(self):
        self.assertEqual(C.REGISTRY["s5_d8.py"], "DESCRIPTIVE"); self.assertTrue(C.check_registry(HERE))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_d8.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
