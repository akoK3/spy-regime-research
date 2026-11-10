#!/usr/bin/env python3
"""AMENDMENT_A28 rule 6b: label-free cross-asset coverage check. Per asset (TLT, HYG, GOLD = XAUUSD mid, DOLLAR = DOLLARIDX mid; SPY for reference) and RTH session of the
DEVELOPMENT spans only (s5_eval_loader.load_development: LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23; no evaluation session is read):
  usable_share   share of the 389 return slots (indices 1..389) with an eligible one-minute return
  zero_share     share of eligible returns exactly 0
  stale_share    GOLD / DOLLAR: share of slots with the causal flat-quote-age >= 15 min flag; ETFs: NaN (no such flag)
  max_gap_min    longest run of consecutive slots without an eligible return
Computed without break times, alarms, detector output or any outcome. Before it runs: A28 must be ADOPTED and equal its sidecar (rule 6a: hashed before any coverage check).
The availability rule (rule 1e) is applied by available() with the constants below; they are this script's proposal, written before the check runs, pending the user's
approval (A28 does not state numbers); a changed rule is reported as a deviation (6g).
Output: section6/results/coverage/coverage_sessions.csv, coverage_summary.json (by asset, era and year). Usage: s6_coverage.py"""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(ROOT / "section5"))
OUT = HERE / "results" / "coverage"; ASSETS = ("SPY", "TLT", "HYG", "GOLD", "DOLLAR"); QUOTES = ("GOLD", "DOLLAR")
MIN_USABLE = 0.80; MAX_GAP = 30; MAX_STALE = 0.25          # proposal, pending approval


def a28_guard():
    a = ROOT / "AMENDMENT_A28.md"; s = ROOT / "AMENDMENT_A28.sha256"
    if not s.exists() or s.read_text().split()[0] != hashlib.sha256(a.read_bytes()).hexdigest() or "Status: ADOPTED" not in a.read_text(encoding="utf-8"): raise PermissionError("AMENDMENT_A28.md not adopted or differs from its sidecar")


def longest_gap(ok):
    best = cur = 0
    for v in ok:
        cur = 0 if v else cur + 1; best = max(best, cur)
    return best


def session_metrics(g, asset):
    """g: the session's rows (minute_index_in_session 0..389). Metrics over return slots 1..389."""
    el = np.zeros(390, bool); r = np.full(390, np.nan); mi = g["minute_index_in_session"].to_numpy()
    el[mi] = g[f"{asset}_return_eligible"].to_numpy() == 1; r[mi] = g[f"{asset}_log_return_1m"].to_numpy(); el, r = el[1:], r[1:]
    n_el = int(el.sum()); stale = np.nan
    if asset in QUOTES:
        f = np.zeros(390); f[mi] = g[f"{asset}_causal_flat_age_ge15_flag"].to_numpy(); stale = float(f[1:].mean())
    return dict(usable_share=n_el / 389, zero_share=(float(np.mean(r[el] == 0)) if n_el else np.nan), stale_share=stale, max_gap_min=longest_gap(el), n_eligible=n_el)


def available(m, asset):
    return bool(m["usable_share"] >= MIN_USABLE and m["max_gap_min"] <= MAX_GAP and (asset not in QUOTES or not (m["stale_share"] > MAX_STALE)))


def main():
    import pandas as pd, s5_eval_loader as EL
    a28_guard(); OUT.mkdir(parents=True, exist_ok=True); rows = []
    cols = [f"{a}_{k}" for a in ASSETS for k in ("return_eligible", "log_return_1m")] + [f"{a}_causal_flat_age_ge15_flag" for a in QUOTES]
    hashes = {}
    for era in ("LEGACY", "RAW"):
        df = EL.load_development(era, cols); hashes[era] = hashlib.sha256(EL.PANELS[era].read_bytes()).hexdigest()
        for day, g in df.groupby("session_date_ny", sort=True):
            for a in ASSETS: rows.append(dict(era=era, day=day, asset=a, **session_metrics(g, a)))
        del df
    for x in rows: x["available"] = available(x, x["asset"])
    sd = pd.DataFrame(rows); tmp = OUT / "coverage_sessions.tmp"; sd.to_csv(tmp, index=False); tmp.replace(OUT / "coverage_sessions.csv")
    sd["year"] = sd["day"].str[:4]; summ = {}
    for (a, e, y), g in sd.groupby(["asset", "era", "year"]):
        summ.setdefault(a, {}).setdefault(e, {})[y] = dict(n_sessions=int(len(g)), n_available=int(g["available"].sum()), median_usable=float(g["usable_share"].median()),
                                                          median_zero=float(g["zero_share"].median()) if g["zero_share"].notna().any() else None, median_max_gap=float(g["max_gap_min"].median()))
    res = dict(label="A28 rule 6b label-free coverage check (development spans only)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), panel_sha256=hashes,
               rule=dict(min_usable=MIN_USABLE, max_gap_min=MAX_GAP, max_stale_quotes=MAX_STALE, status="proposal pending user approval"), script_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(), by_asset_era_year=summ)
    (OUT / "coverage_summary.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print(f"coverage: {len(rows)} asset-sessions; written to {OUT}"); return 0


if __name__ == "__main__": sys.exit(main())
