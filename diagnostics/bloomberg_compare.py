#!/usr/bin/env python3
"""Post-evaluation data check (ledger plan row 2026-11-12 17:22:43Z; user order 2026-11-13): RAW canonical panel 1-minute returns vs Bloomberg 1-minute trade bars
(Book1.xlsx = SPY US Equity, Book2.xlsx = HYG US Equity; 2026-03-18..2026-09-30), for (1) the timestamp convention (bar-start vs bar-end labelling) and (2) price agreement.
The panel holds log returns only (no prices), so agreement is measured on 1-minute close-to-close log returns and on per-session sums.
The panel's evaluation span is read only through s5_eval_loader.load_eval (guarded, logged in eval_access_log.txt); the run happens after the official 5.13 RAW, Section 6
and A38 results exist. Descriptive; changes no result, setup, threshold or verdict. Not a result module. The xlsx files are parsed with the standard library.
Output: section5/results/bloomberg_comparison.json (written once)."""
import sys, json, re, zipfile, hashlib, datetime
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; S5 = ROOT / "section5"; sys.path.insert(0, str(S5))
OUT = S5 / "results" / "bloomberg_comparison.json"; FREEZE = S5 / "results" / "section5_freeze.json"
BOOKS = {"SPY": ROOT / "Book1.xlsx", "HYG": ROOT / "Book2.xlsx"}; LO, HI = "2026-03-18", "2026-09-30"
NS = "{http://schemas.openxmlformats.org/spreadsheetml/2006/main}"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read_book(path):
    """(ticker, header, list of (excel serial, open, close, high, low, volume)) from the first sheet; layout checked."""
    z = zipfile.ZipFile(path); ss = [("".join(t.text or "" for t in si.iter(NS + "t"))) for si in ET.fromstring(z.read("xl/sharedStrings.xml")).findall(NS + "si")]
    rows = []
    for r in ET.fromstring(z.read("xl/worksheets/sheet1.xml")).iter(NS + "row"):
        v = {}
        for c in r.findall(NS + "c"):
            col = re.match(r"[A-Z]+", c.get("r")).group(); x = c.find(NS + "v")
            if x is None: continue
            v[col] = ss[int(x.text)] if c.get("t") == "s" else float(x.text)
        rows.append(v)
    assert rows[0].get("F") == "BarTp" and rows[0].get("G") == "Trade", rows[0]
    hdr = [rows[2].get(k) for k in "FGHIJKL"]; assert hdr == ["Dates", "Open", "Close", "High", "Low", "Value", "Volume"], hdr
    data = [(r["F"], r["G"], r["H"], r["I"], r["J"], r.get("L")) for r in rows[3:] if isinstance(r.get("F"), float)]
    return rows[1].get("F"), hdr, data


def excel_to_ny(serial):
    """Excel serial (1900 system) as naive local wall time, rounded to the minute."""
    dt = datetime.datetime(1899, 12, 30) + datetime.timedelta(days=serial); return (dt + datetime.timedelta(seconds=30)).replace(second=0, microsecond=0)


def main():
    if OUT.exists(): print("exists; written once"); return 3
    import pandas as pd, s5_eval_loader as EL
    token = sha(FREEZE)
    cols = [f"{a}_{k}" for a in BOOKS for k in ("return_eligible", "log_return_1m")]
    df = EL.load_eval("RAW", cols, FREEZE, token, section6=True)
    df = df[(df["session_date_ny"] >= LO) & (df["session_date_ny"] <= HI)].copy()
    ny = pd.to_datetime(df["utc_minute_start_assumed"], utc=True).dt.tz_convert("America/New_York").dt.tz_localize(None)
    df["ny_minute"] = ny; res = dict(label="DESCRIPTIVE post-evaluation data check (not part of any hypothesis test; evaluation-period data read through the guard after all evaluation results were written)",
                                     window=[LO, HI], freeze_sha256=token, panel=str(EL.PANELS["RAW"].relative_to(ROOT)), panel_sha256=sha(EL.PANELS["RAW"]),
                                     panel_minute_label="utc_minute_start_assumed (Section 3 minute-start assumption), converted to New York time", assets={})
    for a, book in BOOKS.items():
        tick, hdr, data = read_book(book)
        b = pd.DataFrame(data, columns=["serial", "open", "close", "high", "low", "volume"]); b["ny_minute"] = b["serial"].map(excel_to_ny)
        b["day"] = b["ny_minute"].dt.strftime("%Y-%m-%d"); b["hm"] = b["ny_minute"].dt.strftime("%H:%M")
        rth = b[(b["hm"] >= "09:30") & (b["hm"] <= "15:59")].sort_values("ny_minute").reset_index(drop=True)
        ext = b[~b.index.isin(b[(b["hm"] >= "09:30") & (b["hm"] <= "15:59")].index)]
        # Bloomberg 1-minute close-to-close return, only between consecutive minutes of the same session
        prev = rth.groupby("day")["close"].shift(1); gap = rth.groupby("day")["ny_minute"].diff() == pd.Timedelta(minutes=1)
        rth["bret"] = np.where(gap, np.log(rth["close"] / prev), np.nan)
        rth["oc_ret"] = np.log(rth["close"] / rth["open"])
        p = df[df[f"{a}_return_eligible"].astype(bool)][["session_date_ny", "ny_minute", f"{a}_log_return_1m"]].rename(columns={f"{a}_log_return_1m": "pret"})
        p = p[np.isfinite(p["pret"])]
        lags = {}
        for k in range(-3, 4):
            m = p.assign(key=p["ny_minute"] + pd.Timedelta(minutes=k)).merge(rth[["ny_minute", "bret"]].rename(columns={"ny_minute": "key"}), on="key", how="inner")
            m = m[np.isfinite(m["bret"])]; d = (m["pret"] - m["bret"]).abs()
            lags[k] = dict(n=int(len(m)), corr=float(np.corrcoef(m["pret"], m["bret"])[0, 1]) if len(m) > 2 else None,
                           share_absdiff_lt_1e_6=float((d < 1e-6).mean()) if len(m) else None, median_absdiff_bp=float(d.median() * 1e4) if len(m) else None)
        best = max(lags, key=lambda k: lags[k]["corr"] or -1)
        m = p.assign(key=p["ny_minute"] + pd.Timedelta(minutes=best)).merge(rth[["ny_minute", "bret", "day"]].rename(columns={"ny_minute": "key"}), on="key", how="inner")
        m = m[np.isfinite(m["bret"])]; d = (m["pret"] - m["bret"]).abs() * 1e4
        # per-session sum of the matched returns (both sides on the same matched minutes)
        ds = m.groupby("session_date_ny").agg(p=("pret", "sum"), b=("bret", "sum"), n=("pret", "size")); dd = (ds["p"] - ds["b"]).abs() * 1e4
        pdays = set(p["session_date_ny"]); bdays = set(rth["day"]); allp = set(df["session_date_ny"])
        res["assets"][a] = dict(
            book=dict(file=book.name, sha256=sha(book), ticker=tick, bar_type="Trade", header=hdr, rows=len(b), first=str(b["ny_minute"].min()), last=str(b["ny_minute"].max()),
                      sessions=len(bdays), rth_bars=int(len(rth)), bars_outside_0930_1559=int(len(ext)), outside_times=sorted(ext["hm"].value_counts().head(8).to_dict().items()),
                      first_bar_time_counts=rth.groupby("day")["hm"].min().value_counts().head(5).to_dict(), last_bar_time_counts=rth.groupby("day")["hm"].max().value_counts().head(5).to_dict(),
                      bars_with_open_ne_previous_close_share=float((rth["open"] != rth.groupby("day")["close"].shift(1))[gap].mean())),
            panel=dict(sessions=len(allp), return_eligible_minutes=int(len(p)), sessions_with_eligible_returns=len(pdays)),
            sessions_only_in_panel=sorted(allp - bdays), sessions_only_in_bloomberg=sorted(bdays - allp),
            lag_scan=dict(definition="panel return at New York minute m vs Bloomberg close-to-close return of the bar labelled m + k", by_k={str(k): v for k, v in lags.items()}, best_k=best),
            agreement_at_best_k=dict(n=int(len(m)), corr=lags[best]["corr"], absdiff_bp_quantiles={q: float(np.quantile(d, q)) for q in (0.5, 0.9, 0.99, 0.999)} if len(d) else None,
                                     share_absdiff_lt_0_1bp=float((d < 0.1).mean()), share_absdiff_lt_1bp=float((d < 1).mean()), share_absdiff_ge_5bp=float((d >= 5).mean()),
                                     n_absdiff_ge_10bp=int((d >= 10).sum()),
                                     largest=[dict(minute=str(r.ny_minute), panel=float(r.pret), bloomberg=float(r.bret)) for r in m.assign(ad=d).nlargest(10, "ad").itertuples()]),
            session_sums=dict(n_sessions=int(len(ds)), absdiff_bp_quantiles={q: float(np.quantile(dd, q)) for q in (0.5, 0.9, 0.99)} if len(dd) else None, max_absdiff_bp=float(dd.max()) if len(dd) else None,
                              worst=[dict(day=k, panel_bp=float(r.p * 1e4), bloomberg_bp=float(r.b * 1e4), n=int(r.n)) for k, r in ds.assign(ad=dd).nlargest(5, "ad").iterrows()]))
    res["generated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    OUT.write_text(json.dumps(res, indent=1, default=str), encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
    for a, v in res["assets"].items():
        print(a, json.dumps(dict(lag=v["lag_scan"], agree=v["agreement_at_best_k"], sums=v["session_sums"], book={k: v["book"][k] for k in ("rows", "sessions", "rth_bars", "first_bar_time_counts", "last_bar_time_counts", "outside_times")},
                                 panel=v["panel"], only_panel=v["sessions_only_in_panel"][:20], only_bbg=v["sessions_only_in_bloomberg"][:20]), default=str)[:4000])
    return 0


if __name__ == "__main__": sys.exit(main())
