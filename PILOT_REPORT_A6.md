# Machinery pilot under Amendment A6

Written 2026-11-01T17:53:49.094658+00:00 UTC. Governed by `AMENDMENT_A6.md` (sha256 `db787ec0071b5b6c0ff4048cd281bf54e95e0c60b5f25e89fb6f02d55d5744a5`), committed before this run. RAW fold 3, fixed a-priori feature sets (base = deseasonalized 5-min return; f3 = + rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj), K = 3, lambda = 39, 1 start, seed 0. No selection, no evaluation-period data, no protocol change from these results. Numbers are machinery outputs, not evidence.

## Results

- Checks: 18 of 18 PASS (exclusions 13, causal timing 5; listed below). Unit tests: 27 run, 0 failures, 0 errors.
- Stable days (D2 definition, A6 item 6b): 16 validation, 18 test; H1(a) evaluable (>= 8 test days): True.

| Check | Result |
|---|---|
| exclusions: primary pool = 19, assert_pool primary | PASS |
| exclusions: sensitivity pool = 80 (83 - 3 jump_variation__sadj) | PASS |
| exclusions: fixed sets inside the primary pool | PASS |
| exclusions: no overnight / raw_volume / log_raw_volume / raw_volume__sadj / response asset / LM flag in model inputs | PASS |
| exclusions: all sessions used are TRAIN partition, RAW era | PASS |
| exclusions: embargo: 5 sessions between segments | PASS |
| exclusions: negative control overnight_return_open | PASS |
| exclusions: negative control raw_volume | PASS |
| exclusions: negative control log_raw_volume | PASS |
| exclusions: negative control raw_volume__sadj | PASS |
| exclusions: negative control tlt_return_1m | PASS |
| exclusions: negative control lee_mykland_jump60 | PASS |
| exclusions: negative control jump_variation_15__sadj | PASS |
| causal_timing: deseason scale ignores later sessions | PASS |
| causal_timing: deseason scale = scale on truncated history | PASS |
| causal_timing: filtered output at update t independent of later updates (prefix invariance, 4 families x 2 sets) | PASS |
| causal_timing: alarm time = bar stamp + 1 min, T_c after T_d by >= hold (501 events checked) | PASS |
| causal_timing: splice integrity on real data (3 splices, 8 checks each) | PASS |

### Section 6 thresholds (A6 item 3): calibrated on real validation sessions to 0.2 confirmed alarms per session; realized on test sessions

| detector | threshold | flagged (no value <= 0.2) | validation rate | test rate realized |
|---|---|---|---|---|
| gaussian_hmm|base | 0.99 | no | 0.138 | 0.071 |
| gaussian_hmm|f3 | 0.9999 | FLAG | 0.259 | 0.300 |
| student_t_hmm|base | 0.99 | no | 0.172 | 0.129 |
| student_t_hmm|f3 | 0.9999 | no | 0.155 | 0.271 |
| hsmm|base | 0.99 | no | 0.172 | 0.100 |
| hsmm|f3 | 0.9999 | FLAG | 0.276 | 0.271 |
| bocpd|base | 30 | FLAG | 0.466 | 0.443 |
| bocpd|f3 | 30 | FLAG | 0.603 | 0.529 |

### H1(a) machinery (A6 item 2): hit rate vs null alarm rate on the 18 test stable days; partial area for alarm rate 0-0.5 (range 0-1)

Splices: 400 null; 960 breaks (5 ratios x 2 directions x 4 durations x 24). Power by ratio = partial area for the breaks of that variance ratio.

| detector | pAUC all | R=1.5 | R=2 | R=3 | R=5 | R=10 | hit at alarm rate 0.1 | null alarm rate: strictest / loosest threshold | BOCPD/threshold run-2 value |
|---|---|---|---|---|---|---|---|---|---|
| gaussian_hmm|base | 0.083 | 0.004 | 0.038 | 0.042 | 0.117 | 0.215 | 0.06 | 0.03 / 3.17 | 0.99 |
| gaussian_hmm|f3 | 0.058 | 0.017 | 0.024 | 0.040 | 0.086 | 0.123 | 0.00 | 0.38 / 3.90 | INFEASIBLE |
| student_t_hmm|base | 0.069 | 0.014 | 0.035 | 0.036 | 0.085 | 0.173 | 0.01 | 0.00 / 2.86 | 0.999 |
| student_t_hmm|f3 | 0.085 | 0.030 | 0.042 | 0.067 | 0.117 | 0.170 | 0.00 | 0.28 / 3.77 | INFEASIBLE |
| hsmm|base | 0.091 | 0.017 | 0.037 | 0.040 | 0.122 | 0.238 | 0.08 | 0.02 / 3.50 | 0.9999 |
| hsmm|f3 | 0.118 | 0.038 | 0.054 | 0.088 | 0.178 | 0.234 | 0.00 | 0.32 / 3.37 | INFEASIBLE |
| bocpd|base | 0.061 | 0.014 | 0.037 | 0.052 | 0.076 | 0.127 | 0.00 | 0.32 / 0.51 | INFEASIBLE |
| bocpd|f3 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.000 | 0.00 | 0.58 / 1.26 | INFEASIBLE |

Partial-area difference f3 minus base (machinery output, not interpreted): gaussian_hmm -0.025, student_t_hmm +0.016, hsmm +0.027, bocpd -0.061.

## Failures and findings (nothing excluded, nothing changed)

1. Section 6 thresholds miss the 0.2 per session target at the strict end of the grid for the f3 models and for BOCPD: Gaussian HMM f3 and HSMM f3 are flagged (strictest value 0.9999 still gives 0.26 and 0.28 alarms per validation session); Student-t HMM f3 reaches 0.155 on validation but 0.271 on test; BOCPD base and f3 are flagged (run-length-drop m = 30 gives 0.47 and 0.60). Realized test frequencies range 0.07-0.53 against the target 0.2.
2. H1(a) curves for the f3 models and BOCPD start at a null alarm rate above 0.1 (strictest-threshold null rates: f3 models 0.28-0.38, BOCPD f3 0.58) so the 0-0.5 window is mostly empty: hit at alarm rate 0.1 is 0.00 for all f3 models; BOCPD f3 partial area is 0.000. The base models have strictest-threshold null rates of 0.00-0.03 (BOCPD base 0.32) and score 0.06-0.09.
3. Partial areas are small throughout (all-ratio 0.00-0.12; R = 10 up to 0.24), as in D2, D4 and D5; partial area rises monotonically with the variance ratio for every detector except BOCPD f3 (all zero).
4. The D4 run-2 rule (A6 item 6a) is INFEASIBLE (no grid value with calibration null FA <= 0.10) for all three f3 HMM/HSMM models and for both BOCPD sets on validation stable-day splices; it selects 0.99 / 0.999 / 0.9999 for the three base HMM/HSMM models.
5. The strict end of the HMM threshold grid (0.9999) and of the drop grid (m = 30) is not strict enough for 3-feature models on real data; A6 does not define a wider grid (change not made).
6. Splice features, deseasonalization and filters are causal as tested (prefix invariance, truncated-history scale, alarm time = bar stamp + 1 min over 501 events); splice integrity PASS on 3 real splices.

## Runtime (one machine, 4 worker processes for splice construction)

| Stage | Seconds |
|---|---|
| load_and_features | 2.74 |
| exclusions | 0.01 |
| fit_all | 6.73 |
| causal_timing | 38.13 |
| section6_calibration | 0.95 |
| build_splices | 110.73 |
| h1a_scoring | 21.54 |
| **total** | **181 (3.02 min)** |

Fit seconds (K = 3, 1 start): gaussian_hmm|base 0.182, gaussian_hmm|f3 0.186, student_t_hmm|base 0.347, student_t_hmm|f3 0.247, hsmm|base 4.23, hsmm|f3 1.289, bocpd|base 0.0, bocpd|f3 0.0.

## Files

| File | SHA-256 |
|---|---|
| section5/s5_a6.py | `ed1e04f17f9c47b758cc489c6d01a61046d130eac81cafde3252a03034c268f9` |
| section5/s5_events.py | `9c96f71664e698747d179151a28e6e1ae2a37f7718eebf5c1dacfc565be65de1` |
| section5/s5_models.py | `8c0f9acbe0fb0a9d83e43bcf4d657518cd24114fd3ff9f2213d51c9ddbd91daf` |
| section5/s5_fast.py | `8132aabb8b66d64c0fa8d815990d33da83ba97247f9a9b65311e10654f54523c` |
| section5/s5_tests.py | `71ff78f8b06916e879880740798f8ea485616833d6002aabe5e4377ef9259a70` |
| section5/write_a6_pilot_report.py | `dc330d705228235579b14570f6631449775b04832e0d707cb4295c8784e1cc9b` |
| section5/results/a6_pilot_results.json | `6712f3988f63837d996f7ab45a45fb0ec5f1d6f54100940f60e2d0ed11ab8f98` |
