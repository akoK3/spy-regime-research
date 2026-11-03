#!/usr/bin/env python3
"""Protocol 5.12 and 5.13: freeze document and the guarded refit runner. This module never reads market data itself: fitting and running are injected callables.
- build_freeze / write_freeze: final setups, thresholds, input hashes, H1 verdicts and the H2 primary detector go into one hashed JSON before any evaluation output exists.
  write_freeze refuses to overwrite, and refuses when evaluation outputs already exist.
- h2_primary: the family passing H1 with the lowest median VALIDATION QLIKE; ties go to the simpler model (order SIMPLICITY below).
- run_confirmatory: verifies the freeze hash, refuses a second run per era, passes only frozen parameters to the injected fit (no retuning) and runs once.
Nothing here is executed on test or evaluation data under the current task."""
import json, hashlib, datetime
from pathlib import Path
import numpy as np

SIMPLICITY = ["gaussian_hmm", "bocpd", "student_t_hmm", "hsmm"]       # implementation choice for 'simpler model' (fewest parameters first); to be confirmed by amendment before use
EVAL_PREFIX = "evaluation_"                                            # evaluation outputs are files named evaluation_*.json in the results directory
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def h2_primary(passing, median_val_qlike):
    """passing: iterable of families that pass H1; median_val_qlike: family -> median validation QLIKE across folds. None if no family passes."""
    ps = [f for f in passing if f in median_val_qlike and np.isfinite(median_val_qlike[f])]
    if not ps: return None
    return sorted(ps, key=lambda f: (median_val_qlike[f], SIMPLICITY.index(f) if f in SIMPLICITY else len(SIMPLICITY)))[0]


def build_freeze(setups, thresholds, input_hashes, h1_verdicts, median_val_qlike, protocol_hash, amendments):
    passing = [f for f, v in h1_verdicts.items() if v.get("reject")]
    return dict(kind="section5_freeze", created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), protocol_sha256=protocol_hash, amendments=amendments,
                setups=setups, thresholds=thresholds, input_hashes=input_hashes, h1_verdicts=h1_verdicts, median_validation_qlike=median_val_qlike, h1_passing_families=passing,
                h2_primary_detector=h2_primary(passing, median_val_qlike))


def write_freeze(doc, results_dir, name="section5_freeze.json"):
    rd = Path(results_dir); out = rd / name
    if out.exists(): raise FileExistsError(f"{out} exists; a freeze is never overwritten")
    if list(rd.glob(EVAL_PREFIX + "*")): raise RuntimeError("evaluation output already exists; the freeze must precede it (5.12)")
    out.write_text(json.dumps(doc, indent=1, default=float), encoding="utf-8"); out.with_suffix(".sha256").write_text(f"{sha(out)}  {out.name}\n", encoding="ascii"); return out


def verify_freeze(path):
    p = Path(path); side = p.with_suffix(".sha256")
    if not side.exists() or side.read_text().split()[0] != sha(p): raise RuntimeError("freeze hash does not match its sidecar")
    return json.loads(p.read_text(encoding="utf-8"))


def run_confirmatory(freeze_path, results_dir, eras, fit_fn, run_fn, confirm_token):
    """5.13: for each era, refit the frozen setup on full TRAIN (fit_fn(era, setup, thresholds) -> model; only frozen values are passed) and run once on the exposed evaluation
    period (run_fn(era, model, setup, thresholds) -> dict). confirm_token must equal the freeze sha256 (explicit, deliberate invocation). A per-era marker blocks a second run."""
    fz = verify_freeze(freeze_path)
    if confirm_token != sha(freeze_path): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    rd = Path(results_dir); out = {}
    for era in eras:
        marker = rd / f"{EVAL_PREFIX}{era}_RAN.marker"
        if marker.exists(): raise RuntimeError(f"{era}: evaluation already run once; no re-run, no retuning (5.13)")
        marker.write_text(f"{sha(freeze_path)}\n", encoding="ascii")
        model = fit_fn(era, fz["setups"][era], fz["thresholds"][era]); res = run_fn(era, model, fz["setups"][era], fz["thresholds"][era]); out[era] = res
        (rd / f"{EVAL_PREFIX}{era}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
    return out
