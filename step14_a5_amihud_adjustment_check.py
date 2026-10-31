#!/usr/bin/env python3
"""A5 G4: report-only check whether LEGACY closes are dividend-adjusted. Changes no data, formula, threshold or classification.

(a) Ex-dividend test, TRAIN rows only. SPY ex-dividend dates are approximated as the third Friday of March, June, September and December
    (the previous session if that Friday is not a session). Per era: mean overnight log return (first-bar Open / previous session's last Close)
    on those sessions minus the mean on all other sessions, with a Welch standard error. An unadjusted series shows a gap of about minus the
    quarterly dividend yield (roughly 0.3-0.5%); a fully adjusted series shows about 0. RAW is the unadjusted reference.
    Fixed reading rule: 'resembles RAW' if the LEGACY gap is more than 2 standard errors below 0 and within 2 combined standard errors of RAW's;
    'resembles zero' if the LEGACY gap is within 2 standard errors of 0 and RAW's is more than 2 standard errors below 0; otherwise 'inconclusive'.
(b) Junction: first RAW Open (2022-03-07) over last LEGACY Close (2022-03-04). This reads ONE price level from a LEGACY session that is
    EVALUATION_EXPOSED in the manifest; no return statistic is computed from that period. Level checks: first and last TRAIN closes of each era."""
import sys, json, hashlib, datetime, calendar, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

R = s.OUT
JS, MD = R / "a5_amihud_adjustment_check.json", R / "a5_amihud_adjustment_check.md"


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def third_friday(y, m):
    fr = [w[calendar.FRIDAY] for w in calendar.monthcalendar(y, m) if w[calendar.FRIDAY]]
    return f"{y}-{m:02d}-{fr[2]:02d}"


def era_data(era):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    return d, spec


def welch(a, b):
    se = np.sqrt(a.var(ddof=1) / len(a) + b.var(ddof=1) / len(b))
    return float(a.mean() - b.mean()), float(se)


def era_test(era, d):
    f, e = d["first"], d["end"]
    days = d["day"][f].tolist()
    op, cl = d["open"][f], d["close"][e - 1]
    ov = np.full(len(f), np.nan)
    ok = np.isfinite(op[1:]) & np.isfinite(cl[:-1]) & (op[1:] > 0) & (cl[:-1] > 0)
    ov[1:][ok] = np.log(op[1:][ok] / cl[:-1][ok])
    dayset = set(days)
    ex = set()
    for y in range(int(days[0][:4]), int(days[-1][:4]) + 1):
        for m in (3, 6, 9, 12):
            tf = third_friday(y, m)
            if tf in dayset: ex.add(tf)
            else:
                prev = [x for x in days if x < tf]
                if prev and (pd.Timestamp(tf) - pd.Timestamp(prev[-1])).days <= 7 and days[0] <= tf <= days[-1]: ex.add(prev[-1])
    is_ex = np.array([x in ex for x in days]) & np.isfinite(ov)
    other = np.isfinite(ov) & ~is_ex
    diff, se = welch(ov[is_ex], ov[other])
    res = dict(era=era, ex_dividend_sessions=int(is_ex.sum()), other_sessions=int(other.sum()), mean_overnight_ex_pct=round(100 * float(ov[is_ex].mean()), 4),
               mean_overnight_other_pct=round(100 * float(ov[other].mean()), 4), gap_pct=round(100 * diff, 4), se_pct=round(100 * se, 4), t=round(diff / se, 2))
    if era == "LEGACY":
        half = {}
        for name, lo, hi in (("2003-2010", "2003", "2010"), ("2011-2018", "2011", "2018")):
            sel = np.array([lo <= x[:4] <= hi for x in days])
            a, b = ov[is_ex & sel], ov[other & sel]
            g, s_ = welch(a, b)
            half[name] = dict(ex_sessions=int(len(a)), gap_pct=round(100 * g, 4), se_pct=round(100 * s_, 4))
        res["by_subperiod"] = half
    levels = dict(first_session=days[0], first_close=float(d["close"][f[0]:e[0]][np.isfinite(d["close"][f[0]:e[0]])][0]),
                  last_session=days[-1], last_close=float(d["close"][f[-1]:e[-1]][np.isfinite(d["close"][f[-1]:e[-1]])][-1]),
                  first_open=float(d["open"][f[0]]))
    return res, levels


def legacy_close_20220304(spec):
    best = None
    for chunk in pd.read_csv(spec["etf_file"], usecols=["utc_minute_start", "session_date_ny", "Close"], chunksize=200_000):
        c = chunk[chunk.session_date_ny == "2022-03-04"]
        if len(c) and np.isfinite(c.Close).any(): best = float(c.Close[np.isfinite(c.Close)].iloc[-1])
    return best


def main():
    s.refuse_overwrite(JS, MD)
    out, levels, data = {}, {}, {}
    for era in ("RAW", "LEGACY"):
        d, spec = era_data(era)
        out[era], levels[era] = era_test(era, d)
        data[era] = (d, spec)
        print(era, out[era], flush=True)
    raw_first_open = levels["RAW"]["first_open"]
    leg_last = legacy_close_20220304(data["LEGACY"][1])
    junction = dict(raw_first_open_2022_03_07=raw_first_open, legacy_last_close_2022_03_04=leg_last, ratio=round(raw_first_open / leg_last, 5) if leg_last else None,
                    note="reads one LEGACY price level from an EVALUATION_EXPOSED session; no return statistic from that period is computed")
    L, R_ = out["LEGACY"], out["RAW"]
    se_c = np.sqrt(L["se_pct"] ** 2 + R_["se_pct"] ** 2)
    if L["gap_pct"] < -2 * L["se_pct"] and abs(L["gap_pct"] - R_["gap_pct"]) < 2 * se_c: reading = "LEGACY resembles RAW (gap present: closes look unadjusted)"
    elif abs(L["gap_pct"]) < 2 * L["se_pct"] and R_["gap_pct"] < -2 * R_["se_pct"]: reading = "LEGACY resembles zero (no ex-dividend gap: closes look dividend-adjusted)"
    else: reading = "inconclusive"
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A5 G4", kind="report only", ex_dividend_test=out, price_levels=levels, junction=junction,
               reading_rule_result=reading, reading_rule="see the script docstring (fixed before the run)",
               external_reference_not_from_the_repository="General knowledge, unverified here: SPY traded near 90 in early January 2003; a series adjusted for all dividends up to 2026 would show a much lower level for that date.",
               consequence_for_amihud="Inference only: if the closes are back-adjusted, the dollar volume (volume x close) in amihud_w is understated in early years and the level of amihud_w drifts with the adjustment factor.",
               script_sha256=sha(__file__))
    JS.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    md = ["# LEGACY dividend-adjustment check (A5 G4, report only)", "", f"Reading: **{reading}**", "",
          "| Era | Ex-dividend sessions | Mean overnight on ex-dates % | Mean on other sessions % | Gap % | SE % | t |", "|---|---|---|---|---|---|---|"] + \
         [f"| {e} | {out[e]['ex_dividend_sessions']} | {out[e]['mean_overnight_ex_pct']} | {out[e]['mean_overnight_other_pct']} | {out[e]['gap_pct']} | {out[e]['se_pct']} | {out[e]['t']} |" for e in ("LEGACY", "RAW")] + \
         ["", f"LEGACY sub-periods: {out['LEGACY']['by_subperiod']}", "", f"Junction: first RAW Open (2022-03-07) {raw_first_open} over last LEGACY Close (2022-03-04) {leg_last} = {junction['ratio']}.",
          f"Levels: LEGACY first close {levels['LEGACY']['first_close']} ({levels['LEGACY']['first_session']}), last TRAIN close {levels['LEGACY']['last_close']} ({levels['LEGACY']['last_session']}); RAW first close {levels['RAW']['first_close']} ({levels['RAW']['first_session']}), last TRAIN close {levels['RAW']['last_close']} ({levels['RAW']['last_session']}).",
          "", "Report only: no data, formula, threshold or classification was changed."]
    MD.write_text("\n".join(md) + "\n", encoding="utf-8")
    (R / "a5_amihud_adjustment_check.sha256").write_text(f"{sha(JS)}  {JS.name}\n{sha(MD)}  {MD.name}\n", encoding="ascii")
    print("\n".join(md))


if __name__ == "__main__":
    main()
