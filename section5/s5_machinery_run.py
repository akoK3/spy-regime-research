#!/usr/bin/env python3
"""A10/A12 machinery check: the full glue (s5_run.run_all + freeze step) on ONE contaminated fold (RAW 3 or LEGACY 29), with runtime and memory. Usage: s5_machinery_run.py ERA FOLD
No selection result or test statistic from this run enters any protocol decision. The freeze is written in a temporary directory and discarded; run_confirmatory is never called."""
import sys, json, time, tempfile, threading, math
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_run as RUN, s5_backend as BK, s5_legacy_pilot as LP

HERE = Path(__file__).resolve().parent; TAG = sys.argv[3] if len(sys.argv) > 3 else "a12"      # run tag: results of earlier tags stay as the record of the earlier code


class Timed:
    """Wraps backend methods with wall-clock accumulation per method."""
    def __init__(self, b): self._b = b; self.t = {}; self.n = {}
    def __getattr__(self, name):
        a = getattr(self._b, name)
        if not callable(a) or name.startswith("_"): return a
        def w(*x, **k):
            t0 = time.perf_counter(); r = a(*x, **k)
            if name in ("objective",):                                  # objective returns a closure: time its calls
                inner = r
                def g(*y, **z):
                    t1 = time.perf_counter(); v = inner(*y, **z); self.t["objective_calls"] = self.t.get("objective_calls", 0) + time.perf_counter() - t1; self.n["objective_calls"] = self.n.get("objective_calls", 0) + 1; return v
                return g
            self.t[name] = self.t.get(name, 0) + time.perf_counter() - t0; self.n[name] = self.n.get(name, 0) + 1; return r
        return w


def finite_tree(x, path="", bad=None):
    bad = [] if bad is None else bad
    if isinstance(x, dict):
        for k, v in x.items(): finite_tree(v, f"{path}/{k}", bad)
    elif isinstance(x, (list, tuple)):
        for i, v in enumerate(x[:2000]): finite_tree(v, f"{path}[{i}]", bad)
    elif isinstance(x, float) and not math.isfinite(x): bad.append(path)
    return bad


def main(era, fold):
    T0 = time.time(); log = lambda m: print(f"[{(time.time()-T0)/60:5.1f} min] {m}", flush=True); peak = [0.0]; minfree = [1e9]; stop = threading.Event()
    def samp():
        while not stop.is_set():
            try:
                v = LP.peak_mb(); peak[0] = max(peak[0], v or 0.0); minfree[0] = min(minfree[0], LP.free_mb())
            except Exception: pass
            time.sleep(2)
    threading.Thread(target=samp, daemon=True).start()
    b = Timed(BK.DataBackend(era, fold)); out_dir = HERE / "results" / f"{TAG}_machinery_{era}{fold}"; res = dict(era=era, fold=fold, failures=[])
    t0 = time.time(); b._b.c; res["load_and_features_s"] = round(time.time() - t0, 1); log(f"context built ({res['load_and_features_s']} s)")
    try:
        s1 = RUN.run_all(b, out_dir, excluded=set(), nboot=1000); res["run_s"] = round(time.time() - T0, 1); log("run_all done")
        s2 = RUN.run_all(b, out_dir, excluded=set(), nboot=1000); res["resume"] = dict(first=s1["checkpoint"], second=s2["checkpoint"]); log("resume check done")
        with tempfile.TemporaryDirectory() as td: p, doc = RUN.freeze_step(b, s1, Path(td), "machinery-check-not-a-freeze", ["A10"]); res["freeze_step"] = dict(written_in_tempdir=True, h2_primary=doc["h2_primary_detector"], passing=doc["h1_passing_families"])
        pf = s1["_per_fold"]; fid = f"{era}|{fold}"
        res["setups"] = {fam: dict(features=pf[fam][fid]["setup"]["features"], params=pf[fam][fid]["setup"]["params"], val_qlike=pf[fam][fid]["setup"]["val_qlike"], base_qlike=pf[fam][fid]["setup"]["base_qlike"],
                                   budget_exhausted=pf[fam][fid]["setup"]["budget_exhausted"], n_steps=len(pf[fam][fid]["setup"]["trace"])) for fam in pf}
        fits = [(k[0], getattr(m, "fit_info", None)) for k, m in b._b._fits.items()]; em = [(f, i) for f, i in fits if i and i.get("converged")]
        res["em_fits"] = dict(n_models=len(em), n_starts=sum(len(i["converged"]) for _, i in em), n_starts_reaching_cap=sum(1 for _, i in em for c in i["converged"] if not c), iterations_median=float(np.median([x for _, i in em for x in i["iterations"]])) if em else None,
                              by_family={f: dict(starts=sum(len(i["converged"]) for g, i in em if g == f), at_cap=sum(1 for g, i in em if g == f for c in i["converged"] if not c)) for f in sorted({f for f, _ in em})})
        res["scores"] = {fam: pf[fam][fid]["score"] for fam in pf}; res["skipped_h1a"] = s1["skipped_h1a"]; res["tests_note"] = "one fold per call: fold-level tests not evaluable (n<2); no H1 verdict is read"
        res["holm_confirmatory_is_not_evaluable"] = all(not np.isfinite(v["p"]) for v in s1["holm"]["confirmatory"].values())
        res["non_finite_outputs"] = finite_tree({k: v for k, v in res.items() if k != "scores"}) + finite_tree(res["scores"])
        res["n_stable_test"] = pf["gaussian_hmm"][fid]["score"]["a"] is not None
    except Exception as e:
        import traceback; res["failures"].append(traceback.format_exc()); log("FAILED: " + str(e))
    stop.set(); res["backend_seconds"] = {k: round(v, 1) for k, v in b.t.items()}; res["backend_calls"] = b.n; res["peak_memory_mb"] = round(peak[0], 0); res["min_free_system_mb"] = round(minfree[0], 0); res["total_minutes"] = round((time.time() - T0) / 60, 2)
    (HERE / "results" / f"{TAG}_machinery_{era}{fold}.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); log(f"done; failures {len(res['failures'])}; peak {res['peak_memory_mb']} MB")


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]))
