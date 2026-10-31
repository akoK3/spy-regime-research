#!/usr/bin/env python3
"""Post-hoc follow-up to 4.3.5 (not defined in amendment A3): which LEGACY stale-close runs have zero volume, by year.

Stale run = 5 or more consecutive grid bars within a session with finite, exactly equal Close (the 4.3.5 definition,
re-derived here and checked against the 4.3.5 result). Zero volume = a bar with Volume == 0. TRAIN rows only.
Reported at bar level and at run level (runs with every bar at zero volume, and runs with at least one). A run belongs to
the year of its first bar. Context column: the share of all observed LEGACY bars with zero volume in that year.
"""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

R = s.OUT


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    era = "LEGACY"
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec)
    c, v, slot = d["close"], d["volume"], d["slot"]
    n = len(c); fin = np.isfinite(c)
    same = np.zeros(n, bool)
    same[1:] = fin[1:] & fin[:-1] & (c[1:] == c[:-1]) & (slot[1:] > 0)
    run_id = np.cumsum(~same)
    length = np.bincount(run_id)[run_id]
    flag = fin & (length >= 5)
    prior = pd.read_csv(R / "sec4_3_5_stale_closes_by_year.csv")
    expected = int(prior[prior.era == era].flagged_bars.sum())
    assert int(flag.sum()) == expected, f"flagged {int(flag.sum())} != 4.3.5 result {expected}"
    zero = np.isfinite(v) & (v == 0)
    years = np.array([x[:4] for x in d["day"]])
    runs = pd.DataFrame(dict(run=run_id[flag], zero=zero[flag], year=years[flag])).groupby("run").agg(bars=("zero", "size"), zero_bars=("zero", "sum"), year=("year", "first"))
    rows = []
    for y in sorted(set(years.tolist())):
        ym = years == y
        fb, fz = int((flag & ym).sum()), int((flag & zero & ym).sum())
        r = runs[runs.year == y]
        ob, oz = int((fin & ym).sum()), int((fin & zero & ym).sum())
        rows.append(dict(year=y, stale_bars=fb, stale_bars_zero_volume=fz, stale_bars_zero_volume_pct=round(100 * fz / fb, 3) if fb else np.nan,
                         stale_runs=len(r), runs_all_bars_zero_volume=int((r.zero_bars == r.bars).sum()), runs_any_zero_volume=int((r.zero_bars > 0).sum()),
                         runs_all_zero_pct=round(100 * (r.zero_bars == r.bars).mean(), 3) if len(r) else np.nan,
                         runs_any_zero_pct=round(100 * (r.zero_bars > 0).mean(), 3) if len(r) else np.nan,
                         context_all_observed_bars_zero_volume_pct=round(100 * oz / ob, 3)))
    tab = pd.DataFrame(rows)
    tot = dict(stale_bars=int(flag.sum()), stale_bars_zero_volume=int((flag & zero).sum()), stale_runs=len(runs),
               runs_all_bars_zero_volume=int((runs.zero_bars == runs.bars).sum()), runs_any_zero_volume=int((runs.zero_bars > 0).sum()),
               context_all_observed_bars_zero_volume_pct=round(100 * (fin & zero).sum() / fin.sum(), 3))
    tot["stale_bars_zero_volume_pct"] = round(100 * tot["stale_bars_zero_volume"] / tot["stale_bars"], 3)
    tot["runs_all_zero_pct"] = round(100 * tot["runs_all_bars_zero_volume"] / tot["stale_runs"], 3)
    tot["runs_any_zero_pct"] = round(100 * tot["runs_any_zero_volume"] / tot["stale_runs"], 3)
    csv = R / "sec4_3_5b_legacy_stale_zero_volume_by_year.csv"
    csv.write_text(tab.to_csv(index=False), encoding="utf-8")
    now = datetime.datetime.now(datetime.timezone.utc)
    doc = dict(created_utc=now.isoformat(), status="POST_HOC_DESCRIPTIVE_FOLLOW_UP_TO_4_3_5 (not defined in amendment A3)", era=era, train_rows=n,
               definition="stale run = 5+ consecutive bars with finite equal Close within a session (4.3.5); zero volume = Volume == 0; a run belongs to the year of its first bar",
               check="flagged bars equal the 4.3.5 LEGACY result", total=tot, by_year_file=csv.name, by_year_sha256=sha(csv))
    js = R / "sec4_3_5b_legacy_stale_zero_volume.json"
    js.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    (R / "sec4_3_5b_legacy_stale_zero_volume.sha256").write_text(f"{sha(js)}  {js.name}\n{sha(csv)}  {csv.name}\n", encoding="ascii")
    print(tab.to_string(index=False)); print("\nTOTAL", json.dumps(tot))


if __name__ == "__main__":
    main()
