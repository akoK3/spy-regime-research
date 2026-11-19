#!/usr/bin/env python3
"""Regenerate the paper's Tables 3-5 and A3-A5 and its six figures from the stored result files, then check every value
against the paper. READ-ONLY on research results: writes only paper/tables/ and paper/figures/.

Steps
  1. Data check (optional): if the canonical files of DATA.md §1 are present, verify their SHA-256 (DATA_SHA256SUMS).
  2. Tables: paper/make_tables.py -> paper/tables/TABLES.md, tables.json.
  3. Figures: paper/make_figures.py, one figure at a time. fig1-fig5 need only committed result files. fig6 needs the
     development feature cache section5/cache/{era}_features.npz; with --build-cache and the canonical panels present,
     the needed columns are built by the audited Section 5 loader (s5_lib.load_era, TRAIN sessions only).
  4. Check: paper/check_paper_values.py (exit 1 on any mismatch).

Usage:  python reproduce_paper.py [--build-cache] [--skip-figures]
Runtime on the reference laptop (AMD Ryzen 7 7435HS): tables + check a few seconds; figures 1-5 about half a minute;
cache build for fig6 see README.md."""
import argparse, hashlib, json, runpy, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PY = sys.executable


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()


def data_check():
    rows = []
    for line in (ROOT / "DATA_SHA256SUMS").read_text(encoding="utf-8").splitlines():
        h, path = line.split("  ", 1); p = ROOT / path
        rows.append((path, "absent" if not p.exists() else ("OK" if sha(p) == h else "MISMATCH")))
    for path, st in rows:
        if st != "absent" or not path.startswith("data/"):
            print(f"  {st:9s} {path}")
    if any(st == "MISMATCH" for _, st in rows):
        sys.exit("data hash mismatch: stop")
    return all(st == "OK" for path, st in rows if not path.startswith("data/"))


def build_cache():
    sys.path.insert(0, str(ROOT / "section5")); sys.path.insert(0, str(ROOT))
    import s5_lib as L
    cols = ["return_1m", "abs_return_1m", "abs_return_1m__sadj", "rv10_partial90", "rv10_partial90__sadj"]
    for era in ("LEGACY", "RAW"):
        t = time.time(); L.load_era(era, cols); print(f"  cache {era}: {time.time() - t:.0f} s")


def figures(have_cache):
    mf = runpy.run_path(str(ROOT / "paper" / "make_figures.py"), run_name="make_figures")
    done = []
    for name in ("fig1", "fig2", "fig3", "fig4", "fig5", "fig6"):
        if name == "fig6" and not have_cache:
            print("  fig6 skipped: section5/cache/{LEGACY,RAW}_features.npz absent (needs data; see --build-cache)"); continue
        t = time.time(); mf[name](); done.append(name); print(f"  {name}: {time.time() - t:.1f} s")
    out = ROOT / "paper" / "figures"
    old = json.loads((out / "figure_sources.json").read_text(encoding="utf-8"))
    old.update(mf["SOURCES"]); (out / "figure_sources.json").write_text(json.dumps(old, indent=1), encoding="utf-8")
    (out / "figure_stats.json").write_text(json.dumps(mf["STATS"], indent=1), encoding="utf-8")
    return [k for k in mf["SOURCES"]]


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--build-cache", action="store_true"); ap.add_argument("--skip-figures", action="store_true")
    a = ap.parse_args(); t0 = time.time()
    print("1. data"); panels = data_check()
    print("2. tables"); subprocess.run([PY, str(ROOT / "paper" / "make_tables.py")], check=True)
    regenerated = []
    if not a.skip_figures:
        cache = all((ROOT / "section5" / "cache" / f"{e}_features.npz").exists() for e in ("LEGACY", "RAW"))
        if a.build_cache and not cache:
            if not panels: sys.exit("--build-cache needs the canonical files of DATA.md §1")
            print("3a. feature cache"); build_cache(); cache = True
        print("3. figures"); regenerated = figures(cache)
    (ROOT / "paper" / "tables" / "figure_run.json").write_text(json.dumps({"regenerated": regenerated}, indent=1), encoding="utf-8")
    print("4. check")
    r = subprocess.run([PY, str(ROOT / "paper" / "check_paper_values.py")] + (["--skip-figures"] if a.skip_figures else []))
    print(f"total {time.time() - t0:.0f} s")
    sys.exit(r.returncode)


if __name__ == "__main__":
    main()
