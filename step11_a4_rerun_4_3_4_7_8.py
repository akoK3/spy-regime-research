#!/usr/bin/env python3
"""A4 F2 + F5: rerun 4.3.4, 4.3.7 and 4.3.8 with the causal seasonal baseline and without the diagnostics-only volume columns.
TRAIN only, RAW then LEGACY. Outputs are prefixed a4_ and are never overwritten.

__sadj = raw / median of the same slot over the previous 20 sessions of the same era (at least 10 finite), NaN if the baseline is
missing or <= 0. Pool = 78 raw detector columns + 35 adjusted = 113 (raw_volume, log_raw_volume, raw_volume__sadj are out).
4.3.7 and 4.3.8 follow A3 unchanged with note N2's tie-break (adjusted columns take positions 80-115, raw wins ties)."""
import sys, json, hashlib, datetime, shutil, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step8_sections_4_3_4_to_4_3_9 as q  # noqa: E402

R, ERAS, log, sha = q.R, q.ERAS, q.log, q.sha
A4_FILE = q.one("amendment_4_3_A4_2*.json")
assert A4_FILE.with_suffix(".sha256").read_text().split()[0] == sha(A4_FILE), "A4 hash mismatch"
DIAG = ("raw_volume", "log_raw_volume")
NAMES = [n for n in q.NAMES if n not in DIAG]
SCALE = [n for n in q.SCALE if n not in DIAG]
POOL = NAMES + [n + "__sadj" for n in SCALE]
assert (len(NAMES), len(SCALE), len(POOL)) == (78, 35, 113)
for n in SCALE:
    q.INP[n + "__sadj"] = dict(lookback_bars=q.INP[n]["lookback_bars"], dictionary_position=80 + q.SCALE.index(n))
OUT = []
WINDOW, MIN_COUNT = 20, 10


def write(name, content, label):
    p = R / name
    p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    OUT.append((label, p))
    return p


def sessions(slot):
    first = np.flatnonzero(slot == 0)
    return first, np.r_[first[1:], len(slot)]


def adjust(x, slot, first, end):
    """Vectorised causal baseline."""
    ns = len(first)
    M = np.full((ns, q.SLOTS), np.nan)
    for k, (a, b) in enumerate(zip(first, end)):
        M[k, slot[a:b]] = x[a:b]
    base = np.full(len(x), np.nan)
    for k, (a, b) in enumerate(zip(first, end)):
        if k == 0: continue
        prev = M[max(0, k - WINDOW):k]
        cnt = np.isfinite(prev).sum(axis=0)
        med = np.full(q.SLOTS, np.nan)
        good = cnt >= MIN_COUNT
        if good.any(): med[good] = np.nanmedian(prev[:, good], axis=0)
        base[a:b] = med[slot[a:b]]
    return x / np.where(np.isfinite(base) & (base > 0), base, np.nan)


def brute_cell(x, slot, first, end, row):
    """Independent per-cell recomputation: explicit loop over the previous sessions."""
    k = int(np.searchsorted(first, row, side="right") - 1)
    s = slot[row]; vals = []
    for j in range(max(0, k - WINDOW), k):
        idx = first[j] + s
        if idx < end[j] and np.isfinite(x[idx]): vals.append(x[idx])
    if len(vals) < MIN_COUNT or not np.isfinite(x[row]): return np.nan
    med = float(np.median(vals))
    return x[row] / med if med > 0 else np.nan


def era_run(era, st, rng):
    slot = st["slot"]; first, end = sessions(slot)
    checks = dict(brute_force_cells=0, brute_force_mismatches=[], prefix_invariance_mismatches=[], first_10_sessions_all_nan=True)
    counts, cov_cmp = {}, {}
    cuts = sorted(int(k) for k in rng.choice(np.arange(40, len(first) - 1), size=2, replace=False))
    prefix_cols = set(rng.choice(SCALE, size=6, replace=False).tolist())
    for i, n in enumerate(SCALE):
        x = q.load_col(st, n)
        adj = adjust(x, slot, first, end)
        np.save(st["folder"] / f"{n}__sadj.npy", adj)
        counts[n + "__sadj"] = int(np.isfinite(adj).sum())
        cov_cmp[n] = dict(raw_pct=round(100 * st["finite"][n] / st["rows"], 3), adjusted_pct=round(100 * counts[n + "__sadj"] / st["rows"], 3))
        if np.isfinite(adj[:end[9]]).any(): checks["first_10_sessions_all_nan"] = False
        rows = rng.choice(np.arange(first[1], len(x)), size=3000, replace=False)
        for r in rows:
            ref = brute_cell(x, slot, first, end, int(r))
            if not (np.isnan(ref) and np.isnan(adj[r])) and not np.isclose(ref, adj[r], rtol=1e-12, atol=0): checks["brute_force_mismatches"].append(f"{n}@{int(r)}")
        checks["brute_force_cells"] += len(rows)
        if n in prefix_cols:
            for K in cuts:
                cut = int(first[K])
                part = adjust(x[:cut], slot[:cut], first[:K], np.r_[first[1:K], cut])
                if not np.allclose(part, adj[:cut], rtol=1e-12, atol=0, equal_nan=True): checks["prefix_invariance_mismatches"].append(f"{n}: cut at session {K}")
        if (i + 1) % 10 == 0: log(f"{era}: adjusted columns {i+1}/{len(SCALE)}")
    checks["prefix_cuts_sessions"] = cuts; checks["prefix_columns"] = sorted(prefix_cols)
    checks["status"] = "PASS" if (not checks["brute_force_mismatches"] and not checks["prefix_invariance_mismatches"] and checks["first_10_sessions_all_nan"]) else "FAIL"
    return counts, cov_cmp, checks


def main():
    q.s.refuse_overwrite(*sorted(R.glob("a4_sec4_3_*")))
    rng = np.random.default_rng(43108)
    pct, rhos, overlaps, finite, checks434, cov_cmp = {}, {}, {}, {}, {}, {}
    primary_pool = None
    for era in ERAS:
        st = q.prepare_era(era)
        log(f"{era}: building the {len(SCALE)} causal adjusted columns and checking them")
        counts, cov_cmp[era], checks434[era] = era_run(era, st, rng)
        log(f"{era}: 4.3.4 checks {checks434[era]['status']} ({checks434[era]['brute_force_cells']} brute-force cells)")
        finite[era] = {**{n: st["finite"][n] for n in NAMES}, **counts}
        pct[era] = {n: round(100 * finite[era][n] / st["rows"], 3) for n in POOL}
        if era == "RAW":
            log("RAW: 4.3.8 Spearman, 113 columns")
            rhos["RAW"], overlaps["RAW"] = q.spearman_matrix(st, POOL, "RAW pool 113")
        else:
            primary_pool = [n for n in POOL if all(pct[e][n] >= 80 for e in ERAS)]
            log(f"LEGACY: primary pool has {len(primary_pool)} columns; 4.3.8 Spearman")
            rhos["LEGACY"], overlaps["LEGACY"] = q.spearman_matrix(st, primary_pool, "LEGACY primary pool")

    primary_raw = [n for n in primary_pool if not n.endswith("__sadj")]
    step6_pass = [c for c, v in q.COV.items() if v["status"] == "PASS" and c in NAMES]
    own_vs_raw = {n: {e: (pct[e][n + "__sadj"], pct[e][n]) for e in ERAS} for n in SCALE}
    elig_checks = {
        "pool has 78 raw and 35 adjusted columns": len(NAMES) == 78 and len(SCALE) == 35 and len(POOL) == 113,
        "none of raw_volume, log_raw_volume, raw_volume__sadj, overnight_return_open is in the pool": not ({"raw_volume", "log_raw_volume", "raw_volume__sadj", "overnight_return_open"} & set(POOL)),
        "primary raw columns equal the Step 6 PASS columns among the 78": sorted(primary_raw) == sorted(step6_pass),
    }
    elig = dict(pool=len(POOL), primary_pool=primary_pool, sensitivity_pool_RAW=POOL, coverage_pct=pct, adjusted_vs_raw_coverage_pct=own_vs_raw, checks=elig_checks)
    write("a4_sec4_3_7_eligibility.json", json.dumps(elig, indent=2) + "\n", "4.3.7 eligibility, 113-column pool")

    rhoR, rhoL = rhos["RAW"], rhos["LEGACY"]
    rho_primary = {"LEGACY": rhoL, "RAW": rhoR.loc[primary_pool, primary_pool]}
    order_p, kept_p, drop_p = q.redundancy(primary_pool, rho_primary, lambda n: min(pct["LEGACY"][n], pct["RAW"][n]))
    order_s, kept_s, drop_s = q.redundancy(POOL, {"RAW": rhoR}, lambda n: pct["RAW"][n])
    def verify(kept, dropped, rr, cols):
        ok = len(kept) + len(dropped) == len(cols)
        for a in kept:
            for b in kept:
                if a != b and any(np.isfinite(r.loc[a, b]) and abs(r.loc[a, b]) > q.THRESHOLD for r in rr.values()): ok = False
        return ok and all(any(h["kept_column"] in kept for h in hits) for hits in dropped.values())
    split = lambda cols: dict(raw=sum(not c.endswith("__sadj") for c in cols), adjusted=sum(c.endswith("__sadj") for c in cols))
    pairs = [dict(column=n, RAW_rho=round(float(rhoR.loc[n, n + "__sadj"]), 6), LEGACY_rho=round(float(rhoL.loc[n, n + "__sadj"]), 6) if n in rhoL.index and n + "__sadj" in rhoL.index else None) for n in SCALE]
    red = dict(rule="A3 4.3.8 unchanged; adjusted-column positions 80-115 (N2); pool per A4 F5", threshold=q.THRESHOLD,
               primary=dict(pool=len(primary_pool), priority_order=order_p, kept=kept_p, dropped=drop_p, kept_split=split(kept_p), dropped_split=split(list(drop_p))),
               sensitivity_RAW=dict(pool=len(POOL), priority_order=order_s, kept=kept_s, dropped=drop_s, kept_split=split(kept_s), dropped_split=split(list(drop_s))),
               raw_vs_adjusted_rho=pairs, undefined_correlations=dict(RAW=int(np.isnan(rhoR.to_numpy()).sum()), LEGACY_primary_pool=int(np.isnan(rhoL.to_numpy()).sum())),
               checks={"primary: no two kept columns redundant, every dropped column has a kept partner": verify(kept_p, drop_p, rho_primary, primary_pool),
                       "sensitivity: no two kept columns redundant, every dropped column has a kept partner": verify(kept_s, drop_s, {"RAW": rhoR}, POOL)})
    write("a4_sec4_3_8_redundancy.json", json.dumps(red, indent=2) + "\n", "4.3.8 redundancy outcome, 113-column pool")
    for name, df, lab in (("a4_sec4_3_8_spearman_RAW_pool.csv", rhoR, "Spearman, 113 columns, RAW"), ("a4_sec4_3_8_spearman_primary_LEGACY.csv", rhoL, "Spearman, primary pool, LEGACY"),
                          ("a4_sec4_3_8_overlap_RAW_pool.csv", overlaps["RAW"], "pairwise overlap, RAW"), ("a4_sec4_3_8_overlap_primary_LEGACY.csv", overlaps["LEGACY"], "pairwise overlap, LEGACY primary pool")):
        write(name, df.to_csv(), lab)
    write("a4_sec4_3_4_checks.json", json.dumps(dict(definition="raw / median of the same slot over the previous 20 sessions of the era, at least 10 finite; NaN if baseline missing or <= 0",
                                                    eras=checks434, adjusted_vs_raw_coverage_pct=cov_cmp), indent=2) + "\n", "4.3.4 checks and coverage, causal baseline")
    rows = []
    for n in POOL:
        def outcome(kept, dropped, in_set):
            if not in_set: return "not in set"
            if n in kept: return "kept"
            h = dropped[n][0]
            return f"dropped: redundant with {h['kept_column']} (rho {h['rho']}, {h['era']})"
        rows.append(dict(column=n, kind="adjusted" if n.endswith("__sadj") else "raw", raw_column=n.replace("__sadj", ""), lookback_bars=q.INP[n]["lookback_bars"],
                         coverage_LEGACY_pct=pct["LEGACY"][n], coverage_RAW_pct=pct["RAW"][n], primary_eligible=n in primary_pool, sensitivity_eligible=True,
                         primary_outcome=outcome(kept_p, drop_p, n in primary_pool), sensitivity_outcome=outcome(kept_s, drop_s, True)))
    write("a4_sec4_3_pool_matrix.csv", pd.DataFrame(rows).to_csv(index=False), "pool matrix (113 rows)")

    now = datetime.datetime.now(datetime.timezone.utc)
    f2 = "PASS" if all(checks434[e]["status"] == "PASS" for e in ERAS) else "FAIL"
    f5 = "PASS" if elig_checks["pool has 78 raw and 35 adjusted columns"] and elig_checks["none of raw_volume, log_raw_volume, raw_volume__sadj, overnight_return_open is in the pool"] else "FAIL"
    sub = {"F2 4.3.4 causal baseline": dict(status=f2, checks=checks434),
           "4.3.7": dict(status="PASS" if all(elig_checks.values()) else "FAIL", checks=elig_checks, primary_pool=len(primary_pool), sensitivity_pool=len(POOL)),
           "4.3.8": dict(status="PASS" if all(red["checks"].values()) else "FAIL", checks=red["checks"], primary=dict(pool=len(primary_pool), kept=len(kept_p), dropped=len(drop_p), kept_split=red["primary"]["kept_split"], dropped_split=red["primary"]["dropped_split"]),
                         sensitivity_RAW=dict(pool=len(POOL), kept=len(kept_s), dropped=len(drop_s), kept_split=red["sensitivity_RAW"]["kept_split"], dropped_split=red["sensitivity_RAW"]["dropped_split"])),
           "F5 pool without diagnostics-only volume columns": dict(status=f5)}
    hashes = [dict(label=l, file=p.name, sha256=sha(p)) for l, p in OUT]
    report = dict(created_utc=now.isoformat(), amendment_A4=dict(file=A4_FILE.name, sha256=sha(A4_FILE)), scope="TRAIN only; RAW then LEGACY; pool 113",
                  subsections=sub, overall="PASS" if all(v["status"] == "PASS" for v in sub.values()) else "FAIL", output_hashes=hashes)
    rp = R / "a4_sec4_3_4_7_8_report.json"
    rp.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    sp, ss = sub["4.3.8"]["primary"], sub["4.3.8"]["sensitivity_RAW"]
    L = ["# 4.3.4, 4.3.7, 4.3.8 rerun under amendment A4 (causal seasonal baseline, 113-column pool)", "", f"Run {now.isoformat()} UTC. TRAIN only, RAW then LEGACY. A4 `{A4_FILE.name}` SHA-256 `{sha(A4_FILE)}`.", "",
         f"F2 (4.3.4 checks): {f2}. 4.3.7: {sub['4.3.7']['status']}. 4.3.8: {sub['4.3.8']['status']}. F5 (pool): {f5}. Overall: **{report['overall']}**.", "",
         "| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |", "|---|---|---|---|---|---|",
         f"| Primary | {sp['pool']} | {sp['kept']} | {sp['dropped']} | {sp['kept_split']['raw']} / {sp['kept_split']['adjusted']} | {sp['dropped_split']['raw']} / {sp['dropped_split']['adjusted']} |",
         f"| RAW sensitivity | {ss['pool']} | {ss['kept']} | {ss['dropped']} | {ss['kept_split']['raw']} / {ss['kept_split']['adjusted']} | {ss['dropped_split']['raw']} / {ss['dropped_split']['adjusted']} |", "",
         "## Primary set kept", "", ", ".join(kept_p), "", "## Primary set dropped", ""] + [f"- {k}: redundant with {v[0]['kept_column']} (rho {v[0]['rho']}, {v[0]['era']})" for k, v in drop_p.items()]
    L += ["", "## Output hashes (SHA-256)", "", "| Output | File | SHA-256 |", "|---|---|---|"] + [f"| {h['label']} | {h['file']} | `{h['sha256']}` |" for h in hashes]
    mp = R / "a4_sec4_3_4_7_8_report.md"
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    (R / "a4_sec4_3_4_7_8_report.sha256").write_text(f"{sha(rp)}  {rp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    shutil.rmtree(q.TMP, ignore_errors=True)
    log("done")
    print("\n".join(L[:14]))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
