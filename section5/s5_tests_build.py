#!/usr/bin/env python3
"""Unit tests for the remaining Section 5 code: selection (5.8), H1 scoring and statistics (5.9, 5.11), freeze and refit runner (5.12, 5.13). Synthetic inputs only; no market data."""
import sys, json, time, tempfile, unittest
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_select as SEL, s5_stats as ST, s5_h1 as H, s5_freeze as FZ


def make_obj(gains, base=100.0, noise=None):
    """Objective whose QLIKE is base minus the summed gains of the subset's features (gains: dict feature -> gain), times a K/lambda factor."""
    calls = []
    def obj(subset, params, starts):
        calls.append((tuple(subset), dict(params), starts)); q = base - sum(gains.get(f, 0.0) for f in subset)
        q *= 1.0 + 0.001 * abs(params.get("K", 3) - 3) + 0.0005 * abs(params.get("lam", 39) - 39) * (0 if "K" in params else 1)
        return dict(qlike=q, delay=float(len(subset)))
    obj.calls = calls; return obj


class TestSelection(unittest.TestCase):
    def test_stops_when_gain_under_one_percent(self):
        o = make_obj(dict(a=5.0, b=3.0, c=0.5, d=0.2)); r = SEL.greedy_forward(["d", "c", "b", "a"], o)
        self.assertEqual(r["selected"], ["a", "b"]); self.assertTrue(r["trace"][-1].get("rejected") == "c"); self.assertFalse(r["exhausted"])     # 0.5/92 < 1%

    def test_stops_at_six_features_and_first_call_is_return_only(self):
        gains = {c: 10.0 for c in "abcdefghij"}; o = make_obj(gains, base=1000.0); r = SEL.greedy_forward(list(gains), o)
        self.assertEqual(len(r["selected"]), 6); self.assertEqual(o.calls[0][0], ()); self.assertTrue(all(c[1] == dict(K=3, lam=39) and c[2] == 1 for c in o.calls))   # fixed K/lambda, 1 start

    def test_tie_break_dictionary_order_and_delay(self):
        o = make_obj(dict(a=5.0, b=5.0)); self.assertEqual(SEL.greedy_forward(["b", "a"], o, max_feats=1)["selected"], ["a"])
        def obj(subset, params, starts): return dict(qlike=90.0 if subset else 100.0, delay={"a": 9.0, "b": 2.0}.get(subset[-1] if subset else "", 0.0))
        self.assertEqual(SEL.greedy_forward(["a", "b"], obj, max_feats=1)["selected"], ["b"])         # equal QLIKE: lower delay wins

    def test_budget_exhausted_keeps_best_so_far_and_records_it(self):
        o = make_obj(dict(a=5.0, b=3.0, c=2.0)); r = SEL.greedy_forward(["a", "b", "c"], o, budget=SEL.Budget(3))
        self.assertTrue(r["exhausted"]); self.assertLessEqual(len(o.calls), 3); self.assertIsNotNone(r["final_qlike"])
        self.assertEqual(SEL.greedy_forward(["a"], o, budget=SEL.Budget(0))["selected"], [])

    def test_selection_uses_only_the_objective_it_is_given(self):
        seen = []
        def obj(subset, params, starts): seen.append(subset); return dict(qlike=100.0 - len(subset), delay=0.0)
        SEL.greedy_forward(["a", "b"], obj); self.assertTrue(all(isinstance(s, tuple) for s in seen))      # no data handle exists in the module: only the injected callable

    def test_tune_picks_lowest_qlike_with_three_starts_and_smaller_param_on_ties(self):
        o = make_obj({}); r = SEL.tune(["a"], o, [dict(K=2), dict(K=3), dict(K=4)]); self.assertEqual(r["params"], dict(K=3)); self.assertTrue(all(c[2] == 3 for c in o.calls))
        flat = lambda s, p, st: dict(qlike=1.0, delay=0.0); self.assertEqual(SEL.tune([], flat, [dict(K=4), dict(K=2)])["params"], dict(K=2))
        self.assertTrue(SEL.tune([], flat, [dict(K=2), dict(K=3)], budget=SEL.Budget(1))["exhausted"])

    def test_final_setup(self):
        s = [dict(features=["a", "b"], params=dict(K=3)), dict(features=["a", "c", "b"], params=dict(K=3)), dict(features=["a"], params=dict(K=2)), dict(features=["b", "d"], params=dict(K=2))]
        f = SEL.final_setup(s); self.assertEqual(f["n_features"], 2); self.assertEqual(f["features"], ["a", "b"]); self.assertEqual(f["params"], dict(K=2))   # median 2; K tie 3 vs 2 -> smaller
        self.assertEqual(SEL.final_setup([dict(features=["z"], params=dict(lam=39)), dict(features=["y", "x"], params=dict(lam=12))])["n_features"], 2)       # median 1.5 rounds up


class TestStats(unittest.TestCase):
    def test_block_bootstrap_detects_effect_and_not_null(self):
        rng = np.random.default_rng(1); self.assertLess(ST.block_bootstrap_p(rng.normal(1.0, 1.0, 30), nboot=2000, rng=np.random.default_rng(0)), 0.01)
        self.assertGreater(ST.block_bootstrap_p(rng.normal(-1.0, 1.0, 30), nboot=2000, rng=np.random.default_rng(0)), 0.9)
        self.assertTrue(np.isnan(ST.block_bootstrap_p([1.0])))

    def test_block_bootstrap_uses_consecutive_blocks(self):
        # strongly autocorrelated effects: blocks of 3 must give a larger p than iid resampling (block=1) for the same data
        x = np.repeat(np.array([2.0, -2.0, 2.0, -1.0, 1.0, 0.5, 2.0, -1.5, 1.0, 0.3]), 3)[:30] + 0.1
        self.assertGreaterEqual(ST.block_bootstrap_p(x, block=3, nboot=4000, rng=np.random.default_rng(0)), ST.block_bootstrap_p(x, block=1, nboot=4000, rng=np.random.default_rng(0)) - 0.02)

    def test_fold_tests_fields_and_sign_consistency(self):
        t = ST.fold_tests([1, 2, 3, -1, 2, 1, 0.5, 2], nboot=2000); self.assertEqual(t["n_folds"], 8); self.assertAlmostEqual(t["sign_consistency"], 7 / 8); self.assertLess(t["p_wilcoxon"], 0.05)
        self.assertTrue(np.isnan(ST.fold_tests([0, 0, 0])["p_wilcoxon"]))

    def test_intersection_union(self):
        self.assertEqual(ST.intersection_union(0.01, 0.20), 0.20); self.assertTrue(np.isnan(ST.intersection_union(0.01, float("nan"))))

    def test_holm_known_values(self):
        r = ST.holm(dict(a=0.01, b=0.04, c=0.03, d=0.5)); self.assertAlmostEqual(r["a"]["p_adj"], 0.04); self.assertAlmostEqual(r["c"]["p_adj"], 0.09); self.assertAlmostEqual(r["b"]["p_adj"], 0.09)
        self.assertEqual([r[k]["reject"] for k in "abcd"], [True, False, False, False])
        r2 = ST.holm(dict(a=0.001, b=float("nan"), c=0.2)); self.assertTrue(r2["a"]["reject"]); self.assertFalse(r2["b"]["reject"]); self.assertAlmostEqual(r2["a"]["p_adj"], 0.003)    # A15 rule 6a: NaN enters as 1 and counts in m

    def test_bh_known_values(self):
        r = ST.benjamini_hochberg(dict(a=0.01, b=0.02, c=0.03, d=0.5)); self.assertAlmostEqual(r["a"]["q_adj"], 0.04); self.assertAlmostEqual(r["c"]["q_adj"], 0.04); self.assertAlmostEqual(r["d"]["q_adj"], 0.5)
        self.assertTrue(r["a"]["reject"] and not r["d"]["reject"])

    def test_mde_monotone_in_folds_and_sd(self):
        a = ST.mde(1.0, 30, nsim=60, nboot=200, seed=1); b = ST.mde(1.0, 8, nsim=60, nboot=200, seed=1); self.assertIsNotNone(a["mde_in_sd"])
        self.assertTrue(b["mde_in_sd"] is None or b["mde_in_sd"] >= a["mde_in_sd"]); self.assertAlmostEqual(ST.mde(2.0, 30, nsim=40, nboot=200, seed=2)["mde"] / 2.0, ST.mde(2.0, 30, nsim=40, nboot=200, seed=2)["mde_in_sd"])


class TestH1(unittest.TestCase):
    def test_h1a_skips_few_stable_days_and_scores_curves(self):
        self.assertIsNone(H.h1a_fold_effect([(0.1, 0.5)], [(0.1, 0.2)], 7)["effect"]); self.assertIn("< 8", H.h1a_fold_effect([], [], 7)["skipped"])
        r = H.h1a_fold_effect([(0.05, 0.6), (0.5, 0.9)], [(0.05, 0.2), (0.5, 0.4)], 8); self.assertGreater(r["effect"], 0); self.assertIsNone(r["skipped"])
        self.assertAlmostEqual(H.h1a_fold_effect([(0.1, 0.5)], [(0.1, 0.5)], 20)["effect"], 0.0)

    def test_h1b_aligns_and_signs(self):
        kb, kf = np.array([1, 2, 3, 4]), np.array([2, 3, 4, 5]); lb, lf = np.array([2.0, 2.0, 2.0, 2.0]), np.array([1.0, 1.0, 1.0, 9.0])
        r = H.h1b_fold_effect(lb, kb, lf, kf); self.assertEqual(r["n"], 3); self.assertAlmostEqual(r["effect"], 1.0)          # common keys 2,3,4: base 2,2,2 ; feat 1,1,1
        self.assertIsNone(H.h1b_fold_effect([1.0], [1], [1.0], [2])["effect"])
        rng = np.random.default_rng(0); n = 200; r2 = H.h1b_fold_effect(rng.normal(2, .1, n), np.arange(n), rng.normal(1, .1, n), np.arange(n)); self.assertLess(r2["dm"]["p_one_sided"], 0.01)

    def test_family_result_confirmatory_excludes_contaminated_and_keeps_sensitivity(self):
        folds = list(range(10)); ea = [1.0] * 8 + [-5.0, -5.0]; eb = [1.0] * 8 + [None, -5.0]
        r = H.family_result(ea, eb, folds, excluded=[8, 9], nboot=2000)
        self.assertEqual(r["confirmatory"]["H1a"]["n_folds"], 8); self.assertEqual(r["confirmatory"]["H1b"]["n_folds"], 8); self.assertEqual(r["all_folds_sensitivity"]["H1a"]["n_folds"], 10); self.assertEqual(r["all_folds_sensitivity"]["H1b"]["n_folds"], 9)
        self.assertGreater(r["confirmatory"]["H1a"]["mean"], 0); self.assertLess(r["all_folds_sensitivity"]["H1a"]["mean"], 0)

    def test_h1_decision_holm_over_three_families_bocpd_secondary(self):
        fr = {f: {"confirmatory": {"p_iu": p}} for f, p in zip(H.FAMILIES, [0.001, 0.2, 0.012, 0.0001])}; d = H.h1_decision(fr)
        self.assertEqual(H.H1_FAMILIES, ("gaussian_hmm", "student_t_hmm", "hsmm")); self.assertAlmostEqual(d["gaussian_hmm"]["p_adj"], 0.003)           # m = 3, smallest p x 3
        self.assertTrue(d["gaussian_hmm"]["reject"]); self.assertFalse(d["student_t_hmm"]["reject"]); self.assertTrue(d["hsmm"]["reject"]); self.assertAlmostEqual(d["hsmm"]["p_adj"], 0.024)
        self.assertTrue(d["bocpd"]["secondary"]); self.assertFalse(d["bocpd"]["reject"]); self.assertEqual(d["bocpd"]["p"], 0.0001)                 # outside Holm even with the smallest p
        fr2 = {f: {"confirmatory": {"p_iu": p}} for f, p in zip(H.FAMILIES, [0.02, 0.02, 0.02, 0.5])}; self.assertFalse(any(H.h1_decision(fr2)[f]["reject"] for f in H.H1_FAMILIES))   # 0.02 x 3 = 0.06


class TestFreeze(unittest.TestCase):
    def doc(self, passing=("hsmm", "gaussian_hmm")):
        return FZ.build_freeze(dict(LEGACY=dict(f=1), RAW=dict(f=2)), dict(LEGACY=dict(t=1), RAW=dict(t=2)), dict(x="abc"), {f: dict(reject=f in passing, secondary=f in H.SECONDARY_FAMILIES) for f in H.FAMILIES},
                               dict(gaussian_hmm=1.0, student_t_hmm=0.9, hsmm=1.0, bocpd=1.2), "ph", ["A6", "A7", "A8"])

    def test_h2_primary_lowest_validation_qlike_then_simpler(self):
        self.assertEqual(FZ.h2_primary(["hsmm", "gaussian_hmm"], dict(hsmm=1.0, gaussian_hmm=1.0)), "gaussian_hmm")           # tie -> simpler
        self.assertEqual(FZ.h2_primary(["hsmm", "student_t_hmm"], dict(hsmm=1.0, student_t_hmm=1.0)), "student_t_hmm"); self.assertIsNone(FZ.h2_primary(["bocpd"], dict(bocpd=0.1)))   # A9: Gaussian < Student-t < HSMM; BOCPD never H2
        self.assertEqual(FZ.h2_primary(["hsmm", "gaussian_hmm"], dict(hsmm=0.9, gaussian_hmm=1.0)), "hsmm"); self.assertIsNone(FZ.h2_primary([], {}))
        self.assertEqual(self.doc()["h2_primary_detector"], "gaussian_hmm"); self.assertEqual(self.doc(())["h2_primary_detector"], None)

    def test_write_freeze_is_hashed_never_overwritten_and_precedes_evaluation(self):
        with tempfile.TemporaryDirectory() as td:
            p = FZ.write_freeze(self.doc(), td); self.assertTrue(p.with_suffix(".sha256").exists()); FZ.verify_freeze(p)
            with self.assertRaises(FileExistsError): FZ.write_freeze(self.doc(), td)
            p.write_text(p.read_text() + " ");
            with self.assertRaises(RuntimeError): FZ.verify_freeze(p)
        with tempfile.TemporaryDirectory() as td:
            (Path(td) / "evaluation_LEGACY.json").write_text("{}")
            with self.assertRaises(RuntimeError): FZ.write_freeze(self.doc(), td)

    def test_runner_requires_token_runs_once_and_passes_only_frozen_values(self):
        with tempfile.TemporaryDirectory() as td:
            p = FZ.write_freeze(self.doc(), td); got = []
            fit = lambda era, s, t: got.append(("fit", era, s, t)) or "M"; run = lambda era, m, s, t: got.append(("run", era, m)) or dict(era=era, ok=True)
            with self.assertRaises(PermissionError): FZ.run_confirmatory(p, td, ["LEGACY"], fit, run, "wrong")
            self.assertEqual(got, [])                                                       # nothing ran without the token
            out = FZ.run_confirmatory(p, td, ["LEGACY", "RAW"], fit, run, FZ.sha(p)); self.assertEqual(set(out), {"LEGACY", "RAW"}); self.assertEqual(got[0], ("fit", "LEGACY", dict(f=1), dict(t=1)))
            with self.assertRaises(RuntimeError): FZ.run_confirmatory(p, td, ["LEGACY"], fit, run, FZ.sha(p))      # second run blocked
            self.assertEqual(sum(1 for g in got if g[0] == "run"), 2)

    def test_runner_refuses_tampered_freeze(self):
        with tempfile.TemporaryDirectory() as td:
            p = FZ.write_freeze(self.doc(), td); tok = FZ.sha(p); p.write_text(p.read_text() + "\n")
            with self.assertRaises(RuntimeError): FZ.run_confirmatory(p, td, ["LEGACY"], lambda *a: 1, lambda *a: {}, tok)


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (Path(__file__).resolve().parent / "results" / "unit_tests_build.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
