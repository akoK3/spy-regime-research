# Amendment A10 to SECTION5_PROTOCOL.md (data backend and machinery check on contaminated folds)

Dated 2026-11-03T14:58:46.441207+00:00 UTC (2026-11-03T09:58:46.441207-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the backend code it governs. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `8abd20f3557dac0991e30ea8c2807aee35be9d7de1c79b199d7f371397c97479` |
| `AMENDMENT_A6.md` | `db787ec0071b5b6c0ff4048cd281bf54e95e0c60b5f25e89fb6f02d55d5744a5` |
| `AMENDMENT_A7.md` | `e64c8647fd3fac01ff2a64de71f25c53e6b9c8814271df9e66b3ab01835d8267` |
| `AMENDMENT_A8.md` | `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931` |
| `AMENDMENT_A8_4.md` | `f57a8734aaf28fd1bac378edc7ec0f13a8f48dc7ea375e491b42612bb56d89e5` |
| `AMENDMENT_A9.md` | `d915f7c90a38a0236a3962857235d7e1096b16f54065bb8104d3795ee4947bb0` |
| `section5/s5_run.py` | `9119bbf2b6a1fa3b9c5369f66c6816094adb5444bf384f2357b199a8ac1b0603` |
| `section5/results/contamination_list.json` | `c872a6ce86142bfbf7d49e00b96ad13eef51e6d65425d9860b425d309425b1b5` |

## 1. Backend (`section5/s5_backend.py`)

A `DataBackend(era, fold)` implements the `s5_run.py` interface on real features, fitted models and splices, for one fold. Per fold it loads the era panel, the 19 primary columns, the fold segments (A4 folds, 5-session embargoes), the deseasonalised 5-minute return and the preprocessing fitted on the inner train only (5.1, 5.7).
- **Objective for selection (5.8):** a model of the family (K or lambda from the parameters, starts as given, seed 0, HSMM Dmax 78) is fitted on the inner-train sequences for the return plus the candidate subset; regime values are fitted on the inner-train filtered output (`state_values`); the objective is the mean QLIKE of the next-60-minute variance forecast on the fold's validation sessions. The test segment is not touched during selection.
- **Deviation, disclosed:** 5.8 breaks QLIKE ties by fewer features, then synthetic delay. Computing synthetic delay for every candidate fit is not affordable; the search returns delay = NaN, so only exact QLIKE ties (not expected with a continuous loss) fall through to dictionary order. Fewer-features is applied by the stop rule (1% gain).
- **Grids:** K in {2, 3, 4} for the Gaussian HMM, Student-t HMM and HSMM; lambda in {12, 39, 78} for BOCPD (5.4). Greedy search at K = 3, lambda = 39, 1 start; tuning and the final fit with 3 starts.
- **Scoring (`score`):** the feature model is the selected subset with the tuned parameter; the baseline is the return-only model of the same family with the same parameter and starts. H1(a): stable-day splices of the fold's test segment as in A7 (sizes x directions x durations, 24 per cell, 400 nulls; the splice scale of A8 item 1), the A7 threshold sweeps (theta 0-30 step 0.25; m 1-80), hit-rate curve against the null alarm rate; skipped (empty curve, reason recorded) when the fold has fewer than 8 stable test days (A8 item 3). H1(b): QLIKE series on the test sessions' decision bars (key = session x 1000 + slot). `val_qlike` is the tuned validation QLIKE.
- **Thresholds:** `final_thresholds` returns the A7 rule (continuous threshold by bisection to 0.2 alarms per session on real validation sessions) and the per-fold calibrated values. How a single numeric threshold is fixed for the era-level refit of 5.13 is not defined by A6-A9; it stays open and is not frozen by this amendment.
- Splices of a fold are built once, serially in the process (memory), and reused by all eight models.

## 2. Machinery check (what may be run)

- Only the two contaminated folds, RAW fold 3 and LEGACY fold 29 (both excluded from confirmatory H1 by `contamination_list.json`; the backend asserts this and refuses any other fold, and refuses any session outside the fold's three segments). Never a clean fold, never an evaluation-period session.
- `run_all` is called once per fold (one fold per call, one era per process), writing to `section5/results/a10_machinery_<ERA><fold>/`. With one fold the fold-level tests are not evaluable (n < 2) and no H1 verdict is read from them; the check is of the machinery only. The freeze step is exercised in a temporary directory that is discarded; `run_confirmatory` is not called.
- Reported: stage runtimes, peak memory, failures, checkpoint resume (second call recomputes nothing), finiteness of every output, the selected setups and their validation QLIKE (descriptive), skip reasons. No result is used for any protocol decision.

## Governs

The backend code, its unit tests, and the machinery run on RAW 3 and LEGACY 29 only. No change to A6-A9.
