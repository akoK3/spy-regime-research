#!/usr/bin/env python3
"""Unit tests for A11: era-level threshold split, HSMM grid, release-time parsing and H1(c) windows. No market data loaded."""
import sys, json, time, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_era_threshold as ET, s5_backend as BK, s5_h1c as H, s5_h1c_times as T, s5_contamination as C

HERE = Path(__file__).resolve().parent


class TestEraThreshold(unittest.TestCase):
    def test_split_58_calibration_5_embargo_rest_fit(self):
        fit, emb, cal = ET.era_split(1000); self.assertEqual((len(fit), len(emb), len(cal)), (937, 5, 58)); self.assertEqual(fit[-1] + 1, emb[0]); self.assertEqual(emb[-1] + 1, cal[0]); self.assertEqual(cal[-1], 999)
        self.assertEqual(len(np.intersect1d(fit, cal)), 0); self.assertEqual(len(np.concatenate([fit, emb, cal])), 1000)
        with self.assertRaises(ValueError): ET.era_split(150)

    def test_era_backend_segments_and_guards(self):
        b = ET.EraBackend("RAW"); self.assertIsNone(b._ctx); seg = b._segments({"first": np.arange(705)}); self.assertEqual((len(seg["train"]), len(seg["embargo"]), len(seg["val"]), len(seg["test"])), (642, 5, 58, 0))
        self.assertLess(seg["train"].max() + 5, seg["val"].min()); self.assertEqual(b.folds(), ["RAW|ERA"])
        with self.assertRaises(ValueError): ET.EraBackend("EVAL")
        with self.assertRaises(PermissionError): b.candidates("RAW|3")                      # inherits the fold-id guard

    def test_fold_backend_still_guarded_and_hsmm_grid_is_k_2_3(self):
        self.assertEqual(BK.HSMM_GRID, [dict(K=2), dict(K=3)]); self.assertEqual(BK.HMM_GRID, [dict(K=2), dict(K=3), dict(K=4)])
        b = BK.DataBackend("RAW", 3); self.assertEqual(b.param_grid("hsmm"), [dict(K=2), dict(K=3)]); self.assertEqual(b.param_grid("student_t_hmm"), BK.HMM_GRID)
        with self.assertRaises(PermissionError): BK.DataBackend("LEGACY", 5)


class TestReleaseTimes(unittest.TestCase):
    def test_parse_formats(self):
        p = lambda s: T.parse_one("<p>" + s + "</p>" + "x" * 300)
        a = p("For release at 2:00 p.m. EST"); self.assertEqual((a["status"], a["time_et"], a["minute_after_0930"], a["tz"]), ("time", "14:00", 270, "EST"))
        b = p("For release at 2:15&nbsp;p.m. EDT"); self.assertEqual((b["time_et"], b["minute_after_0930"]), ("14:15", 285))
        self.assertEqual(p("For release at 10:00 a.m. EST")["time_et"], "10:00"); self.assertEqual(p("For release at 12:30 p.m. EDT")["time_et"], "12:30")
        self.assertEqual(p("For immediate release")["status"], "unavailable"); self.assertIn("immediate", p("For immediate release")["reason"])
        self.assertEqual(p("nothing here")["status"], "unavailable"); self.assertEqual(T.parse_one("HTTP 404")["status"], "unavailable")

    def test_statement_page_detection(self):
        good = "<p>Release Date: x The Federal Open Market Committee decided today to keep the target range</p>" + "x " * 100
        bad = "<p>Federal Reserve announces results of auction ... Term Auction Facility ...</p>" + "x " * 100
        self.assertTrue(T.is_statement(good)); self.assertFalse(T.is_statement(bad)); self.assertFalse(T.is_statement("HTTP 404"))

    def test_hit_window_is_sixty_minutes_from_actual_release(self):
        self.assertTrue(H.hit([285], event=285)); self.assertTrue(H.hit([345], event=285)); self.assertFalse(H.hit([346], event=285)); self.assertFalse(H.hit([284.9], event=285)); self.assertTrue(H.hit([330], event=270))
        self.assertEqual(H.release_minute(dict(status="time", minute_after_0930=285)), 285); self.assertIsNone(H.release_minute(dict(status="unavailable"))); self.assertIsNone(H.release_minute(None))

    def test_stored_release_times_are_complete_and_hashed(self):
        j = json.loads((HERE / "results" / "h1c_release_times.json").read_text()); m0 = j["meetings"]; self.assertEqual(j["n_meetings"], len(m0)); self.assertEqual(j["counts"]["time"] + j["counts"]["unavailable"], len(m0)); m = m0
        for d, v in m.items():
            if v["status"] == "time": self.assertTrue(v["url"].startswith("https://www.federalreserve.gov/")); self.assertEqual(len(v["page_sha256"]), 64); self.assertIsInstance(v["minute_after_0930"], int)
            else: self.assertTrue(v["reason"])
        cl = json.loads((HERE / "results" / "contamination_list.json").read_text()); ev = {x for v in cl["h1c_eligible_events_per_fold"].values() for x in v}
        sch = json.loads((HERE / "results" / "h1c_schedule_times.json").read_text())["meetings"]; m = sch      # A12: events come from the schedule file
        self.assertTrue(all(m[x]["status"] == "time" for x in ev)); self.assertEqual(set(cl["h1c_event_release_minute_after_0930"]), ev)
        self.assertEqual(len(ev), cl["n_h1c_events"]); self.assertTrue(all(m[x]["status"] != "time" for x in cl["h1c_excluded_release_time_unavailable"]))


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a11.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
