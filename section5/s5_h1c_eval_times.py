#!/usr/bin/env python3
"""AMENDMENT_A36 rule 3: FOMC statement release times for the evaluation periods (LEGACY 2019-01-02..2022-03-04, RAW 2025-01-02..2026-10-12), by the development
pipeline extended to the evaluation dates. No market data is read. Outside the frozen closure.
  dates   scheduled meetings with a statement, by the D6 parsers on the Federal Reserve pages: fomchistorical{YEAR}.htm for 2019 and 2020, fomccalendars.htm for
          2021, 2022, 2025 and 2026; dates outside the evaluation periods are dropped (3a).
  times   order of evidence of A11 item 3 / A12 item 2 (3b):
          1. the statement page states "For release at ..." (s5_h1c_times.parse_one);
          2. the Fed's press-conference page states "FOMC Meeting Statement (Released <date> at <time>)" (s5_h1c_schedule.parse_pc);
          3. from 2013 on: 14:00, accepted only if every Fed page stating a time from 2013 on, development and evaluation pages together, states 14:00;
          otherwise the meeting is excluded. No time is assumed.
  built first (3c): refuses if the evaluation access log shows an allowed read; the output is written once with a sidecar.
Pages are fetched once by curl (generic user agent) into cache/fomc_eval/ and recorded with their sha256.
Usage: s5_h1c_eval_times.py fetch | build | check      Output: results/h1c_schedule_times_evaluation.json (+ .sha256)"""
import sys, re, json, hashlib, subprocess, time, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; CACHE = HERE / "cache" / "fomc_eval"; DEV_FOMC = HERE / "cache" / "fomc"
OUT = RES / "h1c_schedule_times_evaluation.json"; ACCESS_LOG = RES / "eval_access_log.txt"; DEV_TIMES = RES / "h1c_schedule_times.json"
BASE = "https://www.federalreserve.gov"; UA = "section5-research-script/1.0"
PERIODS = {"LEGACY": ("2019-01-02", "2022-03-04"), "RAW": ("2025-01-02", "2026-10-12")}
HIST_YEARS = (2019, 2020); CAL_YEARS = (2021, 2022, 2025, 2026)
MON = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}
ABBR = {m[:3]: i for m, i in MON.items()}
sha_file = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def txt(t): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.replace("&nbsp;", " ").replace("\xa0", " ")))
def read(f): return Path(f).read_text(encoding="utf-8", errors="ignore")
def in_periods(d): return any(a <= d <= b for a, b in PERIODS.values())


def date_of(s, year):
    """As s5_d6.date_of: '<Month[/Month]> d[-d2]' -> the last day, in the last month named."""
    mo, days = s.rsplit(" ", 1); last = int(days.split("-")[-1]); last_mo = mo.split("/")[-1]
    return f"{year}-{(MON.get(last_mo) or ABBR.get(last_mo[:3])):02d}-{last:02d}"


def parse_hist(t, year):
    """As s5_d6.parse_hist on the text of a fomchistorical page: scheduled 'Meeting' entries (not conference calls) that list a Statement."""
    pat = re.compile(r"((?:[A-Z][a-z]+(?:/[A-Z][a-z]+)?) \d{1,2}(?:-\d{1,2})?) (Meeting|Conference Call) - " + str(year)); ms = list(pat.finditer(t)); out = []
    for k, m in enumerate(ms):
        if m.group(2) != "Meeting": continue
        if "Statement" in t[m.end(): ms[k + 1].start() if k + 1 < len(ms) else len(t)]: out.append(date_of(m.group(1), year))
    return out


def parse_cal(t, year):
    """As s5_d6.parse_cal on the text of the calendars page: the entries of one year's block that carry a Statement."""
    i = t.find(f"{year} FOMC Meetings"); j = t.find(f"{year - 1} FOMC Meetings"); seg = t[i: j if j > i else i + 6000]
    pat = re.compile(r"((?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sep|Oct|Nov|Dec)(?:/[A-Z][a-z]+)? \d{1,2}(?:-\d{1,2})?)\*? Statement")
    return [date_of(m.group(1), year) for m in pat.finditer(seg)] if i >= 0 else []


def curl(url, f):
    f = Path(f)
    if f.exists() and f.stat().st_size > 500: return read(f)
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", UA, "-o", str(f), "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout.strip() != "200": f.write_text(f"HTTP {r.stdout.strip()} {r.stderr.strip()}", encoding="utf-8")
    time.sleep(0.6); return read(f)


def pages():
    """{name: text} of the date pages: historical 2019 and 2020, and the calendars page (the development copy cache/fomc/cal.htm if present, else fetched)."""
    out = {}
    for y in HIST_YEARS:
        f = CACHE / f"h{y}.htm"
        if f.exists(): out[f.name] = read(f)
    cal = CACHE / "cal.htm"
    if cal.exists(): out["cal.htm"] = read(cal)
    return out


def dates():
    pg = pages(); miss = [n for n in [f"h{y}.htm" for y in HIST_YEARS] + ["cal.htm"] if n not in pg or len(pg[n]) < 2000]
    if miss: raise SystemExit(f"date pages not fetched: {miss} (run: s5_h1c_eval_times.py fetch)")
    by = {y: parse_hist(txt(pg[f"h{y}.htm"]), y) for y in HIST_YEARS}; by.update({y: parse_cal(txt(pg["cal.htm"]), y) for y in CAL_YEARS})
    return sorted(x for v in by.values() for x in v if in_periods(x)), {str(y): v for y, v in by.items()}


def pc_urls():
    """{date: press-conference page URL} linked from the date pages."""
    out = {}
    for t in pages().values():
        for m in re.finditer(r'href="(/monetarypolicy/fomcpresconf(\d{8})\.htm)"', t): d = m.group(2); out[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = BASE + m.group(1)
    return out


def fetch():
    import s5_h1c_times as T
    refuse_after_evaluation_read(); CACHE.mkdir(parents=True, exist_ok=True)
    for y in HIST_YEARS: curl(f"{BASE}/monetarypolicy/fomchistorical{y}.htm", CACHE / f"h{y}.htm")
    if not (CACHE / "cal.htm").exists(): curl(f"{BASE}/monetarypolicy/fomccalendars.htm", CACHE / "cal.htm")
    ds, _ = dates(); pcs = pc_urls()
    for d in ds:
        f = CACHE / f"{d}.htm"
        if not (f.exists() and T.is_statement(read(f))):
            for k, x in enumerate("ab"):                                               # the press-release pattern of s5_h1c_times.cand_map
                u = f"{BASE}/newsevents/pressreleases/monetary{d.replace('-', '')}{x}.htm"; t = curl(u, CACHE / f"{d}_c{k}.htm")
                if T.is_statement(t): f.write_text(t, encoding="utf-8"); (CACHE / f"{d}.url").write_text(u); break
        if d in pcs: curl(pcs[d], CACHE / f"{d}_pc.htm")


def refuse_after_evaluation_read():
    if ACCESS_LOG.exists() and " ALLOWED " in ACCESS_LOG.read_text(encoding="utf-8"): raise PermissionError("an evaluation-period read has been allowed: the FOMC list must be built before it (A36 3c)")


def build(write=True):
    import s5_h1c_times as T, s5_h1c_schedule as SC
    refuse_after_evaluation_read(); ds, by_year = dates(); pcs = pc_urls(); stated, pc_time = {}, {}
    for d in ds:
        f = CACHE / f"{d}.htm"
        if f.exists():
            r = T.parse_one(read(f))
            if r["status"] == "time": stated[d] = dict(r, url=(read(CACHE / f"{d}.url") if (CACHE / f"{d}.url").exists() else None), page_sha256=sha_file(f))
        g = CACHE / f"{d}_pc.htm"; r = SC.parse_pc(read(g)) if g.exists() else None
        if r and r[0] == d: pc_time[d] = dict(time_et=r[1], url=pcs.get(d), page_sha256=sha_file(g))
    dev = json.loads(DEV_TIMES.read_text(encoding="utf-8"))["meetings"] if DEV_TIMES.exists() else {}
    fed = {d: v["time_et"] for d, v in dev.items() if v.get("status") == "time" and not v.get("basis", "").startswith("schedule") and d >= "2013-01-01"}      # development pages that state a time
    fed.update({d: v["time_et"] for d, v in stated.items()}); fed.update({d: v["time_et"] for d, v in pc_time.items()}); rule_ok = bool(fed) and all(t == "14:00" for t in fed.values())
    out = {}
    for d in ds:
        if d in stated: s = stated[d]; out[d] = dict(status="time", time_et=s["time_et"], minute_after_0930=s["minute_after_0930"], basis="statement page states the time", url=s["url"], page_sha256=s["page_sha256"])
        elif d in pc_time: t = pc_time[d]["time_et"]; out[d] = dict(status="time", time_et=t, minute_after_0930=SC.mins(t), basis="Fed press-conference page states the statement release time", url=pc_time[d]["url"], page_sha256=pc_time[d]["page_sha256"])
        elif rule_ok: out[d] = dict(status="time", time_et="14:00", minute_after_0930=SC.mins("14:00"), basis=f"schedule (from 2013 on 14:00), consistent with all {len(fed)} Fed pages that state a time from 2013 on (development and evaluation)")
        else: out[d] = dict(status="excluded", reason="Fed pages stating a time from 2013 on are not all 14:00")
    cnt = {}
    for v in out.values(): k = v["basis"].split(",")[0].split(" (")[0] if v["status"] == "time" else "excluded"; cnt[k] = cnt.get(k, 0) + 1
    res = dict(source="AMENDMENT_A36 rule 3 (A11 item 3 and A12 item 2 extended to the evaluation periods)", written_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               periods=PERIODS, date_pages={n: hashlib.sha256(t.encode("utf-8", "ignore")).hexdigest() for n, t in sorted(pages().items())}, dates_parsed_by_year=by_year,
               rule_2013_plus_consistent=rule_ok, n_fed_pages_stating_time_2013_plus=len(fed), exceptions_to_schedule_rule=[dict(date=d, stated=t) for d, t in sorted(fed.items()) if t != "14:00"],
               counts=dict(meetings=len(out), time=sum(1 for v in out.values() if v["status"] == "time"), excluded=sum(1 for v in out.values() if v["status"] == "excluded"), by_basis=cnt,
                           by_period={k: sum(1 for d in out if a <= d <= b) for k, (a, b) in PERIODS.items()}), meetings=out)
    if write:
        if OUT.exists(): raise SystemExit(f"{OUT} exists (written once)")
        OUT.write_text(json.dumps(res, indent=1), encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha_file(OUT)}  {OUT.name}\n", encoding="ascii")
    return res


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch": fetch(); ds, by = dates(); print(len(ds), "evaluation meetings;", {k: len(v) for k, v in by.items()})
    elif cmd in ("build", "check"): r = build(write=(cmd == "build")); print(json.dumps({k: r[k] for k in ("counts", "rule_2013_plus_consistent", "n_fed_pages_stating_time_2013_plus", "exceptions_to_schedule_rule")}, indent=1))
    else: print(__doc__)
