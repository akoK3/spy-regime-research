# A8.3 gate characterization (P1 vs P2, 20 new seeds)

Written 2026-11-03T03:23:14.635084+00:00 UTC. Rule: `AMENDMENT_A8_3.md` (sha256 `8867dc3e526285ce24768480bbfe200d1e37f68a2e86bbeea425dc31740d52a1`). Seeds 1001-1020; validation sessions only; no test-segment scoring.

Stable validation days: LEGACY 29 = 7, RAW 3 = 16. Seeds run: LEGACY 20, RAW 20.

| Detector | LEGACY fails | LEGACY rate [Wilson 95%] | RAW fails | RAW rate [Wilson 95%] | Floor 2x max(RAW, .05) | Within 2x | seed 777 LEGACY / RAW outside |
|---|---|---|---|---|---|---|---|
| gaussian_hmm|base | 3/20 | 0.15 [0.05, 0.36] | 1/20 | 0.05 [0.01, 0.24] | 0.10 | **NO** | True / False |
| gaussian_hmm|f3 | 1/20 | 0.05 [0.01, 0.24] | 0/20 | 0.00 [0.00, 0.16] | 0.10 | yes | True / False |
| student_t_hmm|base | 0/20 | 0.00 [0.00, 0.16] | 0/20 | 0.00 [0.00, 0.16] | 0.10 | yes | False / False |
| student_t_hmm|f3 | 0/20 | 0.00 [0.00, 0.16] | 0/20 | 0.00 [0.00, 0.16] | 0.10 | yes | False / False |
| hsmm|base | 1/20 | 0.05 [0.01, 0.24] | 0/20 | 0.00 [0.00, 0.16] | 0.10 | yes | False / False |
| hsmm|f3 | 3/20 | 0.15 [0.05, 0.36] | 0/20 | 0.00 [0.00, 0.16] | 0.10 | **NO** | True / False |
| bocpd|base | 2/20 | 0.10 [0.03, 0.30] | 1/20 | 0.05 [0.01, 0.24] | 0.10 | yes | False / False |
| bocpd|f3 | 2/20 | 0.10 [0.03, 0.30] | 3/20 | 0.15 [0.05, 0.36] | 0.30 | yes | False / False |

Pooled over the 8 detectors (information): LEGACY 0.075, RAW 0.031. Seeds with at least one detector outside: LEGACY 7/20, RAW 5/20.

## Pre-stated rule result

Detectors far higher on LEGACY (> 2x max(RAW, .05)): gaussian_hmm|base, hsmm|f3. To be investigated before any main run (separate dated step).
