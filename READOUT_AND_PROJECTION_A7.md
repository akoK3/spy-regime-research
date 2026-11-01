# Hit-rate readout check, vectorised sweep, projected run time

Written 2026-11-01T18:25:23.888150+00:00 UTC. RAW fold 3, validation/test machinery data only; no selection, no evaluation-period data.

## 1. hit(alarm rate 0.2) versus hit(alarm rate 0.1)

- Result: **no violation exists.** In `a6_pilot_results.json` and `a7_pilot_results.json` every detector and every variance ratio (48 A7 readouts, all A6 readouts) has hit at 0.2 >= hit at 0.1; the re-computed readout also has none (`hit0p2_below_hit0p1` empty).
- Why it cannot occur: the readout is `y_at(points, x0)` = the highest hit rate among sweep points whose null alarm rate is <= x0 (a running maximum), so it is non-decreasing in x0 by construction. The partial-area metric uses the same step function.
- Guard added: `test_hit_rate_is_nondecreasing_in_alarm_rate` in `s5_tests.py` checks the property on 300 random point sets and on every stored A6/A7 readout (31 unit tests, 0 failures, 0 errors in the last run).
- Re-run of the readout only (same data, models, splices and seeds as the A7 pilot, vectorised sweep): maximum absolute difference to the stored loop-based values over partial area and both hit readouts = **0.0**; the D4 run-2 thresholds equal the stored ones for 8 of 8 detectors. Curves are stored in `a7_readout_vectorised.json` so later readouts need no recomputation.

## 2. Vectorised threshold sweep

`s5_sweep.py` evaluates the alarm state machines (log-odds old-state rule, run-length-drop rule) for all thresholds and all sessions at once; only the loop over updates remains. Equality with the loop implementations (alarm counts and hit flags per session and threshold, with skips, K = 2 and 3) is asserted in `TestSweep.test_vectorised_equals_loops`.

| | Loop (A7 pilot) | Vectorised |
|---|---|---|
| H1(a) sweep, 8 detectors, 1,360 test + 344 calibration splices | 619 s | 22.6 s |
| speedup | | 27x |

Per detector (s): gaussian_hmm|base 1.66, gaussian_hmm|f3 1.65, student_t_hmm|base 1.65, student_t_hmm|f3 1.67, hsmm|base 1.84, hsmm|f3 1.85, bocpd|base 2.75, bocpd|f3 9.52. The A7 pilot would take about 3.3 min instead of 13.22 min (projected from the stage times; not re-run end to end).

## 3. Projected run time, 34 folds (30 LEGACY + 4 RAW) with selection

Per-fold components (measured unless marked): splice features 1704 splices x 0.229 s = 390 s CPU (the A7 pilot built them in 119 s wall on 4 workers: speedup 3.3x, efficiency 0.82); vectorised sweep + run-2 + curves 23 s; Section 6 bisection 5 s; fits of the 8 final models 7 s; prep/other allowance 5 s (estimate). Selection (5.8: greedy forward to 6 of the 19 primary columns, then K tuning with 3 starts; serial seconds per fold from the PILOT_REPORT.md timings, BOCPD D = 7 extrapolated): Gaussian HMM 21, Student-t HMM 30, HSMM 128 (estimates from measured fit times), BOCPD 233.

| Case | CPU s per fold | 34 folds CPU h | 34 folds wall h, 4 workers (speedup 3.3x as measured for splices) | 34 folds wall h, 3 workers (2.5x) |
|---|---|---|---|---|
| H1 families only (3 HMM/HSMM), BOCPD scored with the HMM-selected features | 608 | 5.7 | 1.8 | 2.3 |
| 3 families + BOCPD with its own selection | 841 | 7.9 | 2.4 | 3.2 |

Add-ons (CPU hours; estimates unless stated):

- RAW sensitivity set (80 columns, 4 RAW folds): selection x4.2 (candidate count 80/19) plus a new set of splice features: 1.3 h (3 families) or 2.4 h (with BOCPD selection).
- 3 seeds: two further fits and sweeps of the final models per fold, splices reused: about 2 x 35 s per fold = 0.6 h over 34 folds.
- Threshold +/-0.05 and LEGACY +5/+10 minute delay: re-use the stored curves and filters for the sweeps (minutes in total); delay re-runs repeat the sweep, about 25 s per fold per variant.
- 1-min and 15-min grids on the final setups: not implemented for features in this pipeline, so not measured. From D5 (synthetic): HMM filtering is cheap on both grids, HSMM filtering at 1 min is about 66x slower per session, sweeps run 5x more updates; my estimate is 3-5 min CPU per fold for the 1-min grid, i.e. 1.7-2.8 h over 34 folds, and a few minutes in total for 15 min.
- One-time: LEGACY feature columns for the 19 primary columns on the full LEGACY panel (1.56 million rows) and the 20-session baselines: not measured in this session (the Section 4 LEGACY feature passes were memory-heavy: two runs were killed for low memory); slow-path splice recomputation is not needed (fast path equals it, rtol 1e-9).
- Not included: H2 placebo (10,000 draws per detector, asset and horizon), power simulations, 5.13 refits, evaluation-period runs.

Memory: each worker holds the era panel and features (about 250 MB for RAW; the LEGACY panel is 5.7x larger by rows); with about 2 GB free the practical ceiling observed here is 4 RAW workers, and fewer for LEGACY.

## Files

| File | SHA-256 |
|---|---|
| section5/s5_sweep.py | `dfb7fe2264df396d68c2c797f929aeeab6aeea910063cfc635c8e4d6f22f9b00` |
| section5/s5_a7_sweep.py | `b18f895f0eae8ee8f57055df81a70e37a08aa80dcd8d5e72d0652020fd8c1a0a` |
| section5/s5_tests.py | `2544c7e4a2c098dd28ad2c522eef82e72075b2d28839ff0fbae4a26f27610ed2` |
| section5/write_projection.py | `029aa75d557f8f88a8ab5f03bd71496340a688d3a89903ba4b43c2e010564e3b` |
| section5/results/a7_readout_vectorised.json | `cfad5b1128195a51bbd95c8247e2ff706ab56cbdc1f4757dbe686851aa67ce7f` |
| section5/results/a7_pilot_results.json | `cd9c1a54ba4bfb0f892723ed286482909daf60ad498928ee10137b8307bb176c` |
