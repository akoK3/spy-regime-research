#!/usr/bin/env python3
"""A21 unit tests: D7 data-validity exclusion and label (rule 1), d7a21 wiring (rule 2), Step 2 liquidity target, QLIKE scale invariance, aggregation and verdict (rule 3), registry,
and the MR2 code version unchanged (so the MR2 completion record still verifies)."""
import sys, json, time, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_d7 as D, s5_step2 as S2, s5_contamination as C, s5_lib as L, s5_eval as V
from s5_tests_d7 import panel

HERE = Path(__file__).resolve().parent


class TestA21D7(unittest.TestCase):
    def test_nan_window_label_and_ratio(self):
        p = panel(); w = np.ones(390); w[160] = np.nan
        for kind, lv in D.LEVELS.items():
            for _, level in lv:
                q, info = D.inject(p, 150, kind, level, w, np.random.default_rng(1), 1.0)
                if kind == "liquidity": self.assertEqual(info["vr"], 1.0)
                else: self.assertTrue(np.isnan(info["vr"]), kind)
                if kind == "jumps": self.assertIsNone(q); self.assertEqual(info["why"], "window variance undefined (NaN)")

    def test_zero_window_label(self):
        p = panel(); p["r"] = np.where(np.isfinite(p["r"]), 0.0, np.nan); q, info = D.inject(p, 150, "jumps", (2, 5.0), np.ones(390), np.random.default_rng(1), 1.0)
        self.assertIsNone(q); self.assertEqual(info["why"], "window variance zero")

    def test_exclusion_before_rows(self):
        src = (HERE / "s5_d7.py").read_text(encoding="utf-8"); i = src.index('why="undefined variance ratio (A21)"'); j = src.index('rows[(len(out["days"]), k)] = F.rows_from_panel')
        self.assertLess(i, j); self.assertIn("continue", src[i:j])

    def test_d7a21_stage(self):
        src = (HERE / "s5_mr2.py").read_text(encoding="utf-8"); self.assertIn('"d7a21"', src); self.assertIn('MR2 / "d7_a21"', src)


class TestStep2(unittest.TestCase):
    def test_target_is_60_mean_dvol(self):
        n = 390; rng = np.random.default_rng(0); dvol = rng.lognormal(0, 0.5, n); dvol[[5, 200]] = np.nan
        d = dict(first=np.array([0]), end=np.array([n]), close=np.exp(np.cumsum(rng.normal(0, 1e-3, n))) * 400, valid=np.ones(n, bool), available=np.arange(n) * 60, features={}, dv=dvol)
        d["open"] = np.r_[d["close"][0], d["close"][:-1]]; g = L.session_grid(d, 0, [])
        for k, s0 in enumerate(g["slots"]):
            if s0 + 60 <= n - 1: self.assertAlmostEqual(g["tgt"][k], 60 * np.nanmean(dvol[s0 + 1:s0 + 61]), places=9)

    def test_dvol_is_d8_adjust(self):
        import step11_a4_rerun_4_3_4_7_8 as pstep
        rng = np.random.default_rng(2); ns = 30; first = np.arange(ns) * 390; end = first + 390; slot = np.tile(np.arange(390), ns); vol = rng.integers(0, 5000, ns * 390).astype(float); vol[7] = np.nan
        d = dict(volume=vol, slot=slot, first=first, end=end); a = S2.dvol_of(d); b = pstep.adjust(vol, slot, first, end)
        self.assertTrue(np.array_equal(np.isnan(a), np.isnan(b)) and np.allclose(a[np.isfinite(a)], b[np.isfinite(b)]))

    def test_qlike_invariant_to_target_scale(self):
        rng = np.random.default_rng(3); P = rng.dirichlet(np.ones(3), 500); t = rng.lognormal(0, 1, 500); res = [dict(P=P)]; seq = [dict(tgt=t)]
        v1 = V.state_values("gaussian_hmm", res, seq); v60 = V.state_values("gaussian_hmm", res, [dict(tgt=60 * t)]); self.assertTrue(np.allclose(v60, 60 * v1))
        f = P @ v1; self.assertTrue(np.allclose(V.qlike_loss(t, f), V.qlike_loss(60 * t, P @ v60)))

    def test_verdict_gate_ii_not_required(self):
        fams = S2.FAMILIES; cd = lambda diff, resp, r0=0.03: dict(diff=diff, ci95=[diff - .05, diff + .05], responds=resp, rate0=r0)
        types = {pc: {f"{f}|{w}": cd(0.0, False) for f in fams for w in ("feature", "baseline")} for pc in ("pc_ratio3", "pc_ratio5.29")}
        types["liquidity:vol_x2"] = {**{f"{f}|feature": cd(0.2, f == "hsmm") for f in fams}, "variance_neutral_share": 1.0}
        types["liquidity:vol_x0.5"] = {**{f"{f}|feature": cd(0.0, False) for f in fams}, "variance_neutral_share": 1.0}
        v = S2.step2_d7_verdict(dict(types=types, n_days=150)); self.assertTrue(v["gates_passed"]); self.assertEqual(v["responds_vol_x2"], {f: f == "hsmm" for f in fams})
        v = S2.step2_d7_verdict(dict(types=types, n_days=50)); self.assertFalse(any(v["responds_vol_x2"].values()))
        types["pc_ratio3"]["bocpd|baseline"]["rate0"] = 0.5; v = S2.step2_d7_verdict(dict(types=types, n_days=150)); self.assertFalse(v["gate_iii"])

    def test_aggregate(self):
        folds = [f"LEGACY|{i}" for i in range(8)] + ["RAW|0"]; excluded = {"LEGACY|7"}; units = {}
        for i, f in enumerate(folds):
            for k, fam in enumerate(S2.FAMILIES):
                units[(f, fam)] = dict(b=0.01 * (k + 1) if fam != "bocpd" else (None if i == 0 else 0.0), setup=dict(features=["relative_volume20"] if k < 3 else [], params=dict(K=3), base_params=dict(K=2)),
                                       qlike_test=dict(mean_base=1.0, mean_feat=1.0 - 0.01 * (k + 1), n=100, pct=(k + 1) * 1.0))
        a = S2.aggregate(units, [], folds, excluded)
        self.assertEqual(a["families"]["hsmm"]["confirmatory"]["tests"]["n_folds"], 8); self.assertEqual(a["families"]["bocpd"]["confirmatory"]["skipped"], ["LEGACY|0"])
        self.assertAlmostEqual(a["families"]["student_t_hmm"]["all_folds"]["qlike_pct_pooled"], 2.0); self.assertEqual(set(a["bh_confirmatory"]), set(S2.FAMILIES))
        self.assertEqual(a["families"]["gaussian_hmm"]["final_setups"]["LEGACY"]["features"], ["relative_volume20"])

    def test_registry_and_code_version(self):
        import s5_guard as G
        self.assertEqual(C.REGISTRY["s5_step2.py"], "POST_MAIN_RUN"); self.assertTrue(C.check_registry(HERE))
        self.assertEqual(G.code_version(), "a0323ed24d68e896")                                                  # MR2's code version: no result module changed


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_step2.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
