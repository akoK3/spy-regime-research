#!/usr/bin/env python3
"""Analyses on the stored main-run outputs only (section5/results/main_run): no data access, no model fit, no protocol change. Reads the completion record (verified) and the 272 checkpoints.
(2) D1: feature-family selection frequency per model family across the 34 folds, including same-family co-selection. Families: name-stem mapping defined here (no pre-registered
    family labels exist for the 19 primary columns): window, qualifier and the __sadj suffix are dropped.
(4) POST HOC: block bootstrap with blocks that do not cross the LEGACY/RAW boundary (moving blocks of 3 within each era, era counts kept; same centring, add-one rule, nboot and seeds
    as 5.9), IU and Holm across the three H1 families.
(5) H1(b) percent QLIKE improvement: only the VALIDATION percent is computable from stored outputs (setup val_qlike vs base_val_qlike); the test-segment level is not stored.
p-values at the add-one floor are reported as '< 1/10001'. Writes results/posthoc_main_run.json."""
import sys, json, re
from pathlib import Path
from collections import Counter
from itertools import combinations
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_guard as G, s5_h1 as H, s5_stats as ST

HERE = Path(__file__).resolve().parent; D = HERE / "results" / "main_run"; NBOOT = 10000; FLOOR = 1 / (NBOOT + 1)


def family_of(col):
    """Name-stem family: rv5_strict / rv10_partial90 (+__sadj) -> rv; downside5/10 -> downside; momentum5..30 -> momentum; abs_return_1m -> abs_return; return_1m -> return;
    intrabar_range_log -> intrabar_range; relative_volume20 -> relative_volume; close_location_proxy -> close_location."""
    c = col[:-6] if col.endswith("__sadj") else col
    for stem in ("abs_return", "return", "intrabar_range", "relative_volume", "close_location", "downside", "momentum", "rv"):
        if c.startswith(stem): return stem
    raise ValueError(col)


def fmt(p): return "< 1/10001" if p is not None and np.isfinite(p) and p <= FLOOR + 1e-15 else (None if p is None or not np.isfinite(p) else round(float(p), 4))


def within_era_p(x, eras, block=3, nboot=NBOOT, seed=0):
    """One-sided p for H0: mean <= 0; moving blocks of `block` consecutive folds drawn within each era, each era keeps its count; centred at the pooled mean; add-one."""
    x = np.asarray(x, float); eras = np.asarray(eras); obs = x.mean(); xc = x - obs; rng = np.random.default_rng(seed); parts = []
    if len(x) < 2: return float("nan")
    for e in sorted(set(eras)):
        v = xc[eras == e]; n = len(v); b = max(1, min(block, n)); starts = np.arange(n - b + 1); nb = int(np.ceil(n / b))
        parts.append(v[(rng.choice(starts, (nboot, nb))[:, :, None] + np.arange(b)).reshape(nboot, -1)[:, :n]])
    m = np.concatenate(parts, axis=1).mean(1); return float((1 + (m >= obs).sum()) / (nboot + 1))


def main():
    rec = G.verify_completion(D / G.COMPLETION, require_main=True); folds = rec["folds"]
    units = {}
    for p in (D / "ckpt").glob("*.json"):
        c = json.loads(p.read_text(encoding="utf-8")); k = c["key"].split("|"); assert c["version"] == rec["checkpoint_version"]; units[(k[0], f"{k[3]}|{k[4]}", k[5])] = c["value"]
    assert len(units) == 272
    summ = json.loads((D / "run_summary.json").read_text(encoding="utf-8")); excluded = set(summ["excluded"]); out = dict(source=dict(completion_record_sha256=G.sha(D / G.COMPLETION), results_sha256=rec["results_sha256"]))
    # (2) D1
    d1 = {}
    for fam in H.FAMILIES:
        sets = [units[("select", f, fam)]["features"] for f in folds]; fams = [[family_of(c) for c in s] for s in sets]
        d1[fam] = dict(n_folds=len(folds), mean_features=round(float(np.mean([len(s) for s in sets])), 2), folds_with_no_feature=sum(1 for s in sets if not s),
                       feature_frequency=dict(Counter(c for s in sets for c in s).most_common()), family_frequency_folds=dict(Counter(x for fs in fams for x in set(fs)).most_common()),
                       same_family_coselection_folds=dict(Counter(x for fs in fams for x, n in Counter(fs).items() if n >= 2).most_common()),
                       family_pair_coselection_folds=dict(Counter(f"{a}+{b}" for fs in fams for a, b in combinations(sorted(set(fs)), 2)).most_common()),
                       by_era={e: dict(Counter(x for f, fs in zip(folds, fams) if f.startswith(e) for x in set(fs)).most_common()) for e in ("LEGACY", "RAW")})
    out["D1"] = dict(family_mapping={c: family_of(c) for c in sorted({c for v in units.values() if "features" in v for c in v["features"]})}, by_model_family=d1,
                     note="Family labels are a name-stem mapping defined in this script; Section 4 defines no family labels for the 19 primary columns.")
    # (4) POST HOC within-era bootstrap
    boot = {}
    for label, keep in (("confirmatory", lambda f: f not in excluded), ("all_folds_sensitivity", lambda f: True)):
        pi = {}; boot[label] = {}
        for fam in H.FAMILIES:
            r = {}
            for comp, key, seed in (("H1a", "a", 0), ("H1b", "b", 1)):
                xs = [(units[("score", f, fam)][key], f.split("|")[0]) for f in folds if keep(f) and units[("score", f, fam)][key] is not None]
                x, e = [v for v, _ in xs], [v for _, v in xs]; p = within_era_p(x, e, seed=seed); p_orig = summ["family_results"][fam][label][comp]["p_block_bootstrap"]
                r[comp] = dict(n=len(x), n_by_era=dict(Counter(e)), mean=round(float(np.mean(x)), 4), p_within_era=p, p_within_era_fmt=fmt(p), p_main_run=p_orig, p_main_run_fmt=fmt(p_orig))
            r["p_iu"] = ST.intersection_union(r["H1a"]["p_within_era"], r["H1b"]["p_within_era"]); boot[label][fam] = r
            if fam in H.H1_FAMILIES: pi[fam] = r["p_iu"]
        hm = ST.holm(pi)
        for fam in H.H1_FAMILIES: boot[label][fam].update(p_iu_fmt=fmt(boot[label][fam]["p_iu"]), holm_p_adj=hm[fam]["p_adj"], holm_p_adj_fmt=fmt(hm[fam]["p_adj"]) if hm[fam]["p_adj"] > FLOOR * 3 else f"<= 3/10001", holm_reject=hm[fam]["reject"])
    out["POST_HOC_within_era_bootstrap"] = boot
    # (5) validation percent QLIKE improvement
    pct = {}
    for fam in H.FAMILIES:
        v = {f: 100 * (units[("select", f, fam)]["base_val_qlike"] - units[("select", f, fam)]["val_qlike"]) / units[("select", f, fam)]["base_val_qlike"] for f in folds}
        c = [v[f] for f in folds if f not in excluded]
        pct[fam] = dict(confirmatory_median_pct=round(float(np.median(c)), 1), confirmatory_iqr_pct=[round(float(q), 1) for q in np.percentile(c, [25, 75])], confirmatory_min_max_pct=[round(min(c), 1), round(max(c), 1)],
                        all_folds_median_pct=round(float(np.median(list(v.values()))), 1), per_fold_pct={f: round(x, 1) for f, x in v.items()})
    out["H1b_percent_QLIKE_improvement_VALIDATION"] = dict(by_family=pct, note="Validation segments (selection data), not the test segments H1(b) is scored on; test-level QLIKE means are not stored in the checkpoints.")
    out["not_computable_from_stored_outputs"] = {"H1(c)": "needs alarm times on FOMC test sessions: filtered outputs and fitted models are not stored",
                                                 "R=1 placebo gap": "needs detector runs on placebo splices: fitted models are not stored",
                                                 "H1(b) test percent": "needs the per-fold mean test QLIKE of the baseline: only the difference is stored"}
    (HERE / "results" / "posthoc_main_run.json").write_text(json.dumps(out, indent=1, default=float), encoding="utf-8"); return out


if __name__ == "__main__":
    o = main(); print(json.dumps({k: o[k] for k in ("POST_HOC_within_era_bootstrap",)}, default=float)[:200]); print("written")
