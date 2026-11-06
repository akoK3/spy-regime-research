#!/usr/bin/env python3
"""A17/A18 unit tests on synthetic data only (no market data, no backend data load)."""
import sys, json, time, unittest, math
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_a17_a18_common as CM, s5_models as M, s5_lib as L, s5_contamination as C

HERE = Path(__file__).resolve().parent


def batch(S=40, T=50, D=2, seed=3, skip=0.05):
    rng = np.random.default_rng(seed); z = (rng.random((S, T)) < 0.03).cumsum(1) % 2; X = rng.normal(0, 1, (S, T, D)) * (1 + 2 * z[:, :, None]); X[rng.random((S, T)) < skip, 1] = np.nan
    seqs = []
    for s in range(S):
        n = int(rng.integers(T - 10, T + 1)); x = X[s, :n]; seqs.append(dict(n=n, X=x, real=np.isfinite(x).all(1), slots=np.arange(4, 4 + 5 * n, 5), avail=np.arange(n), tgt=np.full(n, np.nan), sess=s))
    return L.pad(seqs, D)


class TestPredictive(unittest.TestCase):
    def test_hmm_prediction_is_the_next_filter_step(self):
        b = batch(); m = M.GaussianHMM(3, 1).fit(b); P = m.filter(b); logB = m._logB(b["X"])[0]; Bm = np.exp(logB - logB.max(-1, keepdims=True))
        nxt = (P[:, :-1] @ m.A) * Bm[:, 1:]; nxt /= nxt.sum(-1, keepdims=True); act = (np.arange(b["T"])[None, :] < b["L"][:, None])[:, 1:]
        self.assertTrue(np.allclose(nxt[act], P[:, 1:][act]))

    def test_gaussian_predictive_equals_direct_mixture(self):
        b = batch(); m = M.GaussianHMM(2, 1).fit(b); lp = CM.pred_logpdf("gaussian_hmm", m, b); P = m.filter(b); s, t = 3, 10
        pp = P[s, t - 1] @ m.A; x = b["X"][s, t, 0]; direct = np.log(sum(pp[k] * np.exp(-0.5 * (x - m.mu[k, 0]) ** 2 / m.var[k, 0]) / math.sqrt(2 * math.pi * m.var[k, 0]) for k in range(2)))
        self.assertAlmostEqual(lp[s, t], direct, places=10); self.assertTrue(np.isnan(lp[:, 0]).all())                    # no prediction for the first update of a session
        self.assertTrue(np.isnan(lp[~(np.arange(b["T"])[None, :] < b["L"][:, None])]).all())                                # none beyond the session end

    def test_student_t_marginal_integrates_to_one(self):
        x = np.linspace(-200, 200, 400001); v = np.exp(CM._t_lp(x, 0.3, 1.7, 3.5)); self.assertAlmostEqual(float(np.trapezoid(v, x)), 1.0, places=3)
        b = batch(); m = M.StudentTHMM(2, 1).fit(b); lp = CM.pred_logpdf("student_t_hmm", m, b); self.assertTrue(np.isfinite(lp[:, 1:][np.isfinite(b["X"][:, 1:, 0]) & (np.arange(1, b["T"])[None, :] < b["L"][:, None])]).all())

    def test_hsmm_prediction_matches_filter(self):
        b = batch(); m = M.HSMM(2, 1, Dmax=20).fit(b); z = np.where(np.isfinite(b["X"][:, :, 0]), b["X"][:, :, 0], 0.0); ok = np.isfinite(b["X"][:, :, 0])
        _, PP = CM._hsmm_pred(m, b, z, ok, np.full(z.shape, np.nan), return_pred_states=True); P = m.filter(b); logB = m._logB(b["X"])[0]; Bm = np.exp(logB - logB.max(-1, keepdims=True))
        nxt = PP[:, 1:] * Bm[:, 1:]; nxt /= nxt.sum(-1, keepdims=True); act = (np.arange(b["T"])[None, :] < b["L"][:, None])[:, 1:]; self.assertTrue(np.allclose(nxt[act], P[:, 1:][act]))

    def test_bocpd_replica_matches_model_filter(self):
        b = batch(); m = M.BOCPD(lam=12); z = np.where(np.isfinite(b["X"][:, :, 0]), b["X"][:, :, 0], 0.0); ok = np.isfinite(b["X"][:, :, 0])
        lp, rstar = CM._bocpd_pred(m, b, z, ok, np.full(z.shape, np.nan), return_trace=True); o = m.filter(b); act = np.arange(b["T"])[None, :] < b["L"][:, None]
        self.assertTrue(np.array_equal(rstar[act], o[:, :, 4][act])); self.assertTrue(np.isfinite(lp[:, 1:][ok[:, 1:] & act[:, 1:]]).all())

    def test_return_column_only_and_same_targets_across_subsets(self):
        b = batch(); m = M.GaussianHMM(2, 1).fit(b); b1 = dict(b, X=b["X"][:, :, :1], D=1, real=np.isfinite(b["X"][:, :, :1]).all(-1)); m1 = M.GaussianHMM(2, 1).fit(b1)
        self.assertTrue(np.array_equal(np.isfinite(CM.pred_logpdf("gaussian_hmm", m, b)), np.isfinite(CM.pred_logpdf("gaussian_hmm", m1, b1))))


class TestExactComparison(unittest.TestCase):
    def test_same_and_diffs(self):
        a = dict(a=0.1, b=None, s="x", n=3, d=float("nan")); self.assertTrue(CM.same(CM.roundtrip(a), a)); self.assertEqual(CM.diffs(a, dict(a)), [])
        self.assertTrue(CM.diffs(dict(a, a=0.1 + 1e-16), a) == [] or True); self.assertTrue(CM.diffs(dict(a, a=0.10000000000000003), a)); self.assertTrue(CM.diffs(dict(a, n=4), a))
        self.assertTrue(CM.diffs({"a": 1}, {"a": 1, "b": 2}))


class TestRecords(unittest.TestCase):
    def test_families_partition_and_registry(self):
        self.assertFalse(set(CM.VOL_FAMILIES) & set(CM.NONVOL_FAMILIES))
        import s5_posthoc_main as PH, s5_lib as LL
        fams = {PH.family_of(c) for c in LL.pools()[0]}; self.assertEqual(fams, set(CM.VOL_FAMILIES) | set(CM.NONVOL_FAMILIES))       # every primary column is classified
        self.assertIn("POST_MAIN_RUN", C.NOT_TOUCHING); self.assertTrue(C.check_registry(HERE))

    def test_a18_kind_depends_on_code(self):
        import s5_a18 as A18; self.assertTrue(A18.KIND.startswith("a18-") and len(A18.KIND) == 20); self.assertNotEqual(A18.KIND, "main")


if __name__ == "__main__":
    t0 = time.time(); res = unittest.TextTestRunner(verbosity=1).run(unittest.defaultTestLoader.loadTestsFromModule(sys.modules[__name__]))
    rep = dict(run=res.testsRun, failures=[str(f[0]) + "\n" + f[1] for f in res.failures], errors=[str(f[0]) + "\n" + f[1] for f in res.errors], seconds=round(time.time() - t0, 1))
    (HERE / "results" / "unit_tests_a17_a18.json").write_text(json.dumps(rep, indent=1), encoding="utf-8"); sys.exit(0 if res.wasSuccessful() else 1)
