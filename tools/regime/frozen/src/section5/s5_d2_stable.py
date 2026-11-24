"""D2 step 1: stable-day definition (fixed before any detector runs). Deseasonalised 1-min variance = r^2 / causal slot baseline (median of r^2 at the
same slot over the previous 20 sessions, >= 10 finite; the A4 F2 rule). Stable: first/second-half mean ratio in [0.8, 1.25] and no hourly block mean above 2x the median block mean."""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_eval as V
import step11_a4_rerun_4_3_4_7_8 as pstep

HALF = 195; BLOCKS = [(0, 60), (60, 120), (120, 180), (180, 240), (240, 300), (300, 360), (360, 390)]


def des_variance(d):
    r = np.where(d["valid"], d["r"], np.nan)
    return pstep.adjust(r ** 2, d["slot"], d["first"], d["end"])


def stable_days(d, sessions, dv):
    out, info = [], {}
    for i in sessions:
        a, b = int(d["first"][i]), int(d["end"][i])
        if b - a != 390 or np.isfinite(d["close"][a:b]).mean() < 0.98: info[int(i)] = "not full/clean"; continue
        x = dv[a:b]
        h1, h2 = np.nanmean(x[:HALF]), np.nanmean(x[HALF:]); blk = np.array([np.nanmean(x[s:e]) for s, e in BLOCKS])
        if not (np.isfinite(h1) and np.isfinite(h2) and h1 > 0 and h2 > 0 and np.isfinite(blk).all()): info[int(i)] = "undefined"; continue
        ratio = h2 / h1; ok = (0.8 <= ratio <= 1.25) and (blk.max() <= 2 * np.median(blk))
        info[int(i)] = dict(half_ratio=round(float(ratio), 3), max_block_over_median=round(float(blk.max() / np.median(blk)), 3), stable=bool(ok))
        if ok: out.append(int(i))
    return out, info


if __name__ == "__main__":
    primary, _, _ = L.pools(); d = L.load_era("RAW", primary + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
    dv = des_variance(d); st, info = stable_days(d, seg["val"], dv)
    print(len(seg["val"]), "validation sessions;", len(st), "stable"); print(st)
    json.dump(dict(stable=st, info=info), open(L.HERE / "results" / "d2_stable_days.json", "w"), indent=1)
