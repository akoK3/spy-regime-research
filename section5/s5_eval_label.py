#!/usr/bin/env python3
"""AMENDMENT_A34 rule 3b (FABLE_AUDIT L3): the A26 rule 1d label on every evaluation-period result, enforced outside the frozen result-module closure.
- run_confirmatory_labelled(...): the only sanctioned entry to 5.13. Wraps the caller's run_fn so that every per-era result carries a26_label and confirmatory = False
  before the 5.13 writer of s5_freeze (closure, unchanged) writes it. ACTIVE is True only while it runs.
- verify_labelled(results_dir): PermissionError if any evaluation-period result file (s5_freeze.EVAL_PREFIX*.json) lacks the label or claims confirmatory.
- ready(): the label equals the A26 rule 1d text in AMENDMENT_A26.md, and no script calls the 5.13 writer directly (direct_callers); called by
  s5_eval_loader.eval_guard before any evaluation-period read.
FABLE_REAUDIT M3 (2026-11-10), closed here without touching the closure:
  1. s5_eval_loader.eval_guard refuses a Section 5 evaluation-period read unless ACTIVE (the read happens inside run_confirmatory_labelled), so a direct call of the
     5.13 writer cannot read evaluation rows through the guarded loader;
  2. ready() refuses while any script in section5/, section6/ or the repository root calls the 5.13 writer directly (ALLOWED_CALLERS excepted: stubs and tests on
     temporary directories, no data);
  3. a run_fn result that is not a dict is wrapped, not refused, so the label step cannot fail after the one-shot marker is written (FABLE_REAUDIT L8).
Not closed (the closure cannot be edited): the 5.13 writer stays importable and callable; a caller that reads the panels without the guarded loader is outside this
module's reach (the contamination registry pattern covers that); tables, figures and sentences are labelled by hand.
No data is read here."""
import re, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
LABEL = "adaptive/exploratory (previously exposed period)"
ACTIVE = False                                  # True only inside run_confirmatory_labelled
WRITER_CALL = re.compile(r"\brun_confirmatory\b(?!_labelled)")      # PREFREEZE_AUDIT L4: any reference (a call with spaces, an alias, getattr by name), not only "run_confirmatory("
ALLOWED_CALLERS = ("section5/s5_freeze.py", "section5/s5_eval_label.py", "section5/s5_dry_run.py", "section5/s5_tests_build.py",      # definition; this wrapper; stub-only dry run and unit tests
                   "section5/s5_run.py", "section5/s5_machinery_run.py", "section5/write_amendment_a10.py")      # PREFREEZE_AUDIT L4: name mentioned in text only (closure docstring, temp-dir rehearsal, amendment writer)
TEST_FILE = re.compile(r"^(section5/|section6/)?s[56]_tests_[A-Za-z0-9_]+\.py$")      # unit tests patch the writer on temporary directories (no data)
SCAN = ((HERE, "section5/"), (ROOT / "section6", "section6/"), (ROOT, ""))


def direct_callers(scan=SCAN, allowed=ALLOWED_CALLERS):
    """Scripts that call the 5.13 writer directly (not through run_confirmatory_labelled)."""
    return sorted(pre + f.name for d, pre in scan if Path(d).exists() for f in Path(d).glob("*.py")
                  if pre + f.name not in allowed and not TEST_FILE.match(pre + f.name) and WRITER_CALL.search(f.read_text(encoding="utf-8", errors="ignore")))


def ready(root=ROOT):
    t = (Path(root) / "AMENDMENT_A26.md").read_text(encoding="utf-8")
    if f'"{LABEL}"' not in t: raise PermissionError("the A26 rule 1d label text was not found in AMENDMENT_A26.md")
    bad = direct_callers()
    if bad: raise PermissionError("scripts call the 5.13 writer directly instead of s5_eval_label.run_confirmatory_labelled: " + ", ".join(bad))
    return True


def label(res):
    if not isinstance(res, dict): res = dict(value=res)      # FABLE_REAUDIT L8: never raise after the one-shot marker
    return dict(res, a26_label=LABEL, confirmatory=False, period=res.get("period", "evaluation"))


def wrap_run_fn(run_fn):
    def run(era, model, setup, thresholds): return label(run_fn(era, model, setup, thresholds))
    return run


def run_confirmatory_labelled(freeze_path, results_dir, eras, fit_fn, run_fn, confirm_token):
    global ACTIVE
    import s5_freeze as FZ
    ready(); ACTIVE = True
    try: out = FZ.run_confirmatory(freeze_path, results_dir, eras, fit_fn, wrap_run_fn(run_fn), confirm_token)
    finally: ACTIVE = False
    verify_labelled(results_dir); return out


def verify_labelled(results_dir):
    import s5_freeze as FZ
    bad = []
    for p in sorted(Path(results_dir).glob(f"{FZ.EVAL_PREFIX}*.json")):
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("a26_label") != LABEL or d.get("confirmatory") is not False: bad.append(p.name)
    if bad: raise PermissionError("evaluation-period results without the A26 label (A34 rule 3b): " + ", ".join(bad))
    return True
