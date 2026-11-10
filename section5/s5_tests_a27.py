#!/usr/bin/env python3
"""A27 tests (AMENDMENT_A27.md rule 3b): r = 1 confirms on the first update above threshold, r = 4 needs four; the vectorised sweeps with run / hold = r equal the loop
detectors with the same r; the validation alarm rate is non-increasing in r at a fixed threshold; r = 3 is the default of every function (the MR2 rule)."""
import sys, inspect, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_sweep as W, s5_events as E, s5_a27_confirm as Z

M = W.MIN


def session(n_above, start=10, T=40):
    """2-state session: old state 0 until update `start`, then n_above updates with P(state 1) = 0.99, then 0.5/0.5 (log-odds 0, never above theta = 0 in either direction)."""
    P = np.tile([0.99, 0.01], (T, 1)); P[start:start + n_above] = [0.01, 0.99]; P[start + n_above:] = [0.5, 0.5]; real = np.ones(T, bool); avail = (np.arange(T) * 5 + 1) * M; return P, real, avail.astype(np.int64)


def rand_session(rng, T=78, K=3):
    P = rng.dirichlet(np.full(K, 0.3), T); real = rng.random(T) > 0.05; return P, real, ((np.arange(T) * 5 + 1) * M).astype(np.int64)


class TestA27(unittest.TestCase):
    def test_r1_first_update(self):
        P, real, av = session(1); ev = Z.events_r("gaussian_hmm", dict(P=P), dict(real=real, avail=av, n=len(real)), 0.0, 1)
        self.assertEqual(len(ev), 1); self.assertEqual(ev[0]["i_d"], 10); self.assertEqual(ev[0]["i_c"], 10)

    def test_r4_needs_four(self):
        for n, want in ((3, 0), (4, 1)):
            P, real, av = session(n); ev = Z.events_r("gaussian_hmm", dict(P=P), dict(real=real, avail=av, n=len(real)), 0.0, 4); self.assertEqual(len(ev), want)
        P, real, av = session(4); ev = Z.events_r("gaussian_hmm", dict(P=P), dict(real=real, avail=av, n=len(real)), 0.0, 4); self.assertEqual((ev[0]["i_d"], ev[0]["i_c"]), (10, 13))

    def test_bocpd_hold_r(self):
        T = 40; rs = np.arange(T, dtype=float); rs[15:] = np.arange(T - 15, dtype=float); real = np.ones(T, bool); av = ((np.arange(T) * 5 + 1) * M).astype(np.int64)
        for r in (1, 2, 3, 4):
            ev = Z.events_r("bocpd", dict(rstar=rs), dict(real=real, avail=av, n=T), 5.0, r); self.assertEqual(len(ev), 1); self.assertEqual(ev[0]["i_c"] - ev[0]["i_d"], r)

    def test_sweep_equals_loop(self):
        rng = np.random.default_rng(27); th = [0.0, 0.5, 1.0, 2.0, 4.0]
        for r in (1, 2, 3, 4):
            ses = [rand_session(rng) for _ in range(12)]; P = np.stack([s[0] for s in ses]); real = np.stack([s[1] for s in ses]); av = np.stack([s[2] for s in ses])
            cnt, _ = W.sweep_old_state(P, real, av, th, None, run=r)
            for i, (p, re, a) in enumerate(ses):
                for j, t in enumerate(th): self.assertEqual(cnt[i, j], len(E.detect_old_state_logodds(p, re, a, t, run=r)[0]))
            R = np.maximum(0, np.cumsum(rng.integers(-6, 3, size=(12, 78)), 1) + 40).astype(float); ms = [1.0, 3.0, 6.0]
            cb, _ = W.sweep_map(R, real, av, ms, None, hold=r)
            for i in range(12):
                for j, m in enumerate(ms): self.assertEqual(cb[i, j], len(E.detect_bocpd_map(R[i], real[i], av[i], m, hold=r)[0]))

    def test_rate_nonincreasing_in_r(self):
        rng = np.random.default_rng(3); ses = [rand_session(rng) for _ in range(30)]
        for t in (0.0, 1.0, 3.0):
            n = [sum(len(Z.events_r("gaussian_hmm", dict(P=p), dict(real=re, avail=a, n=len(re)), t, r)) for p, re, a in ses) for r in (1, 2, 3, 4)]
            self.assertEqual(n, sorted(n, reverse=True))

    def test_defaults_are_r3(self):
        self.assertEqual(inspect.signature(E.detect_old_state_logodds).parameters["run"].default, 3); self.assertEqual(inspect.signature(E.detect_bocpd_map).parameters["hold"].default, 3)
        self.assertEqual(inspect.signature(W.sweep_old_state).parameters["run"].default, 3); self.assertEqual(inspect.signature(W.sweep_map).parameters["hold"].default, 3)
        self.assertEqual(Z.MAIN_R, 3); self.assertEqual(Z.RS, (1, 2, 3, 4))


if __name__ == "__main__": unittest.main()
