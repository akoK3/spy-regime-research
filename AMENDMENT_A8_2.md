# Amendment A8.2 to AMENDMENT_A8.md and AMENDMENT_A8_1.md (gate bootstrap unit; status of D6)

Dated 2026-11-03T01:35:19.191879+00:00 UTC (2026-11-02T20:35:19.191879-05:00 New York). Status: ADOPTED when committed with its hash sidecar. Both changes were decided after the A8.1 gate result (RAW 3 passed 8 of 8, LEGACY 29 passed 3 of 8); written before the re-run they govern.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A8.md` | `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931` |
| `AMENDMENT_A8_1.md` | `bd7a854ed681c16b5bddadda1791fb66087aeecc63e4341e05c95da8de48fbd8` |
| `A8_1_GATE_REPORT.md` | `bb20d319d30fbf49cf8fb9a13274f125f46fe64169eb10d0c6fcc95b68156f51` |
| `D6_REPORT.md` | `f404fe0f846d53efa599db3f89a452df81d603944234136b5d7d583387f070e0` |
| `section5/results/a8_1_gate_LEGACY29_seed777.json` | `565bbf61e32d5b33d7ad30218725792fdf9912b6165c1959ec0e90fa95dd696b` |
| `section5/results/a8_1_gate_RAW3_seed777.json` | `d7e9d10eac89efac4441ce0d1be67ed166d045d468485f6a0d50f31481129ba1` |

## 1. Gate bootstrap resamples stable days

- A8.1 resampled the 200 placebo splices of P2. The splices are drawn from few stable validation days (7 on LEGACY 29, 16 on RAW 3), so they are not independent; the interval was too narrow (inference). Decided after the LEGACY 29 failure.
- Now: each bootstrap replicate draws n stable validation days with replacement (n = number of stable days of the fold) and weights each P2 splice by the number of times its session A was drawn; pAUC is computed from the weighted hit curve. 2,000 replicates, 95% percentile interval. Pass rule, placebo sets, seed (777) and folds unchanged from A8.1. The splice-level result is reported for information.
- If the gate fails on either fold: stop and report; nothing else changes.

## 2. D6 is descriptive, not contamination

- D6 ran no detector, no model and no performance measure; it computed SPY variance ratios around dates. Item 2 of A8 is amended: D6 dates (FOMC statements and the three listed shocks) are not entered in the contamination list. The registry marks D6 scripts as DESCRIPTIVE. All other registry entries (pilots, diagnostics D2-D5, audit runs, gate) stay.
- Disclosure: the H1(c) events (FOMC announcements) were chosen knowing from D6 that SPY variance around FOMC statements is large (median ratio 8.6 against 0.91 at random 14:00 moments). H1(c) is secondary; the choice of event type is not independent of that observation.

## Governs

The gate re-run on both folds. If it passes: A8 item 2 (contamination list, fold exclusions) and, for item 5, only the list of eligible FOMC events per fold (uncontaminated test segment, post-embargo, 390 bars). No detector is scored on test-segment data. If it fails: nothing further.
