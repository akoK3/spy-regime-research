# Section 5 pilot report 2

**Status: diagnosis and fix tests on the pilot fold (RAW fold 3). No selection run. No evaluation-period data. The fold's test segment is not used in this report.**

Written 2026-11-01T02:31:58.269481+00:00 UTC. Follows `PILOT_REPORT.md`. Protocol `SECTION5_PROTOCOL.md` sha256 `8abd20f3557dac0991e30ea8c2807aee35be9d7de1c79b199d7f371397c97479` (unchanged).

## Setup

- Data: validation sessions of RAW fold 3 (58 sessions, TRAIN partition). 100 break and 100 null splices built from them (fast path, 4 worker processes). Models fitted on the inner-train segment only (189 sessions), K=3, lambda=39, 1 start, seed 0.
- Feature sets (a priori, not selected): base = 5-min return; f3 = + rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj; f6 = f3 + downside5_strict__sadj, momentum15_endpoint, close_location_proxy.
- Threshold rule as in 5.6: smallest grid threshold with at most 1 false alarm per 20 null sessions (null false-alarm rate <= 0.05 on the same null splices). Hit = confirmed (T_c) within 60 min of tau. 'Chance' = rate of a confirmed event in [tau, tau+60 min] of a NULL splice at the same threshold.
- Break splices: post/pre variance ratio quantiles (10/25/50/75/90%) 0.07, 0.13, 0.77, 3.18, 5.29 (half are stressed-to-calm).
- Fast splice path (features of the spliced session computed alone; relative_volume20 and __sadj baselines from A's 20 previous sessions) equals the 21-session recomputation on 6 real splices (rtol 1e-9, all equal): 4.16 s vs 0.23 s per splice.

## 1. Diagnosis: null-splice false alarms (raw 5-min return, as piloted)

Share of the 100 null sessions with at least one confirmed event, and confirmed events by clock hour of T_d availability; 'pre/post' = T_d at or before / after the seam bar g.

### Threshold 0.9

| model | set | sessions with FA | events | 09:30-10:00 | 10:00-11:00 | 11:00-12:00 | 12:00-13:00 | 13:00-14:00 | 14:00-15:00 | 15:00-16:00 | pre | post |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | 0.72 | 73 | 0 | 9 | 17 | 15 | 13 | 10 | 9 | 40 | 33 |
| gaussian_hmm | f3 | 0.58 | 69 | 2 | 12 | 11 | 7 | 7 | 16 | 14 | 24 | 45 |
| gaussian_hmm | f6 | 0.54 | 87 | 0 | 17 | 12 | 15 | 14 | 19 | 10 | 38 | 49 |
| student_t_hmm | base | 0.64 | 65 | 0 | 5 | 20 | 13 | 11 | 8 | 8 | 37 | 28 |
| student_t_hmm | f3 | 0.49 | 58 | 2 | 7 | 12 | 5 | 4 | 13 | 15 | 25 | 33 |
| student_t_hmm | f6 | 0.54 | 72 | 0 | 14 | 11 | 17 | 8 | 10 | 12 | 38 | 34 |
| hsmm | base | 0.54 | 54 | 0 | 2 | 6 | 19 | 9 | 4 | 14 | 27 | 27 |
| hsmm | f3 | 0.55 | 63 | 3 | 11 | 14 | 6 | 6 | 9 | 14 | 27 | 36 |
| hsmm | f6 | 0.56 | 87 | 0 | 17 | 13 | 12 | 13 | 17 | 15 | 39 | 48 |
| bocpd | base | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bocpd | f3 | 0.52 | 62 | 0 | 10 | 10 | 11 | 13 | 4 | 14 | 27 | 35 |
| bocpd | f6 | 0.71 | 107 | 0 | 16 | 17 | 22 | 23 | 14 | 15 | 50 | 57 |

### Threshold 0.99

| model | set | sessions with FA | events | 09:30-10:00 | 10:00-11:00 | 11:00-12:00 | 12:00-13:00 | 13:00-14:00 | 14:00-15:00 | 15:00-16:00 | pre | post |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| gaussian_hmm | f3 | 0.18 | 19 | 2 | 1 | 2 | 6 | 3 | 3 | 2 | 9 | 10 |
| gaussian_hmm | f6 | 0.27 | 33 | 0 | 2 | 10 | 7 | 5 | 4 | 5 | 19 | 14 |
| student_t_hmm | base | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| student_t_hmm | f3 | 0.16 | 17 | 0 | 0 | 2 | 7 | 3 | 4 | 1 | 7 | 10 |
| student_t_hmm | f6 | 0.25 | 30 | 0 | 2 | 8 | 7 | 4 | 4 | 5 | 16 | 14 |
| hsmm | base | 0.10 | 10 | 0 | 0 | 0 | 1 | 8 | 1 | 0 | 4 | 6 |
| hsmm | f3 | 0.25 | 27 | 0 | 8 | 4 | 4 | 5 | 3 | 3 | 14 | 13 |
| hsmm | f6 | 0.29 | 35 | 0 | 2 | 10 | 8 | 5 | 4 | 6 | 20 | 15 |
| bocpd | base | 0.00 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| bocpd | f3 | 0.18 | 18 | 0 | 4 | 6 | 0 | 6 | 1 | 1 | 12 | 6 |
| bocpd | f6 | 0.45 | 57 | 0 | 7 | 13 | 9 | 8 | 5 | 15 | 27 | 30 |

### By feature: null false-alarm rate with the 5-min return + ONE feature (raw return, K=3 / lambda=39)

| feature | gaussian_hmm @0.9 / @0.99 | student_t_hmm @0.9 / @0.99 | hsmm @0.9 / @0.99 | bocpd @0.9 / @0.99 |
|---|---|---|---|---|
| abs_return_1m | 0.35 / 0.02 | 0.23 / 0.03 | 0.34 / 0.09 | 0.26 / 0.06 |
| abs_return_1m__sadj | 0.45 / 0.03 | 0.54 / 0.08 | 0.23 / 0.02 | 0.23 / 0.04 |
| close_location_proxy | 0.51 / 0.30 | 0.51 / 0.16 | 0.52 / 0.29 | 0.00 / 0.00 |
| downside10_strict | 0.80 / 0.25 | 0.79 / 0.27 | 0.80 / 0.28 | 0.32 / 0.09 |
| downside10_strict__sadj | 0.69 / 0.12 | 0.70 / 0.20 | 0.66 / 0.30 | 0.33 / 0.10 |
| downside5_strict | 0.36 / 0.07 | 0.13 / 0.07 | 0.47 / 0.12 | 0.28 / 0.10 |
| downside5_strict__sadj | 0.19 / 0.08 | 0.17 / 0.07 | 0.39 / 0.16 | 0.33 / 0.06 |
| intrabar_range_log | 0.68 / 0.04 | 0.69 / 0.04 | 0.60 / 0.23 | 0.30 / 0.10 |
| intrabar_range_log__sadj | 0.50 / 0.04 | 0.55 / 0.05 | 0.45 / 0.11 | 0.29 / 0.07 |
| momentum10_endpoint | 0.77 / 0.24 | 0.75 / 0.14 | 0.76 / 0.40 | 0.19 / 0.03 |
| momentum15_endpoint | 0.88 / 0.37 | 0.82 / 0.29 | 0.75 / 0.54 | 0.21 / 0.01 |
| momentum30_endpoint | 0.94 / 0.62 | 0.97 / 0.60 | 0.92 / 0.73 | 0.13 / 0.00 |
| momentum5_endpoint | 0.64 / 0.15 | 0.51 / 0.07 | 0.64 / 0.24 | 0.31 / 0.03 |
| relative_volume20 | 0.69 / 0.02 | 0.72 / 0.03 | 0.61 / 0.06 | 0.01 / 0.00 |
| return_1m | 0.67 / 0.02 | 0.63 / 0.02 | 0.53 / 0.27 | 0.06 / 0.00 |
| rv10_partial90 | 0.82 / 0.36 | 0.84 / 0.31 | 0.82 / 0.34 | 0.12 / 0.00 |
| rv10_partial90__sadj | 0.78 / 0.31 | 0.75 / 0.29 | 0.69 / 0.37 | 0.18 / 0.00 |
| rv5_strict | 0.57 / 0.12 | 0.64 / 0.07 | 0.46 / 0.15 | 0.13 / 0.00 |
| rv5_strict__sadj | 0.53 / 0.13 | 0.55 / 0.19 | 0.62 / 0.31 | 0.11 / 0.00 |

Findings:
- False alarms are spread over all clock hours (no concentration at the open, lunch or close) and split roughly evenly between before and after the seam. They are not seam artefacts and not a time-of-day seasonality effect.
- The return-only models have 0 false alarms at 0.99 (HSMM 0.10); every added feature raises them. At 0.99 the mean null false-alarm rate over single-feature models is gaussian_hmm 0.17, student_t_hmm 0.16, hsmm 0.26, bocpd 0.04.
- f6 is worse than f3 for all four families (null false-alarm rate at 0.99: 0.25-0.45 vs 0.16-0.25).

## 2-3. Fix tests

Configurations: piloted = raw return, grid <= 0.99; (b) = grid extended by 0.995, 0.999, 0.9995, 0.9999; (a) = 5-min return divided by the median |return| of the same grid slot over the previous 20 sessions (>= 10 finite; causal; spliced sessions use A's history); (d) = BOCPD persistence: at the would-be T_c, P(run length <= 5) >= threshold; (c) = miss rule, delay censored at 60 min (a metric rule: median over all breaks with misses = 60).

| model | set | configuration | threshold | null FA | hit rate | chance (null window) | median delay of hits (min) | median delay, misses = 60 (min) |
|---|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | piloted (raw, grid<=0.99) | 0.99 | 0.00 | 0.00 | 0.00 | - | 60 |
| gaussian_hmm | base | b: extended grid | 0.99 | 0.00 | 0.00 | 0.00 | - | 60 |
| gaussian_hmm | base | a: deseasonalised return | 0.9 | 0.04 | 0.05 | 0.01 | 45 | 60 |
| gaussian_hmm | base | a+b | 0.9 | 0.04 | 0.05 | 0.01 | 45 | 60 |
| gaussian_hmm | f3 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| gaussian_hmm | f3 | b: extended grid | 0.999 | 0.04 | 0.09 | 0.00 | 30 | 60 |
| gaussian_hmm | f3 | a: deseasonalised return | none feasible | - | - | - | - | - |
| gaussian_hmm | f3 | a+b | 0.9995 | 0.04 | 0.10 | 0.00 | 27.5 | 60 |
| gaussian_hmm | f6 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| gaussian_hmm | f6 | b: extended grid | none feasible | - | - | - | - | - |
| gaussian_hmm | f6 | a: deseasonalised return | none feasible | - | - | - | - | - |
| gaussian_hmm | f6 | a+b | none feasible | - | - | - | - | - |
| student_t_hmm | base | piloted (raw, grid<=0.99) | 0.99 | 0.00 | 0.00 | 0.00 | - | 60 |
| student_t_hmm | base | b: extended grid | 0.99 | 0.00 | 0.00 | 0.00 | - | 60 |
| student_t_hmm | base | a: deseasonalised return | 0.99 | 0.02 | 0.00 | 0.01 | - | 60 |
| student_t_hmm | base | a+b | 0.99 | 0.02 | 0.00 | 0.01 | - | 60 |
| student_t_hmm | f3 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| student_t_hmm | f3 | b: extended grid | 0.999 | 0.01 | 0.05 | 0.01 | 45 | 60 |
| student_t_hmm | f3 | a: deseasonalised return | none feasible | - | - | - | - | - |
| student_t_hmm | f3 | a+b | 0.999 | 0.03 | 0.07 | 0.01 | 25 | 60 |
| student_t_hmm | f6 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| student_t_hmm | f6 | b: extended grid | 0.9999 | 0.05 | 0.04 | 0.01 | 32.5 | 60 |
| student_t_hmm | f6 | a: deseasonalised return | none feasible | - | - | - | - | - |
| student_t_hmm | f6 | a+b | none feasible | - | - | - | - | - |
| hsmm | base | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| hsmm | base | b: extended grid | 0.995 | 0.00 | 0.00 | 0.00 | - | 60 |
| hsmm | base | a: deseasonalised return | 0.95 | 0.05 | 0.04 | 0.02 | 40 | 60 |
| hsmm | base | a+b | 0.95 | 0.05 | 0.04 | 0.02 | 40 | 60 |
| hsmm | f3 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| hsmm | f3 | b: extended grid | 0.9999 | 0.05 | 0.07 | 0.00 | 45 | 60 |
| hsmm | f3 | a: deseasonalised return | none feasible | - | - | - | - | - |
| hsmm | f3 | a+b | 0.9999 | 0.05 | 0.07 | 0.00 | 35 | 60 |
| hsmm | f6 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| hsmm | f6 | b: extended grid | none feasible | - | - | - | - | - |
| hsmm | f6 | a: deseasonalised return | none feasible | - | - | - | - | - |
| hsmm | f6 | a+b | none feasible | - | - | - | - | - |
| bocpd | base | piloted (raw, grid<=0.99) | 0.7 | 0.04 | 0.05 | 0.02 | 30 | 60 |
| bocpd | base | b: extended grid | 0.7 | 0.04 | 0.05 | 0.02 | 30 | 60 |
| bocpd | base | a: deseasonalised return | 0.85 | 0.03 | 0.04 | 0.00 | 20 | 60 |
| bocpd | base | a+b | 0.85 | 0.03 | 0.04 | 0.00 | 20 | 60 |
| bocpd | base | b+d: persistence | 0.55 | 0.04 | 0.07 | 0.07 | 20 | 60 |
| bocpd | base | a+b+d | 0.7 | 0.05 | 0.06 | 0.03 | 22.5 | 60 |
| bocpd | base | d only (grid<=0.99) | 0.55 | 0.04 | 0.07 | 0.07 | 20 | 60 |
| bocpd | f3 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| bocpd | f3 | b: extended grid | 0.999 | 0.05 | 0.08 | 0.01 | 20 | 60 |
| bocpd | f3 | a: deseasonalised return | none feasible | - | - | - | - | - |
| bocpd | f3 | a+b | 0.999 | 0.05 | 0.08 | 0.01 | 20 | 60 |
| bocpd | f3 | b+d: persistence | 0.999 | 0.04 | 0.06 | 0.01 | 20 | 60 |
| bocpd | f3 | a+b+d | 0.995 | 0.05 | 0.11 | 0.02 | 20 | 60 |
| bocpd | f3 | d only (grid<=0.99) | none feasible | - | - | - | - | - |
| bocpd | f6 | piloted (raw, grid<=0.99) | none feasible | - | - | - | - | - |
| bocpd | f6 | b: extended grid | none feasible | - | - | - | - | - |
| bocpd | f6 | a: deseasonalised return | none feasible | - | - | - | - | - |
| bocpd | f6 | a+b | none feasible | - | - | - | - | - |
| bocpd | f6 | b+d: persistence | none feasible | - | - | - | - | - |
| bocpd | f6 | a+b+d | none feasible | - | - | - | - | - |
| bocpd | f6 | d only (grid<=0.99) | none feasible | - | - | - | - | - |

Feasibility (number of the 12 model x set cells with a threshold meeting the false-alarm target): piloted 3, (b) 9, (a) 4, (a)+(b) 8.

Findings:
- (b) extended grid: makes f3 feasible for all four families (thresholds 0.999 to 0.9999). f6 stays infeasible for the Gaussian HMM, HSMM and BOCPD in every configuration and for the Student-t HMM except raw at 0.9999 (null FA 0.05).
- (a) deseasonalised return: makes the return-only Gaussian HMM, HSMM and BOCPD feasible at lower thresholds (Gaussian 0.99 to 0.90, HSMM none to 0.95, BOCPD 0.70 to 0.85) with hit rates 0.04-0.05. For f3 it does not help without (b).
- (d) persistence: BOCPD return-only threshold falls from 0.70 to 0.55 (hit 0.05 to 0.07); BOCPD f3 with (a)+(b)+(d) reaches hit 0.11 at 0.995. Effect is small.
- Hit rates are not reasonable under any configuration: the highest feasible hit rate is 0.11 (bocpd|f3|a+b+d). At the false-alarm target 20 of 29 feasible cells have a hit rate above the chance rate, and hit rates are 0.00-0.11 (0.04-0.11 where hit > 0).
- Away from the target the detectors carry signal (Gaussian HMM f3, deseasonalised, threshold 0.99: hit 0.22 vs chance 0.04, but null false-alarm 0.15, above target).
- (c) miss rule: with hit rates below 50% the censored median delay equals 60 min in every cell, so it carries no information; hit rate (and delay among hits) is the usable summary until hit rates exceed 50%.
- Unconstrained detection (threshold 0.5 sweeps in `fixes_results.json`, key `sweep`) reaches hit 0.20-0.78 with null false-alarm 0.26-0.86 in the cells inspected (Gaussian base/f3, HSMM base, BOCPD base/f3): the trade-off between the false-alarm target and hit rate is steep for the 3-update hold on a 5-min grid.
- Not tested (listed for the decision on A6): shorter hold, a looser false-alarm target, a longer hit window, regime-specific (direction-specific) thresholds, hit rate split by direction.

## 4. Parallelization and re-projected budget

- Machine: 16 logical cores, about 2.3 GB free RAM at the time; each worker process holds about 250 MB, so 4 workers were used (6 is the practical ceiling).
- Splice features, 64 splices: 1 worker 16.6 s, 4 workers 8.8 s (speedup 1.9x including process start and data load in each worker).
- Model fits, 16 HSMM fits including setup: 1 worker 25.7 s, 4 workers 12.9 s (speedup 2.0x including the same per-worker setup).
- 200 + 200 splices (fixes run) with 4 workers: 18-19 s wall.
- Splice feature recomputation per fold: slow path 3328 s (800 splices x 4.16 s); fast path 183 s serial.

Per fold (800 splices + selection and tuning for the 4 families, serial 412 s from PILOT_REPORT.md; BOCPD D=7 extrapolated). Folds are independent, so parallelism is across folds; the measured end-to-end speedups above include setup, a long run amortizes setup. Two efficiency assumptions: measured (2.0x at 4 workers) and amortized (0.85 per worker).

| Setting | Seconds per fold | 34 folds (h) | 17 folds (h) |
|---|---|---|---|
| serial, slow splice path (PILOT_REPORT.md) | 3740 | 35.3 | 17.7 |
| serial, fast splice path | 595 | 5.6 | 2.8 |
| 4 workers, measured speedup 2.0x | 298 | 2.8 | 1.4 |
| 4 workers, amortized 0.85 efficiency | 175 | 1.7 | 0.8 |
| 6 workers, amortized 0.85 efficiency | 117 | 1.1 | 0.6 |

- Selection and tuning (412 s of the serial 595 s) is now the dominant cost: BOCPD 233 s and HSMM 128 s per fold.
- Sensitivity set (80 columns, RAW only, 4 folds): selection x4.2, i.e. about 29 min serial per fold.
- Not included: 1-/15-min grids, 3 seeds, +/-0.05 threshold runs, LEGACY delay runs, H2 placebo (10,000 draws), power simulations, 5.13 refits.

## 5. 80 vs 83

- Matrix v2 keeps 83 sensitivity columns; 5.2 drops `jump_variation__sadj` (three columns: jump_variation_15/30/60__sadj), so the set that reaches models is 80. `assert_pool` and the unit tests already enforce 80 (and 83 for the matrix itself); no code uses 83 as a model pool.
- The protocol file is not edited (changes only by dated, hashed amendment); the correction is item 1 of `AMENDMENT_A6_DRAFT.md`.

## Choices made without asking (user away)

- Diagnosis and fix tests use validation splices only (100 + 100). The fold's test segment was not scored, to keep it unused for choosing fixes.
- Threshold calibration and hit rate use the same 100 + 100 splices (hit rate is not used to choose the threshold).
- 'Reasonable' hit rate: above 50% at the false-alarm target (my criterion; the protocol has none). No configuration meets it.
- Deseasonalization: scale = median |ret5| per grid slot over the previous 20 sessions, >= 10 finite, NaN if <= 0 (a missing scale is a skipped update); applied to the return column only; the preprocessing (log/winsorize/z-score) is refit on the deseasonalized column.
- Persistence statistic: P(run length <= 5) = hold + 2 at the would-be T_c, same threshold as the alarm. The choice of 5 was not tuned.
- Extended grid values 0.995, 0.999, 0.9995, 0.9999 chosen by me; the 0.9999 cell is printed as 1.0 in some outputs (rounded).
- Process pool of 4 workers (memory-limited); the first benchmark attempt was re-run with 1 and 4 workers only. The earlier session's benchmark did not finish; cause not established beyond memory and spawn overhead.
- A6 is drafted as a file only; nothing in the pipeline or protocol was changed to apply it, except the BOCPD persistence statistic and the extended-grid option, which were added as off-by-default code paths.

## Files

| File | SHA-256 |
|---|---|
| section5/s5_fast.py | `8db9cf0f6511145ecc9924f66c01e6f297e1295b74dee8732b9ed43c5d2b979b` |
| section5/s5_fixes.py | `a807144ffee222cc4d51e5a998cbc6370c87da037b90a77a5003a3893cbc6d69` |
| section5/s5_bench.py | `22699eb75ff4fba2a58477b41a281d1ac044a4610882de9da38198d81027a15b` |
| section5/s5_eval.py | `c48799bfea17ac22811e301137d981c9eb7f0dba9810b3f2a60ef065254f3ae7` |
| section5/s5_events.py | `6f294d55207bcf9293831be9090809a127e35cf00fb73dd69f3fad17b4fa5cdf` |
| section5/s5_models.py | `ad86b3e40fa112e65eeb63452022d6d0ea06a324c9a06dabef30c1be87ba1f98` |
| section5/write_pilot_report_2.py | `2074566883c7b6aba72b4272d68baebf9ce259121c81dd8ddb8cf64ff45e3e84` |
| section5/results/fixes_results.json | `12be1d17264be9d9bf3460ddf26c5a9ce899494a6ec078325b3580ce4c60dc2a` |
| section5/results/bench_results.json | `de2bb237668927a9e248b3eea8a7899f72eefcc36c5511a6783db0bc36aa04da` |
| AMENDMENT_A6_DRAFT.md | see its sidecar `AMENDMENT_A6_DRAFT.sha256` |
