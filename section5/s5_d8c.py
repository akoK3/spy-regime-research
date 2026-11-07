#!/usr/bin/env python3
"""D8c (AMENDMENT_A22.md rule 1): descriptive overlap breakdown of large volatility, liquidity and jump changes on the D8 windows (same sessions, windows and statistics as D8,
via s5_d8.era_windows). No detector, no model, no outcome. Large volatility change: VR >= 2 or <= 0.5 (fixed in A22; the i.i.d. two-sided 1% points of F(60, 60) are 0.51 and 1.96).
Usage: s5_d8c.py [--check] [--out PATH]      --check: RAW era only, written to results/a22_preflight/d8c_preflight.json."""
import sys, json, time, datetime, itertools
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_d8 as D8

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = HERE / "results" / "d8" / "d8c_results.json"; PRE = HERE / "results" / "a22_preflight" / "d8c_preflight.json"
VOL_HI, VOL_LO = 2.0, 0.5                                                                  # A22 rule 1b
PRIMARY = ("volatility", "liquidity", "jumps"); ALL5 = ("volatility", "liquidity", "jumps", "trend", "momentum")


def flags(df):
    """Boolean large-change flags per window (NaN statistics count as not large)."""
    f = D8.large_flags(df)
    return dict(volatility=((df.VR >= VOL_HI) | (df.VR <= VOL_LO)).to_numpy(), liquidity=f["liquidity"].to_numpy(), jumps=f["jumps"].to_numpy(), trend=f["trend"].to_numpy(), momentum=f["momentum"].to_numpy())


def pattern_name(on): return "+".join(on) if on else "none"


def breakdown(fl, types):
    """Among windows with at least one large change of `types`: share of each single type alone and of each combination (two or more)."""
    M = np.column_stack([fl[t] for t in types]); anyl = M.any(1); n_any = int(anyl.sum()); k = M.sum(1)
    pats = {}
    for r in range(1, len(types) + 1):
        for combo in itertools.combinations(range(len(types)), r):
            want = np.zeros(len(types), bool); want[list(combo)] = True; c = int((M == want).all(1).sum())
            pats[pattern_name([types[i] for i in combo])] = dict(n=c, share_of_any=c / n_any if n_any else float("nan"))
    single = {f"{t}_only": pats[t] for t in types}
    comb = dict(n=int((k >= 2).sum()), share_of_any=float((k >= 2).sum() / n_any) if n_any else float("nan"))
    return dict(n_windows=int(len(M)), n_any_large=n_any, share_any_large=float(n_any / len(M)) if len(M) else float("nan"), single=single, combined=comb,
                combined_patterns={p: v for p, v in pats.items() if "+" in p}, all_patterns=pats)


def report(df):
    fl = flags(df); nonvol = fl["liquidity"] | fl["jumps"] | fl["trend"] | fl["momentum"]
    sec = breakdown(fl, ALL5)
    sec["nonvol_large_without_large_volatility"] = dict(n=int((nonvol & ~fl["volatility"]).sum()), share_of_nonvol_large=float((nonvol & ~fl["volatility"]).sum() / nonvol.sum()) if nonvol.any() else float("nan"))
    sec["per_type_without_large_volatility"] = {t: float((fl[t] & ~fl["volatility"]).sum() / fl[t].sum()) if fl[t].any() else float("nan") for t in ALL5[1:]}
    return dict(primary=breakdown(fl, PRIMARY), secondary_5_types=sec, large_shares={t: float(fl[t].mean()) for t in ALL5}, sessions=int(df.sess.nunique()))


def main():
    import s5_contamination as C
    check = "--check" in sys.argv[1:]; out = Path(sys.argv[sys.argv.index("--out") + 1]) if "--out" in sys.argv else (PRE if check else OUT)
    C.check_registry(HERE); t0 = time.time(); eras = ("RAW",) if check else ("LEGACY", "RAW"); frames = []
    res = dict(label="D8c descriptive overlap breakdown (AMENDMENT_A22.md rule 1); no detector, no model, no outcome", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               amendment_sha256=D8.L.sha(ROOT / "AMENDMENT_A22.md"), d8_script_sha256=D8.L.sha(HERE / "s5_d8.py"), thresholds=dict(volatility=[VOL_LO, VOL_HI], d8=D8.LARGE), eras={})
    for era in eras:
        df, info = D8.era_windows(era); frames.append(df); res["eras"][era] = info | report(df); print(era, info, len(df), f"{time.time() - t0:.0f}s", flush=True)
    if len(frames) > 1: res["pooled"] = report(pd.concat(frames, ignore_index=True))
    res["seconds"] = round(time.time() - t0, 1); out.parent.mkdir(parents=True, exist_ok=True); out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    p = res.get("pooled", res["eras"][eras[-1]])["primary"]
    print("primary (share of windows with any large vol/liq/jump change):", {k: round(v["share_of_any"], 3) for k, v in p["single"].items()}, "combined", round(p["combined"]["share_of_any"], 3), flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
