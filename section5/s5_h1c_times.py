#!/usr/bin/env python3
"""A11 item 3: release time of each FOMC statement from its federalreserve.gov page ("For release at 2:00 p.m. EST"). Pages are fetched once (curl), cached with sha256; unavailable
times (immediate release, no parseable time, fetch failure) are recorded and those meetings are excluded from H1(c); no time is assumed. Output: results/h1c_release_times.json.
Minutes are counted from 09:30 ET (14:00 = 270). Usage: s5_h1c_times.py fetch | parse"""
import sys, re, json, hashlib, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; CACHE = HERE / "cache" / "fomc"; OUTC = HERE / "cache" / "fomc_stmt"; BASE = "https://www.federalreserve.gov"
UA = "section5-research-script/1.0"


def txt(t): return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", t.replace("&nbsp;", " ").replace("\xa0", " ")))


def cand_map(dates):
    """date -> candidate statement URLs: every 'Statement' anchor of the historical pages that carries the date, then the press-release pattern (a, b)."""
    hrefs = {}
    for f in sorted(CACHE.glob("h*.htm")):
        t = f.read_text(encoding="utf-8", errors="ignore")
        for m in re.finditer(r'href="([^"]+)"[^>]*>\s*Statement', t):
            h = m.group(1); d = re.search(r"(20\d{6})", h)
            if d and h.startswith("/") and ("monetary" in h or "boarddocs" in h): hrefs.setdefault(f"{d.group(1)[:4]}-{d.group(1)[4:6]}-{d.group(1)[6:]}", []).append(BASE + h)
    out = {}
    for d in dates:
        c = list(dict.fromkeys(hrefs.get(d, []) + [f"{BASE}/newsevents/pressreleases/monetary{d.replace('-', '')}{x}.htm" for x in "ab"])); out[d] = (c, d in hrefs)
    return out


def is_statement(t):
    """The page must be the FOMC statement itself (a press-release URL pattern can point to another release of the same day)."""
    s = txt(t); i = s.find("Federal Open Market Committee"); return i >= 0 and ("decided" in s[i:i + 600] or "Committee" in s[i:i + 200]) and "Term Auction Facility" not in s[:1500]


def fetch_one(url, f):
    if f.exists() and f.stat().st_size > 0: return f.read_text(encoding="utf-8", errors="ignore")
    r = subprocess.run(["curl", "-sS", "-L", "--max-time", "40", "-A", UA, "-o", str(f), "-w", "%{http_code}", url], capture_output=True, text=True)
    if r.stdout.strip() != "200": f.write_text(f"HTTP {r.stdout.strip()} {r.stderr.strip()}", encoding="utf-8")
    time.sleep(0.6); return f.read_text(encoding="utf-8", errors="ignore")


def fetch(dates):
    """Fetch candidates in order until one is the FOMC statement; the chosen page is cached as <date>.htm."""
    OUTC.mkdir(parents=True, exist_ok=True)
    for d, (cands, _) in cand_map(dates).items():
        f = OUTC / f"{d}.htm"
        if f.exists() and is_statement(f.read_text(encoding="utf-8", errors="ignore")): continue
        for k, u in enumerate(cands):
            tmp = OUTC / f"{d}_c{k}.htm"; t = fetch_one(u, tmp)
            if is_statement(t): f.write_text(t, encoding="utf-8"); (OUTC / f"{d}.url").write_text(u); break


REL = re.compile(r"For\s+release\s+at\s+(\d{1,2})(?::(\d{2}))?\s*(a\.m\.|p\.m\.|am|pm)\s*(E[SD]T)?", re.I)
IMM = re.compile(r"For\s+immediate\s+release", re.I)


def parse_one(t):
    s = txt(t); m = REL.search(s)
    if m:
        h, mi, ap = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower()[0]
        h = h % 12 + (12 if ap == "p" else 0); return dict(status="time", time_et=f"{h:02d}:{mi:02d}", tz=(m.group(4) or "").upper(), minute_after_0930=h * 60 + mi - 570)
    if IMM.search(s): return dict(status="unavailable", reason="statement page says 'For immediate release' (no release time)")
    if s.startswith("HTTP") or len(s) < 200: return dict(status="unavailable", reason=f"page not fetched or empty: {s[:80]}")
    return dict(status="unavailable", reason="no 'For release at' time found on the page")


def parse(dates):
    cm = cand_map(dates); out = {}
    for d in dates:
        f = OUTC / f"{d}.htm"; u = OUTC / f"{d}.url"
        r = parse_one(f.read_text(encoding="utf-8", errors="ignore")) if f.exists() else dict(status="unavailable", reason="no candidate page was the FOMC statement (fetch failed or other release): " + "; ".join(cm[d][0][:3]))
        r.update(url=u.read_text() if u.exists() else None, url_source=("historical page link" if u.exists() and u.read_text() in cm[d][0][:len(cm[d][0]) - 2] else "press-release pattern") if u.exists() else None,
                 page_sha256=hashlib.sha256(f.read_bytes()).hexdigest() if f.exists() else None); out[d] = r
    n = {k: sum(1 for v in out.values() if v["status"] == k) for k in ("time", "unavailable")}
    times = {}
    for v in out.values():
        if v["status"] == "time": times[v["time_et"]] = times.get(v["time_et"], 0) + 1
    res = dict(source="federalreserve.gov statement pages (see url per meeting)", n_meetings=len(dates), counts=n, release_time_counts=dict(sorted(times.items())), meetings=out)
    (RES / "h1c_release_times.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); return res


def dates():
    j = json.loads((RES / "d6_fomc_dates.json").read_text()); return sorted(x for v in j["scheduled_meetings_with_statement"].values() for x in v)


if __name__ == "__main__":
    ds = dates()
    if sys.argv[1] == "fetch": fetch(ds)
    r = parse(ds); print(r["counts"], r["release_time_counts"])
