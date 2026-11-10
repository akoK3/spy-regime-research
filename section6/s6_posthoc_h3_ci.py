#!/usr/bin/env python3
"""POST-HOC REPORTING ONLY (user request 2026-11-10, after the Section 6 development run): the AMENDMENT_A29 rule 3b interval for H3 next-day gamma, TLT and gold,
Gaussian HMM and HSMM. No test is changed, added or re-run; the H3 p-values, Holm and BH results of s6_development_DETECTOR.json stand as written.
Rebuilds the H3 rows exactly as s6_run.analyse / h3_test do (same units, placebos and seeds, development data only through s6_run.load_era), checks that gamma equals
the stored development-run gamma, then computes the two-sided 95% basic week-block bootstrap interval (s6_lib.week_block_ci: within-era calendar-week blocks,
9,999 resamples, seed 0 as in the primary H3 test). A29 3b: an interval wholly below 0 is reported as a transient cross-asset response, never as a calming effect.
Output (written once): section6/results/posthoc/h3_ci_a29_3b.json.   Usage: s6_posthoc_h3_ci.py"""
import sys, json, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R

ASSETS = ("TLT", "GOLD"); DETS = ("gaussian_hmm", "hsmm")


def h3_rows(E_by, units, a):
    """Exactly the rows of s6_run.h3_test(..., outcome="next_day", off=0, ph_end="T")."""
    ys, Xs, bs, days, eras = [], [], [], [], []
    for u in units:
        E = E_by[u["era"]]
        for b, (di, S, T) in [(1, (u["day_idx"], u["S"], u["T"]))] + [(0, (p["day_idx"], p["S"], p["T"])) for p in u["placebos"]]:
            r = R.h3_row(E, a, di, S, T, "next_day", 0, "T")
            if r is None or not np.isfinite(r["y"]) or not np.isfinite(r["X"]).all(): continue
            ys.append(r["y"]); Xs.append(r["X"]); bs.append(b); days.append(E.days[di]); eras.append(u["era"])
    return np.array(ys), np.array(Xs), np.array(bs, float), days, eras


def main():
    R.a29_guard()
    out_p = R.OUT / "posthoc" / "h3_ci_a29_3b.json"
    if out_p.exists(): print("result exists; written once"); return 3
    E_by = {era: R.load_era(era, "development") for era in ("LEGACY", "RAW")}
    res = dict(label="POST-HOC REPORTING ONLY (user request 2026-11-10): A29 rule 3b interval for H3 next-day gamma; no test changed; development data",
               interval="two-sided 95% basic week-block bootstrap (within era), 9,999 resamples, seed 0", by_detector={})
    for det in DETS:
        rows, sess = R.load_breaks(det); stored = json.loads((R.OUT / f"s6_development_{det}.json").read_text(encoding="utf-8"))["primary"]; units = []
        for era, E in E_by.items():
            u, c, al = R.build(E, rows, sess); units += R.attach_placebos(u, c, al)
        R.fed_flags(units); br, _ = R.unit_lists(units); d = {}
        for a in ASSETS:
            y, X, b, days, eras = h3_rows(E_by, br, a)
            g0 = L.ols_gamma(y, X, b); gs = stored[f"H3_{a}"]["gamma"]
            if not (np.isclose(g0, gs, rtol=0, atol=1e-10) and int(b.sum()) == stored[f"H3_{a}"]["n_breaks"]): raise SystemExit(f"{det} {a}: rebuilt gamma {g0} / n {int(b.sum())} differ from the stored {gs} / {stored[f'H3_{a}']['n_breaks']}")
            t, lo, hi, nv = L.week_block_ci(lambda ix: L.ols_gamma(y[ix], X[ix], b[ix]), days, eras, L.NBOOT, 0)
            d[a] = dict(gamma=t, ci95=[lo, hi], n_valid_resamples=nv, n_breaks=int(b.sum()), n_placebos=int(len(b) - b.sum()), stored_gamma=gs, stored_p_one_sided=stored[f"H3_{a}"]["p"],
                        wholly_below_0=bool(np.isfinite(hi) and hi < 0),
                        a29_3b_reading=("transient cross-asset response (A29 3b): same-day asset moves that the next day does not continue beyond the prior-hour control; not a calming effect"
                                        if np.isfinite(hi) and hi < 0 else "interval includes 0: no A29 3b reading"))
            print(det, a, json.dumps(d[a]), flush=True)
        res["by_detector"][det] = d
    res.update(generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=R.provenance())
    p = R.write_once(out_p, res); print(f"written {p}"); return 0


if __name__ == "__main__": sys.exit(main())
