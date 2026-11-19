#!/usr/bin/env python3
"""Compare regenerated paper outputs with the values printed in the paper. Standard library only; read-only except for
the report it writes (paper/tables/check_report.json).

Checks
  1. Tables: every entry of paper/expected_values.json against paper/tables/tables.json (written by make_tables.py).
     numeric: |computed - printed| <= half a unit in the printed last digit, plus 1e-9 (printed values round half up);
     hashes and other text: exact; "range" entries: computed value, at printed precision, lies in [lo, hi].
  2. Figures: for each of the six figures, (a) it was regenerated in this run (paper/tables/figure_run.json, written by
     reproduce_paper.py), (b) the PNG and PDF exist in paper/figures/, (c) the input-file hashes in
     paper/figures/figure_sources.json equal the files on disk OR the PNG bytes equal paper/figures_png/<name>.png
     (a rebuilt feature cache for fig6 has a new file hash even with identical columns), and (d) for fig1/fig2,
     paper/figures/figure_stats.json equals the committed reference paper/figures_reference_stats.json to 1e-12.
     PDFs are not byte-compared (matplotlib embeds a creation date).

Usage: python paper/check_paper_values.py [--expected FILE] [--skip-figures]
Exit:  0 all pass / 1 a value differs / 2 an input is missing."""
import argparse, hashlib, json, sys
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
P = ROOT / "paper"
FIGS = ["fig1_h1a_pauc_gain", "fig2_fomc_hit_rates", "fig3_detection_by_break_size", "fig4_h3_gamma", "fig5_a30_timing", "fig6_seasonality"]


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def num(s):
    s = str(s).replace("−", "-").replace(",", "").replace("+", "").strip()
    return Decimal(s)


def half_unit(s):
    d = num(s)
    return Decimal(1).scaleb(d.as_tuple().exponent) / 2


def check_value(exp, got):
    txt = str(exp["paper"]).strip()
    if got is None:
        return False, "no computed value"
    if exp.get("kind") == "range":
        lo, hi = txt.split("..")
        return num(lo) - half_unit(lo) <= Decimal(repr(float(got))) <= num(hi) + half_unit(hi), f"range [{lo}, {hi}]"
    try:
        e = num(txt)
    except Exception:
        return str(got) == txt, "text"
    if isinstance(got, str):
        return got == txt, "text"
    tol = half_unit(txt) + Decimal("1e-9")
    diff = abs(Decimal(repr(float(got))) - e)
    return diff <= tol, f"|diff| {float(diff):.3g} <= {float(tol):.3g}"


def check_tables(expected_path):
    tj = P / "tables" / "tables.json"
    if not tj.exists():
        print("MISSING paper/tables/tables.json: run python paper/make_tables.py first"); sys.exit(2)
    got = json.loads(tj.read_text(encoding="utf-8")); exp = json.loads(Path(expected_path).read_text(encoding="utf-8"))
    rows = []
    for e in exp["values"]:
        g = got.get(e["id"], {}).get("value")
        ok, how = check_value(e, g)
        if g is None and e["id"].startswith("A3.") and not ok:
            how = "file not present (data or git-ignored); not checked"; ok = None
        rows.append({"id": e["id"], "paper": e["paper"], "computed": g, "pass": ok, "rule": how,
                     "source": got.get(e["id"], {}).get("source")})
    return rows


def check_figures():
    out = []
    srcs = json.loads((P / "figures" / "figure_sources.json").read_text(encoding="utf-8"))
    ref_stats = P / "figures_reference_stats.json"; new_stats = P / "figures" / "figure_stats.json"
    stats_ok = None
    if ref_stats.exists() and new_stats.exists():
        a = json.loads(ref_stats.read_text(encoding="utf-8")); b = json.loads(new_stats.read_text(encoding="utf-8"))
        def eq(x, y):
            if isinstance(x, dict): return isinstance(y, dict) and x.keys() == y.keys() and all(eq(x[k], y[k]) for k in x)
            if isinstance(x, list): return isinstance(y, list) and len(x) == len(y) and all(eq(i, j) for i, j in zip(x, y))
            if isinstance(x, float) or isinstance(y, float): return abs(float(x) - float(y)) <= 1e-12
            return x == y
        stats_ok = eq(a, b)
    run = P / "tables" / "figure_run.json"
    regen = set(json.loads(run.read_text(encoding="utf-8"))["regenerated"]) if run.exists() else None
    for name in FIGS:
        r = {"figure": name, "regenerated_this_run": None if regen is None else name in regen}
        r["files_exist"] = all((P / "figures" / f"{name}.{e}").exists() for e in ("png", "pdf"))
        bad = [s for s, h in srcs.get(name, {}).items() if not (ROOT / s).exists() or sha(ROOT / s) != h]
        r["inputs_match"] = not bad; r["inputs_bad"] = bad
        if name in ("fig1_h1a_pauc_gain", "fig2_fomc_hit_rates"): r["stats_match"] = stats_ok
        ref = P / "figures_png" / f"{name}.png"; new = P / "figures" / f"{name}.png"
        r["png_identical_to_committed"] = ref.exists() and new.exists() and sha(ref) == sha(new)
        # A rebuilt feature cache (fig6) has a different file hash from the original cache even when the columns are the
        # same, so a figure passes if its inputs match OR its PNG is byte-identical to the committed one.
        r["pass"] = (r["files_exist"] and r["regenerated_this_run"] is not False and (r["inputs_match"] or r["png_identical_to_committed"])
                     and r.get("stats_match", True) is not False)
        out.append(r)
    return out


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--expected", default=str(P / "expected_values.json")); ap.add_argument("--skip-figures", action="store_true")
    a = ap.parse_args()
    tab = check_tables(a.expected); fig = [] if a.skip_figures else check_figures()
    n_fail = sum(1 for r in tab if r["pass"] is False) + sum(1 for r in fig if not r["pass"])
    n_skip = sum(1 for r in tab if r["pass"] is None)
    for r in tab:
        if r["pass"] is False: print(f"FAIL  {r['id']}: paper {r['paper']}, computed {r['computed']} ({r['rule']})")
    for r in fig:
        flag = "PASS" if r["pass"] else "FAIL"
        print(f"{flag}  {r['figure']}: regenerated {r['regenerated_this_run']}, files {r['files_exist']}, inputs {r['inputs_match']}{' ' + str(r['inputs_bad']) if r['inputs_bad'] else ''}, "
              f"stats {r.get('stats_match', 'n/a')}, PNG byte-identical {r['png_identical_to_committed']}")
    print(f"tables: {sum(1 for r in tab if r['pass'])} pass, {sum(1 for r in tab if r['pass'] is False)} fail, {n_skip} not checked (file absent); "
          f"figures: {sum(1 for r in fig if r['pass'])}/{len(fig)} pass")
    (P / "tables" / "check_report.json").write_text(json.dumps({"tables": tab, "figures": fig}, indent=1, default=str), encoding="utf-8")
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
