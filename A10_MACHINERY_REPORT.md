# A10 machinery check (contaminated folds only)

Written 2026-11-03T15:20:53.273012+00:00 UTC. Rule: `AMENDMENT_A10.md` (sha256 `73d0a99fdb9d5e5a753bba8f1a85c3f2ecc5629a5b03ae8f3d6bcfe8f52c4763`). Folds: RAW 3 and LEGACY 29 only (both on the contamination list); one fold per call; no clean fold, no evaluation data. Statistics are not evaluable with one fold; no result enters any protocol decision.

| | RAW 3 | LEGACY 29 |
|---|---|---|
| Failures | 0 | 0 |
| Context load and features (s) | 3.6 | 15.3 |
| Total run incl. resume and freeze step (min) | 9.89 | 9.87 |
| Peak process memory (MB) | 408 | 949 |
| Min free system memory (MB) | 1031 | 1390 |
| Selection objective calls / seconds | 215 / 158.9 | 198 / 240.0 |
| Scoring (4 families, incl. splice build) seconds | 425.1 | 325.9 |
| Threshold bisection seconds | 5.8 | 11.2 |
| Resume: second call computed / reused | 0 / 8 | 0 / 8 |
| Non-finite outputs | 0 | 0 |
| H1(a) skipped folds | 0 | 0 |
| Fold-level tests not evaluable (n<2) | True | True |

Selected setups (descriptive; validation QLIKE of the tuned model against the return-only model):

| Fold | Family | Features | Params | val QLIKE | return-only QLIKE |
|---|---|---|---|---|---|
| RAW3 | gaussian_hmm | rv10_partial90, momentum30_endpoint | {'K': 3} | 0.2160 | 0.4508 |
| RAW3 | student_t_hmm | rv10_partial90, momentum30_endpoint | {'K': 4} | 0.2572 | 0.4120 |
| RAW3 | hsmm | rv10_partial90, momentum30_endpoint | {'K': 3} | 0.2116 | 0.4263 |
| RAW3 | bocpd | momentum30_endpoint | {'lam': 12} | 0.4515 | 0.5175 |
| LEGACY29 | gaussian_hmm | rv5_strict | {'K': 4} | 0.1929 | 0.2879 |
| LEGACY29 | student_t_hmm | downside5_strict | {'K': 4} | 0.2094 | 0.2785 |
| LEGACY29 | hsmm | rv10_partial90, downside10_strict__sadj | {'K': 3} | 0.1894 | 0.2753 |
| LEGACY29 | bocpd | momentum15_endpoint, momentum10_endpoint | {'lam': 12} | 0.3241 | 0.3361 |

Deviation as stated in A10: synthetic delay is not computed during the selection search (NaN). Open item: the era-level numeric threshold for 5.13 is not defined by A6-A10.
Files: `section5/results/a10_machinery_RAW3.json`, `a10_machinery_LEGACY29.json`, logs, `section5/s5_backend.py`, `s5_machinery_run.py`.
