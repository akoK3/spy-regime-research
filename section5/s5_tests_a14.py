#!/usr/bin/env python3
"""A14 unit tests: documented HSMM parameters (finding 22) and Student-t occupancy reporting (finding 19). No market data."""
import sys, json, time, unittest, re
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_models as M, s5_eval as V, s5_lib as L

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent


def old_hazard(leave_c, stay_c):                      # the expression as it stood in the code before A14
    h0 = (leave_c.sum() + 1e-9) / (leave_c.sum() + stay_c.sum() + 1e-9)
    h = (leave_c + 0.5 * h0) / (leave_c + stay_c + 0.5); h[:, -1] = 1.0
    return np.clip(h, 1e-6, 1.0)


class TestFinding22(unittest.TestCase):
    def test_documented_constants(self):
        self.assertEqual((M.HSMM_HAZARD_PSEUDO, M.HAZARD_CLIP, M.PROB_FLOOR, M.DUR_CAP, M.VAR_FLOOR), (0.5, 1e-6, 1e-12, 78, 1e-6))

    def test_hazard_update_equals_the_pre_a14_expression(self):
        rng = np.random.default_rng(0)
        for _ in range(20):
            lv = rng.random((3, 78)) * rng.choice([0, 0.01, 5.0], (3, 78)); st = rng.random((3, 78)) * 50
            self.assertTrue(np.array_equal(M.hsmm_hazard_update(lv, st), old_hazard(lv, st)))
        h = M.hsmm_hazard_update(np.zeros((2, 5)), np.zeros((2, 5))); self.assertTrue(np.all(h[:, -1] == 1.0)); self.assertTrue(np.all((h >= 1e-6) & (h <= 1.0)))
        lv = np.array([[2.0, 0.0, 0.0]]); st = np.array([[8.0, 10.0, 0.0]]); h0 = (2.0 + 1e-9) / (20.0 + 1e-9)
        self.assertAlmostEqual(M.hsmm_hazard_update(lv, st)[0, 0], (2.0 + 0.5 * h0) / (10.0 + 0.5))               # pseudo-observation of weight 0.5 at the pooled hazard

    def test_duration_cap_equals_scheduled_updates_of_a_full_session(self):
        self.assertEqual(len(L.grid_slots(390)), M.DUR_CAP); self.assertEqual(V.make_model("hsmm", K=2).Dmax, 78); self.assertEqual(M.HSMM(2).Dmax, 78)

    def test_floors_are_the_documented_values_in_the_source(self):
        src = (HERE / 's5_models.py').read_text(encoding='utf-8'); lines = src.split(chr(10))
        self.assertEqual(M.WEIGHT_GUARD, 1e-12)
        body = chr(10).join(l for l in lines if not l.startswith(('PROB_FLOOR', 'WEIGHT_GUARD')))
        self.assertNotIn('1e-12', body, 'no bare 1e-12 outside the named constants'); self.assertGreaterEqual(body.count('PROB_FLOOR'), 4); self.assertGreaterEqual(body.count('WEIGHT_GUARD'), 5)

    def test_record_corrections(self):
        self.assertIn("s5_bench.py", (HERE / "s5_fast.py").read_text(encoding="utf-8")[:700]); t = (ROOT / "PILOT_REPORT_LEGACY_FILES.md").read_text(encoding="utf-8")
        self.assertIn("PILOT_REPORT_LEGACY.md", t); self.assertEqual(len(re.findall(r"`[0-9a-f]{64}`", t)) >= 10 + 12, True)


def stub(m, occ_seq, ll_seq):
    """Student-t HMM whose EM is replaced: each attempt consumes one occupancy vector and one final log-likelihood."""
    occ = iter(occ_seq); lls = iter(ll_seq); cur = {}
    m._init = lambda b, r: cur.update(o=next(occ), ll=next(lls)); m._em_step = lambda b: (setattr(m, "_occ", cur["o"]), cur["ll"])[1]
    m._state = lambda: {"ll": cur["ll"]}; m._load = lambda s: setattr(m, "_loaded", s); m._reorder = lambda: None; return m


GOOD, BAD = np.array([0.5, 0.5]), np.array([0.995, 0.005])


class TestFinding19(unittest.TestCase):
    batch = {"real": np.ones((1, 100), bool)}

    def test_restart_then_success_is_recorded(self):
        m = stub(M.StudentTHMM(2, 1), [BAD, BAD, GOOD], [-10.0, -9.0, -12.0]); m.fit(self.batch)
        self.assertEqual((m.fit_info["restarts"], m.fit_info["attempts"], m.fit_info["occupancy_ok"], m.fit_info["kept_fit_occupancy_ok"]), (2, [3], [True], True))

    def test_exhausted_attempts_are_flagged_and_behaviour_is_unchanged(self):
        m = stub(M.StudentTHMM(2, 1), [BAD] * 10, [-10.0 - i for i in range(10)]); m.fit(self.batch)
        self.assertEqual((m.fit_info["restarts"], m.fit_info["attempts"], m.fit_info["occupancy_ok"], m.fit_info["kept_fit_occupancy_ok"]), (10, [10], [False], False))
        self.assertEqual(m._loaded, {"ll": -19.0})                                                              # the failing fit is still kept (current behaviour, left open in A14)

    def test_higher_likelihood_violating_start_is_still_kept_and_flagged(self):
        m = stub(M.StudentTHMM(2, 2), [GOOD, BAD * 0 + BAD] + [BAD] * 9, [-20.0] + [-5.0] * 10); m.fit(self.batch)
        self.assertEqual(m.fit_info["occupancy_ok"], [True, False]); self.assertFalse(m.fit_info["kept_fit_occupancy_ok"]); self.assertEqual(m._loaded, {"ll": -5.0})     # documents the open design choice


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a14.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
