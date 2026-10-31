#!/usr/bin/env python3
"""Regenerate 4.3.6 (yearly median and IQR) and the 4.3.9 frozen matrix under the A4/A5 definitions: 113-column pool (78 raw + 35 adjusted),
causal 20-session seasonal baseline (A4 F2), scaled jump_variation (A5 G3), calibrated Lee-Mykland threshold (A4 F3).
TRAIN only, RAW then LEGACY. Features are spilled to float64 files per era. Outputs are never overwritten.

4.3.6: per calendar year and era, the median and the interquartile range (Q3 - Q1, linear interpolation) of every pool column over its finite TRAIN values.
4.3.9: one matrix with a row per pool column (A3 fields), a primary view and a sensitivity view, and the SHA-256 of every input and output.
The selection outcomes are those of the A4 rerun (primary) and of the A5 G3 rerun (RAW sensitivity); they are read, not recomputed."""
import sys, json, hashlib, datetime, shutil, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step11_a4_rerun_4_3_4_7_8 as p  # noqa: E402
import step12_a4_prefix_isolation_rerun as m12  # noqa: E402

q, s, R, log, sha = p.q, p.q.s, p.R, p.log, p.sha
OUT_YEARLY = R / "a4_sec4_3_6_yearly_median_iqr.csv"
OUT_MATRIX, OUT_PRIMARY, OUT_SENS = R / "a4_sec4_3_9_frozen_matrix.csv", R / "a4_sec4_3_9_matrix_primary_view.csv", R / "a4_sec4_3_9_matrix_sensitivity_view.csv"
OUT_REPORT = R / "a4_sec4_3_6_9_report.json"
OUT_FILES = [OUT_YEARLY, OUT_MATRIX, OUT_PRIMARY, OUT_SENS, OUT_REPORT, R / "a4_sec4_3_6_9_report.md", R / "a4_sec4_3_6_9_report.sha256"]


def load(x):
    return json.loads(Path(x).read_text(encoding="utf-8"))


def yearly_rows(rows, era, ysl, name, kind, x):
    fin = np.isfinite(x)
    for y, (a, b) in ysl:
        v = x[a:b][fin[a:b]]
        if len(v):
            q1, med, q3 = np.percentile(v, [25, 50, 75])
            rows.append(dict(era=era, year=y, column=name, kind=kind, n_finite=int(len(v)), n_rows=int(b - a), median=med, iqr=q3 - q1))
        else:
            rows.append(dict(era=era, year=y, column=name, kind=kind, n_finite=0, n_rows=int(b - a), median=np.nan, iqr=np.nan))


def era_yearly(era, a4pct):
    first, last, panel, etf = s.CONFIG[era]
    spec = {"first_session": first, "last_session": last, "panel_file": str(s.file_path(panel)), "etf_file": str(s.file_path(etf))}
    log(f"{era}: loading TRAIN rows")
    d = s.load_development(era, spec)
    d.update(s.load_ohlc(spec, d))
    assert len(d["r"]) == q.TRAIN_ROWS[era]
    years = np.array([x[:4] for x in d["day"]])
    yl = sorted(set(years.tolist()))
    starts = np.searchsorted(years, yl, side="left")
    ysl = list(zip(yl, zip(starts, np.r_[starts[1:], len(years)])))
    slot = d["slot"]; first_i, end_i = p.sessions(slot)
    rows, cov_mismatch = [], []
    folder = m12.era_folder(era)
    try:
        log(f"{era}: features (spilled)")
        cols = m12.calc_spilled(d, f"{era} 4.3.6", folder)
        for i, n in enumerate(p.NAMES):
            x = np.array(cols[n])
            yearly_rows(rows, era, ysl, n, "raw", x)
            if round(100 * np.isfinite(x).sum() / len(x), 3) != a4pct[n]: cov_mismatch.append(n)
            if n in p.SCALE:
                adj = p.adjust(x, slot, first_i, end_i)
                yearly_rows(rows, era, ysl, n + "__sadj", "adjusted", adj)
                if round(100 * np.isfinite(adj).sum() / len(adj), 3) != a4pct[n + "__sadj"]: cov_mismatch.append(n + "__sadj")
            if (i + 1) % 20 == 0: log(f"{era}: {i+1}/{len(p.NAMES)} raw columns done")
    finally:
        shutil.rmtree(folder, ignore_errors=True)
    return rows, cov_mismatch, yl


def sidecar_ok(path):
    side = Path(path).with_suffix(".sha256")
    if not side.exists(): return None
    lines = [l.split(None, 1) for l in side.read_text().splitlines() if l.strip()]
    mine = [h for h, n in lines if n.strip() == Path(path).name]
    return bool(mine) and mine[0] == sha(path)


def main():
    reuse = OUT_YEARLY.exists()  # the 4.3.6 file of the first run is kept (log: a4_sec4_3_6_run_log.txt); only the matrix part is rerun
    s.refuse_overwrite(*[f for f in OUT_FILES if not (reuse and f == OUT_YEARLY)])
    elig = load(R / "a4_sec4_3_7_eligibility.json")
    g3c = load(R / "a5_jump_variation_redundancy_corrected.json")
    a4red, a5jv, a4rep = load(R / "a4_sec4_3_8_redundancy.json"), load(R / "a5_jump_variation_redundancy.json"), load(R / "a4_sec4_3_4_7_8_report.json")
    pool = pd.read_csv(R / "a4_sec4_3_pool_matrix.csv").set_index("column")
    assert list(pool.index) == p.POOL

    # ---- 4.3.6
    if not reuse:
        all_rows = []
        for era in ("RAW", "LEGACY"):
            rws, mm, yl = era_yearly(era, elig["coverage_pct"][era])
            all_rows += rws
        pd.DataFrame(all_rows).to_csv(OUT_YEARLY, index=False)
    yearly = pd.read_csv(OUT_YEARLY, dtype={"year": str})
    years = {e: sorted(yearly[yearly.era == e].year.unique().tolist()) for e in ("RAW", "LEGACY")}
    fin = yearly.groupby(["era", "column"]).n_finite.sum()
    pct_now = {e: {n: round(100 * int(fin[(e, n)]) / q.TRAIN_ROWS[e], 3) for n in p.POOL} for e in years}  # coverage recomputed from the data in the 4.3.6 file
    cov_changed = {e: sorted(n for n in p.POOL if pct_now[e][n] != elig["coverage_pct"][e][n]) for e in years}
    log(f"4.3.6: {len(yearly)} rows (reused: {reuse}); coverage differs from the A4 run for {cov_changed}")

    # ---- 4.3.9
    dic = {x["output"]: x for x in load(q.one("section_4_3_1_closing_report_2*.json"))["feature_dictionary"]}
    a3m = pd.read_csv(R / "sec4_3_9_frozen_matrix.csv").set_index("output")
    word = lambda x: str(x).split(":")[0]
    kept_s, dropped_s = g3c["kept"], g3c["dropped"]  # RAW sensitivity outcome of the corrected A5 G3 run
    kept_p, dropped_p = a4red["primary"]["kept"], a4red["primary"]["dropped"]
    rows = []
    for n in p.POOL:
        raw = n.replace("__sadj", ""); d0 = dic[raw]; adj = n.endswith("__sadj"); pr = pool.loc[n]
        def outcome(kept, dropped, in_set):
            if not in_set: return "not in set"
            if n in kept: return "kept"
            h = dropped[n][0]
            return f"dropped: redundant with {h['kept_column']} (rho {h['rho']}, {h['era']})"
        rows.append(dict(column=n, kind="adjusted" if adj else "raw", raw_column=raw,
                         feature_class="adjusted" if adj else a3m.loc[raw, "feature_class"], adjusted_column="" if adj or raw not in p.SCALE else raw + "__sadj",
                         lookback_bars=d0["lookback_bars"], lookback_sessions=20 if adj else d0["lookback_sessions"],
                         min_valid_obs=(d0["min_valid_obs"] + "; baseline needs 10 of the previous 20 sessions") if adj else d0["min_valid_obs"],
                         warmup=d0["warmup"].replace("session 0", "session 10") if adj else d0["warmup"],
                         coverage_LEGACY_pct=pct_now["LEGACY"][n], coverage_RAW_pct=pct_now["RAW"][n],
                         primary_eligible=bool(pct_now["LEGACY"][n] >= 80 and pct_now["RAW"][n] >= 80), sensitivity_eligible=True,
                         primary_outcome=outcome(kept_p, dropped_p, pct_now["LEGACY"][n] >= 80 and pct_now["RAW"][n] >= 80), sensitivity_outcome=outcome(kept_s, dropped_s, True),
                         outputs="a4_sec4_3_4_checks.json; a4_sec4_3_6_yearly_median_iqr.csv; a4_sec4_3_7_eligibility.json; a4_sec4_3_8_redundancy.json (primary); a5_jump_variation_redundancy_corrected.json (RAW sensitivity, after A5 G3)"))
    mat = pd.DataFrame(rows)
    mat.to_csv(OUT_MATRIX, index=False)
    mat[mat.primary_eligible][["column", "kind", "feature_class", "lookback_bars", "coverage_LEGACY_pct", "coverage_RAW_pct", "primary_outcome"]].to_csv(OUT_PRIMARY, index=False)
    mat[["column", "kind", "feature_class", "lookback_bars", "coverage_RAW_pct", "sensitivity_outcome"]].to_csv(OUT_SENS, index=False)

    # ---- checks and hashes
    cited = {"approval_of_A1": q.one("approval_4_3_0_A1_2*.json"), "A2": q.one("amendment_4_3_1_A2_*.json"), "A3": q.one("amendment_4_3_A3_2*.json"), "A4": q.one("amendment_4_3_A4_2*.json"),
             "A5": q.one("amendment_4_3_A5_2*.json"), "P1": q.one("policy_4_3_1_P1_2*.json"), "N1": q.one("note_4_3_N1_2*.json"), "N2": q.one("note_4_3_N2_2*.json"), "N3": q.one("note_4_3_N3_2*.json"),
             "closing_report_4_3_1": q.one("section_4_3_1_closing_report_2*.json"), "closing_report_4_3": q.one("section_4_3_closing_report_section4_2*.json")}
    inputs = {**cited, "a4_4_3_4_checks": R / "a4_sec4_3_4_checks.json", "a4_4_3_7_eligibility": R / "a4_sec4_3_7_eligibility.json", "a4_4_3_8_redundancy": R / "a4_sec4_3_8_redundancy.json",
              "a4_4_3_8_spearman_RAW_pool": R / "a4_sec4_3_8_spearman_RAW_pool.csv", "a4_4_3_8_spearman_primary_LEGACY": R / "a4_sec4_3_8_spearman_primary_LEGACY.csv",
              "a4_4_3_8_overlap_RAW_pool": R / "a4_sec4_3_8_overlap_RAW_pool.csv", "a4_4_3_8_overlap_primary_LEGACY": R / "a4_sec4_3_8_overlap_primary_LEGACY.csv",
              "a4_pool_matrix": R / "a4_sec4_3_pool_matrix.csv", "a4_4_3_4_7_8_report": R / "a4_sec4_3_4_7_8_report.json", "a5_jump_variation_redundancy": R / "a5_jump_variation_redundancy.json",
              "a5_jump_variation_redundancy_corrected": R / "a5_jump_variation_redundancy_corrected.json", "a5_jump_variation_spearman_RAW_pool_corrected": R / "a5_jump_variation_spearman_RAW_pool_corrected.csv",
              "4_3_6_first_run_log": R / "a4_sec4_3_6_run_log.txt"}
    n_years = sum(len(v) for v in years.values())
    checks = {
        "matrix has 113 rows: 78 raw + 35 adjusted": len(mat) == 113 and int((mat.kind == "raw").sum()) == 78 and int((mat.kind == "adjusted").sum()) == 35,
        "raw_volume, log_raw_volume, raw_volume__sadj, overnight_return_open are not in the matrix": not ({"raw_volume", "log_raw_volume", "raw_volume__sadj", "overnight_return_open"} & set(mat.column)),
        "primary kept = 19 and sensitivity kept = 83": len(kept_p) == 19 and len(kept_s) == 83 and a4rep["subsections"]["4.3.8"]["primary"]["kept"] == 19 and a4rep["subsections"]["4.3.8"]["sensitivity_RAW"]["kept"] == 83,
        "corrected A5 G3 sensitivity outcome equals the A4 outcome (the jump_variation change moved no column)": set(g3c["kept"]) == set(a4red["sensitivity_RAW"]["kept"]) and set(a5jv["kept"]) == set(g3c["kept"]),
        "primary eligibility recomputed from the 4.3.6 coverage equals the A4 primary pool": sorted(mat[mat.primary_eligible].column) == sorted(elig["primary_pool"]),
        "matrix outcomes equal the A4 pool matrix (primary and sensitivity)": all(word(mat.set_index("column").loc[n, "primary_outcome"]) == word(pool.loc[n, "primary_outcome"]) and word(mat.set_index("column").loc[n, "sensitivity_outcome"]) == word(pool.loc[n, "sensitivity_outcome"]) for n in p.POOL),
        "4.3.6 has one row per era, year and pool column": len(yearly) == n_years * 113,
        "coverage recomputed from the 4.3.6 data differs from the A4 run only for jump_variation_w__sadj, and the RAW values equal the corrected G3 file": all(n.startswith("jump_variation_") and n.endswith("__sadj") for e in cov_changed for n in cov_changed[e]) and all(abs(pct_now["RAW"][n] - g3c["coverage_changes_RAW"][n]["now"]) < 1e-9 for n in cov_changed["RAW"]) and sorted(cov_changed["RAW"]) == sorted(g3c["coverage_changes_RAW"]),
        "sidecar hashes of the cited amendments, notes, policy, approval and closing reports verify": all(sidecar_ok(f) in (True, None) for f in cited.values()),
        "matrix has all A3 fields": all(c in mat.columns for c in ["feature_class", "adjusted_column", "lookback_bars", "min_valid_obs", "warmup", "coverage_LEGACY_pct", "coverage_RAW_pct", "primary_eligible", "sensitivity_eligible", "primary_outcome", "sensitivity_outcome"]),
    }
    now = datetime.datetime.now(datetime.timezone.utc)
    report = dict(created_utc=now.isoformat(), scope="TRAIN only; RAW then LEGACY; 113-column pool under A4 and A5",
                  sections={"4.3.6": dict(status="DESCRIPTIVE", rows=int(len(yearly)), columns=113, era_years={e: years[e] for e in years}),
                            "4.3.9": dict(status="PASS" if all(checks.values()) else "FAIL", checks=checks, rows=int(len(mat)), primary_view_rows=int(mat.primary_eligible.sum()), sensitivity_view_rows=int(len(mat)),
                                          primary_kept=len(kept_p), primary_dropped=len(dropped_p), sensitivity_kept=len(kept_s), sensitivity_dropped=len(dropped_s))},
                  overall="PASS" if all(checks.values()) else "FAIL", primary_kept=kept_p, sensitivity_kept=kept_s,
                  coverage_changes_versus_A4_run={e: {n: dict(A4_run=elig["coverage_pct"][e][n], now=pct_now[e][n]) for n in cov_changed[e]} for e in cov_changed},
                  history=["The first run computed 4.3.6 (kept, log a4_sec4_3_6_run_log.txt) and wrote a matrix that failed the coverage cross-check: the A5 G3 scaling makes about half of the jump_variation values exactly 0, so jump_variation_w__sadj lost coverage.",
                           "Step 13 (A5 G3) had ranked columns with the A4-run coverage; step 16 repeated it with current coverage and found the same sensitivity outcome (keep 83, drop 30). The matrix was then rebuilt from the kept 4.3.6 file and the corrected G3 outcome."],
                  output_hashes=[dict(file=f.name, sha256=sha(f)) for f in (OUT_YEARLY, OUT_MATRIX, OUT_PRIMARY, OUT_SENS)],
                  input_hashes=[dict(name=k, file=v.name, sha256=sha(v)) for k, v in inputs.items()],
                  freeze="The matrix is written once and never edited; any change needs a new dated amendment.")
    OUT_REPORT.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    md = ["# 4.3.6 and 4.3.9 regenerated under A4 and A5", "", f"Run {now.isoformat()} UTC. TRAIN only, RAW then LEGACY. Pool: 78 raw + 35 adjusted = 113 columns. Overall: **{report['overall']}**.", "",
          f"- 4.3.6 (descriptive): {len(yearly)} rows ({n_years} era-years x 113 columns).",
          f"- 4.3.9: {len(mat)}-row matrix; primary view {int(mat.primary_eligible.sum())} rows (kept {len(kept_p)}, dropped {len(dropped_p)}); sensitivity view {len(mat)} rows (kept {len(kept_s)}, dropped {len(dropped_s)}).", "",
          "| Check | Result |", "|---|---|"] + [f"| {k} | {'PASS' if v else 'FAIL'} |" for k, v in checks.items()] + \
         ["", "## Output hashes (SHA-256)", "", "| File | SHA-256 |", "|---|---|"] + [f"| {h['file']} | `{h['sha256']}` |" for h in report["output_hashes"]] + \
         ["", "## Input hashes (SHA-256)", "", "| Input | File | SHA-256 |", "|---|---|---|"] + [f"| {h['name']} | {h['file']} | `{h['sha256']}` |" for h in report["input_hashes"]]
    (R / "a4_sec4_3_6_9_report.md").write_text("\n".join(md) + "\n", encoding="utf-8")
    (R / "a4_sec4_3_6_9_report.sha256").write_text(f"{sha(OUT_REPORT)}  {OUT_REPORT.name}\n{sha(R / 'a4_sec4_3_6_9_report.md')}  a4_sec4_3_6_9_report.md\n", encoding="ascii")
    print("\n".join(md[:16]))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
