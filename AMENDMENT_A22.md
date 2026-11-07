# Amendment A22 (D8c overlap breakdown; A18 rerun on A20 inputs; 5.10 robustness on MR2; 5.11 power; one priority-ordered runner)

Dated 2026-11-07T16:20:00+00:00 UTC (2026-11-07T11:20:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before any code it governs and before any of its results exist. Decided by the user after the A21 results. Disclosed: MR2, its A17-style phase, D7 (A21) and Step 2 results have been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A18.md` | `f9b8f371090c2db2e6467c250622b527c9bbf255b09e37d6478379d07a9673b0` |
| `AMENDMENT_A19.md` | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` |
| `AMENDMENT_A20.md` | `828e14b7d8b3445eb499fdcd7a32e1e0a5bd41dfc80b5d3224186c6a85481160` |
| `AMENDMENT_A21.md` | `b4ed40509480b6a69e621c3be309ab28d397e8e2b53b25bd459d4da305b5eda0` |
| `section5/results/main_run_2/run_complete.json` (MR2) | `19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a` |
| `section5/results/main_run_2/run_summary.json` | `a1c69277213a3ff8ee827994620b70d1ff91eaa1ab7a4aa682114077807348fc` |
| `section5/results/mr2/a17/a17_results.json` | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/results/mr2/d7_a21/d7_results.json` | `cc21ff4a62e669ed0fcac7e02f651c37ae9f8076f261d8903cbd6e4359f389ed` |
| `section5/results/step2_liquidity/step2_results.json` | `3a3695dde1bd8504ab613768b2be7e280b36cd7c7ef555aecd0addbaec6f8437` |
| `section5/results/d8/d8_results.json` | `540bfb5c924600811a7ac19a91c1bef64958eaf0c77b1080f74a7b2b8a0a7098` |
| `section5/results/a18/a18_results.json` (A18 on MR1 inputs) | `a791c379fbbbfa220342e0b479ad7adaf11afc4002baa2b290fb56c61b6a23cf` |
| `section5/results/contamination_list.json` | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/s5_a18.py` | `580bb98e404a8196327349ff1890423b8d91d99c88770dfc458e197578f76805` |
| `section5/s5_d8.py` | `986f33aa1a03a992900591a2dff8ef1220ff9647ea54317b55abd15507584dc3` |
| `section5/s5_stats.py` | `aa40e5e6d34a1a648e73ff5f70a2255df8e2b9bf32ca3e9e7f0e9d11c65950f7` |

Facts used below: the MR2 fold setups, models (A17-style pickles in `results/mr2/a17/models/`) and fold-level A7 thresholds; the MR2 era final setups (`run_summary.json`); 0 of the 136 MR2 score records has a flagged Student-t fit; the A20 rule applied to the 80-column sensitivity set leaves 69 columns; confirmatory folds 26 (LEGACY 0-22, 25, 26; RAW 0).

## Rule 1: D8c, descriptive overlap breakdown (no detector, no model, no outcome)

1a. Same sessions, windows and statistics as D8 (A19 rule 1a-1c; `s5_d8.era_windows`).
1b. Large volatility change (fixed now): VR >= 2 or VR <= 0.5 (the i.i.d. two-sided 1% points of F(60, 60) are 0.51 and 1.96). Large liquidity change: VOL >= 2 or <= 0.5 (D8). Large jump change: dJ >= 1 (D8).
1c. Primary report, per era and pooled: among windows with at least one large change of the three types, the shares volatility-only, liquidity-only, jump-only and combined (two or more), with combined split into its four patterns; counts; and the share of all windows with any large change.
1d. Secondary: the same with trend (|dt| >= 3.64) and momentum (|drho| >= 0.47) added as types (the 5-type pattern table) and the share of large non-volatility changes that occur without a large volatility change.
1e. Registry DESCRIPTIVE (as D8). Results `section5/results/d8/d8c_results.json`.

## Rule 2: A18 rerun on A20 inputs

2a. A18 rules 1-3 unchanged, run through the MR2 inputs: the A20 pool (13 columns), the deseasonalised QLIKE target for H1(b) scoring, all 34 folds, completion record of kind 'a18-<script hash>'. Comparisons (same features as the main run, D1, non-volatility share) are against the MR2 setups.
2b. Results `section5/results/mr2/a18/`; the A18 run on MR1 inputs (`results/a18/`) is kept unchanged as a record. Sensitivity only (A18 rule 4); contamination POST_MAIN_RUN.

## Rule 3: 5.10 robustness on the MR2 setups (A19 rule 5 made concrete)

Common: MR2 fold setups and A17-style models unless stated; confirmatory 26 folds primary, all folds reported where the item has them; fold tests, IU and Holm as 5.9 and 5.11; nothing changes the MR2 verdicts, setups or 5.12. Contamination POST_MAIN_RUN.

3a. Era: H1(a), H1(b), IU and Holm restricted to LEGACY (25 confirmatory folds) and RAW (1 confirmatory fold, RAW 0: reported as its fold effects; fold tests not evaluable); all-folds per era also reported. From the MR2 records; no computation on data.
3b. Student-t flagged fits: the A14.2 exclusion applied to MR2. MR2 has 0 flagged fits, so the result equals the main result; computed mechanically and reported as such.
3c. Threshold +/-0.05: A7 bisection to 0.15 and to 0.25 confirmed alarms per validation session (same bounds and tolerance), per fold, family and model, on the saved MR2 models; test alarm times; realised test alarm rate per session; H1(c) (98 events, as A17). Reproduction check: the 0.20 target recomputed must equal the stored MR2 thresholds exactly, else stop (exit 4).
3d. LEGACY delay +5 and +10 min: on the 25 confirmatory LEGACY folds, the saved models, and the MR2 splices (same specs, rebuilt), every alarm time (T_d and T_c availability) is shifted by delta; hit = T_d + delta strictly after tau and T_c + delta <= tau + 60 min; null alarm counts unchanged. delta = 0 must reproduce the MR2 H1(a) fold effect exactly, else stop (exit 4). H1(a) fold tests use the shifted LEGACY folds with RAW 0 unchanged; H1(b) is unaffected by definition (A19 rule 5); IU and Holm reported. H1(c) recomputed with shifted alarm times at the 0.20 target.
3e. 3 seeds: seeds 1, 2, 3 replace both the model start seed (0) and the H1(a) splice seed (4242); per confirmatory fold and family the MR2 fold setup (features, K/lambda, baseline K/lambda; no reselection) is refitted (3 starts) and scored (H1(a), H1(b)); fold tests, IU and Holm per seed; the spread across seeds 0 (MR2) to 3 reported.
3f. RAW sensitivity pool: the 80-column set with the A20 rule (69 columns, Lee-Mykland flag included per 5.2); 5.8 selection and scoring rerun on RAW folds 0-3 (RAW 0 confirmatory; RAW 1-3 reported as all-folds); per-fold setups and effects beside MR2's.
3g. Grids (5.3, final setups only): the MR2 era final setups (features, K/lambda, baseline K/lambda) fitted per confirmatory fold on the fold's inner train (seed 0, 3 starts) and scored on grid G in {5, 15, 1} min; G = 5 is the reference that separates the grid effect from the fold-setup versus final-setup difference. For grid G: decision bars stamped G-1, 2G-1, ... minutes after 09:30; return input = the G-minute log return deseasonalised per grid slot by the 5.3 rule; HSMM Dmax = updates of a full session (390 / G); event rule unchanged (3 consecutive real updates, first 2 silent, 30-min refractory, 60-min hit window, same theta and m grids); H1(a) on the MR2 splice specs (same days and taus); H1(b) same target per decision bar, Diebold-Mariano lag 60 / G. 
3h. 1-min HSMM contingency (fixed now): the preflight measures the 1-min HSMM cost; if the projected cost for the 26 folds exceeds 24 h, the 1-min HSMM is not run and is reported as not run with the measured cost (no other duration cap is substituted). It runs last in any case.

## Rule 4: 5.11 power

4a. As A19 rule 6 with MR2: per family (H1 families; BOCPD reported) and component, `s5_stats.mde` with sd = the MR2 confirmatory fold-effect sd, n_folds 26, alpha 0.05/3 and 0.05, power 0.8, nsim 400, nboot 500, seed 0; reported with the observed mean effect.
4b. D7: the smallest true hit-rate difference with 80% power under the A19 rule 2e (difference >= 0.10 and 95% CI excluding 0), given 258 days and each feature model's D7 (A21) null rate; also for the Step 2 D7. Binomial simulation, 2,000 draws, seed 1907, days independent, null and injected hits independent; the CI in each draw by the normal approximation (a bootstrap inside each draw is not computed; disclosed). Grid 0.01 to 0.40 step 0.01.

## Rule 5: runner, order, preflight

5a. One checkpointed unattended runner, phases in this priority order (most important finish first; cheap items first): (1) 5.11 power; (2) D8c; (3) 5.10 era and flagged-fit aggregation; (4) 5.10 threshold +/-0.05; (5) 5.10 LEGACY delay; (6) A18 rerun; (7) 5.10 seeds; (8) 5.10 RAW sensitivity pool; (9) grids 5 (reference) and 15 min; (10) 1-min grid without the HSMM; (11) 1-min HSMM (rule 3h). Every unit checkpointed; a crash resumes; a guard refusal or a reproduction mismatch stops.
5b. Preflight on the contaminated folds only (RAW 3, LEGACY 29) for every data phase (unit tests; D8c on the RAW era; thresholds, delay, A18, seeds, RAW pool and grids units), written only to `section5/results/a22_preflight/`. The user launches.
5c. No protocol re-freeze (A22 is not integrated, as A17-A21); no 5.12 freeze; no era calibration.

## Governs

`section5/s5_a22.py`, `section5/s5_d8c.py`, their tests and `section5/run_a22_overnight.ps1`; results under `section5/results/a22/`, `section5/results/mr2/a18/` and `section5/results/d8/d8c_results.json`.
