#!/usr/bin/env python3
"""A4 F4: real-data prefix and isolation tests with relative tolerance only (rtol 1e-9, atol 0, NaN equals NaN),
mid-session cuts added, RAW then LEGACY, on the code with the calibrated Lee-Mykland constant (F3).

Method (as in Step 3, plus mid-session cuts): rebuild only a 40-session slice ending at the cut and compare its last 15 sessions
(and the rows of a partial last session) with the full-run values.
  Prefix:    10 cuts per era, alternating session-end and mid-session (a random row 70 to 10 rows before the session end).
  Isolation: 8 blankings per era, alternating a full session and, from a random mid-session row, the rest of the session;
             rows before the blanked rows must not change.
  Power:     every feature scaled by 1+1e-6 must be flagged by the same comparison.
A mismatch is reported as FAIL; the tolerance is never loosened."""
import sys, os, json, hashlib, datetime, shutil, tempfile, warnings
from pathlib import Path
import numpy as np

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step3_all_in_one as s  # noqa: E402

R, log = s.OUT, s.log
RTOL, SLICE, COMPARE = 1e-9, 40, 15
WARM = SLICE - COMPARE
BAR = ("r", "close", "volume", "range", "open", "high", "low")


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def flat(f):
    return {**f["original"], **f["additional"]}


def era_folder(era):
    return Path(tempfile.gettempdir()) / f"a4_f4_{era}_{os.getpid()}"


def calc_spilled(d, label, folder):
    """The same features as s.calculate, computed in three parts and spilled to float64 .npy files so that only one part is in memory
    (float32 is not used: the tolerance of this test is rtol 1e-9). Returns name -> memory-mapped column."""
    folder.mkdir(parents=True, exist_ok=True)
    def spill(dic):
        for k, v in dic.items(): np.save(folder / f"{k}.npy", np.asarray(v, float))
    a, _ = s.construct(d); spill(a); del a
    view = dict(d); view["first"] = s.SessionProgress(d["first"], label)
    b = s.construct_additions(view); spill(b); del b
    spill(s.construct_deferred(d))  # overwrites the placeholder files of construct_additions, as s.calculate does with update()
    return {p.stem: np.load(p, mmap_mode="r") for p in sorted(folder.glob("*.npy"))}


def same(a, b):
    return a.shape == b.shape and np.allclose(a, b, rtol=RTOL, atol=0, equal_nan=True)


def run_era(era, rng):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    log(f"{era}: full run")
    f = calc_spilled(d, f"{era} full run", era_folder(era))
    assert len(f) == 81, f"{era}: {len(f)} feature files, expected 81"
    nS = len(d["first"])
    prefix, iso = [], []
    for n, i in enumerate(sorted(int(x) for x in rng.choice(np.arange(30, nS - 1), size=10, replace=False))):
        a, b = int(d["first"][i]), int(d["end"][i])
        kind = "session_end" if n % 2 == 0 else "mid_session"
        cut = b if kind == "session_end" else a + int(rng.integers(70, (b - a) - 10))
        lo = max(0, i - SLICE + 1)
        z, off = s.slice_sessions(d, lo, i + 1)
        small = flat(s.calculate(s.truncate(z, cut - off), f"{era} prefix {n+1}/10 ({kind})"))
        cf = int(d["first"][lo + WARM]) if lo > 0 else 0
        bad = [k for k in small if not same(f[k][cf:cut], small[k][cf - off:cut - off])]
        prefix.append(dict(session_index=i, kind=kind, cut_row=cut, rows_compared=cut - cf, mismatching_features=bad))
    for n, i in enumerate(sorted(int(x) for x in rng.choice(np.arange(30, nS - 1), size=8, replace=False))):
        a, b = int(d["first"][i]), int(d["end"][i])
        kind = "full_session" if n % 2 == 0 else "from_mid_session"
        lo = max(0, i - SLICE + 1)
        z, off = s.slice_sessions(d, lo, i + 1)
        alt = s.copied(z)
        a_loc, b_loc = int(z["first"][-1]), len(z["r"])
        j0 = a_loc if kind == "full_session" else a_loc + int(rng.integers(70, (b_loc - a_loc) - 10))
        for key in BAR: alt[key][j0:] = np.nan
        alt["valid"][j0:] = False
        changed = flat(s.calculate(alt, f"{era} isolation {n+1}/8 ({kind})"))
        cf = int(d["first"][lo + WARM - 1]) if lo > 0 else 0
        bad = [k for k in changed if not same(f[k][cf:j0 + off], changed[k][cf - off:j0])]
        iso.append(dict(session_index=i, kind=kind, blanked_from_row=j0 + off, rows_compared=j0 + off - cf, mismatching_features=bad))
    undetectable = []
    for k in list(f):
        x = np.array(f[k])
        fin = np.isfinite(x) & (x != 0)
        if not fin.any(): undetectable.append(f"{k} (no non-zero finite value)"); continue
        y = x.copy(); y[fin] = x[fin] * (1 + 1e-6)
        if same(x, y): undetectable.append(k)
    power = dict(features=len(f), not_detectable=undetectable, status="PASS" if all("no non-zero" in u for u in undetectable) else "FAIL")
    res = dict(era=era, train_rows=int(len(d["r"])), tolerance=dict(rtol=RTOL, atol=0), slice_sessions=SLICE, compared_sessions=COMPARE,
               prefix=dict(cuts=prefix, kinds=dict(session_end=sum(c["kind"] == "session_end" for c in prefix), mid_session=sum(c["kind"] == "mid_session" for c in prefix)),
                           status="PASS" if not any(c["mismatching_features"] for c in prefix) else "FAIL"),
               isolation=dict(blankings=iso, status="PASS" if not any(c["mismatching_features"] for c in iso) else "FAIL"), power_check=power)
    log(f"{era}: prefix {res['prefix']['status']}, isolation {res['isolation']['status']}, power check {power['status']}")
    return res


def main():
    """python step12_a4_prefix_isolation_rerun.py [RAW] [LEGACY]  (default both, RAW first). Each era has its own fixed seed and its own
    result file, so the eras can run in separate processes to limit memory; the combined report is written once both exist."""
    want = [a.upper() for a in sys.argv[1:]] or ["RAW", "LEGACY"]
    s.refuse_overwrite(*[R / f"a4_prefix_isolation_{e}.json" for e in want])
    for e in want:
        rng = np.random.default_rng(43109 + (e == "LEGACY"))
        try: res = run_era(e, rng)
        finally: shutil.rmtree(era_folder(e), ignore_errors=True)
        (R / f"a4_prefix_isolation_{e}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    files = {e: R / f"a4_prefix_isolation_{e}.json" for e in ("RAW", "LEGACY")}
    if not all(p.exists() for p in files.values()):
        print("combined report waits for the other era"); return 0
    s.refuse_overwrite(R / "a4_prefix_isolation_report.json", R / "a4_prefix_isolation_report.md", R / "a4_prefix_isolation_report.sha256")
    eras = {e: json.loads(files[e].read_text(encoding="utf-8")) for e in files}
    now = datetime.datetime.now(datetime.timezone.utc)
    table = [dict(item=f"{e} {t}", status=eras[e][k]["status"] if k != "power_check" else eras[e][k]["status"])
             for e in eras for t, k in (("prefix (relative tolerance, session-end and mid-session cuts)", "prefix"), ("isolation (full-session and mid-session blanking)", "isolation"), ("tolerance power check (1e-6 relative error detected)", "power_check"))]
    report = dict(created_utc=now.isoformat(), amendment="4.3-A4 F4", lm_calibration_sha256=sha(s.LM_CALIBRATION), step3_script_sha256=sha(ROOT / "step3_all_in_one.py"),
                  table=table, overall="PASS" if all(r["status"] == "PASS" for r in table) else "FAIL", eras=eras)
    rp = R / "a4_prefix_isolation_report.json"
    rp.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    L = ["# Prefix and isolation rerun (A4 F4)", "", f"Run {now.isoformat()} UTC. Relative tolerance rtol 1e-9, atol 0. Overall: **{report['overall']}**.", "", "| Test | Status |", "|---|---|"] + [f"| {t['item']} | {t['status']} |" for t in table]
    for e in eras:
        L += ["", f"## {e}", "", f"Prefix cuts: {eras[e]['prefix']['kinds']}. Rows compared per cut: {min(c['rows_compared'] for c in eras[e]['prefix']['cuts'])}-{max(c['rows_compared'] for c in eras[e]['prefix']['cuts'])}.",
              f"Isolation blankings: {len(eras[e]['isolation']['blankings'])}. Power check: {eras[e]['power_check']['features']} features, not detectable: {eras[e]['power_check']['not_detectable'] or 'none'}."]
    mp = R / "a4_prefix_isolation_report.md"
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    (R / "a4_prefix_isolation_report.sha256").write_text(f"{sha(rp)}  {rp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    print("\n".join(L[:12]))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
