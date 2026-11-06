# Amendment A19.2 (D7: jump sizes, threshold-sweep scoring, positive control)

Dated 2026-11-06T19:30:00+00:00 UTC (2026-11-06T14:30:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before D7 is launched and before the code change it governs. Decided by the user after the D7 preflight on RAW fold 3 (contaminated; the preflight and an 18-day diagnostic on that fold only). No clean-fold D7 result has been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A19.md` | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` |
| `AMENDMENT_A19_1.md` | `bffed0e9f8acf7aea9d98ae83950624d7cb3f4b95e37c15997fccda584eed0a0` |
| `section5/s5_d7.py` (before this amendment) | `73eab2c34256d9a36f3d8d975f3c1c9557d340e29e2d5b497c96b88a6537cd8d` |
| `section5/results/d7_log.txt` | `c6526b6f140001d257adeb3f6969a44fa8a406dcdabe1d4021b8db3b8a7aa662` |
| `section5/results/d8/d8_results.json` | `540bfb5c924600811a7ac19a91c1bef64958eaf0c77b1080f74a7b2b8a0a7098` |

What the preflight showed (RAW 3 only): 3 jumps of 6 local sd exceed the 60-min window's variance, so A19 gate (i) fails for jumps by construction; at the A17 fold thresholds the ratio-3 variance splice hit 0 of 18 days for the Gaussian and HSMM feature models (null .22), because a single strict threshold measures one point of the hit/alarm curve.

## Rule (replaces the named parts of A19 rule 2; everything else in A19 rule 2 stands)

1. Jumps (replaces the jump levels of A19 rule 2c): 2 jumps of 4 local sd (about the D8 p90 of the jump count) and 2 jumps of 5 local sd (p99 level); local sd = the bipower scale of the 60 bars before tau; jump minutes and signs drawn per day (seed 1907). The diffusive (non-jump) returns of the 60 min after tau are rescaled so that the window's sum of w r^2 equals the unmodified value, so gate (i) holds where feasible (an infeasible day keeps its unscaled returns and counts against gate (i)). Primary level: 2 x 5 sd; 2 x 4 sd reported.
2. Scoring by threshold sweep (replaces the fixed-threshold hit of A19 rule 2d-2e as the decision statistic): per fold and model, the 5.6 sweep (theta 0-30 step 0.25; BOCPD m 1-80) is run on the fold's matched null (the unmodified stable test days with the same tau) and on each injected set. x = confirmed alarms per matched-null session at each threshold. For each alarm rate x on the grid 0, 0.01, ..., 0.50 the fold uses the loosest threshold whose matched-null alarm rate is <= x (no such threshold: y = 0); each day's injected and null hit indicators (5.6 hit: confirmed within 60 min after tau, T_d strictly after tau) at that threshold are averaged over the grid. The mean over days of (injected minus null) is the mean hit-rate gain over alarm rates 0-0.5 (the pAUC difference divided by 0.5). "Responds" = gain >= 0.10 AND its 95% CI excludes 0 (percentile bootstrap over (era, day) clusters, 10,000 resamples, seed 1907; thresholds held at their full-sample choice). Feature minus baseline reported the same way. The fixed-threshold (A17) hit rates are still reported, as secondary.
3. Positive control (replaces A19 gate (ii)): 5.6 permanent variance splices of ratio 3 and ratio 5.29 (the D8 pooled p99 variance ratio) on the same days and taus, scored by the same sweep. Gate (ii) passes when every H1 family's feature model responds to both.
4. Gate (iii) under the sweep: the matched-null grid-averaged hit rate <= 0.30 for every H1 family model. Gates (i) and (iv), the "missed" rule and the Step 2 trigger are unchanged.

## Governs

`section5/s5_d7.py`, `section5/s5_tests_d7.py`; results under `section5/results/d7/`.
