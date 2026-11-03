# A8.2 gate report (day-level bootstrap)

Written 2026-11-03T01:42:38.244184+00:00 UTC. Rule: `AMENDMENT_A8_2.md` (sha256 `c85e40ba4484d648e44a2eda9f4900f29ffbf0bff0751b38c2f878455e96c157`). Seed 777, validation sessions only.

**Result: gate FAILED. LEGACY 29: 5 of 8 detectors inside; RAW 3: 8 of 8.** Stopped per the A8.2 rule; contamination list and event list not run; nothing else changed.

| Fold | Stable val days | Detector | pAUC P1 | pAUC P2 | P2 day-level 95% CI | Inside |
|---|---|---|---|---|---|---|
| LEGACY 29 | 7 | gaussian_hmm|base | 0.052 | 0.020 | [0.006, 0.040] | False |
| LEGACY 29 | 7 | gaussian_hmm|f3 | 0.035 | 0.015 | [0.006, 0.027] | False |
| LEGACY 29 | 7 | student_t_hmm|base | 0.010 | 0.029 | [0.008, 0.058] | True |
| LEGACY 29 | 7 | student_t_hmm|f3 | 0.089 | 0.057 | [0.010, 0.159] | True |
| LEGACY 29 | 7 | hsmm|base | 0.020 | 0.019 | [0.000, 0.061] | True |
| LEGACY 29 | 7 | hsmm|f3 | 0.016 | 0.003 | [0.000, 0.007] | False |
| LEGACY 29 | 7 | bocpd|base | 0.030 | 0.020 | [0.000, 0.053] | True |
| LEGACY 29 | 7 | bocpd|f3 | 0.013 | 0.017 | [0.000, 0.043] | True |
| RAW 3 | 16 | gaussian_hmm|base | 0.045 | 0.059 | [0.008, 0.120] | True |
| RAW 3 | 16 | gaussian_hmm|f3 | 0.018 | 0.033 | [0.010, 0.062] | True |
| RAW 3 | 16 | student_t_hmm|base | 0.030 | 0.030 | [0.010, 0.064] | True |
| RAW 3 | 16 | student_t_hmm|f3 | 0.021 | 0.022 | [0.008, 0.040] | True |
| RAW 3 | 16 | hsmm|base | 0.027 | 0.030 | [0.004, 0.076] | True |
| RAW 3 | 16 | hsmm|f3 | 0.015 | 0.026 | [0.009, 0.057] | True |
| RAW 3 | 16 | bocpd|base | 0.028 | 0.027 | [0.010, 0.048] | True |
| RAW 3 | 16 | bocpd|f3 | 0.020 | 0.026 | [0.011, 0.044] | True |

Outside on LEGACY 29: gaussian_hmm|base, gaussian_hmm|f3, hsmm|f3 (P1 above P2 in each).
Files: `section5/results/a8_2_gate_LEGACY29_seed777.json`, `a8_2_gate_RAW3_seed777.json`, `a8_2_gate_log.txt`.
