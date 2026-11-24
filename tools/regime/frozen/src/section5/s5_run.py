#!/usr/bin/env python3
"""Orchestration of a full Section 5 run (A9, A15, A16): per-fold selection (5.8) with the baseline tuned on the same grid (A15 rule 1), H1(a)/(b) scoring (A6-A8), statistics (5.9, 5.11),
final setups, completion record, freeze document (5.12). Everything that touches data sits behind a Backend object; this module never reads market data. Guards (s5_guard): the protocol
must be FROZEN (A15 rule 5b); the contamination list is the canonical, hash-checked file (A16 rule 2); checkpoints are keyed by the code version over every result-affecting module and the
verified protocol hash (A15 rule 4, A16 rules 4 and 6); no unit is computed after the era calibration (A16 rule 5). The refit/run step (5.13) is s5_freeze.run_confirmatory, not called here.

Backend interface (all per fold id 'ERA|n'; a family is one of s5_h1.FAMILIES):
  folds() -> list of fold ids in consecutive order          candidates(fold) -> feature names          param_grid(family) -> [dict(K=..)] or [dict(lam=..)]
  objective(fold, family) -> f(subset, params, starts) -> dict(qlike, delay)        (validation QLIKE and synthetic delay of a model fitted on the fold's inner train)
  score(fold, family, setup) -> dict(points_feat, points_base, n_stable_test, loss_base, key_base, loss_feat, key_feat, val_qlike[, h1a_failed, flagged_fit])   (test segment; after selection)
  era_thresholds(era, family, setup, completion) -> dict   (A11 era-level rule; needs the completion record, A16 rule 1)          input_hashes() -> dict          optional: kind (str)"""
import json, hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_select as SEL, s5_h1 as H, s5_freeze as FZ, s5_guard as G

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
result_modules = G.result_modules; code_version = G.code_version; VERSION_SCHEME = G.VERSION_SCHEME; RESULT_ROOTS = G.RESULT_ROOTS


class Checkpoint:
    """One JSON file per unit; the key includes the version (code and protocol), so a change misses every older unit. A16 rule 5: computing a missing unit is refused after the era calibration."""
    def __init__(self, directory, version): self.dir = Path(directory); self.dir.mkdir(parents=True, exist_ok=True); self.version = version; self.hits = 0; self.misses = 0

    def path(self, key): return self.dir / (hashlib.sha256(f"{self.version}|{key}".encode()).hexdigest()[:40] + ".json")

    def run(self, key, fn):
        p = self.path(key)
        if p.exists(): self.hits += 1; return json.loads(p.read_text(encoding="utf-8"))["value"]
        G.check_unlocked(f"computing {key.split('|')[0]}")
        v = fn(); self.misses += 1; tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(dict(key=key, version=self.version, value=v), default=float), encoding="utf-8"); tmp.replace(p); return v


def excluded_from_contamination():
    """Fold ids 'ERA|n' excluded from confirmatory H1 by the canonical contamination list (A8 item 2, A16 rule 2)."""
    return G.excluded_folds()[0]


def select_fold(backend, fold, family, budget=None):
    """5.8 on the fold's own validation: greedy forward with fixed K/lambda, then tuning of the selected set; then (A15 rule 1) the return-only baseline tuned on the identical grid,
    starts and tie rule. Returns the fold setup (features, params, base_params, trace)."""
    obj = backend.objective(fold, family); grid = backend.param_grid(family); g = SEL.greedy_forward(backend.candidates(fold), obj, budget=SEL.Budget(budget) if budget else None)
    t = SEL.tune(g["selected"], obj, grid); tb = SEL.tune((), obj, grid)
    return dict(features=g["selected"], params=t["params"], base_params=tb["params"], trace=g["trace"], budget_exhausted=bool(g["exhausted"] or t["exhausted"] or tb["exhausted"]),
                base_qlike=g["base_qlike"], val_qlike=t["result"]["qlike"] if t["result"] else None, base_val_qlike=tb["result"]["qlike"] if tb["result"] else None)


def score_fold(backend, fold, family, setup):
    s = backend.score(fold, family, setup)
    a = H.h1a_fold_effect(s["points_feat"], s["points_base"], s["n_stable_test"], failed=s.get("h1a_failed")); b = H.h1b_fold_effect(s["loss_base"], s["key_base"], s["loss_feat"], s["key_feat"])
    return dict(a=a["effect"], a_skipped=a["skipped"], a_failed=a.get("failed"), b=b["effect"], b_skipped=b["skipped"], b_n=b["n"], b_dm_stat=(b["dm"] or {}).get("stat"), val_qlike=s["val_qlike"],
                flagged_fit=bool(s.get("flagged_fit", False)))


def run_all(backend, out_dir, budget=None, nboot=10000, seed=0):
    """Exclusions from the canonical contamination list (A16 rule 2); version = code closure + verified protocol hash (A16 rules 4, 6). Folds in consecutive order, every family per fold.
    After every unit exists, writes the completion record (A16 rule 1)."""
    ph = G.frozen_protocol_hash(); excluded, ch = G.excluded_folds(); cv = G.code_version(); bk = getattr(backend, "kind", type(backend).__name__)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); ck = Checkpoint(out / "ckpt", G.checkpoint_version(cv, ph)); folds = backend.folds(); per = {f: {} for f in H.FAMILIES}
    for fold in folds:
        for fam in H.FAMILIES:
            setup = ck.run(f"select|{bk}|budget={budget}|{fold}|{fam}", lambda: select_fold(backend, fold, fam, budget))
            sc = ck.run(f"score|{bk}|budget={budget}|{fold}|{fam}", lambda: score_fold(backend, fold, fam, setup)); per[fam][fold] = dict(setup=setup, score=sc)
    col = lambda fam, k: [per[fam][f]["score"].get(k) for f in folds]
    fam_res = {fam: H.family_result(col(fam, "a"), col(fam, "b"), folds, excluded, nboot, seed, flagged=[bool(x) for x in col(fam, "flagged_fit")], failed_a=col(fam, "a_failed")) for fam in H.FAMILIES}
    dec = {w: H.h1_decision(fam_res, which=w) for w in ("confirmatory", "all_folds_sensitivity")}
    eras = sorted({f.split("|")[0] for f in folds}); final = {e: {fam: SEL.final_setup([per[fam][f]["setup"] for f in folds if f.startswith(e + "|")]) for fam in H.FAMILIES} for e in eras}
    medq = {fam: float(np.median([per[fam][f]["score"]["val_qlike"] for f in folds])) for fam in H.FAMILIES}
    results_sha = hashlib.sha256(json.dumps(per, sort_keys=True, default=float).encode()).hexdigest()
    rec = G.write_completion(out, backend=bk, folds=list(folds), families=list(H.FAMILIES), code_version=cv, checkpoint_version=ck.version, protocol_sha256=ph, contamination_sha256=ch, results_sha256=results_sha)
    summ = dict(code_version=cv, checkpoint_version=ck.version, protocol_sha256=ph, backend=bk, complete=True, run_dir=str(out), completion_record=str(rec), n_folds=len(folds), folds=list(folds),
                contamination_sha256=ch, excluded=sorted(excluded), checkpoint=dict(hits=ck.hits, misses=ck.misses), family_results=fam_res, holm=dec, final_setups=final, median_validation_qlike=medq,
                skipped_h1a={fam: [f for f in folds if per[fam][f]["score"]["a_skipped"]] for fam in H.FAMILIES},
                failed_h1a={fam: {f: per[fam][f]["score"].get("a_failed") for f in folds if per[fam][f]["score"].get("a_failed")} for fam in H.FAMILIES},
                exhausted_budget={fam: [f for f in folds if per[fam][f]["setup"]["budget_exhausted"]] for fam in H.FAMILIES})
    (out / "run_summary.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8"); summ["_per_fold"] = per; return summ


def freeze_step(backend, summ, results_dir, amendments):
    """5.12: the hashed freeze document from a complete run. A16: the completion record must verify (rule 1), its protocol hash must equal the FROZEN protocol and the main backend's
    (rule 6), the canonical list must be the one the run used (rule 2). Thresholds: A11 era-level rule via backend.era_thresholds with the record. Input hashes per A15 rule 6c."""
    rec_path = Path(summ["run_dir"]) / G.COMPLETION; rec = G.verify_completion(rec_path, require_main=(getattr(backend, "kind", None) == "main")); ph = G.frozen_protocol_hash(); _, ch = G.canonical_contamination()
    if rec["protocol_sha256"] != ph or summ.get("protocol_sha256") != ph or getattr(backend, "protocol_sha256", ph) != ph: raise PermissionError("protocol hash of run, backend and FROZEN protocol differ (A16 rule 6)")
    if rec["contamination_sha256"] != ch or summ.get("contamination_sha256") != ch: raise PermissionError("the run used another contamination list (A16 rule 2)")
    if rec["code_version"] != summ.get("code_version") or rec["folds"] != summ.get("folds"): raise PermissionError("run summary does not match its completion record")
    setups = summ["final_setups"]; thr = {e: {fam: backend.era_thresholds(e, fam, setups[e][fam], rec_path) for fam in setups[e]} for e in setups}
    doc = FZ.build_freeze(setups, thr, backend.input_hashes(), summ["holm"]["confirmatory"], summ["median_validation_qlike"], ph, amendments)
    doc.update(contamination_sha256=ch, code_version=rec["code_version"], completion_record_sha256=G.sha(rec_path), failed_h1a=summ.get("failed_h1a"))
    return FZ.write_freeze(doc, results_dir), doc
