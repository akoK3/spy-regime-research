# Diagnostic D5 report

Written 2026-11-01T17:21:50.985709+00:00 UTC. Ratios are VARIANCE ratios. Parts A and B are pure synthetic; part C uses RAW fold 3 validation stable-day null splices (D2 sampling); no selection, no evaluation data, nothing excluded, no grid changed.

## Decision rule (stated before the runs)

Adopt the 1-minute grid if (1) synthetic hit at 3x variance ratio >= 50% at test FA <= 10% of sessions, (2) real stable-null FA is no worse, and (3) delay and compute are acceptable. The task left (3) undefined; I define it here: delay = mean over directions of the median delay at 10x is no larger than at 5 minutes; compute = filtering <= 10 ms per session and fitting <= 60 s. (1) is required in both noise types (strict) -- the 'either' column relaxes it; (2) is checked at the synthetic R = 3 thresholds of the same noise type, both noise types.

| family | K | (1) hit at 3x >= 0.5, FA <= 0.10, both noises | (1) either noise | (2) real FA 1-min <= 5-min | (3a) delay no larger | (3b) compute | adopt 1-min |
|---|---|---|---|---|---|---|---|
| gaussian_hmm | 2 | NO | NO | NO | yes | yes | no |
| gaussian_hmm | 3 | NO | NO | yes | yes | yes | no |
| student_t_hmm | 2 | NO | NO | NO | yes | yes | no |
| student_t_hmm | 3 | NO | NO | yes | yes | yes | no |
| hsmm | 2 | NO | NO | NO | yes | yes | no |
| hsmm | 3 | NO | yes | NO | yes | NO | no |

**Verdict: do not adopt the 1-minute grid under the stated rule (criterion 1 fails for every family and K).**

## A. BOCPD root cause

- Independent reference (Adams & MacKay 2007 recursion; each run-length hypothesis scored by the closed-form Normal-Gamma marginal likelihood ratio ML(segment + x) / ML(segment), prefix-sum evaluation; the `bayesian_changepoint_detection` package was not used): maximum absolute difference between the two run-length posteriors P(r_t | x_1:t) over all updates and run lengths, 12 sessions (6 up, 6 down) x 4 priors x lambda 12/39/78: **1.70e-14**. Our implementation reproduces the reference to rounding error: **not a code bug**.
- Evidence asymmetry (analytic, per update): KL of a 10x variance increase 3.35 nats, of a 10x decrease 0.70 nats. The reference itself needs [None, 1, 0, 10, None, 1] updates (None = never within the session) after an increase before P(run length <= 2) >= 0.5, and [None, None, None, None, None, None] after a decrease: the reference posterior reproduces the one-sided behaviour.
- **Verdict A: method limitation** (Normal-Gamma BOCPD with these alarms responds to variance increases and weakly to decreases), not our bug. Alarm (b) (MAP run-length drop) is the only BOCPD alarm that responds in both directions.

Priors tested (z-scored inputs, pooled train variance 1; calm train variance 0.22, stressed 2.29): default (0,1,1,1); beta0 = calm variance; beta0 = stressed variance; tighter (0,1,3,2). Detection, Gaussian R = 10, D4 'maxhit' rule, 500 test sessions per cell. Cells: hit up / down (test FA); '-' = no calibration threshold with FA <= 10%.

| prior | lambda | (a) P(r<=2) | (b) MAP drop | (c) P(r<6) |
|---|---|---|---|---|
| default (0,1,1,1) | 12 | 0.47 / 0.00 (0.01) | 0.77 / 0.76 (0.06) | 0.57 / 0.00 (0.00) |
| default (0,1,1,1) | 39 | 0.58 / 0.00 (0.02) | 0.82 / 0.65 (0.00) | 0.91 / 0.02 (0.07) |
| default (0,1,1,1) | 78 | 0.69 / 0.00 (0.03) | 0.79 / 0.38 (0.00) | 0.84 / 0.00 (0.02) |
| beta0 = calm train variance (0.22) | 12 | 0.47 / 0.00 (0.05) | - | 0.57 / 0.15 (0.02) |
| beta0 = calm train variance (0.22) | 39 | 0.53 / 0.00 (0.05) | 0.79 / 0.73 (0.08) | 0.74 / 0.15 (0.05) |
| beta0 = calm train variance (0.22) | 78 | 0.66 / 0.00 (0.08) | 0.80 / 0.65 (0.04) | 0.66 / 0.04 (0.01) |
| beta0 = stressed train variance (2.29) | 12 | 0.75 / 0.03 (0.05) | 0.76 / 0.64 (0.00) | 0.88 / 0.03 (0.03) |
| beta0 = stressed train variance (2.29) | 39 | 0.77 / 0.01 (0.03) | 0.69 / 0.20 (0.00) | 0.96 / 0.05 (0.06) |
| beta0 = stressed train variance (2.29) | 78 | 0.79 / 0.00 (0.03) | 0.67 / 0.07 (0.00) | 0.95 / 0.04 (0.04) |
| tighter (0,1,3,2): mean variance 1, alpha0=3 | 12 | 0.41 / 0.00 (0.00) | 0.87 / 0.71 (0.09) | 0.51 / 0.01 (0.00) |
| tighter (0,1,3,2): mean variance 1, alpha0=3 | 39 | 0.52 / 0.00 (0.01) | 0.77 / 0.69 (0.00) | 0.90 / 0.03 (0.05) |
| tighter (0,1,3,2): mean variance 1, alpha0=3 | 78 | 0.82 / 0.00 (0.06) | 0.73 / 0.43 (0.00) | 0.81 / 0.01 (0.02) |

Scaling the prior to the train variance changes the up-hit rate (up to 0.95-0.96 for (c) with beta0 = stressed variance) but leaves the down-hit rate of (a) and (c) at 0.00-0.15; only (b) detects decreases (0.38-0.76 at the default prior).

## B. 1-minute vs 5-minute grid (synthetic, Gaussian and Student-t df 5)

Cells: hit up / hit down (test FA). Thresholds calibrated per grid, family, K, noise and ratio on separate seeds (calibration null FA <= 10%, 'maxhit' rule); scored on test seeds; 500 sessions per set. Hit within 60 minutes of the break.

| noise | family | K | grid | R=2 | R=3 | R=5 | R=10 | delay R=10 up / down (min) | delay R=3 up / down (min) | fit s | filter ms/session |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gaussian | gaussian_hmm | 2 | 5min | 0.01 / 0.00 (0.00) | 0.30 / 0.06 (0.11) | 0.83 / 0.53 (0.07) | 0.98 / 0.95 (0.07) | 25 / 40 | 45 / 40 | 0.1 | 0.01 |
| gaussian | gaussian_hmm | 2 | 1min | 0.05 / 0.00 (0.03) | 0.03 / 0.00 (0.00) | 0.14 / 0.00 (0.00) | 1.00 / 1.00 (0.07) | 5 / 11 | 40 / - | 0.2 | 0.07 |
| gaussian | gaussian_hmm | 3 | 5min | 0.02 / 0.02 (0.03) | 0.40 / 0.35 (0.08) | 0.85 / 0.88 (0.06) | 0.98 / 0.96 (0.06) | 25 / 30 | 40 / 45 | 0.1 | 0.01 |
| gaussian | gaussian_hmm | 3 | 1min | 0.01 / 0.00 (0.01) | 0.24 / 0.05 (0.05) | 1.00 / 1.00 (0.10) | 1.00 / 1.00 (0.05) | 7 / 16 | 40 / 48 | 0.2 | 0.09 |
| gaussian | student_t_hmm | 2 | 5min | 0.02 / 0.01 (0.01) | 0.00 / 0.00 (0.00) | 0.82 / 0.62 (0.09) | 0.97 / 0.93 (0.06) | 25 / 40 | - / - | 0.3 | 0.02 |
| gaussian | student_t_hmm | 2 | 1min | 0.00 / 0.00 (0.00) | 0.06 / 0.01 (0.04) | 0.04 / 0.00 (0.00) | 1.00 / 1.00 (0.07) | 6 / 11 | 29 / 0 | 0.6 | 0.07 |
| gaussian | student_t_hmm | 3 | 5min | 0.00 / 0.00 (0.00) | 0.21 / 0.34 (0.10) | 0.83 / 0.93 (0.08) | 0.95 / 0.95 (0.04) | 25 / 35 | 50 / 45 | 0.3 | 0.02 |
| gaussian | student_t_hmm | 3 | 1min | 0.00 / 0.00 (0.00) | 0.10 / 0.09 (0.07) | 0.04 / 0.00 (0.00) | 1.00 / 1.00 (0.05) | 10 / 16 | 45 / 50 | 0.5 | 0.11 |
| gaussian | hsmm | 2 | 5min | 0.06 / 0.04 (0.11) | 0.35 / 0.13 (0.09) | 0.87 / 0.71 (0.08) | 0.98 / 0.96 (0.08) | 20 / 35 | 45 / 40 | 1.1 | 0.07 |
| gaussian | hsmm | 2 | 1min | 0.03 / 0.00 (0.01) | 0.03 / 0.00 (0.00) | 0.98 / 0.93 (0.15) | 1.00 / 1.00 (0.06) | 6 / 14 | 25 / - | 5.9 | 6.65 |
| gaussian | hsmm | 3 | 5min | 0.00 / 0.00 (0.00) | 0.49 / 0.65 (0.10) | 0.87 / 0.88 (0.06) | 0.98 / 0.96 (0.07) | 25 / 35 | 40 / 40 | 1.8 | 0.10 |
| gaussian | hsmm | 3 | 1min | 0.00 / 0.01 (0.01) | 0.67 / 0.83 (0.09) | 0.03 / 0.26 (0.07) | 1.00 / 1.00 (0.06) | 10 / 14 | 27 / 18 | 13.2 | 10.32 |
| student_t5 | gaussian_hmm | 2 | 5min | 0.01 / 0.00 (0.02) | 0.02 / 0.00 (0.00) | 0.60 / 0.23 (0.11) | 0.97 / 0.88 (0.12) | 25 / 40 | 45 / 0 | 0.1 | 0.01 |
| student_t5 | gaussian_hmm | 2 | 1min | 0.05 / 0.02 (0.08) | 0.30 / 0.05 (0.09) | 0.88 / 0.98 (0.10) | 0.99 / 0.99 (0.06) | 13 / 14 | 30 / 4 | 0.3 | 0.07 |
| student_t5 | gaussian_hmm | 3 | 5min | 0.01 / 0.06 (0.05) | 0.20 / 0.20 (0.09) | 0.60 / 0.39 (0.08) | 0.97 / 0.94 (0.11) | 25 / 35 | 40 / 45 | 0.1 | 0.01 |
| student_t5 | gaussian_hmm | 3 | 1min | 0.06 / 0.01 (0.03) | 0.03 / 0.02 (0.01) | 0.88 / 0.96 (0.09) | 0.99 / 1.00 (0.06) | 13 / 16 | 34 / 27 | 0.4 | 0.08 |
| student_t5 | student_t_hmm | 2 | 5min | 0.00 / 0.00 (0.02) | 0.01 / 0.00 (0.00) | 0.54 / 0.20 (0.11) | 0.97 / 0.91 (0.10) | 25 / 40 | 48 / - | 0.1 | 0.02 |
| student_t5 | student_t_hmm | 2 | 1min | 0.01 / 0.01 (0.01) | 0.03 / 0.00 (0.00) | 0.99 / 1.00 (0.11) | 1.00 / 1.00 (0.10) | 11 / 15 | 44 / 0 | 0.4 | 0.08 |
| student_t5 | student_t_hmm | 3 | 5min | 0.01 / 0.01 (0.05) | 0.18 / 0.24 (0.09) | 0.74 / 0.83 (0.13) | 0.96 / 0.96 (0.06) | 30 / 30 | 45 / 50 | 0.2 | 0.02 |
| student_t5 | student_t_hmm | 3 | 1min | 0.03 / 0.00 (0.02) | 0.77 / 0.66 (0.11) | 0.99 / 0.99 (0.11) | 1.00 / 1.00 (0.04) | 13 / 17 | 37 / 43 | 0.5 | 0.11 |
| student_t5 | hsmm | 2 | 5min | 0.02 / 0.03 (0.05) | 0.07 / 0.03 (0.09) | 0.74 / 0.61 (0.09) | 0.98 / 0.93 (0.10) | 25 / 40 | 45 / 15 | 1.3 | 0.09 |
| student_t5 | hsmm | 2 | 1min | 0.11 / 0.02 (0.07) | 0.41 / 0.05 (0.09) | 0.99 / 0.98 (0.06) | 1.00 / 0.99 (0.02) | 12 / 13 | 30 / 1 | 7.3 | 6.32 |
| student_t5 | hsmm | 3 | 5min | 0.01 / 0.03 (0.04) | 0.16 / 0.36 (0.09) | 0.69 / 0.61 (0.07) | 0.98 / 0.96 (0.12) | 25 / 35 | 42 / 30 | 2.1 | 0.10 |
| student_t5 | hsmm | 3 | 1min | 0.02 / 0.00 (0.01) | 0.39 / 0.71 (0.09) | 0.97 / 0.96 (0.07) | 1.00 / 0.99 (0.06) | 11 / 12 | 32 / 24 | 20.3 | 9.18 |

Timing notes: four worker processes ran concurrently, so absolute times are indicative; filter time is wall time for all calibration and test sessions of a cell divided by their number (3,000), batch-vectorised. HSMM at 1 minute uses the protocol cap of 390 durations; the 1-minute fits use 40 training sessions (15,600 updates) against 189 sessions (14,742 updates) at 5 minutes. K = 4 (used in D4) was not run here. Run 1 of D4 (smallest-threshold rule) is not used.

## C. Real stable-day nulls, both grids

Return-only detectors (raw 1- or 5-minute return, no features, no deseasonalisation) fitted on real inner-train returns of RAW fold 3 (1-minute grid: last 40 train sessions); thresholds from part B for the same grid / family / K / noise / ratio; 400 stable-day null splices (D2 sampling). Cells: share of null sessions with any confirmed alarm / alarms per 20 sessions.

| family | K | grid | Gaussian R=3 | t5 R=3 | Gaussian R=10 | t5 R=10 |
|---|---|---|---|---|---|---|
| gaussian_hmm | 2 | 5min | 0.64 / 16.2 (thr 0.95) | 0.00 / 0.0 (thr 0.99) | 0.97 / 51.3 (thr 0.5) | 0.79 / 27.1 (thr 0.8) |
| gaussian_hmm | 2 | 1min | 0.93 / 75.2 (thr 0.8) | 0.93 / 75.2 (thr 0.8) | 1.00 / 107.2 (thr 0.6) | 0.12 / 2.4 (thr 0.99) |
| gaussian_hmm | 3 | 5min | 0.70 / 24.8 (thr 0.9) | 0.59 / 13.8 (thr 0.95) | 0.96 / 54.0 (thr 0.5) | 0.83 / 33.4 (thr 0.8) |
| gaussian_hmm | 3 | 1min | 0.15 / 4.5 (thr 0.999) | 0.28 / 6.4 (thr 0.995) | 0.28 / 6.4 (thr 0.995) | 0.28 / 6.5 (thr 0.99) |
| student_t_hmm | 2 | 5min | 0.68 / 20.2 (thr 0.8) | 0.00 / 0.0 (thr 0.99) | 0.79 / 34.5 (thr 0.5) | 0.79 / 34.5 (thr 0.5) |
| student_t_hmm | 2 | 1min | 0.81 / 58.2 (thr 0.8) | 0.00 / 0.0 (thr 0.999) | 0.93 / 76.5 (thr 0.5) | 0.78 / 41.6 (thr 0.9) |
| student_t_hmm | 3 | 5min | 0.69 / 18.7 (thr 0.9) | 0.69 / 18.7 (thr 0.9) | 1.00 / 67.2 (thr 0.6) | 1.00 / 67.2 (thr 0.6) |
| student_t_hmm | 3 | 1min | 0.00 / 0.0 (thr 0.999) | 0.67 / 21.1 (thr 0.99) | 0.67 / 21.1 (thr 0.99) | 0.67 / 21.1 (thr 0.99) |
| hsmm | 2 | 5min | 0.52 / 15.0 (thr 0.9) | 0.43 / 9.7 (thr 0.95) | 0.83 / 45.0 (thr 0.5) | 0.72 / 25.6 (thr 0.7) |
| hsmm | 2 | 1min | 0.92 / 44.7 (thr 0.8) | 1.00 / 74.2 (thr 0.6) | 0.92 / 44.7 (thr 0.8) | 0.78 / 21.8 (thr 0.95) |
| hsmm | 3 | 5min | 0.76 / 30.6 (thr 0.8) | 0.76 / 30.6 (thr 0.8) | 0.85 / 70.2 (thr 0.6) | 0.85 / 51.1 (thr 0.7) |
| hsmm | 3 | 1min | 0.97 / 54.9 (thr 0.9) | 0.97 / 54.9 (thr 0.9) | 0.29 / 6.2 (thr 0.99) | 0.87 / 31.4 (thr 0.95) |

## Files

| File | SHA-256 |
|---|---|
| section5/s5_d5a.py | `a8ec05890342f6e17ff0a8b82c5e7fa0ac45aaf559b1254d24204144f4e91d5d` |
| section5/s5_d5b.py | `3c49543c191d6151b5369535f992b9d9e1f6d2cef7af320a7390ce4099eee91c` |
| section5/s5_d5c.py | `6eb85449c10fae1e3e13f7220c3b427407d8d6fdafe38d2cd249059de5969891` |
| section5/s5_models.py | `8c0f9acbe0fb0a9d83e43bcf4d657518cd24114fd3ff9f2213d51c9ddbd91daf` |
| section5/s5_events.py | `9c96f71664e698747d179151a28e6e1ae2a37f7718eebf5c1dacfc565be65de1` |
| section5/write_d5_report.py | `31ecb761d7b292a821c2f918b5a3302fa866041bb1628f7012320fbcbe0ff914` |
| section5/results/d5a_results.json | `da594e78c200fc0f3ce420f3b149e53bb549871432b922b14e4532f39f585d9d` |
| section5/results/d5b_results.json | `067431641c97f3f8442ff723dcdce16a241062ffda2972bde91f6344133bf9db` |
| section5/results/d5c_results.json | `af22157f42679944b87a49ec09ec7a44a87515cee80cf73022be8c9de36238f9` |
