#!/usr/bin/env python3
"""A25 tests (AMENDMENT_A25.md rule 2a): a detection before tau confirmed after it is a hit under the A22 shifted scoring at delta 10 but not under A25; a detection at
tau + 5 confirmed at tau + 45 is a hit at delta 0/5/10 under both; H1(c) window shortening; delta 0 H1(c) reproduces MR2."""
import sys, json, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_sweep as W, s5_h1c as HC, s5_a22 as A, s5_a25_delay as Z

M = W.MIN; TAU = 1_000 * M


def session(t_det_min, step_min=5):
    """One 2-state session whose old-state log-odds exceed every threshold from the update at t_det onwards; 5-min updates; warm updates long before."""
    ts = np.arange(-120, 120, step_min); P = np.where((ts >= t_det_min)[:, None], [[0.01, 0.99]], [[0.99, 0.01]])[None]
    real = np.ones((1, len(ts)), bool); avail = (TAU + ts * M).astype(np.int64)[None]; return P, real, avail


def hit_a22(t_det, dl):
    P, real, av = session(t_det); _, h = W.sweep_old_state(P, real, A.shift_avail(av, dl), [0.0], [TAU]); return bool(h[0, 0])


def hit_a25(t_det, dl):
    P, real, av = session(t_det); _, h = W.sweep_old_state(P, real, av, [0.0], [TAU], window=(60 - dl) * M); return bool(h[0, 0])


class TestA25(unittest.TestCase):
    def test_pre_tau_detection(self):
        # first update of the run at tau - 5, confirmation (3rd update) at tau + 5
        self.assertTrue(hit_a22(-5, 10)); self.assertFalse(hit_a25(-5, 10)); self.assertFalse(hit_a22(-5, 0)); self.assertFalse(hit_a25(-5, 0))

    def test_post_tau_detection(self):
        # first update at tau + 35, confirmation at tau + 45: a hit at 0/5/10 under both
        for dl in (0, 5, 10): self.assertTrue(hit_a22(35, dl)); self.assertTrue(hit_a25(35, dl))

    def test_window_edge(self):
        # confirmation at tau + 55: hit at delta 0 and 5, not at 10, under both scorings
        for f in (hit_a22, hit_a25): self.assertTrue(f(45, 0)); self.assertTrue(f(45, 5)); self.assertFalse(f(45, 10))

    def test_h1c_window(self):
        rel = 285
        self.assertFalse(HC.hit([rel - 5], rel, 50)); self.assertTrue(HC.hit([rel - 5 + 10], rel))      # A22 admitted a pre-release confirmation shifted by 10
        self.assertTrue(HC.hit([rel + 50], rel, 50)); self.assertFalse(HC.hit([rel + 51], rel, 50))

    def test_h1c_zero_reproduces(self):
        _, _, conf = A.folds_split(); leg = [f for f in conf if f.startswith("LEGACY|")]; al = {(f, fam): A.a17_record(f, fam)["alarms"] for f in conf for fam in A.FAMILIES}
        got = Z.h1c_window(al, {f: 0 for f in leg}); ref = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]
        for f in A.FAMILIES: self.assertTrue(A.same({k: v for k, v in ref[f].items() if k != "events"}, got[f]))


if __name__ == "__main__": unittest.main()
