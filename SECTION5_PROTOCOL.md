# Section 5 protocol

**Status: DRAFT pending pilot**

Written 2026-10-31T17:48:19.805045+00:00 UTC (2026-10-31T13:48:19.805045-04:00 New York). Governing document for the Section 5 pipeline and pilot; written before any Section 5 code was run.
Changes: dated, hashed amendments only. Source: text supplied by the user, reproduced unchanged below.

## Cited inputs (SHA-256)

| File | SHA-256 |
|---|---|
| `section431_step3_all_in_one_results/a4_sec4_3_9_frozen_matrix_v2.csv` | `9378f93f79e358f98d9dcad3992c269cb9a823a15bf28e8a21dbe319763ebe86` |
| `section431_step3_all_in_one_results/a4_sec4_3_9_matrix_primary_view_v2.csv` | `74f2c14fe15b0b7957283e66624a6352bab26e731535053371b0f8fd51243f25` |
| `section431_step3_all_in_one_results/a4_sec4_3_9_matrix_sensitivity_view_v2.csv` | `33f3cc2a9fcf8baa9ea53753375880a965377e23c88b65b4a76967255b14be53` |
| `section431_step3_all_in_one_results/a4_development_nested_folds_TRAIN.csv` | `06258e5a1645327a64aa07d155b59d20949c11c81ce657a26e4d44c27882adfc` |
| `section431_step3_all_in_one_results/a4_folds_check.json` | `0cf4b5901cddfc17ef83947e94f92c8696d12240d15f2883cc4b05579326612d` |
| `section431_step3_all_in_one_results/a4_lm_threshold_calibration.json` | `c6c5c775fd43a92131f4ce86481d216ec528a65a9a07d42354a19f64db9e0253` |

Feature matrix: 4.3.9 matrix v2 = `a4_sec4_3_9_frozen_matrix_v2.csv` (hash above).

## Protocol text (verbatim)

5.0 Scope: detection quality and cross-asset association only; no trading claims. H1 (primary): feature detectors beat returns-only baselines per family on BOTH (a) synthetic splices: median delay at 1 false alarm per 20 sessions, and (b) out-of-sample QLIKE for next-60-min SPY volatility; intersection-union test per family, Holm across families. H2 (primary): around confirmed calm-to-stressed SPY breaks, TLT/HYG/gold/USD cumulative return from T to T+30 lies outside a placebo distribution matched on time-of-day slot, era and SPY volatility decile (10,000 draws); horizons -30 and +5/15/30/60 min; stressed-to-calm is secondary. S1: return between T_d and T_c versus equal-length placebo. S2: H2 verdict agreement and response correlation across detectors. E1: footprint taxonomy (cite Cieslak & Pang). E2: overnight gaps versus early-session breaks. D1: feature-family selection frequency, including same-family co-selection. Multiple testing: Holm primary, BH secondary, exploratory uncorrected. Features: 4.3.9 matrix v2 by name and hash. Changes: dated, hashed amendments only.

5.1 Folds: 30 LEGACY and 4 RAW TRAIN-only folds (A4); inner train / validation / test with 5-session embargoes. Inner train fits all parameters, scaling, winsorization 0.5/99.5, Amihud normalization, Lee-Mykland Student-t threshold. Seasonal and relative-volume baselines are already causal. Intraday horizons only.

5.2 Pools: primary 19 (both eras); sensitivity 83 (RAW only). Enforced exclusions: overnight, raw_volume, log_raw_volume, raw_volume__sadj, response assets, cross-era rows; jump_variation__sadj dropped; Lee-Mykland flag sensitivity-only. Log only if strictly positive in inner train. Every feature model = 5-min return + 1 to 6 selected features; baselines = 5-min return only, same architecture and hyperparameter budget.

5.3 Decision bars every 5 min (stamped minute 4, 9, ... after 09:30); alarm time = t+1 min. Start at the first grid bar with all features present; abstain before. Session reset (HMM initial probabilities; HSMM state plus duration=1; BOCPD run length 0). No alarms on the first 2 updates. Any missing feature means a skipped update: HMM transition-only; HSMM duration advances with hazard; BOCPD hazard-only, statistics unchanged; no alarms on skips. Last decision: last grid bar with availability at or before the close. Report abstention and skip shares. Sensitivity grids 1 and 15 min on the final setups only.

5.4 Gaussian HMM diagonal, K 2-4, EM 3 starts, 200 iterations, tol 1e-4, variance floor 1e-6. Student-t HMM via EM with hidden scales, df in [2.1, 30], restart if a state is under 1% occupancy. HSMM K 2-3, free-form durations by EM, durations in elapsed grid intervals capped at the session's scheduled updates, cut off at session end. BOCPD Normal-Gamma per feature, lambda 12/39/78, run length truncated at 200; alarm when P(changepoint within 3 updates) is at or above the threshold. Seeds and versions recorded.

5.5 T_d: first real update where a new state wins with probability at or above the threshold (BOCPD: alarm). T_c: 3 consecutive real updates hold, and a skip resets the count (BOCPD: no new alarm over those 3). States ordered by return variance within each fit. 30-min refractory period. Unconfirmed by the close: dropped and counted. All timestamps at availability time. Direction rule at T_c: SPY 1-min realized variance over [T_d, T_c] versus the 60 min before T_d; above 1 = calm-to-stressed.

5.6 Synthetic splices per fold: calibrate on validation sessions, score on test sessions once. Break splice: a calm session until tau (random grid bar 11:00-14:30), then a stressed session, same clock times, prices rescaled for continuity, session A's history for baselines, features recomputed; both directions. Null splice: same volatility AND volume tercile. Hit = confirmed within 60 min of tau; delay = T_c - tau; 200 break and 200 null splices per fold. Threshold: smallest with at most 1 false alarm per 20 null sessions on validation. QLIKE: regime-conditional forecast of next-60-min variance, decision bars at or before 15:00 (12:00 on early closes); Diebold-Mariano test. Historical anchors (Flash Crash 2010-05-06 14:42, 2018-02-05) are descriptive; COVID only in evaluation. Hindsight segmentation is secondary.

5.7 No screening beyond Section 4; the pilot drops only zero-variance features.

5.8 Per fold, own validation only; the test segment never informs selection. Greedy forward from the return-only model, fixed K=3 / lambda=39, 1 start; stop when the gain is under 1% or at 6 features; then tune K/lambda with 3 starts. Objective: validation QLIKE; tie-breaks: fewer features, then synthetic delay. Budget exhausted: keep the best so far, record it. All folds if the pilot budget allows, else every 2nd (by amendment). Final setup for 5.13: feature count = median across folds, filled by frequency, ties by dictionary order; K/lambda = mode.

5.9 H1 scored per fold on that fold's own selected setup, on all available test segments; paired block bootstrap over consecutive folds (block 3), plus Wilcoxon, plus sign consistency. Cross-family comparison is descriptive.

5.10 Robustness: by era; LEGACY +5/+10 min delay; 3 seeds; 1/15-min grids; RAW sensitivity set; threshold +/-0.05.

5.11 Holm: H1 x4 families, H2 x4 assets. BH for secondary. Power: simulated minimum detectable effects.

5.12 Freeze final setups, thresholds and hashes before any evaluation output exists. The H2 primary detector = the family passing H1 with the lowest median VALIDATION QLIKE; ties go to the simpler model.

5.13 Refit the frozen setup on full TRAIN per era; run once on the exposed evaluation periods; no retuning. Fold tests are development evidence; 5.13 is confirmatory.

