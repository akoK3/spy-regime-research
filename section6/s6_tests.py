#!/usr/bin/env python3
"""Section 6 unit tests (AMENDMENT_A28): finding 12 / 14 fixes, availability clock (no look-ahead), deseasonalised RV and real-break label, placebo rules (before-the-break,
slot / era / decile, alarm distance), confirmation score (share of available assets, no minimum), OLS / AUC / Holm / BH, coverage metrics (label-free), fingerprint scope."""
import sys, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_coverage as C


class TestFixes(unittest.TestCase):
    def test_cache_key(self):
        with tempfile.TemporaryDirectory() as td:
            c = L.Cache(td); c.put("rv", "code1", "panel1", np.arange(3.0))
            self.assertTrue(np.array_equal(c.get("rv", "code1", "panel1"), np.arange(3.0)))
            self.assertIsNone(c.get("rv", "code2", "panel1")); self.assertIsNone(c.get("rv", "code1", "panel2")); self.assertIsNone(c.get("rv2", "code1", "panel1"))

    def test_blocks_within_era(self):
        days = ["2018-12-17", "2018-12-18", "2022-03-07", "2022-03-08", "2018-12-24"]; eras = ["LEGACY", "LEGACY", "RAW", "RAW", "LEGACY"]
        b = L.week_blocks(days, eras); self.assertEqual(len(b["LEGACY"]), 2); self.assertEqual(len(b["RAW"]), 1)
        for e, bl in b.items():
            for blk in bl: self.assertEqual({eras[i] for i in blk}, {e})
        seen = []
        L.week_block_bootstrap(lambda ix: (seen.append(ix), 1.0)[1], days, eras, nboot=50, seed=1)
        for ix in seen[1:]: self.assertEqual(sum(eras[i] == "RAW" for i in ix), 2); self.assertIn(sum(eras[i] == "LEGACY" for i in ix), (2, 3, 4))      # 2 LEGACY weeks (2 and 1 rows) drawn with replacement; the RAW week always twice-row

    def test_bootstrap_p(self):
        rng = np.random.default_rng(0); days = [str(pd.Timestamp("2010-01-04") + pd.Timedelta(days=int(k))).split()[0] for k in range(400)]; eras = ["LEGACY"] * 400
        x = rng.normal(0.5, 1, 400); t, p, _ = L.week_block_bootstrap(lambda ix: x[ix].mean(), days, eras, 999, 1); self.assertLess(p, 0.01)
        x0 = rng.normal(0, 1, 400) - rng.normal(0, 1, 400).mean(); _, p0, _ = L.week_block_bootstrap(lambda ix: x0[ix].mean() - x0.mean(), days, eras, 999, 1)
        self.assertGreater(p0, 0.2); self.assertGreaterEqual(p0, 1 / 1000)


class TestClock(unittest.TestCase):
    def test_rv_availability(self):
        r = np.zeros(390); r[9] = 1.0                        # the bar stamped 09:39 is available at minute 10
        self.assertEqual(L.rv(r, 9, 10)[0], 1.0); self.assertEqual(L.rv(r, 0, 9)[0], 0.0); self.assertEqual(L.rv(r, 10, 60)[0], 0.0)

    def test_deseasonalised_and_label(self):
        R_ = np.full((40, 390), 0.001); d = L.deseasonalised_rv(R_); self.assertTrue(np.isnan(d[:20]).all()); self.assertTrue(np.allclose(d[20:], 390))
        drv = np.r_[np.full(30, 1.0), 5.0, 1.0]; self.assertEqual(L.real_label(drv, 29), 1.0); self.assertEqual(L.real_label(drv, 30), 0.0)
        self.assertTrue(np.isnan(L.real_label(drv, 10))); self.assertTrue(np.isnan(L.real_label(drv, 31)))
        self.assertEqual(L.real_label(np.r_[np.full(30, 1.0), 5.0, 5.0, 5.0, 5.0, 5.0], 29, horizon=5), 1.0)


def cand_grid(n_days, vol_fn, era="LEGACY"):
    d, s = np.meshgrid(np.arange(n_days), np.arange(5, 390, 5), indexing="ij"); d, s = d.ravel(), s.ravel()
    return dict(day_idx=d, S=s, era=np.array([era] * len(d)), vol=np.array([vol_fn(a, b) for a, b in zip(d, s)], float))


class TestPlacebos(unittest.TestCase):
    def test_rules(self):
        rng = np.random.default_rng(1); vol = rng.normal(size=(100, 390)); cand = cand_grid(100, lambda a, b: vol[a, b])
        u = dict(day_idx=80, era="LEGACY", S=100, gap=10, vol=0.0); al = {50: [100]}
        ix = L.draw_placebos(u, cand, al, seed=3); self.assertEqual(len(ix), 20)
        cuts = L.decile_cuts(cand["vol"][cand["day_idx"] < 80]); dz = L.decile(0.0, cuts)
        for i in ix:
            self.assertLess(cand["day_idx"][i], 80); self.assertEqual(L.slot_of(cand["S"][i]), L.slot_of(100)); self.assertEqual(L.decile(cand["vol"][i], cuts), dz)
            if cand["day_idx"][i] == 50: self.assertGreater(abs(cand["S"][i] - 100), 60)
        self.assertTrue(np.array_equal(ix, L.draw_placebos(u, cand, al, seed=3)))

    def test_future_does_not_move_deciles(self):
        rng = np.random.default_rng(2); vol = rng.normal(size=(100, 390)); c1 = cand_grid(100, lambda a, b: vol[a, b]); c2 = cand_grid(100, lambda a, b: vol[a, b] + (100.0 if a >= 80 else 0))
        u = dict(day_idx=80, era="LEGACY", S=100, gap=10, vol=0.3)
        self.assertTrue(np.array_equal(L.draw_placebos(u, c1, {}, seed=4), L.draw_placebos(u, c2, {}, seed=4)))

    def test_other_era_excluded(self):
        c = cand_grid(50, lambda a, b: 0.0, era="RAW"); self.assertEqual(len(L.draw_placebos(dict(day_idx=40, era="LEGACY", S=100, gap=5, vol=0.0), c, {}, seed=1)), 0)


class TestScores(unittest.TestCase):
    def test_confirmation_score(self):
        pl = {a: np.arange(20.0) for a in ("TLT", "HYG", "GOLD", "DOLLAR")}
        self.assertEqual(L.confirmation_score({"TLT": 100.0, "HYG": np.nan, "GOLD": np.nan, "DOLLAR": np.nan}, pl), 1.0)
        self.assertEqual(L.confirmation_score({"TLT": 0.0, "HYG": np.nan, "GOLD": np.nan, "DOLLAR": np.nan}, pl), 0.0)
        self.assertEqual(L.confirmation_score({"TLT": 100.0, "HYG": 0.0, "GOLD": 100.0, "DOLLAR": np.nan}, pl), 2 / 3)
        self.assertTrue(np.isnan(L.confirmation_score({a: np.nan for a in pl}, pl)))

    def test_ols_auc_multiplicity(self):
        rng = np.random.default_rng(3); X = rng.normal(size=(500, 2)); b = (rng.random(500) < 0.2).astype(float); y = 1 + X @ [0.5, -0.2] + 0.7 * b + rng.normal(0, 0.1, 500)
        self.assertAlmostEqual(L.ols_gamma(y, X, b), 0.7, places=1)
        self.assertEqual(L.auc([1, 2, 3, 4], [0, 0, 1, 1]), 1.0); self.assertEqual(L.auc([1, 2, 3, 4], [1, 1, 0, 0]), 0.0)
        c = rng.random(500); yy = (rng.random(500) < 0.2 + 0.6 * c).astype(float); self.assertGreater(L.auc_gain(X, c, yy), 0.05)
        self.assertTrue(np.allclose(L.holm([0.01, 0.04, 0.03]), [0.03, 0.06, 0.06])); self.assertTrue(np.allclose(L.bh([0.01, 0.04, 0.03]), [0.03, 0.04, 0.04]))


class FakeEra(R.EraData):
    def __init__(self, n=80, era="LEGACY", seed=0):
        rng = np.random.default_rng(seed); self.era = era; self.days = [str(pd.Timestamp("2010-01-04") + pd.Timedelta(days=k)).split()[0] for k in range(n)]; self.ix = {d: i for i, d in enumerate(self.days)}
        self.R = {a: rng.normal(0, 1e-3, (n, 390)) for a in ("SPY",) + R.ASSETS}; self.avail = {a: np.ones(n, bool) for a in R.ASSETS}; self.drv = L.deseasonalised_rv(self.R["SPY"])


class TestNoLookAhead(unittest.TestCase):
    def test_h3_controls_and_c_score(self):
        E = FakeEra(); u = dict(era="LEGACY", day_idx=70, day=E.days[70], S=100, gap=15, T=115, kind="confirmed", direction="calm_to_stressed", placebos=[dict(day_idx=60 - k, S=100, gap=15, T=115) for k in range(20)])
        before = R.h3_row(E, "TLT", 70, 100, 115, "next_day")["X"]; cs = R.c_score({"LEGACY": E}, u, "S"); c0 = R.c_score({"LEGACY": E}, u, "T0")
        E.R["TLT"][70, 115:] = 1.0; E.R["HYG"][70, 100:] = 1.0                        # values not yet available at T = 115 (TLT) / at S = 100 (HYG)
        self.assertEqual(before, R.h3_row(E, "TLT", 70, 100, 115, "next_day")["X"]); self.assertEqual(cs, R.c_score({"LEGACY": E}, u, "S"))
        self.assertNotEqual(c0, R.c_score({"LEGACY": E}, u, "T0"))                      # HYG returns inside (S, T] do count at T = 0

    def test_offset(self):
        E = FakeEra(); E.R["TLT"][70] = 0; E.R["TLT"][70, 115] = 1.0                    # available at 116: inside (55, 115] only with offset +1
        self.assertTrue(np.isnan(R.h3_row(E, "TLT", 70, 100, 115, "next_day", 0)["X"][0])); self.assertEqual(R.h3_row(E, "TLT", 70, 100, 115, "next_day", 1)["X"][0], 0.0)

    def test_unavailable_asset_skipped(self):
        E = FakeEra(); E.avail["HYG"][:] = False; self.assertIsNone(R.h3_row(E, "HYG", 70, 100, 115, "next_day"))
        E.avail["TLT"][71] = False; self.assertIsNone(R.h3_row(E, "TLT", 70, 100, 115, "next_day")); self.assertIsNotNone(R.h3_row(E, "TLT", 70, 100, 115, "rest_of_day"))


class TestCoverage(unittest.TestCase):
    def test_metrics(self):
        g = pd.DataFrame(dict(minute_index_in_session=np.arange(390), TLT_return_eligible=np.r_[0, np.ones(300), np.zeros(40), np.ones(49)].astype(int), TLT_log_return_1m=np.r_[np.nan, np.zeros(10), np.ones(290) * 1e-4, np.full(40, np.nan), np.ones(49) * 1e-4]))
        m = C.session_metrics(g, "TLT"); self.assertEqual(m["max_gap_min"], 40); self.assertAlmostEqual(m["usable_share"], 349 / 389); self.assertAlmostEqual(m["zero_share"], 10 / 349)
        self.assertFalse(C.available(m, "TLT")); m["max_gap_min"] = 30; self.assertTrue(C.available(m, "TLT"))

    def test_label_free(self):
        src = (HERE / "s6_coverage.py").read_text(encoding="utf-8").split('"""', 2)[2]
        for w in ("breaks", "alarm", "s5_break_export", "load_eval", "real_label", "h3_", "h4_"): self.assertNotIn(w, src)


class TestFingerprint(unittest.TestCase):
    def test_scope(self):
        import s6_fingerprint as FP
        cur = FP.current(); self.assertEqual(cur["code_version"], FP.CODE_VERSION)
        for p in HERE.glob("*.py"): self.assertIn(f"section6/{p.name}", cur["files"])


if __name__ == "__main__": unittest.main()
