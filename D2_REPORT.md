# Diagnostic D2 report

**RAW fold 3, validation sessions only; frozen pilot detectors (K=3, lambda=39, 1 start, seed 0, raw 5-min return) with fixed a-priori feature sets; no selection; no evaluation data; the fold's test segment is not used.**

Written 2026-11-01T16:25:27.344470+00:00 UTC.

## Design

- Stable days (defined in `s5_d2_stable.py` before any detector ran): deseasonalised 1-min variance (r^2 / median r^2 of the same slot over the previous 20 sessions, >= 10 finite) with first-half / second-half ratio in [0.8, 1.25] and no hourly block mean above 2x the median block mean. 16 of 58 validation sessions qualify: [573, 575, 577, 578, 588, 593, 594, 597, 602, 604, 609, 610, 614, 617, 625, 628].
- Null: 400 splices of two distinct stable days of the same session-volatility tercile (terciles over the 16 stable days), tau drawn from the 11:05-14:30 grid. Only 16 distinct days exist, so pairs and null sessions repeat; the Wilson 95% intervals below treat the 400 null sessions as independent and are therefore too narrow.
- Breaks: stable day A until tau, then stable day B whose 1-min returns, ranges and price excursions are scaled by f so that the deseasonalised variance after tau equals R x (up) or 1/R x (down) the deseasonalised variance of A before tau (R = 1.5, 2, 3, 5, 10), volume unchanged; permanent (to the close) or a sandwich of 30 / 60 / 120 min after which A's own path continues (price-continuous at both seams); tau <= 14:00 so the 120-min sandwich fits. 24 splices per (size, direction, duration) cell = 960 breaks. Features recomputed from the spliced series (fast path, equal to the 21-session recomputation).
- Hit = confirmed (T_c) within 60 min of tau; for sandwiches it counts even if the sandwich has ended before T_c. Delay = T_c - tau, median over hits.
- Construction checks on 8 real panels (price at g unchanged, return across tau = f x B's return, deseasonalised variance ratio = target, sandwich tail continuous): all PASS.
- Natural scaling needed (f^2 quantiles 10/50/90% by cell, how far B's own variance is from the target): range of medians over cells 0.10-13.24.

- Realized deseasonalised variance ratio over the FIRST 60 min after tau (median over splices), by size and duration, up direction: R=1.5: None:1.72, 30:1.36, 60:1.5, 120:1.49; R=2: None:2.02, 30:1.91, 60:2.0, 120:1.96; R=3: None:3.4, 30:3.14, 60:3.0, 120:2.95; R=5: None:5.68, 30:5.1, 60:5.0, 120:5.63; R=10: None:10.33, 30:9.51, 60:10.0, 120:10.2. Down direction: R=1.5: None:0.69, 30:0.7, 60:0.67, 120:0.72; R=2: None:0.53, 30:0.53, 60:0.5, 120:0.53; R=3: None:0.35, 30:0.29, 60:0.33, 120:0.34; R=5: None:0.2, 30:0.23, 60:0.2, 120:0.2; R=10: None:0.1, 30:0.09, 60:0.1, 120:0.11. The target ratio is enforced over the whole post-tau segment (to the close for permanent), so the first-60-min ratio differs by duration.

## A. False alarms per 20 stable-day null sessions (95% Wilson CI), by detector and threshold

| detector | set | 0.5 | 0.7 | 0.9 | 0.95 | 0.99 | 0.999 | 0.9999 |
|---|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | 18.6 [18.0-19.0] | 15.2 [14.3-15.9] | 13.2 [12.2-14.0] | 10.2 [9.3-11.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] |
| gaussian_hmm | f3 | 18.9 [18.4-19.3] | 16.4 [15.6-17.1] | 10.4 [9.5-11.4] | 7.2 [6.3-8.2] | 5.1 [4.3-6.0] | 3.5 [2.9-4.4] | 1.5 [1.1-2.1] |
| gaussian_hmm | f6 | 14.9 [14.1-15.8] | 13.6 [12.6-14.4] | 10.2 [9.3-11.2] | 8.2 [7.3-9.2] | 5.8 [4.9-6.7] | 4.3 [3.6-5.2] | 3.0 [2.3-3.7] |
| student_t_hmm | base | 18.0 [17.3-18.5] | 13.7 [12.7-14.5] | 12.1 [11.1-13.0] | 10.9 [10.0-11.9] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] |
| student_t_hmm | f3 | 19.6 [19.2-19.8] | 16.6 [15.9-17.3] | 10.7 [9.7-11.6] | 7.5 [6.5-8.4] | 4.4 [3.6-5.3] | 1.6 [1.1-2.2] | 0.1 [0.1-0.4] |
| student_t_hmm | f6 | 14.8 [13.8-15.6] | 13.3 [12.3-14.2] | 9.8 [8.9-10.8] | 8.2 [7.3-9.2] | 5.2 [4.4-6.1] | 3.0 [2.4-3.8] | 1.9 [1.4-2.6] |
| hsmm | base | 11.3 [10.4-12.3] | 6.5 [5.6-7.4] | 4.3 [3.6-5.2] | 4.0 [3.2-4.8] | 0.2 [0.1-0.5] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] |
| hsmm | f3 | 17.1 [16.3-17.7] | 16.1 [15.2-16.8] | 12.3 [11.4-13.3] | 9.4 [8.5-10.4] | 6.8 [6.0-7.8] | 5.2 [4.3-6.1] | 3.0 [2.3-3.7] |
| hsmm | f6 | 14.1 [13.1-14.9] | 13.5 [12.6-14.4] | 11.2 [10.2-12.2] | 9.1 [8.1-10.0] | 5.5 [4.7-6.4] | 4.5 [3.7-5.3] | 3.6 [3.0-4.5] |
| bocpd | base | 0.2 [0.1-0.5] | 0.1 [0.0-0.3] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] |
| bocpd | f3 | 14.6 [13.7-15.4] | 9.8 [8.8-10.7] | 6.5 [5.7-7.5] | 4.2 [3.4-5.0] | 0.8 [0.5-1.3] | 0.0 [0.0-0.2] | 0.0 [0.0-0.2] |
| bocpd | f6 | 18.2 [17.6-18.7] | 14.7 [13.8-15.5] | 10.8 [9.8-11.8] | 9.7 [8.7-10.6] | 6.2 [5.3-7.1] | 2.5 [1.9-3.2] | 0.6 [0.3-1.0] |

Target: <= 1 per 20.

## B. Attribution: old tercile test vs stable-day test, same detectors

FA = false alarms per 20 null sessions (old null = the earlier tercile-matched null of any day; stable null = this report). Hit: old = the earlier tercile breaks (100, both directions, permanent); new = pooled over all D2 breaks with permanent duration (sizes 1.5-10, both directions, 240 splices); new>=3x = same restricted to R >= 3 (144 splices).

| detector | set | thr | FA old null | FA stable null | hit old tercile | hit D2 permanent (all sizes) | hit D2 permanent (R>=3) |
|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | 0.99 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| gaussian_hmm | base | 0.999 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| gaussian_hmm | f3 | 0.99 | 3.6 | 5.1 | 0.21 | 0.28 | 0.38 |
| gaussian_hmm | f3 | 0.999 | 0.8 | 3.5 | 0.09 | 0.20 | 0.28 |
| gaussian_hmm | f6 | 0.99 | 5.4 | 5.8 | 0.31 | 0.28 | 0.40 |
| gaussian_hmm | f6 | 0.999 | 3.6 | 4.3 | 0.16 | 0.25 | 0.35 |
| student_t_hmm | base | 0.99 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| student_t_hmm | base | 0.999 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| student_t_hmm | f3 | 0.99 | 3.2 | 4.4 | 0.21 | 0.28 | 0.39 |
| student_t_hmm | f3 | 0.999 | 0.2 | 1.6 | 0.05 | 0.16 | 0.23 |
| student_t_hmm | f6 | 0.99 | 5.0 | 5.2 | 0.24 | 0.23 | 0.33 |
| student_t_hmm | f6 | 0.999 | 3.4 | 3.0 | 0.10 | 0.18 | 0.24 |
| hsmm | base | 0.99 | 2.0 | 0.2 | 0.00 | 0.00 | 0.01 |
| hsmm | base | 0.999 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| hsmm | f3 | 0.99 | 5.0 | 6.8 | 0.24 | 0.26 | 0.37 |
| hsmm | f3 | 0.999 | 3.2 | 5.2 | 0.13 | 0.23 | 0.31 |
| hsmm | f6 | 0.99 | 5.8 | 5.5 | 0.33 | 0.26 | 0.38 |
| hsmm | f6 | 0.999 | 4.6 | 4.5 | 0.18 | 0.25 | 0.35 |
| bocpd | base | 0.99 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| bocpd | base | 0.999 | 0.0 | 0.0 | 0.00 | 0.00 | 0.00 |
| bocpd | f3 | 0.99 | 3.6 | 0.8 | 0.14 | 0.02 | 0.03 |
| bocpd | f3 | 0.999 | 1.0 | 0.0 | 0.08 | 0.00 | 0.01 |
| bocpd | f6 | 0.99 | 9.0 | 6.2 | 0.27 | 0.10 | 0.13 |
| bocpd | f6 | 0.999 | 5.8 | 2.5 | 0.10 | 0.03 | 0.04 |

## C. Hit rate (median delay of hits, min) by size, direction and duration

Cells: hit rate (median delay); n = 24 per cell. Columns: direction up (calm to stressed) then down, each permanent / 30 / 60 / 120-min sandwich. '-' = no hit.

### gaussian_hmm / f3 / threshold 0.999 (stable-null FA per 20: 3.5)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.12 (25) | 0.21 (20) | 0.04 (45) | 0.00 (-) | 0.08 (12) | 0.08 (20) | 0.00 (-) | 0.12 (25) |
| 2 | 0.12 (20) | 0.17 (20) | 0.17 (40) | 0.17 (40) | 0.04 (25) | 0.04 (20) | 0.04 (20) | 0.00 (-) |
| 3 | 0.12 (25) | 0.25 (25) | 0.12 (15) | 0.33 (20) | 0.17 (20) | 0.04 (50) | 0.12 (20) | 0.04 (60) |
| 5 | 0.50 (30) | 0.21 (20) | 0.29 (20) | 0.54 (20) | 0.21 (20) | 0.12 (20) | 0.12 (20) | 0.21 (25) |
| 10 | 0.38 (20) | 0.25 (20) | 0.75 (20) | 0.42 (20) | 0.29 (25) | 0.29 (25) | 0.21 (25) | 0.21 (20) |

### student_t_hmm / f3 / threshold 0.999 (stable-null FA per 20: 1.6)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.12 (40) | 0.08 (38) | 0.00 (-) | 0.04 (50) | 0.00 (-) | 0.00 (-) | 0.04 (0) | 0.08 (28) |
| 2 | 0.08 (20) | 0.08 (20) | 0.08 (42) | 0.17 (45) | 0.00 (-) | 0.04 (25) | 0.04 (25) | 0.00 (-) |
| 3 | 0.04 (25) | 0.21 (25) | 0.08 (18) | 0.25 (20) | 0.17 (35) | 0.04 (55) | 0.08 (30) | 0.00 (-) |
| 5 | 0.42 (40) | 0.17 (20) | 0.38 (25) | 0.38 (35) | 0.17 (20) | 0.08 (22) | 0.12 (25) | 0.12 (30) |
| 10 | 0.33 (20) | 0.25 (25) | 0.79 (20) | 0.38 (20) | 0.25 (32) | 0.25 (25) | 0.21 (30) | 0.21 (25) |

### hsmm / f3 / threshold 0.999 (stable-null FA per 20: 5.2)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.12 (25) | 0.25 (20) | 0.04 (45) | 0.00 (-) | 0.12 (15) | 0.08 (20) | 0.00 (-) | 0.12 (25) |
| 2 | 0.17 (25) | 0.17 (20) | 0.21 (40) | 0.21 (55) | 0.04 (50) | 0.04 (20) | 0.04 (20) | 0.04 (40) |
| 3 | 0.12 (25) | 0.21 (25) | 0.08 (18) | 0.42 (20) | 0.17 (20) | 0.04 (50) | 0.12 (20) | 0.12 (40) |
| 5 | 0.46 (25) | 0.21 (20) | 0.29 (20) | 0.50 (20) | 0.33 (22) | 0.17 (22) | 0.21 (20) | 0.29 (30) |
| 10 | 0.33 (22) | 0.21 (20) | 0.75 (20) | 0.46 (20) | 0.46 (40) | 0.29 (20) | 0.46 (30) | 0.38 (20) |

### bocpd / f3 / threshold 0.999 (stable-null FA per 20: 0.0)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 2 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.04 (20) | 0.00 (-) |
| 3 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 5 | 0.04 (20) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 10 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.08 (20) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |

### gaussian_hmm / base / threshold 0.9 (stable-null FA per 20: 13.2)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.08 (12) | 0.04 (40) | 0.08 (38) | 0.00 (-) | 0.08 (55) | 0.21 (50) | 0.25 (38) | 0.21 (10) |
| 2 | 0.04 (40) | 0.21 (45) | 0.08 (52) | 0.04 (0) | 0.33 (50) | 0.17 (18) | 0.33 (45) | 0.25 (32) |
| 3 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.04 (45) | 0.46 (25) | 0.08 (35) | 0.46 (45) | 0.42 (45) |
| 5 | 0.04 (5) | 0.08 (5) | 0.04 (0) | 0.00 (-) | 0.33 (45) | 0.42 (22) | 0.46 (40) | 0.50 (45) |
| 10 | 0.08 (40) | 0.04 (25) | 0.08 (58) | 0.00 (-) | 0.50 (50) | 0.42 (38) | 0.67 (42) | 0.46 (40) |

### student_t_hmm / base / threshold 0.9 (stable-null FA per 20: 12.1)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.12 (20) | 0.08 (22) | 0.08 (40) | 0.00 (-) | 0.08 (58) | 0.17 (48) | 0.21 (40) | 0.17 (25) |
| 2 | 0.00 (-) | 0.12 (50) | 0.00 (-) | 0.04 (5) | 0.21 (40) | 0.17 (18) | 0.33 (48) | 0.29 (30) |
| 3 | 0.04 (10) | 0.00 (-) | 0.04 (35) | 0.00 (-) | 0.50 (22) | 0.08 (35) | 0.50 (50) | 0.42 (48) |
| 5 | 0.00 (-) | 0.04 (5) | 0.04 (0) | 0.00 (-) | 0.29 (45) | 0.42 (25) | 0.46 (40) | 0.42 (45) |
| 10 | 0.08 (22) | 0.04 (25) | 0.04 (60) | 0.00 (-) | 0.42 (48) | 0.33 (32) | 0.58 (45) | 0.46 (40) |

### hsmm / base / threshold 0.9 (stable-null FA per 20: 4.3)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.04 (5) | 0.04 (45) | 0.04 (30) | 0.00 (-) | 0.08 (55) | 0.08 (52) | 0.12 (40) | 0.04 (5) |
| 2 | 0.04 (40) | 0.04 (50) | 0.04 (50) | 0.04 (0) | 0.12 (55) | 0.08 (10) | 0.08 (52) | 0.12 (55) |
| 3 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.04 (45) | 0.04 (55) | 0.04 (35) | 0.17 (55) | 0.21 (55) |
| 5 | 0.04 (45) | 0.00 (-) | 0.04 (0) | 0.04 (40) | 0.17 (42) | 0.25 (18) | 0.21 (50) | 0.25 (55) |
| 10 | 0.17 (25) | 0.00 (-) | 0.08 (58) | 0.04 (25) | 0.29 (55) | 0.08 (18) | 0.38 (50) | 0.33 (50) |

### bocpd / base / threshold 0.9 (stable-null FA per 20: 0.0)

| R | up perm | up 30 | up 60 | up 120 | down perm | down 30 | down 60 | down 120 |
|---|---|---|---|---|---|---|---|---|
| 1.5 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 2 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 3 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 5 | 0.04 (25) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |
| 10 | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) | 0.00 (-) |

## Files

| File | SHA-256 |
|---|---|
| section5/s5_d2_stable.py | `600a3a5ea0815a91cd7b9681d2412f69fa60ef7079038f47e41059e5eb0b53db` |
| section5/s5_d2.py | `de822812d38d1b152a179ef37cd7fc2b77a1144fadf8d97be6e8300f8d761a02` |
| section5/s5_fast.py | `8132aabb8b66d64c0fa8d815990d33da83ba97247f9a9b65311e10654f54523c` |
| section5/write_d2_report.py | `2235c83f09a26eead52b239343ba9431bb43d2dad20daf9015429efc03772d20` |
| section5/results/d2_stable_days.json | `76ebb1fd1dade6c6fa10d49e4e97b432a955b2d14a845c5a073d44e93ed9d728` |
| section5/results/d2_results.json | `740118021478afa4deb7d85dd0dbf830d9d0f3893d455e52cecd0aed640c711c` |
