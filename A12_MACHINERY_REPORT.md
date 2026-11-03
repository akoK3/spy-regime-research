# A12 machinery check (contaminated folds only; rerun under the A12 code)

Written 2026-11-03T22:55:09.126651+00:00 UTC. Rule: `AMENDMENT_A12.md` (sha256 `dd90c6b22b85851c61e1a88be82d294ecd95d9f8893c2f246fd78278927ff96a`). Folds RAW 3 and LEGACY 29 only (both on the contamination list); one fold per call; no clean fold, no evaluation data. Statistics are not evaluable with one fold; no result enters any protocol decision. A10 figures are the earlier run (old EM tolerance, old event and hit rules, old tau range, HSMM K 2-4).

| | RAW 3 (A12) | RAW 3 (A10) | LEGACY 29 (A12) | LEGACY 29 (A10) |
|---|---|---|---|---|
| Failures | 0 | 0 | 0 | 0 |
| Total run incl. resume and freeze step (min) | 25.79 | 9.89 | 23.55 | 9.87 |
| Peak process memory (MB) | 415 | 408 | 965 | 949 |
| Min free system memory (MB) | 1816 | 1031 | 1654 | 1390 |
| Selection objective calls / seconds | 246 / 1057.8 | 215 / 158.9 | 214 / 959.7 | 198 / 240.0 |
| Scoring incl. splice build (s) | 446.0 | 425.1 | 381.7 | 325.9 |
| Threshold bisection (s) | 40.7 | 5.8 | 57.4 | 11.2 |
| Resume: second call computed / reused | 0 / 8 | 0 / 8 | 0 / 8 | 0 / 8 |
| Non-finite outputs | 0 | 0 | 0 | 0 |
| H1(a) skipped folds | 0 | 0 | 0 | 0 |

EM fits (A12 finding 6; absolute tolerance 1e-4 nats, cap 200 iterations):

| Fold | Models fitted | Starts | Starts at the cap | Median iterations | By family (starts / at cap) |
|---|---|---|---|---|---|
| RAW3 | 211 | 239 | 56 | 106.0 | gaussian_hmm 86 / 5; hsmm 83 / 12; student_t_hmm 70 / 39 |
| LEGACY29 | 161 | 187 | 30 | 109.0 | gaussian_hmm 70 / 0; hsmm 67 / 12; student_t_hmm 50 / 18 |

Selected setups (descriptive; validation QLIKE of the tuned model against the return-only model):

| Fold | Family | Features | Params | val QLIKE | return-only QLIKE |
|---|---|---|---|---|---|
| RAW3 | gaussian_hmm | rv10_partial90, momentum30_endpoint, intrabar_range_log | {'K': 4} | 0.2144 | 0.4175 |
| RAW3 | student_t_hmm | rv10_partial90, momentum30_endpoint | {'K': 4} | 0.2590 | 0.3899 |
| RAW3 | hsmm | rv10_partial90, momentum30_endpoint, intrabar_range_log | {'K': 3} | 0.2119 | 0.4213 |
| RAW3 | bocpd | momentum30_endpoint | {'lam': 12} | 0.4515 | 0.5175 |
| LEGACY29 | gaussian_hmm | rv5_strict, downside10_strict__sadj | {'K': 3} | 0.2057 | 0.2790 |
| LEGACY29 | student_t_hmm | downside5_strict | {'K': 3} | 0.2119 | 0.2786 |
| LEGACY29 | hsmm | rv10_partial90, intrabar_range_log__sadj | {'K': 3} | 0.1919 | 0.2752 |
| LEGACY29 | bocpd | momentum15_endpoint, momentum10_endpoint | {'lam': 12} | 0.3241 | 0.3361 |

Open candidate share at the close (finding 15), at the bisected threshold on the validation sessions (final-setup models): see `final_thresholds` records in the run summaries; the HSMM grid is K in {2, 3} (A11).
Files: `section5/results/a12_machinery_RAW3.json`, `a12_machinery_LEGACY29.json`, logs.
