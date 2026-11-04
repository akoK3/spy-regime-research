# A13 report: gate sanity check and machinery timing (RAW 3 only, contaminated fold)

Written 2026-11-04T00:06:15.296528+00:00 UTC. Rule: `AMENDMENT_A13.md` (sha256 `301be6ed93fdf80d9a3841664faf8398d2a8b5d30073ad00ba9f88d20e7c5755`). Validation sessions for the gate; no clean fold, no evaluation data. No result enters any protocol decision.

## Gate sanity check (A8.2 rule, seed 777, A13 code)

Detectors inside: **8 of 8** (A8.2 result on the earlier code: 8 of 8). Stable validation days 16.

| Detector | pAUC P1 | pAUC P2 | P2 day-level 95% CI | Inside (A13) | Inside (A8.2 earlier code) |
|---|---|---|---|---|---|
| gaussian_hmm|base | 0.018 | 0.025 | [0.009, 0.048] | True | True |
| gaussian_hmm|f3 | 0.009 | 0.021 | [0.006, 0.043] | True | True |
| student_t_hmm|base | 0.017 | 0.022 | [0.007, 0.050] | True | True |
| student_t_hmm|f3 | 0.009 | 0.023 | [0.004, 0.050] | True | True |
| hsmm|base | 0.021 | 0.025 | [0.005, 0.059] | True | True |
| hsmm|f3 | 0.008 | 0.021 | [0.002, 0.054] | True | True |
| bocpd|base | 0.021 | 0.018 | [0.004, 0.038] | True | True |
| bocpd|f3 | 0.013 | 0.027 | [0.010, 0.050] | True | True |

## Machinery timing on RAW 3

| | A10 code (EM relative 1e-4, cap 200) | A12 code (absolute 1e-4 nats, cap 200) | A13 code (1e-6 per observation, cap 500) |
|---|---|---|---|
| Failures | 0 | 0 | 0 |
| Total run incl. resume and freeze step (min) | 9.89 | 25.79 | 19.92 |
| Selection objective calls / seconds | 215 / 158.9 | 246 / 1057.8 | 246 / 640.3 |
| Scoring incl. splice build (s) | 425.1 | 446.0 | 526.2 |
| Threshold bisection (s) | 5.8 | 40.7 | 25.8 |
| Peak process memory (MB) | 408 | 415 | 416 |
| Resume: second call computed / reused | 0 / 8 | 0 / 8 | 0 / 8 |
| Non-finite outputs | 0 | 0 | 0 |

EM cap hits per family (starts at the cap / starts):

| Family | A12 (cap 200) | A13 (cap 500) |
|---|---|---|
| gaussian_hmm | 5 / 86 | 0 / 86 |
| hsmm | 12 / 83 | 1 / 83 |
| student_t_hmm | 39 / 70 | 0 / 70 |

Total: A12 56 of 239 starts at the cap, median 106.0 iterations; A13 1 of 239, median 58.0 iterations.

Files: `section5/results/a13_gate_RAW3_seed777.json`, `a13_machinery_RAW3.json`, logs.
