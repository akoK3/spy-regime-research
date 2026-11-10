#!/usr/bin/env python3
"""AMENDMENT_A34 rule 3b (FABLE_AUDIT L3): the A26 rule 1d label on every evaluation-period result, enforced outside the frozen result-module closure.
- run_confirmatory_labelled(...): the only sanctioned entry to 5.13. Wraps the caller's run_fn so that every per-era result carries a26_label and confirmatory = False
  before s5_freeze.run_confirmatory (closure, unchanged) writes it.
- verify_labelled(results_dir): PermissionError if any evaluation-period result file (s5_freeze.EVAL_PREFIX*.json) lacks the label or claims confirmatory.
- ready(): the label equals the A26 rule 1d text in AMENDMENT_A26.md (called by s5_eval_loader.eval_guard before any evaluation-period read).
No data is read here."""
import json
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
LABEL = "adaptive/exploratory (previously exposed period)"


def ready(root=ROOT):
    t = (Path(root) / "AMENDMENT_A26.md").read_text(encoding="utf-8")
    if f'"{LABEL}"' not in t: raise PermissionError("the A26 rule 1d label text was not found in AMENDMENT_A26.md")
    return True


def label(res):
    if not isinstance(res, dict): raise TypeError("an evaluation-period result must be a dict")
    return dict(res, a26_label=LABEL, confirmatory=False, period=res.get("period", "evaluation"))


def wrap_run_fn(run_fn):
    def run(era, model, setup, thresholds): return label(run_fn(era, model, setup, thresholds))
    return run


def run_confirmatory_labelled(freeze_path, results_dir, eras, fit_fn, run_fn, confirm_token):
    import s5_freeze as FZ
    ready(); out = FZ.run_confirmatory(freeze_path, results_dir, eras, fit_fn, wrap_run_fn(run_fn), confirm_token)
    verify_labelled(results_dir); return out


def verify_labelled(results_dir):
    import s5_freeze as FZ
    bad = []
    for p in sorted(Path(results_dir).glob(f"{FZ.EVAL_PREFIX}*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("a26_label") != LABEL or d.get("confirmatory") is not False: bad.append(p.name)
    if bad: raise PermissionError("evaluation-period results without the A26 label (A34 rule 3b): " + ", ".join(bad))
    return True
