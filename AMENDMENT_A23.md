# Amendment A23 (EXPLORATORY: combined volatility + volume model, rv10_partial90__sadj + relative_volume20)

Dated 2026-11-08T22:35:00+00:00 UTC (2026-11-08T17:35:00-05:00 New York). Status: ADOPTED 2026-11-08T23:05:00+00:00 UTC (user approval "A23: approved, force both inputs"; the draft, sidecar 1bfcbaa0..., committed in 5e85e8e, is unchanged apart from this status line; rule 1a forced inputs confirmed by the user). Written before any code it governs and before any of its results exist. Decided by the user after the A22 results (Section 5 close-out item 5); runs before the freeze. Disclosed: MR2, its A17-style phase, D7 (A21), Step 2 (liquidity) and all A22 results have been seen; the choice of the two inputs is informed by them (rv10_partial90__sadj is the MR2 era final feature of all three H1 families in LEGACY; relative_volume20 is the Step 2 liquidity feature; Step 2 D7 volume response +0.06 to +0.10). Therefore EXPLORATORY: no confirmatory claim, no change to the MR2 verdicts, setups, H1 families or 5.12. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A20.md` | `828e14b7d8b3445eb499fdcd7a32e1e0a5bd41dfc80b5d3224186c6a85481160` |
| `AMENDMENT_A21.md` | `b4ed40509480b6a69e621c3be309ab28d397e8e2b53b25bd459d4da305b5eda0` |
| `AMENDMENT_A22.md` | `3ce7b683a1369659b14b22c068bcc25c6a7b14a7a6b15758946c7050f8a15217` |
| `section5/results/main_run_2/run_complete.json` (MR2) | `19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a` |
| `section5/results/mr2/a17/a17_results.json` | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/results/mr2/d7_a21/d7_results.json` | `cc21ff4a62e669ed0fcac7e02f651c37ae9f8076f261d8903cbd6e4359f389ed` |
| `section5/results/step2_liquidity/step2_results.json` | `3a3695dde1bd8504ab613768b2be7e280b36cd7c7ef555aecd0addbaec6f8437` |
| `section5/results/contamination_list.json` | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/s5_d7.py` | `a0f531b8e79d0939bae8b64d657ca759265f48b6a01d4b777a5a1e1748f288fa` |
| `section5/s5_step2.py` | `f4fdf4c2e775dec5699c531cfb08b82958fbbd13bf178144c80c901e5952807a` |

Facts used: both inputs are in the A20 pool (13 columns); in MR2, 5 of the 136 fold-family setups already select exactly these two features, 8 select relative_volume20.

## Rule 1: model

1a. Inputs fixed: the deseasonalised 5-minute return plus rv10_partial90__sadj and relative_volume20 (A20 inputs, same preprocessing and 5.3 abstention rule). No greedy selection and no 1% rule: the feature set is forced. If a fold's inner-train preprocessing drops either column (zero variance), the fold is reported as not evaluable for that family, not refitted with one input.
1b. Families: Gaussian HMM, Student-t HMM, HSMM (H1 families) and BOCPD (secondary, as 5.4).
1c. Tuning as 5.8: K (HMM 2-4, HSMM 2-3) or lambda (12, 39, 78) by the validation objective of MR2 (mean QLIKE of the regime-conditional forecast of the next-60-minute deseasonalised variance, A20 rule 2), 3 starts, seed 0, inner train only. Baseline: the return-only model with its own tuned K/lambda, tuned identically (= the MR2 baseline).
1d. Thresholds: A7 fold-level bisection to 0.20 confirmed alarms per validation session (same bounds and tolerance), feature and baseline models.
1e. Reproduction check: for the 5 MR2 fold-family units whose MR2 setup is exactly these two features, if the tuned K/lambda equals MR2's, the H1(a) and H1(b) fold effects must equal MR2 exactly; every baseline test QLIKE mean must equal the MR2 A17-style record exactly. A mismatch stops the run (exit 4).

## Rule 2: scoring (all EXPLORATORY)

2a. H1 on all 34 folds, MR2 splices (seed 4242): H1(a) and H1(b) fold effects; fold tests, IU and Holm over the three H1 families exactly as 5.9 / 5.11, 26 confirmatory folds primary, all folds reported; per fold beside the MR2 effect of the same family (difference A23 - MR2 reported, no test on it).
2b. D7 (A19, A19.2, A19.3, A21 rule 1) on the A23 fits of the 26 confirmatory folds at the 1d thresholds: all injection types and levels; the two outcomes of interest are (i) liquidity vol_x2 (primary) and vol_x0.5 and (ii) the variance positive controls pc_ratio3 and pc_ratio5.29. 'Responds' as A19 rule 2e (gain >= 0.10 and day-clustered 95% CI excluding 0), feature model and feature-minus-baseline both reported. Gates i (variance-neutral share, liquidity), iii (null <= 0.30) and iv (>= 100 days) required for a liquidity verdict; gate ii is outcome (ii) and is reported, not required. Compared descriptively with the MR2 D7 (A21) and Step 2 D7 responses.
2c. Secondary: H1(c) (98 events, as A17) from the A23 test alarms at 0.20; test liquidity QLIKE (Step 2 target) of the A23 feature model versus its return-only baseline, reported without a test.
2d. Nothing here enters the MR2 verdicts, the 5.12 setups or the freeze.

## Rule 3: runner, preflight, runtime

3a. One checkpointed runner (per fold-family unit; tag = script, amendment, code version, protocol); a crash resumes; a guard refusal or reproduction mismatch stops. Order: H1 units (all 34 folds), thresholds, D7 (26 folds), aggregation.
3b. Preflight on the contaminated RAW 3 and LEGACY 29 only (unit tests; full unit for the four families: tuning, H1 scoring, thresholds, D7 fold unit), written only to `section5/results/a23_preflight/`. The user launches.
3c. Runtime estimate (from the A22 seed phase, 2.55 h per 26-fold refit-and-score pass, and MR2 timings): tuning fits about 1-1.5 h, H1 scoring of 34 folds about 3.3 h, thresholds and D7 about 0.5 h: about 5-6 h in total (range 4-8 h); preflight about 40 min.
3d. Script `section5/s5_a23.py` (registry POST_MAIN_RUN), tests `section5/s5_tests_a23.py`, runner `section5/run_a23.ps1`; results `section5/results/a23/`. No protocol re-freeze, no 5.12 freeze, no era calibration.

## Governs

`section5/s5_a23.py`, `section5/s5_tests_a23.py`, `section5/run_a23.ps1`, `section5/results/a23/`, `section5/results/a23_preflight/`.
