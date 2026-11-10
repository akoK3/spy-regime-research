#!/usr/bin/env python3
"""LABEL-FREE diagnosis of the HYG data gap (user request 2026-11-10): why E1 (A32 4c) and the A32 deseasonalised |return| statistic use far fewer HYG breaks
than the H2 primary (A33). Counts only: for each break / placebo window, the first condition that makes it unusable (window past the close, asset unavailable in
the session, no finite one-minute return in the window, fewer than 10 earlier sessions with data, all-flat median window, fewer than 10 usable placebos), and per
asset and year the shares of finite and of exactly-zero one-minute returns and of flat 30-minute windows. No break-versus-placebo comparison, no return level,
no test, no change to any H2 code; TLT and gold are counted the same way for contrast. Development data only (s6_run.load_era).
Output (written once): section6/results/hyg_gap/hyg_gap.json.   Usage: s6_hyg_gap.py"""
import sys, json, csv, collections, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_h2 as H

ASSETS = ("TLT", "HYG", "GOLD"); W = 30


def dz_reason(E, a, di, t0, t1):
    """The first reason s6_h2.dz would be undefined, else 'ok' (same conditions, same order)."""
    if t0 < 0 or t1 > L.N_MIN: return "outside_regular_hours"
    if not E.avail[a][di]: return "asset_unavailable"
    Q, N, _ = H._pref(E, a)
    if N[di, t1] - N[di, t0] == 0: return "no_finite_return_in_window"
    rows = np.arange(max(0, di - H.PRIOR), di); rows = rows[E.avail[a][rows] & ((N[rows, t1] - N[rows, t0]) > 0)]
    if len(rows) < H.MIN_PRIOR: return "fewer_than_10_prior_sessions_with_data"
    return "median_prior_window_all_flat" if float(np.median(Q[rows, t1] - Q[rows, t0])) <= 0 else "ok"


def move_reason(E, a, di, t0, t1):
    """Per-window condition of s6_h2.move (break or reference window)."""
    if t1 > L.N_MIN: return "outside_regular_hours"
    if not E.avail[a][di]: return "asset_unavailable"
    _, N, _ = H._pref(E, a)
    return "no_finite_return_in_window" if N[di, t1] - N[di, t0] == 0 else "ok"


def main():
    out_p = R.OUT / "hyg_gap" / "hyg_gap.json"
    if out_p.exists(): print("result exists; written once"); return 3
    allrows = list(csv.DictReader(open(R.BREAKS / "breaks.csv", encoding="utf-8")))
    for x in allrows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    sess = json.loads((R.BREAKS / "sessions.json").read_text(encoding="utf-8"))
    E_by = {era: R.load_era(era, "development") for era in ("LEGACY", "RAW")}; res = dict(label=__doc__.split("\n")[0], by_detector={})
    for det in ("gaussian_hmm", "hsmm"):
        rows = [x for x in allrows if x["family"] == det]; c2s, _, _ = H.units50(E_by, rows, sess); br = H.units_for(E_by, rows, sess); d = {}
        for a in ASSETS:
            prim = collections.Counter(move_reason(E_by[u["era"]], a, u["day_idx"], u["T"], u["T"] + W) for u in c2s)
            brk = collections.Counter(); plc = collections.Counter(); npl_ok = []; final = collections.Counter(); e1 = collections.Counter(); e1_ref = collections.Counter()
            for u in br:
                E = E_by[u["era"]]; r = dz_reason(E, a, u["day_idx"], u["T"], u["T"] + W); brk[r] += 1
                pr = [dz_reason(E, a, p["day_idx"], p["T"], p["T"] + W) for p in u["placebos"]]; plc.update(pr); k = sum(x == "ok" for x in pr)
                if r == "ok": npl_ok.append(k)
                final[r if r != "ok" else ("fewer_than_10_usable_placebos" if k < H.MIN_PLACEBO else "used")] += 1
                m = move_reason(E, a, u["day_idx"], u["T"], u["T"] + W); refs = [move_reason(E, a, p["day_idx"], p["T"], p["T"] + W) for p in u["placebos"]]; e1_ref.update(refs)
                e1[m if m != "ok" else ("fewer_than_10_reference_windows" if sum(x == "ok" for x in refs) < H.MIN_PLACEBO else "evaluable")] += 1
            d[a] = dict(h2_primary_break_window=dict(prim), a32_breaks=dict(n=len(br), final=dict(final), break_window=dict(brk), placebo_windows=dict(plc),
                        usable_placebos_per_usable_break=(dict(zip(("p10", "p50", "p90"), map(float, np.percentile(npl_ok, [10, 50, 90])))) if npl_ok else None)),
                        e1_breaks=dict(final=dict(e1), reference_windows=dict(e1_ref)))
        res["by_detector"][det] = d
    q = {}
    for a in ASSETS:
        q[a] = {}
        for era, E in E_by.items():
            X = E.R[a]; Q, N, _ = H._pref(E, a); yrs = np.array([d[:4] for d in E.days])
            for y in sorted(set(yrs)):
                s = np.flatnonzero((yrs == y) & E.avail[a])
                if len(s) == 0: continue
                fin = np.isfinite(X[s]); z = fin & (X[s] == 0); st = np.arange(L.STEP, L.N_MIN - W + 1, L.STEP)
                n30 = N[np.ix_(s, st + W)] - N[np.ix_(s, st)]; q30 = Q[np.ix_(s, st + W)] - Q[np.ix_(s, st)]
                q[a][f"{era}|{y}"] = dict(n_available_sessions=int(len(s)), share_finite_minutes=float(fin.mean()), share_zero_among_finite=float(z.sum() / max(fin.sum(), 1)),
                                          share_30min_windows_no_data=float((n30 == 0).mean()), share_30min_windows_all_flat=float(((n30 > 0) & (q30 <= 0)).mean()))
    res["data_quality_by_asset_era_year"] = q; res.update(generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), provenance=H.provenance())
    R.write_once(out_p, res); print(json.dumps(res["by_detector"], indent=1)); return 0


if __name__ == "__main__": sys.exit(main())
