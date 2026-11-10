#!/usr/bin/env python3
"""Unit tests for s6_h2.py (AMENDMENT_A32). Synthetic arrays only."""
import sys, unittest
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_h2 as H


class FakeEra(R.EraData):
    def __init__(self, n=80, seed=0, const=None):
        rng = np.random.default_rng(seed); self.era = "LEGACY"; self.days = [str(pd.Timestamp("2010-01-04") + pd.Timedelta(days=k)).split()[0] for k in range(n)]; self.ix = {d: i for i, d in enumerate(self.days)}
        self.R = {a: (np.full((n, 390), const) if const is not None else rng.normal(0, 1e-3, (n, 390))) for a in ("SPY",) + R.ASSETS}; self.avail = {a: np.ones(n, bool) for a in R.ASSETS}


def unit(di=70, T=115, k=20, era="LEGACY"):
    return dict(era=era, day_idx=di, day=f"2010-03-{1 + di % 28:02d}", S=T - 10, gap=10, T=T, placebos=[dict(day_idx=di - 1 - j, S=T - 10, gap=10, T=T) for j in range(k)])


class TestMeasure(unittest.TestCase):
    def test_deseasonalised_value_and_causality(self):
        E = FakeEra(const=1e-3)
        self.assertAlmostEqual(H.dz(E, "TLT", 50, 100, 130), 0.03 / np.sqrt(30e-6), places=9)      # |r| = 30 x 1e-3; median RV over the window = 30 x 1e-6
        v = H.dz(E, "TLT", 50, 100, 130); E.R["TLT"][50, 130:] = 5.0; E.R["TLT"][51:] = 9.0; E.__dict__.pop("_h2")
        self.assertEqual(v, H.dz(E, "TLT", 50, 100, 130))                                        # minutes after t1 and later sessions are never read
        E.R["TLT"][50, 99] = 5.0; E.__dict__.pop("_h2"); self.assertAlmostEqual(v, H.dz(E, "TLT", 50, 100, 130), places=9)   # index 99 is available at 100: outside (100, 130]
        E.R["TLT"][50, 100] = 5.0; E.__dict__.pop("_h2"); self.assertNotEqual(v, H.dz(E, "TLT", 50, 100, 130))

    def test_undefined_cases(self):
        E = FakeEra(const=1e-3)
        self.assertTrue(np.isnan(H.dz(E, "TLT", 5, 100, 130)))                                   # fewer than 10 previous sessions
        self.assertTrue(np.isnan(H.dz(E, "TLT", 50, 370, 400))); self.assertTrue(np.isnan(H.dz(E, "TLT", 50, -10, 20)))   # window outside regular hours
        E.avail["TLT"][50] = False; self.assertTrue(np.isnan(H.dz(E, "TLT", 50, 100, 130)))
        E.avail["HYG"][30:50] = False; self.assertTrue(np.isnan(H.dz(E, "HYG", 50, 100, 130)))  # no previous session with the asset available

    def test_contrib_test_and_planted(self):
        E = FakeEra(n=700, seed=1); E_by = {"LEGACY": E}; br = [unit(di=60 + 41 * j, T=115) for j in range(15)]      # spaced: no break session among another break's placebos or prior 20 sessions
        for u in br: u["day"] = E.days[u["day_idx"]]
        g0 = H.h2_test(E_by, br, "TLT", 0, 30, nboot=199)
        for u in br: E.R["TLT"][u["day_idx"], 115:145] *= 4.0
        E.__dict__.pop("_h2"); g1 = H.h2_test(E_by, br, "TLT", 0, 30, nboot=199)
        self.assertGreater(g1["G"], g0["G"] + 1.0); self.assertLess(g1["p"], 0.05); self.assertEqual(g1["n_breaks"], 15)
        self.assertIsNone(H.h2_test(E_by, br[:4], "TLT", 0, 30, nboot=199)["G"])                # fewer than 5 breaks
        u = unit(T=115, k=9); u["day"] = E.days[70]; self.assertTrue(np.isnan(H.contrib(E_by, u, "TLT", 0, 30)[0]))   # fewer than 10 placebo values

    def test_holm4(self):
        res = {f"H2_{a}": dict(p=0.02) for a in R.ASSETS}; res["H2_DOLLAR"] = dict(p=None); H.holm4(res)
        self.assertEqual({v["holm_m"] for v in res.values()}, {4}); self.assertEqual(res["H2_DOLLAR"]["p_used"], 1.0); self.assertFalse(res["H2_DOLLAR"]["reject_0.05"])
        self.assertAlmostEqual(res["H2_TLT"]["p_holm"], 0.08); self.assertFalse(res["H2_TLT"]["reject_0.05"])     # m = 4: 4 x 0.02 = 0.08, not rejected (m = 3 would give 0.06)


class TestE1(unittest.TestCase):
    def test_classify(self):
        self.assertEqual(H.classify(dict(TLT=1, HYG=-1, GOLD=0, DOLLAR=1)), "flight_to_safety")
        self.assertEqual(H.classify(dict(TLT=0, HYG=-1, GOLD=1, DOLLAR=None)), "credit_stress")
        self.assertEqual(H.classify(dict(TLT=-1, HYG=0, GOLD=0, DOLLAR=1)), "dollar_driven")
        self.assertEqual(H.classify(dict(TLT=0, HYG=0, GOLD=0, DOLLAR=None)), "spy_only")
        self.assertEqual(H.classify(dict(TLT=1, HYG=0, GOLD=0, DOLLAR=None)), "other")

    def test_e1_flight_to_safety(self):
        E = FakeEra(seed=2); u = unit(T=115); u["day"] = E.days[70]
        E.R["TLT"][70, 115:145] = 0.01; E.R["HYG"][70, 115:145] = -0.01
        res = H.e1({"LEGACY": E}, [u]); self.assertEqual(res["breaks"]["flight_to_safety"]["n"], 1); self.assertEqual(res["n_placebos"], 20)
        self.assertEqual(H.e1({"LEGACY": E}, [unit(T=380)])["skipped"]["window_past_close"], 1)


if __name__ == "__main__": unittest.main()
