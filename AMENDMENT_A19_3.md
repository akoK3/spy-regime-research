# Amendment A19.3 (D7: bar-scaling check, jumps sized from the post-tau window)

Dated 2026-11-06T19:45:00+00:00 UTC (2026-11-06T14:45:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code change it governs and before D7 is launched. Decided by the user after the A19.2 preflight on RAW fold 3 (contaminated; diagnostics on that fold only). No clean-fold D7 result has been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A19_2.md` | `619d32de48aeaa8a1fd9054fcb676982a84c7028fc27d1c673a38af001480b27` |
| `section5/s5_d7.py` (before this amendment) | `d14f737d368b26c6aea59e2690601660d364226d5f3efa4e3a3bd516875eec11` |
| `section5/results/d7_log.txt` | `c8cc258f42dcca9f35579f852b39f5e7135c835f67726841eab3f2506ac77a0f` |

## Diagnosis (RAW 3, 3 stable test days, before this amendment)

- The variance splice (5.6 `regime_panel`, B = A) scales open, high, low and close together: over the 60 min after tau, log(high/low), |r| and the stored range each change by exactly f (2.11, 2.28, 2.35 for ratio 5.29).
- Every feature is recomputed from the modified panel (`s5_fast.rows_from_panel`). Mean over the hour after tau, spliced vs unmodified: rv10_partial90 2.0x, 2.3x, 2.3x; intrabar_range_log 2.1x, 2.3x, 2.4x. Before tau they are identical.
- The non-variance injections rebuild open = previous close and scale the wicks by the same factor as the returns, so the bar stays consistent. No construction fix is needed (the user's item 2 does not apply).
- The A19.2 jump size used the bipower sd of the 60 bars BEFORE tau. When the hour after tau is calmer, two jumps exceed the window's variance; gate (i) held on 44% (2 x 5 sd) and 78% (2 x 4 sd) of RAW 3 days.

## Rule (replaces A19.2 rule 1's jump size; everything else in A19, A19.1 and A19.2 stands)

1. Jump size from the post-tau window's own sd, in the deseasonalised units the variance-neutral constraint uses: s = sqrt(S0 / 60), S0 = sum of w r^2 over the 60 unmodified bars after tau (w = 1 / slot baseline of r^2). A jump of k sd at minute m REPLACES that minute's return with sign * k * s / sqrt(w_m) (its deseasonalised square is k^2 s^2). Two jumps of 5 sd use 50/60 of S0 and two of 4 sd use 32/60, so the remaining 58 returns can always be rescaled to restore S0 and gate (i) holds by construction. Levels, minutes and signs as A19.2 (primary 2 x 5 sd; seed 1907).
2. Stop rule (user): if the H1 family feature models still do not respond to the positive controls in the RAW 3 preflight, D7 is not launched and the result is reported.

## Governs

`section5/s5_d7.py`, `section5/s5_tests_d7.py`.
