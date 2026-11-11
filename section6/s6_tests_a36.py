#!/usr/bin/env python3
"""Unit tests for AMENDMENT_A36 (the joint evaluation driver): panel joining and partitions, segments, day-cluster intervals, H1(c) on events, detector choice
(A28 1b, A35 rule 3), Fed flag, label, FOMC date parsers and the built-first rule, fingerprint compared with the code, guarded authorisation, evaluation options
of the Section 6 analyses. Synthetic arrays and temporary files only; no market file and no evaluation-period row is read. The whole path is exercised by
s6_eval_synth.py."""
import sys, json, inspect, tempfile, unittest
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_run as R, s6_h2 as H2, s6_eval as S6E
import s5_eval513 as S513, s5_eval_loader as EL, s5_h1c_eval_times as FT


def tiny(n_sessions, m=4, t0=0):
    N = n_sessions * m; first = np.arange(0, N, m, dtype=np.int64)
    return dict(era="LEGACY", t=np.arange(N, dtype=np.int64) + t0, day=np.repeat([f"d{t0}_{i}" for i in range(n_sessions)], m), close=np.arange(N, dtype=float), first=first, end=first + m)


class TestPanel(unittest.TestCase):
    def test_concat_rebases_sessions(self):
        a, b = tiny(3), tiny(2, t0=100); d = S513.concat(a, b)
        self.assertEqual(len(d["t"]), 20); self.assertEqual(d["first"].tolist(), [0, 4, 8, 12, 16]); self.assertEqual(d["end"].tolist(), [4, 8, 12, 16, 20])
        self.assertEqual([str(d["day"][i]) for i in d["first"]], ["d0_0", "d0_1", "d0_2", "d100_0", "d100_1"]); self.assertEqual(d["close"][12:].tolist(), b["close"].tolist())

    def test_partitions_train_then_evaluation_only(self):
        saved = S513.partitions
        try:
            S513.partitions = lambda era: {"a": "TRAIN", "b": "TRAIN", "x": "EMBARGO", "c": "EVALUATION_EXPOSED", "d": "EVALUATION_EXPOSED"}
            self.assertTrue(S513.check_partitions("LEGACY", ["a", "b", "c", "d"], 2))
            with self.assertRaises(PermissionError): S513.check_partitions("LEGACY", ["a", "b", "x", "c", "d"], 2)        # an embargo session in the panel (A36 1e)
            with self.assertRaises(PermissionError): S513.check_partitions("LEGACY", ["a", "b", "c"], 2)                  # an evaluation session missing
            with self.assertRaises(PermissionError): S513.check_partitions("LEGACY", ["a", "c", "d"], 1)                  # a TRAIN session missing
        finally: S513.partitions = saved

    def test_segments(self):
        import s5_era_threshold as ET
        full, cal = S513.segments(300, 420); fit, emb, c = ET.era_split(300)
        self.assertEqual((full["train"][0], full["train"][-1], full["test"][0], full["test"][-1], len(full["val"])), (0, 299, 300, 419, 0))
        self.assertTrue(np.array_equal(cal["train"], fit)); self.assertTrue(np.array_equal(cal["val"], c)); self.assertEqual(len(cal["test"]), 0); self.assertEqual((len(c), len(emb)), (58, 5))
        self.assertLess(cal["val"].max(), 300)                                                                           # the calibration never reaches an evaluation session

    def test_fit_needs_the_driver_and_backend_has_no_selection(self):
        S513._AUTH.clear()
        with self.assertRaises(PermissionError): S513.fit_fn("LEGACY", {}, {})
        EB = S513._backend_class(); b = EB("LEGACY", dict(era="LEGACY"), dict(train=np.arange(3), val=np.array([], int), test=np.arange(3, 5)))
        for f in (lambda: b.objective("LEGACY|EVAL", "hsmm"), lambda: b.score("LEGACY|EVAL", "hsmm", {}), lambda: b.era_thresholds("LEGACY", "hsmm", {})):
            with self.assertRaises(PermissionError): f()
        with self.assertRaises(ValueError): EB("RAW", dict(era="LEGACY"), {})


class TestIntervals(unittest.TestCase):
    def test_mean_diff(self):
        rng = np.random.default_rng(0); cl = np.repeat(np.arange(60), 20); y0 = rng.normal(1.0, 0.3, 1200); y1 = y0 + 0.2 + rng.normal(0, 0.05, 1200)
        r = S513.ci_mean_diff(y1, y0, cl); self.assertAlmostEqual(r["effect"], float(y1.mean() - y0.mean())); self.assertTrue(r["ci95"][0] < r["effect"] < r["ci95"][1]); self.assertGreater(r["ci95"][0], 0.15)
        self.assertEqual((r["n"], r["n_clusters"]), (1200, 60)); self.assertNotIn("p", r); self.assertIsNone(S513.ci_mean_diff([], [], [])["effect"])
        z = S513.ci_mean_diff(y0, y0, cl); self.assertEqual(z["effect"], 0.0); self.assertEqual(z["ci95"], [0.0, 0.0])

    def test_pauc_diff(self):
        rng = np.random.default_rng(1); G = 20; dn = np.repeat(np.arange(12), 10); db = np.repeat(np.arange(12), 15)
        cnt = np.cumsum(np.full((120, G), 0.05), 1)[:, ::-1].copy(); hb = (rng.random((180, G)) < np.linspace(0.6, 0.1, G)).astype(float); hf = np.maximum(hb, (rng.random((180, G)) < 0.3).astype(float))
        same = S513.ci_pauc_diff((cnt, dn, hb, db), (cnt, dn, hb, db)); self.assertEqual(same["effect"], 0.0); self.assertEqual(same["ci95"], [0.0, 0.0])
        up = S513.ci_pauc_diff((cnt, dn, hf, db), (cnt, dn, hb, db)); self.assertGreater(up["effect"], 0); self.assertGreater(up["ci95"][0], 0); self.assertTrue(up["ci95"][0] <= up["effect"] <= up["ci95"][1])
        self.assertEqual((up["n_null"], up["n_break"], up["n_stable_days_in_splices"]), (120, 180, 12)); self.assertNotIn("p", up)

    def test_h1c_events_and_no_p(self):
        mins = {"e1": 270, "e2": 270, "e3": 270, "short": 270, "absent": 270}
        af = {"e1": [[250, 280]], "e2": [[100, 120]], "e3": [[300, 331]], "short": [[270, 280]], "n1": [[260, 290]], "n2": []}; ab = {"e1": [], "e2": [[265, 271]], "e3": [], "short": [], "n1": [], "n2": []}
        r = S513.h1c(af, ab, mins, full_days={"e1", "e2", "e3", "n1", "n2"})
        self.assertEqual([e["date"] for e in r["events"]], ["e1", "e2", "e3"])                       # a short session and a day outside the panel are not events
        self.assertEqual([e["feature_hit"] for e in r["events"]], [True, False, False])              # 331 > 270 + 60: outside the window
        self.assertEqual([e["baseline_hit"] for e in r["events"]], [False, True, False]); self.assertAlmostEqual(r["effect"], 0.0)
        self.assertEqual((r["feature_only"], r["baseline_only"], r["n_events"]), (1, 1, 3)); self.assertEqual(r["feature"]["reference_alarm_rate"], 0.5)
        self.assertNotIn("p_two_sided", json.dumps(r)); self.assertIsNone(S513.h1c({"n1": []}, {"n1": []}, mins, {"n1"})["effect"])

    def test_fomc_list_needs_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "f.json"; p.write_text(json.dumps(dict(meetings={"2019-01-30": dict(status="time", minute_after_0930=270), "2019-03-20": dict(status="excluded")})))
            with self.assertRaises(PermissionError): S513.fomc_minutes(p)
            import s5_guard as G; G.write_side(p); self.assertEqual(S513.fomc_minutes(p), {"2019-01-30": 270})


class TestDetectors(unittest.TestCase):
    def test_h34_primary(self):
        ok = lambda d: (True, True); gfail = lambda d: ((d != "gaussian_hmm"), True); hfail = lambda d: ((d != "hsmm"), True); norep = lambda d: (True, d != "gaussian_hmm")
        self.assertEqual(S6E.h34_primary(dict(h2_primary_detector="gaussian_hmm"), ok)[0], "gaussian_hmm")                # A35 3c
        d, why = S6E.h34_primary(dict(h2_primary_detector="gaussian_hmm"), gfail); self.assertEqual(d, "hsmm"); self.assertIn("A35 3a", why)
        self.assertEqual(S6E.h34_primary(dict(h2_primary_detector="student_t_hmm"), gfail)[0], "student_t_hmm")           # A35 3a concerns the Gaussian HMM only
        self.assertEqual(S6E.h34_primary(dict(h2_primary_detector="hsmm"), gfail)[0], "hsmm")
        with self.assertRaisesRegex(PermissionError, "A35 3d"): S6E.h34_primary(dict(h2_primary_detector="gaussian_hmm"), hfail)
        with self.assertRaisesRegex(PermissionError, "A35 2d"): S6E.h34_primary(dict(h2_primary_detector="hsmm"), norep)
        fb = dict(h2_primary_detector=None, median_validation_qlike=dict(gaussian_hmm=1.2, student_t_hmm=1.0, hsmm=1.0, bocpd=0.1))
        d, why = S6E.h34_primary(fb, ok); self.assertEqual(d, "student_t_hmm"); self.assertIn("fallback", why)            # tie to the simpler model; BOCPD never
        with self.assertRaises(PermissionError): S6E.h34_primary(dict(h2_primary_detector=None), ok)

    def test_a35_status_needs_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "a35_null_control_hsmm.json"; p.write_text(json.dumps(dict(passed=True, reproduces_development_run=True)))
            with self.assertRaises(PermissionError): S6E.a35_status("hsmm", Path(td))
            import s5_guard as G; G.write_side(p); self.assertEqual(S6E.a35_status("hsmm", Path(td)), (True, True))

    def test_fed_flag_and_label(self):
        u = [dict(day="2019-01-30", S=270), dict(day="2019-01-30", S=331), dict(day="2019-01-30", S=269), dict(day="2019-02-01", S=280)]
        self.assertEqual([x["fed"] for x in S6E.fed_fn_of({"2019-01-30": 270})(u)], [True, False, False, False])
        r = S6E.label(dict(a=1, period="development")); self.assertEqual((r["period"], r["a26_label"], r["confirmatory"]), ("evaluation", R.LABEL_EVAL, False))
        with tempfile.TemporaryDirectory() as td: self.assertTrue(R.write_once(Path(td) / "x.json", r).exists())


class TestFomcTimes(unittest.TestCase):
    HIST = "x January 29-30 Meeting - 2019 Statement: PDF | HTML y March 19-20 Meeting - 2019 Statement z October 4 Conference Call - 2019 Statement w April/May 30-1 Meeting - 2019 Minutes only"
    CAL = "2026 FOMC Meetings January 27-28 Statement: x March 17-18* Statement: y 2025 FOMC Meetings January 28-29 Statement: a Apr/May 30-1 Statement b 2024 FOMC Meetings December 17-18 Statement"

    def test_date_parsers(self):
        self.assertEqual(FT.parse_hist(self.HIST, 2019), ["2019-01-30", "2019-03-20"])                 # conference calls and meetings without a statement are left out
        self.assertEqual(FT.parse_cal(self.CAL, 2026), ["2026-01-28", "2026-03-18"]); self.assertEqual(FT.parse_cal(self.CAL, 2025), ["2025-01-29", "2025-05-01"]); self.assertEqual(FT.parse_cal(self.CAL, 2023), [])
        import s5_d6 as D6                                                                             # the development parsers give the same dates on the same text
        self.assertEqual(FT.date_of("April/May 30-1", 2019), D6.date_of("April/May 30-1", 2019)); self.assertEqual(FT.date_of("Jan 27-28", 2026), "2026-01-28")

    def test_periods(self):
        self.assertTrue(FT.in_periods("2019-01-30")); self.assertTrue(FT.in_periods("2022-01-26")); self.assertFalse(FT.in_periods("2022-03-16")); self.assertFalse(FT.in_periods("2024-12-18"))
        self.assertTrue(FT.in_periods("2026-09-16")); self.assertFalse(FT.in_periods("2026-10-28")); self.assertEqual(FT.PERIODS, EL.EVAL)

    def test_built_before_any_evaluation_read(self):
        saved = FT.ACCESS_LOG
        with tempfile.TemporaryDirectory() as td:
            try:
                FT.ACCESS_LOG = Path(td) / "log.txt"; FT.refuse_after_evaluation_read(); FT.ACCESS_LOG.write_text("2026 REQUEST era=RAW\n2026 REFUSED era=RAW: x\n"); FT.refuse_after_evaluation_read()
                FT.ACCESS_LOG.write_text("2026 REQUEST era=RAW\n2026 ALLOWED era=RAW\n")
                with self.assertRaisesRegex(PermissionError, "A36 3c"): FT.refuse_after_evaluation_read()
            finally: FT.ACCESS_LOG = saved


class TestGuards(unittest.TestCase):
    def test_fingerprint_compared_with_code(self):
        import s6_fingerprint as FPM, s5_guard as G
        saved = EL.FINGERPRINT
        with tempfile.TemporaryDirectory() as td:
            try:
                EL.FINGERPRINT = Path(td) / "fp.json"
                with self.assertRaisesRegex(PermissionError, "A28 rule 6e"): EL.fingerprint_check()
                cur = FPM.current(); EL.FINGERPRINT.write_text(json.dumps(cur)); G.write_side(EL.FINGERPRINT); self.assertTrue(EL.fingerprint_check())
                for k in ("section5/s5_eval513.py", "section5/s5_eval_label.py", "section5/s5_h1c_eval_times.py", "section6/s6_eval.py", "section6/s6_h2.py"): self.assertIn(k, cur["files"])   # A36 7b
                old = dict(cur, files=dict(cur["files"], **{"section6/s6_h2.py": "0" * 64})); EL.FINGERPRINT.write_text(json.dumps(old)); G.write_side(EL.FINGERPRINT)
                with self.assertRaisesRegex(PermissionError, "A36 rule 7c.*s6_h2.py"): EL.fingerprint_check()        # a file changed after the fingerprint (re-audit L9)
                EL.FINGERPRINT.write_text(json.dumps(dict(cur, code_version="x"))); G.write_side(EL.FINGERPRINT)
                with self.assertRaisesRegex(PermissionError, "code version"): EL.fingerprint_check()
            finally: EL.FINGERPRINT = saved

    def test_authorise_is_guarded_and_logged(self):
        saved = (EL.ACCESS_LOG, list(EL.EVAL_READS))
        with tempfile.TemporaryDirectory() as td:
            try:
                EL.ACCESS_LOG = Path(td) / "log.txt"
                with self.assertRaises(Exception): EL.authorise("RAW", Path(td) / "no_freeze.json", "x", section6=True, what="test")
                t = EL.ACCESS_LOG.read_text(); self.assertIn("REQUEST era=RAW what='test'", t); self.assertIn("REFUSED", t); self.assertNotIn("ALLOWED", t); self.assertEqual(EL.EVAL_READS, saved[1])
            finally: EL.ACCESS_LOG = saved[0]; EL.EVAL_READS[:] = saved[1]
        self.assertEqual(list(inspect.signature(EL.authorise).parameters), ["era", "freeze_path", "confirm_token", "section6", "what"])
        self.assertEqual(list(inspect.signature(EL.load_eval).parameters), ["era", "columns", "freeze_path", "confirm_token", "section6"])

    def test_driver_refuses_without_freeze_and_lists(self):
        import s5_amendment_manifest as AM
        self.assertIn("A36", S6E.AMENDMENTS); self.assertIn("A36", AM.AMENDMENTS); self.assertEqual(S6E.N_HIST, 60)
        with self.assertRaises(Exception): S6E.guards(Path("no_such_freeze.json"))


class TestEvaluationOptions(unittest.TestCase):
    def test_signatures_and_subsets(self):
        p = inspect.signature(R.analyse).parameters; self.assertEqual((p["evaluation"].default, p["fed_fn"].default), (False, None))          # the development run is unchanged by default
        self.assertEqual(inspect.signature(H2.analyse).parameters["per_era"].default, False)
        u = [dict(era="LEGACY"), dict(era="RAW")]; self.assertEqual([R.SUBSETS["era_LEGACY"](x) for x in u], [True, False]); self.assertEqual([R.SUBSETS["era_RAW"](x) for x in u], [False, True])
        res = dict(secondary={}, by_era=dict(LEGACY=dict(H3_TLT=dict(p=0.2)), RAW=dict(H3_TLT=dict(p=0.4))))
        self.assertEqual(sorted(k for k, _ in R.flatten_secondary(res)), ["by_era.LEGACY.H3_TLT", "by_era.RAW.H3_TLT"])                          # each era alone joins the BH family (A36 1d)


if __name__ == "__main__": unittest.main()
