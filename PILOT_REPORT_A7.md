# Machinery pilot under Amendment A7

Written 2026-11-01T18:12:24.266098+00:00 UTC. Governed by `AMENDMENT_A7.md` (sha256 `e64c8647fd3fac01ff2a64de71f25c53e6b9c8814271df9e66b3ab01835d8267`), committed before this run; A7 widens the threshold range only (continuous thresholds, bisection to the fixed 0.2 alarms/session target, same range for the H1(a) sweep). Same design as the A6 pilot: RAW fold 3, fixed a-priori feature sets, K = 3, lambda = 39, no selection, no evaluation-period data, no protocol change from these results. Machinery outputs, not evidence.

## Results

- Checks: 17 of 17 PASS (exclusions 12, causal timing 5). Unit tests: 29 run, 0 failures, 0 errors. The embargo-spacing check of the A6 pilot is not in this script's list (the embargo is enforced by an assertion inside `fold_segments`, which ran).
- Stable days: 16 validation, 18 test (H1(a) evaluable: True).

### Section 6 thresholds by bisection (target 0.2 confirmed alarms per session on the real validation sessions; HMM/HSMM theta in log-odds, BOCPD drop size m)

| detector | A7 threshold | probability equivalent | validation rate | test rate realized | rate evaluations | A6 grid threshold | A6 validation / test |
|---|---|---|---|---|---|---|---|
| gaussian_hmm|base | 3.564 (ok) | 0.972458888517 | 0.190 | 0.129 | 18 | 0.99 | 0.138 / 0.071 |
| gaussian_hmm|f3 | 11.49 (ok) | 0.999989794920 | 0.190 | 0.271 | 18 | 0.9999 FLAG | 0.259 / 0.300 |
| student_t_hmm|base | 4.306 (ok) | 0.986688487314 | 0.190 | 0.171 | 18 | 0.99 | 0.172 / 0.129 |
| student_t_hmm|f3 | 8.148 (ok) | 0.999710826174 | 0.190 | 0.300 | 18 | 0.9999 | 0.155 / 0.271 |
| hsmm|base | 4.163 (ok) | 0.984676157014 | 0.190 | 0.129 | 18 | 0.99 | 0.172 / 0.100 |
| hsmm|f3 | 12.55 (ok) | 0.999996448787 | 0.190 | 0.214 | 18 | 0.9999 FLAG | 0.276 / 0.271 |
| bocpd|base | 47.29 (ok) | - | 0.190 | 0.229 | 11 | 30 FLAG | 0.466 / 0.443 |
| bocpd|f3 | 44.2 (ok) | - | 0.190 | 0.314 | 11 | 30 FLAG | 0.603 / 0.529 |

### H1(a) machinery: partial area (null alarm rate 0-0.5, range 0-1) on the 18 test stable days; sweep theta 0-30 step 0.25 (121 values), m 1-80 step 1 (80 values)

| detector | pAUC all (A6) | R=1.5 | R=2 | R=3 | R=5 | R=10 | hit at alarm rate 0.1 | hit at 0.2 | smallest null alarm rate in sweep | sweep points with rate <= 0.5 | run-2 value |
|---|---|---|---|---|---|---|---|---|---|---|---|
| gaussian_hmm|base | 0.099 (0.083) | 0.006 | 0.054 | 0.055 | 0.141 | 0.240 | 0.07 | 0.10 | 0.000 | 113 | 4.75 |
| gaussian_hmm|f3 | 0.161 (0.058) | 0.059 | 0.077 | 0.112 | 0.228 | 0.341 | 0.11 | 0.15 | 0.050 | 94 | 19.5 |
| student_t_hmm|base | 0.094 (0.069) | 0.033 | 0.055 | 0.062 | 0.117 | 0.208 | 0.05 | 0.08 | 0.000 | 108 | 6.0 |
| student_t_hmm|f3 | 0.153 (0.085) | 0.053 | 0.076 | 0.111 | 0.222 | 0.312 | 0.07 | 0.11 | 0.000 | 99 | 9.75 |
| hsmm|base | 0.102 (0.091) | 0.020 | 0.053 | 0.049 | 0.135 | 0.257 | 0.08 | 0.10 | 0.000 | 112 | 8.25 |
| hsmm|f3 | 0.217 (0.118) | 0.064 | 0.096 | 0.155 | 0.317 | 0.455 | 0.11 | 0.15 | 0.000 | 101 | 22.25 |
| bocpd|base | 0.086 (0.061) | 0.023 | 0.057 | 0.069 | 0.103 | 0.180 | 0.00 | 0.06 | 0.000 | 77 | 48.0 |
| bocpd|f3 | 0.040 (0.000) | 0.023 | 0.035 | 0.038 | 0.047 | 0.059 | 0.00 | 0.01 | 0.000 | 46 | 49.0 |

Partial-area difference f3 minus base (machinery output, not interpreted): gaussian_hmm +0.063 (A6 -0.025), student_t_hmm +0.058 (A6 +0.016), hsmm +0.115 (A6 +0.027), bocpd -0.046 (A6 -0.061).

## Failures and findings (nothing excluded, nothing changed)

1. The A6 failures are resolved mechanically: all 8 bisections end at a validation rate of 0.19 (<= 0.2, none flagged); the H1(a) sweep now has 46-113 points with null alarm rate <= 0.5 for every detector (A6: the f3 models started above 0.1); the D4 run-2 rule is feasible for all 8 detectors (A6: 5 infeasible).
2. Realized test-session frequencies differ from the target: 0.13-0.17 (base HMM/HSMM), 0.21-0.30 (f3 models), 0.23 (BOCPD base), 0.31 (BOCPD f3); the 3-feature models and BOCPD exceed 0.2 on test by 0.01-0.11.
3. BOCPD thresholds land at drop sizes m = 47 and 44 updates: with the most likely run length at most t after t updates, a drop of 44 or more needs t >= 44, i.e. the alarm can only fire from about 13:10 on. Break splices start at 11:05-14:30 (updates 19-60), so at the target rate the BOCPD alarm cannot detect early breaks. BOCPD partial areas are 0.086 (base) and 0.040 (f3).
4. Gaussian HMM f3 has a smallest null alarm rate of 0.050 at theta = 30 (the upper bound), so its curve does not reach rate 0; the other detectors reach 0.000 inside the range.
5. Partial areas are larger than under A6 for every detector (f3 models 0.15-0.22 against 0.06-0.12; base HMM/HSMM models 0.09-0.10 against 0.07-0.09) and rise with the variance ratio; the hit rate at alarm rate 0.1 is 0.00-0.11 and at 0.2 is 0.01-0.15.
6. Edge case found by the new unit test and fixed in the three event functions that track an 'old state' (`detect_old_state`, `detect_old_state_logodds`, `detect_states_mass`): when the first updates of a session are skipped the old state was undefined and the code raised an error; now the first real update sets the old state. Behaviour is otherwise unchanged; the A6 pilot did not hit the case.
7. The sweep stage dominates the runtime (see below): 121 thresholds x 8 detectors x 1,360 test splices in python loops.

## Runtime (one machine, 4 worker processes for splice construction)

| Stage | Seconds |
|---|---|
| load_and_features | 2.81 |
| exclusions | 0.01 |
| fit_all | 6.9 |
| causal_timing | 40.8 |
| section6_bisection | 4.59 |
| build_splices | 119.36 |
| h1a_sweep | 618.69 |
| **total** | **793 (13.22 min)** |

A6 pilot total was 3.0 min.

## Files

| File | SHA-256 |
|---|---|
| section5/s5_a7.py | `84b6f42a200b02b047cba393b5b9bb7aee953961331c5d6e92d4b2e5e671f01e` |
| section5/s5_events.py | `25b3e7c713942966f26e8ec6262ab6113ee684f2bb825eae56b094735d50665e` |
| section5/s5_a6.py | `ed1e04f17f9c47b758cc489c6d01a61046d130eac81cafde3252a03034c268f9` |
| section5/s5_tests.py | `f4915f2f821aa59d5ccf7bb756922570e386481c71b7a33b5f266554684bbb85` |
| section5/write_amendment_a7.py | `a83eb84545c0ef3652de2c99df64cd34eb21ea5a52b6bb33516cfc9206148a65` |
| section5/write_a7_pilot_report.py | `5b1963547251e77ce155c6bb13f4f9e4f398205f65c9727358eacc3f4d86ea16` |
| section5/results/a7_pilot_results.json | `cd9c1a54ba4bfb0f892723ed286482909daf60ad498928ee10137b8307bb176c` |
