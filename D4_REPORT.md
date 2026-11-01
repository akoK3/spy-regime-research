# Diagnostic D4 report (pure synthetic power study)

Written 2026-11-01T17:00:34.544676+00:00 UTC. Frozen detector code; D4 event rules; no market data.

## Design

- Sessions: 78 updates of iid noise (Gaussian, or Student-t df 5 scaled to unit variance); variance ratio R in 2, 3, 5, 10 at a random update j in 20-60; up = sd 1 to sqrt(R), down = sd sqrt(R) to 1. Per cell: 500 null, 500 up and 500 down test sessions. Separate seeds for training (189 sessions at the same R: 40% calm, 20% stressed, 20% up, 20% down), 500 calibration nulls, 500 + 500 calibration breaks and the test sessions.
- One model per (family, K or lambda, data type, R) fitted on the training seeds (1 start, seed 0); inputs z-scored with the pooled training mean/sd. The model therefore knows R (favourable to the detectors; my choice).
- HMM/HSMM rule (new): alarm when P(old state) < 1 - threshold for 3 consecutive real updates; old state = argmax at updates 1-2, then at each alarm; 30-min refractory and silent first 2 updates as in the frozen code.
- BOCPD alarms: (a) P(changepoint within 3 updates) = P(run length <= 2): rising edge >= threshold, held 3 updates with no new alarm (frozen `detect_bocpd`); (b) the most likely run length drops by >= m between consecutive updates (m = the threshold: 1, 2, 3, 5, 8, 12, 20, 30) and holds: at the k-th update after the drop it is <= low + k, for 3 updates; (c) P(run length < 6), same edge/hold logic as (a). lambda = 12, 39, 78; prior (0, 1, 1, 1).
- Threshold grids: HMM/HSMM 0.5-0.9999; BOCPD (a), (c) 0.01-0.999; (b) drop 1-30. Two selection rules were computed from the same fits and are both reported: run 1 'smallest' = smallest grid value with calibration-null session false-alarm share <= 0.10; run 2 'maxhit' = among grid values with calibration false-alarm share <= 0.10, the one with the highest calibration hit rate, ties to the smallest. Run 2 was added after run 1 showed the degenerate BOCPD (a)/(c) calibrations (below). Run 1 as first executed is `d4_run1_as_first_executed.json`; the 'smallest' rule reproduces it exactly.
- Hit = confirmed alarm (T_c) within 12 updates after the break (T_c availability in [tau, tau + 60 min], tau = availability of update j-1); delay = T_c - tau in minutes (median over hits). FA = share of the 500 test null sessions with any confirmed alarm; 'per20' = confirmed alarms per 20 null sessions.
- Pass mark (yours): hit >= 0.80 for R = 10 in both directions at test FA <= 0.10.

## Failure recorded in run 1

- BOCPD (a) and (c) were calibrated to threshold 0.01 and then produced no alarms at all (FA 0.00, hit 0.00) in every cell: P(run length <= 2) never falls below 0.01 (its prior floor is about 1-(1-1/lambda)^3 = 7-22%), so the rising-edge alarm cannot occur and 'smallest threshold with FA <= 10%' selects this dead zone. The false-alarm constraint is not monotone in the threshold for these alarms. This is a threshold-selection defect, not evidence about BOCPD; run 2 selects on calibration hit rate instead.

## Run 2 (threshold = highest calibration hit rate subject to calibration FA <= 0.10)

### Verdict per family (pass: R=10 hit >= 0.80 up and down, test FA <= 0.10, feasible calibration)

- **gaussian_hmm**: gaussian: **PASS** (2 of 3 configurations; gaussian_hmm|K=2, gaussian_hmm|K=3); student_t5: **FAIL** (best gaussian_hmm|K=2: hit up 0.77 / down 0.73, test FA 0.09)
- **student_t_hmm**: gaussian: **PASS** (3 of 3 configurations; student_t_hmm|K=2, student_t_hmm|K=3, student_t_hmm|K=4); student_t5: **PASS** (1 of 3 configurations; student_t_hmm|K=4)
- **hsmm**: gaussian: **PASS** (3 of 3 configurations; hsmm|K=2, hsmm|K=3, hsmm|K=4); student_t5: **PASS** (1 of 3 configurations; hsmm|K=2)
- **bocpd**: gaussian: **FAIL** (best bocpd|lam=12|b_map: hit up 0.81 / down 0.68, test FA 0.04); student_t5: **FAIL** (best bocpd|lam=78|c_r_lt_6: hit up 0.32 / down 0.01, test FA 0.09)

### R = 10, every configuration: threshold, test FA (share of null sessions), alarms per 20 null sessions, hit up / down, median delay up / down (min)

| configuration | thr (G) | FA (G) | per20 (G) | hit up/down (G) | delay (G) | pass (G) | thr (t5) | FA (t5) | per20 (t5) | hit up/down (t5) | delay (t5) | pass (t5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bocpd|lam=12|a_pcp3 | 0.7 | 0.01 | 0.2 | 0.43 / 0.01 | 25 / 12 | fail | 0.9 | 0.06 | 1.4 | 0.15 / 0.00 | 20 / 10 | fail |
| bocpd|lam=12|b_map | 3 | 0.04 | 0.8 | 0.81 / 0.68 | 25 / 30 | fail | 30 (INF) | 0.25 | 5.5 | 0.63 / 0.16 | 25 / 25 | fail |
| bocpd|lam=12|c_r_lt_6 | 0.9 | 0.01 | 0.2 | 0.55 / 0.01 | 30 / 15 | fail | 0.99 | 0.04 | 0.8 | 0.17 / 0.00 | 25 / 10 | fail |
| bocpd|lam=39|a_pcp3 | 0.5 | 0.02 | 0.3 | 0.54 / 0.00 | 25 / 15 | fail | 0.9 | 0.05 | 1.1 | 0.13 / 0.00 | 20 / 10 | fail |
| bocpd|lam=39|b_map | 8 | 0.00 | 0.1 | 0.78 / 0.65 | 30 / 50 | fail | 30 (INF) | 0.14 | 2.9 | 0.57 / 0.38 | 30 / 45 | fail |
| bocpd|lam=39|c_r_lt_6 | 0.5 | 0.07 | 1.5 | 0.90 / 0.02 | 30 / 10 | fail | 0.99 | 0.04 | 0.7 | 0.14 / 0.00 | 25 / 10 | fail |
| bocpd|lam=78|a_pcp3 | 0.2 | 0.10 | 2.1 | 0.82 / 0.01 | 25 / 10 | fail | 0.9 | 0.04 | 0.9 | 0.12 / 0.00 | 20 / 10 | fail |
| bocpd|lam=78|b_map | 5 | 0.00 | 0.1 | 0.77 / 0.39 | 35 / 55 | fail | 30 | 0.11 | 2.2 | 0.55 / 0.29 | 30 / 50 | fail |
| bocpd|lam=78|c_r_lt_6 | 0.5 | 0.02 | 0.4 | 0.83 / 0.01 | 30 / 5 | fail | 0.95 | 0.09 | 2.0 | 0.32 / 0.01 | 25 / 10 | fail |
| gaussian_hmm|K=2 | 0.5 | 0.07 | 1.4 | 0.97 / 0.98 | 25 / 35 | PASS | 0.95 | 0.09 | 2.0 | 0.77 / 0.73 | 30 / 45 | fail |
| gaussian_hmm|K=3 | 0.7 | 0.04 | 0.8 | 0.96 / 0.96 | 25 / 30 | PASS | 0.99 | 0.08 | 1.6 | 0.37 / 0.19 | 35 / 55 | fail |
| gaussian_hmm|K=4 | 0.8 | 0.11 | 2.3 | 0.97 / 0.96 | 25 / 35 | fail | 0.999 | 0.00 | 0.0 | 0.21 / 0.01 | 40 / 58 | fail |
| hsmm|K=2 | 0.5 | 0.07 | 1.6 | 0.97 / 0.96 | 25 / 35 | PASS | 0.7 | 0.08 | 1.8 | 0.92 / 0.94 | 30 / 35 | PASS |
| hsmm|K=3 | 0.6 | 0.06 | 1.1 | 0.96 / 0.95 | 25 / 25 | PASS | 0.95 | 0.09 | 1.9 | 0.75 / 0.64 | 35 / 50 | fail |
| hsmm|K=4 | 0.9 | 0.05 | 1.1 | 0.95 / 0.91 | 25 / 45 | PASS | 0.95 | 0.11 | 2.4 | 0.74 / 0.54 | 40 / 50 | fail |
| student_t_hmm|K=2 | 0.5 | 0.07 | 1.3 | 0.96 / 0.96 | 25 / 40 | PASS | 0.9 | 0.09 | 2.0 | 0.88 / 0.61 | 35 / 50 | fail |
| student_t_hmm|K=3 | 0.6 | 0.04 | 0.8 | 0.95 / 0.95 | 30 / 25 | PASS | 0.7 | 0.11 | 2.3 | 0.93 / 0.93 | 30 / 35 | fail |
| student_t_hmm|K=4 | 0.9 | 0.06 | 1.1 | 0.92 / 0.90 | 30 / 45 | PASS | 0.7 | 0.10 | 2.1 | 0.93 / 0.91 | 30 / 35 | PASS |

### Power curves 2-10x, best configuration per family (best = highest min(hit up, hit down) at R=10 among configurations with test FA <= 0.10 and a feasible calibration; if none qualifies, the highest min hit overall)

Cells: hit up / hit down (test FA). Thresholds were calibrated separately for each R.

| family | data | configuration | R=2 | R=3 | R=5 | R=10 |
|---|---|---|---|---|---|---|
| gaussian_hmm | gaussian | gaussian_hmm|K=2 | 0.01 / 0.00 (0.00) | 0.04 / 0.02 (0.02) | 0.14 / 0.01 (0.04) | 0.97 / 0.98 (0.07) |
| gaussian_hmm | student_t5 | gaussian_hmm|K=2 | 0.03 / 0.02 (0.08) | 0.04 / 0.22 (0.10) | 0.07 / 0.00 (0.00) | 0.77 / 0.73 (0.09) |
| student_t_hmm | gaussian | student_t_hmm|K=2 | 0.03 / 0.00 (0.03) | 0.01 / 0.00 (0.00) | 0.06 / 0.00 (0.04) | 0.96 / 0.96 (0.07) |
| student_t_hmm | student_t5 | student_t_hmm|K=4 | 0.01 / 0.01 (0.02) | 0.01 / 0.01 (0.05) | 0.00 / 0.00 (0.00) | 0.93 / 0.91 (0.10) |
| hsmm | gaussian | hsmm|K=2 | 0.01 / 0.00 (0.00) | 0.04 / 0.02 (0.01) | 0.80 / 0.54 (0.12) | 0.97 / 0.96 (0.07) |
| hsmm | student_t5 | hsmm|K=2 | 0.06 / 0.04 (0.09) | 0.14 / 0.32 (0.08) | 0.53 / 0.73 (0.09) | 0.92 / 0.94 (0.08) |
| bocpd | gaussian | bocpd|lam=12|b_map | 0.34 / 0.20 (0.57) | 0.41 / 0.22 (0.37) | 0.56 / 0.26 (0.19) | 0.81 / 0.68 (0.04) |
| bocpd | student_t5 | bocpd|lam=78|c_r_lt_6 | 0.04 / 0.01 (0.09) | 0.02 / 0.00 (0.02) | 0.17 / 0.00 (0.06) | 0.32 / 0.01 (0.09) |

### Power curves, every configuration (hit up / hit down at the frozen threshold, test FA in brackets)

| data | configuration | R=2 | R=3 | R=5 | R=10 |
|---|---|---|---|---|---|
| gaussian | bocpd|lam=12|a_pcp3 | 0.05 / 0.00 (0.05) | 0.11 / 0.01 (0.03) | 0.24 / 0.01 (0.03) | 0.43 / 0.01 (0.01) |
| gaussian | bocpd|lam=12|b_map | 0.34 / 0.20 (0.57) | 0.41 / 0.22 (0.37) | 0.56 / 0.26 (0.19) | 0.81 / 0.68 (0.04) |
| gaussian | bocpd|lam=12|c_r_lt_6 | 0.05 / 0.00 (0.03) | 0.10 / 0.01 (0.01) | 0.27 / 0.01 (0.02) | 0.55 / 0.01 (0.01) |
| gaussian | bocpd|lam=39|a_pcp3 | 0.06 / 0.00 (0.05) | 0.15 / 0.01 (0.03) | 0.30 / 0.00 (0.03) | 0.54 / 0.00 (0.02) |
| gaussian | bocpd|lam=39|b_map | 0.11 / 0.07 (0.08) | 0.24 / 0.10 (0.04) | 0.52 / 0.26 (0.03) | 0.78 / 0.65 (0.00) |
| gaussian | bocpd|lam=39|c_r_lt_6 | 0.09 / 0.00 (0.04) | 0.19 / 0.00 (0.03) | 0.43 / 0.00 (0.04) | 0.90 / 0.02 (0.07) |
| gaussian | bocpd|lam=78|a_pcp3 | 0.11 / 0.00 (0.08) | 0.23 / 0.01 (0.06) | 0.43 / 0.00 (0.06) | 0.82 / 0.01 (0.10) |
| gaussian | bocpd|lam=78|b_map | 0.08 / 0.03 (0.03) | 0.15 / 0.03 (0.02) | 0.46 / 0.11 (0.02) | 0.77 / 0.39 (0.00) |
| gaussian | bocpd|lam=78|c_r_lt_6 | 0.12 / 0.01 (0.05) | 0.28 / 0.00 (0.06) | 0.54 / 0.00 (0.05) | 0.83 / 0.01 (0.02) |
| gaussian | gaussian_hmm|K=2 | 0.01 / 0.00 (0.00) | 0.04 / 0.02 (0.02) | 0.14 / 0.01 (0.04) | 0.97 / 0.98 (0.07) |
| gaussian | gaussian_hmm|K=3 | 0.02 / 0.01 (0.04) | 0.29 / 0.14 (0.07) | 0.81 / 0.85 (0.12) | 0.96 / 0.96 (0.04) |
| gaussian | gaussian_hmm|K=4 | 0.04 / 0.02 (0.07) | 0.15 / 0.01 (0.06) | 0.76 / 0.37 (0.12) | 0.97 / 0.96 (0.11) |
| gaussian | hsmm|K=2 | 0.01 / 0.00 (0.00) | 0.04 / 0.02 (0.01) | 0.80 / 0.54 (0.12) | 0.97 / 0.96 (0.07) |
| gaussian | hsmm|K=3 | 0.01 / 0.02 (0.06) | 0.32 / 0.63 (0.07) | 0.83 / 0.86 (0.12) | 0.96 / 0.95 (0.06) |
| gaussian | hsmm|K=4 | 0.03 / 0.01 (0.04) | 0.10 / 0.01 (0.09) | 0.75 / 0.38 (0.11) | 0.95 / 0.91 (0.05) |
| gaussian | student_t_hmm|K=2 | 0.03 / 0.00 (0.03) | 0.01 / 0.00 (0.00) | 0.06 / 0.00 (0.04) | 0.96 / 0.96 (0.07) |
| gaussian | student_t_hmm|K=3 | 0.00 / 0.00 (0.00) | 0.00 / 0.00 (0.03) | 0.76 / 0.91 (0.11) | 0.95 / 0.95 (0.04) |
| gaussian | student_t_hmm|K=4 | 0.00 / 0.02 (0.03) | 0.02 / 0.01 (0.04) | 0.35 / 0.09 (0.11) | 0.92 / 0.90 (0.06) |
| student_t5 | bocpd|lam=12|a_pcp3 | 0.04 / 0.02 (0.07) | 0.03 / 0.00 (0.05) | 0.09 / 0.00 (0.04) | 0.15 / 0.00 (0.06) |
| student_t5 | bocpd|lam=12|b_map | 0.28 / 0.17 (0.62) | 0.40 / 0.14 (0.51) | 0.49 / 0.16 (0.37) | 0.63 / 0.16 (0.25) |
| student_t5 | bocpd|lam=12|c_r_lt_6 | 0.02 / 0.01 (0.05) | 0.02 / 0.00 (0.03) | 0.09 / 0.00 (0.02) | 0.17 / 0.00 (0.04) |
| student_t5 | bocpd|lam=39|a_pcp3 | 0.03 / 0.01 (0.05) | 0.02 / 0.00 (0.03) | 0.07 / 0.00 (0.03) | 0.13 / 0.00 (0.05) |
| student_t5 | bocpd|lam=39|b_map | 0.15 / 0.06 (0.21) | 0.23 / 0.11 (0.18) | 0.39 / 0.18 (0.15) | 0.57 / 0.38 (0.14) |
| student_t5 | bocpd|lam=39|c_r_lt_6 | 0.05 / 0.01 (0.11) | 0.02 / 0.00 (0.03) | 0.07 / 0.00 (0.01) | 0.14 / 0.00 (0.04) |
| student_t5 | bocpd|lam=78|a_pcp3 | 0.03 / 0.01 (0.04) | 0.02 / 0.00 (0.03) | 0.06 / 0.00 (0.02) | 0.12 / 0.00 (0.04) |
| student_t5 | bocpd|lam=78|b_map | 0.11 / 0.03 (0.16) | 0.20 / 0.06 (0.11) | 0.36 / 0.12 (0.10) | 0.55 / 0.29 (0.11) |
| student_t5 | bocpd|lam=78|c_r_lt_6 | 0.04 / 0.01 (0.09) | 0.02 / 0.00 (0.02) | 0.17 / 0.00 (0.06) | 0.32 / 0.01 (0.09) |
| student_t5 | gaussian_hmm|K=2 | 0.03 / 0.02 (0.08) | 0.04 / 0.22 (0.10) | 0.07 / 0.00 (0.00) | 0.77 / 0.73 (0.09) |
| student_t5 | gaussian_hmm|K=3 | 0.06 / 0.02 (0.10) | 0.01 / 0.00 (0.01) | 0.04 / 0.00 (0.01) | 0.37 / 0.19 (0.08) |
| student_t5 | gaussian_hmm|K=4 | 0.02 / 0.01 (0.03) | 0.01 / 0.01 (0.01) | 0.05 / 0.01 (0.00) | 0.21 / 0.01 (0.00) |
| student_t5 | hsmm|K=2 | 0.06 / 0.04 (0.09) | 0.14 / 0.32 (0.08) | 0.53 / 0.73 (0.09) | 0.92 / 0.94 (0.08) |
| student_t5 | hsmm|K=3 | 0.05 / 0.02 (0.08) | 0.17 / 0.34 (0.10) | 0.46 / 0.65 (0.10) | 0.75 / 0.64 (0.09) |
| student_t5 | hsmm|K=4 | 0.02 / 0.01 (0.03) | 0.01 / 0.01 (0.01) | 0.53 / 0.72 (0.10) | 0.74 / 0.54 (0.11) |
| student_t5 | student_t_hmm|K=2 | 0.01 / 0.00 (0.00) | 0.00 / 0.00 (0.01) | 0.01 / 0.00 (0.00) | 0.88 / 0.61 (0.09) |
| student_t5 | student_t_hmm|K=3 | 0.00 / 0.01 (0.07) | 0.01 / 0.01 (0.07) | 0.00 / 0.00 (0.00) | 0.93 / 0.93 (0.11) |
| student_t5 | student_t_hmm|K=4 | 0.01 / 0.01 (0.02) | 0.01 / 0.01 (0.05) | 0.00 / 0.00 (0.00) | 0.93 / 0.91 (0.10) |

Cells with no feasible calibration threshold (recorded, not excluded; the strictest grid value was used): 14 of 144: gaussian|R2|bocpd|lam=12|b_map, gaussian|R5|bocpd|lam=12|b_map, gaussian|R3|bocpd|lam=12|b_map, student_t5|R5|bocpd|lam=12|b_map, student_t5|R5|bocpd|lam=39|b_map, student_t5|R5|bocpd|lam=78|b_map, student_t5|R2|bocpd|lam=12|b_map, student_t5|R2|bocpd|lam=39|b_map, student_t5|R2|bocpd|lam=78|b_map, student_t5|R3|bocpd|lam=12|b_map ...

## Run 1 (threshold = smallest value with calibration FA <= 0.10)

### Verdict per family (pass: R=10 hit >= 0.80 up and down, test FA <= 0.10, feasible calibration)

- **gaussian_hmm**: gaussian: **PASS** (2 of 3 configurations; gaussian_hmm|K=2, gaussian_hmm|K=3); student_t5: **FAIL** (best gaussian_hmm|K=2: hit up 0.77 / down 0.73, test FA 0.09)
- **student_t_hmm**: gaussian: **PASS** (3 of 3 configurations; student_t_hmm|K=2, student_t_hmm|K=3, student_t_hmm|K=4); student_t5: **PASS** (1 of 3 configurations; student_t_hmm|K=4)
- **hsmm**: gaussian: **PASS** (3 of 3 configurations; hsmm|K=2, hsmm|K=3, hsmm|K=4); student_t5: **PASS** (1 of 3 configurations; hsmm|K=2)
- **bocpd**: gaussian: **FAIL** (best bocpd|lam=12|b_map: hit up 0.76 / down 0.72, test FA 0.04); student_t5: **FAIL** (best bocpd|lam=12|a_pcp3: hit up 0.00 / down 0.00, test FA 0.00)

### R = 10, every configuration: threshold, test FA (share of null sessions), alarms per 20 null sessions, hit up / down, median delay up / down (min)

| configuration | thr (G) | FA (G) | per20 (G) | hit up/down (G) | delay (G) | pass (G) | thr (t5) | FA (t5) | per20 (t5) | hit up/down (t5) | delay (t5) | pass (t5) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| bocpd|lam=12|a_pcp3 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| bocpd|lam=12|b_map | 1 | 0.04 | 0.9 | 0.76 / 0.72 | 25 / 30 | fail | 30 (INF) | 0.25 | 5.5 | 0.63 / 0.16 | 25 / 25 | fail |
| bocpd|lam=12|c_r_lt_6 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| bocpd|lam=39|a_pcp3 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| bocpd|lam=39|b_map | 1 | 0.00 | 0.1 | 0.78 / 0.63 | 30 / 50 | fail | 30 (INF) | 0.14 | 2.9 | 0.57 / 0.38 | 30 / 45 | fail |
| bocpd|lam=39|c_r_lt_6 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| bocpd|lam=78|a_pcp3 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| bocpd|lam=78|b_map | 1 | 0.00 | 0.1 | 0.76 / 0.38 | 35 / 55 | fail | 30 | 0.11 | 2.2 | 0.55 / 0.29 | 30 / 50 | fail |
| bocpd|lam=78|c_r_lt_6 | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail | 0.01 | 0.00 | 0.0 | 0.00 / 0.00 | - / - | fail |
| gaussian_hmm|K=2 | 0.5 | 0.07 | 1.4 | 0.97 / 0.98 | 25 / 35 | PASS | 0.95 | 0.09 | 2.0 | 0.77 / 0.73 | 30 / 45 | fail |
| gaussian_hmm|K=3 | 0.5 | 0.05 | 1.0 | 0.97 / 0.93 | 25 / 20 | PASS | 0.99 | 0.08 | 1.6 | 0.37 / 0.19 | 35 / 55 | fail |
| gaussian_hmm|K=4 | 0.8 | 0.11 | 2.3 | 0.97 / 0.96 | 25 / 35 | fail | 0.999 | 0.00 | 0.0 | 0.21 / 0.01 | 40 / 58 | fail |
| hsmm|K=2 | 0.5 | 0.07 | 1.6 | 0.97 / 0.96 | 25 / 35 | PASS | 0.7 | 0.08 | 1.8 | 0.92 / 0.94 | 30 / 35 | PASS |
| hsmm|K=3 | 0.5 | 0.06 | 1.2 | 0.97 / 0.92 | 25 / 20 | PASS | 0.95 | 0.09 | 1.9 | 0.75 / 0.64 | 35 / 50 | fail |
| hsmm|K=4 | 0.9 | 0.05 | 1.1 | 0.95 / 0.91 | 25 / 45 | PASS | 0.95 | 0.11 | 2.4 | 0.74 / 0.54 | 40 / 50 | fail |
| student_t_hmm|K=2 | 0.5 | 0.07 | 1.3 | 0.96 / 0.96 | 25 / 40 | PASS | 0.9 | 0.09 | 2.0 | 0.88 / 0.61 | 35 / 50 | fail |
| student_t_hmm|K=3 | 0.5 | 0.04 | 0.9 | 0.95 / 0.94 | 30 / 20 | PASS | 0.7 | 0.11 | 2.3 | 0.93 / 0.93 | 30 / 35 | fail |
| student_t_hmm|K=4 | 0.9 | 0.06 | 1.1 | 0.92 / 0.90 | 30 / 45 | PASS | 0.7 | 0.10 | 2.1 | 0.93 / 0.91 | 30 / 35 | PASS |

Cells with no feasible calibration threshold (recorded, not excluded; the strictest grid value was used): 14 of 144: gaussian|R2|bocpd|lam=12|b_map, gaussian|R5|bocpd|lam=12|b_map, gaussian|R3|bocpd|lam=12|b_map, student_t5|R5|bocpd|lam=12|b_map, student_t5|R5|bocpd|lam=39|b_map, student_t5|R5|bocpd|lam=78|b_map, student_t5|R2|bocpd|lam=12|b_map, student_t5|R2|bocpd|lam=39|b_map, student_t5|R2|bocpd|lam=78|b_map, student_t5|R3|bocpd|lam=12|b_map ...

## Files

| File | SHA-256 |
|---|---|
| section5/s5_d4.py | `d025cbcff83db91050a89215ddfba9e5d5154ef7b8c27886d8778b0c6c55f8e0` |
| section5/s5_events.py | `9c96f71664e698747d179151a28e6e1ae2a37f7718eebf5c1dacfc565be65de1` |
| section5/s5_models.py | `653952a0c8e70fb111dc2ab59a568a06b67fd780d444f2b717093be626ada664` |
| section5/write_d4_report.py | `cd8022b308f54ce5033c5d4c656ba774e06a5990be9473c8fa8a3fac81b46a3d` |
| section5/results/d4_results.json | `f7fdea93398db546a44be0993716086fe6fa12576da442351d62d3004516128a` |
| section5/results/d4_run1_as_first_executed.json | `d6ed570ed5d7900e26f7c1ec622af59e4cf783319576fbe0534d0a9d49a87099` |
