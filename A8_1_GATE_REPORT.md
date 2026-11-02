# A8.1 gate report (R=1 placebo reference, construction check)

Written 2026-11-02T18:14:21.598307+00:00 UTC. Rule: `AMENDMENT_A8_1.md` (sha256 `bd7a854ed681c16b5bddadda1791fb66087aeecc63e4341e05c95da8de48fbd8`). Seed 777, validation sessions only.

**Result: gate FAILED (LEGACY 29: 3 of 8 detectors inside; RAW 3: 8 of 8).** Stopped per the A8 rule; contamination list was not run on real data.

| Fold | Stable val days | Detector | pAUC P1 | pAUC P2 | P2 95% CI | Inside |
|---|---|---|---|---|---|---|
| LEGACY 29 | 7 | gaussian_hmm|base | 0.052 | 0.020 | [0.008, 0.036] | False |
| LEGACY 29 | 7 | gaussian_hmm|f3 | 0.035 | 0.015 | [0.005, 0.027] | False |
| LEGACY 29 | 7 | student_t_hmm|base | 0.010 | 0.029 | [0.014, 0.051] | False |
| LEGACY 29 | 7 | student_t_hmm|f3 | 0.089 | 0.057 | [0.030, 0.088] | False |
| LEGACY 29 | 7 | hsmm|base | 0.020 | 0.019 | [0.007, 0.036] | True |
| LEGACY 29 | 7 | hsmm|f3 | 0.016 | 0.003 | [0.000, 0.007] | False |
| LEGACY 29 | 7 | bocpd|base | 0.030 | 0.020 | [0.005, 0.040] | True |
| LEGACY 29 | 7 | bocpd|f3 | 0.013 | 0.017 | [0.004, 0.035] | True |
| RAW 3 | 16 | gaussian_hmm|base | 0.045 | 0.059 | [0.033, 0.090] | True |
| RAW 3 | 16 | gaussian_hmm|f3 | 0.018 | 0.033 | [0.015, 0.055] | True |
| RAW 3 | 16 | student_t_hmm|base | 0.030 | 0.030 | [0.020, 0.050] | True |
| RAW 3 | 16 | student_t_hmm|f3 | 0.021 | 0.022 | [0.010, 0.041] | True |
| RAW 3 | 16 | hsmm|base | 0.027 | 0.030 | [0.016, 0.053] | True |
| RAW 3 | 16 | hsmm|f3 | 0.015 | 0.026 | [0.013, 0.045] | True |
| RAW 3 | 16 | bocpd|base | 0.028 | 0.027 | [0.013, 0.044] | True |
| RAW 3 | 16 | bocpd|f3 | 0.020 | 0.026 | [0.012, 0.044] | True |

pAUC f3 minus base (P2 / P1 / N2): LEGACY 29: gaussian_hmm -0.006, student_t_hmm +0.028, hsmm -0.015, bocpd -0.003; RAW 3: gaussian_hmm -0.026, student_t_hmm -0.008, hsmm -0.004, bocpd -0.001

Facts: P1 and P2 differ by more than the bootstrap interval on LEGACY 29 for 5 detector rows. Both placebo sets are drawn from the same 7 stable validation days there, so the bootstrap over splices does not include day-level variance (inference); with 16 days (RAW 3) all 8 pass.

Files: `section5/results/a8_1_gate_LEGACY29_seed777.json`, `a8_1_gate_RAW3_seed777.json`, `a8_1_gate_log.txt`.
