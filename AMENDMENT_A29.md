# Amendment A29 (Section 6: H4 AUC gain out of sample; H3/H4 interpretation rules)

Dated 2026-11-10T04:12:35+00:00 UTC (2026-11-09T23:12:35-05:00 New York). Status: DRAFT (revised 2026-11-10T04:19:00Z), awaiting the user's approval. First draft (sha256 in the ledger row of 2026-11-10 04:12:35Z) written before its code; this revision of rules 1b, 1c and 1g follows a diagnostic made during the rule 2 smoke test (below) and precedes the rule 2 run. No Section 6 development result exists; the development run is held until A29 is adopted. Requested by the user on 2026-11-09 after the synthetic validation of the A28 code.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A28.md` (ADOPTED; rules 3, 4e, 5b, 6d, 7d) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `section6/results/synth_validation.json` (A28 code, 999 resamples) | `f5809016cbf0019c72e35b8a10453572cd980c50fc7957f401528f42b98ed209` |
| `section6/s6_lib.py` (A28 code: `auc_gain`, in sample) | `440201823b654934e6b050e235a964742eb5b8279952e6af079696ea22f478bd` |
| `section6/s6_run.py` (A28 code: `h4_test`) | `9bead28170c8207ac23588a1dfb9ab8fb6792a16ad29d7eb244e997c417f2f92` |

Synthetic validation (A28 code; 200 replicates per null generator):
- With no effect the in-sample AUC gain averages +0.010 to +0.011, not 0. Adding C to the logistic model always fits slightly better in sample.
- H4a rejected 8.0% and 7.0% at 0.05; H4b rejected 1.5% and 1.5%.
- With H4 planted alone (large same-hour asset moves, no next-day persistence), H3 gamma averaged -0.50 to -0.56 for every asset.

## Rule 1: H4 statistic out of sample (replaces the in-sample gain of A28 4e)

1a. Folds: within each era, the calendar weeks that hold H4 units are taken in date order and split into K = 5 contiguous blocks of as equal a number of weeks as possible. Fold k is block k of every era, so a week is in exactly one fold and a fold never splits a week.
1b. For each fold k, both logistic models of A28 4e are fitted on the units of the other four folds:
  - SPY's own information at t;
  - the same plus C(t).
  Each is then evaluated on the units of fold k.
1c. Statistic: within each fold, the AUC of the model with C minus the AUC of the model without C; then the mean of the fold gains, weighted by the number of units per fold. A fold whose evaluation units hold one label class only is left out of the mean. H0: gain <= 0, one-sided. Same logistic fit (Newton, ridge 1e-6) and AUC (midranks) as A28.
  - Not pooled: pooling out-of-fold predictors across folds mixes fold-specific intercepts, whose errors are anti-correlated with each fold's base rate (Forman and Scholz 2010, "Apples-to-apples in cross-validation studies", SIGKDD Explorations 12(1)). The first draft pooled.
1d. p-value: the week-block bootstrap of A28 3c (within era, 9,999 resamples, centred, add-one).
  - Each resampled row keeps the fold of its original week, so copies of one week are never split between training and evaluation.
  - A resample in which a training set holds one label class only, or a fold is empty, gives NaN. NaN resamples count as not exceeding, as in A28.
1e. Scope: H4a and H4b, and every H4 secondary, sensitivity and check: at S and at T + 15; the 5-day label; the 70th and 90th percentile labels; rules 7a, 7c, 7e and 7f; and the 7d null control. The in-sample gain is reported beside each test as descriptive only.
1f. The A28 6d power check is rerun with this statistic before any development result. The power run started 2026-11-09 22:59 NY with the A28 statistic was stopped at 23:17 NY before finishing; nothing from it is used.
1g. Size reporting. The out-of-fold AUC of a near-uninformative model falls below 0.5: its slopes, fitted on the other folds, are anti-correlated with the held-out fold's own association. The model with C is protected when C dominates, so the out-of-fold gain can exceed the in-sample gain when SPY's own information is weak.
  - Smoke test, planted H4 replicate 0, H4a: the SPY-only model's per-fold out-of-fold AUC was 0.32-0.49 (0.52 in sample). The gain was 0.256 out of fold against 0.160 in sample.
  - The rule 1 statistic is the test. Each H4 result also reports, as descriptive: each model's out-of-fold AUC, and the in-sample gain.
  - The size of an H4 effect is read from the out-of-fold AUC of the model with C, next to the SPY-only model's AUC, not from the gain alone.

## Rule 2: acceptance check before adoption (synthetic data only)

2a. The synthetic validation is rerun with the rule 1 statistic, with the A28 code otherwise unchanged:
  - the same two no-effect generators, 200 replicates each;
  - planted H3 and planted H4, 40 replicates each;
  - 999 resamples.
2b. Target: about 5% rejection at 0.05 under no effect. Accepted when, for H4a and H4b under both generators, the rejection rate is at most 0.081 (5% plus two Monte Carlo standard errors at 200 replicates).
2c. Planted H4 must still be detected. The rule 1 target uses the same out-of-fold statistic with C replaced by the oracle score. The estimate must lie within two standard errors of that target.
2d. If 2b or 2c fails, work stops and the user decides. The results are reported with the request for adoption.

## Rule 3: interpretation rules for H3 and H4

3a. **Dependence.** H3's prior-hour control, log RV over (T - 60, T], contains the window (S, T] in which H4b's C(T = 0) is measured, and H3's own-return controls are taken over (S, T]. A break with large same-hour asset moves therefore raises H3's controls.
  - H3's gamma measures next-day RV beyond what the asset's own same-day hour already predicts.
  - H3 and H4 are not independent. Holm (5b) is valid under any dependence and is unchanged.
  - A rejection of both is read as one cross-asset finding seen two ways, not as two independent confirmations.
3b. **Negative H3.** H3 is one-sided, and gamma < 0 is never a rejection. When gamma's two-sided 95% bootstrap interval lies wholly below 0, it is reported as a transient cross-asset response: same-hour asset moves that the next day does not continue beyond the prior-hour control. It is not reported as a calming effect.
  - It is read together with H4. Negative H3 with a positive H4 is the pattern the synthetic validation produces when H4 moves are planted without persistence.
3c. **Descriptive diagnostic (secondary, not tested).** H3 per asset with the prior-hour control taken over (S - 60, S], before the break window, instead of (T - 60, T]. The other controls are unchanged. A gamma that moves up under this control shows how much of the 3a dependence sits in the S-to-T window.

## Rule 4: order

4a. A29 is hashed into the ledger before its code.
4b. The Section 6 development run (`s6_run.py development`) refuses to start unless A29 is ADOPTED and matches its sidecar.
4c. The development run on Gaussian HMM and HSMM (ledger 2026-11-10 03:42Z) follows adoption, the rule 2 check and the rule 1f power rerun, in that order.

## Governs

The H4 statistic and its bootstrap, the Section 6 synthetic acceptance check, and the reading of H3 next to H4. A28 is otherwise unchanged. H2 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.
