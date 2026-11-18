# Post hoc benchmark: regime detectors vs simple volatility rules (facts)

**Status.** POST HOC (user order 2026-11-17). Development folds only; run after the freeze and the evaluation; changes no verdict and no frozen, MR2 or evaluation result. No evaluation-period data were read. Spec and script hash in the ledger row of 2026-11-18 01:33:09Z (`posthoc_benchmark.py`, SHA-256 `1367986b…`), written before the run on real data.

**Source.** Every number below is from `section5/results/posthoc_benchmark/posthoc_benchmark.json` (SHA-256 in `posthoc_benchmark.sha256`: `311c4229…`), key given per table. Per-fold records: `units/*.json`. Synthetic checks: `synthetic_check.json`. Run log: `log.txt`.

**Definitions** (full text in the script docstring and the ledger row).
- **B1** (primary detection benchmark): score s_t = |log(f_t / mean of f over the previous 60 min)|, f = `rv10_partial90__sadj`; alarm rule of the detectors (run of 3 updates above threshold, warm-up 2, refractory 30 min); threshold calibrated to 0.2 alarms per validation session.
- **B1b** (secondary): s_t = f_t, same alarm rule.
- **HAR** (forecasting benchmark): OLS of the existing next-60-min deseasonalised variance target on past-hour, previous-session and previous-5-session deseasonalised realised variance, fitted on each fold's inner train.
- **Detectors**: the saved MR2 per-fold feature models (A17-style pickles, sha256-checked).
- **Effects** are detector minus benchmark, positive = detector better: H1(a) = pAUC(detector) − pAUC(benchmark) on the same splices; H1(b) = QLIKE(HAR) − QLIKE(detector) on common test bars.
- **Statistics**: `s5_h1.family_result` (moving-block bootstrap of fold effects, 10,000 resamples, one-sided p for "detector better"; share of folds > 0). Confirmatory = 26 uncontaminated folds (H1(a) evaluable in 22); sensitivity = all 34 (H1(a) evaluable in 30).

## 1. Checks

- **Synthetic** (`synthetic_check.json`, `passed: true`): B1 null test rate 0.16 at target 0.2, hit within 60 min at variance ×10 0.91 (null placebo 0.03); B1b 0.21, 1.00 (0.03). The scalar alarm loop and sweep equal `s5_events.detect_old_state_logodds` and `s5_sweep.sweep_old_state` on an embedded P. HAR OLS recovered simulated coefficients.
- **Reproduction** (`reproduction`): in all 34 folds × 4 families, the recomputed pAUC(feature) − pAUC(baseline) equals MR2 `a` exactly (where evaluable) and the recomputed H1(b) equals MR2 `b` and `b_n` exactly (`all_h1a_reproduced`, `all_h1b_reproduced`: true). The recomputed feature pAUC equals `posthoc_absolute_detection/units` in every fold where H1(a) is evaluable (`abs_unit_feature_pauc_equal`; None = fold with fewer than 8 stable test days).
- **Runtime**: 190 min of worker time (`minutes`), 2 workers, 20:33–22:09 New York, 2026-11-17. Feature caches unchanged (`log.txt`).

## 2. Detection, H1(a): detector minus B1 and B1b

Key: `comparison.<family>.h1a_vs_B1` / `h1a_vs_B1b`, `.confirmatory` / `.all_folds`.

| Family | vs B1, confirmatory (22): mean / p / share > 0 | vs B1, all (30) | vs B1b, confirmatory (22) | vs B1b, all (30) |
|---|---|---|---|---|
| Gaussian HMM | −0.1125 / 1.0 / 0.09 | −0.1066 / 1.0 / 0.07 | +0.0046 / 0.406 / 0.59 | +0.0200 / 0.088 / 0.63 |
| Student-t HMM | −0.1505 / 1.0 / 0.00 | −0.1440 / 1.0 / 0.00 | −0.0334 / 1.0 / 0.23 | −0.0174 / 0.929 / 0.33 |
| HSMM | −0.0979 / 1.0 / 0.00 | −0.0917 / 1.0 / 0.00 | +0.0192 / 0.240 / 0.45 | +0.0350 / 0.013 / 0.57 |
| BOCPD | −0.2795 / 1.0 / 0.00 | −0.2804 / 1.0 / 0.00 | −0.1624 / 1.0 / 0.00 | −0.1537 / 1.0 / 0.00 |

## 3. Forecasting, H1(b): QLIKE(HAR) minus QLIKE(detector)

Key: `comparison.<family>.h1b_vs_HAR`; IU p of the B1/HAR pair: `comparison.<family>.p_iu_vs_B1_HAR` (1.0 for every family, both scopes).

| Family | Confirmatory (26): mean / p / share > 0 | All (34) |
|---|---|---|
| Gaussian HMM | −0.0428 / 1.0 / 0.04 | −0.0501 / 1.0 / 0.03 |
| Student-t HMM | −0.0410 / 1.0 / 0.04 | −0.0460 / 1.0 / 0.03 |
| HSMM | −0.0452 / 1.0 / 0.04 | −0.0517 / 1.0 / 0.03 |
| BOCPD | −0.1594 / 1.0 / 0.00 | −0.1940 / 1.0 / 0.00 |

## 4. Absolute values (mean over folds)

Key: `absolute.confirmatory` (all-folds values in `absolute.all_folds`).

**pAUC** (22 confirmatory folds with H1(a)):

| Model | pAUC |
|---|---|
| B1 | 0.333 |
| B1b | 0.216 |
| Gaussian HMM, feature / baseline | 0.220 / 0.116 |
| Student-t HMM, feature / baseline | 0.182 / 0.114 |
| HSMM, feature / baseline | 0.235 / 0.124 |
| BOCPD, feature / baseline | 0.053 / 0.053 |

**QLIKE** (26 confirmatory folds; detector and HAR on the same bars; lower is better):

| Family | Detector | HAR, same bars | Median gain as % of HAR |
|---|---|---|---|
| Gaussian HMM | 0.2252 | 0.1825 | −17.6% |
| Student-t HMM | 0.2233 | 0.1823 | −17.6% |
| HSMM | 0.2278 | 0.1827 | −19.0% |
| BOCPD | 0.3415 | 0.1821 | −76.7% |

HAR on all its scored test bars: 0.1821 (`absolute.confirmatory.HAR.mean_qlike_fold_mean`); no forecast was floored (`floored_total` 0). Per-fold HAR coefficients: `har_beta_per_fold`.

**Benchmark thresholds and realised test alarm rates** (confirmatory; target 0.2 on validation): B1 median threshold 0.636, 0.227 alarms per test session; B1b median threshold 2.17, 0.386 alarms per test session; no threshold flagged (`absolute.confirmatory.B1`, `.B1b`).

## 5. FOMC statements, H1(c) (98 development events)

Key: `fomc.B1`, `fomc.B1b`; detector hit rates from `section5/results/mr2/a17/a17_results.json` (`h1c.<family>.f3.hit_rate`). Paired test: exact two-sided sign test on discordant events (`s5_h1c.paired_sign`; `fomc.<benchmark>.vs_detector.<family>.paired_detector_minus_benchmark`).

| | Hit rate (Wilson 95%) | Reference alarm rate, non-FOMC sessions |
|---|---|---|
| B1 | 0.490 (0.393–0.587) | 0.045 |
| B1b | 0.622 (0.524–0.712) | 0.063 |

| Family | Detector hit rate | vs B1: detector only / B1 only / p | vs B1b: detector only / B1b only / p |
|---|---|---|---|
| Gaussian HMM | 0.622 | 27 / 14 / 0.060 | 13 / 13 / 1.0 |
| Student-t HMM | 0.469 | 18 / 20 / 0.871 | 11 / 26 / 0.020 |
| HSMM | 0.622 | 21 / 8 / 0.024 | 14 / 14 / 1.0 |
| BOCPD | 0.398 | 22 / 31 / 0.272 | 14 / 36 / 0.0026 |

B1b's realised test alarm rate (0.386 per session) is above the 0.2 calibration target, so its FOMC hit rate is not at a matched alarm rate (§4).
