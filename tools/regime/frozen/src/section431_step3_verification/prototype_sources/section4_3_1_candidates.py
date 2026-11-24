"""Development-only, causal Section 4.3.1 candidate feature construction.

Run with the existing Downloads/research_hmm_env Python. No HMM is fitted.
The protocol hash is checked before reading numeric data. Source CSVs stay intact.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import warnings
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

MINUTE = 60_000_000_000
WINDOWS = (5, 10, 15, 30, 60)
PANEL_COLUMNS = ["utc_minute_start_assumed", "available_utc_assuming_minute_start",
                 "session_date_ny", "minute_index_in_session", "source_epoch",
                 "SPY_log_return_1m", "SPY_return_eligible"]
ETF_COLUMNS = ["utc_minute_start", "session_date_ny", "Close", "High", "Low",
               "Volume", "numeric_ohlcv_valid"]


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def require(value, message):
    if not value:
        raise AssertionError(message)


def ns(values):
    return pd.DatetimeIndex(pd.to_datetime(values, utc=True)).as_unit("ns").asi8


def selected_csv(path, columns, first, last):
    # Gzip streams must be decoded; chunks outside development are discarded
    # before feature construction. No target-return columns are requested.
    chunks = []
    for chunk in pd.read_csv(path, usecols=columns, chunksize=100_000):
        keep = chunk.session_date_ny.between(first, last)
        if keep.any():
            chunks.append(chunk.loc[keep])
    require(bool(chunks), f"No development rows: {path}")
    return pd.concat(chunks, ignore_index=True)


def load_development(era, spec):
    first, last = spec["first_session"], spec["last_session"]
    p = selected_csv(spec["panel_file"], PANEL_COLUMNS, first, last)
    e = selected_csv(spec["etf_file"], ETF_COLUMNS, first, last)
    require(p.source_epoch.eq(era).all(), "Mixed source eras")
    t = ns(p.utc_minute_start_assumed)
    available = ns(p.available_utc_assuming_minute_start)
    day = p.session_date_ny.to_numpy(str)
    slot = p.minute_index_in_session.to_numpy(int)
    r = p.SPY_log_return_1m.to_numpy(float)
    require(p.SPY_return_eligible.isin([0, 1]).all(), "Nonbinary return mask")
    valid = p.SPY_return_eligible.to_numpy(bool)
    require(np.array_equal(np.isfinite(r), valid), "Return/mask mismatch")
    require((np.diff(t) > 0).all(), "Duplicate/out of order panel timestamps")
    require((available == t + MINUTE).all(), "Availability not bar close")
    a = np.flatnonzero(np.r_[True, day[1:] != day[:-1]])
    b = np.r_[a[1:], len(t)]
    require(not valid[a].any(), "Session-open return is present")
    for lo, hi in zip(a, b):
        require(np.array_equal(slot[lo:hi], np.arange(hi-lo)), "Broken session grid")
        require(hi-lo in (210, 390), "Unexpected session length")
        require((np.diff(t[lo:hi]) == MINUTE).all(), "Nonconsecutive calendar grid")
    local = pd.DatetimeIndex(pd.to_datetime(t[a], utc=True)).tz_convert("America/New_York")
    require(all(x.hour == 9 and x.minute == 30 for x in local), "Incorrect RTH open")
    require(np.array_equal(np.array([str(x.date()) for x in local]), day[a]), "Session date mismatch")
    te = ns(e.utc_minute_start)
    require((np.diff(te) > 0).all(), "Duplicate/out of order ETF timestamps")
    j = pd.Index(t).get_indexer(te)
    require((j >= 0).all(), "Observed ETF row outside calendar grid")
    require(np.array_equal(e.session_date_ny.to_numpy(str), day[j]), "ETF date mismatch")
    close, high, low, volume = (e[c].to_numpy(float) for c in ["Close", "High", "Low", "Volume"])
    require((e.numeric_ohlcv_valid.to_numpy() == 1).all(), "Invalid audited ETF row")
    require((np.isfinite(close) & np.isfinite(high) & np.isfinite(low) & np.isfinite(volume)
             & (low > 0) & (high >= close) & (close >= low) & (volume >= 0)).all(), "Bad OHLCV")
    c, rg, vol = (np.full(len(t), np.nan) for _ in range(3))
    c[j], rg[j], vol[j] = close, np.log(high / low), volume
    ii = np.flatnonzero(valid)
    require((slot[ii] > 0).all(), "Return across session open")
    require(np.isfinite(c[ii]).all() and np.isfinite(c[ii-1]).all(), "Return without two prices")
    require(np.allclose(r[ii], np.log(c[ii]/c[ii-1]), rtol=1e-10, atol=1e-12), "Return not exact adjacent closes")
    require(day[0] == first and day[-1] == last, "Unexpected development endpoints")
    return dict(era=era, t=t, available=available, day=day, slot=slot, r=r,
                valid=valid, close=c, range=rg, volume=vol, first=a, end=b)


def relative_volume(d):
    mat = np.full((len(d["first"]), 390), np.nan)
    for k, (a, b) in enumerate(zip(d["first"], d["end"])):
        v = d["volume"][a:b]
        mat[k, d["slot"][a:b]] = np.where(v > 0, v, np.nan)
    baseline, count = np.full(len(d["r"]), np.nan), np.zeros(len(d["r"]), np.int16)
    for k, (a, b) in enumerate(zip(d["first"], d["end"])):
        prev = mat[max(0, k-20):k]
        n = np.isfinite(prev).sum(axis=0)
        med = np.full(390, np.nan)
        good = n >= 10
        if good.any():
            med[good] = np.nanmedian(prev[:, good], axis=0)
        baseline[a:b], count[a:b] = med[d["slot"][a:b]], n[d["slot"][a:b]]
    out = np.full(len(baseline), np.nan)
    # A real zero current volume has ratio 0 when a positive past baseline exists.
    good = np.isfinite(d["volume"]) & (d["volume"] >= 0) & (baseline > 0)
    out[good] = d["volume"][good] / baseline[good]
    return out, baseline, count


def construct(d):
    r, ok, slot, c = (d[k] for k in ["r", "valid", "slot", "close"])
    f = {"return_1m": r.copy(), "abs_return_1m": np.abs(r),
         "intrabar_range_log": d["range"].copy(), "raw_volume": d["volume"].copy()}
    with np.errstate(divide="ignore", invalid="ignore"):
        f["log_raw_volume"] = np.where(d["volume"] > 0, np.log(d["volume"]), np.nan)
    rel, baseline, nprior = relative_volume(d)
    f["relative_volume20"] = rel
    with np.errstate(divide="ignore", invalid="ignore"):
        f["log_relative_volume20"] = np.where(rel > 0, np.log(rel), np.nan)
    quality = {"relative_volume_prior_count": nprior, "relative_volume_baseline": baseline}
    for w in WINDOWS:
        for key in [f"rv{w}_strict", f"downside{w}_strict", f"momentum{w}_strict",
                    f"rv{w}_partial90", f"momentum{w}_endpoint"]:
            f[key] = np.full(len(r), np.nan)
        quality[f"n_return_obs_{w}"] = np.zeros(len(r), np.int16)
    f["downside15_partial90"] = np.full(len(r), np.nan)
    f["rv60_sampled5_exact"] = np.full(len(r), np.nan)
    f["shock_prior60_mad"] = np.full(len(r), np.nan)
    for a, b in zip(d["first"], d["end"]):
        x = np.where(ok[a:b], r[a:b], 0.)
        cumul = lambda v: np.r_[0., np.cumsum(v)]
        sums, sq, dsq, counts = (cumul(z) for z in [x, x*x, np.minimum(x, 0)**2, ok[a:b]])
        for w in WINDOWS:
            j = np.arange(w, b-a)
            n = counts[j+1] - counts[j-w+1]
            q = np.maximum(0., sq[j+1] - sq[j-w+1])
            dq = np.maximum(0., dsq[j+1] - dsq[j-w+1])
            quality[f"n_return_obs_{w}"][a+j] = n
            full, partial = n == w, n >= int(np.ceil(.9*w))
            f[f"rv{w}_strict"][a+j[full]] = np.sqrt(q[full])
            f[f"downside{w}_strict"][a+j[full]] = np.sqrt(dq[full])
            f[f"momentum{w}_strict"][a+j[full]] = (sums[j+1] - sums[j-w+1])[full]
            f[f"rv{w}_partial90"][a+j[partial]] = np.sqrt(q[partial]*w/n[partial])
            if w == 15:
                f["downside15_partial90"][a+j[partial]] = np.sqrt(dq[partial]*w/n[partial])
            ep = np.isfinite(c[a+j]) & np.isfinite(c[a+j-w])
            f[f"momentum{w}_endpoint"][a+j[ep]] = np.log(c[a+j[ep]] / c[a+j[ep]-w])
        j = np.arange(60, b-a)
        endpoints = np.stack([c[a+j-z] for z in range(0, 61, 5)], axis=1)
        full = np.isfinite(endpoints).all(axis=1)
        z = np.diff(np.log(endpoints[full]), axis=1)
        f["rv60_sampled5_exact"][a+j[full]] = np.sqrt((z*z).sum(axis=1))
        # Strict 60 previous returns plus current return. Current r is excluded
        # from the MAD reference; flat history leaves scale unavailable.
        if b-a > 61:
            windows = np.lib.stride_tricks.sliding_window_view(r[a:b], 61)[1:]
            j = np.arange(61, b-a)
            full = np.isfinite(windows).all(axis=1)
            past = windows[full, :60]
            med = np.median(past, axis=1)
            scale = 1.4826*np.median(np.abs(past-med[:, None]), axis=1)
            usable = scale > 0
            f["shock_prior60_mad"][a+j[full][usable]] = (windows[full, 60][usable]-med[usable])/scale[usable]
    return f, quality


def feature_warmup(name):
    if name == "shock_prior60_mad":
        return 61
    if name.startswith(("rv", "downside", "momentum")):
        import re
        return int(re.search(r"\d+", name).group())
    return 1 if name in ("return_1m", "abs_return_1m") else 0


def verify_prefix(d, f, cut):
    prefix = {k: v[:cut].copy() if isinstance(v, np.ndarray) and len(v) == len(d["r"]) else v
              for k, v in d.items() if k not in ("first", "end")}
    a = np.flatnonzero(np.r_[True, prefix["day"][1:] != prefix["day"][:-1]])
    prefix["first"], prefix["end"] = a, np.r_[a[1:], cut]
    short, _ = construct(prefix)
    for name in f:
        require(np.allclose(f[name][:cut], short[name], rtol=0, atol=0, equal_nan=True), f"Future deletion changed {name}")


def build(protocol_path, outdir):
    expected = protocol_path.with_suffix(".sha256").read_text().split()[0]
    require(sha256(protocol_path) == expected, "Protocol hash mismatch")
    protocol = json.loads(protocol_path.read_text(encoding="utf-8"))
    require(protocol["status"] == "FROZEN_RETROSPECTIVE_EXPLORATORY", "Wrong protocol status")
    for item in protocol["implementation_files"]:
        require(sha256(protocol_path.parent/item["name"]) == item["sha256"], f"Implementation changed: {item['name']}")
    require(not outdir.exists(), "Use a new output directory; never overwrite a run")
    outdir.mkdir(parents=True)
    before = {}
    for spec in protocol["development"].values():
        for role in ("panel", "etf"):
            path = spec[f"{role}_file"]
            before[path] = sha256(path)
            require(before[path] == spec[f"{role}_sha256"], f"Frozen source changed: {path}")
    coverage, runs, tests, support = [], {}, [], []
    for era, spec in protocol["development"].items():
        print(f"Loading development only: {era} {spec['first_session']} to {spec['last_session']}", flush=True)
        d = load_development(era, spec)
        f, quality = construct(d)
        require(sorted(f) == sorted(protocol["candidate_features"]), "Candidate registry mismatch")
        years = np.array([s[:4] for s in d["day"]])
        for name, values in f.items():
            require(not np.isinf(values).any(), f"Infinite feature: {name}")
            warm = feature_warmup(name)
            require(not np.isfinite(values[d["slot"] < warm]).any(), f"Warmup failure: {name}")
            if name.endswith("_strict") and name.startswith(("rv", "downside", "momentum")):
                require(np.array_equal(np.isfinite(values), (d["slot"] >= warm) &
                        (quality[f"n_return_obs_{warm}"] == warm)), f"Strict mask failure: {name}")
            for year in ["ALL", *np.unique(years)]:
                mask = np.ones(len(values), bool) if year == "ALL" else years == year
                after_warmup = mask & (d["slot"] >= warm)
                coverage.append(dict(era=era, year=year, feature=name, calendar_minutes=int(mask.sum()),
                    after_warmup_minutes=int(after_warmup.sum()), available=int((mask & np.isfinite(values)).sum()),
                    available_after_warmup_pct=100*float(np.isfinite(values[after_warmup]).mean())))
        # An interior-day cut tests deletion of future bars, future sessions, and
        # stability of the same-slot volume baseline on actual development data.
        cut = int(d["first"][min(40, len(d["first"])-1)]) + 123
        verify_prefix(d, f, cut)
        tests.append(dict(era=era, test="actual_data_future_deletion_all_features", result="PASS", prefix_rows=cut))
        for tier, names in protocol["comparison_tiers"].items():
            mask = np.logical_and.reduce([np.isfinite(f[n]) for n in names])
            support.append(dict(era=era, tier=tier, union_features="|".join(names),
                                common_minutes=int(mask.sum()), calendar_minutes=len(mask)))
        meta = pd.DataFrame({"utc_minute_start_assumed": pd.to_datetime(d["t"], utc=True),
            "available_utc_assuming_minute_start": pd.to_datetime(d["available"], utc=True),
            "session_date_ny": d["day"], "minute_index_in_session": d["slot"], "source_epoch": era,
            "SPY_return_eligible": d["valid"].astype(np.uint8)})
        output = pd.concat([meta, pd.DataFrame(f), pd.DataFrame(quality)], axis=1)
        path = outdir/f"candidate_features_{era}_DEVELOPMENT.csv.gz"
        output.to_csv(path, index=False, float_format="%.17g", compression={"method": "gzip", "mtime": 0})
        runs[era] = dict(rows=len(d["r"]), sessions=len(d["first"]), first_session=d["day"][0],
                         last_session=d["day"][-1], feature_count=len(f), output=str(path), output_sha256=sha256(path))
        print(f"Saved {era}: {len(output):,} rows, {len(f)} candidate features", flush=True)
        del output, meta, f, quality, d
    pd.DataFrame(coverage).to_csv(outdir/"feature_coverage_development.csv", index=False)
    pd.DataFrame(support).to_csv(outdir/"common_support_development.csv", index=False)
    after = {path: sha256(path) for path in before}
    require(before == after, "Source file changed during run")
    summary = dict(created_utc=datetime.now(timezone.utc).isoformat(), status="PASS_CANDIDATE_CONSTRUCTION",
        protocol_file=str(protocol_path), protocol_sha256=expected, runs=runs,
        tests=tests, original_input_hashes_before=before, original_input_hashes_after=after,
        retrospective_evaluation_features_constructed=False, hmm_fitted=False, feature_winner_selected=False,
        caveats=["Causal under inherited bar-start/availability assumptions; does not establish vendor causality.",
                 "Partial RV is an extrapolation proxy. Five-minute sampled RV is a different estimator.",
                 "No unexposed final test identified. 2025-2026 has prior outcome/feature exposure."])
    (outdir/"summary.json").write_text(json.dumps(summary, indent=2)+"\n", encoding="utf-8")


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--protocol", type=Path, required=True)
    p.add_argument("--out-dir", type=Path, required=True)
    args = p.parse_args()
    build(args.protocol.resolve(), args.out_dir.resolve())
