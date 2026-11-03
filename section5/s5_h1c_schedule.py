#!/usr/bin/env python3
"""A12 item 2: H1(c) event times for meetings whose statement page states no release time. Order of evidence per meeting:
 (1) the statement page states 'For release at ...' (results/h1c_release_times.json, A11);
 (2) the Fed's press-conference page states 'FOMC Meeting Statement (Released <date> at <time>)' (press-conference days are those with a 'Press Conference' link on the Fed's historical FOMC pages);
 (3) before April 2011: 14:15, the documented schedule of Lucca and Moench (2015), sec. 2 ('regularly released at, or a few minutes after, 2:15 pm'; no Fed page states these times: recorded);
 (4) from 2013 on: 14:00, accepted only if every Fed page that states a time from 2013 on states 14:00 (checked here);
 (5) April 2011 - December 2012 on a non-press-conference day: no Fed source and no statement in Lucca and Moench: ambiguous, excluded.
No time is assumed otherwise. Output results/h1c_schedule_times.json. Usage: s5_h1c_schedule.py fetch | build"""
import sys, re, json, hashlib, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; CACHE = HERE / "cache" / "fomc"; PC = HERE / "cache" / "fomc_pc"; BASE = "https://www.federalreserve.gov"
UA = "section5-research-script/1.0"; LM = "Lucca and Moench (2015), 'The Pre-FOMC Announcement Drift', J. Finance; NY Fed Staff Report 512, section 2"
sha_file = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
REL_PC = re.compile(r"FOMC Meeting Statement\s*(?:&nbsp;|\s)*\(Released\s+([A-Za-z]+)\s+(\d{1,2}),\s*(\d{4})\s+at\s+(\d{1,2})(?::(\d{2}))?\s*([ap])\.?m\.?\)", re.I)
MONTH = {m: i + 1 for i, m in enumerate("January February March April May June July August September October November December".split())}


def txt(t): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.replace("&nbsp;", " ").replace("\xa0", " ")))


def pc_days():
    out = {}
    for f in sorted(CACHE.glob("h*.htm")):
        for m in re.finditer(r'href="(/monetarypolicy/fomcpresconf(\d{8})\.htm)"', f.read_text(encoding="utf-8", errors="ignore")):
            d = m.group(2); out[f"{d[:4]}-{d[4:6]}-{d[6:]}"] = BASE + m.group(1)
    return out


def fetch():
    PC.mkdir(parents=True, exist_ok=True)
    for d, u in pc_days().items():
        f = PC / f"{d}.htm"
        if f.exists() and f.stat().st_size > 500: continue
        r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", UA, "-o", str(f), "-w", "%{http_code}", u], capture_output=True, text=True)
        if r.stdout.strip() != "200": f.write_text(f"HTTP {r.stdout.strip()}", encoding="utf-8")
        time.sleep(0.6)


def parse_pc(t):
    """(date 'YYYY-MM-DD', 'HH:MM') of the statement release stated on a press-conference page, or None."""
    m = REL_PC.search(txt(t))
    if not m: return None
    mo, dd, yy, h, mi, ap = m.groups(); h = int(h) % 12 + (12 if ap.lower() == "p" else 0)
    return f"{int(yy)}-{MONTH[mo.capitalize()]:02d}-{int(dd):02d}", f"{h:02d}:{int(mi or 0):02d}"


mins = lambda hhmm: int(hhmm[:2]) * 60 + int(hhmm[3:]) - 570


def build():
    dates = sorted(x for v in json.loads((RES / "d6_fomc_dates.json").read_text())["scheduled_meetings_with_statement"].values() for x in v)
    stated = json.loads((RES / "h1c_release_times.json").read_text())["meetings"]; pcs = pc_days(); pc_time = {}
    for d in pcs:
        f = PC / f"{d}.htm"; r = parse_pc(f.read_text(encoding="utf-8", errors="ignore")) if f.exists() else None
        if r and r[0] == d: pc_time[d] = dict(time_et=r[1], url=pcs[d], page_sha256=sha_file(f))
    fed_stated = {d: v["time_et"] for d, v in stated.items() if v["status"] == "time"}; fed_stated.update({d: v["time_et"] for d, v in pc_time.items()})
    post2013 = {d: t for d, t in fed_stated.items() if d >= "2013-01-01"}; rule4_ok = bool(post2013) and all(t == "14:00" for t in post2013.values())
    out = {}
    for d in dates:
        s = stated.get(d, {})
        if s.get("status") == "time": out[d] = dict(status="time", time_et=s["time_et"], minute_after_0930=s["minute_after_0930"], basis="statement page states the time", url=s["url"], page_sha256=s["page_sha256"])
        elif d in pc_time: t = pc_time[d]["time_et"]; out[d] = dict(status="time", time_et=t, minute_after_0930=mins(t), basis="Fed press-conference page states the statement release time", url=pc_time[d]["url"], page_sha256=pc_time[d]["page_sha256"])
        elif d < "2011-04-01": out[d] = dict(status="time", time_et="14:15", minute_after_0930=mins("14:15"), basis=f"schedule, {LM} (before April 2011: 2:15 pm or a few minutes after); no Fed page states this time", uncertainty="window start may be a few minutes late")
        elif d >= "2013-01-01":
            if rule4_ok: out[d] = dict(status="time", time_et="14:00", minute_after_0930=mins("14:00"), basis=f"schedule (from 2013 on 14:00), consistent with all {len(post2013)} Fed pages that state a time from 2013 on")
            else: out[d] = dict(status="excluded", reason="2013 or later: Fed pages stating a time are not all 14:00")
        else: out[d] = dict(status="excluded", reason="April 2011 - December 2012, not a press-conference day: no Fed source states the time and Lucca and Moench do not document it (ambiguous)")
    cnt = {}
    for v in out.values(): k = v["basis"].split(",")[0].split(" (")[0] if v["status"] == "time" else "excluded"; cnt[k] = cnt.get(k, 0) + 1
    res = dict(source="A12 item 2", rule_2013_plus_consistent=rule4_ok, n_fed_pages_stating_time_2013_plus=len(post2013), fed_press_conference_pages_with_time=len(pc_time),
               exceptions_to_schedule_rule=[dict(date=d, stated=v["time_et"]) for d, v in sorted(pc_time.items()) if (d < "2011-04-01" and v["time_et"] != "14:15") or (d >= "2013-01-01" and v["time_et"] != "14:00")],
               counts=dict(time=sum(1 for v in out.values() if v["status"] == "time"), excluded=sum(1 for v in out.values() if v["status"] == "excluded"), by_basis=cnt), meetings=out)
    (RES / "h1c_schedule_times.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


if __name__ == "__main__":
    if sys.argv[1] == "fetch": fetch()
    r = build(); print(r["counts"], r["rule_2013_plus_consistent"], r["n_fed_pages_stating_time_2013_plus"], r["exceptions_to_schedule_rule"])
