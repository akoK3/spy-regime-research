# Amendment A20 (seasonally adjusted scale inputs and QLIKE target; MR1 superseded by MR2; protocol re-frozen through A20)

Dated 2026-11-06T20:04:00+00:00 UTC (2026-11-06T15:04:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before any code it governs. Decided by the user after the main run (MR1), A17, A18 and the D7 diagnostic on RAW fold 3. Disclosed: this change is motivated by MR1-era outputs (the D7 diagnostic on the contaminated RAW 3 fold); MR1's fold results had been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A16) | `0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9` |
| `AMENDMENT_A17.md` | `3778a860320e11db1de520162adf36899cd3dd1b249bb8f9050b8f5f3566f874` |
| `AMENDMENT_A18.md` | `f9b8f371090c2db2e6467c250622b527c9bbf255b09e37d6478379d07a9673b0` |
| `AMENDMENT_A19.md` | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` |
| `AMENDMENT_A19_1.md` | `bffed0e9f8acf7aea9d98ae83950624d7cb3f4b95e37c15997fccda584eed0a0` |
| `AMENDMENT_A19_2.md` | `619d32de48aeaa8a1fd9054fcb676982a84c7028fc27d1c673a38af001480b27` |
| `AMENDMENT_A19_3.md` | `7269d2cb5034cec52e9f42a006e26f93e7662825c3a89f065df4553735a8f7e2` |
| `section5/results/d7_diag_raw3.json` | `50d2299ffd41036e90e63b5c8dde36923b6c1c3abd64cfe9e5b80d413f91d842` |
| `section5/results/main_run/run_complete.json` (MR1) | `e6f56ae2e19bbc0f56c1437adc04edfa425e2b86c9334065b8d0d3c034630dc1` |
| `section5/s5_lib.py` (before A20) | `bd91387861974903148e8a0e0bbcafd48722583f80ed70933f894c6a02a89d20` |
| `section5/s5_eval.py` | `88107ffaff297abd32c8c282274ab7221da381eb5b5fd3434ffc2213c9d7ef47` |
| `section5/s5_backend.py` (before A20) | `4a077d86a7d2881b821c32a655724db6bd27dbbbb28e60149b0b9f1e88da0773` |

## Findings that motivate it

- D7 diagnostic (RAW 3): the feature models' states track the time of day (Cramer's V with the hour .18-.23, baselines .03-.06); the open state is their highest-variance state on 39-56% of days; with the `__sadj` versions of the selected scale features the variance positive control responds (x5.29: +.24 to +.33, CIs exclude 0), with the raw versions it does not.
- H1(b) target (checked in code before this amendment): `s5_lib.session_grid` sets the target to the RAW sum of squared 1-min returns over the next 60 bars (scaled by 60/n, n >= 50 finite), not deseasonalised. The regime-conditional forecasts (`s5_eval.state_values`) are posterior-weighted means of this raw target, so they inherit the intraday volatility pattern.

## Rule

1. Scale-type detector inputs use only their `__sadj` versions. Scale-type = the name-stem families rv, downside, abs_return, intrabar_range (A18 rule 3). Primary pool: the 19 columns minus the six raw scale columns that have a `__sadj` version in the pool (abs_return_1m, intrabar_range_log, rv5_strict, downside5_strict, downside10_strict, rv10_partial90), leaving 13: return_1m, relative_volume20, momentum5/10/15/30_endpoint, close_location_proxy and the six `__sadj` columns. Sensitivity pool (5.2, RAW only): the same rule (raw scale columns excluded; a scale column without a `__sadj` version is excluded). The deseasonalised 5-min return input (5.3) is unchanged.
2. H1(b) QLIKE target deseasonalised by the same causal slot baseline: target = (60 / n) * sum over the next 60 one-minute bars of r^2 / b, where b = median r^2 of the same slot over the previous 20 sessions (>= 10 finite; `s5_d2_stable.des_variance`), n = number of finite terms (>= 50), floor 1e-10. State values, forecasts, Diebold-Mariano and the A17-style QLIKE percent use this target.
3. Everything else identical: folds, embargoes, preprocessing, models, grids, selection (5.8), events, splices, sweep, thresholds (A7), H1(a)/(b) tests, IU, Holm, BOCPD secondary, H1(c), A17 rules (reproduction with exact-match abort, saved models and alarms, H1(c), POST HOC R=1-net H1(a), QLIKE percent), D7 per A19 to A19.3 (sizes, sweep scoring, gates, Step 2 trigger), D8 unchanged (no detector).
4. MR1 = the main run of 2026-11-04/05 (`section5/results/main_run/`, completion record above) with A17, A18 and the A19 D7 work on its fits: labeled MR1, superseded; kept unchanged as a record. MR2 = the main run under this amendment, all 34 folds, in `section5/results/main_run_2/`, followed automatically by the A17-style phase on MR2 (`section5/results/mr2/a17/`) and D7 per A19.3 on the MR2 fits (`section5/results/mr2/d7/`), one unattended checkpointed runner. Its H1 verdicts replace MR1's for the study; MR1's are reported as superseded beside them. A18 is not rerun.
5. Contamination: the canonical list (sha256 `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b`) and the 26 / 8 fold split are kept unchanged. Every fold's test segment was scored in MR1 and the change is motivated by MR1-era outputs; MR2's fold tests are therefore development evidence (as 5.13 already states for fold tests); 5.13 (era level, evaluation periods never used) remains the confirmatory step. MR2 scripts are registry category MAIN_RUN.
6. Re-freeze: `SECTION5_PROTOCOL.md` is re-frozen integrating A17, A18, A19, A19.1, A19.2, A19.3 and A20 (consolidation; the previous frozen text kept as `SECTION5_PROTOCOL_v8_FROZEN_A16.md`). The new hash invalidates MR1's checkpoints and completion record under A16 rule 6, as intended. No 5.12 freeze, no era calibration.
7. Preflight before launch, on the contaminated folds only (RAW 3, LEGACY 29): the full MR2 unit (selection and scoring) for all four families, the A17-style reproduction and extras, and D7 per A19.3 including the positive control, written outside the run directories.

## Governs

`section5/s5_lib.py` (A20 pool filter, deseasonalised target), `section5/s5_backend.py` (pool and target wiring), MR2 orchestration and runner, the protocol integration writer; results under `section5/results/main_run_2/` and `section5/results/mr2/`.
