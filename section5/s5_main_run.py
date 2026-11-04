#!/usr/bin/env python3
"""Main run of Section 5 (A15 rule 5, A16): MainBackend over all 34 folds -> s5_run.run_all (checkpointed, one process, resumable). Stops after run_all has written the completion
record: no freeze, no era calibration. Progress is appended with timestamps to results/main_run_log.txt. Never asks questions.
Usage: s5_main_run.py PROTOCOL_SHA256 [--check]
  --check: preflight only (protocol token, canonical contamination list, lock, registry, backend construction, output directory, resume state); reads no market data, scores nothing.
Exit codes: 0 done (or preflight passed); 2 stopped with Ctrl+C (not retried); 3 guard refusal (not retryable: protocol, contamination list, lock, registry, bad token); 1 any other error (retryable: resume from checkpoints)."""
import sys, os, time, json, ctypes, datetime, platform, shutil, traceback
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent; LOG = HERE / "results" / "main_run_log.txt"; OUT = HERE / "results" / "main_run"


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def keep_awake(on=True):
    """Windows: keep the system out of sleep while the run is active (ES_CONTINUOUS | ES_SYSTEM_REQUIRED); the display may still turn off."""
    try: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | (0x00000001 if on else 0))
    except Exception: pass


class Logged:
    """Wraps the main backend: logs every fold switch and every selection/scoring unit with its duration. Results are unchanged (pure pass-through)."""
    def __init__(self, b, n_folds): self._b = b; self._n = n_folds; self._seen = []
    def __getattr__(self, name): return getattr(self._b, name)

    def _fold(self, fold):
        if fold not in self._seen: self._seen.append(fold); log(f"fold {len(self._seen)}/{self._n} {fold}: start")

    def objective(self, fold, family):
        self._fold(fold); log(f"  {fold} {family}: selection start"); t0 = time.time(); f = self._b.objective(fold, family); self._t0 = t0; return f

    def score(self, fold, family, setup):
        self._fold(fold); t_sel = getattr(self, "_t0", None); self._t0 = None
        sel = f"selection done ({(time.time() - t_sel) / 60:.1f} min)" if t_sel else "selection from checkpoint"
        log(f"  {fold} {family}: {sel}; features {setup['features']} params {setup['params']} baseline {setup['base_params']}; scoring start")
        t0 = time.time(); r = self._b.score(fold, family, setup); log(f"  {fold} {family}: scoring done ({(time.time() - t0) / 60:.1f} min)"); return r


def preflight(token):
    import s5_guard as G, s5_contamination as C, s5_main as MB
    ph = G.verify_frozen_protocol(token); log(f"preflight: protocol FROZEN, sidecar matches, token = {ph[:16]}...")
    _, ch = G.canonical_contamination(); excl, _ = G.excluded_folds(); log(f"preflight: canonical contamination list {ch[:16]}..., {len(excl)} folds excluded, {34 - len(excl)} confirmatory")
    if G.LOCK.exists(): raise PermissionError(f"{G.LOCK} exists: era calibration has run; scoring is refused (A16 rule 5)")
    log("preflight: no era-calibration lock"); C.check_registry(HERE); log("preflight: every data-loading script is registered")
    b = MB.MainBackend(ph); assert b._era is None and b._cur is None, "backend loaded data during construction"
    log(f"preflight: MainBackend built ({len(b.folds())} folds, {b.folds()[0]} ... {b.folds()[-1]}); no data loaded")
    OUT.mkdir(parents=True, exist_ok=True); probe = OUT / ".write_probe"; probe.write_text("ok"); probe.unlink()
    cv = G.code_version(); n_ck = len(list((OUT / "ckpt").glob("*.json"))) if (OUT / "ckpt").exists() else 0
    log(f"preflight: output {OUT} writable; code version {cv}; checkpoint version {G.checkpoint_version(cv, ph)}; existing checkpoint units {n_ck} of {34 * 4 * 2}")
    if (OUT / G.COMPLETION).exists(): log("preflight: NOTE a completion record already exists in the output directory (a finished run; run_all would only re-read checkpoints)")
    import numpy, scipy, pandas
    du = shutil.disk_usage(OUT); log(f"preflight: python {platform.python_version()} at {sys.executable}; numpy {numpy.__version__}, scipy {scipy.__version__}, pandas {pandas.__version__}; free disk {du.free / 2**30:.1f} GB")
    try:
        import s5_legacy_pilot as LP; log(f"preflight: free memory {LP.free_mb():.0f} MB (rehearsal peak 1027 MB)")
    except Exception: pass
    return ph, b


def main():
    if len(sys.argv) < 2: print("usage: s5_main_run.py PROTOCOL_SHA256 [--check]"); return 3
    token, check = sys.argv[1], "--check" in sys.argv[2:]; LOG.parent.mkdir(parents=True, exist_ok=True)
    try:
        ph, b = preflight(token)
    except (PermissionError, RuntimeError, AssertionError) as e:
        log(f"REFUSED (not retryable): {type(e).__name__}: {e}"); return 3
    if check: log("preflight passed (--check): main run NOT started"); return 0
    import s5_run as RUN, s5_guard as G
    keep_awake(True); t0 = time.time(); log(f"main run: start (resumes from existing checkpoints in {OUT})")
    try:
        s = RUN.run_all(Logged(b, len(b.folds())), OUT)
        rec = G.verify_completion(OUT / G.COMPLETION, require_main=True)
        log(f"main run: DONE in {(time.time() - t0) / 3600:.2f} h; checkpoint hits {s['checkpoint']['hits']}, misses {s['checkpoint']['misses']}; completion record verified "
            f"(sha256 {G.sha(OUT / G.COMPLETION)[:16]}..., results {rec['results_sha256'][:16]}...); H1(a) failures {sum(len(v) for v in s['failed_h1a'].values())}; no freeze, no era calibration")
        return 0
    except PermissionError as e:
        log(f"REFUSED (not retryable): PermissionError: {e}"); return 3
    except KeyboardInterrupt:
        log(f"STOPPED by the user (Ctrl+C) after {(time.time() - t0) / 60:.1f} min; finished units are checkpointed; not retried"); return 2
    except BaseException as e:
        log(f"CRASH after {(time.time() - t0) / 60:.1f} min: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return 1
    finally:
        keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
