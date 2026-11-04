#!/usr/bin/env python3
"""Orchestration of a full Section 5 run (A9): per-fold selection (5.8), H1(a)/(b) scoring (A6-A8), statistics (5.9, 5.11), final setups, freeze document (5.12). Everything that touches
data sits behind a Backend object; this module never reads market data. Checkpoints are keyed with the code version (sha256 of the modules below), so results of older code are never reused
(audit finding 11). The refit/run step (5.13) is s5_freeze.run_confirmatory and is not called here.

Backend interface (all per fold id 'ERA|n'; a family is one of s5_h1.FAMILIES):
  folds() -> list of fold ids in consecutive order          candidates(fold) -> feature names          param_grid(family) -> [dict(K=..)] or [dict(lam=..)]
  objective(fold, family) -> f(subset, params, starts) -> dict(qlike, delay)        (validation QLIKE and synthetic delay of a model fitted on the fold's inner train)
  score(fold, family, setup) -> dict(points_feat, points_base, n_stable_test, loss_base, key_base, loss_feat, key_feat, val_qlike)   (test segment; used only after selection)
  final_thresholds(era, family, setup) -> dict                       input_hashes() -> dict"""
import json, hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_select as SEL, s5_h1 as H, s5_freeze as FZ

HERE = Path(__file__).resolve().parent
CODE_FILES = ["s5_select.py", "s5_stats.py", "s5_h1.py", "s5_freeze.py", "s5_run.py", "s5_a6.py", "s5_eval.py"]


def code_version(files=CODE_FILES, base=HERE):
    h = hashlib.sha256()
    for f in files:
        p = base / f; h.update(f.encode()); h.update(hashlib.sha256(p.read_bytes()).digest() if p.exists() else b"missing")
    return h.hexdigest()[:16]


class Checkpoint:
    """One JSON file per unit; the key includes the code version, so a code change misses every older unit."""
    def __init__(self, directory, version): self.dir = Path(directory); self.dir.mkdir(parents=True, exist_ok=True); self.version = version; self.hits = 0; self.misses = 0

    def path(self, key): return self.dir / (hashlib.sha256(f"{self.version}|{key}".encode()).hexdigest()[:40] + ".json")

    def run(self, key, fn):
        p = self.path(key)
        if p.exists(): self.hits += 1; return json.loads(p.read_text(encoding="utf-8"))["value"]
        v = fn(); self.misses += 1; tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(dict(key=key, version=self.version, value=v), default=float), encoding="utf-8"); tmp.replace(p); return v


def excluded_from_contamination(path):
    """Fold ids 'ERA|n' excluded from confirmatory H1 by the contamination list (A8 item 2)."""
    j = json.loads(Path(path).read_text(encoding="utf-8")); return {f"{x['era']}|{x['fold']}" for x in j["folds"] if x["excluded"]}


def select_fold(backend, fold, family, budget=None):
    """5.8 on the fold's own validation: greedy forward with fixed K/lambda, then tuning. Returns the fold setup (features, params, trace)."""
    obj = backend.objective(fold, family); g = SEL.greedy_forward(backend.candidates(fold), obj, budget=SEL.Budget(budget) if budget else None)
    t = SEL.tune(g["selected"], obj, backend.param_grid(family))
    return dict(features=g["selected"], params=t["params"], trace=g["trace"], budget_exhausted=bool(g["exhausted"] or t["exhausted"]), base_qlike=g["base_qlike"], val_qlike=t["result"]["qlike"] if t["result"] else None)


def score_fold(backend, fold, family, setup):
    s = backend.score(fold, family, setup)
    a = H.h1a_fold_effect(s["points_feat"], s["points_base"], s["n_stable_test"]); b = H.h1b_fold_effect(s["loss_base"], s["key_base"], s["loss_feat"], s["key_feat"])
    return dict(a=a["effect"], a_skipped=a["skipped"], b=b["effect"], b_skipped=b["skipped"], b_n=b["n"], b_dm_stat=(b["dm"] or {}).get("stat"), val_qlike=s["val_qlike"], flagged_fit=bool(s.get("flagged_fit", False)))


def run_all(backend, out_dir, excluded=(), budget=None, nboot=10000, seed=0, files=CODE_FILES):
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); ck = Checkpoint(out / "ckpt", code_version(files)); folds = backend.folds(); per = {f: {} for f in H.FAMILIES}
    for fam in H.FAMILIES:
        for fold in folds:
            setup = ck.run(f"select|{fold}|{fam}", lambda: select_fold(backend, fold, fam, budget))
            sc = ck.run(f"score|{fold}|{fam}", lambda: score_fold(backend, fold, fam, setup)); per[fam][fold] = dict(setup=setup, score=sc)
    fam_res = {fam: H.family_result([per[fam][f]["score"]["a"] for f in folds], [per[fam][f]["score"]["b"] for f in folds], folds, excluded, nboot, seed, flagged=[bool(per[fam][f]["score"].get("flagged_fit", False)) for f in folds]) for fam in H.FAMILIES}
    dec = {w: H.h1_decision(fam_res, which=w) for w in ("confirmatory", "all_folds_sensitivity")}
    eras = sorted({f.split("|")[0] for f in folds}); final = {e: {fam: SEL.final_setup([per[fam][f]["setup"] for f in folds if f.startswith(e + "|")]) for fam in H.FAMILIES} for e in eras}
    medq = {fam: float(np.median([per[fam][f]["score"]["val_qlike"] for f in folds])) for fam in H.FAMILIES}
    summ = dict(code_version=ck.version, n_folds=len(folds), excluded=sorted(excluded), checkpoint=dict(hits=ck.hits, misses=ck.misses), family_results=fam_res, holm=dec, final_setups=final,
                median_validation_qlike=medq, skipped_h1a={fam: [f for f in folds if per[fam][f]["score"]["a_skipped"]] for fam in H.FAMILIES},
                exhausted_budget={fam: [f for f in folds if per[fam][f]["setup"]["budget_exhausted"]] for fam in H.FAMILIES})
    (out / "run_summary.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8"); summ["_per_fold"] = per; return summ


def freeze_step(backend, summ, results_dir, protocol_hash, amendments):
    """5.12: write the hashed freeze document from a run summary (confirmatory verdicts). Refuses to overwrite or to precede-violate (see s5_freeze.write_freeze)."""
    setups = summ["final_setups"]; thr = {e: {fam: backend.final_thresholds(e, fam, setups[e][fam]) for fam in setups[e]} for e in setups}
    doc = FZ.build_freeze(setups, thr, backend.input_hashes(), summ["holm"]["confirmatory"], summ["median_validation_qlike"], protocol_hash, amendments)
    return FZ.write_freeze(doc, results_dir), doc
