#!/usr/bin/env python3
"""Unit tests for AMENDMENT_A34: per-asset placebo pools (rule 1) and the A26 label enforcement (rule 3). Synthetic arrays only."""
import sys, json, tempfile, unittest
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_a34 as A
from s6_tests import FakeEra, cand_grid


class TestPerAssetPool(unittest.TestCase):
    def test_eligible_mask(self):
        cand = cand_grid(80, lambda a, b: 0.0); u = dict(day_idx=75, era="LEGACY", S=100, gap=10, vol=0.0)
        base = L.draw_placebos(u, cand, {}, seed=3); self.assertTrue(np.array_equal(base, L.draw_placebos(u, cand, {}, seed=3, eligible=None)))      # default unchanged
        el = cand["day_idx"] >= 50; ix = L.draw_placebos(u, cand, {}, seed=3, eligible=el)
        self.assertEqual(len(ix), 20); self.assertTrue(all(cand["day_idx"][i] >= 50 for i in ix))

    def test_units_get_per_asset_and_joint_pools(self):
        E = FakeEra(n=120); E.avail["HYG"][:60] = False; E.avail["TLT"][:30] = False
        rows = [dict(era="LEGACY", day=E.days[100], kind="confirmed", S_min=100, T0_min=110, end_min=105, direction="calm_to_stressed", old_state="0", family="x", fold="LEGACY|0")]
        br = A.units_a34({"LEGACY": E}, rows, {"LEGACY|0": E.days}); self.assertEqual(len(br), 1); u = br[0]
        self.assertTrue(all(p["day_idx"] >= 60 for p in u["pl_by_asset"]["HYG"])); self.assertTrue(all(p["day_idx"] >= 30 for p in u["pl_by_asset"]["TLT"]))
        self.assertTrue(all(p["day_idx"] >= 60 for p in u["pl_joint"])); self.assertTrue(all(p["gap"] == 10 for p in u["pl_by_asset"]["GOLD"]))
        self.assertGreater(len(u["pl_by_asset"]["HYG"]), 0)


class TestLabelEnforcement(unittest.TestCase):
    def test_s6_write_once_refuses_unlabelled_evaluation_output(self):
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError): R.write_once(Path(td) / "a.json", dict(period="joint", x=1))
            with self.assertRaises(PermissionError): R.write_once(Path(td) / "b.json", dict(period="joint", a26_label=R.LABEL_EVAL, confirmatory=True))
            self.assertTrue(R.write_once(Path(td) / "c.json", dict(period="joint", a26_label=R.LABEL_EVAL, confirmatory=False)).exists())
            self.assertTrue(R.write_once(Path(td) / "d.json", dict(period="development")).exists())

    def test_s5_label_module(self):
        import s5_eval_label as EV, s5_freeze as FZ
        self.assertTrue(EV.ready()); self.assertEqual(EV.LABEL, R.LABEL_EVAL)
        run = EV.wrap_run_fn(lambda era, m, s, t: dict(h1=0.1)); r = run("RAW", None, None, None)
        self.assertEqual(r["a26_label"], EV.LABEL); self.assertIs(r["confirmatory"], False)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / f"{FZ.EVAL_PREFIX}RAW.json").write_text(json.dumps(r)); self.assertTrue(EV.verify_labelled(td))
            (Path(td) / f"{FZ.EVAL_PREFIX}LEGACY.json").write_text(json.dumps(dict(h1=0.1)))
            with self.assertRaises(PermissionError): EV.verify_labelled(td)

    def test_eval_guard_requires_label_module(self):
        import s5_eval_loader as EL, s5_eval_label as EV
        saved = EV.ready
        try:
            EV.ready = lambda: (_ for _ in ()).throw(PermissionError("label module not ready"))
            with self.assertRaises(PermissionError) as cm: EL.eval_guard("RAW", "missing_freeze.json", "x")
            self.assertIn("label", str(cm.exception))
        finally: EV.ready = saved


if __name__ == "__main__": unittest.main()
