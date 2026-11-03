# A8.4 investigation

Written 2026-11-03T05:02:40.331821+00:00 UTC. Rule: `AMENDMENT_A8_4.md` (sha256 `f57a8734aaf28fd1bac378edc7ec0f13a8f48dc7ea375e491b42612bb56d89e5`). Validation sessions only; no test-segment scoring.

## 1. Multiplicity

- Observed detectors above 2x RAW: 2 of 8.
- Permutation (primary, 10,000 re-splits of the 40 seed records, seed 84): P(at least 2 exceed) = **0.152**. Distribution of the count: 0: 0.480, 1: 0.368, 2: 0.126, 3: 0.022, 4: 0.003.
- Independent binomial (information, 100,000 draws): P(at least 2 exceed) = 0.088.

## 2. Leave-one-day-out (LEGACY 29, seeds 1001-1020)

- Seeds completed: 20. Validity check, full-day outcomes versus A8.3 file: 0 mismatches over 160 (must be 0, else void).

| Day removed | gaussian_hmm|base | gaussian_hmm|f3 | student_t_hmm|base | student_t_hmm|f3 | hsmm|base | hsmm|f3 | bocpd|base | bocpd|f3 | exceeds | clears all |
|---|---|---|---|---|---|---|---|---|---|---|
| (none) | 3 | 1 | 0 | 0 | 1 | 3 | 2 | 2 | 2 | no |
| session 3851 | 5 | 1 | 1 | 1 | 2 | 4 | 4 | 4 | 3 | no |
| session 3855 | 3 | 2 | 1 | 0 | 2 | 4 | 3 | 4 | 3 | no |
| session 3858 | 2 | 1 | 1 | 1 | 3 | 6 | 1 | 2 | 2 | no |
| session 3872 | 3 | 0 | 0 | 0 | 2 | 2 | 1 | 1 | 1 | no |
| session 3874 | 2 | 3 | 4 | 0 | 4 | 3 | 3 | 3 | 5 | no |
| session 3878 | 1 | 0 | 3 | 0 | 0 | 0 | 2 | 2 | 1 | no |
| session 3889 | 5 | 1 | 0 | 0 | 0 | 4 | 4 | 7 | 4 | no |

- Days whose removal clears all detectors: 0 (none). Single driving day: **no**.

## Decision (pre-stated)

- P1 = 0.152 (above 10%); single driving day: False.
- **Document and proceed.**
