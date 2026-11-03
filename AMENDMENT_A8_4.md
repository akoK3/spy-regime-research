# Amendment A8.4 (investigation of the two flagged LEGACY 29 detectors)

Dated 2026-11-03T03:38:42.565100+00:00 UTC (2026-11-02T22:38:42.565100-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the analyses it governs. The A8.3 result (Gaussian HMM base and HSMM f3 above 2x RAW) is the trigger.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A8_2.md` | `c85e40ba4484d648e44a2eda9f4900f29ffbf0bff0751b38c2f878455e96c157` |
| `AMENDMENT_A8_3.md` | `8867dc3e526285ce24768480bbfe200d1e37f68a2e86bbeea425dc31740d52a1` |
| `A8_3_GATE_CHARACTERIZATION.md` | `20f35e2abf33b663692c533753f8be7194940737cb3bce85d40d43da5f180a40` |
| `section5/results/a8_3_gate_LEGACY29.jsonl` | `6c3ef1cd08d707f9aaaa6d8874ef9aff43b4a762957e2abd37846f24672a1438` |
| `section5/results/a8_3_gate_RAW3.jsonl` | `ff22a1c4ac53eba0fdf4b50dbe85bc580891b1b37e882ad9e7bfdaa5c9110603` |

## Question 1: multiplicity

- Observed: 2 of 8 detectors exceed their limit (LEGACY rate > 2 x max(RAW rate, 0.05)).
- Primary test (decides the rule): permutation. The 40 seed records (20 LEGACY + 20 RAW; each record is the vector of 8 outside/inside flags of one seed, so cross-detector correlation is kept) are pooled and re-split at random into 20 and 20, 10,000 times; for each split the number of detectors whose 'LEGACY' rate exceeds 2 x max('RAW' rate, 0.05) is counted. P1 = share of splits with at least 2 detectors exceeding. This tests that the two folds' failure processes are exchangeable.
- Information: independent-binomial version (each detector's count ~ Binomial(20, pooled rate of that detector over the 40 seeds), LEGACY and RAW counts independent, 100,000 simulations); it ignores the correlation of detectors (they share the splices).

## Question 2: leave-one-day-out

- Seeds 1001-1020, LEGACY 29, same models and same splices as A8.3 (regenerated deterministically from the seed; the full-day outcomes must equal the A8.3 file, else the analysis is void and reported as such). For each of the 7 stable validation days in turn, every N1, P1 and P2 splice whose session A or session B is that day is removed, the day-level bootstrap uses the 6 remaining days, and the A8.2 gate outcome is recomputed per detector and seed. Splices are not redrawn.
- A day is a **driving day** if, with it removed, no detector exceeds its limit (limits from the A8.3 RAW counts, unchanged). **A single driving day exists** if exactly one of the 7 days satisfies this. If several days do, or none, no single driving day is declared; the per-day LEGACY failure counts per detector are reported either way.

## Pre-stated decision

- If P1 (permutation) is above 10%, or a single driving day exists: document it and proceed. 'Proceed' means only the steps A8.2 attached to a passed gate: the contamination list and fold exclusions (A8 item 2, with D6 not counted as contamination as A8.2 says) and the list of eligible FOMC events per fold. No detector is scored on test-segment data.
- Otherwise (P1 at most 10% and no single driving day): stop and report. Nothing else changes.

## Governs

Questions 1 and 2 only.
