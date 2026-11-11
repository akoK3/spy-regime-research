# Amendment A32 (H2 specified: deseasonalised absolute cross-asset response after calm-to-stressed breaks; S1, S2, E1, E2)

Dated 2026-11-10T21:33:00+00:00 UTC (2026-11-10T16:33:00-05:00 New York). Status: ADOPTED 2026-11-10T21:32:49Z (user pre-approval 2026-11-10: "Draft and adopt A32 (H2), pre-approved as specified"; the draft, sha256 ee45753d96d752c7..., is unchanged apart from this status line). Written before its code.
- **Requested and pre-approved by the user on 2026-11-10:**

  > Draft and adopt A32 (H2), pre-approved as specified unless you must deviate:
  > - Statistic: per asset (TLT, HYG, gold, USD), mean deseasonalized |return| over [T, T+30] after calm-to-stressed breaks minus matched placebos; one-sided (breaks > placebos); mean across breaks; week-block bootstrap within era; Holm across the 4 assets as its own family.
  > - Placebos: A31 causal rule (past alarms only), matched on 30-min slot, era, SPY vol decile.
  > - Primary horizon T to T+30. Secondary (BH): +5, +15, +60. Descriptive: -30 to T.
  > - S1 = covered by H4a + A30; S2 = covered by A28 7a detector dependence; E1 = footprint taxonomy, descriptive: classify each break by its T+30 move pattern (flight to safety: TLT up and HYG down; credit stress: HYG down only; dollar-driven: USD up; SPY-only: none unusual), shares vs placebo shares; E2 (overnight gaps) deferred to future work, stated.
  > - Then: code, unit tests, synthetic check (null ~5%, planted recovered), power, then H2 dev run on Gaussian and HSMM (TRAIN only), detached. Stop if any check fails.
- **This changes H2.**
  - `SECTION5_PROTOCOL.md` 5.0 stated H2 as the signed cumulative return from T to T+30 against a placebo distribution of 10,000 draws.
  - A26 rule 3a and A28 rule 2 kept that text unchanged; A28 1d kept its placebo distribution.
  - A32 replaces the H2 statistic, its placebos and its S1, S2, E1 and E2 by the rules below. The H2 primary detector (A9 item 2, chosen at the 5.12 freeze), H2's own Holm family across the 4 assets (5.11) and the A26 label of every evaluation-period result are unchanged.
- **Disclosed: what had been seen when this was specified.**
  - The Section 6 development results of H3, H4 and A30 on the same development data had been seen:
    - `s6_development_gaussian_hmm.json` and `s6_development_hsmm.json`;
    - the A29 3b intervals.
  - A30 measured a related quantity: first exceedance of the placebo 90th percentile of 5-minute |return| in [S - 30, T + 60].
  - The H2 development run below is therefore not independent of results already seen. No H2 statistic as defined here has been computed.
- No freeze, no O8, no era calibration.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (FROZEN; H2 in 5.0, Holm in 5.11) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A26.md` (rule 3a: H2 unchanged; label) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `AMENDMENT_A28.md` (rules 1, 2, 3c, 7a) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A30.md` (lead-lag description) | `1c421aa7ced0c8748648e9fe5fc723fa14c606a67943001fc482372d3990b9da` |
| `AMENDMENT_A31.md` (rule 1: past alarms only) | `1efd5a1f338b31c6f7459c8d328c854450eed6800052d2be261f83d240ef036f` |
| `section6/results/s6_development_gaussian_hmm.json` (seen) | `831c8ec5972e8f39a6112b75e9c72b439c8a6f096c20ded26895518fe0a1207e` |
| `section6/results/s6_development_hsmm.json` (seen) | `504a22ebbfb48805b06630c171bda271b6fd719129642eb09f6a05833be02ba8` |

## Rule 1: units and placebos

1a. **Units.** Confirmed calm-to-stressed breaks of the detector analysed, burn-in passed (A28 1g): the H3 units. T = T_c, in minutes after 09:30 on the SPY clock (A28 1c). LEGACY clock offset 0.
1b. **Placebos.** The H3 placebos: A28 1d with A31 rule 1. That is:
  - same era;
  - a session before the break's session;
  - the same 30-minute slot of S;
  - the same SPY prior-hour-RV decile, with cut points from earlier sessions;
  - no confirmed alarm in the 60 minutes before the placebo time (past alarms only);
  - T_p = S_p + gap <= 390;
  - 20 per break.

  The pre-registered 10,000-draw distribution is replaced.

## Rule 2: measure

2a. **Windows** relative to T: W_h = (T, T + h] for h = 5, 15, 30, 60, and the descriptive window (T - 30, T]. For a placebo the same window is relative to T_p. A window must lie inside regular hours (0 <= start, end <= 390); otherwise it is not used.
2b. **Deseasonalised |return|** of asset a in window (t0, t1] of session s: d = |r| / sqrt(m).
  - r is the cumulative one-minute log return over the window.
  - m is the median, over the asset's previous 20 sessions of the era, of the realised variance over the same minute window (t0, t1]. Only sessions where the asset is available and the window has data count. At least 10 are required, else d is undefined.
  - m is causal: it uses earlier sessions only. It removes the time-of-day and slow volatility level of the asset.
2c. **Per-break contribution.** c = d(break) - mean of d over the break's placebos.
  - The asset must be available in the break's session (coverage rule), d(break) must be defined, and at least 10 placebo values are required; else the break is not used for that asset and window.

## Rule 3: tests

3a. **Statistic.** G(a, h) = the mean of c over the breaks used.
3b. **H2 primary.** h = 30, per asset (TLT, HYG, gold, USD).
  - H0: G <= 0, one-sided (breaks > placebos).
  - The p-value is the week-block bootstrap of A28 3c: within era, calendar-week blocks of the break's session; each break resampled together with its placebos; 9,999 resamples, centred, add-one.
  - **Holm across the 4 assets as H2's own family** (5.11). m = 4 always; a test that cannot be evaluated enters with p = 1 (A15 rule 6a).
3c. **Secondary.** h = 5, 15 and 60 per asset, tested the same way. They are corrected by BH together with the S2 tests of rule 4b, and labelled secondary.
3d. **Descriptive.** The window (T - 30, T] per asset: G with no p-value.

## Rule 4: S1, S2, E1, E2

4a. **S1** (return between T_d and T_c) is covered by H4a (A31 rule 2) and A30. No separate computation.
4b. **S2** (agreement across detectors) is covered by A28 7a detector dependence. The rule 3b statistic and p are computed for every detector of the break export: Gaussian HMM, Student-t HMM, HSMM and BOCPD, each on its own breaks and placebos.
  - Their p-values join the rule 3c BH family.
  - The Holm verdict per detector is reported side by side, as verdict agreement.
4c. **E1 footprint taxonomy (descriptive; Cieslak and Pang).** Each break with TLT and HYG available is classified by its move over (T, T + 30].
  - A move is unusual when its |r| exceeds the 90th percentile of the same asset's |r| over its placebos' windows (at least 10 values). Its sign is the sign of r. Gold and USD are unusual only if available; an unavailable asset counts as not unusual.
  - Categories, in this order:
    1. **flight to safety:** TLT up-unusual and HYG down-unusual;
    2. **credit stress:** HYG down-unusual, TLT not up-unusual;
    3. **dollar-driven:** USD up-unusual;
    4. **SPY-only:** no asset unusual;
    5. **other:** anything else.
  - **Shares for breaks** are reported against **placebo shares**: each placebo is classified the same way against the break's other placebos.
4d. **E2** (overnight gaps versus early-session breaks) is **deferred to future work** and not computed under this amendment.

## Rule 5: checks before the development run (must pass)

5a. **Synthetic check.**
  - The Section 6 synthetic generator (`s6_synth_validation.gen_era`): null "indep" and "vol", 200 replicates each; planted, 40 replicates; 999 resamples.
  - **Planted effect.** In every confirmed calm-to-stressed break (burn-in passed), the returns of each available asset in (T, T + 30] are multiplied by k_a: TLT 1.3, HYG 1.15, gold 1.3, USD 1.0 (USD is a planted null).
  - **Target per replicate:** (k_a - 1) times the mean d(break) of the same breaks before planting.
  - **Accepted when all hold:**
    - under each null generator, each of the 4 primary tests rejects at 0.05 in at most 8.1% of replicates;
    - planted TLT, HYG and gold are within the larger of two standard errors and 10% of their target;
    - planted TLT and gold are rejected in at least 80% of replicates.
5b. **Power.**
  - Per-break contributions are simulated on the real break structure of each detector: c = delta + u_week + e, with u_week ~ N(0, 0.3^2) and e ~ N(0, 1). This uses all breaks, an upper bound.
  - Tested at the first Holm step, 0.05 / 4; 200 simulations, 999 resamples.
  - The minimum detectable delta (power >= 0.80) is reported in units of the per-break SD.
5c. If 5a fails, work stops and the user is told. Power is reported, not a gate.

## Rule 6: development run and order

6a. A32 is hashed into the ledger before its code. It is adopted on the user's pre-approval:
  - the status line is changed;
  - the sidecar is written;
  - a ledger row is added;
  - the ledger tests are run.
6b. **H2 development run.**
  - Gaussian HMM and HSMM; development data only (the TRAIN-span test segments of the uncontaminated folds, through `s5_eval_loader.load_development`); run detached.
  - It refuses to start unless A28, A29, A30, A31 and A32 are ADOPTED and equal their sidecars.
  - Outputs are written once, with code hashes and the amendment manifest.
6c. A32 is in the freeze manifest. The H2 code is in `section6/`, so the Section 6 fingerprint covers it before any evaluation-period run.

## Governs

H2's statistic, placebos, horizons, tests and S1, S2, E1, E2, and the H2 checks and development run. H3, H4, A30 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.
