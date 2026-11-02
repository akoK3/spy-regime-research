# Descriptive check D6: variance ratio around FOMC statements and listed shocks

Written 2026-11-02. TRAIN dates only (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23), no detectors, no models. Script `section5/s5_d6.py` (+ `s5_d6_flash.py`); results `section5/results/d6_results.json`, `d6_flash_supplement.json`, `d6_fomc_dates.json` (dates and sha256 of the fetched pages).

## Definitions (set before the run)
- Deseasonalised 1-min variance = r^2 / median r^2 of the same slot over the previous 20 sessions (same as the D2 stable-day definition). Slot 0 = 09:30 bar.
- Ratio = mean over the 60 bars from T (the bar stamped T contains the event) / mean over the 60 bars before T. A window needs >= 50 finite bars of 60, else the ratio is undefined. Sessions need 390 bars and >= 20 prior sessions.
- Random moments: 1,000 draws per event time (FOMC: 1,000 per era, pooled) from other 390-bar sessions of the same era, FOMC days and the event day excluded, same slot T, same window rule.
- FOMC dates: scheduled meetings with a statement, last meeting day, fetched from federalreserve.gov (`fomchistorical{2003..2018}.htm`, `fomccalendars.htm` for 2022-2024): 152 meetings listed. All are taken at 14:00 ET as instructed; the Federal Reserve pages do not give release times, and releases were at 14:15 on some earlier dates, so the true release minute can differ from 14:00. Conference calls are excluded.
- Shock times (my choice, documented): Flash Crash decline from 14:32, and 14:45; 2015-08-24 at the 09:30 open (before = previous session's last 60 bars); 2018-02-05 at 15:00.

## FOMC statements at 14:00
129 of 152 are usable: 21 LEGACY dates lack a clean window or are absent from the panel, and the 2022-01-26 and 2022-03-16 meetings fall before TRAIN or the 20-session baseline (list in `d6_results.json`).

| | n | 5% | 25% | median | mean | 75% | 95% | share > 1.5 | share > 2 |
|---|---|---|---|---|---|---|---|---|---|
| FOMC 14:00 | 129 | 1.64 | 4.90 | 8.56 | 12.13 | 18.02 | 29.72 | 0.96 | 0.91 |
| random 14:00 | 1,909 | 0.39 | 0.62 | 0.91 | 1.18 | 1.30 | 2.67 | 0.18 | 0.09 |
| FOMC LEGACY | 107 | 1.63 | 4.34 | 7.40 | 10.64 | 13.58 | 26.85 | 0.96 | 0.91 |
| FOMC RAW | 22 | 2.86 | 11.54 | 18.04 | 19.38 | 24.13 | 47.62 | 0.95 | 0.95 |

99.4% of random moments are below the FOMC median; Mann-Whitney p = 2e-70. Two FOMC ratios are below 1 (minimum 0.45).

## Listed shocks (percentile among 1,000 random moments at the same time of day)
| event | ratio | percentile | random median / 95% quantile |
|---|---|---|---|
| 2010-05-06 from 14:32 | undefined under the 50-bar rule (47 finite bars after T) | - | 0.93 / 2.39 |
| 2010-05-06 14:45 | undefined (49 finite bars after T) | - | 0.94 / 2.50 |
| 2010-05-06 14:32, deviation: minimum 40 bars | 7.53 | 99.8 | 0.96 / 2.41 |
| 2010-05-06 14:45, deviation: minimum 40 bars | 4.42 | 99.0 | 0.95 / 2.39 |
| 2015-08-24 open | 3.08 | 97.2 | 0.93 / 2.65 |
| 2018-02-05 15:00 | 6.15 | 99.9 | 0.91 / 2.19 |

The Flash Crash windows fall just below the 50-bar rule because the panel has missing bars; the lowered minimum (40, applied also to its random moments, seed 6002) is a stated deviation, applied after seeing the NaN.

## Notes
- The random 14:00 distribution is centred near 0.9 with a long right tail (18% above 1.5, 9% above 2): ordinary 60-minute windows often have large ratios, so a ratio of 2 alone is weak evidence of a break; FOMC ratios are mostly far above this (median 8.6).
- Ratios are of means of squared-return ratios and are dominated by a few large bars; no outlier trimming. The FOMC ratio is large partly because the hour before 14:00 is quieter than the slot baseline.
- Descriptive only; no threshold or protocol change follows from this report.
