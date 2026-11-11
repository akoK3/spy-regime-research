# Amendment A36 (evaluation path: one joint driver for the Section 5 5.13 run and the Section 6 analyses on the evaluation periods)

Dated 2026-11-11T01:11:23+00:00 UTC (2026-11-10T20:11:23-05:00 New York). Status: ADOPTED 2026-11-11T01:11:23Z (user pre-approval 2026-11-10: "A36 decisions, pre-approved unless you must deviate ... Adopt A36, add to the freeze manifest"; the draft, sha256 71c94e50499c3d08..., is unchanged apart from this status line). Written before its code.
- **Decided and pre-approved by the user on 2026-11-10 (New York):**

  > A36 decisions, pre-approved unless you must deviate:
  > 1. Evaluation-only tests (no pooling with development); combine the two evaluation eras as in development (era terms); report each era separately as secondary.
  > 2. Full analyses mirroring the dev run (primaries, secondaries, checks, descriptives), all with the A26 label.
  > 3. BOCPD included as secondary (detector dependence).
  > 4. Look-back: causal baselines and 20/60-session histories may use earlier sessions; placebo draws from evaluation sessions only.
  > 5. FOMC times: same sources and pipeline as development, extended to evaluation dates, built before any evaluation data is read.
  > 6. A36 covers one joint driver: Section 5 5.13 (H1 on evaluation, era calibration per A11, effect sizes with CIs, no confirmatory p) plus Section 6.
- **This replaces the first draft** (ledger row "Amendment A36 (DRAFT, not adopted)", sha256 `df44d1c0282fc3f6b5ed36cdd30a2b0d4d8e7518b443125b4333658d43779257`), whose choices were proposals. Where they differ, the decisions above govern: the look-back (rule 4) and the scope (rule 6).
- **Source.** `FABLE_REAUDIT.md` M2: no code computes anything on the evaluation periods, and the choices that arise only there were unspecified. The 5.12 freeze records the amendment list, so they are fixed here, before the freeze.
- **Disclosed: what had been seen.** Every Section 5 and Section 6 development result. No evaluation-period row has been read; no evaluation access log exists.
- No freeze, no O8, no era calibration. No evaluation-period data.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `FABLE_REAUDIT.md` (M2, M3, L8, L9) | `11cf11db13e41f9d811b31820b6d411903425425a40dfb6a106af0feb4b48a19` |
| `SECTION5_PROTOCOL.md` (FROZEN; 5.9, 5.12, 5.13) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A11.md` (item 1: era-level threshold; item 3: release times) | `297551fb2e58b1f84939e66a6b67104e4c71db6ad30bb2534a7fd5ac6235f97c` |
| `AMENDMENT_A12.md` (item 2: schedule times) | `dd90c6b22b85851c61e1a88be82d294ecd95d9f8893c2f246fd78278927ff96a` |
| `AMENDMENT_A26.md` (rule 1: label; evaluation periods; rule 1f) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `AMENDMENT_A28.md` (rules 1b, 1f, 1g, 6b, 6e, 7) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A31.md` (rule 1 placebos) | `1efd5a1f338b31c6f7459c8d328c854450eed6800052d2be261f83d240ef036f` |
| `AMENDMENT_A33.md` (H2 primary) | `f101adce416ed256499fe779f5c0152de4c26d6bfbd9324a7a2546ecf9506747` |
| `AMENDMENT_A34.md` (per-asset pools; label in code) | `a2c58b4560eba9320fd78564a5d7f39031c09f4825cca822d75c0d2ec9484faa` |
| `AMENDMENT_A35.md` (H4 p-value; rule 3 H3/H4 primary detector) | `bf84069e620e5b839c2f98b259b0740ef982b4a999a4f9252eb587808a21e1b3` |

## Rule 1: periods, label, combination (decision 1)

1a. **Periods.** LEGACY 2019-01-02 to 2022-03-04 and RAW 2025-01-02 to 2026-10-12 (A26 1c). Every result computed on them carries `a26_label` = "adaptive/exploratory (previously exposed period)" and `confirmatory` = false.
1b. **Evaluation-only.** Every statistic is computed on evaluation-period units alone. Development results are reported beside them and are never pooled into a statistic.
1c. **Combination.** The two evaluation eras are combined exactly as LEGACY and RAW are in the development run: one test over both, with every "within era" rule applied within each evaluation era (bootstrap week blocks, cross-validation folds, placebo matching, H2 pools).
1d. **Each era separately, secondary.** The H2 primary family and the six H3/H4 primary tests are also computed on each evaluation era alone. These are secondary: they join the BH family of their analysis and never enter Holm.
1e. **No embargo session is read.** The five sessions between each TRAIN span and its evaluation period (LEGACY 2018-12-24 to 2018-12-31, RAW 2024-12-24 to 2024-12-31) are read by nothing. Histories skip over them.

## Rule 2: analyses (decisions 2 and 3)

2a. **Section 6, mirrored from the development run with the same definitions:**
  - H2 (A33): primary family (Holm, m = 4), the secondary horizons, stressed-to-calm, detector dependence, the BH family; the exploratory A32 statistic; E1.
  - H3 and H4 (A28 with A29, A31, A35): the six primary tests (Holm, m = 6); the secondaries of A28 5c; the Fed split; the LEGACY clock offsets; the alternative anchor; detector dependence; the curve and taxonomy; the A29 3c diagnostic; the A31 rule 3 control and its descriptive variant; A30; the A28 7d sanity checks (200 null sets).
  - A34: the per-asset-pool parts.
2b. **Not repeated:** the 2007+ sensitivity (A28 7f). Every evaluation session is after 2007-04-11, so it equals the primary by construction; it is reported as identical and is not entered in BH a second time. Power and synthetic checks are not evaluation-period analyses.
2c. **Sanity checks on the evaluation periods are reported, not gates.** Nothing follows the evaluation, so a failed check there is stated beside the results.
2d. **Detectors.**
  - 5.13 fits all four families of the freeze (Gaussian HMM, Student-t HMM, HSMM, BOCPD).
  - H2 uses the H2 primary detector of the freeze (5.12, A9 item 2).
  - H3 and H4 use the detector of A28 1b as amended by A35 rule 3.
  - **BOCPD is secondary only:** it enters the detector-dependence analyses of H2, H3 and H4 and nothing else. H4a is not defined for it (A31 2a).
  - If the freeze names no H2 primary detector (no family passes H1), H2 is not evaluable and is reported so; H3 and H4 use the A28 1b fallback.

## Rule 3: FOMC release times for the evaluation periods (decision 5)

3a. **Dates.** Scheduled meetings with a statement, from the Federal Reserve pages by the D6 parsers: `fomchistorical{YEAR}.htm` for 2019 and 2020, `fomccalendars.htm` for 2021, 2022, 2025 and 2026. Dates outside the evaluation periods are dropped.
3b. **Times.** The order of evidence of A11 item 3 and A12 item 2: the statement page states the time; else the Fed's press-conference page states it; else, from 2013 on, 14:00, accepted only if every Fed page that states a time from 2013 on (development and evaluation pages together) states 14:00. Otherwise the meeting is excluded. No time is assumed.
3c. **Built first.** The list is written once, with a sidecar and a ledger row, before any evaluation-period row is read. The builder refuses if the evaluation access log shows an allowed read. The driver refuses to start without the list and its sidecar.
3d. **Uses.** H1(c) events: evaluation FOMC days with a time and a full 390-bar session. Section 6 Fed flag: S within the 60 minutes after the release on those days (A28 7c, 7d(i); A30 3c).

## Rule 4: look-back (decision 4)

4a. **Section 5 features.** The panel for an era is the TRAIN span followed by the evaluation span. The causal 20-session baselines of the deseasonalised target and of the `__sadj` features run across that boundary, so the first evaluation sessions use the last TRAIN sessions as history.
4b. **Section 6 histories.** Each evaluation era is preceded by the last 60 TRAIN sessions of its era as history. They serve only:
  - the 20-session causal medians (the deseasonalised RV behind the real-break label, A28 4d; the A32 measure);
  - the prior-day control of H3;
  - the 60-session burn-in count (A28 1g), which every evaluation unit therefore passes.
4c. **Evaluation sessions only** for everything that is drawn or matched: units, candidate times, placebo draws (H3, H4, A34), decile cut points, H2 pools, alarms used for the placebo exclusion. A history session is never a unit, a placebo or a candidate.
4d. Consequence of 4c: early evaluation breaks have few earlier candidates. A break with fewer than 10 earlier candidates has no cut points and no placebos, as in development.

## Rule 5: Section 5 5.13 on the evaluation periods (decision 6)

5a. **Entry.** One guarded run per era through `s5_eval_label.run_confirmatory_labelled` (frozen `s5_freeze.run_confirmatory` inside). Only frozen values are passed: the final setups and the era-level thresholds of the freeze.
5b. **Fit.** Per family, the frozen final setup (features, K or lambda) and the return-only baseline with its frozen parameters are fitted on every TRAIN session of the era, with the main run's fit (3 starts, seed 0). Preprocessing is fitted on TRAIN rows only. No retuning.
5c. **Thresholds (A11 item 1).**
  - Feature model: the era-level threshold stored in the freeze, used unchanged.
  - Baseline model: the freeze stores none. It is set by the same A11 rule on TRAIN data only (fit on sessions 0 to n - 64, 5 embargo sessions, the last 58 as calibration, A7 bisection to 0.2 alarms per session).
  - Reproduction: the feature threshold is recomputed by the same code path. A difference from the frozen value is reported as a deviation; the frozen value is still the one used.
5d. **H1(a).** Splices are built from the stable evaluation days with the main run's builders, seed and counts. Effect: pAUC(features) - pAUC(baseline). Fewer than 8 stable days: skipped, with the reason (A8 item 3).
5e. **H1(b).** Effect: mean QLIKE(baseline) - mean QLIKE(features) on the common decision bars of the evaluation sessions, and the same as a percentage of the baseline.
5f. **H1(c).** Hit rates of the two models in [release, release + 60 min] on the rule 3d events, their difference, and the reference alarm rates on non-FOMC evaluation sessions in the same clock window.
5g. **Effect sizes with intervals; no confirmatory p.** Each effect is reported per era and family with a 95% percentile interval from a day-cluster bootstrap (2,000 resamples, seed 513): stable days for (a), sessions for (b), events for (c). No p-value, no fold test, no Holm and no H1 verdict is computed on the evaluation periods. A confirmatory test needs a new period (A26 1f).
5h. **Break export.** For every family, every run of updates above the frozen feature threshold on the evaluation sessions is recorded with the fields of `s5_break_export` (kind, S, T_c, direction, old state), together with the sessions that have detector output. SPY only; no outcome. This is the Section 6 input.
5i. Output: `section5/results/evaluation_{ERA}.json`, labelled, one per era.

## Rule 6: Section 6 on the evaluation periods

6a. **Coverage first.** The label-free coverage check of A28 6b on the evaluation sessions, with the thresholds approved on 2026-11-09, before any break time or asset outcome is used there. Written once, labelled.
6b. **Inputs.** Breaks and sessions from the 5.13 outputs (rule 5h); asset returns through `s5_eval_loader.load_eval(..., section6=True)`; histories (rule 4b) through `load_development`.
6c. **Outputs.** `section6/results/s6_evaluation_{detector}.json`, `h2_evaluation_{detector}.json` and `a34_evaluation_{detector}.json`, written once, labelled, with provenance.

## Rule 7: order and guards

7a. Before the freeze: A36 adopted and in the freeze manifest; the driver, its unit tests and a synthetic end-to-end run of the whole path exist and pass. No test reads an evaluation-period row.
7b. After the freeze (which includes the era calibration and its lock): the rule 3 list exists; the Section 6 fingerprint (A28 6e) is written and now also covers the Section 5 helpers of this path; then the driver runs 5.13 for both eras, the evaluation coverage, and the Section 6 analyses, in that order.
7c. **The fingerprint is compared with the code.** A Section 6 evaluation read is refused when any fingerprinted file differs from the fingerprint (re-audit L9). The driver also checks this before 5.13.
7d. Every evaluation read goes through `s5_eval_loader` (guard, access log). The Section 5 panel read of rule 4a is authorised and logged by the same guard before the evaluation span is opened.

## Governs

The evaluation-period path of H1, H2, H3 and H4. Every development result, the freeze rule for the H2 primary detector, and the frozen closure (code version a0323ed24d68e896) are unchanged. No freeze, no O8, no era calibration under this amendment.
