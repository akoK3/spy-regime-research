# Amendment A21 (D7 data-validity exclusion of undefined variance ratios; D7 rerun on MR2; Step 2 for liquidity)

Dated 2026-11-07T07:31:00+00:00 UTC (2026-11-07T02:31:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before any code it governs. Decided by the user after the MR2 D7 result (gate (i) failed for trend, momentum and jumps). Disclosed: rule 1 is decided after that gate failure, with the MR2 D7 outcomes of every day (including the excluded days) already seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A19.md` | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` |
| `AMENDMENT_A19_3.md` | `7269d2cb5034cec52e9f42a006e26f93e7662825c3a89f065df4553735a8f7e2` |
| `AMENDMENT_A20.md` | `828e14b7d8b3445eb499fdcd7a32e1e0a5bd41dfc80b5d3224186c6a85481160` |
| `section5/s5_d7.py` (before A21) | `36d9cc1f6106a2cfbb830b7c7fb2146e329d2c82d4c79b4674812db07a29bb35` |
| `section5/results/main_run_2/run_complete.json` (MR2) | `19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a` |
| `section5/results/mr2/a17/a17_results.json` | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/results/mr2/d7/d7_results.json` (MR2 D7, before A21) | `c1ca6f1c3ffd987f958adae993da925c0eea710549991d2b7a9d1944d01a87fa` |
| `section5/results/d8/d8_results.json` | `540bfb5c924600811a7ac19a91c1bef64958eaf0c77b1080f74a7b2b8a0a7098` |

## Finding that motivates rule 1

MR2 D7 (305 days): gate (i) share 0.846 for trend, momentum and jumps. All 47 failing days are LEGACY days whose variance ratio is NaN (S0, the weighted sum of squared returns over the 60 bars after tau, is NaN); every finite ratio is 1.000. The jump injection logged these days as "window variance zero", which is wrong (the value is undefined, not zero). Liquidity's ratio is 1 by construction. The cause of the NaN was not diagnosed (the data backend serves only RAW 3 and LEGACY 29 for diagnostics, and neither has such a day).

## Rule

1. Data validity (D7): a stable test day on which the realised variance ratio of ANY injection is undefined (NaN) is excluded from ALL D7 types, from the matched null and from both positive controls; it is listed in the fold's `skipped` with the reason "undefined variance ratio (A21)". Gate (i) is computed on the remaining days. The check runs before any detector sees the day. The jump-injection label distinguishes "window variance undefined (NaN)" from "window variance zero".
2. D7 rerun on the MR2 fits (A17-style saved models and thresholds, unchanged) with rule 1, into `section5/results/mr2/d7_a21/`. Everything else per A19 to A19.3. The first MR2 D7 (`section5/results/mr2/d7/`) is kept unchanged as a record and is superseded.
3. Step 2 for liquidity (A19 rule 3), triggered by the MR2 D7 verdict (liquidity missed, D8 occurs). If the rule-2 rerun changes the liquidity verdict, both are reported; Step 2 still runs (decided now).
   a. Families: Gaussian HMM, Student-t HMM, HSMM, BOCPD. Folds: all 34.
   b. Pool: the A20 pool (13 columns), replacing A19 rule 3b's "primary 19" (A20 rule 1 applies to every detector input).
   c. Objective: QLIKE of a regime-conditional forecast of next-60-min deseasonalised volume from each decision bar (the 5.6 grid; bars at or before 15:00 by the 60-bar horizon). dvol = volume / median volume of the same slot over the previous 20 sessions (>= 10 finite; the D8 `adjust`). Target = (60 / n) * sum of dvol over the next 60 one-minute bars, n = finite terms >= 50, floor 1e-10 (= 60 x the mean dvol; QLIKE is unchanged by the constant because the regime forecasts are linear in the target). Selection otherwise exactly 5.8: greedy forward, 1% rule, at most 6 features, K/lambda tuning with 3 starts, the return-only baseline tuned identically on the same objective.
   d. Score (a), H1-style: per fold, test-segment liquidity QLIKE, baseline minus features on common decision bars, with Diebold-Mariano; fold tests as 5.9 (block bootstrap, Wilcoxon, sign consistency) on the 26 confirmatory folds and on all 34; Benjamini-Hochberg (q = 0.05) across the 4 families (the only triggered type); also the test QLIKE percent (median and pooled). No H1(a) (variance splices do not apply to a liquidity detector).
   e. Score (b), D7: the Step 2 fits on the 26 confirmatory folds, A7 fold-level thresholds per model (bisection to 0.2 alarms per session on validation), the same days, taus, injections, sweep scoring, null and A21 rule 1 as rule 2. Step 2 "responds to liquidity" per family = the feature model's sweep gain at the primary level (volume x2) >= 0.10 with the day-clustered CI excluding 0; volume x0.5 reported. Required gates: (i), (iii), (iv). Gate (ii) (variance positive control) is reported, not required: a liquidity detector is not meant to respond to variance.
   f. Secondary; not part of H1; does not change H1, the 5.8 setups or 5.12. Contamination category POST_MAIN_RUN.
4. Preflight on the contaminated folds only (RAW 3, LEGACY 29): the rule-2 D7 fold units (MR2 fits) and the full Step 2 unit (selection, score (a), thresholds, D7 unit) for all four families, plus unit tests. Both phases chained in one checkpointed unattended runner; launched by Claude (user instruction) only if every preflight passes, otherwise not launched and the failure written to `OVERNIGHT_STATUS.md`.
5. No protocol re-freeze (A21 is not integrated, as A17-A19); no 5.12 freeze; no era calibration.

## Governs

`section5/s5_d7.py` (rule 1), `section5/s5_mr2.py` (rule 2 stage), `section5/s5_step2.py`, its tests and runner; results under `section5/results/mr2/d7_a21/` and `section5/results/step2_liquidity/`.
