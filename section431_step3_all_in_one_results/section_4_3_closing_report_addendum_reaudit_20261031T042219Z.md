# Addendum from the re-audit (disclosures and the lows fixed)

**SECTION_4_3_CLOSED** (the closed reports are not edited)

Added 2026-10-31T04:22:19.434655+00:00 UTC (2026-10-31T00:22:19.434655-04:00 New York). Note N4 `note_4_3_N4_20261031T041938Z.json` SHA-256 `27e81cc9d1a703a20d31174d291362457ba1b072f85c7cdb77770c3807238b1d`. Re-audit `reaudit_20261031.md` SHA-256 `10740f4d554d2b33c796a3e8dd341e69483c9bb6707feee0bf978384219a1566`.

## Fix results

| Fix | Status |
|---|---|
| L5 warmup of relative_volume20__sadj (new #5) | PASS |
| L6 hash lists (new #6) | PASS |
| L7 paths (new #7) | PASS |
| L11 housekeeping (new #11) | PASS |

L5: first defined session in the data, relative_volume20 and relative_volume20__sadj: {'RAW': {'relative_volume20': 10, 'relative_volume20__sadj': 20}, 'LEGACY': {'relative_volume20': 10, 'relative_volume20__sadj': 20}}. Matrix v2 `a4_sec4_3_9_frozen_matrix_v2.csv` `9378f93f79e358f98d9dcad3992c269cb9a823a15bf28e8a21dbe319763ebe86`; rows changed versus the base matrix: ['relative_volume20__sadj'].
L6: 8 mismatches in 40 hash lists; 10 reports older than the latest change to a producing script (details in `n4_checks.json`).
L7: absolute user paths in tracked scripts: none. L11: .gitignore entries without a file: none; F6 before F4: True (A4 stated order F7, F3, F1, F2+F5, F4, F6).

## Disclosure new #2: jump_variation_w is still biased upward.

- A5's bias check tested RV - BV, but the feature is max(0, RV - scaled BV). Simulated Gaussian no-jump windows (unit variance, 200,000 per w), mean value in units of one bar's variance: w=15: unclipped old 1.0, unclipped new 0.0012, clipped old 1.6912, clipped new 1.2334, share exactly 0 after the fix 0.5272; w=30: unclipped old 0.9934, unclipped new -0.0073, clipped old 2.1878, clipped new 1.7181, share exactly 0 after the fix 0.5199; w=60: unclipped old 1.0172, unclipped new 0.0173, clipped old 2.9167, clipped new 2.4387, share exactly 0 after the fix 0.5149.
- The clipping at 0 keeps a positive mean even when the unclipped difference is unbiased, so the fix removed part of the bias and not all of it.
- N.4 in the ledger covers only the exact zeros and the lost adjusted coverage; this bias is recorded here.

## Disclosure new #4: The frozen matrix was regenerated without an amendment.

- A4 said the 4.3.6 rows and the 4.3.9 matrix were not regenerated in that pass; the regeneration (steps 15 and 16) had no pre-run document, and the regeneration report's own freeze line requires a new dated amendment for any change.
- After the first matrix failed its coverage cross-check, the check was reworded from 'equals the A4 coverage for all 113 columns' to 'differs only for jump_variation_w__sadj'.
- The failed first matrix was not kept; its hash is recorded in the first-attempt report (b7f2678f6977cf3b41843a8953fa4093e06254bb82bb7887e8957cb780a94bc7) and cannot be verified.
- Note N4 (note_4_3_N4_20261031T041938Z.json) is the dated amendment for the matrix, issued after the fact; the corrected v2 matrix is a4_sec4_3_9_frozen_matrix_v2.csv.

## Disclosure audit #5 (limit): The Lee-Mykland threshold was calibrated for Gaussian returns only.

- Share of simulated 390-bar no-jump sessions with at least one flag at the threshold 4.6113, 40,000 sessions each: Gaussian 0.9825%, Student-t with 5 degrees of freedom 69.09%, with 3 degrees of freedom 96.70%.
- Real returns have fat tails and missing bars; the flag rate on real data has never been measured, so lee_mykland_jump60 is not controlled at 1% per session on real data.

## Disclosure audit #6 (visibility_ok): visibility_ok in the point-in-time replay is true by construction.

- Lines of delay_v2 in step5_policy.py:
    d2 = dict(d); d2["available"] = d["available"] + MINUTE
    lag = d2["available"] - d["t"]
    vis_new = int(np.searchsorted(d2["available"], t + 2 * MINUTE, side="right"))
    vis_old = int(np.searchsorted(d2["available"], t + MINUTE, side="right"))
    prefix = compute(s.truncate(d2, vis_new))
    replay.append(dict(row=idx, visible_rows_at_t_plus_2=vis_new, visible_rows_at_t_plus_1=vis_old,
    visibility_ok=(vis_new == idx + 1 and vis_old == idx), differing_outputs=off))
    ok_replay = all(r["visibility_ok"] and not r["differing_outputs"] for r in replay)
    print(f"delay v2 {label}: values identical {80 - len(different)}/80, available_at = t+2min {len(detector) - len(wrong_lag)}/80 outputs ({finite_rows} finite values), replay {sum(r['visibility_ok'] and not r['differing_outputs'] for r in replay)}/3", flush=True)
- The visible-row counts come from searchsorted on d2['available'], which is built as d['available'] + one minute from the same t array, so vis_new == idx + 1 and vis_old == idx hold for any feature values. Only the comparison of the prefix features with the full run exercises the data.

## Disclosure audit #7 (stale sentences): Two copies of the false evaluation-period sentence repeated the closed report's wording without a pointer.

- Ledger limitation 18 and SECTION4_COMPLETE.md line 392 copy the closing report's limitation 'never in an audited or analysed span'. The builders now append a pointer to the correction (the audit addendum) to that sentence. The closed report itself is unchanged.

## Not addressed in this pass

- re-audit new #8 (F4 hashed step 3 only; the G3 change also touched section431_additions.py)
- re-audit new #9 (the bipower_w reading of A5 G3 was never confirmed)
- audit #3: selection inside folds (remains a Section 5 open item)
- audit #4: no Section 5 open item exists for era-crossing decisions
- audit #8: ATOL=1e-10 remains in step3_all_in_one.py
- the rest of the re-audit's 'disclosed and still open' items
