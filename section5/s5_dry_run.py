#!/usr/bin/env python3
"""A9 dry run on SYNTHETIC data only: a synthetic backend with known effects (Gaussian and Student-t HMM and BOCPD informative, HSMM null), run through s5_run, the Holm decision,
the freeze, and the guarded runner with stubs. No market data, no test or evaluation data; temporary directories. Writes results/a9_dry_run_synthetic.json."""
import sys, json, tempfile, hashlib, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_run as RUN, s5_h1 as H, s5_freeze as FZ

TRUE_FEATS = {"gaussian_hmm": {"f1": 8.0, "f2": 4.0}, "student_t_hmm": {"f1": 6.0, "f3": 4.0}, "hsmm": {}, "bocpd": {"f2": 5.0}}
EFFECT = {"gaussian_hmm": 0.08, "student_t_hmm": 0.06, "hsmm": 0.0, "bocpd": 0.07}          # true pAUC and loss effects of the synthetic features


class SyntheticBackend:
    kind = "synthetic"

    def __init__(self, n_legacy=16, n_raw=4, seed=0):
        self.ids = [f"LEGACY|{i}" for i in range(n_legacy)] + [f"RAW|{i}" for i in range(n_raw)]; self.seed = seed
        self.rng = lambda *k: np.random.default_rng([self.seed] + [int(hashlib.sha256(str(x).encode()).hexdigest()[:8], 16) for x in k])

    def folds(self): return list(self.ids)
    def candidates(self, fold): return [f"f{i}" for i in range(1, 9)]
    def param_grid(self, family): return [dict(lam=12), dict(lam=39), dict(lam=78)] if family == "bocpd" else [dict(K=2), dict(K=3), dict(K=4)]

    def objective(self, fold, family):
        g = TRUE_FEATS[family]; noise = self.rng("obj", fold, family).normal(0, 0.05, 1)[0]
        def f(subset, params, starts):
            q = 100.0 - sum(g.get(x, 0.0) for x in subset) + 0.2 * len(set(subset) - set(g)) + noise + (0.05 if params.get("K", 3) != 3 or params.get("lam", 39) != 39 else 0.0)
            return dict(qlike=float(q), delay=float(len(subset)))
        return f

    def score(self, fold, family, setup):
        r = self.rng("score", fold, family); eff = EFFECT[family]; n_stable = 5 if fold in ("LEGACY|3", "RAW|1") else 12        # two folds with too few stable days
        base = [(0.1, 0.30), (0.3, 0.45), (0.5, 0.55)]; gain = eff + r.normal(0, 0.03); feat = [(x, min(1.0, y + gain)) for x, y in base]
        n = 300; keys = np.arange(n); lb = r.normal(1.0, 0.1, n); lf = lb - eff * 0.5 + r.normal(0, 0.1, n)
        return dict(points_feat=feat, points_base=base, n_stable_test=n_stable, loss_base=lb, key_base=keys, loss_feat=lf, key_feat=keys, val_qlike=float(setup["val_qlike"]))

    def final_thresholds(self, era, family, setup): return dict(rate_target=0.2, note="synthetic")
    def era_thresholds(self, era, family, setup, completion): return dict(rate_target=0.2, note="synthetic era-level", completion=str(completion))
    def input_hashes(self): return dict(synthetic="n/a")


def main():
    t0 = time.time(); b = SyntheticBackend()
    with tempfile.TemporaryDirectory() as td:
        s1 = RUN.run_all(b, Path(td) / "run", nboot=2000); s2 = RUN.run_all(b, Path(td) / "run", nboot=2000)          # A16: canonical contamination list only           # second call must hit every checkpoint
        res = Path(td) / "results"; res.mkdir(); fz_path, doc = RUN.freeze_step(b, s1, res, ["A6", "A7", "A8", "A9"]); got = []
        out = FZ.run_confirmatory(fz_path, res, ["LEGACY", "RAW"], lambda e, s, t: got.append(("fit", e)) or "M", lambda e, m, s, t: got.append(("run", e)) or dict(era=e, synthetic=True), FZ.sha(fz_path))
        try: FZ.run_confirmatory(fz_path, res, ["LEGACY"], lambda *a: 1, lambda *a: {}, FZ.sha(fz_path)); second = "ran again (BUG)"
        except RuntimeError: second = "blocked"
    conf = s1["holm"]["confirmatory"]; summary = dict(SYNTHETIC=True, minutes=round((time.time() - t0) / 60, 3), code_version=s1["code_version"], n_folds=s1["n_folds"], excluded=s1["excluded"],
        checkpoint_first_run=s1["checkpoint"], checkpoint_second_run=s2["checkpoint"], holm_confirmatory={f: dict(p=v["p"], p_adj=v["p_adj"], reject=v["reject"], secondary=v.get("secondary", False)) for f, v in conf.items()},
        h1a_skipped_folds=s1["skipped_h1a"], final_setups_LEGACY={f: dict(features=v["features"], params=v["params"]) for f, v in s1["final_setups"]["LEGACY"].items()},
        h1_passing=doc["h1_passing_families"], h2_primary_detector=doc["h2_primary_detector"], runner_calls=got, second_run=second, n_confirmatory_folds_used={f: s1["family_results"][f]["confirmatory"]["H1a"]["n_folds"] for f in H.FAMILIES},
        n_all_folds_used={f: s1["family_results"][f]["all_folds_sensitivity"]["H1a"]["n_folds"] for f in H.FAMILIES})
    (Path(__file__).resolve().parent / "results" / "a9_dry_run_synthetic.json").write_text(json.dumps(summary, indent=1, default=float), encoding="utf-8"); print(json.dumps(summary, indent=1, default=float)[:3500])


if __name__ == "__main__":
    main()
