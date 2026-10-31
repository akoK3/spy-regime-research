#!/usr/bin/env python3
"""A5 G3 (redundancy part): after the w/(w-1) scaling of the bipower term in jump_variation_w, recompute every RAW Spearman pair that involves
jump_variation_w or jump_variation_w__sadj, keep all other pairs from the A4 rerun (after re-checking a random sample of them), and
rerun the 4.3.8 greedy rule for the RAW sensitivity pool. Also runs the bias check on simulated Gaussian windows. TRAIN only."""
import sys, json, hashlib, datetime, shutil, warnings
from pathlib import Path
import numpy as np
import pandas as pd

warnings.simplefilter("ignore")
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step11_a4_rerun_4_3_4_7_8 as p  # noqa: E402

q, R, log, sha = p.q, p.R, p.log, p.sha
OUTJ, OUTM = R / "a5_jump_variation_redundancy.json", R / "a5_jump_variation_redundancy.md"
CHANGED = [f"jump_variation_{w}" for w in (15, 30, 60)]
CHANGED += [c + "__sadj" for c in CHANGED]


def rho(xa, xb):
    m = np.isfinite(xa) & np.isfinite(xb)
    if m.sum() < 3: return np.nan
    ra, rb = pd.Series(xa[m]).rank().to_numpy(), pd.Series(xb[m]).rank().to_numpy()
    ra, rb = ra - ra.mean(), rb - rb.mean()
    den = np.sqrt((ra * ra).sum() * (rb * rb).sum())
    return float((ra * rb).sum() / den) if den > 0 else np.nan


def bias_check(n=200_000, seed=43110):
    rng = np.random.default_rng(seed); out = {}
    for w in (15, 30, 60):
        x = rng.standard_normal((n, w))
        rv = (x * x).sum(axis=1)
        bv = (np.pi / 2) * (np.abs(x[:, 1:]) * np.abs(x[:, :-1])).sum(axis=1)
        out[w] = dict(mean_RV_minus_unscaled_BV=round(float((rv - bv).mean()), 4), mean_RV_minus_scaled_BV=round(float((rv - bv * w / (w - 1)).mean()), 4))
        out[w]["status"] = "PASS" if abs(out[w]["mean_RV_minus_unscaled_BV"] - 1) <= 0.05 and abs(out[w]["mean_RV_minus_scaled_BV"]) <= 0.05 else "FAIL"
    return out


def main():
    q.s.refuse_overwrite(OUTJ, OUTM)
    a4 = json.loads((R / "a4_sec4_3_7_eligibility.json").read_text(encoding="utf-8"))
    a4red = json.loads((R / "a4_sec4_3_8_redundancy.json").read_text(encoding="utf-8"))
    rho_old = pd.read_csv(R / "a4_sec4_3_8_spearman_RAW_pool.csv", index_col=0)
    assert list(rho_old.columns) == p.POOL
    pct_raw = {n: a4["coverage_pct"]["RAW"][n] for n in p.POOL}
    log("RAW: features with the scaled jump_variation")
    st = q.prepare_era("RAW")
    slot = st["slot"]; first, end = p.sessions(slot)
    X = {n: q.load_col(st, n) for n in p.NAMES}
    for n in p.SCALE: X[n + "__sadj"] = X[n] if False else None
    for n in p.SCALE:
        if n in CHANGED: X[n + "__sadj"] = p.adjust(X[n], slot, first, end)
        else: X[n + "__sadj"] = None
    # unchanged adjusted columns are rebuilt only for the sample re-check below
    def col(n):
        if X[n] is None: X[n] = p.adjust(X[n[:-6]], slot, first, end)
        return X[n]
    rho_new = rho_old.copy()
    log("recomputing the pairs that involve a changed column")
    for a in CHANGED:
        xa = col(a)
        for b in p.POOL:
            if b == a: continue
            v = rho(xa, col(b))
            rho_new.loc[a, b] = rho_new.loc[b, a] = v
    rng = np.random.default_rng(43111)
    others = [c for c in p.POOL if c not in CHANGED]
    mism = []
    for _ in range(150):
        a, b = rng.choice(others, size=2, replace=False)
        v = rho(col(a), col(b))
        if not np.isclose(v, rho_old.loc[a, b], rtol=1e-9, atol=1e-12, equal_nan=True): mism.append((a, b))
    log(f"sample re-check of 150 unchanged pairs: {len(mism)} mismatches")
    order, kept, dropped = q.redundancy(p.POOL, {"RAW": rho_new}, lambda n: pct_raw[n])
    old_kept, old_dropped = a4red["sensitivity_RAW"]["kept"], a4red["sensitivity_RAW"]["dropped"]
    changes = dict(newly_kept=sorted(set(kept) - set(old_kept)), newly_dropped=sorted(set(dropped) - set(old_dropped)))
    primary_has_jump = [c for c in a4["primary_pool"] if c in CHANGED]
    changed_pairs = [dict(column=a, RAW_rho_before_vs_its_raw=None) for a in []]
    comp = {a: dict(rho_with_raw_or_scaled_before_after=None) for a in []}
    shifts = []
    for a in CHANGED:
        for b in CHANGED:
            if a < b: shifts.append(dict(pair=[a, b], before=round(float(rho_old.loc[a, b]), 6), after=round(float(rho_new.loc[a, b]), 6)))
    bias = bias_check()
    checks = {"sample of 150 unchanged pairs equals the A4 rerun": not mism, "bias check on simulated Gaussian windows": all(v["status"] == "PASS" for v in bias.values()),
              "greedy rule consistent": len(kept) + len(dropped) == len(p.POOL)}
    doc = dict(created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment="4.3-A5 G3", changed_columns=CHANGED,
               pairs_recomputed=len(CHANGED) * (len(p.POOL) - 1) - len(CHANGED) * (len(CHANGED) - 1) // 2, unchanged_pair_sample_mismatches=mism,
               primary_pool_contains_changed_column=primary_has_jump, primary_set_status="unchanged (no jump_variation column is in the primary pool)" if not primary_has_jump else "NEEDS REVIEW",
               sensitivity_RAW=dict(pool=len(p.POOL), kept=len(kept), dropped=len(dropped), before=dict(kept=len(old_kept), dropped=len(old_dropped)), changes=changes),
               jump_variation_pair_correlations=shifts, bias_check=bias, checks=checks, status="PASS" if all(checks.values()) else "FAIL",
               priority_order=order, kept=kept, dropped=dropped)
    OUTJ.write_bytes((json.dumps(doc, indent=2) + "\n").encode("utf-8"))
    md = ["# jump_variation scaling: redundancy rerun (A5 G3)", "", f"Status: **{doc['status']}**. Changed columns: {', '.join(CHANGED)}.", "",
          f"RAW sensitivity pool: kept {len(kept)} / dropped {len(dropped)} (before: kept {len(old_kept)} / dropped {len(old_dropped)}). Newly kept: {changes['newly_kept'] or 'none'}. Newly dropped: {changes['newly_dropped'] or 'none'}.",
          f"Primary pool contains a changed column: {primary_has_jump or 'no'} -> {doc['primary_set_status']}.", "", "Bias check (simulated Gaussian windows, mean of RV - BV):", ""] + \
         [f"- w={w}: unscaled {v['mean_RV_minus_unscaled_BV']}, scaled {v['mean_RV_minus_scaled_BV']} ({v['status']})" for w, v in bias.items()]
    OUTM.write_text("\n".join(md) + "\n", encoding="utf-8")
    (R / "a5_jump_variation_redundancy.sha256").write_text(f"{sha(OUTJ)}  {OUTJ.name}\n{sha(OUTM)}  {OUTM.name}\n", encoding="ascii")
    shutil.rmtree(q.TMP, ignore_errors=True)
    print("\n".join(md))
    return 0 if doc["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
