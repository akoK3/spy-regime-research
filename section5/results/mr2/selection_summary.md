# MR2 feature selection: summary (5.8 greedy forward, A20 pool)

Source: the 136 MR2 selection checkpoints (`section5/results/main_run_2/ckpt/`, key `select|main|budget=None|<era>|<fold>|<family>`), covered by `run_complete.json` (results_sha256 `814171c0813fd668a591f54af8e26a45127dc81d2899286c98dc057b647135d6`, code a0323ed24d68e896, protocol 15be2570...). All 34 folds; folds marked * are in the contamination exclusion list (LEGACY 23, 24, 27, 28, 29; RAW 1, 2, 3). Descriptive; no new computation beyond counting the stored traces.

Limitation: the trace stores only each round's best candidate (added if its relative validation QLIKE gain is >= 1%, otherwise recorded as rejected and selection stops). Runner-up candidates within a round are not recorded.

## Folds selecting more than one feature (none selected three or more)

| Family | 0 features | 1 feature | 2 features | Two-feature folds |
|---|---|---|---|---|
| Gaussian HMM | 4 | 25 | 5 | rv10_partial90__sadj + intrabar_range_log__sadj: LEGACY 2, 19, 28*; rv10_partial90__sadj + relative_volume20: LEGACY 21, 26 |
| Student-t HMM | 13 | 17 | 4 | rv10_partial90__sadj + intrabar_range_log__sadj: LEGACY 0, 2, 10; rv10_partial90__sadj + relative_volume20: LEGACY 19 |
| HSMM | 0 | 25 | 9 | rv10_partial90__sadj + intrabar_range_log__sadj: LEGACY 1, 2, 10, 19, 28*; rv10_partial90__sadj + relative_volume20: LEGACY 21, 26; rv10_partial90__sadj + momentum30_endpoint: LEGACY 11; relative_volume20 + rv5_strict__sadj: LEGACY 20 |
| BOCPD | 33 | 1 | 0 | (single feature: momentum30_endpoint, RAW 3*) |

## Best candidate per round, across folds

Counts are folds where the candidate was the round's best; gains are median relative validation QLIKE gains; "rejected" = below the 1% rule.

| Family | Round 1 | Round 2 |
|---|---|---|
| Gaussian HMM | rv10_partial90__sadj 27 (25 added, median +9.7%; 2 rejected); intrabar_range_log__sadj 4 (3 added, +5.6%; 1 rejected) | intrabar_range_log__sadj 12 (10 rejected, +0.3%; 2 added, +1.4%); relative_volume20 12 (10 rejected, -0.1%; 2 added, +2.9%) |
| Student-t HMM | rv10_partial90__sadj 19 (12 added, +6.1%; 7 rejected, -2.0%); intrabar_range_log__sadj 9 (6 added, +12.3%; 3 rejected) | rv10_partial90__sadj 6 (all rejected, -3.8%); relative_volume20 6 (5 rejected, +0.2%; 1 added); intrabar_range_log__sadj 5 (3 added, +1.1%; 2 rejected) |
| HSMM | rv10_partial90__sadj 29 (all added, +12.4%); intrabar_range_log__sadj 3 (added, +13.6%) | intrabar_range_log__sadj 15 (11 rejected, +0.4%; 4 added, +1.3%); relative_volume20 12 (10 rejected, -0.1%; 2 added, +3.0%) |
| BOCPD | best candidates all rejected (gains about +0.1%): abs_return_1m__sadj 10, relative_volume20 7, intrabar_range_log__sadj 4; one fold added momentum30_endpoint (+2.9%, RAW 3*) | one fold: momentum5_endpoint rejected |

Reading: in round 1 the HMM-type families almost always take rv10_partial90__sadj. In round 2 the best candidate is usually intrabar_range_log__sadj or relative_volume20, and it typically fails the 1% rule.
