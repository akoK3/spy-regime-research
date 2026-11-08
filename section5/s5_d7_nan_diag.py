#!/usr/bin/env python3
"""D7 NaN-variance-ratio diagnosis (post hoc, LABEL_FREE: no detector, no model, no outcome). For each day that D7 under A21 skipped with an undefined variance ratio
(results/mr2/d7_a21/d7_results.json), rebuilds the day's tau exactly as s5_d7.fold_unit (same rng seed, same window rule) and reports why the weights w = 1 / slot baseline of r^2
(s5_fast.in_units_of_A, the D8 / __sadj construction) are undefined on the 60-bar window after tau: per bar, whether the causal slot median of r^2 over the previous 20 sessions is 0
(more than half of those minutes had a zero 1-min return), has fewer than 10 finite values, or the bar's own return is missing. Also: share of zero 1-min returns per era-year.
Usage: s5_d7_nan_diag.py      writes results/d7_nan_diag/d7_nan_diag.json"""
import sys, json, time, datetime, collections
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_lib as L, s5_eval as V, s5_d7 as D

HERE = Path(__file__).resolve().parent; SRC = HERE / "results" / "mr2" / "d7_a21" / "d7_results.json"; OUT = HERE / "results" / "d7_nan_diag" / "d7_nan_diag.json"
WINDOW, MIN_COUNT = 20, 10


def slot_baseline_parts(d, i, slots):
    """For session i and the given slots: number of finite r^2 over the previous 20 sessions, and their median (as pstep.adjust)."""
    r2 = np.where(d["valid"], d["r"], np.nan) ** 2; hs = list(range(max(0, i - WINDOW), i)); M = np.full((len(hs), 390), np.nan)
    for k, s in enumerate(hs):
        a, b = int(d["first"][s]), int(d["end"][s]); M[k, d["slot"][a:b]] = r2[a:b]
    cnt = np.isfinite(M[:, slots]).sum(0); med = np.array([np.nanmedian(M[:, s]) if c >= MIN_COUNT else np.nan for s, c in zip(slots, cnt)])
    zero_share = np.array([float(np.mean(M[np.isfinite(M[:, s]), s] == 0)) if c else np.nan for s, c in zip(slots, cnt)])
    return cnt, med, zero_share


def main():
    import s5_contamination as C
    C.check_registry(HERE); t0 = time.time(); src = json.loads(SRC.read_text(encoding="utf-8"))
    sk = [s for s in src["skipped"] if s["why"].startswith("undefined variance ratio")]; by_fold = collections.defaultdict(list)
    for s in sk: by_fold[s["fold"]].append(s["day"])
    d = L.load_era("LEGACY", []); days = np.array([str(d["day"][f]) for f in d["first"]]); rows = []
    for fold, dl in sorted(by_fold.items()):
        n = int(fold.split("|")[1])
        for day in dl:
            i = int(np.where(days == day)[0][0]); fa = int(d["first"][i]); p0 = L.sub_panel(d, [i]); rng = np.random.default_rng((D.SEED, 0, n, i)); g = None
            for _ in range(200):
                gg = int(rng.choice(V.TAU_SLOTS))
                if D.window_ok(p0, gg): g = gg; break
            J = np.arange(g + 1, g + D.WIN + 1); slots = d["slot"][fa + J]; cnt, med, zs = slot_baseline_parts(d, i, slots)
            r = p0["r"][J]; zero_base = (cnt >= MIN_COUNT) & (med == 0); few = cnt < MIN_COUNT; r_nan = ~np.isfinite(r)
            rows.append(dict(fold=fold, day=day, tau_slot=g, n_bad_bars=int((zero_base | few | r_nan).sum()), zero_median_bars=int(zero_base.sum()), few_count_bars=int(few.sum()), r_missing_bars=int(r_nan.sum()),
                             max_prev_zero_share=float(np.nanmax(zs)), day_zero_return_share=float(np.mean(p0["r"][1:390] == 0)), spy_close=float(p0["close"][g])))
    r = np.where(d["valid"], d["r"], np.nan); yr = np.array([str(d["day"][f])[:4] for f in d["first"]]); zy = {}
    for y in sorted(set(yr)):
        idx = np.concatenate([np.arange(d["first"][k], d["end"][k]) for k in np.where(yr == y)[0]]); x = r[idx]; x = x[np.isfinite(x)]; zy[y] = float(np.mean(x == 0))
    cause = collections.Counter("zero slot median" if x["zero_median_bars"] else "too few finite" if x["few_count_bars"] else "missing return" if x["r_missing_bars"] else "other" for x in rows)
    res = dict(label="D7 NaN-variance-ratio diagnosis (post hoc, LABEL_FREE)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), source_sha256=L.sha(SRC), n_days=len(rows),
               cause_counts=dict(cause), days=rows, legacy_zero_return_share_by_year=zy, seconds=round(time.time() - t0, 1))
    OUT.parent.mkdir(parents=True, exist_ok=True); OUT.write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(dict(cause=res["cause_counts"], n=len(rows)), indent=1)); return 0


if __name__ == "__main__":
    sys.exit(main())
