# A9 dry run (SYNTHETIC data only)

Written 2026-11-03T14:52:53.040262+00:00 UTC. Rule: `AMENDMENT_A9.md` (sha256 `d915f7c90a38a0236a3962857235d7e1096b16f54065bb8104d3795ee4947bb0`). No market data, no test or evaluation data; synthetic backend with known effects (Gaussian HMM +0.08, Student-t HMM +0.06, BOCPD +0.07, HSMM 0), 16 LEGACY + 4 RAW synthetic folds, 4 synthetic exclusions.

| Family | p (IU, block bootstrap) | Holm p_adj (3 H1 families) | Reject |
|---|---|---|---|
| gaussian_hmm | 0.0005 | 0.0015 | True |
| student_t_hmm | 0.0005 | 0.0015 | True |
| hsmm | 0.5727 | 0.5727 | False |
| bocpd (secondary) | 0.0005 | n/a | n/a (outside Holm) |

- Checks: first run 160 units computed, second run 160 hits and 0 misses (resume); H1(a) skipped on 2 folds with too few stable days; confirmatory folds used 14, all-folds sensitivity 18.
- Freeze written and verified; H1 passing: gaussian_hmm, student_t_hmm; H2 primary detector: gaussian_hmm (tie on simplicity not tested here; Gaussian HMM < Student-t HMM < HSMM). Guarded runner: ran each era once on stubs, second run blocked.
- Not covered: a data backend (fitted models, splices, QLIKE series) does not exist yet; it needs its own dated amendment before any run on data.

Files: `section5/results/a9_dry_run_synthetic.json`, `section5/s5_dry_run.py`, `section5/s5_run.py`.
