# Amendment A8.3 (characterization of the P1-vs-P2 gate; no re-roll)

Dated 2026-11-03T01:48:23.965489+00:00 UTC (2026-11-02T20:48:23.965489-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the runs it governs.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A8.md` | `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931` |
| `AMENDMENT_A8_1.md` | `bd7a854ed681c16b5bddadda1791fb66087aeecc63e4341e05c95da8de48fbd8` |
| `AMENDMENT_A8_2.md` | `c85e40ba4484d648e44a2eda9f4900f29ffbf0bff0751b38c2f878455e96c157` |
| `A8_2_GATE_REPORT.md` | `fb0fc1bac22fe1c192a785a6896f4f1e2ab62a28737782bacc490ff7560385bb` |
| `section5/results/a8_2_gate_LEGACY29_seed777.json` | `78c1077ee44943491bad30c5a1d17c961b51afb96dba6b46a3e71861036bfa66` |
| `section5/results/a8_2_gate_RAW3_seed777.json` | `a8790889099698bce45b7873e979dd40791cf7568bc497ec972b5a3397d426a0` |

## Purpose

The A8.2 gate (seed 777) passed on RAW fold 3 (8 of 8) and failed on LEGACY fold 29 (5 of 8). One seed cannot say whether that is chance. This amendment characterizes the gate; it does not replace the seed-777 decision, which stays recorded as FAILED.

## Procedure

- Seeds 1001 to 1020 (20 new seeds, none used before). For each seed and each of the two folds (LEGACY 29, RAW 3), the A8.2 gate is repeated unchanged: fresh N1 null set (alarm-rate axis), fresh placebo sets P1 and P2 (200 R = 1 splices each, 50 per duration), models fitted once per fold (as in the gate), day-level bootstrap (2,000 replicates) of P2, 95% percentile interval; P1 outside the interval = failure for that detector and seed. N2 is not drawn (not used by the rule).
- Reported: per detector (8) and fold, the failure rate over the 20 seeds with Wilson 95% interval; the pooled failure rate per fold; the seed-777 results alongside.

## Pre-stated rule

- RAW's failure rate per detector is floored at the nominal 0.05 (a rate of 0 of 20 is not evidence of a rate below 0.05).
- A detector is 'within 2x' if LEGACY rate <= 2 x max(RAW rate, 0.05). If all 8 detectors are within 2x, the LEGACY 29 failure is documented as chance. If any detector is above 2x, that detector is 'far higher' and is investigated before any main run (the investigation is a separate, dated step; nothing is changed by this amendment).
- Pooled over detectors the same comparison is reported for information, not as the rule.
- No test-segment scoring, no other change to A6, A7, A8, A8.1 or A8.2.

## Governs

The 2 x 20 gate repetitions and their report only.
