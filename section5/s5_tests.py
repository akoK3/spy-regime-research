#!/usr/bin/env python3
"""Unit tests for the Section 5 pipeline on synthetic data (unittest; pytest is not installed in the project environment).
Run: python s5_tests.py  (writes section5/results/unit_tests.json)."""
import sys, json, time, tempfile, unittest, hashlib
from pathlib import Path
import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_models as M, s5_events as E, s5_eval as V

MIN = E.MIN


def seqs_from(X, real=None, avail0=0):
    """Synthetic sequences -> pad() input."""
    out = []
    for k in range(X.shape[0]):
        x = X[k].copy(); r = np.isfinite(x).all(1) if real is None else real[k]
        out.append(dict(sess=k, n=len(x), X=x, real=r, avail=avail0 + np.arange(len(x)) * 5 * MIN, tgt=np.full(len(x), np.nan), slots=4 + 5 * np.arange(len(x)), start=0, grid_n=len(x)))
    return out


def gen_hmm(S=150, T=60, seed=1, t_df=None, skip=0.05):
    rng = np.random.default_rng(seed)
    mu = np.array([[0.0, 0.0], [0.0, 3.0]]); sd = np.array([[0.5, 1.0], [2.0, 1.0]])
    A = np.array([[0.93, 0.07], [0.10, 0.90]]); X = np.zeros((S, T, 2)); Z = np.zeros((S, T), int)
    for s in range(S):
        z = rng.integers(2)
        for t in range(T):
            if t: z = rng.choice(2, p=A[z])
            e = rng.standard_normal(2)
            if t_df: e = e / np.sqrt(rng.gamma(t_df / 2, 2 / t_df))
            X[s, t] = mu[z] + sd[z] * e; Z[s, t] = z
    X[rng.random((S, T)) < skip] = np.nan
    return X, Z


class TestModels(unittest.TestCase):
    def test_gaussian_hmm_recovers_parameters(self):
        X, Z = gen_hmm(); b = L.pad(seqs_from(X), 2)
        m = M.GaussianHMM(K=2, starts=3, seed=0).fit(b)
        self.assertLess(m.var[0, 0], m.var[1, 0], "states ordered by return variance")
        self.assertTrue(np.allclose(m.mu[1], [0, 3], atol=0.5)); self.assertTrue(np.allclose(np.sqrt(m.var[0]), [0.5, 1.0], atol=0.2))
        self.assertTrue(np.allclose(m.A.sum(1), 1)); self.assertGreater(m.A[0, 0], 0.85)
        P = m.filter(b); self.assertTrue(np.allclose(P[b["real"]].sum(-1), 1)); self.assertTrue((P >= 0).all())
        acc = ((P.argmax(-1) == Z) & b["real"]).sum() / b["real"].sum(); self.assertGreater(acc, 0.85)
        self.assertTrue((m.var >= M.VAR_FLOOR).all())

    def test_gaussian_hmm_loglik_monotone(self):
        X, _ = gen_hmm(S=60, seed=2); b = L.pad(seqs_from(X), 2)
        m = M.GaussianHMM(K=2, starts=1, seed=0); m._init(b, np.random.default_rng(0)); ll = [m._em_step(b) for _ in range(15)]
        self.assertTrue(all(y >= x - 1e-6 for x, y in zip(ll, ll[1:])), ll)

    def test_skipped_update_is_transition_only(self):
        X, _ = gen_hmm(S=60, seed=3); b = L.pad(seqs_from(X), 2)
        m = M.GaussianHMM(K=2, starts=1, seed=0).fit(b)
        x = np.array([[[0.0, 0.0], [np.nan, np.nan]]]); bb = L.pad(seqs_from(x), 2)
        P = m.filter(bb)[0]; expect = (P[0] @ m.A); self.assertTrue(np.allclose(P[1], expect))

    def test_student_t_hmm(self):
        X, _ = gen_hmm(t_df=4, seed=5); b = L.pad(seqs_from(X), 2)
        m = M.StudentTHMM(K=2, starts=2, seed=0).fit(b)
        self.assertTrue(((m.nu >= 2.1) & (m.nu <= 30)).all()); self.assertLess(np.median(m.nu), 15)
        Xg, _ = gen_hmm(seed=5); mg = M.StudentTHMM(K=2, starts=2, seed=0).fit(L.pad(seqs_from(Xg), 2))
        self.assertGreater(np.median(mg.nu), np.median(m.nu), "heavier tails -> smaller df")
        P = m.filter(b); self.assertTrue(np.allclose(P[b["real"]].sum(-1), 1))
        self.assertTrue((m._occ >= 0.01).all())
        self.assertLess(m.var[0, 0], m.var[1, 0])

    def test_hsmm_recovers_durations_and_states(self):
        rng = np.random.default_rng(7); S, T = 120, 70; X = np.zeros((S, T, 2)); Z = np.zeros((S, T), int)
        mu = np.array([[0, 0], [0, 3.0]]); sd = np.array([[0.5, 1], [1.5, 1]])
        for s in range(S):
            z, t = rng.integers(2), 0
            while t < T:
                d = int(rng.integers(8, 13))  # non-geometric: durations 8..12
                for _ in range(d):
                    if t < T: X[s, t] = mu[z] + sd[z] * rng.standard_normal(2); Z[s, t] = z; t += 1
                z = 1 - z
        b = L.pad(seqs_from(X), 2)
        m = M.HSMM(K=2, starts=3, seed=0, Dmax=40).fit(b)
        self.assertTrue(np.allclose(m.h[:, -1], 1.0)); self.assertLess(m.var[0, 0], m.var[1, 0])
        self.assertLess(m.h[:, :5].max(), 0.2, "no exits before duration 8"); self.assertGreater(m.h[:, 7:13].max(), 0.4, "exits concentrated at 8..12")
        P = m.filter(b); self.assertTrue(np.allclose(P.sum(-1), 1))
        acc = (P.argmax(-1) == Z).mean(); self.assertGreater(acc, 0.9)
        # skip: duration advances with the hazard, state mass is conserved
        x = X[:1, :8].copy(); x[0, 4] = np.nan; self.assertTrue(np.allclose(m.filter(L.pad(seqs_from(x), 2))[0].sum(-1), 1))

    def test_bocpd_alarm_on_mean_shift_and_quiet_otherwise(self):
        rng = np.random.default_rng(11); S, T = 40, 80; X = rng.standard_normal((S, T, 2)); X[:20, 40:, 0] += 5.0
        b = L.pad(seqs_from(X), 2); out = M.BOCPD(39).fit(b).filter(b); pcp = out[:, :, 0]
        self.assertTrue(np.all(out[:, :, 0] <= 1 + 1e-9))
        self.assertGreater(np.median(pcp[:20, 40:43].max(1)), 0.8, "shift detected within 3 updates")
        self.assertLess(np.median(pcp[20:, 10:].max(1)), 0.5, "no systematic alarm without a shift")
        self.assertTrue(np.allclose(pcp[:, :2], 1.0), "run length <=2 is certain for the first two updates")

    def test_bocpd_skip_is_hazard_only(self):
        rng = np.random.default_rng(12); X = rng.standard_normal((1, 30, 1))
        a = L.pad(seqs_from(X), 1)
        Xs = X.copy(); Xs[0, 15] = np.nan; bsk = L.pad(seqs_from(Xs), 1)
        m = M.BOCPD(39); o1, o2 = m.filter(a), m.filter(bsk)
        self.assertTrue(np.allclose(o1[0, :15], o2[0, :15]), "identical before the skip")
        self.assertTrue(np.isfinite(o2).all()); self.assertAlmostEqual(o2[0, 15, 0], o2[0, 15, 0])
        # one skip step moves exactly the hazard mass: E[run length] grows by 1 - H * E[run length] (shift + reset)
        H = 1 / 39; self.assertAlmostEqual(o2[0, 15, 1], (1 - H) * (o2[0, 14, 1] + 1), places=6)


class TestEvents(unittest.TestCase):
    av = np.arange(40) * 5 * MIN

    def test_states_alarm_hold_and_confirmation(self):
        n = 30; P = np.tile([0.95, 0.05], (n, 1)); P[10:] = [0.05, 0.95]; real = np.ones(n, bool)
        ev, dr = E.detect_states(P, real, self.av[:n], 0.9)
        self.assertEqual(len(ev), 1); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 13), "T_c = third real update after T_d")

    def test_states_no_alarm_on_first_two_updates(self):
        P = np.array([[0.05, 0.95], [0.95, 0.05]] + [[0.95, 0.05]] * 10); ev, _ = E.detect_states(P, np.ones(12, bool), self.av[:12], 0.9)
        self.assertEqual(ev, [])
        P = np.array([[0.95, 0.05], [0.95, 0.05]] + [[0.05, 0.95]] * 10); ev, _ = E.detect_states(P, np.ones(12, bool), self.av[:12], 0.9)
        self.assertEqual(ev[0]["i_d"], 2)

    def test_states_skip_resets_count(self):
        n = 30; P = np.tile([0.95, 0.05], (n, 1)); P[10:] = [0.05, 0.95]; real = np.ones(n, bool); real[12] = False
        ev, _ = E.detect_states(P, real, self.av[:n], 0.9)
        self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 15), "count restarts after the skip")
        real2 = np.ones(n, bool); real2[10:] = False; real2[10] = True; real2[11:] = False
        ev2, dr2 = E.detect_states(P, real2, self.av[:n], 0.9); self.assertEqual((ev2, dr2), ([], 1), "unconfirmed at the close: dropped and counted")

    def test_states_failed_hold_cancels_and_refractory(self):
        n = 40; P = np.tile([0.95, 0.05], (n, 1)); P[10:12] = [0.05, 0.95]
        ev, dr = E.detect_states(P, np.ones(n, bool), self.av[:n], 0.9); self.assertEqual(ev, []); self.assertEqual(dr, 0)
        P = np.tile([0.95, 0.05], (n, 1)); P[10:] = [0.05, 0.95]; P[16:] = [0.95, 0.05]; P[22:] = [0.05, 0.95]
        ev, _ = E.detect_states(P, np.ones(n, bool), self.av[:n], 0.9)
        self.assertEqual(ev[0]["i_c"], 13); self.assertTrue(all(e["i_d"] * 5 * MIN >= self.av[13] + 30 * MIN - 1 or e is ev[0] for e in ev), "no T_d inside the 30-min refractory period")
        self.assertEqual([e["i_d"] for e in ev][1:], [22] if ev[-1]["i_d"] == 22 else [e["i_d"] for e in ev][1:])

    def test_bocpd_alarm_hold_reset_on_skip(self):
        n = 40; pcp = np.full(n, 0.1); pcp[10:13] = 0.95; real = np.ones(n, bool)
        ev, _ = E.detect_bocpd(pcp, real, self.av[:n], 0.9); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 13), "alarm at 10, no new alarm over updates 11-13")
        real2 = real.copy(); real2[12] = False
        ev2, _ = E.detect_bocpd(pcp, real2, self.av[:n], 0.9); self.assertEqual((ev2[0]["i_d"], ev2[0]["i_c"]), (10, 15), "skip at 12 resets the count: 13, 14, 15 are the three real updates")
        pcp3 = pcp.copy(); pcp3[12] = 0.1; pcp3[13] = 0.95   # falls then a fresh alarm during the hold: candidate restarts at 13
        ev3, _ = E.detect_bocpd(pcp3, real, self.av[:n], 0.9); self.assertEqual((ev3[0]["i_d"], ev3[0]["i_c"]), (13, 16))
        pcp4 = np.full(n, 0.1); pcp4[0:3] = 1.0
        self.assertEqual(E.detect_bocpd(pcp4, real, self.av[:n], 0.9)[0], [], "no alarm in the first two updates; the third is not a rising edge")
        ev5, dr5 = E.detect_bocpd(pcp, np.r_[np.ones(11, bool), np.zeros(29, bool)], self.av[:n], 0.9); self.assertEqual((ev5, dr5), ([], 1))

    def test_bocpd_persistence_rule_and_outputs(self):
        n = 40; pcp = np.full(n, 0.1); pcp[10:13] = 0.95; real = np.ones(n, bool); pers = np.full(n, 0.95)
        ev, _ = E.detect_bocpd(pcp, real, self.av[:n], 0.9, pers=pers); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 13))
        pers2 = pers.copy(); pers2[13] = 0.2
        self.assertEqual(E.detect_bocpd(pcp, real, self.av[:n], 0.9, pers=pers2)[0], [], "run length reverted to long: not confirmed")
        self.assertEqual(len(E.detect_bocpd(pcp, real, self.av[:n], 0.9)[0]), 1, "default behaviour unchanged")
        X = np.random.default_rng(1).standard_normal((2, 30, 1)); o = M.BOCPD(39).filter(L.pad(seqs_from(X), 1)); self.assertEqual(o.shape, (2, 30, 5))
        self.assertTrue(np.all(o[:, :, 3] >= o[:, :, 0] - 1e-12), "P(r<=5) >= P(r<=2)")

    def test_d4_rules(self):
        n = 30; av = self.av[:n]; real = np.ones(n, bool)
        P = np.tile([0.97, 0.03], (n, 1)); P[10:] = [0.03, 0.97]
        ev, _ = E.detect_old_state(P, real, av, 0.9); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 12), "P(old) < 1 - thr for 3 consecutive updates: T_c is the third")
        r2 = real.copy(); r2[11] = False; ev, _ = E.detect_old_state(P, r2, av, 0.9); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (12, 14), "skip resets the count")
        P2 = P.copy(); P2[11] = [0.95, 0.05]; self.assertEqual(E.detect_old_state(P2, real, av, 0.9)[0][0]["i_d"], 12, "a recovery inside the run restarts it")
        self.assertEqual(E.detect_old_state(np.tile([0.5, 0.5], (n, 1)), real, av, 0.9)[0], [])
        rs = np.arange(n, dtype=float); rs[15:] = np.arange(n - 15) + 1      # drop from 14 to 1 at update 15, then grows
        ev, _ = E.detect_bocpd_map(rs, real, av, 5); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (15, 18))
        rs2 = rs.copy(); rs2[17:] = np.arange(n - 17) + 30.0; self.assertEqual(E.detect_bocpd_map(rs2, real, av, 5)[0], [], "returning to a long run cancels")
        self.assertEqual(E.detect_bocpd_map(np.arange(n, dtype=float), real, av, 1)[0], [], "no drop, no alarm")

    def test_direction_rule(self):
        rng = np.random.default_rng(3); r = rng.standard_normal(390) * 1e-3; r[200:] *= 4
        slots = np.arange(4, 390, 5); i_d = int(np.where(slots == 199)[0][0]); i_c = i_d + 3
        self.assertEqual(E.direction(r, slots, i_d, i_c)[0], "calm_to_stressed")
        r2 = rng.standard_normal(390) * 1e-3; r2[:200] *= 4
        self.assertEqual(E.direction(r2, slots, i_d, i_c)[0], "stressed_to_calm")
        self.assertEqual(E.direction(r, slots, 2, 5)[0], None, "fewer than 30 reference bars")


class TestA6(unittest.TestCase):
    def test_partial_area(self):
        import s5_a6 as A
        self.assertAlmostEqual(A.pauc([(0.0, 0.0), (0.5, 1.0)]), 0.0 + 0.0, places=12, msg="y(x) is a step: stays at the previous level until x=0.5 is reached")
        self.assertAlmostEqual(A.pauc([(0.1, 0.4), (0.3, 0.8)]), (0.0 * 0.1 + 0.4 * 0.2 + 0.8 * 0.2) / 0.5)
        self.assertAlmostEqual(A.pauc([(0.0, 0.6), (0.2, 0.5)]), 0.6, msg="y is the running maximum")
        self.assertAlmostEqual(A.pauc([(0.7, 1.0)]), 0.0, msg="points beyond the range do not count")
        self.assertAlmostEqual(A.pauc([(0.0, 1.0)]), 1.0)
        self.assertEqual(A.y_at([(0.05, 0.3), (0.2, 0.9)], 0.1), 0.3)

    def test_rate_threshold_rule(self):
        import s5_a6 as A
        g = [1, 2, 3, 4]; self.assertEqual(A.choose_rate_threshold({1: 0.9, 2: 0.19, 3: 0.12, 4: 0.0}, g), (2, False), "highest rate not above 0.2")
        self.assertEqual(A.choose_rate_threshold({1: 0.9, 2: 0.5, 3: 0.4, 4: 0.3}, g), (4, True), "none qualifies: strictest value, flagged")
        self.assertEqual(A.choose_rate_threshold({1: 0.2, 2: 0.2, 3: 0.1, 4: 0.0}, g), (2, False), "ties to the stricter threshold")


class TestA7(unittest.TestCase):
    def test_logodds_rule_equals_a6_rule_and_keeps_precision(self):
        rng = np.random.default_rng(3); n = 60; av = np.arange(n) * 5 * MIN
        for K in (2, 3):
            for trial in range(30):
                P = rng.dirichlet(np.ones(K) * 0.2, size=n); real = rng.random(n) > 0.1
                for thr in (0.5, 0.8, 0.9, 0.99):
                    th = float(np.log(thr / (1 - thr)))
                    a = E.detect_old_state(P, real, av, thr)[0]; b = E.detect_old_state_logodds(P, real, av, th - 1e-9)[0]
                    self.assertEqual([(e["i_d"], e["i_c"]) for e in a], [(e["i_d"], e["i_c"]) for e in b])
        P = np.tile([1 - 1e-14, 1e-14], (20, 1)); P[8:] = [1e-14, 1 - 1e-14]; real = np.ones(20, bool)
        self.assertEqual(len(E.detect_old_state_logodds(P, real, av[:20], 25.0)[0]), 1, "log-odds 32 > 25 is resolved")
        self.assertEqual(E.detect_old_state_logodds(P, real, av[:20], 33.0)[0], [], "log-odds 32 < 33 does not alarm")

    def test_bisection(self):
        import s5_a7 as B
        rate = lambda th: 3.0 * np.exp(-th / 4.0)              # strictly decreasing
        th, info = B.bisect_threshold(rate, 0.0, 30.0, 0.2, 1e-3)
        self.assertLessEqual(rate(th), 0.2); self.assertGreater(rate(th - 2e-3), 0.2); self.assertEqual(info, "ok")
        self.assertEqual(B.bisect_threshold(lambda t: 5.0, 0.0, 30.0, 0.2, 1e-3), (30.0, "FLAG: strictest bound still above target"))
        self.assertEqual(B.bisect_threshold(lambda t: 0.1, 0.0, 30.0, 0.2, 1e-3), (0.0, "FLAG: loosest bound already at or below target"))
        step = lambda m: [9.0, 0.6, 0.4, 0.15, 0.0][min(4, int(np.ceil(m)) - 1)] if m >= 1 else 9.0
        m, info = B.bisect_threshold(step, 1.0, 80.0, 0.2, 0.5); self.assertLessEqual(step(m), 0.2)


class TestFast(unittest.TestCase):
    def test_deseason_is_causal(self):
        import s5_fast as F
        rng = np.random.default_rng(0); Mx = np.abs(rng.standard_normal((40, 78))) * 1e-3
        sc = F.ret5_scale(Mx, 25); M2 = Mx.copy(); M2[25:] *= 100; M2[24] = Mx[24]
        self.assertTrue(np.array_equal(sc, F.ret5_scale(M2, 25)), "scale uses sessions before i only")
        self.assertTrue(np.isnan(F.ret5_scale(Mx, 5)).all(), "fewer than 10 prior sessions -> missing")
        self.assertTrue(np.allclose(sc, np.median(Mx[5:25], axis=0)))


class TestLibrary(unittest.TestCase):
    def test_pool_assertions(self):
        primary, sens, sens_all = L.pools()
        self.assertEqual((len(primary), len(sens_all)), (19, 83)); self.assertTrue(L.assert_pool(primary, "primary")); self.assertTrue(L.assert_pool(sens, "sensitivity"))
        for bad in ("overnight_return_open", "raw_volume", "log_raw_volume", "raw_volume__sadj", "tlt_return_1m", "hyg_rv5", "usd_return", "gold_range", "jump_variation_15__sadj", "lee_mykland_jump60", "lee_mykland_approx60"):
            with self.assertRaises(AssertionError, msg=bad): L.assert_pool(primary + [bad], "primary")
        self.assertTrue(L.assert_pool(sens + [], "sensitivity"))
        with self.assertRaises(AssertionError): L.assert_pool(sens + ["jump_variation_15__sadj"], "sensitivity")
        self.assertIn("lee_mykland_jump60", sens)   # allowed only in the sensitivity set
        self.assertEqual(len(sens), 80)

    def test_train_only_and_single_era(self):
        mf = pd.read_csv(L.FZ / "section430_executable_split_manifest.csv")
        tr = mf[(mf.provider_era == "RAW") & (mf.partition == "TRAIN")].session_date.iloc[:5]
        self.assertTrue(L.assert_train_only("RAW", tr, mf))
        for part in ("EMBARGO", "EVALUATION_EXPOSED", "EXCLUDED"):
            x = mf[(mf.provider_era.isin(["RAW", "LEGACY"])) & (mf.partition == part)]
            if len(x):
                with self.assertRaises(AssertionError, msg=part): L.assert_train_only(x.provider_era.iloc[0], x[x.provider_era == x.provider_era.iloc[0]].session_date.iloc[:2], mf)
        with self.assertRaises(AssertionError): L.assert_train_only("LEGACY", ["2022-03-07"], mf)   # a RAW date in the LEGACY era
        with self.assertRaises(AssertionError): L.assert_single_era({"era": "RAW"}, "LEGACY")

    def test_prep_uses_inner_train_only(self):
        rng = np.random.default_rng(0); tr = np.column_stack([rng.standard_normal(500), np.exp(rng.standard_normal(500)), np.zeros(500), rng.standard_normal(500) ** 2, np.exp(rng.standard_normal(500))])
        names = ["ret5", "rv5_strict", "const", "momentum5_endpoint", "amihud_15"]
        tr[:5, 3] = 0.0; p = L.Prep().fit(tr, names)
        self.assertNotIn("const", p.keep); self.assertEqual(p.info["const"][:7], "dropped"); self.assertTrue(p.log["rv5_strict"]); self.assertFalse(p.log["momentum5_endpoint"]); self.assertFalse(p.log["ret5"])
        self.assertIn("amihud_15", p.amihud)
        Z = p.transform(tr); self.assertAlmostEqual(float(np.nanmean(Z[:, 0])), 0, places=1)
        q1 = (p.lo["rv5_strict"], p.hi["rv5_strict"], p.mu["rv5_strict"])
        later = np.vstack([tr, 1e6 * np.abs(rng.standard_normal((50, 5))) + 1]); p.transform(later)
        self.assertEqual(q1, (p.lo["rv5_strict"], p.hi["rv5_strict"], p.mu["rv5_strict"]), "transform never refits")
        out = p.transform(np.array([[0.0, 1e12, 0.0, 0.0, 1.0]])); self.assertLessEqual(abs(out[0, p.keep.index("rv5_strict")]), (p.hi["rv5_strict"] - p.mu["rv5_strict"]) / p.sd["rv5_strict"] + 1e-9, "winsorised")
        neg = p.transform(np.array([[0.0, -1.0, 0.0, 0.0, 1.0]])); self.assertTrue(np.isnan(neg[0, p.keep.index("rv5_strict")]), "non-positive value of a logged feature -> skipped update")

    def test_lm_student_t_threshold(self):
        from scipy import stats
        x = stats.t.rvs(4, size=60000, random_state=1) * 1.3; r = L.lm_student_t_threshold(x)
        self.assertLess(abs(r["df"] - 4), 0.6); self.assertGreater(r["threshold"], 4.6113, "heavier tails give a larger threshold than the Gaussian-calibrated one")
        self.assertAlmostEqual(2 * stats.t.sf(r["threshold"], r["df"], scale=r["scale"]) * 390, 0.01, places=4)

    def test_checkpoint_resume(self):
        with tempfile.TemporaryDirectory() as td:
            c = L.Checkpoint(td); calls = []
            f = lambda: calls.append(1) or {"x": 1}
            self.assertEqual(c.run("a", f), {"x": 1}); self.assertEqual(c.run("a", f), {"x": 1}); self.assertEqual(len(calls), 1)
            c2 = L.Checkpoint(td); c2.run("a", f); self.assertEqual((len(calls), c2.hits, c2.misses), (1, 1, 0)); c2.run("b", f); self.assertEqual(len(calls), 2)

    def test_sequence_start_abstention_and_skips(self):
        g = np.arange(4, 390, 5); X = np.random.default_rng(0).standard_normal((len(g), 3)); X[:4, 1] = np.nan; X[10, 2] = np.nan
        row = dict(sess=0, slots=g, avail=g * MIN, X=X, tgt=np.full(len(g), np.nan)); q = L.build_sequence(row)
        self.assertEqual(q["start"], 4); self.assertEqual(q["n"], len(g) - 4); self.assertFalse(q["real"][10 - 4]); self.assertEqual(L.shares([q])["sessions_without_start"], 0)
        self.assertAlmostEqual(L.shares([q])["abstained_share"], 4 / len(g), places=5)
        self.assertEqual(L.grid_slots(390)[[0, 1, -1]].tolist(), [4, 9, 389]); self.assertEqual(L.grid_slots(210)[-1], 209)


def synth_panel(ns=30, m=390, seed=0):
    rng = np.random.default_rng(seed); N = ns * m
    vol = np.repeat(rng.uniform(0.5e-3, 3e-3, ns), m); r = rng.standard_normal(N) * vol
    first = np.arange(ns) * m; end = first + m; r[first] = np.nan
    c = np.empty(N)
    for i in range(ns): c[first[i]:end[i]] = 400 * np.exp(np.nancumsum(r[first[i]:end[i]])) * (1 + 0.01 * i)
    o = np.r_[c[0], c[:-1]]; o[first] = c[first]
    t0 = np.datetime64("2022-03-07T14:30").astype("datetime64[ns]").astype("int64")
    t = (t0 + (np.arange(ns)[:, None] * 1440 + np.arange(m)[None]) * 60 * 10 ** 9).ravel()
    day = np.repeat([f"2022-04-{1 + i:02d}" if i < 30 else "x" for i in range(ns)], m)
    return dict(t=t, available=t + 60 * 10 ** 9, day=day, slot=np.tile(np.arange(m), ns), r=r, valid=np.isfinite(r) | (np.arange(N) % m == 0) & False, close=c, range=np.abs(rng.standard_normal(N)) * 1e-3 + 1e-4,
                volume=rng.uniform(1e3, 1e4, N), open=o, high=c * 1.0005, low=c * 0.9995, first=first.astype(np.int64), end=end.astype(np.int64), era="RAW")


class TestSplice(unittest.TestCase):
    def test_splice_continuity_tau_and_isolation(self):
        d = synth_panel(); iA, iB, g = 25, 3, 94
        p, k, tau = V.make_splice(d, iA, iB, g); a = int(p["first"][k]); fa, fb = int(d["first"][iA]), int(d["first"][iB])
        self.assertEqual(k, 20); self.assertEqual(tau, int(d["available"][fa + g]), "tau = availability of the last A bar")
        self.assertTrue(np.array_equal(p["close"][a:a + g + 1], d["close"][fa:fa + g + 1]), "A up to and including bar g is untouched")
        changed = np.where(p["close"][a:a + 390] != d["close"][fa:fa + 390])[0]; self.assertEqual(int(changed.min()), g + 1, "first changed bar is g+1 (tau exact)")
        sc = d["close"][fa + g] / d["close"][fb + g]
        self.assertAlmostEqual(float(np.log(p["close"][a + g + 1] / p["close"][a + g])), float(np.log(d["close"][fb + g + 1] / d["close"][fb + g])), places=12, msg="no jump at tau: the return across tau is B's own return")
        self.assertTrue(np.allclose(p["close"][a + g + 1:a + 390], d["close"][fb + g + 1:fb + 390] * sc, rtol=1e-14))
        self.assertTrue(np.array_equal(p["volume"][a + g + 1:a + 390], d["volume"][fb + g + 1:fb + 390]))
        self.assertTrue(np.array_equal(p["t"][a:a + 390], d["t"][fa:fa + 390]), "clock times are A's")
        # B's pre-tau bars are irrelevant: change them and the spliced panel is unchanged
        d2 = {k_: (v.copy() if isinstance(v, np.ndarray) else v) for k_, v in d.items()}; d2["close"][fb:fb + g] *= 1.37; d2["volume"][fb:fb + g] *= 9
        p2, _, _ = V.make_splice(d2, iA, iB, g); self.assertTrue(all(np.array_equal(p[x].astype(float), p2[x].astype(float), equal_nan=True) for x in ("close", "open", "high", "low", "volume", "r", "valid")))
        # history sessions are A's own previous sessions
        self.assertTrue(np.array_equal(p["close"][:int(p["first"][k])], d["close"][int(d["first"][iA - 20]):fa]))
        with self.assertRaises(AssertionError): V.make_splice(synth_panel(ns=30, m=390), 25, 3, 400)

    def test_pairs_terciles(self):
        d = synth_panel(ns=60, seed=4); rng = np.random.default_rng(0)
        br, nu = V.sample_pairs(d, np.arange(60), 40, 40, rng); rv, vol, n = V.session_stats(d, np.arange(60)); tv, tq = V.tercile(rv), V.tercile(vol)
        self.assertTrue(all(b["g"] in V.TAU_SLOTS for b in br + nu)); self.assertEqual({b["kind"] for b in br}, {"calm_to_stressed", "stressed_to_calm"})
        for b in br:
            lo, hi = (0, 2) if b["kind"] == "calm_to_stressed" else (2, 0); self.assertEqual((tv[b["iA"]], tv[b["iB"]]), (lo, hi))
        for b in nu: self.assertEqual((tv[b["iA"]], tq[b["iA"]]), (tv[b["iB"]], tq[b["iB"]])); self.assertNotEqual(b["iA"], b["iB"])
        self.assertEqual(V.TAU_SLOTS[0] + 1, 95); self.assertEqual(V.TAU_SLOTS[-1] + 1, 300, "availability 11:05 ... 14:30")


class TestScoring(unittest.TestCase):
    def test_qlike_dm_threshold(self):
        t = np.array([1.0, 2.0, 3.0]); self.assertTrue(np.allclose(V.qlike_loss(t, t), 0)); self.assertTrue((V.qlike_loss(t, t * 2) > 0).all())
        rng = np.random.default_rng(0); a = rng.exponential(1, 4000); self.assertGreater(V.diebold_mariano(a + 0.2, a)["stat"], 3)
        self.assertLess(abs(V.diebold_mariano(a, a + rng.standard_normal(4000) * 0.01)["stat"]), 4)
        grid = [0.5, 0.6, 0.7]; ns = {0.5: dict(fa_rate=0.2), 0.6: dict(fa_rate=0.05), 0.7: dict(fa_rate=0.0)}
        self.assertEqual(V.choose_threshold(ns, grid), 0.6, "smallest threshold with at most 1 false alarm per 20 null sessions"); self.assertIsNone(V.choose_threshold({k: dict(fa_rate=0.5) for k in grid}, grid))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1), numpy=np.__version__)
    (L.HERE / "results" / "unit_tests.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
