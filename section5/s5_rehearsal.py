#!/usr/bin/env python3
"""Rehearsal of the main-run path (s5_main.MainBackend -> s5_run.run_all -> s5_run.freeze_step) on the contaminated folds only (LEGACY 29, RAW 3). Machinery check under 5.16.
It cannot produce a valid main completion record: backend kind 'rehearsal' and 2 folds (s5_guard.verify_completion(require_main=True) refuses both). Clean folds are refused (fold backends
are built without the protocol token). The era step is a stub: no EraBackend, no era fit, no lock. The freeze is written in a temporary directory and discarded.
Records wall-clock time per backend call and per fold, peak memory, failures and the projected full-run time. Usage: s5_rehearsal.py  ->  results/rehearsal_a16.json"""
import sys, json, time, tempfile, threading, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_main as MB, s5_backend as BK, s5_guard as G, s5_run as RUN, s5_legacy_pilot as LP

HERE = Path(__file__).resolve().parent; FOLDS = ["LEGACY|29", "RAW|3"]; OUT = HERE / "results" / "rehearsal_a16"


class RehearsalBackend(MB.MainBackend):
    kind = "rehearsal"

    def __init__(self):
        self.protocol_sha256 = G.frozen_protocol_hash(); excluded, _ = G.excluded_folds()
        assert set(FOLDS) <= excluded and set(FOLDS) <= BK.ALLOWED_MACHINERY, "rehearsal folds must be contaminated machinery folds"
        self.ids = list(FOLDS); self._era = None; self._cur = None; self._era_b = None; self.t = {}; self.n = {}

    def _b(self, fold):
        if fold not in FOLDS: raise PermissionError(f"rehearsal serves {FOLDS} only")
        if self._cur is None or self._cur.id != fold:
            era, n = fold.split("|"); self._cur = None; t0 = time.perf_counter(); ctx = self._ctx(era); self._acc("era_context", era, time.perf_counter() - t0)
            self._cur = BK.DataBackend(era, int(n), shared=ctx)                    # no protocol token: a clean fold would raise
        return self._cur

    def _acc(self, what, fold, dt): k = f"{what}|{fold}"; self.t[k] = self.t.get(k, 0.0) + dt; self.n[k] = self.n.get(k, 0) + 1

    def objective(self, fold, family):
        f = super().objective(fold, family)
        def g(*a, **k): t0 = time.perf_counter(); v = f(*a, **k); self._acc("objective_calls", fold, time.perf_counter() - t0); return v
        return g

    def score(self, fold, family, setup):
        t0 = time.perf_counter(); v = super().score(fold, family, setup); self._acc("score", fold, time.perf_counter() - t0); return v

    def era_thresholds(self, era, family, setup, completion):
        return dict(stub=True, era=era, family=family, note="rehearsal: era calibration not run (no EraBackend, no fit, no lock)")


def main():
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True); peak = [0.0]; minfree = [1e9]; stop = threading.Event()
    def samp():
        while not stop.is_set():
            try: peak[0] = max(peak[0], LP.peak_mb() or 0.0); minfree[0] = min(minfree[0], LP.free_mb())
            except Exception: pass
            time.sleep(2)
    threading.Thread(target=samp, daemon=True).start()
    res = dict(folds=FOLDS, failures=[], lock_before=G.LOCK.exists()); b = RehearsalBackend(); fit_t = {}
    orig_fit = BK.DataBackend.fit
    def timed_fit(self, family, subset, params, starts):
        key = (family, tuple(subset), tuple(sorted(params.items())), starts); new = key not in self._fits; t0 = time.perf_counter(); m = orig_fit(self, family, subset, params, starts)
        if new: k = f"{self.id}|{family}|starts={starts}"; fit_t.setdefault(k, []).append(time.perf_counter() - t0)
        return m
    BK.DataBackend.fit = timed_fit
    try:
        s1 = RUN.run_all(b, OUT, nboot=1000); res["run_minutes"] = round((time.time() - T0) / 60, 2); log("run_all done")
        t1 = time.time(); s2 = RUN.run_all(b, OUT, nboot=1000); res["resume"] = dict(first=s1["checkpoint"], second=s2["checkpoint"], seconds=round(time.time() - t1, 1)); log("resume done")
        rec = Path(s1["completion_record"])
        try: G.verify_completion(rec, require_main=True); res["completion_record_valid_as_main"] = True
        except PermissionError as e: res["completion_record_valid_as_main"] = False; res["completion_record_refused_because"] = str(e)
        try: G.verify_completion(rec, require_main=False); res["completion_record_hash_checked"] = True
        except PermissionError as e: res["completion_record_hash_checked"] = str(e)
        with tempfile.TemporaryDirectory() as td:
            t1 = time.time(); _, doc = RUN.freeze_step(b, s1, Path(td), ["A16 rehearsal"]); res["freeze_step"] = dict(written_in_tempdir_and_discarded=True, seconds=round(time.time() - t1, 1),
                thresholds_are_stubs=all(v.get("stub") for e in doc["thresholds"].values() for v in e.values()), n_input_hashes=len(doc["input_hashes"]), protocol_sha256=doc["protocol_sha256"])
        try: b._b("LEGACY|0"); res["clean_fold_refused"] = False
        except PermissionError: res["clean_fold_refused"] = True
        pf = s1["_per_fold"]
        res["setups"] = {fam: {f: dict(features=pf[fam][f]["setup"]["features"], params=pf[fam][f]["setup"]["params"], base_params=pf[fam][f]["setup"]["base_params"]) for f in FOLDS} for fam in pf}
        res["scores"] = {fam: {f: {k: pf[fam][f]["score"][k] for k in ("a", "a_skipped", "a_failed", "b", "b_n", "flagged_fit")} for f in FOLDS} for fam in pf}
        res["non_finite"] = [f"{fam}|{f}|{k}" for fam in pf for f in FOLDS for k in ("a", "b") if pf[fam][f]["score"][k] is not None and not np.isfinite(pf[fam][f]["score"][k])]
    except Exception:
        res["failures"].append(traceback.format_exc()); log("FAILED")
    finally:
        BK.DataBackend.fit = orig_fit
    stop.set(); res["lock_after"] = G.LOCK.exists(); res["backend_seconds"] = {k: round(v, 1) for k, v in sorted(b.t.items())}; res["backend_calls"] = b.n
    res["new_fit_seconds"] = {k: dict(n=len(v), total=round(sum(v), 1), median=round(float(np.median(v)), 2)) for k, v in sorted(fit_t.items())}
    res["peak_memory_mb"] = round(peak[0]); res["min_free_system_mb"] = round(minfree[0]); res["total_minutes"] = round((time.time() - T0) / 60, 2)
    per_fold = {f: sum(v for k, v in b.t.items() if k.endswith("|" + f) or k == f"era_context|{f.split('|')[0]}") / 60 for f in FOLDS}
    res["fold_minutes"] = {f: round(v, 1) for f, v in per_fold.items()}
    (HERE / "results" / "rehearsal_a16.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); log(f"done; failures {len(res['failures'])}; peak {res['peak_memory_mb']} MB")


if __name__ == "__main__":
    main()
