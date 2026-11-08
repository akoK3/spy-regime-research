#!/usr/bin/env python3
"""A24 tests: clock offset moves hits at the window edges; c = 0 reproduces the MR2 A17-style H1(c)."""
import sys, json, unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_h1c as HC, s5_a22 as A, s5_a24_clock as K


class TestClock(unittest.TestCase):
    def test_edges(self):
        rel = 285; pre, end = [[rel - 3, rel - 1]], [[rel + 50, rel + 60]]
        self.assertFalse(HC.hit([a[1] for a in pre], rel)); self.assertTrue(HC.hit([a[1] + 1 for a in pre], rel))
        self.assertTrue(HC.hit([a[1] for a in end], rel)); self.assertFalse(HC.hit([a[1] + 1 for a in end], rel)); self.assertTrue(HC.hit([a[1] - 1 for a in end], rel))

    def test_zero_reproduces(self):
        _, _, conf = A.folds_split(); al = K.alarms_at("0.20", conf); got = A.h1c(al, {f: 0 for f in conf if f.startswith("LEGACY|")})
        ref = json.loads((A.A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]
        for f in A.FAMILIES: self.assertTrue(A.same({k: v for k, v in ref[f].items() if k != "events"}, got[f]))


if __name__ == "__main__": unittest.main()
