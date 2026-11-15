# Absolute detection performance (POST HOC, descriptive)

POST HOC descriptive (Veksler's point): absolute detection performance. Development folds with saved models; evaluation from already-written outputs only. Changes no frozen, MR2 or evaluation result.

Source: `section5/results/posthoc_absolute_detection.json`; script `diagnostics/absolute_detection.py` (sha256 `74d8d82ee0f0b9c359a43ba5b5a6409b435bec3963c46d88cecd71c6b1cd7c42`); code version `a0323ed24d68e896`.

## 1. Absolute pAUC, development test splices (mean over folds; confirmatory folds)

| Era | Family | Folds scored | pAUC feature | pAUC baseline | Difference |
|---|---|---|---|---|---|
| LEGACY | gaussian_hmm | 21/25 | 0.219 | 0.114 | 0.105 |
| LEGACY | student_t_hmm | 21/25 | 0.183 | 0.114 | 0.069 |
| LEGACY | hsmm | 21/25 | 0.237 | 0.124 | 0.113 |
| LEGACY | bocpd | 21/25 | 0.054 | 0.054 | 0.000 |
| RAW | gaussian_hmm | 1/1 | 0.251 | 0.157 | 0.093 |
| RAW | student_t_hmm | 1/1 | 0.166 | 0.117 | 0.049 |
| RAW | hsmm | 1/1 | 0.193 | 0.128 | 0.065 |
| RAW | bocpd | 1/1 | 0.044 | 0.044 | 0.000 |

pAUC = area under the curve of hit rate (share of break splices hit within 60 min) against null alarm rate (confirmed alarms per null spliced session) for null alarm rates 0-0.5, divided by 0.5 (protocol 5.0). The two axes are in different units, so there is no simple chance level; the baseline column is the returns-only reference.

## 2. Detection at the calibrated threshold, by planted variance ratio and direction (development, confirmatory folds, feature model)

Hit = T_d after onset and T_c within 60 min (the H1(a) hit). Delay = minutes from onset to T_c: median [IQR] (n). 'Any' = first confirmation after onset before the session end.

### LEGACY

| Family | Ratio, direction | Splices | Hit within 60 min | Delay of those hits | Detected by close | Delay to first confirmation |
|---|---|---|---|---|---|---|
| gaussian_hmm | R1.5 up | 2016 | 0.04 | 40 [25, 50] (n 85) | 0.08 | 55 [40, 100] (n 163) |
| gaussian_hmm | R1.5 down | 2016 | 0.01 | 35 [25, 55] (n 23) | 0.03 | 82 [55, 149] (n 66) |
| gaussian_hmm | R2 up | 2016 | 0.10 | 30 [20, 45] (n 195) | 0.15 | 45 [25, 76] (n 296) |
| gaussian_hmm | R2 down | 2016 | 0.03 | 30 [25, 44] (n 58) | 0.06 | 60 [30, 135] (n 115) |
| gaussian_hmm | R3 up | 2016 | 0.24 | 25 [20, 40] (n 477) | 0.32 | 35 [20, 65] (n 640) |
| gaussian_hmm | R3 down | 2016 | 0.05 | 30 [25, 40] (n 106) | 0.09 | 45 [25, 80] (n 173) |
| gaussian_hmm | R5 up | 2016 | 0.46 | 20 [15, 35] (n 919) | 0.52 | 25 [15, 40] (n 1045) |
| gaussian_hmm | R5 down | 2016 | 0.11 | 25 [20, 35] (n 213) | 0.13 | 30 [20, 50] (n 257) |
| gaussian_hmm | R10 up | 2016 | 0.63 | 20 [15, 25] (n 1263) | 0.66 | 20 [15, 30] (n 1340) |
| gaussian_hmm | R10 down | 2016 | 0.16 | 20 [20, 30] (n 319) | 0.18 | 20 [20, 35] (n 356) |
| student_t_hmm | R1.5 up | 2016 | 0.04 | 35 [25, 45] (n 90) | 0.10 | 70 [40, 135] (n 204) |
| student_t_hmm | R1.5 down | 2016 | 0.02 | 45 [35, 55] (n 37) | 0.07 | 110 [60, 155] (n 135) |
| student_t_hmm | R2 up | 2016 | 0.10 | 30 [20, 45] (n 201) | 0.16 | 50 [30, 90] (n 332) |
| student_t_hmm | R2 down | 2016 | 0.03 | 40 [30, 55] (n 54) | 0.10 | 110 [60, 165] (n 192) |
| student_t_hmm | R3 up | 2016 | 0.20 | 25 [20, 40] (n 402) | 0.28 | 35 [20, 70] (n 568) |
| student_t_hmm | R3 down | 2016 | 0.06 | 30 [25, 45] (n 121) | 0.14 | 72 [35, 129] (n 274) |
| student_t_hmm | R5 up | 2016 | 0.37 | 25 [20, 40] (n 744) | 0.46 | 30 [20, 55] (n 935) |
| student_t_hmm | R5 down | 2016 | 0.11 | 35 [25, 45] (n 221) | 0.19 | 55 [30, 105] (n 383) |
| student_t_hmm | R10 up | 2016 | 0.53 | 20 [15, 30] (n 1072) | 0.61 | 25 [15, 40] (n 1239) |
| student_t_hmm | R10 down | 2016 | 0.16 | 30 [20, 40] (n 326) | 0.26 | 45 [25, 90] (n 532) |
| hsmm | R1.5 up | 2016 | 0.04 | 35 [20, 50] (n 72) | 0.07 | 60 [35, 102] (n 143) |
| hsmm | R1.5 down | 2016 | 0.01 | 35 [25, 49] (n 26) | 0.04 | 90 [51, 125] (n 82) |
| hsmm | R2 up | 2016 | 0.09 | 30 [20, 45] (n 174) | 0.15 | 50 [30, 84] (n 294) |
| hsmm | R2 down | 2016 | 0.02 | 30 [20, 50] (n 46) | 0.05 | 70 [44, 108] (n 108) |
| hsmm | R3 up | 2016 | 0.22 | 30 [20, 40] (n 452) | 0.31 | 35 [20, 70] (n 633) |
| hsmm | R3 down | 2016 | 0.06 | 35 [25, 46] (n 128) | 0.11 | 50 [30, 92] (n 223) |
| hsmm | R5 up | 2016 | 0.48 | 20 [15, 35] (n 968) | 0.55 | 25 [20, 45] (n 1112) |
| hsmm | R5 down | 2016 | 0.13 | 30 [20, 40] (n 259) | 0.18 | 40 [25, 65] (n 360) |
| hsmm | R10 up | 2016 | 0.69 | 20 [15, 25] (n 1397) | 0.73 | 20 [15, 30] (n 1472) |
| hsmm | R10 down | 2016 | 0.21 | 20 [20, 30] (n 423) | 0.26 | 25 [20, 52] (n 531) |
| bocpd | R1.5 up | 2016 | 0.02 | 45 [30, 55] (n 49) | 0.17 | 135 [85, 195] (n 338) |
| bocpd | R1.5 down | 2016 | 0.01 | 45 [35, 55] (n 22) | 0.18 | 160 [110, 209] (n 362) |
| bocpd | R2 up | 2016 | 0.03 | 42 [30, 60] (n 58) | 0.17 | 130 [75, 190] (n 340) |
| bocpd | R2 down | 2016 | 0.01 | 48 [40, 55] (n 28) | 0.16 | 148 [100, 200] (n 326) |
| bocpd | R3 up | 2016 | 0.04 | 40 [30, 50] (n 85) | 0.15 | 105 [55, 170] (n 293) |
| bocpd | R3 down | 2016 | 0.01 | 40 [30, 50] (n 25) | 0.14 | 155 [108, 200] (n 291) |
| bocpd | R5 up | 2016 | 0.05 | 40 [30, 50] (n 101) | 0.12 | 80 [40, 175] (n 234) |
| bocpd | R5 down | 2016 | 0.01 | 55 [50, 60] (n 18) | 0.13 | 148 [105, 200] (n 266) |
| bocpd | R10 up | 2016 | 0.09 | 30 [25, 40] (n 175) | 0.13 | 40 [25, 81] (n 264) |
| bocpd | R10 down | 2016 | 0.02 | 50 [30, 55] (n 31) | 0.14 | 135 [89, 200] (n 276) |

### RAW

| Family | Ratio, direction | Splices | Hit within 60 min | Delay of those hits | Detected by close | Delay to first confirmation |
|---|---|---|---|---|---|---|
| gaussian_hmm | R1.5 up | 96 | 0.04 | 40 [29, 52] (n 4) | 0.07 | 60 [40, 80] (n 7) |
| gaussian_hmm | R1.5 down | 96 | 0.00 | – | 0.00 | – |
| gaussian_hmm | R2 up | 96 | 0.09 | 40 [30, 40] (n 9) | 0.15 | 45 [32, 69] (n 14) |
| gaussian_hmm | R2 down | 96 | 0.00 | – | 0.00 | – |
| gaussian_hmm | R3 up | 96 | 0.24 | 30 [20, 32] (n 23) | 0.32 | 30 [25, 60] (n 31) |
| gaussian_hmm | R3 down | 96 | 0.00 | – | 0.00 | – |
| gaussian_hmm | R5 up | 96 | 0.49 | 20 [15, 38] (n 47) | 0.62 | 25 [15, 51] (n 60) |
| gaussian_hmm | R5 down | 96 | 0.00 | – | 0.00 | – |
| gaussian_hmm | R10 up | 96 | 0.83 | 15 [15, 25] (n 80) | 0.85 | 15 [15, 25] (n 82) |
| gaussian_hmm | R10 down | 96 | 0.04 | 50 [41, 55] (n 4) | 0.04 | 50 [41, 55] (n 4) |
| student_t_hmm | R1.5 up | 96 | 0.01 | 35 [35, 35] (n 1) | 0.02 | 60 [48, 72] (n 2) |
| student_t_hmm | R1.5 down | 96 | 0.00 | – | 0.01 | 70 [70, 70] (n 1) |
| student_t_hmm | R2 up | 96 | 0.06 | 18 [15, 28] (n 6) | 0.07 | 20 [15, 42] (n 7) |
| student_t_hmm | R2 down | 96 | 0.00 | – | 0.00 | – |
| student_t_hmm | R3 up | 96 | 0.10 | 30 [20, 34] (n 10) | 0.12 | 30 [20, 45] (n 12) |
| student_t_hmm | R3 down | 96 | 0.01 | 25 [25, 25] (n 1) | 0.03 | 105 [65, 135] (n 3) |
| student_t_hmm | R5 up | 96 | 0.09 | 20 [15, 25] (n 9) | 0.19 | 55 [21, 99] (n 18) |
| student_t_hmm | R5 down | 96 | 0.02 | 32 [29, 36] (n 2) | 0.06 | 80 [49, 89] (n 6) |
| student_t_hmm | R10 up | 96 | 0.43 | 25 [20, 30] (n 41) | 0.51 | 30 [20, 50] (n 49) |
| student_t_hmm | R10 down | 96 | 0.05 | 50 [40, 55] (n 5) | 0.06 | 52 [42, 55] (n 6) |
| hsmm | R1.5 up | 96 | 0.03 | 35 [28, 40] (n 3) | 0.04 | 40 [31, 55] (n 4) |
| hsmm | R1.5 down | 96 | 0.00 | – | 0.00 | – |
| hsmm | R2 up | 96 | 0.04 | 32 [26, 39] (n 4) | 0.07 | 50 [32, 75] (n 7) |
| hsmm | R2 down | 96 | 0.00 | – | 0.00 | – |
| hsmm | R3 up | 96 | 0.11 | 30 [18, 42] (n 11) | 0.21 | 58 [29, 100] (n 20) |
| hsmm | R3 down | 96 | 0.00 | – | 0.00 | – |
| hsmm | R5 up | 96 | 0.26 | 25 [15, 45] (n 25) | 0.39 | 45 [15, 70] (n 37) |
| hsmm | R5 down | 96 | 0.00 | – | 0.00 | – |
| hsmm | R10 up | 96 | 0.68 | 20 [15, 30] (n 65) | 0.74 | 25 [15, 35] (n 71) |
| hsmm | R10 down | 96 | 0.00 | – | 0.00 | – |
| bocpd | R1.5 up | 96 | 0.01 | 60 [60, 60] (n 1) | 0.17 | 172 [154, 229] (n 16) |
| bocpd | R1.5 down | 96 | 0.02 | 35 [30, 40] (n 2) | 0.19 | 190 [150, 229] (n 18) |
| bocpd | R2 up | 96 | 0.01 | 20 [20, 20] (n 1) | 0.11 | 145 [110, 192] (n 11) |
| bocpd | R2 down | 96 | 0.04 | 45 [42, 46] (n 4) | 0.22 | 165 [70, 215] (n 21) |
| bocpd | R3 up | 96 | 0.03 | 40 [30, 40] (n 3) | 0.14 | 115 [65, 135] (n 13) |
| bocpd | R3 down | 96 | 0.01 | 60 [60, 60] (n 1) | 0.17 | 168 [116, 191] (n 16) |
| bocpd | R5 up | 96 | 0.04 | 22 [20, 26] (n 4) | 0.06 | 28 [21, 86] (n 6) |
| bocpd | R5 down | 96 | 0.02 | 48 [46, 49] (n 2) | 0.11 | 180 [132, 218] (n 11) |
| bocpd | R10 up | 96 | 0.04 | 22 [20, 28] (n 4) | 0.05 | 25 [20, 35] (n 5) |
| bocpd | R10 down | 96 | 0.00 | – | 0.04 | 235 [195, 264] (n 4) |

Per duration (permanent, 30, 60, 120 min) and for the baseline models: `development.<era>.<scope>.<family>.<model>.cells` in the JSON.

## 3. Alarm rates

| Era | Family | Null splices: alarms per splice, feature / baseline | Real test sessions: alarms per session, feature / baseline (A17 records) |
|---|---|---|---|
| LEGACY | gaussian_hmm | 0.177 / 0.231 | 0.202 / 0.231 |
| LEGACY | student_t_hmm | 0.208 / 0.213 | 0.193 / 0.224 |
| LEGACY | hsmm | 0.149 / 0.216 | 0.214 / 0.232 |
| LEGACY | bocpd | 0.180 / 0.180 | 0.206 / 0.205 |
| RAW | gaussian_hmm | 0.052 / 0.085 | 0.212 / 0.254 |
| RAW | student_t_hmm | 0.048 / 0.207 | 0.225 / 0.229 |
| RAW | hsmm | 0.033 / 0.133 | 0.222 / 0.212 |
| RAW | bocpd | 0.198 / 0.198 | 0.217 / 0.218 |

Thresholds were calibrated to 0.2 alarms per validation session (A7).

## 4. FOMC hit rates (release to release + 60 min)

| Data | Era | Family | Events | Hit rate feature | Hit rate baseline |
|---|---|---|---|---|---|
| development (A17) | LEGACY | gaussian_hmm | 94 | 0.49 | 0.34 |
| development (A17) | LEGACY | student_t_hmm | 94 | 0.30 | 0.24 |
| development (A17) | LEGACY | hsmm | 94 | 0.38 | 0.34 |
| development (A17) | LEGACY | bocpd | 94 | 0.40 | 0.51 |
| development (A17) | RAW | gaussian_hmm | 4 | 0.50 | 0.75 |
| development (A17) | RAW | student_t_hmm | 4 | 0.50 | 0.50 |
| development (A17) | RAW | hsmm | 4 | 1.00 | 0.50 |
| development (A17) | RAW | bocpd | 4 | 0.50 | 1.00 |
| evaluation (written) | LEGACY | gaussian_hmm | 24 | 0.71 | 0.29 |
| evaluation (written) | LEGACY | student_t_hmm | 24 | 0.71 | 0.29 |
| evaluation (written) | LEGACY | hsmm | 24 | 0.67 | 0.29 |
| evaluation (written) | LEGACY | bocpd | 24 | 0.33 | 0.33 |
| evaluation (written) | RAW | gaussian_hmm | 14 | 0.71 | 0.57 |
| evaluation (written) | RAW | student_t_hmm | 14 | 0.50 | 0.79 |
| evaluation (written) | RAW | hsmm | 14 | 0.79 | 0.64 |
| evaluation (written) | RAW | bocpd | 14 | 0.29 | 0.29 |

## 5. Evaluation periods (already-written outputs; adaptive/exploratory label, previously exposed periods)

| Era | Family | Sessions | Alarms per session, feature / baseline | Confirmation lag T_c - T_d, min: median [IQR] (n) | Absolute pAUC |
|---|---|---|---|---|---|
| LEGACY | gaussian_hmm | 800 | 0.214 / 0.141 | 10 [10, 10] (n 171) | not stored |
| LEGACY | student_t_hmm | 800 | 0.215 / 0.168 | 10 [10, 10] (n 172) | not stored |
| LEGACY | hsmm | 800 | 0.159 / 0.101 | 10 [10, 10] (n 127) | not stored |
| LEGACY | bocpd | 800 | 0.186 / 0.186 | 15 [15, 15] (n 149) | not stored |
| RAW | gaussian_hmm | 445 | 0.137 / 0.276 | 10 [10, 10] (n 61) | not stored |
| RAW | student_t_hmm | 445 | 0.117 / 0.310 | 10 [10, 10] (n 52) | not stored |
| RAW | hsmm | 445 | 0.200 / 0.306 | 10 [10, 10] (n 89) | not stored |
| RAW | bocpd | 445 | 0.187 / 0.187 | 15 [15, 15] (n 83) | not stored |

The evaluation outputs store only the pAUC difference (H1a), and a break-onset delay needs a planted onset, so onset delays exist only for the development splices. Sources: `section5/results/evaluation_{LEGACY,RAW}.json`, `section5/results/a17/a17_results.json`, `section5/results/a17/ckpt/`.
