#!/usr/bin/env python3
"""Orchestration of a full Section 5 run (A9, A15): per-fold selection (5.8) with the baseline tuned on the same grid (A15 rule 1), H1(a)/(b) scoring (A6-A8), statistics (5.9, 5.11),
final setups, freeze document (5.12). Everything that touches data sits behind a Backend object; this module never reads market data. Checkpoints are keyed with the code version: the
sha256 over every result-affecting module (A15 rule 4: the transitive closure of local imports from RESULT_ROOTS), so results of older code are never reused. The refit/run step (5.13) is
s5_freeze.run_confirmatory and is not called here.

Backend interface (all per fold id 'ERA|n'; a family is one of s5_h1.FAMILIES):
  folds() -> list of fold ids in consecutive order          candidates(fold) -> feature names          param_grid(family) -> [dict(K=..)] or [dict(lam=..)]
  objective(fold, family) -> f(subset, params, starts) -> dict(qlike, delay)        (validation QLIKE and synthetic delay of a model fitted on the fold's inner train)
  score(fold, family, setup) -> dict(points_feat, points_base, n_stable_test, loss_base, key_base, loss_feat, key_feat, val_qlike[, h1a_failed, flagged_fit])   (test segment; after selection)
  era_thresholds(era, family, setup) -> dict   (A11 era-level rule; refused before mark_scoring_complete)          input_hashes() -> dict
  optional: kind (str), mark_scoring_complete()"""
import ast, json, hashlib, sys
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_select as SEL, s5_h1 as H, s5_freeze as FZ

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
VERSION_SCHEME = "A15"                                                                   # A15 rule 4: changes every version, so all older checkpoints miss
RESULT_ROOTS = ["s5_run.py", "s5_backend.py", "s5_era_threshold.py", "s5_main.py"]
DEFAULT_CONTAMINATION = HERE / "results" / "contamination_list.json"


def _local(name, dirs):
    for dd in dirs:
        p = dd / (name.replace(".", "/") + ".py")
        if p.exists(): return p
    return None


def result_modules(roots=RESULT_ROOTS, base=HERE):
    """A15 rule 4: every local module that can change a result = the transitive closure of imports (any depth, function-level imports included) that resolve to a file in
    section5/, the repository root or the Section 4 source folder that step3_all_in_one.py puts on the path, starting from `roots`. Returns paths relative to the repository root, sorted."""
    dirs = [base, base.parent, base.parent / "section431_step3_verification" / "prototype_sources"]; seen = set(); todo = [base / r for r in roots if (base / r).exists()]
    while todo:
        p = todo.pop()
        if p in seen: continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else [])
            for n in names:
                q = _local(n, dirs)
                if q is not None and q not in seen: todo.append(q)
    return sorted(str(p.relative_to(base.parent)).replace("\\", "/") for p in seen)


def code_version(files=None, base=HERE):
    """sha256 over the scheme tag and (relative path, content hash) of each file. files=None: result_modules() (relative to the repository root); else names relative to `base`."""
    h = hashlib.sha256(); h.update(VERSION_SCHEME.encode())
    paths = [(f, base.parent / f) for f in result_modules(base=base)] if files is None else [(f, base / f) for f in files]
    for f, p in paths:
        h.update(f.encode()); h.update(hashlib.sha256(p.read_bytes()).digest() if p.exists() else b"missing")
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


def run_all(backend, out_dir, contamination=DEFAULT_CONTAMINATION, budget=None, nboot=10000, seed=0, files=None):
    """A15 rule 5d: the confirmatory exclusions come from the contamination list, loaded here (no exclusion argument). Folds are processed in consecutive order, every family per fold
    (one fold in memory at a time for the main backend); results do not depend on the order."""
    cpath = Path(contamination); excluded = excluded_from_contamination(cpath); bk = getattr(backend, "kind", type(backend).__name__)
    out = Path(out_dir); out.mkdir(parents=True, exist_ok=True); ck = Checkpoint(out / "ckpt", code_version(files)); folds = backend.folds(); per = {f: {} for f in H.FAMILIES}
    for fold in folds:
        for fam in H.FAMILIES:
            setup = ck.run(f"select|{bk}|budget={budget}|{fold}|{fam}", lambda: select_fold(backend, fold, fam, budget))
            sc = ck.run(f"score|{bk}|budget={budget}|{fold}|{fam}", lambda: score_fold(backend, fold, fam, setup)); per[fam][fold] = dict(setup=setup, score=sc)
    if hasattr(backend, "mark_scoring_complete"): backend.mark_scoring_complete()
    col = lambda fam, k: [per[fam][f]["score"].get(k) for f in folds]
    fam_res = {fam: H.family_result(col(fam, "a"), col(fam, "b"), folds, excluded, nboot, seed, flagged=[bool(x) for x in col(fam, "flagged_fit")], failed_a=col(fam, "a_failed")) for fam in H.FAMILIES}
    dec = {w: H.h1_decision(fam_res, which=w) for w in ("confirmatory", "all_folds_sensitivity")}
    eras = sorted({f.split("|")[0] for f in folds}); final = {e: {fam: SEL.final_setup([per[fam][f]["setup"] for f in folds if f.startswith(e + "|")]) for fam in H.FAMILIES} for e in eras}
    medq = {fam: float(np.median([per[fam][f]["score"]["val_qlike"] for f in folds])) for fam in H.FAMILIES}
    summ = dict(code_version=ck.version, backend=bk, complete=True, n_folds=len(folds), folds=list(folds), contamination_list=str(cpath), contamination_sha256=hashlib.sha256(cpath.read_bytes()).hexdigest(),
                excluded=sorted(excluded), checkpoint=dict(hits=ck.hits, misses=ck.misses), family_results=fam_res, holm=dec, final_setups=final, median_validation_qlike=medq,
                skipped_h1a={fam: [f for f in folds if per[fam][f]["score"]["a_skipped"]] for fam in H.FAMILIES},
                failed_h1a={fam: {f: per[fam][f]["score"].get("a_failed") for f in folds if per[fam][f]["score"].get("a_failed")} for fam in H.FAMILIES},
                exhausted_budget={fam: [f for f in folds if per[fam][f]["setup"]["budget_exhausted"]] for fam in H.FAMILIES})
    (out / "run_summary.json").write_text(json.dumps(summ, indent=1, default=float), encoding="utf-8"); summ["_per_fold"] = per; return summ


def freeze_step(backend, summ, results_dir, protocol_hash, amendments):
    """5.12: write the hashed freeze document from a complete run summary (confirmatory verdicts). Thresholds: A11 era-level rule via backend.era_thresholds (A15 rule 5c).
    Input hashes: protocol, all integrated amendments, cited inputs, data files (A15 rule 6c). Refuses to overwrite or to follow evaluation output (s5_freeze.write_freeze)."""
    if not summ.get("complete"): raise RuntimeError("freeze needs a complete run summary (every fold selected and scored)")
    setups = summ["final_setups"]; thr = {e: {fam: backend.era_thresholds(e, fam, setups[e][fam]) for fam in setups[e]} for e in setups}
    doc = FZ.build_freeze(setups, thr, backend.input_hashes(), summ["holm"]["confirmatory"], summ["median_validation_qlike"], protocol_hash, amendments)
    doc.update(contamination_sha256=summ.get("contamination_sha256"), code_version=summ.get("code_version"), failed_h1a=summ.get("failed_h1a"))
    return FZ.write_freeze(doc, results_dir), doc
