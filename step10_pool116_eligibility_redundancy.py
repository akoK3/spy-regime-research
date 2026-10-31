#!/usr/bin/env python3
"""A3's 4.3.7 and 4.3.8 rules, unchanged, applied to the 116-column pool (80 raw + 36 adjusted), as fixed in note 4.3-N2.
TRAIN only, RAW then LEGACY. Reuses the loaders and the Spearman and redundancy routines of the A3 run."""
import sys, json, hashlib, datetime, shutil
from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step8_sections_4_3_4_to_4_3_9 as q  # noqa: E402

R, ERAS, log = q.R, q.ERAS, q.log
sha = q.sha
N2_FILE = q.one("note_4_3_N2_2*.json")
assert N2_FILE.with_suffix(".sha256").read_text().split()[0] == sha(N2_FILE), "N2 hash mismatch"
POOL = q.NAMES + [n + "__sadj" for n in q.SCALE]
assert len(POOL) == 116
for i, n in enumerate(q.SCALE):  # N2: adjusted columns take dictionary positions 80-115, window of the raw column
    q.INP[n + "__sadj"] = dict(lookback_bars=q.INP[n]["lookback_bars"], dictionary_position=80 + i)
OUT = []


def write(name, content, label):
    p = R / name
    p.write_bytes(content.encode("utf-8") if isinstance(content, str) else content)
    OUT.append((label, p))
    return p


def main():
    pct, rhos, overlaps, finite = {}, {}, {}, {}
    primary_pool = None
    for era in ERAS:
        st = q.prepare_era(era)
        log(f"{era}: building the 36 adjusted columns")
        ref = pd.read_csv(R / f"sec4_3_4_slot_medians_{era}.csv")
        slot = st["slot"]
        counts = dict(st["finite"])
        for n in q.SCALE:
            x = q.load_col(st, n); fin = np.isfinite(x)
            m = pd.Series(x[fin]).groupby(slot[fin]).median().reindex(range(q.SLOTS)).to_numpy()
            m = np.where(np.isfinite(m) & (m > 0), m, np.nan)
            assert np.allclose(m, ref[n].to_numpy(), equal_nan=True, rtol=1e-12, atol=0), f"{era}.{n}: medians differ from the 4.3.4 table"
            adj = x / m[slot]
            np.save(st["folder"] / f"{n}__sadj.npy", adj)
            counts[n + "__sadj"] = int(np.isfinite(adj).sum())
        finite[era] = counts
        pct[era] = {n: round(100 * counts[n] / st["rows"], 3) for n in POOL}
        if era == "RAW":
            log("RAW: 4.3.8 Spearman, all 116 columns")
            rhos["RAW"], overlaps["RAW"] = q.spearman_matrix(st, POOL, "RAW pool 116x116")
        else:
            primary_pool = [n for n in POOL if all(pct[e][n] >= 80 for e in ERAS)]
            log(f"LEGACY: primary pool has {len(primary_pool)} columns; 4.3.8 Spearman")
            rhos["LEGACY"], overlaps["LEGACY"] = q.spearman_matrix(st, primary_pool, "LEGACY primary pool")

    # ---- 4.3.7
    primary_raw = [n for n in primary_pool if not n.endswith("__sadj")]
    inherit = all(pct[e][n + "__sadj"] == pct[e][n] for n in q.SCALE for e in ERAS)
    elig_checks = {
        "primary raw columns equal A3's 20 (Step 6 PASS)": sorted(primary_raw) == sorted(q.PRIMARY),
        "adjusted coverage equals raw coverage in both eras (N1 inheritance holds)": inherit,
        "primary adjusted columns are exactly the adjusted versions of the primary scale columns": sorted(n for n in primary_pool if n.endswith("__sadj")) == sorted(n + "__sadj" for n in q.SCALE if n in q.PRIMARY),
        "overnight_return_open is not in the pool": "overnight_return_open" not in POOL,
    }
    elig = dict(pool=len(POOL), primary_pool=primary_pool, sensitivity_pool_RAW=POOL, coverage_pct=pct, checks=elig_checks)
    write("sec4_3_7_8_pool116_eligibility.json", json.dumps(elig, indent=2) + "\n", "4.3.7 pool eligibility")

    # ---- 4.3.8
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
    pairs = []
    for n in q.SCALE:
        a = n + "__sadj"
        pairs.append(dict(column=n, RAW_rho=round(float(rhoR.loc[n, a]), 6), LEGACY_rho=round(float(rhoL.loc[n, a]), 6) if n in rhoL.index and a in rhoL.index else None))
    def split(cols):
        return dict(raw=sum(not c.endswith("__sadj") for c in cols), adjusted=sum(c.endswith("__sadj") for c in cols))
    red = dict(rule="A3 4.3.8 unchanged; adjusted-column positions 80-115 (N2)", threshold=q.THRESHOLD, note=dict(file=N2_FILE.name, sha256=sha(N2_FILE)),
               primary=dict(pool=len(primary_pool), priority_order=order_p, kept=kept_p, dropped=drop_p, kept_split=split(kept_p), dropped_split=split(list(drop_p))),
               sensitivity_RAW=dict(pool=len(POOL), priority_order=order_s, kept=kept_s, dropped=drop_s, kept_split=split(kept_s), dropped_split=split(list(drop_s))),
               raw_vs_adjusted_rho=pairs,
               undefined_correlations=dict(RAW=int(np.isnan(rhoR.to_numpy()).sum()), LEGACY_primary_pool=int(np.isnan(rhoL.to_numpy()).sum())),
               checks={"primary: no two kept columns redundant, every dropped column has a kept partner": verify(kept_p, drop_p, rho_primary, primary_pool),
                       "sensitivity: no two kept columns redundant, every dropped column has a kept partner": verify(kept_s, drop_s, {"RAW": rhoR}, POOL)})
    write("sec4_3_7_8_pool116_redundancy.json", json.dumps(red, indent=2) + "\n", "4.3.8 pool redundancy outcome")
    for name, df, lab in (("sec4_3_7_8_pool116_spearman_RAW.csv", rhoR, "Spearman, 116 columns, RAW"), ("sec4_3_7_8_pool116_spearman_primary_LEGACY.csv", rhoL, "Spearman, primary pool, LEGACY"),
                          ("sec4_3_7_8_pool116_overlap_RAW.csv", overlaps["RAW"], "pairwise overlap, RAW"), ("sec4_3_7_8_pool116_overlap_primary_LEGACY.csv", overlaps["LEGACY"], "pairwise overlap, LEGACY primary pool")):
        write(name, df.to_csv(), lab)
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
    write("sec4_3_7_8_pool116_matrix.csv", pd.DataFrame(rows).to_csv(index=False), "pool matrix (116 rows)")

    now = datetime.datetime.now(datetime.timezone.utc)
    sub = {"4.3.7": dict(status="PASS" if all(elig_checks.values()) else "FAIL", checks=elig_checks, primary_pool=len(primary_pool), sensitivity_pool=len(POOL)),
           "4.3.8": dict(status="PASS" if all(red["checks"].values()) else "FAIL", checks=red["checks"],
                         primary=dict(pool=len(primary_pool), kept=len(kept_p), dropped=len(drop_p), kept_split=red["primary"]["kept_split"], dropped_split=red["primary"]["dropped_split"]),
                         sensitivity_RAW=dict(pool=len(POOL), kept=len(kept_s), dropped=len(drop_s), kept_split=red["sensitivity_RAW"]["kept_split"], dropped_split=red["sensitivity_RAW"]["dropped_split"]))}
    hashes = [dict(label=l, file=p.name, sha256=sha(p)) for l, p in OUT]
    report = dict(created_utc=now.isoformat(), note_N2=dict(file=N2_FILE.name, sha256=sha(N2_FILE)), scope="TRAIN only; RAW then LEGACY; 116-column pool; overnight_return_open excluded",
                  subsections=sub, overall="PASS" if all(v["status"] == "PASS" for v in sub.values()) else "FAIL", output_hashes=hashes)
    rp = R / "sec4_3_7_8_pool116_report.json"
    rp.write_bytes((json.dumps(report, indent=2) + "\n").encode("utf-8"))
    sp, ss = sub["4.3.8"]["primary"], sub["4.3.8"]["sensitivity_RAW"]
    L = ["# 4.3.7 and 4.3.8 on the 116-column pool (A3 unchanged, note N2)", "",
         f"Run {now.isoformat()} UTC. TRAIN only, RAW then LEGACY. N2 `{N2_FILE.name}` SHA-256 `{sha(N2_FILE)}`.", "",
         "| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |", "|---|---|---|---|---|---|",
         f"| Primary | {sp['pool']} | {sp['kept']} | {sp['dropped']} | {sp['kept_split']['raw']} / {sp['kept_split']['adjusted']} | {sp['dropped_split']['raw']} / {sp['dropped_split']['adjusted']} |",
         f"| RAW sensitivity | {ss['pool']} | {ss['kept']} | {ss['dropped']} | {ss['kept_split']['raw']} / {ss['kept_split']['adjusted']} | {ss['dropped_split']['raw']} / {ss['dropped_split']['adjusted']} |", "",
         f"4.3.7: {sub['4.3.7']['status']}. 4.3.8: {sub['4.3.8']['status']}. Overall: **{report['overall']}**.", "",
         "## Primary set kept", "", ", ".join(kept_p), "", "## Primary set dropped", ""] + [f"- {k}: redundant with {v[0]['kept_column']} (rho {v[0]['rho']}, {v[0]['era']})" for k, v in drop_p.items()]
    L += ["", "## Output hashes (SHA-256)", "", "| Output | File | SHA-256 |", "|---|---|---|"] + [f"| {h['label']} | {h['file']} | `{h['sha256']}` |" for h in hashes]
    mp = R / "sec4_3_7_8_pool116_report.md"
    mp.write_text("\n".join(L) + "\n", encoding="utf-8")
    (R / "sec4_3_7_8_pool116_report.sha256").write_text(f"{sha(rp)}  {rp.name}\n{sha(mp)}  {mp.name}\n", encoding="ascii")
    shutil.rmtree(q.TMP, ignore_errors=True)
    log("done")
    print("\n".join(L[:12]))
    return 0 if report["overall"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
