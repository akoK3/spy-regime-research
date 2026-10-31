# Section 5 pilot report

**Status: pilot of DRAFT protocol; no selection run; no evaluation-period data touched.**

Written 2026-10-31T18:10:23.081977+00:00 UTC. Protocol: `SECTION5_PROTOCOL.md` sha256 `8abd20f3557dac0991e30ea8c2807aee35be9d7de1c79b199d7f371397c97479`.

## Scope of the run

- Fold: RAW fold 3 (smallest outer block, 75 sessions). Train 189, validation 58, test 70 sessions after 5-session embargoes; sessions 2023-09-07..2024-12-23, all TRAIN partition (asserted against `section430_executable_split_manifest.csv`).
- Models fitted with fixed a-priori feature sets (timing only; not selected): f3 = rv5_strict__sadj, relative_volume20, intrabar_range_log__sadj; f6 = f3 + downside5_strict__sadj, momentum15_endpoint, close_location_proxy; base = 5-min return only. K=3, lambda=39, seed 0.
- Versions: {'python': '3.12.10', 'numpy': '2.5.4', 'scipy': '1.18.1'}. Total pilot compute after features: 0.79 min (splice features cached from the first pass).
- Splices in pilot: 24 break + 24 null on validation, 24 + 24 on test (protocol: 200 + 200).

## Unit tests (synthetic data)

- 22 tests, 0 failures, 0 errors (`section5/results/unit_tests.json`). Families covered: Gaussian HMM, Student-t HMM, HSMM, BOCPD; also events (T_d, T_c, hold, skip reset, refractory, first-2-update rule, direction), pool/era/TRAIN assertions, preprocessing, LM Student-t threshold, checkpoint resume, splice construction, tercile pairing, QLIKE/DM/threshold choice.
- Defects found by the tests and fixed before the pilot: Student-t df update counted the (nu+D) digamma terms twice (df stuck at the 2.1 bound on Gaussian data); NaN-unaware comparison in the splice test; splice tau drawn at a bar with a missing price (assert in `make_splice`); sessions with missing closes now excluded from splice sampling (< 98% finite closes).

## Splice-integrity tests on real RAW data (3 splices, B outside A's 20-session history window)

| iA | iB | g | continuous at tau | tau exact (first changed bar = g+1) | tau = availability of bar g | tau in 11:00-14:30 | pre-tau features = A native (rtol 1e-9) | B pre-tau edits change nothing | A post-tau edits change nothing | post-tau features differ | PASS |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 628 | 586 | 254 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 604 | 578 | 274 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |
| 617 | 594 | 194 | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS | PASS |

- The first pass of these tests reported 2 of 3 FAIL because B sat inside A's 20-session history (the relative-volume and __sadj baselines legitimately use that history) and because NaN closes compared unequal. Test selection and comparison were corrected; the pipeline was unchanged.
- BOCPD confirmation tests (unit tests, synthetic streams): alarm at T_d; T_c at the third real update after T_d with no new alarm; a skip resets the count (T_c moves from update 13 to 15 in the test case); a new alarm during the hold restarts the candidate; no alarm in the first two updates; the third update is not a rising edge; unconfirmed at the close is dropped and counted. All PASS. State-model equivalents (HMM/HSMM) also PASS.

## Timings (seconds, one core, RAW fold 3: 14,706 train grid bars)

| Family | base D=1, 1 start | f3 D=4, 1 start | f6 D=7, 1 start | base 3 starts | f3 3 starts | filter val (58 sessions, f3) |
|---|---|---|---|---|---|---|
| gaussian_hmm (K=3) | 0.17 | 0.15 | 0.20 | 0.53 | 0.52 | 0.002 |
| student_t_hmm (K=3) | 0.21 | 0.22 | 0.28 | 0.63 | 0.72 | 0.002 |
| hsmm (K=3) | 1.09 | 1.02 | 1.13 | 3.32 | 3.67 | 0.018 |
| bocpd (lambda=39; no fit; filter train) | 0.17 | 1.47 | not timed | n/a | n/a | 0.214 |

- HSMM K=2 base 1 start: 0.90 s. BOCPD filter of train at lambda 12 / 78 (f3): 1.47 / 1.47 s.
- EM iterations at 1 start: Gaussian 21/12/14, Student-t 20/17/19, HSMM 13/12/13 (base/f3/f6); tol 1e-4 reached before the 200 cap in every fit.
- Load RAW panel and compute the 20 columns: 2.0 s (cached afterwards). LM Student-t fit: 0.42 s.
- Spliced-session feature recomputation: about 4.3 s per splice (24 splices in 1.7-1.8 min, from run-log timestamps; the per-splice timer was lost on cached reruns). Splice filtering is negligible (HSMM 0.009 s, BOCPD 0.08 s per 24 sessions).

## Projected budget (one core)

Assumptions: greedy forward selection tries all remaining primary candidates at each of 6 steps (99 fits per family per fold; steps 1-3 timed at D=4, steps 4-6 at D=7), each fit followed by filtering of train and validation; K/lambda tuning with 3 starts for the feature model and the baseline; 200 + 200 validation and 200 + 200 test splices per fold with features recomputed once and shared by all families. BOCPD D=7 is extrapolated (D=4 time x 7/4).

| Item | Seconds per fold |
|---|---|
| selection + tuning, gaussian_hmm | 21 |
| selection + tuning, student_t_hmm | 30 |
| selection + tuning, hsmm | 128 |
| selection + tuning, bocpd | 233 |
| splice feature recomputation (800 splices) | 3440 |
| **Total per fold** | **3852 (64 min)** |

- 34 folds: 36 h. Every 2nd fold (17): 18 h. Splice feature recomputation is 89% of the per-fold time.
- Sensitivity set (80 columns, RAW only, 4 folds): selection scales with the candidate count (about 4.2x the selection part, 29 min per fold) plus the same splice cost.
- Not included: 1-/15-min grid runs (5x / 0.33x the steps per session), 3 seeds, +/-0.05 threshold runs, LEGACY +5/+10 min delay runs, H2 placebo (10,000 draws), power simulations, 5.13 refits.

## Pilot sanity numbers (fixed sets, not selected; development evidence only, not results)

| Family | variant | threshold chosen on validation nulls | val null FA rate | val hit rate | test FA | test hit rate | val mean QLIKE |
|---|---|---|---|---|---|---|---|
| gaussian_hmm | base | 0.99 | 0.0 | 0.0 | 0.0 | 0.0 | 0.3536 |
| gaussian_hmm | f3 | None | None | None | None | None | 0.3476 |
| student_t_hmm | base | 0.99 | 0.0 | 0.0 | 0.0 | 0.0 | 0.3439 |
| student_t_hmm | f3 | None | None | None | None | None | 0.3500 |
| hsmm | base | 0.99 | 0.041666666666666664 | 0.0 | 0.0 | 0.041666666666666664 | 0.3755 |
| hsmm | f3 | None | None | None | None | None | 0.3466 |
| bocpd | base | 0.7 | 0.0 | 0.08333333333333333 | 0.0 | 0.08333333333333333 | 0.5159 |
| bocpd | f3 | None | None | None | None | None | 0.5070 |

- `None` = no grid threshold met at most 1 false alarm per 20 validation null sessions. Diagnostic (`diag_pilot_fa.py`, Gaussian HMM, validation nulls): false-alarm rate by threshold for base 0.9:0.88, 0.95:0.42, 0.99:0.00; for f3 0.9:0.71, 0.95:0.42, 0.99:0.21. T_d at threshold 0.99 for f3 relative to the seam bar g (slots): [-270, -140, -75, -145, 20] (4 of 5 occur before the seam).
- Abstention / skip shares (validation, share of grid bars / of used bars): base 0.0000 / 0.0049; f3 0.0129 / 0.0070; f6 0.0388 / 0.0171.
- Prep (inner train only), 20 inputs: log=5, raw=15; dropped 0. Student-t Lee-Mykland threshold on inner train: 9.5648 (df 6.23, scale 0.868, n 61506) vs 4.6113 Gaussian; used only for the sensitivity-only flag.
- Checkpointing: second and later pilot passes loaded cached fits/splices (hits 98, misses 17 in the last pass); no recomputation of finished units.

## Protocol problems found

1. 5.2 'sensitivity 83' vs 'jump_variation__sadj dropped': the 83 kept in matrix v2 include jump_variation_15/30/60__sadj; after the drop the set is 80. Assertions enforce 80.
2. 5.1 embargo placement is not specified. A4 gives inner train 189 / validation 63 / outer 126 (RAW fold 3: 75). Here the first 5 sessions of validation and of test are removed (fold 3: 189 / 58 / 70). The outer block is also the 'test' segment; no separate embargo precedes inner train.
3. 5.5 'T_c: 3 consecutive real updates hold': whether T_d counts as one is not stated; chosen: T_c is the third real update after T_d.
4. 5.5 BOCPD 'no new alarm over those 3' is undefined while P(changepoint within 3 updates) stays high for 3 updates after a true change; chosen: alarm = rising edge of P >= threshold. Consequence: a transient outlier (P drops next update) is also confirmed; the rule has no persistence requirement for BOCPD.
5. 5.3 'no alarms on the first 2 updates': for BOCPD P(run length <= 2) equals 1 at updates 1-2 and about 1-(1-1/lambda)^3 at update 3 (22% at lambda 12), so the first-2-updates rule is necessary and sufficient only with the rising-edge definition.
6. 5.5 refractory start and state baseline are not specified; chosen: refractory starts at T_c; the current state is the argmax at updates 1-2 and after each T_c; a cancelled candidate has no refractory.
7. 5.6 threshold rule is infeasible with a grid capped at 0.99 for the f3 models (validation null false-alarm rate 0.21 at 0.99 for the Gaussian HMM; most false alarms are far from the seam, i.e. ordinary state switching, not splice artefacts). Return-only baselines meet the rule only at 0.99 (HMM, HSMM) or 0.70 (BOCPD). The grid needs an upper extension or a different criterion; this changes which model families can be scored.
8. 5.6 hit rates are very low in the pilot (validation 0-8% for baselines at the chosen threshold), so 'median delay' is undefined for most folds unless misses are censored. No censoring rule is given; the pilot reports hit rate and delays of hits separately.
9. 5.6 'calm' / 'stressed' and 'volume tercile' are undefined; chosen: session realized variance and session volume terciles within the fold segment (validation for calibration, test for scoring); calm = lowest, stressed = highest; full 390-bar sessions with >= 98% finite closes only (early closes and gap sessions are excluded from splices).
10. 5.6 QLIKE for BOCPD: 'regime-conditional forecast' has no regimes; chosen: two regimes weighted by P(changepoint within 3), with inner-train regime means of the next-60-min variance. HMM/HSMM use filtered-state-weighted inner-train means. BOCPD QLIKE is 0.51 vs 0.34-0.38 for the state models (pilot).
11. 5.8 objective compares validation QLIKE across feature sets whose start bars differ (abstention f3 1.3%, f6 3.9% of grid bars); the protocol does not say whether to compare on common bars. The pilot DM uses common bars only.
12. 5.2 'log only if strictly positive' does not say which features are log candidates. Chosen: every input except the 5-min return, return_1m, momentum*, close_location* (signed or bounded). Out-of-sample non-positive values of a logged feature become missing (skipped update).
13. 5.1 'Amihud normalization' has no object in the primary 19 (no Amihud column); implemented as division by the inner-train median for the sensitivity set and tested on synthetic data only.
14. 5.3 the 5-min return at the first decision bar (stamped minute 4) has no prior close; chosen: log(close / session open).
15. 5.4 HSMM details unspecified: hazard parameterization with a smoothing prior (0.5 pseudo-count toward the overall hazard), duration cap 78 for all sessions, Gaussian emissions; Student-t HMM uses one hidden scale per observation (multivariate t, diagonal scale); Normal-Gamma prior mu0 0, kappa0 1, alpha0 1, beta0 1 on standardized inputs.
16. 5.6 splice B may come from the 20 sessions before A (inside A's baseline history) or from later sessions; the features use only the spliced series and A's past history in either case; the pilot integrity test excludes the first case because B's edits then legitimately move A's baselines.
17. 5.8 budget: splice-feature recomputation, not model fitting, dominates (see projection); the protocol's 'pilot budget' is therefore a function of the splice count and the 21-session recomputation window.

## Choices made without asking (user away)

- All items 3, 4, 6, 9, 10, 12, 14, 15 above were decided by the pipeline author as the most reasonable reading and are listed so they can be amended.
- Pilot set: f3/f6 chosen a priori for timing; they are not selection outputs and must not be read as such.
- Splice sizes in the pilot (24 + 24 per segment) were chosen for runtime; test splices were scored once per model at the validation-chosen threshold (fold-3 test segment is TRAIN-partition development data).
- Threshold grids: states 0.50-0.95 step 0.05 plus 0.99; BOCPD 0.05-0.95 step 0.05 plus 0.99.
- QLIKE target floor 1e-10; target needs >= 50 valid minute bars of the next 60; DM uses Newey-West lag 12.
- The protocol file was committed before any Section 5 code was run; no amendments were made to it.

## Files

| File | SHA-256 |
|---|---|
| section5/s5_lib.py | `bd91387861974903148e8a0e0bbcafd48722583f80ed70933f894c6a02a89d20` |
| section5/s5_models.py | `754108ea0645dbf5df06b8876337c1a5501ecef985823349b0aa5ceb1d6b9c5c` |
| section5/s5_events.py | `483ef9b63d793fe50725eb091fddfcf88eb685e01a6b0ca9e3b1d760408c8cef` |
| section5/s5_eval.py | `85ebce066fa4b13adaaff09d743d3b31bed5fbe6b46dada7e97957f57691ffd4` |
| section5/s5_tests.py | `69cbf5e0ade9ffac9ab281f2cb4b9ecd1b51dcd1b0e3325772afa2e9354679ca` |
| section5/s5_pilot.py | `3706267fb06d0a269a240d4d7704159b42d6724cb700dd28272debb992f77764` |
| section5/diag_pilot_fa.py | `48bb84abd1a1a83474387807e924696b85b839606fe22dfd7b553f16485a576d` |
| section5/write_protocol.py | `36f1a048835fbaaf8269f39c96cdb9e12f87e6c89e714785d6f23dfcf8ea36d9` |
| section5/write_pilot_report.py | `61e8b4ceec7cd17e72a696123cf3237836bd9eb2f7bc0bf501e6853a221f8706` |
| section5/results/pilot_results.json | `a108095d1483b31e2cee766ee5b34761d2c401a6be6ebef8e495f75cc9733ba7` |
| section5/results/unit_tests.json | `474482e40781a9890e3c2c2706fe4c43802fb349be7deefd9db8922e77864666` |
| section5/results/diag_pilot_fa.json | `d57d5cbf8f6ef5773200c65bf6be414ffddfc13055ebfff5c3d9962a07b604cd` |
