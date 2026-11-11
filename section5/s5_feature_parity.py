#!/usr/bin/env python3
"""PREFREEZE_AUDIT M2 (LABEL_FREE; development data only): the feature path of the frozen models and of every evaluation score (s5_eval513._load_span +
s5_eval513.context: s5_lib.compute_features on a fresh load of the panel) against the main-run era context (s5_backend.era_context: the development caches), on
each era's TRAIN span. Compared: the session days, every A20-pool column and lee_mykland_approx60 (NaN masks equal, values equal within 1e-10 relative), the
deseasonalised QLIKE target dv, the 5-minute return matrix Mx, and every session's native grid rows (X, availability). No detector, model or outcome.
Used now (`run`) and inside the freeze driver (s5_freeze_run, before any model is fitted).
Usage: s5_feature_parity.py run      Output (written once): section5/results/feature_parity.json"""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE))
RTOL = 1e-10; ATOL = 1e-12


def _cmp(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    if a.shape != b.shape: return dict(equal=False, why=f"shape {a.shape} vs {b.shape}")
    fa, fb = np.isfinite(a), np.isfinite(b); both = fa & fb
    same = bool(np.array_equal(fa, fb)); close = bool(np.allclose(a[both], b[both], rtol=RTOL, atol=ATOL)); mx = float(np.max(np.abs(a[both] - b[both]))) if both.any() else 0.0
    return dict(equal=same and close, nan_mask_equal=same, allclose=close, max_abs_diff=mx, n=int(a.size), n_finite=int(both.sum()))


def parity(era, ctx_main=None, ctx_513=None):
    """dict(passed, fields) for one era. Either context may be passed in (the freeze driver reuses what it built)."""
    import s5_backend as BK, s5_eval513 as S513, s5_eval_loader as EL
    m = ctx_main or BK.era_context(era)
    if ctx_513 is None: EL.check_dev_spans(); ctx_513 = S513.context(era, S513._load_span(era, *EL.DEV[era]))
    e = ctx_513; dm, de = m["d"], e["d"]; out = dict(era=era, fields={})
    days_m = [str(dm["day"][i]) for i in dm["first"]]; days_e = [str(de["day"][i]) for i in de["first"]]
    out["sessions"] = dict(equal=days_m == days_e, n_main=len(days_m), n_513=len(days_e), first=days_e[:1], last=days_e[-1:])
    out["columns_equal"] = list(m["cols"]) == list(e["cols"])
    if out["sessions"]["equal"] and out["columns_equal"]:
        for c in list(m["cols"]) + ["lee_mykland_approx60"]: out["fields"][c] = _cmp(dm["features"][c], de["features"][c])
        out["fields"]["dv"] = _cmp(m["dv"], e["dv"]); out["fields"]["Mx"] = _cmp(m["Mx"], e["Mx"])
        same_row = lambda x, y: set(x) == set(y) and all(_cmp(x[k], y[k])["equal"] if np.asarray(x[k]).dtype.kind in "fiu" else np.array_equal(np.asarray(x[k]), np.asarray(y[k])) for k in x)
        bad = [i for i, (x, y) in enumerate(zip(m["native"], e["native"])) if not same_row(x, y)]
        out["fields"]["native_grid_rows"] = dict(equal=not bad, n_sessions_differing=len(bad), first_differing=[days_e[i] for i in bad[:5]])
    out["passed"] = bool(out["sessions"]["equal"] and out["columns_equal"] and out["fields"] and all(v["equal"] for v in out["fields"].values()))
    return out


def main():
    a = sys.argv[1:]
    if a[:1] != ["run"]: print(__doc__); return 3
    p = HERE / "results" / "feature_parity.json"
    if p.exists(): print("result exists; written once"); return 3
    import s5_guard as G, gc
    res = dict(label="PREFREEZE_AUDIT M2: 5.13 feature path vs main-run era context, TRAIN spans (LABEL_FREE)", code_version=G.code_version(), eras={})
    for era in ("RAW", "LEGACY"): res["eras"][era] = parity(era); gc.collect(); print(era, res["eras"][era]["passed"], flush=True)
    res["passed"] = all(v["passed"] for v in res["eras"].values()); res["generated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    p.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); G.write_side(p); print(json.dumps({e: dict(passed=v["passed"], bad=[k for k, f in v["fields"].items() if not f["equal"]]) for e, v in res["eras"].items()}))
    return 0 if res["passed"] else 1


if __name__ == "__main__": sys.exit(main())
