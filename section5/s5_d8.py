#!/usr/bin/env python3
"""D8 (AMENDMENT_A19.md rule 1): descriptive census of non-volatility changes. No detector, no model, no outcome. Post-embargo VALIDATION sessions of all 34 folds, each session once
per era, 390 bars and >= 98% finite closes. 60-min windows W = [s, s+60) against P = [s-60, s), s = 60, 65, ..., 330. Writes section5/results/d8/d8_results.json."""
import sys, json, time, datetime
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_d2_stable as S
import step11_a4_rerun_4_3_4_7_8 as pstep

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "d8"
STARTS = np.arange(60, 331, 5); MIN_FINITE = 50
LARGE = dict(trend=3.64, momentum=0.47, vol_hi=2.0, vol_lo=0.5, jump=1)      # A19 rule 1e
BAND = (0.8, 1.25); OCCURS = 0.02                                           # A19 rules 1e, 1f
Q = (50, 90, 99)


def tstat(x):
    x = x[np.isfinite(x)]
    if len(x) < MIN_FINITE: return np.nan
    s = x.std(ddof=1); return float(np.sqrt(60) * x.mean() / s) if s > 0 else np.nan


def rho1(x):
    a, b = x[:-1], x[1:]; ok = np.isfinite(a) & np.isfinite(b)
    if ok.sum() < MIN_FINITE - 1: return np.nan
    a, b = a[ok] - a[ok].mean(), b[ok] - b[ok].mean(); d = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / d) if d > 0 else np.nan


def ratio(w, p):
    if np.isfinite(w).sum() < MIN_FINITE or np.isfinite(p).sum() < MIN_FINITE: return np.nan
    x, y = np.nanmean(w), np.nanmean(p); return float(x / y) if x > 0 and y > 0 else np.nan


def windows(r, dv, dvol, jump):
    """One session's arrays (390 rows) -> list of window records."""
    out = []
    for s in STARTS:
        W, P = slice(s, s + 60), slice(s - 60, s)
        if np.isfinite(r[W]).sum() < MIN_FINITE or np.isfinite(r[P]).sum() < MIN_FINITE: continue
        tw, tp = tstat(r[W]), tstat(r[P]); jw, jp = np.nansum(jump[W]), np.nansum(jump[P])
        out.append(dict(s=int(s), VR=ratio(dv[W], dv[P]), VOL=ratio(dvol[W], dvol[P]), tW=tw, dt=tw - tp, drho=rho1(r[W]) - rho1(r[P]), JW=float(jw), dJ=float(jw - jp)))
    return out


def large_flags(df):
    return dict(trend=df.dt.abs() >= LARGE["trend"], momentum=df.drho.abs() >= LARGE["momentum"], liquidity=(df.VOL >= LARGE["vol_hi"]) | (df.VOL <= LARGE["vol_lo"]), jumps=df.dJ >= LARGE["jump"])


def summarise(df):
    pct = lambda x: {f"p{q}": float(np.nanpercentile(x, q)) for q in Q} | dict(n=int(np.isfinite(x).sum()))
    dist = dict(VR=pct(df.VR), inv_VR=pct(1 / df.VR), VOL=pct(df.VOL), inv_VOL=pct(1 / df.VOL), abs_tW=pct(df.tW.abs()), abs_dt=pct(df.dt.abs()), abs_drho=pct(df.drho.abs()),
                JW=pct(df.JW), dJ=pct(df.dJ), median_signed=dict(tW=float(np.nanmedian(df.tW)), dt=float(np.nanmedian(df.dt)), drho=float(np.nanmedian(df.drho)), log_VR=float(np.nanmedian(np.log(df.VR))), log_VOL=float(np.nanmedian(np.log(df.VOL)))))
    stable = (df.VR >= BAND[0]) & (df.VR <= BAND[1]); fl = large_flags(df); share = {}
    for k, f in fl.items():
        share[k] = dict(large=float(f.mean()), large_and_variance_stable=float((f & stable).mean()), large_given_variance_stable=float(f[stable].mean()), variance_stable_given_large=float(stable[f].mean()) if f.any() else None, n_large=int(f.sum()))
    return dict(windows=len(df), sessions=int(df.sess.nunique()), variance_stable_share=float(stable.mean()), distributions=dist, large_shares=share)


def era_windows(era):
    d = L.load_era(era, ["lee_mykland_approx60"]); s3 = L._step3(); jump = s3.construct_deferred(d)["lee_mykland_jump60"]
    dv = S.des_variance(d); vol = np.where(np.isfinite(d["volume"]) & (d["volume"] >= 0), d["volume"].astype(float), np.nan); dvol = pstep.adjust(vol, d["slot"], d["first"], d["end"])
    nf = int(pd.read_csv(L.R / "a4_development_nested_folds_TRAIN.csv").query("era == @era").fold.max()) + 1; val = set()
    for f in range(nf): val.update(int(i) for i in L.fold_segments(d, era, f)["val"])
    used, recs = [], []
    for i in sorted(val):
        a, b = int(d["first"][i]), int(d["end"][i])
        if b - a != 390 or np.isfinite(d["close"][a:b]).mean() < 0.98: continue
        r = np.where(d["valid"][a:b], d["r"][a:b], np.nan); used.append(i)
        for w in windows(r, dv[a:b], dvol[a:b], jump[a:b]): w["sess"] = f"{era}:{d['day'][a]}"; recs.append(w)
    return pd.DataFrame(recs), dict(folds=nf, validation_sessions=len(val), sessions_used=len(used))


def main():
    import s5_contamination as C; C.check_registry(HERE); OUT.mkdir(parents=True, exist_ok=True); t0 = time.time(); res = dict(label="D8 descriptive census (AMENDMENT_A19.md rule 1); no detector, no model, no outcome",
        generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment_sha256=L.sha(L.ROOT / "AMENDMENT_A19.md"), thresholds=dict(large=LARGE, variance_band=BAND, occurs=OCCURS), eras={})
    frames = []
    for era in ("LEGACY", "RAW"):
        df, info = era_windows(era); frames.append(df); res["eras"][era] = info | summarise(df); print(era, info, len(df), f"{time.time() - t0:.0f}s", flush=True)
    res["pooled"] = summarise(pd.concat(frames, ignore_index=True))
    res["occurs"] = {k: all(res["eras"][e]["large_shares"][k]["large_given_variance_stable"] >= OCCURS for e in ("LEGACY", "RAW")) for k in ("trend", "momentum", "liquidity", "jumps")}
    res["seconds"] = round(time.time() - t0, 1)
    (OUT / "d8_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(json.dumps(res["occurs"]))


if __name__ == "__main__":
    main()
