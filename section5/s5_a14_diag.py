#!/usr/bin/env python3
"""Diagnostic for audit finding 19 (Student-t HMM restart on a state under 1% occupancy), contaminated folds RAW 3 and LEGACY 29, inner-train fits only, no scoring.
Fits the Student-t HMM (K=3, 1 start, seed 0, as in the greedy search) for the return-only model and for each single candidate feature, and reports restarts and whether the kept fit has all states >= 1%.
Usage: s5_a14_diag.py ERA FOLD  ->  results/a14_student_t_occupancy_<ERA><FOLD>.json"""
import sys, json, time
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_backend as BK

HERE = Path(__file__).resolve().parent


def main(era, fold, K=3):
    b = BK.DataBackend(era, fold); cands = [()] + [(c,) for c in b.candidates(b.id)]; out = []
    for sub in cands:
        t0 = time.time(); m = b.fit("student_t_hmm", sub, dict(K=K), 1); fi = m.fit_info
        out.append(dict(subset=list(sub), restarts=int(fi["restarts"]), occupancy=[round(float(x), 4) for x in m._occ], all_states_at_least_1pct=bool((m._occ >= 0.01).all()), exhausted_10_attempts=bool(fi["restarts"] >= 10), iterations=fi["iterations"], seconds=round(time.time() - t0, 1)))
    res = dict(era=era, fold=fold, K=K, n_fits=len(out), n_with_restart=sum(1 for o in out if o["restarts"] > 0), n_exhausted=sum(o["exhausted_10_attempts"] for o in out), n_kept_with_small_state=sum(not o["all_states_at_least_1pct"] for o in out), fits=out)
    (HERE / "results" / f"a14_student_t_occupancy_{era}{fold}_K{K}.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print({k: v for k, v in res.items() if k != "fits"})


if __name__ == "__main__":
    main(sys.argv[1], int(sys.argv[2]), int(sys.argv[3]) if len(sys.argv) > 3 else 3)
