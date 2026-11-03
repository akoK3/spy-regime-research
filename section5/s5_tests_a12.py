#!/usr/bin/env python3
"""A12 unit tests, one group per cold-audit finding: 6 EM tolerance, 7 old state in the refractory period, 9 break tau range, 14 hit window, 15 unconfirmed alarms; and the H1(c) schedule rule."""
import sys, json, time, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_models as M, s5_events as E, s5_sweep as W, s5_d2 as D2, s5_a6 as A, s5_eval as V, s5_d2_stable as S
from s5_tests import synth_panel

MIN = 60 * 10 ** 9; HERE = Path(__file__).resolve().parent


def seq_P(states, p=0.97):
    P = np.full((len(states), 2), 1 - p); P[np.arange(len(states)), states] = p; return P


def stub(m, seq):
    it = iter(seq + [seq[-1]] * 400); m._init = lambda *a: None; m._em_step = lambda b: next(it); m._state = lambda: {}; m._load = lambda s: None; m._reorder = lambda: None; return m


class TestFinding6(unittest.TestCase):
    LL = [-1000.0, -900.0, -899.96, -899.9602, -899.96025, -899.96026]

    def test_em_tolerance_is_absolute_one_e_minus_4_nats(self):
        # changes: 900, 0.04, 2e-4, 5e-5 -> stops at iteration 5 (|dll| = 5e-5 < 1e-4); the old relative rule (0.09 at |ll| 900) stopped at iteration 3
        m = stub(M.GaussianHMM(2, 1, iters=200, tol=1e-4), self.LL); m.fit(None); self.assertEqual(m.fit_info["iterations"], [5]); self.assertEqual(m.fit_info["converged"], [True])
        t = stub(M.StudentTHMM(2, 1, iters=200, tol=1e-4), self.LL); t._occ = np.array([0.5, 0.5]); t.fit(None); self.assertEqual(t.fit_info["iterations"], [5]); self.assertEqual(t.fit_info["converged"], [True])

    def test_hsmm_same_rule(self):
        h = M.HSMM(2, 1, iters=200, tol=1e-4); it = iter(self.LL + [self.LL[-1]] * 400); h._init = lambda *a: None; h._em_step = lambda b: next(it)
        h.pi = np.array([.5, .5]); h.A = np.eye(2); h.mu = np.zeros((2, 1)); h.var = np.ones((2, 1)); h.h = np.ones((2, 5)); h.fit(None); self.assertEqual(h.fit_info["iterations"], [5])

    def test_cap_is_reported_not_hidden(self):
        m = stub(M.GaussianHMM(2, 1, iters=10, tol=1e-4), [-1000.0 + i for i in range(500)]); m.fit(None); self.assertEqual(m.fit_info["iterations"], [10]); self.assertEqual(m.fit_info["converged"], [False])


class TestFinding7(unittest.TestCase):
    def setUp(self):
        self.P = seq_P([0, 0, 1, 1, 1] + [0] * 35); self.real = np.ones(40, bool); self.av = ((np.arange(40) + 1) * 5 * MIN).astype(np.int64)

    def test_old_state_not_rebased_in_refractory_loop(self):
        ev = E.detect_old_state_logodds(self.P, self.real, self.av, 2.0)[0]; self.assertEqual([(e["i_d"], e["i_c"]) for e in ev], [(2, 4), (10, 12)])      # state left at the first alarm is still 'old' after the refractory period
        ev = E.detect_old_state(self.P, self.real, self.av, 0.9)[0]; self.assertEqual([(e["i_d"], e["i_c"]) for e in ev], [(2, 4), (10, 12)])

    def test_sweep_equals_loop_on_the_scenario(self):
        cnt, hit = W.sweep_old_state(self.P[None], self.real[None], self.av[None], [2.0, 6.0], np.array([self.av[0]]))
        self.assertEqual(int(cnt[0, 0]), 2); self.assertEqual(int(cnt[0, 1]), 0)               # log-odds of a 0.97 state is 3.5: theta 6 never alarms


class TestFinding9(unittest.TestCase):
    def test_tau_cap_values(self):
        self.assertEqual(D2.tau_cap(None), 299); self.assertEqual(D2.tau_cap(30), 269); self.assertEqual(D2.tau_cap(60), 269); self.assertEqual(D2.tau_cap(120), 268)
        grid = V.TAU_SLOTS; self.assertEqual(max(t for t in grid if t <= D2.tau_cap(120)), 264); self.assertEqual(max(t for t in grid if t <= D2.tau_cap(30)), 269)
        self.assertEqual((int(V.TAU_SLOTS[-1]) + 1, 269 + 1), (300, 270), "availability 14:30 and 14:00")

    def test_build_specs_draws_permanent_breaks_to_14_30_and_sandwiches_within_caps(self):
        d = synth_panel(ns=60, seed=3); dv = S.des_variance(d); rng = np.random.default_rng(1)
        cells = [(3, "up", None), (3, "up", 30), (3, "up", 120)]; sp = A.build_specs(d, dv, list(range(25, 60)), rng, 0, cells, 80)
        g = {c: [s["g"] for s in sp if s["cell"][2] == c] for c in (None, 30, 120)}
        self.assertGreater(max(g[None]), 264); self.assertLessEqual(max(g[None]), 299); self.assertLessEqual(max(g[30]), 269); self.assertLessEqual(max(g[120]), 264)
        self.assertTrue(all(s["dur"] is None or s["g"] + s["dur"] + 1 <= 389 for s in sp))


class TestFinding14(unittest.TestCase):
    def test_hit_needs_first_update_after_tau_and_confirmation_within_60_min(self):
        av = ((np.arange(30) + 1) * 5 * MIN).astype(np.int64); tau = int(av[9]); ev = lambda d, c: [dict(i_d=d, i_c=c)]
        self.assertFalse(E.hit_in_window(ev(9, 11), av, tau)); self.assertFalse(E.hit_in_window(ev(8, 11), av, tau))           # run began at tau or before: pre-seam evidence
        self.assertTrue(E.hit_in_window(ev(10, 12), av, tau)); self.assertTrue(E.hit_in_window(ev(10, 21), av, tau)); self.assertFalse(E.hit_in_window(ev(10, 22), av, tau))   # T_c at tau + 60 min counts, +65 does not

    def test_sweeps_apply_the_rule(self):
        P = seq_P([0, 0, 0, 0, 1, 1, 1] + [1] * 20); real = np.ones(27, bool); av = ((np.arange(27) + 1) * 5 * MIN).astype(np.int64)
        c1, h1 = W.sweep_old_state(P[None], real[None], av[None], [2.0], np.array([av[3]]))      # run starts at update 4 (after tau at update 3): hit
        c2, h2 = W.sweep_old_state(P[None], real[None], av[None], [2.0], np.array([av[4]]))      # run starts at tau: no hit
        self.assertTrue(h1[0, 0]); self.assertFalse(h2[0, 0]); self.assertEqual(int(c1[0, 0]), int(c2[0, 0]))
        r = np.array([10, 11, 12, 13, 1, 2, 3, 4, 5, 6.0] + [7, 8, 9, 10, 11, 12, 13, 14, 15, 16.0]); rr = np.ones(20, bool); a2 = ((np.arange(20) + 1) * 5 * MIN).astype(np.int64)
        c, h = W.sweep_map(r[None], rr[None], a2[None], [5.0], np.array([a2[3]])); self.assertTrue(h[0, 0])
        c, h = W.sweep_map(r[None], rr[None], a2[None], [5.0], np.array([a2[4]])); self.assertFalse(h[0, 0])


class TestFinding15(unittest.TestCase):
    def av(self, n): return ((np.arange(n) + 1) * 5 * MIN).astype(np.int64)

    def test_open_run_at_close_is_counted_loop_and_sweep(self):
        P = seq_P([0, 0, 1, 1]); real = np.ones(4, bool); ev, dr = E.detect_old_state_logodds(P, real, self.av(4), 2.0); self.assertEqual((len(ev), dr), (0, 1))
        c, h, d = W.sweep_old_state(P[None], real[None], self.av(4)[None], [2.0, 6.0], None, return_dropped=True); self.assertEqual(d[0].tolist(), [1, 0])
        ev, dr = E.detect_old_state_logodds(seq_P([0, 0, 1, 1, 1]), np.ones(5, bool), self.av(5), 2.0); self.assertEqual((len(ev), dr), (1, 0))         # confirmed: not dropped
        ev, dr = E.detect_old_state_logodds(seq_P([0, 0, 1, 1, 0]), np.ones(5, bool), self.av(5), 2.0); self.assertEqual((len(ev), dr), (0, 0))         # broken before the close
        r3 = np.array([0, 1, 2, 3, 4, 5, 6, 7, 8, 1.0]); ev, dr = E.detect_bocpd_map(r3, np.ones(10, bool), self.av(10), 5.0); self.assertEqual((len(ev), dr), (0, 1))   # BOCPD drop at the last update
        c, h, d = W.sweep_map(r3[None], np.ones((1, 10), bool), self.av(10)[None], [5.0], None, return_dropped=True); self.assertEqual(int(d[0, 0]), 1)

    def test_padding_does_not_hide_an_open_run(self):
        P = np.full((1, 6, 2), 0.5); P[0, :4] = seq_P([0, 0, 1, 1]); real = np.array([[1, 1, 1, 1, 0, 0]], bool); av = np.array([[5, 10, 15, 20, 0, 0]], np.int64) * MIN
        c, h, d = W.sweep_old_state(P, real, av, [2.0], None, return_dropped=True); self.assertEqual(int(d[0, 0]), 1)

    def test_random_equality_of_loops_and_sweeps_including_dropped(self):
        rng = np.random.default_rng(5); S_, T = 50, 40; P = rng.dirichlet(np.ones(2) * 0.2, size=(S_, T)); real = rng.random((S_, T)) > 0.1; av = np.tile(self.av(T), (S_, 1))
        th = [0.0, 1.0, 3.0]; c, h, d = W.sweep_old_state(P, real, av, th, None, return_dropped=True)
        for s in range(S_):
            for g, t in enumerate(th):
                ev, dr = E.detect_old_state_logodds(P[s], real[s], av[s], t); self.assertEqual((int(c[s, g]), int(d[s, g])), (len(ev), dr))


class TestSchedule(unittest.TestCase):
    def test_parse_press_conference_page(self):
        import s5_h1c_schedule as H
        t = "<p>Related Information FOMC Meeting Statement &nbsp; (Released April 27, 2011 at 12:30 p.m.) Projections</p>"
        self.assertEqual(H.parse_pc(t), ("2011-04-27", "12:30")); self.assertEqual(H.parse_pc("FOMC Meeting Statement (Released January 25, 2012 at 12:20 p.m.)"), ("2012-01-25", "12:20"))
        self.assertEqual(H.parse_pc("FOMC Meeting Statement (Released March 20, 2013 at 2:00 p.m.)"), ("2013-03-20", "14:00")); self.assertIsNone(H.parse_pc("nothing"))
        self.assertEqual(H.mins("14:15"), 285); self.assertEqual(H.mins("12:30"), 180)

    def test_stored_schedule_follows_the_rule_and_catches_exceptions(self):
        j = json.loads((HERE / "results" / "h1c_schedule_times.json").read_text()); m = j["meetings"]
        self.assertTrue(j["rule_2013_plus_consistent"]); self.assertEqual(m["2012-01-25"]["time_et"], "12:20"); self.assertEqual(m["2011-04-27"]["time_et"], "12:30"); self.assertEqual(m["2003-01-29"]["time_et"], "14:15")
        self.assertEqual(m["2014-12-17"]["time_et"], "14:00"); self.assertEqual(m["2018-12-19"]["basis"], "statement page states the time")
        for d, v in m.items():
            if v["status"] == "excluded": self.assertTrue("2011-04" <= d < "2013-01" and "ambiguous" in v["reason"], d)
            else: self.assertTrue(v["basis"] and isinstance(v["minute_after_0930"], int), d)
            if "2011-04-01" <= d < "2013-01-01" and v["status"] == "time": self.assertIn("press-conference page", v["basis"], d)         # in that window only Fed-stated times are used
            if d < "2011-04-01": self.assertIn("Lucca and Moench", v["basis"], d)
        self.assertEqual(j["counts"]["time"] + j["counts"]["excluded"], len(m)); self.assertEqual(sorted(d for d, v in m.items() if v["status"] == "excluded"), ["2011-08-09", "2011-09-21", "2011-12-13", "2012-03-13", "2012-08-01", "2012-10-24"])


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a12.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
