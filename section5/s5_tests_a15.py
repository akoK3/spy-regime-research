#!/usr/bin/env python3
"""A15 unit tests (cold audit 2). No model is fitted and no detector run on market data; backends are stubs or lazy (no data loaded)."""
import sys, json, time, tempfile, unittest, re, hashlib, shutil
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_guard as G, s5_run as RUN, s5_select as SEL, s5_stats as ST, s5_h1 as H, s5_backend as BK, s5_contamination as C, s5_dry_run as DR

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
PROTOCOL_SHA = hashlib.sha256((ROOT / "SECTION5_PROTOCOL.md").read_bytes()).hexdigest()


class GridBackend(DR.SyntheticBackend):
    """Feature model best at K=4, return-only baseline best at K=2; records every objective call."""
    def __init__(self, *a, **k): super().__init__(*a, **k); self.calls = []
    def objective(self, fold, family):
        def f(subset, params, starts):
            self.calls.append((tuple(subset), dict(params), starts)); K = params.get("K", 3)
            return dict(qlike=100.0 - 8.0 * ("f1" in subset) + (0.1 * abs(K - 4) if subset else 0.1 * abs(K - 2)), delay=0.0)
        return f


class TestRule1BaselineTuning(unittest.TestCase):
    def test_baseline_tuned_on_identical_grid_and_starts(self):
        b = GridBackend(n_legacy=2, n_raw=0); s = RUN.select_fold(b, "LEGACY|0", "gaussian_hmm")
        self.assertEqual(s["features"], ["f1"]); self.assertEqual(s["params"], dict(K=4)); self.assertEqual(s["base_params"], dict(K=2))
        tune = lambda sub: sorted((c[1]["K"], c[2]) for c in b.calls if c[0] == sub and c[2] == 3)
        self.assertEqual(tune(("f1",)), [(2, 3), (3, 3), (4, 3)]); self.assertEqual(tune(()), tune(("f1",)))          # same grid, 3 starts each

    def test_score_fits_the_baseline_with_its_own_params(self):
        b = object.__new__(BK.DataBackend); b.id = "RAW|3"; b.min_days = 8; fits = []
        b._splices = lambda: dict(n_stable=0, specs=[], rows=[], why=None)
        b.fit = lambda fam, sub, params, starts: fits.append((tuple(sub), dict(params), starts)) or object()
        b.qlike_on = lambda fam, m, sub, split: (np.ones(3), np.arange(3))
        b.score("RAW|3", "gaussian_hmm", dict(features=["x"], params=dict(K=4), base_params=dict(K=2), val_qlike=1.0))
        self.assertIn(((), dict(K=2), 3), fits); self.assertIn((("x",), dict(K=4), 3), fits)

    def test_final_setup_carries_baseline_mode(self):
        st = [dict(features=["a"], params=dict(K=3), base_params=dict(K=k)) for k in (2, 2, 4, 3)]
        self.assertEqual(SEL.final_setup(st)["base_params"], dict(K=2))


class TestRule2Contamination(unittest.TestCase):
    def test_regenerated_list_excludes_legacy_23_24(self):
        j = json.loads((HERE / "results" / "contamination_list.json").read_text())
        self.assertEqual(sorted((e["era"], e["fold"]) for e in j["folds"] if e["excluded"]), [("LEGACY", f) for f in (23, 24, 27, 28, 29)] + [("RAW", f) for f in (1, 2, 3)])
        self.assertEqual(34 - j["n_excluded"], 26); self.assertEqual(j["n_h1c_events"], 98)

    def test_audit1_legacy25_run_is_the_cause(self):
        days = json.loads((HERE / "results" / "session_days.json").read_text()); ft = C.folds_table()
        ex = lambda reg: sorted((e["era"], e["fold"]) for e in C.exclusions(days, C.touched(days, [], reg, ft), ft) if e["excluded"])
        without = {k: v for k, v in C.REGISTRY.items() if k != "cold_audit_1/x5_robust.py"}
        self.assertNotIn(("LEGACY", 24), ex(without)); self.assertIn(("LEGACY", 24), ex(C.REGISTRY)); self.assertIn(("LEGACY", 23), ex(C.REGISTRY))

    def test_label_free_does_not_touch(self):
        days = json.loads((HERE / "results" / "session_days.json").read_text()); ft = C.folds_table()
        t = C.touched(days, [], {"x1_folds.py": "LABEL_FREE", "main": "MAIN_RUN"}, ft); self.assertEqual(t, {"LEGACY": {}, "RAW": {}})


class TestRule3Registry(unittest.TestCase):
    def test_pattern_has_no_control_characters_and_matches(self):
        self.assertTrue(all(ord(c) >= 32 for c in C.DATA_LOAD.pattern))
        for s in ("d = L.load_era(e, c)", "seg = L.fold_segments(d, e, f)", "b = BK.DataBackend(e, f)", "ET.EraBackend(e)", "MainBackend(h)"): self.assertTrue(C.DATA_LOAD.search(s), s)
        self.assertFalse(re.search("\x08fold_segments\\(|\x08load_era\\(", "d = L.load_era(e, c)"))          # the pattern before A15 could not match

    def test_check_passes_on_section5_and_fails_on_an_unregistered_script(self):
        self.assertTrue(C.check_registry(HERE))
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "s5_new_diag.py").write_text("import s5_lib as L\nd = L.load_era('RAW', [])\n"); (Path(td) / "s5_other.py").write_text("b = BK.DataBackend('RAW', 3)\n")
            (Path(td) / "write_report.py").write_text("L.load_era('RAW', [])\n")                                              # writer scripts are exempt
            with self.assertRaises(AssertionError) as cm: C.check_registry(td)
            self.assertIn("s5_new_diag.py", str(cm.exception)); self.assertIn("s5_other.py", str(cm.exception)); self.assertNotIn("write_report.py", str(cm.exception))

    def test_previously_missing_scripts_registered(self):
        for f in ("s5_a8_gate_seeds.py", "s5_a8_loo.py", "s5_backend.py", "s5_machinery_run.py", "s5_a14_diag.py", "s5_main.py"): self.assertIn(f, C.REGISTRY)


class TestRule4CheckpointVersion(unittest.TestCase):
    def test_closure_covers_result_affecting_modules(self):
        m = set(RUN.result_modules())
        for f in ("s5_models.py", "s5_events.py", "s5_sweep.py", "s5_backend.py", "s5_lib.py", "s5_fast.py", "s5_d2.py", "s5_d2_stable.py", "s5_a7.py", "s5_a6.py", "s5_eval.py",
                  "s5_main.py", "s5_era_threshold.py", "s5_select.py", "s5_stats.py", "s5_h1.py", "s5_freeze.py", "s5_run.py"): self.assertIn("section5/" + f, m)
        self.assertIn("step3_all_in_one.py", m)

    def test_model_change_changes_version(self):
        with tempfile.TemporaryDirectory() as td:
            s = Path(td) / "section5"; s.mkdir(); (s / "s5_run.py").write_text("def f():\n    import s5_models\n"); (s / "s5_models.py").write_text("x = 1\n")
            v1 = RUN.code_version(base=s); (s / "s5_models.py").write_text("x = 2\n"); self.assertNotEqual(v1, RUN.code_version(base=s))         # the A12 -> A13 case

    def test_old_versions_invalidated_and_key_has_backend_kind(self):
        old = hashlib.sha256()
        for f in ["s5_select.py", "s5_stats.py", "s5_h1.py", "s5_freeze.py", "s5_run.py", "s5_a6.py", "s5_eval.py"]: old.update(f.encode()); old.update(hashlib.sha256((HERE / f).read_bytes()).digest())
        self.assertNotEqual(old.hexdigest()[:16], RUN.code_version())
        class Other(DR.SyntheticBackend): kind = "other"
        with tempfile.TemporaryDirectory() as td:
            b = DR.SyntheticBackend(n_legacy=3, n_raw=0)
            RUN.run_all(b, Path(td) / "r", nboot=100); s2 = RUN.run_all(Other(n_legacy=3, n_raw=0), Path(td) / "r", nboot=100)
            self.assertEqual(s2["checkpoint"]["hits"], 0)


class TestRule5MainRunPath(unittest.TestCase):
    def test_clean_fold_needs_frozen_protocol_hash(self):
        allowed = {"LEGACY|0", "RAW|3"}
        with self.assertRaises(PermissionError): BK.DataBackend("LEGACY", 0, allowed=allowed)
        with self.assertRaises(PermissionError): BK.DataBackend("LEGACY", 0, allowed=allowed, protocol_sha256="0" * 64)
        b = BK.DataBackend("LEGACY", 0, allowed=allowed, protocol_sha256=PROTOCOL_SHA); self.assertIsNone(b._ctx)          # lazy: no data read
        BK.DataBackend("RAW", 3, allowed=allowed)                                                                             # contaminated: machinery, no hash needed
        with self.assertRaises(PermissionError): BK.DataBackend("LEGACY", 1, allowed=allowed, protocol_sha256=PROTOCOL_SHA)   # not allowed

    def test_protocol_must_say_frozen_and_match_sidecar(self):
        import s5_guard as G; orig = G.PROTOCOL
        with tempfile.TemporaryDirectory() as td:
            try:
                p = Path(td) / "P.md"; G.PROTOCOL = p; p.write_text("# draft\n"); h = BK.sha(p); p.with_suffix(".sha256").write_text(f"{h}  P.md\n")
                with self.assertRaises(PermissionError): BK.verify_frozen_protocol(h)
                p.write_text("**Status: FROZEN**\n"); h2 = BK.sha(p)
                with self.assertRaises(PermissionError): BK.verify_frozen_protocol(h2)                                            # sidecar stale
                p.with_suffix(".sha256").write_text(f"{h2}  P.md\n"); self.assertEqual(BK.verify_frozen_protocol(h2), h2)
            finally: G.PROTOCOL = orig

    def test_main_backend_folds_and_era_guard(self):
        with self.assertRaises(PermissionError): __import__("s5_main").MainBackend("0" * 64)
        import s5_main as MB
        b = MB.MainBackend(PROTOCOL_SHA); self.assertEqual(b.folds(), [f"LEGACY|{i}" for i in range(30)] + [f"RAW|{i}" for i in range(4)])
        self.assertEqual(b.param_grid("hsmm"), [dict(K=2), dict(K=3)])
        with tempfile.TemporaryDirectory() as td:
            with self.assertRaises(PermissionError): b.era_thresholds("RAW", "gaussian_hmm", dict(features=[], params=dict(K=3)), Path(td) / "run_complete.json")     # no record (A16)
        with self.assertRaises(PermissionError): BK.DataBackend("RAW", 3).era_thresholds("RAW", "gaussian_hmm", {}, None)

    def test_run_all_loads_contamination_and_freeze_needs_complete_run(self):
        import inspect; self.assertNotIn("excluded", inspect.signature(RUN.run_all).parameters); self.assertNotIn("contamination", inspect.signature(RUN.run_all).parameters)
        b = DR.SyntheticBackend(n_legacy=4, n_raw=4)
        with tempfile.TemporaryDirectory() as td:
            s = RUN.run_all(b, Path(td) / "r", nboot=100); canon = Path(RUN.HERE) / "results" / "contamination_list.json"
            self.assertEqual(s["excluded"], sorted(G.excluded_folds()[0])); self.assertIn("RAW|1", s["excluded"]); self.assertEqual(s["contamination_sha256"], hashlib.sha256(canon.read_bytes()).hexdigest())
            (Path(td) / "fz").mkdir(); p, doc = RUN.freeze_step(b, s, Path(td) / "fz", ["A15"]); self.assertEqual(doc["thresholds"]["LEGACY"]["gaussian_hmm"]["note"], "synthetic era-level")


class TestRule6(unittest.TestCase):
    def test_holm_missing_p_counts_as_one(self):
        r = ST.holm(dict(g=0.02, t=0.024, h=float("nan"))); self.assertFalse(r["g"]["reject"] or r["t"]["reject"] or r["h"]["reject"])
        self.assertAlmostEqual(r["g"]["p_adj"], 0.06); self.assertEqual(r["h"]["p_used"], 1.0)
        self.assertEqual({k: v["reject"] for k, v in r.items()}, {k: v["reject"] for k, v in ST.holm(dict(g=0.02, t=0.024, h=1.0)).items()})

    def test_h1a_failure_is_recorded_not_zero(self):
        r = H.h1a_fold_effect([], [], 12); self.assertIsNone(r["effect"]); self.assertIsNone(r["skipped"]); self.assertTrue(r["failed"])
        r = H.h1a_fold_effect([(0.1, 0.5)], [(0.1, 0.4)], 12, failed="skipped: break pair"); self.assertIsNone(r["effect"]); self.assertEqual(r["failed"], "skipped: break pair")
        self.assertIsNone(H.h1a_fold_effect([], [], 5)["failed"])                                                                 # few stable days: a skip
        b = object.__new__(BK.DataBackend); b.id = "RAW|3"; b.min_days = 8
        b._splices = lambda: dict(n_stable=12, specs=[], rows=[], why="skipped: break pair"); b.fit = lambda *a: object(); b.qlike_on = lambda *a: (np.ones(3), np.arange(3))
        s = b.score("RAW|3", "hsmm", dict(features=[], params=dict(K=2), base_params=dict(K=2), val_qlike=1.0)); self.assertEqual(s["h1a_failed"], "skipped: break pair")
        fr = H.family_result([0.1, None, 0.2], [0.1, 0.1, 0.1], ["A|0", "A|1", "A|2"], nboot=100, failed_a=[None, "x", None]); self.assertEqual(fr["confirmatory"]["H1a_failed_folds"], ["A|1"])
        self.assertEqual(fr["confirmatory"]["H1a"]["n_folds"], 2)

    def test_freeze_hashes_cover_all_amendments_and_data(self):
        h = BK.freeze_input_hashes(); t = (ROOT / "SECTION5_PROTOCOL.md").read_text(encoding="utf-8")
        for a in set(re.findall(r"`(AMENDMENT_A[0-9_]+\.md)`", t)): self.assertIn(a, h)
        self.assertGreaterEqual(len([k for k in h if k.startswith("AMENDMENT_")]), 15)
        for k in ("section431_step3_all_in_one_results/a4_sec4_3_9_frozen_matrix_v2.csv", "split_manifest", "section5/results/contamination_list.json"): self.assertIn(k, h)
        self.assertEqual(len([k for k in h if k.startswith(("LEGACY_", "RAW_"))]), 4)


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a15.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
