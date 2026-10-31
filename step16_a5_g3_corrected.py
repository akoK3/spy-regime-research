#!/usr/bin/env python3
"""Correction of the A5 G3 redundancy rerun (step13). Step 13 ranked columns by the coverage of the A4 run, but the w/(w-1) scaling of
jump_variation makes about half of its values exactly 0, so the median baseline of jump_variation_w__sadj is 0 on many slots and its adjusted
coverage fell. This script recomputes the RAW coverage of every pool column from the data, repeats the pair patch and the greedy rule with
that coverage, and compares the outcome with the A4 run and with the original G3 result. The original G3 files are not edited."""
import sys, json, hashlib, datetime, shutil, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step13_a5_jump_variation_redundancy as g3  # noqa: E402

p, q, R, log, sha = g3.p, g3.q, g3.R, g3.log, g3.sha
OUTJ, OUTM, OUTC = R / "a5_jump_variation_redundancy_corrected.json", R / "a5_jump_variation_redundancy_corrected.md", R / "a5_jump_variation_spearman_RAW_pool_corrected.csv"


def main():
    q.s.refuse_overwrite(OUTJ, OUTM, OUTC)
    a4 = json.loads((R / "a4_sec4_3_7_eligibility.json").read_text(encoding="utf-8"))
    a4red = json.loads((R / "a4_sec4_3_8_redundancy.json").read_text(encoding="utf-8"))
    orig = json.loads((R / "a5_jump_variation_redundancy.json").read_text(encoding="utf-8"))
    rho_old = pd.read_csv(R / "a4_sec4_3_8_spearman_RAW_pool.csv", index_col=0)
    log("RAW: features with the scaled jump_variation")
    st = q.prepare_era("RAW")
    slot = st["slot"]; first, end = p.sessions(slot)
    X = {n: q.load_col(st, n) for n in p.NAMES}
    def col(n):
        if n not in X: X[n] = p.adjust(X[n[:-6]], slot, first, end)
        return X[n]
    pct = {n: round(100 * np.isfinite(col(n)).sum() / st["rows"], 3) for n in p.POOL}
    changed_cov = {n: dict(A4_run=a4["coverage_pct"]["RAW"][n], now=pct[n]) for n in p.POOL if pct[n] != a4["coverage_pct"]["RAW"][n]}
    zero_share = {}
    for w in (15, 30, 60):
        x = X[f"jump_variation_{w}"]; fin = np.isfinite(x)
        zero_share[f"jump_variation_{w}"] = round(float((x[fin] == 0).mean()), 4)
    log(f"coverage differs from the A4 run for {len(changed_cov)} columns: {sorted(changed_cov)}")
    rho_new = rho_old.copy()
    for a in g3.CHANGED:
        xa = col(a)
        for b in p.POOL:
            if b != a:
                v = g3.rho(xa, col(b)); rho_new.loc[a, b] = rho_new.loc[b, a] = v
    rng = np.random.default_rng(43112)
    others = [c for c in p.POOL if c not in g3.CHANGED]
    mism = []
    for _ in range(150):
        a, b = rng.choice(others, size=2, replace=False)
        if not np.isclose(g3.rho(col(a), col(b)), rho_old.loc[a, b], rtol=1e-9, atol=1e-12, equal_nan=True): mism.append((a, b))
    order, kept, dropped = q.redundancy(p.POOL, {"RAW": rho_new}, lambda n: pct[n])
    rho_new.to_csv(OUTC)
    diff = lambda a_kept: dict(newly_kept=sorted(set(kept) - set(a_kept)), newly_dropped=sorted(set(p.POOL) - set(kept) - (set(p.POOL) - set(a_kept))))
    vs_a4 = dict(newly_kept=sorted(set(kept) - set(a4red["sensitivity_RAW"]["kept"])), newly_dropped=sorted(set(a4red["sensitivity_RAW"]["kept"]) - set(kept)))
    vs_orig = dict(newly_kept=sorted(set(kept) - set(orig["kept"])), newly_dropped=sorted(set(orig["kept"]) - set(kept)))
    primary_has = [c for c in a4["primary_pool"] if c in g3.CHANGED]
    checks = {"sample of 150 unchanged pairs equals the A4 run": not mism, "greedy rule consistent": len(kept) + len(dropped) == len(p.POOL),
              "coverage differs from the A4 run only for jump_variation_w__sadj": all(c.startswith("jump_variation_") and c.endswith("__sadj") for c in changed_cov),
              "no jump_variation column is in the A4 primary pool": not primary_has}
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A5 G3 correction", status="PASS" if all(checks.values()) else "FAIL",
               reason="Step 13 ranked columns by the A4-run coverage. After the w/(w-1) scaling about half of the jump_variation values are exactly 0, so the median baseline is 0 on many slots and jump_variation_w__sadj is undefined there; its coverage fell. The corrected run uses the coverage of the current data.",
               original_g3_file="a5_jump_variation_redundancy.json", original_g3_sha256=sha(R / "a5_jump_variation_redundancy.json"),
               share_of_exactly_zero_values_among_finite_RAW=zero_share, coverage_changes_RAW=changed_cov,
               sensitivity_RAW=dict(pool=len(p.POOL), kept=len(kept), dropped=len(dropped), A4_run=dict(kept=len(a4red["sensitivity_RAW"]["kept"]), dropped=len(a4red["sensitivity_RAW"]["dropped"])),
                                    original_G3=dict(kept=len(orig["kept"]), dropped=len(orig["dropped"])), changes_vs_A4_run=vs_a4, changes_vs_original_G3=vs_orig),
               primary_set="unchanged: no jump_variation column is in the primary pool" if not primary_has else "NEEDS REVIEW", checks=checks, priority_order=order, kept=kept, dropped=dropped,
               spearman_matrix_file=OUTC.name, spearman_matrix_sha256=sha(OUTC))
    OUTJ.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    md = ["# A5 G3 redundancy: corrected run", "", f"Status: **{doc['status']}**. {doc['reason']}", "",
          f"Share of exactly-zero values among finite RAW values: {zero_share}.", "", "RAW coverage changes (percent): " + "; ".join(f"{k}: {v['A4_run']} -> {v['now']}" for k, v in changed_cov.items()), "",
          f"RAW sensitivity (113 columns): kept {len(kept)} / dropped {len(dropped)}. A4 run: kept {len(a4red['sensitivity_RAW']['kept'])} / dropped {len(a4red['sensitivity_RAW']['dropped'])}. Original G3: kept {len(orig['kept'])} / dropped {len(orig['dropped'])}.",
          f"Changes versus the A4 run: newly kept {vs_a4['newly_kept'] or 'none'}; newly dropped {vs_a4['newly_dropped'] or 'none'}.",
          f"Changes versus the original G3 result: newly kept {vs_orig['newly_kept'] or 'none'}; newly dropped {vs_orig['newly_dropped'] or 'none'}.", "", f"Primary set: {doc['primary_set']}."]
    OUTM.write_text("\n".join(md) + "\n", encoding="utf-8")
    (R / "a5_jump_variation_redundancy_corrected.sha256").write_text(f"{sha(OUTJ)}  {OUTJ.name}\n{sha(OUTM)}  {OUTM.name}\n{sha(OUTC)}  {OUTC.name}\n", encoding="ascii")
    shutil.rmtree(q.TMP, ignore_errors=True)
    print("\n".join(md))
    return 0 if doc["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
