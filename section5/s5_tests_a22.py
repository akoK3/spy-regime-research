#!/usr/bin/env python3
"""A22 unit tests: D8c breakdown, D7 MDE simulation, alarm-time shift in the sweep, H1(c) recomputation against the MR2 A17-style result, MR2 family results recomputed (era phase),
grid switch, phase order (rule 5a), registry, and the MR2 code version unchanged (so the MR2 completion record still verifies)."""
import sys, json, time, tempfile, unittest
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A, s5_d8c as D8C, s5_contamination as C, s5_lib as L, s5_sweep as W

HERE = Path(__file__).resolve().parent


class TestD8c(unittest.TestCase):
    def test_breakdown(self):
        df = pd.DataFrame(dict(VR=[3, 1, 1, 0.4, 1, 3, 1], VOL=[1, 2.5, 1, 1, 1, 3, 1], dJ=[0, 0, 1, 0, 0, 1, 0], dt=[0, 0, 0, 0, 5, 0, 0], drho=[0] * 7, sess=list("abcdefg")))
        r = D8C.report(df); p = r["primary"]
        self.assertEqual(p["n_any_large"], 5); self.assertEqual(p["single"]["volatility_only"]["n"], 2); self.assertEqual(p["single"]["liquidity_only"]["n"], 1)
        self.assertEqual(p["single"]["jumps_only"]["n"], 1); self.assertEqual(p["combined"]["n"], 1); self.assertEqual(p["combined_patterns"]["volatility+liquidity+jumps"]["n"], 1)
        self.assertAlmostEqual(sum(v["share_of_any"] for v in p["all_patterns"].values()), 1.0)
        self.assertEqual(r["secondary_5_types"]["n_any_large"], 6)

    def test_volatility_threshold(self): self.assertEqual((D8C.VOL_LO, D8C.VOL_HI), (0.5, 2.0))


class TestPower(unittest.TestCase):
    def test_d7_mde_floor_and_monotone(self):
        r = A.d7_mde(258, 0.03); self.assertIsNotNone(r["mde"]); self.assertGreaterEqual(r["mde"], 0.10)
        v = list(r["curve"].values()); self.assertTrue(all(b >= a - 0.02 for a, b in zip(v, v[1:])))
        self.assertGreater(A.d7_mde(50, 0.03)["mde"] or 1, r["mde"] - 1e-9)


class TestDelayShift(unittest.TestCase):
    def test_shift_moves_hit_out_of_window(self):
        T = 30; P = np.zeros((1, T, 2)); P[0, :, 0] = 1.0; P[0, 20:, :] = [0.0, 1.0]; real = np.ones((1, T), bool); av = (np.arange(T, dtype=np.int64) * 5 + 5)[None] * A.MIN_NS
        tau = np.array([int(av[0, 9])]); th = [0.0]                                                # run starts at update 20 (55 min after tau), T_c at 22 (65 min) -> no hit
        tau2 = np.array([int(av[0, 12])])                                                          # tau 15 min later: T_d 40 min, T_c 50 min after tau -> hit at delta 0
        _, h0 = W.sweep_old_state(P, real, A.shift_avail(av, 0), th, tau2); _, h5 = W.sweep_old_state(P, real, A.shift_avail(av, 5), th, tau2); _, h10 = W.sweep_old_state(P, real, A.shift_avail(av, 10), th, tau2)
        _, hx = W.sweep_old_state(P, real, A.shift_avail(av, 0), th, tau)
        self.assertTrue(h0[0, 0]); self.assertTrue(h5[0, 0]); self.assertTrue(h10[0, 0]); self.assertFalse(hx[0, 0])
        tau3 = np.array([int(av[0, 22]) - 58 * A.MIN_NS]); _, a = W.sweep_old_state(P, real, A.shift_avail(av, 0), th, tau3); _, b = W.sweep_old_state(P, real, A.shift_avail(av, 5), th, tau3)
        self.assertTrue(a[0, 0]); self.assertFalse(b[0, 0])                                         # T_c 58 min after tau: a hit, but not with +5 min

    def test_padding_stays(self): self.assertTrue(np.array_equal(A.shift_avail(np.array([0, A.MIN_NS]), 5), np.array([0, 6 * A.MIN_NS])))


class TestReproductions(unittest.TestCase):
    def test_h1c_matches_mr2_a17(self):
        _, _, conf = A.folds_split(); al = {(f, fam): A.a17_record(f, fam)["alarms"] for f in conf for fam in A.FAMILIES}; got = A.h1c(al)
        ref = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]
        for fam in A.FAMILIES: self.assertTrue(A.same({k: v for k, v in ref[fam].items() if k != "events"}, got[fam]), fam)

    def test_era_phase_reproduces_mr2_summary(self):
        with tempfile.TemporaryDirectory() as t:
            old = A.LOG; A.LOG = Path(t) / "log.txt"
            try: r = A.phase_era_flagged(None, Path(t))
            finally: A.LOG = old
        self.assertTrue(r["reproduces_mr2_summary"]); self.assertEqual(r["flagged"]["n_flagged"]["student_t_hmm"], 0)


class TestGrid(unittest.TestCase):
    def test_grid_switch(self):
        with A.Grid(15):
            self.assertTrue(np.array_equal(L.grid_slots(390), np.arange(14, 390, 15)))
            n = 390; rng = np.random.default_rng(0); c = np.exp(np.cumsum(rng.normal(0, 1e-3, n))) * 400
            d = dict(first=np.array([0]), end=np.array([n]), close=c, open=np.r_[c[0], c[:-1]], valid=np.ones(n, bool), available=np.arange(n) * 60, features={})
            g = L.session_grid(d, 0, []); self.assertEqual(len(g["X"]), 26); self.assertAlmostEqual(g["X"][1, 0], np.log(c[29] / c[14]))
        with A.Grid(1): self.assertEqual(len(L.grid_slots(390)), 390)
        self.assertEqual((L.GRID, L.FIRST_SLOT), (5, 4))


class TestOrderRegistry(unittest.TestCase):
    def test_phase_order(self):
        self.assertEqual(A.PHASES, ("power", "d8c", "era_flagged", "thresholds", "delay", "a18", "seeds", "raw80", "grids", "grid1", "grid1_hsmm"))
        self.assertEqual(set(A.DONE_FILES), set(A.PHASES))

    def test_registry_and_code_version(self):
        import s5_guard as G
        self.assertEqual(C.REGISTRY["s5_a22.py"], "POST_MAIN_RUN"); self.assertEqual(C.REGISTRY["s5_d8c.py"], "DESCRIPTIVE"); self.assertTrue(C.check_registry(HERE))
        self.assertEqual(G.code_version(), "a0323ed24d68e896")


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a22.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
