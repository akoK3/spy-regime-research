# Diagnostic D3 report

**RAW fold 3, validation sessions only (test 1 uses synthetic data only); frozen pilot detectors (K=3, lambda=39, 1 start, seed 0), fixed a-priori feature sets; no selection; no evaluation data.**

Written 2026-11-01T16:48:17.143277+00:00 UTC.

## Verdicts

1. **Implementation sanity: FAIL under the protocol event rule; not an implementation bug in the models.** On synthetic iid Gaussian data with a 10x variance jump no family reaches FA <= 0.05 with hit >= 0.9 in both directions. The Gaussian HMM, Student-t HMM and HSMM catch stressed-to-calm (0.86-0.94 at threshold 0.5) but not calm-to-stressed (0.34-0.41 at 0.5, 0.00-0.03 at >= 0.9). Cause found: with K=3 the 2-regime data splits the stressed regime over two states (fitted variances 0.99 / 6.0 / 6.6) and the protocol rule needs ONE new state to win for 3 updates; with K=2 (variances 0.99 / 10.2) or the mass rule the jump is caught (up 0.90-0.92 at 0.9, FA 0.04-0.06). Filtering, EM and the unit tests are consistent with this; the defect is the state-identity requirement in 5.5. BOCPD also fails: no threshold gives FA <= 0.05 with both hits >= 0.9 (0.5: FA 0.06, up 0.59, down 0.00).
2. **Seasonality: CONFIRMED for return-only inputs, ABSENT for feature inputs.** Return-only HMM/HSMM states track the clock (Cramer's V 0.19-0.25, medium; the highest-variance state holds 26-36% of first-hour bars vs 9-13% mid-day). With f3/f6 inputs V <= 0.06 (negligible). Deseasonalising the return cuts the return-only V to 0.04-0.11.
3. **Seasonality fix: NO material change.** Stable-null false alarms and permanent-break hit rates are essentially unchanged for f3/f6 (e.g. Gaussian f3 at 0.99: FA 5.1 -> 5.1, hit 0.28 -> 0.26; HSMM f3: 6.8 -> 6.5, 0.26 -> 0.28). Only the Student-t f6 false alarms fall (5.2 -> 2.7 at 0.99, hit unchanged), and return-only hits stay <= 0.10. Seasonality is not the cause of the low hit rates or the false alarms. The raw mode reproduces D2 exactly.
4. **BOCPD: no usable contrast between null and break.** The changepoint probability is nearly the same on null and break splices (f3 pooled 99th percentile 0.71 null vs 0.90 break; base 0.29 vs 0.32-0.37; session maxima on null days reach 0.72 median for f3 and 0.97 for f6). At thresholds 0.05-0.5 the stable-null false-alarm rate is 15-20 per 20 for f3/f6 (return-only: 16-20 at 0.05-0.1, 0.2 at 0.5) while hit rates are 0.31-0.78; below 0.05 nothing fires. No threshold gives FA <= 1 per 20 with hit above ~0.04 (return-only 0.5: 0.2 / 0.04). Hyperparameters are listed under test 4.
5. **Extra finding (not requested): the protocol event rule itself lowers hit rates.** The mass rule raises permanent-break hit rates for R>=3 (Gaussian f3 at 0.99: 0.38 -> 0.51, up-direction 0.47 -> 0.68) but also raises stable-null false alarms (5.1 -> 10.5 per 20), so the false-alarm trade-off is not removed by changing the rule.

## Test 1: implementation sanity (synthetic iid Gaussian, 10x variance jump at update 36 of 78)

Cells: null false-alarm rate / hit up (calm to stressed) / hit down (stressed to calm), hit = T_c within 60 min of the jump; 200 sessions each; training set = 189 regime-mixture sessions; protocol event rule ('state').

| model | D | 0.5 | 0.9 | 0.99 | 0.999 | best (FA<=0.05, both hits>=0.9) |
|---|---|---|---|---|---|---|
| gaussian_hmm | 1 | 0.04/0.36/0.88 | 0.04/0.01/0.51 | 0.04/0.00/0.15 | 0.00/0.00/0.00 | None |
| gaussian_hmm | 4 | 0.04/0.41/0.92 | 0.04/0.03/0.54 | 0.04/0.00/0.14 | 0.00/0.00/0.00 | None |
| student_t_hmm | 1 | 0.04/0.34/0.86 | 0.04/0.01/0.52 | 0.04/0.00/0.14 | 0.00/0.00/0.00 | None |
| student_t_hmm | 4 | 0.02/0.38/0.92 | 0.02/0.01/0.49 | 0.02/0.00/0.12 | 0.00/0.00/0.00 | None |
| hsmm | 1 | 0.04/0.37/0.87 | 0.04/0.01/0.54 | 0.04/0.00/0.20 | 0.01/0.00/0.01 | None |
| hsmm | 4 | 0.04/0.41/0.94 | 0.04/0.02/0.57 | 0.04/0.00/0.18 | 0.01/0.00/0.01 | None |
| bocpd | 1 | 0.06/0.59/0.00 | 0.00/0.09/0.00 | 0.00/0.00/0.00 | 0.00/0.00/0.00 | None |
| bocpd | 4 | 0.18/0.58/0.04 | 0.01/0.17/0.00 | 0.00/0.01/0.00 | 0.00/0.00/0.00 | None |

BOCPD low thresholds (D=1): 0.01: 0.00/0.00/0.00, 0.02: 0.00/0.00/0.00, 0.05: 0.66/0.36/0.48, 0.1: 1.00/0.93/0.90, 0.2: 0.60/0.90/0.12, 0.3: 0.24/0.81/0.01, 0.5: 0.06/0.59/0.00.

Probe (not saved as a script; run inline during the session): Gaussian HMM, D=1, same data generator, 200 sessions each. K=2 recovers variances 0.99 and 10.21. K=3 fits variances 0.99 / 6.02 / 6.63, i.e. the stressed regime is split over two states. Protocol 'state' rule (one new state must win for 3 updates): K=2 at 0.9: FA 0.06, up 0.92, down 0.61; K=3 at 0.9: FA 0.04, up 0.01, down 0.51. Mass rule (1 - P[baseline state] >= thr for 3 updates; `s5_events.detect_states_mass`): K=3 at 0.9: FA 0.04, up 0.90, down 0.85.

## Test 2: state occupancy by time of day (train sessions, filtered argmax; Cramer's V of state x clock bin, 7 bins; df* = 2: V 0.07 small, 0.21 medium, 0.35 large)

| model | set | V raw | V deseasonalised | NMI raw | NMI des | share of the highest-variance state by bin (raw): 09:30 / 10 / 11 / 12 / 13 / 14 / 15 |
|---|---|---|---|---|---|---|
| gaussian_hmm | base | 0.23 | 0.04 | 0.057 | 0.003 | 0.26 / 0.22 / 0.13 / 0.10 / 0.11 / 0.12 / 0.13 |
| gaussian_hmm | f3 | 0.05 | 0.04 | 0.003 | 0.002 | 0.10 / 0.13 / 0.10 / 0.12 / 0.13 / 0.15 / 0.14 |
| gaussian_hmm | f6 | 0.04 | 0.03 | 0.002 | 0.001 | 0.17 / 0.16 / 0.13 / 0.14 / 0.15 / 0.17 / 0.15 |
| student_t_hmm | base | 0.25 | 0.06 | 0.067 | 0.004 | 0.32 / 0.26 / 0.16 / 0.11 / 0.12 / 0.13 / 0.14 |
| student_t_hmm | f3 | 0.05 | 0.05 | 0.002 | 0.002 | 0.12 / 0.15 / 0.13 / 0.14 / 0.15 / 0.18 / 0.15 |
| student_t_hmm | f6 | 0.04 | 0.02 | 0.002 | 0.000 | 0.17 / 0.16 / 0.14 / 0.16 / 0.17 / 0.19 / 0.16 |
| hsmm | base | 0.19 | 0.11 | 0.041 | 0.012 | 0.36 / 0.25 / 0.16 / 0.09 / 0.11 / 0.12 / 0.16 |
| hsmm | f3 | 0.06 | 0.05 | 0.003 | 0.002 | 0.10 / 0.13 / 0.11 / 0.12 / 0.14 / 0.16 / 0.14 |
| hsmm | f6 | 0.04 | 0.03 | 0.002 | 0.001 | 0.16 / 0.15 / 0.12 / 0.13 / 0.15 / 0.17 / 0.15 |

## Test 3: D2 vs D3 (all inputs deseasonalised), side by side

Stable-null false alarms per 20 sessions (95% CI) and pooled hit rates over D2 breaks (permanent; all sizes / R>=3; both directions). Rule 'state' = protocol; 'mass' = diagnostic alternative (HMM/HSMM only). 'D2' columns are from this run's raw mode (identical splices to `d2_results.json`; reproducibility check below).

| detector | set | rule | thr | FA D2 | FA D3 | hit perm D2 (all / R>=3) | hit perm D3 (all / R>=3) | D3 up R>=3 | D3 down R>=3 |
|---|---|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | state | 0.99 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| gaussian_hmm | base | state | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| gaussian_hmm | base | mass | 0.99 | 0.0 [0.0-0.2] | 0.1 [0.0-0.3] | 0.00 / 0.00 | 0.08 / 0.12 | 0.24 | 0.00 |
| gaussian_hmm | base | mass | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.03 / 0.05 | 0.10 | 0.00 |
| gaussian_hmm | f3 | state | 0.99 | 5.1 [4.3-6.0] | 5.1 [4.3-6.0] | 0.28 / 0.38 | 0.26 / 0.35 | 0.47 | 0.24 |
| gaussian_hmm | f3 | state | 0.999 | 3.5 [2.9-4.4] | 3.4 [2.7-4.1] | 0.20 / 0.28 | 0.20 / 0.26 | 0.43 | 0.10 |
| gaussian_hmm | f3 | mass | 0.99 | 10.5 [9.5-11.5] | 9.5 [8.5-10.5] | 0.38 / 0.51 | 0.38 / 0.49 | 0.68 | 0.31 |
| gaussian_hmm | f3 | mass | 0.999 | 7.1 [6.2-8.1] | 6.5 [5.6-7.4] | 0.30 / 0.39 | 0.28 / 0.38 | 0.64 | 0.12 |
| gaussian_hmm | f6 | state | 0.99 | 5.8 [4.9-6.7] | 5.5 [4.7-6.4] | 0.28 / 0.40 | 0.30 / 0.42 | 0.43 | 0.40 |
| gaussian_hmm | f6 | state | 0.999 | 4.3 [3.6-5.2] | 4.7 [3.9-5.6] | 0.25 / 0.35 | 0.23 / 0.35 | 0.39 | 0.31 |
| gaussian_hmm | f6 | mass | 0.99 | 9.4 [8.5-10.4] | 9.1 [8.1-10.1] | 0.38 / 0.56 | 0.37 / 0.53 | 0.58 | 0.49 |
| gaussian_hmm | f6 | mass | 0.999 | 7.3 [6.4-8.3] | 6.8 [5.9-7.7] | 0.37 / 0.49 | 0.31 / 0.46 | 0.50 | 0.42 |
| student_t_hmm | base | state | 0.99 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| student_t_hmm | base | state | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| student_t_hmm | base | mass | 0.99 | 4.1 [3.4-4.9] | 3.8 [3.1-4.6] | 0.09 / 0.12 | 0.10 / 0.13 | 0.26 | 0.00 |
| student_t_hmm | base | mass | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.02 / 0.03 | 0.07 | 0.00 |
| student_t_hmm | f3 | state | 0.99 | 4.4 [3.6-5.3] | 3.8 [3.1-4.6] | 0.28 / 0.39 | 0.20 / 0.28 | 0.33 | 0.24 |
| student_t_hmm | f3 | state | 0.999 | 1.6 [1.1-2.2] | 1.9 [1.4-2.6] | 0.16 / 0.23 | 0.10 / 0.13 | 0.25 | 0.01 |
| student_t_hmm | f3 | mass | 0.99 | 7.1 [6.2-8.1] | 7.5 [6.6-8.5] | 0.38 / 0.51 | 0.33 / 0.44 | 0.53 | 0.35 |
| student_t_hmm | f3 | mass | 0.999 | 3.4 [2.7-4.1] | 3.4 [2.7-4.2] | 0.23 / 0.31 | 0.20 / 0.30 | 0.35 | 0.25 |
| student_t_hmm | f6 | state | 0.99 | 5.2 [4.4-6.1] | 2.7 [2.1-3.4] | 0.23 / 0.33 | 0.23 / 0.28 | 0.19 | 0.38 |
| student_t_hmm | f6 | state | 0.999 | 3.0 [2.4-3.8] | 0.7 [0.4-1.2] | 0.18 / 0.24 | 0.12 / 0.17 | 0.11 | 0.22 |
| student_t_hmm | f6 | mass | 0.99 | 9.2 [8.2-10.1] | 5.0 [4.2-5.8] | 0.33 / 0.47 | 0.34 / 0.40 | 0.32 | 0.49 |
| student_t_hmm | f6 | mass | 0.999 | 6.3 [5.4-7.2] | 1.8 [1.3-2.4] | 0.31 / 0.40 | 0.21 / 0.27 | 0.22 | 0.32 |
| hsmm | base | state | 0.99 | 0.2 [0.1-0.5] | 0.0 [0.0-0.2] | 0.00 / 0.01 | 0.03 / 0.06 | 0.11 | 0.00 |
| hsmm | base | state | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.01 / 0.02 | 0.04 | 0.00 |
| hsmm | base | mass | 0.99 | 1.4 [1.0-2.0] | 1.4 [1.0-2.0] | 0.02 / 0.02 | 0.10 / 0.13 | 0.26 | 0.00 |
| hsmm | base | mass | 0.999 | 0.0 [0.0-0.2] | 0.8 [0.5-1.2] | 0.01 / 0.01 | 0.05 / 0.07 | 0.14 | 0.00 |
| hsmm | f3 | state | 0.99 | 6.8 [6.0-7.8] | 6.5 [5.7-7.5] | 0.26 / 0.37 | 0.28 / 0.38 | 0.42 | 0.35 |
| hsmm | f3 | state | 0.999 | 5.2 [4.3-6.1] | 5.0 [4.2-5.9] | 0.23 / 0.31 | 0.23 / 0.31 | 0.40 | 0.21 |
| hsmm | f3 | mass | 0.99 | 11.3 [10.4-12.3] | 9.6 [8.6-10.5] | 0.34 / 0.47 | 0.38 / 0.51 | 0.61 | 0.40 |
| hsmm | f3 | mass | 0.999 | 7.8 [6.8-8.7] | 6.3 [5.4-7.2] | 0.31 / 0.40 | 0.29 / 0.41 | 0.51 | 0.31 |
| hsmm | f6 | state | 0.99 | 5.5 [4.7-6.4] | 5.8 [4.9-6.7] | 0.26 / 0.38 | 0.29 / 0.40 | 0.38 | 0.42 |
| hsmm | f6 | state | 0.999 | 4.5 [3.7-5.3] | 4.8 [4.0-5.7] | 0.25 / 0.35 | 0.23 / 0.34 | 0.33 | 0.35 |
| hsmm | f6 | mass | 0.99 | 9.7 [8.7-10.6] | 9.1 [8.1-10.0] | 0.36 / 0.53 | 0.37 / 0.52 | 0.53 | 0.51 |
| hsmm | f6 | mass | 0.999 | 7.5 [6.5-8.4] | 6.8 [6.0-7.8] | 0.38 / 0.49 | 0.32 / 0.45 | 0.44 | 0.46 |
| bocpd | base | state | 0.99 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| bocpd | base | state | 0.999 | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.00 / 0.00 | 0.00 / 0.00 | 0.00 | 0.00 |
| bocpd | f3 | state | 0.99 | 0.8 [0.5-1.3] | 1.1 [0.7-1.6] | 0.02 / 0.03 | 0.02 / 0.03 | 0.06 | 0.01 |
| bocpd | f3 | state | 0.999 | 0.0 [0.0-0.2] | 0.1 [0.0-0.4] | 0.00 / 0.01 | 0.00 / 0.00 | 0.00 | 0.00 |
| bocpd | f6 | state | 0.99 | 6.2 [5.3-7.1] | 7.4 [6.5-8.4] | 0.10 / 0.13 | 0.10 / 0.14 | 0.21 | 0.07 |
| bocpd | f6 | state | 0.999 | 2.5 [1.9-3.2] | 3.2 [2.6-4.0] | 0.03 / 0.04 | 0.03 / 0.05 | 0.10 | 0.00 |

Reproducibility: raw-mode stable-null false-alarm rates equal D2's for all 24 detector/threshold cells checked.

## Test 4: BOCPD

Hyperparameters: independent Normal-Gamma per input dimension (Student-t predictive), prior mu0 = 0, kappa0 = 1, alpha0 = 1, beta0 = 1 on inputs standardised with inner-train statistics; constant hazard 1/lambda with lambda = 39 (12 and 78 in the protocol grid, not used here); run length truncated at 200 (mass beyond is merged into the last bucket); statistic = P(run length <= 2) = P(changepoint within the last 3 updates); alarm = rising edge of the statistic >= threshold at update >= 3; hold 3 real updates without a new alarm; skip = hazard-only step with statistics unchanged; first 2 updates silent (the statistic is 1.0 there by construction).

Changepoint-probability quantiles (50 / 90 / 99 / 99.9%) at updates >= 3, raw inputs: null = stable-null splices (all update values; per-session maximum); breaks = permanent D2 breaks, updates within 60 min after tau.

| set | null pooled | null session max | breaks pooled (all) | breaks session max (all) | breaks pooled (R>=3) | breaks session max (R>=3) |
|---|---|---|---|---|---|---|
| base | [0.0613, 0.0943, 0.2862, 0.4553] | [0.3117, 0.4279, 0.5815, 0.7104] | [0.0625, 0.0967, 0.3188, 0.6854] | [0.1028, 0.3084, 0.7467, 0.8842] | [0.0617, 0.0999, 0.3682, 0.7865] | [0.102, 0.3545, 0.791, 0.8954] |
| f3 | [0.0358, 0.1025, 0.7081, 0.9866] | [0.7175, 0.9866, 0.9987, 0.9988] | [0.035, 0.1591, 0.8989, 0.9937] | [0.2641, 0.8999, 0.9929, 0.999] | [0.0336, 0.1739, 0.9529, 0.9959] | [0.2781, 0.9548, 0.9966, 0.999] |
| f6 | [0.0301, 0.1234, 0.9675, 0.9993] | [0.9654, 0.9993, 1.0, 1.0] | [0.0297, 0.1944, 0.9811, 0.9998] | [0.3428, 0.9814, 0.9997, 1.0] | [0.0289, 0.1923, 0.9906, 0.9999] | [0.3947, 0.992, 0.9999, 1.0] |

Same, deseasonalised inputs:

| set | null pooled | null session max | breaks pooled (all) | breaks session max (all) | breaks pooled (R>=3) | breaks session max (R>=3) |
|---|---|---|---|---|---|---|
| base | [0.0591, 0.0938, 0.3728, 0.759] | [0.4123, 0.759, 0.7791, 0.7963] | [0.0617, 0.1072, 0.4703, 0.7608] | [0.1233, 0.4191, 0.7831, 0.9258] | [0.0607, 0.1118, 0.5215, 0.8091] | [0.1277, 0.5375, 0.8501, 0.9303] |
| f3 | [0.0355, 0.0978, 0.7839, 0.9877] | [0.7105, 0.9858, 0.9989, 0.9992] | [0.035, 0.1653, 0.9122, 0.9949] | [0.2617, 0.9099, 0.9946, 0.9987] | [0.0336, 0.1776, 0.9452, 0.9956] | [0.2908, 0.946, 0.9966, 0.9988] |
| f6 | [0.0296, 0.1134, 0.9742, 0.9993] | [0.9529, 0.9993, 1.0, 1.0] | [0.0296, 0.2175, 0.98, 0.9996] | [0.4109, 0.9776, 0.9996, 1.0] | [0.0288, 0.1967, 0.9926, 0.9999] | [0.4256, 0.993, 0.9998, 1.0] |

BOCPD thresholds 0.01-0.5 (stable null FA per 20 / hit perm all sizes / hit perm R>=3):

| inputs | set | 0.01 | 0.02 | 0.05 | 0.1 | 0.2 | 0.3 | 0.5 |
|---|---|---|---|---|---|---|---|---|
| raw | base | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 16.2 / 0.33 / 0.38 | 19.9 / 0.47 / 0.49 | 9.8 / 0.18 / 0.24 | 7.9 / 0.12 / 0.15 | 0.2 / 0.04 / 0.06 |
| raw | f3 | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 20.0 / 0.78 / 0.77 | 19.9 / 0.69 / 0.74 | 18.9 / 0.54 / 0.60 | 17.3 / 0.43 / 0.46 | 14.6 / 0.31 / 0.36 |
| raw | f6 | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 20.0 / 0.75 / 0.75 | 20.0 / 0.64 / 0.70 | 19.6 / 0.54 / 0.58 | 19.4 / 0.46 / 0.51 | 18.2 / 0.39 / 0.45 |
| des | base | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 15.7 / 0.35 / 0.36 | 19.8 / 0.57 / 0.59 | 17.6 / 0.29 / 0.33 | 13.1 / 0.19 / 0.22 | 7.5 / 0.11 / 0.15 |
| des | f3 | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 20.0 / 0.76 / 0.78 | 19.7 / 0.68 / 0.74 | 19.3 / 0.55 / 0.62 | 18.2 / 0.42 / 0.48 | 15.9 / 0.32 / 0.35 |
| des | f6 | 0.0 / 0.00 / 0.00 | 0.0 / 0.00 / 0.00 | 19.9 / 0.73 / 0.72 | 19.9 / 0.65 / 0.67 | 19.6 / 0.54 / 0.60 | 19.5 / 0.50 / 0.57 | 18.0 / 0.42 / 0.47 |

## Files

| File | SHA-256 |
|---|---|
| section5/s5_d3_synth.py | `01b43be5770c7f3fe1db8561ee7c0359533518a39ce142f57d9461d4d4f98105` |
| section5/s5_d3.py | `dcca647e2618670f754a6f77a183d7331dc6f9fa63822b55010cbf9b38d86ca9` |
| section5/s5_events.py | `b95a178366002ad4681504b8e0725dd6320ff052412e0a21808cdf328bb94cab` |
| section5/write_d3_report.py | `36653fd945f718642d89f53d5dc516d98f07f3fe055b8a767a0863c54de27161` |
| section5/results/d3_synth_results.json | `2c9b5bb31bfed7b73c3079ae13f9f9b40b4aecf6c4ffb003c45211a4ca9efb1c` |
| section5/results/d3_results.json | `86b2d29760a8308a45423e5a51237f4b48b35bf1b896368d944102b61baa53f3` |
