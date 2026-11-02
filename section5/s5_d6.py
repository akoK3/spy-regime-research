#!/usr/bin/env python3
"""Descriptive check D6 (no detectors, TRAIN dates only): SPY deseasonalised 1-min variance ratio, mean over the 60 bars after the event / mean over the 60 bars before,
for FOMC statements (scheduled meetings, taken as 14:00 ET), and three listed shocks; compared with 1,000 random same-time-of-day moments (other full TRAIN sessions of the
same era, FOMC days and the event day excluded). Deseasonalised variance = r^2 / median r^2 of the same slot over the previous 20 sessions (s5_d2_stable.des_variance).
Slot 0 = 09:30 bar. 'After' = bars T..T+59 (the bar stamped T contains the event), 'before' = bars T-60..T-1."""
import sys, re, json, hashlib
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_d2_stable as S

FOMC = L.CACHE / "fomc"; SEED = 6001; NR = 1000
MON = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}
ABBR = {"Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4, "May": 5, "Jun": 6, "Jul": 7, "Aug": 8, "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12}
SHOCKS = [("2010-05-06", "Flash Crash, decline from 14:32", 14 * 60 + 32 - 570), ("2010-05-06", "Flash Crash, 14:45 (near the trough)", 14 * 60 + 45 - 570),
          ("2015-08-24", "open (09:30; before = previous session's last hour)", 0), ("2018-02-05", "afternoon, 15:00", 15 * 60 - 570)]


def txt(f):
    t = open(f, encoding="utf-8", errors="ignore").read(); return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t))


def parse_hist(year):
    """Scheduled meetings with a statement: '<Month d[-d2]> Meeting - YYYY' ... 'Statement' before the next entry. Returns statement (last) dates."""
    t = txt(FOMC / f"h{year}.htm"); pat = re.compile(r"((?:[A-Z][a-z]+(?:/[A-Z][a-z]+)?) \d{1,2}(?:-\d{1,2})?) (Meeting|Conference Call) - " + str(year))
    ms = list(pat.finditer(t)); out = []
    for k, m in enumerate(ms):
        if m.group(2) != "Meeting": continue
        seg = t[m.end(): ms[k + 1].start() if k + 1 < len(ms) else len(t)]
        if "Statement" not in seg[:1500] and "Statement" not in seg: continue
        out.append(date_of(m.group(1), year))
    return out


def date_of(s, year):
    mo, days = s.rsplit(" ", 1); last = int(days.split("-")[-1]); first_mo = mo.split("/")[0]; last_mo = mo.split("/")[-1]
    mn = MON.get(last_mo) or ABBR.get(last_mo[:3]); return f"{year}-{mn:02d}-{last:02d}"


def parse_cal(year):
    t = txt(FOMC / "cal.htm"); i = t.find(f"{year} FOMC Meetings"); j = t.find(f"{year - 1} FOMC Meetings"); seg = t[i: j if j > i else i + 6000]
    pat = re.compile(r"((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:/[A-Z][a-z]+)? \d{1,2}(?:-\d{1,2})?)\*? Statement")
    return [date_of(m.group(1), year) for m in pat.finditer(seg)]


def ratio(dv, a, T, valid_prev=None):
    """a = session start row, T = slot; before = rows a+T-60..a+T-1 (for T = 0: previous session's last 60 rows), after = a+T..a+T+59."""
    after = dv[a + T: a + T + 60]
    before = dv[a + T - 60: a + T] if T >= 60 else valid_prev
    if np.isfinite(after).sum() < 50 or np.isfinite(before).sum() < 50: return np.nan
    x, y = np.nanmean(after), np.nanmean(before)
    return float(x / y) if x > 0 and y > 0 else np.nan


def qs(x):
    x = np.asarray(x, float); x = x[np.isfinite(x)]; return dict(n=len(x), q05=np.quantile(x, .05), q25=np.quantile(x, .25), median=np.median(x), mean=x.mean(), q75=np.quantile(x, .75), q95=np.quantile(x, .95), share_gt_1p5=(x > 1.5).mean(), share_gt_2=(x > 2).mean())


def main():
    # ---- FOMC dates from the Federal Reserve pages (fetched 2026-11 by curl; sha256 stored)
    dates = {}
    for y in range(2003, 2019): dates[y] = parse_hist(y)
    for y in (2022, 2023, 2024): dates[y] = parse_cal(y)
    allf = sorted(x for v in dates.values() for x in v); src = {f.name: hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(FOMC.glob("*.htm"))}
    json.dump(dict(source="https://www.federalreserve.gov/monetarypolicy/fomchistorical{YEAR}.htm (2003-2018) and /fomccalendars.htm (2022-2024)", scheduled_meetings_with_statement=dates, page_sha256=src),
              open(L.HERE / "results" / "d6_fomc_dates.json", "w"), indent=1)
    rng = np.random.default_rng(SEED); res = dict(fomc={}, shocks=[]); fomc_rows = []; primary, _, _ = L.pools()
    for era in ("LEGACY", "RAW"):
        d = L.load_era(era, primary[:1]); dv = S.des_variance(d); days = np.array([str(d["day"][i]) for i in d["first"]]); n = len(days)
        full = np.array([(d["end"][i] - d["first"][i]) == 390 for i in range(n)])   # window-level finiteness (>= 50 of 60 bars) is enforced in ratio()
        idx = {x: i for i, x in enumerate(days)}; fset = set(allf)
        pool = np.array([i for i in range(21, n) if full[i] and full[i - 1] and days[i] not in fset])
        # FOMC
        for x in allf:
            if x in idx and idx[x] >= 21 and full[idx[x]] and np.isfinite(ratio(dv, int(d["first"][idx[x]]), 270)): fomc_rows.append((era, x, ratio(dv, int(d["first"][idx[x]]), 270)))
        res.setdefault("fomc_missing_in_panel", {})[era] = [x for x in allf if (x[:4] <= "2018") == (era == "LEGACY") and not (x in idx and idx[x] >= 21 and full[idx[x]] and np.isfinite(ratio(dv, int(d["first"][idx[x]]), 270)))]
        # random moments at 14:00 (for FOMC) and at the shock times
        def rand(T, excl=None):
            p = pool[days[pool] != excl] if excl else pool; ch = rng.choice(p, NR, replace=True)
            return np.array([ratio(dv, int(d["first"][i]), T, None if T else dv[int(d["end"][i - 1]) - 60: int(d["end"][i - 1])]) for i in ch])
        res.setdefault("_rand14", {})[era] = rand(270)
        for day, label, T in SHOCKS:
            if day not in idx: continue
            i = idx[day]; r = ratio(dv, int(d["first"][i]), T, None if T else dv[int(d["end"][i - 1]) - 60: int(d["end"][i - 1])]); rr = rand(T, day)
            res["shocks"].append(dict(date=day, event=label, ratio=r, random=qs(rr), percentile_of_event_among_random=float((rr[np.isfinite(rr)] < r).mean() * 100), full_session=bool(full[i])))
        del d, dv
    fr = np.array([r for _, _, r in fomc_rows]); rnd = np.concatenate([res["_rand14"]["LEGACY"], res["_rand14"]["RAW"]]); rnd = rnd[np.isfinite(rnd)]
    from scipy.stats import mannwhitneyu
    res["fomc"] = dict(n_statements_listed=len(allf), n_used=int(np.isfinite(fr).sum()), fomc=qs(fr), random_14_00=qs(rnd), mannwhitney_p_two_sided=float(mannwhitneyu(fr[np.isfinite(fr)], rnd).pvalue),
                       share_of_random_below_fomc_median=float((rnd < np.nanmedian(fr)).mean()),
                       by_era={e: qs([r for ee, _, r in fomc_rows if ee == e]) for e in ("LEGACY", "RAW")}, per_event=[dict(era=e, date=x, ratio=r) for e, x, r in fomc_rows])
    del res["_rand14"]
    json.dump(res, open(L.HERE / "results" / "d6_results.json", "w"), indent=1, default=float)
    print(json.dumps({k: v for k, v in res["fomc"].items() if k != "per_event"}, indent=1, default=float)); print(json.dumps(res["shocks"], indent=1, default=float)); print(res["fomc_missing_in_panel"])
    print({y: len(v) for y, v in dates.items()})


if __name__ == "__main__":
    main()
