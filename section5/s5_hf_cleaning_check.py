#!/usr/bin/env python3
"""LABEL-FREE check of HF Data Library cleaning (user request 2026-11-10). Compares SPY Raw and Clean one-minute files of the SAME release, kept outside the study
data, over 2022-03-07..2024-12-23, 09:30-15:59 ET. No study file, panel, feature, detector output or label is read; no result module is imported.
Reports:
  1. bars removed (in Raw, not in Clean), added (in Clean, not in Raw) and changed (same timestamp, any OHLCV field differs), by count and share; per-field changes;
     removals attributed to HF's documented steps 2-7 (deterministic on Raw) and the residual (step 8 candidates: the 50-bar centered Brownlees-Gallo filter).
  2. Reversal test: for each Raw bar t with a nonzero move into it, r_t = log(C_t / C_prev) (previous Raw bar of the session), and the forward move
     R_{t,k} = log(C_{t+k} / C_t) over the next k = 1..5 Raw bars of the session. Reversal = sign(R_{t,k}) = -sign(r_t); strong reversal = -R_{t,k} / r_t >= 0.5.
     Removed and changed bars are compared with kept bars OF SIMILAR SIZE: bins of |r_t| from the kept bars' quantiles (0, 10, ..., 90, 95, 99, 99.9 pct, open top);
     the difference is the flagged-count-weighted mean over bins of (flagged rate - kept rate), with a 95% percentile interval from a day-cluster bootstrap (999).
     A clearly positive difference means the filter removes bars that later reverse, i.e. it likely uses later bars.
Usage: s5_hf_cleaning_check.py --raw RAW_FILE --clean CLEAN_FILE [--out DIR]
  RAW_FILE / CLEAN_FILE: a .zip containing SPY_raw_1min.csv / SPY_clean_1min.csv, or the .csv itself. Both must be from the same release (release dates in the
  file names must agree when present) and must not be the study's input files. Output (written once): DIR/hf_cleaning_spy.json (default section5/results/hf_cleaning)."""
import sys, re, io, json, zipfile, hashlib, datetime
from pathlib import Path
import numpy as np, pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
LO, HI = "2022-03-07", "2024-12-23"; K = (1, 2, 3, 4, 5); NBOOT = 999
STUDY_INPUTS = [ROOT / "hfdatalibrary_clean_1min_5tickers_2026-10-03.zip", ROOT / "hfdatalibrary_raw_1min_1tickers_2026-10-13.zip",
                ROOT / "hfdatalibrary_raw_1min_2tickers_2026-10-15.zip", Path.home() / "OneDrive" / "Desktop" / "data" / "raw"]
HF_DOC = dict(source="https://hfdatalibrary.com/pages/docs", read="2026-11-10",
              clean_steps=["1 remove bars outside 09:30-16:00 ET", "2 remove bars with Open, High, Low or Close <= 0", "3 remove bars with High < Low",
                           "4 remove bars with Open or Close outside [Low, High]", "5 remove duplicate timestamps, keep first", "6 remove bars with zero volume",
                           "7 remove bars with |log return| > 25% relative to the previous close (backward-looking)",
                           "8 Brownlees-Gallo: remove bars with |close - median| > 3 x MAD over a 50-bar CENTERED window (uses later bars)"],
              notes="steps applied in order; a bar failing any step is removed; prices split-adjusted only; the page does not describe Filled; Raw is described on a separate Data Versions page")


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def release_date(p):
    m = re.search(r"(\d{4}-\d{2}-\d{2})", Path(p).name); return m.group(1) if m else None


def load(p, kind):
    p = Path(p)
    def chunks(f):      # PREFREEZE_AUDIT L5: rows outside LO..HI (e.g. 2025-2026, the RAW evaluation period) are discarded chunk by chunk while streaming, never kept
        for ch in pd.read_csv(f, chunksize=200_000):
            ch.columns = [c.strip() for c in ch.columns]; dd = ch["datetime"].astype(str).str[:10]; keep = (dd >= LO) & (dd <= HI)
            if keep.any(): yield ch.loc[keep]
    if p.suffix.lower() == ".zip":
        with zipfile.ZipFile(p) as z:
            name = next((n for n in z.namelist() if n.lower().endswith(f"spy_{kind}_1min.csv")), None)
            if name is None: raise SystemExit(f"SPY_{kind}_1min.csv not found in {p.name}")
            with z.open(name) as f: df = pd.concat(list(chunks(f)), ignore_index=True)
    else: df = pd.concat(list(chunks(p)), ignore_index=True)
    df["datetime"] = pd.to_datetime(df["datetime"])
    d = df["datetime"].dt.strftime("%Y-%m-%d"); hm = df["datetime"].dt.hour * 60 + df["datetime"].dt.minute
    return df[(d >= LO) & (d <= HI) & (hm >= 570) & (hm <= 959)].sort_values("datetime", kind="stable").reset_index(drop=True)


def documented_reason(raw):
    """HF steps 2-7 on Raw, in order (step 1 is the window, already applied); the first failing step, or '' (step 8 / unexplained)."""
    x = raw; r = np.full(len(x), "", dtype=object)
    def setr(mask, name):
        m = mask & (r == ""); r[m] = name
    setr(((x[["Open", "High", "Low", "Close"]] <= 0).any(axis=1)).to_numpy(), "2_nonpositive")
    setr((x["High"] < x["Low"]).to_numpy(), "3_high_below_low")
    setr(((x["Open"] < x["Low"]) | (x["Open"] > x["High"]) | (x["Close"] < x["Low"]) | (x["Close"] > x["High"])).to_numpy(), "4_ohlc_range")
    setr(x["datetime"].duplicated(keep="first").to_numpy(), "5_duplicate")
    setr((x["Volume"] == 0).to_numpy(), "6_zero_volume")
    ok = r == ""; c = x["Close"].to_numpy(float); lr = np.full(len(x), np.nan); idx = np.flatnonzero(ok)
    if len(idx) > 1: lr[idx[1:]] = np.log(c[idx[1:]] / c[idx[:-1]])
    setr(np.abs(lr) > 0.25, "7_logret_gt_25pct")
    return r


def compare(raw, clean):
    rd = raw.drop_duplicates("datetime", keep="first").set_index("datetime"); cd = clean.drop_duplicates("datetime", keep="first").set_index("datetime")
    both = rd.index.intersection(cd.index); removed = rd.index.difference(cd.index); added = cd.index.difference(rd.index)
    f = ["Open", "High", "Low", "Close", "Volume"]; a = rd.loc[both, f].to_numpy(float); b = cd.loc[both, f].to_numpy(float)
    diff = ~np.isclose(a, b, rtol=1e-9, atol=1e-9); changed_mask = diff.any(axis=1)
    return both, removed, added, both[changed_mask], {fld: int(diff[:, j].sum()) for j, fld in enumerate(f)}


def moves(raw):
    """Per Raw bar (duplicates after the first dropped): session day, r_t and R_{t,k} within the session."""
    x = raw.drop_duplicates("datetime", keep="first").reset_index(drop=True); day = x["datetime"].dt.strftime("%Y-%m-%d").to_numpy(); c = np.log(x["Close"].to_numpy(float))
    n = len(x); r = np.full(n, np.nan); same = np.r_[False, day[1:] == day[:-1]]; r[same] = c[1:][same[1:]] - c[:-1][same[1:]]
    F = {}
    for k in K:
        f = np.full(n, np.nan); ok = np.r_[day[k:] == day[:-k], np.zeros(k, bool)] if n > k else np.zeros(n, bool); f[ok] = c[k:][ok[:n - k]] - c[:-k][ok[:n - k]]; F[k] = f
    return x["datetime"].to_numpy(), day, r, F


def reversal_test(dt, day, r, F, flagged, kept, seed=0):
    """Weighted (by flagged count per |r| bin) difference of reversal rates, flagged minus kept, with a day-cluster bootstrap interval."""
    use = np.isfinite(r) & (r != 0); kq = np.abs(r[kept & use])
    if len(kq) < 100 or (flagged & use).sum() < 10: return dict(n_flagged=int((flagged & use).sum()), note="too few bars")
    edges = np.unique(np.quantile(kq, [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 0.95, 0.99, 0.999])); b = np.searchsorted(edges, np.abs(r), side="right"); nb = len(edges) + 1
    days, di = np.unique(day, return_inverse=True); out = dict(n_flagged=int((flagged & use).sum()), n_kept=int((kept & use).sum()),
                                                              n_flagged_above_kept_max=int(((flagged & use) & (np.abs(r) > kq.max())).sum()), bins=int(nb), by_k={})
    rng = np.random.default_rng(seed); boot_days = rng.integers(0, len(days), (NBOOT, len(days)))
    for k in K:
        g = use & np.isfinite(F[k]); rev = (np.sign(F[k]) == -np.sign(r)); strong = (-F[k] / np.where(r == 0, np.nan, r)) >= 0.5; res = {}
        for name, ind in (("reversal", rev), ("strong_reversal", strong)):
            def tab(mask):      # per day x bin: totals and events
                t = np.zeros((len(days), nb)); e = np.zeros((len(days), nb)); m = mask & g
                np.add.at(t, (di[m], b[m]), 1); np.add.at(e, (di[m], b[m]), ind[m].astype(float)); return t, e
            tf, ef = tab(flagged); tk, ek = tab(kept)
            def stat(w):
                Tf = (w[:, None] * tf).sum(0); Ef = (w[:, None] * ef).sum(0); Tk = (w[:, None] * tk).sum(0); Ek = (w[:, None] * ek).sum(0)
                ok = (Tf > 0) & (Tk > 0)
                if not ok.any(): return np.nan, np.nan, np.nan
                rf = Ef[ok] / Tf[ok]; rk = Ek[ok] / Tk[ok]; wt = Tf[ok] / Tf[ok].sum(); return float((wt * (rf - rk)).sum()), float((wt * rf).sum()), float((wt * rk).sum())
            d0, rf0, rk0 = stat(np.ones(len(days))); bs = []
            for s in boot_days:
                w = np.bincount(s, minlength=len(days)).astype(float); v = stat(w)[0]
                if np.isfinite(v): bs.append(v)
            lo, hi = (np.percentile(bs, [2.5, 97.5]) if bs else (np.nan, np.nan))
            res[name] = dict(flagged_rate=rf0, kept_rate_same_size=rk0, difference=d0, ci95=[float(lo), float(hi)], n_flagged_used=int((flagged & g).sum()))
        out["by_k"][str(k)] = res
    return out


def main():
    a = sys.argv[1:]
    if "--raw" not in a or "--clean" not in a: print(__doc__); return 3
    rawp, cleanp = Path(a[a.index("--raw") + 1]).resolve(), Path(a[a.index("--clean") + 1]).resolve()
    outd = Path(a[a.index("--out") + 1]) if "--out" in a else HERE / "results" / "hf_cleaning"; out_p = outd / "hf_cleaning_spy.json"
    for p in (rawp, cleanp):
        if any(p == s.resolve() or s.resolve() in p.parents for s in STUDY_INPUTS): raise SystemExit(f"{p} is a study input; use fresh downloads kept outside the study data")
    if release_date(rawp) and release_date(cleanp) and release_date(rawp) != release_date(cleanp): raise SystemExit(f"different releases: {release_date(rawp)} vs {release_date(cleanp)}")
    if out_p.exists(): print("result exists; written once"); return 3
    raw, clean = load(rawp, "raw"), load(cleanp, "clean")
    both, removed, added, changed, by_field = compare(raw, clean); nr, nc = int(raw["datetime"].nunique()), int(clean["datetime"].nunique())
    reason = documented_reason(raw); rr = pd.Series(reason, index=raw["datetime"]); rr = rr[~rr.index.duplicated(keep="first")]
    rem_reason = rr.loc[removed].replace("", "8_or_unexplained").value_counts().to_dict()
    dt, day, r, F = moves(raw); s_rem = np.isin(dt, removed.to_numpy()); s_chg = np.isin(dt, changed.to_numpy()); kept = ~s_rem & ~s_chg
    rem8 = s_rem & np.isin(dt, rr[rr == ""].index.intersection(removed).to_numpy())
    res = dict(label="LABEL-FREE vendor check (HF Data Library Raw vs Clean, SPY); no study data, no result module", window=dict(dates=[LO, HI], times="09:30-15:59 ET"),
               inputs=dict(raw=dict(file=rawp.name, sha256=sha(rawp), release=release_date(rawp)), clean=dict(file=cleanp.name, sha256=sha(cleanp), release=release_date(cleanp))),
               counts=dict(raw_bars=nr, clean_bars=nc, raw_duplicate_rows=int(len(raw) - nr), clean_duplicate_rows=int(len(clean) - nc), sessions_raw=int(raw["datetime"].dt.date.nunique()),
                           removed=int(len(removed)), removed_share_of_raw=len(removed) / nr if nr else None, added=int(len(added)), added_share_of_clean=len(added) / nc if nc else None,
                           changed=int(len(changed)), changed_share_of_raw=len(changed) / nr if nr else None, changed_by_field=by_field, removed_by_documented_step=rem_reason,
                           raw_source_values=raw["source"].astype(str).value_counts().to_dict() if "source" in raw else None,
                           clean_source_values=clean["source"].astype(str).value_counts().to_dict() if "source" in clean else None),
               reversal=dict(removed_all=reversal_test(dt, day, r, F, s_rem, kept), removed_step8_or_unexplained=reversal_test(dt, day, r, F, rem8, kept),
                             changed=reversal_test(dt, day, r, F, s_chg, kept),
                             definition="reversal: sign of the next-k-bar move opposite to the move into the bar; strong: at least half of the move undone; size-matched by |r| bins of kept bars; day-cluster bootstrap 999"),
               hf_documentation=HF_DOC, generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), script_sha256=sha(__file__))
    outd.mkdir(parents=True, exist_ok=True); out_p.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); out_p.with_suffix(".sha256").write_text(f"{sha(out_p)}  {out_p.name}\n", encoding="ascii")
    print(json.dumps(dict(counts=res["counts"], reversal_k1=res["reversal"]["removed_all"].get("by_k", {}).get("1")), indent=1, default=float)); return 0


if __name__ == "__main__": sys.exit(main())
