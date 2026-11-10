# Amendment A33 (H2 primary restored to protocol 5.0; gaps filled minimally; A32's statistic becomes exploratory)

Dated 2026-11-10T21:40:40+00:00 UTC (2026-11-10T16:40:40-05:00 New York). Status: ADOPTED 2026-11-10T21:41:19Z (user pre-approval 2026-11-10: "Draft and adopt A33: H2 primary is exactly the protocol 5.0 H2"; the draft, sha256 c69960f637efbfaa..., is unchanged apart from this status line). Written before its code.
- **Requested and pre-approved by the user on 2026-11-10:**

  > Stop the H2 chain before the dev run starts (do not open any H2 dev output). Draft and adopt A33: H2 primary is exactly the protocol 5.0 H2 (signed cumulative return, T to T+30, 10,000 matched placebo draws, as pre-registered). Fill only gaps the protocol leaves open, minimally, and list each. A32's |return| statistic becomes secondary/exploratory, labeled as specified after seeing H3/H4/A30 dev results. E1 and detector dependence stay as in A32. Then code, unit tests, synthetic check, power, and H2 dev run on Gaussian and HSMM (TRAIN only), detached. Stop if any check fails.
- **The A32 chain is stopped.** It was stopped on 2026-11-10 at 16:39 New York, during its synthetic step.
  - No H2 power or development output exists.
  - The partial A32 synthetic file (`section6/results/h2_synth_reps_a32.jsonl`) was not opened.
- **The pre-registered text** (`SECTION5_PROTOCOL.md` 5.0): "H2 (primary): around confirmed calm-to-stressed SPY breaks, TLT/HYG/gold/USD cumulative return from T to T+30 lies outside a placebo distribution matched on time-of-day slot, era and SPY volatility decile (10,000 draws); horizons -30 and +5/15/30/60 min; stressed-to-calm is secondary. S1 ... S2 ... E1 ... E2 ..."
  - 5.11 adds: "Holm ... H2 across 4 assets. BH for secondary. Power: simulated minimum detectable effects."
  - A33 implements that text. Every choice the text does not fix is listed in rule 2 as a gap, filled with the least added structure.
- **Supersedes:** A32 rules 1-3 and 5 as H2's primary definition and gate. A32's statistic is kept as exploratory (rule 4). A32 rules 4a, 4b (as rule 5b here), 4c and 4d stand.
- **Disclosed: what had been seen.**
  - The H3, H4 and A30 development results and the A29 3b intervals had been seen.
  - No H2 statistic of either definition has been computed on real data.
  - The pre-registered H2 was written before any data were seen.
- No freeze, no O8, no era calibration.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (FROZEN; H2 in 5.0, Holm in 5.11) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A9.md` (item 2: H2 primary detector at 5.12) | `d915f7c90a38a0236a3962857235d7e1096b16f54065bb8104d3795ee4947bb0` |
| `AMENDMENT_A28.md` (1b breaks, 1c clock, 1d "H2 keeps its pre-registered placebo distribution (10,000 draws) exactly; the before-the-break rule does not apply to H2", 7a) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A32.md` (ADOPTED; superseded here as H2 primary) | `d222539ced84ceb2d4336d3c3c35f73bf57300fc82794f3694f8b7447c424c1b` |

## Rule 1: H2 primary (protocol 5.0, as pre-registered)

Per asset (TLT, HYG, gold, USD):
- the signed cumulative log return from T to T + 30 after confirmed calm-to-stressed SPY breaks;
- compared with a placebo distribution matched on time-of-day slot, era and SPY volatility decile, with 10,000 draws.

Holm across the 4 assets is H2's own family (5.11).

## Rule 2: gaps the protocol leaves open, each filled minimally

| # | Gap | Filled as |
|---|---|---|
| G1 | What "lies outside" is computed on, across many breaks | The statistic M is the mean over breaks of the signed cumulative return. Each of the 10,000 draws takes one matched placebo per break and computes the same mean. The draws form the placebo distribution of M. |
| G2 | Sidedness | "Outside" is two-sided: p = min(1, 2 min(P_lo, P_hi)), with P_lo = (1 + #{M_b <= M}) / 10,001 and P_hi = (1 + #{M_b >= M}) / 10,001. |
| G3 | Event time and window | T = T_c (A28 1b). The window is (T, T + 30] on the A28 1c availability clock: returns of minute indices T..T+29. LEGACY clock offset 0. |
| G4 | Breaks | Confirmed calm-to-stressed SPY alarms of the detector analysed (A28 1b). No burn-in: A28 1g exists for H3/H4's causal cut points, which H2 does not use. |
| G5 | Slot width and what is matched | The 30-minute slot of T (width approved 2026-11-09, ledger 03:42Z). The SPY prior-hour RV decile at T. The same era. |
| G6 | Placebo pool | Candidate times are the SPY update times (5-minute grid) of the era's sessions with detector output, excluding the break's own session. Earlier and later sessions both count: A28 1d says the before-the-break rule does not apply to H2. Decile cut points come from all candidate times of the era. No alarm exclusion: none is pre-registered (A31 rule 1 left H2 unchanged). |
| G7 | Draws | Uniform with replacement from each break's pool, independently per break and per draw. |
| G8 | Windows outside regular hours; missing data | A break with T + 30 > 390, or with the asset unavailable in its session (coverage rule), is not used for that asset. A candidate is used only if its window lies inside the session and the asset is available with data in it. A break with an empty pool is not used. Fewer than 5 breaks: not evaluable. |
| G9 | Holm when an asset is not evaluable | m = 4 always; a non-evaluable test enters with p = 1 (A15 rule 6a, as for H1 and H3/H4). |
| G10 | Status of the other horizons | Secondary (5.0 lists them; 5.11: BH for secondary): -30, meaning (T - 30, T], and +5, +15, +60, meaning (T, T + h]. Each is tested as in rules 1-2 with its own pool (window inside the session). Stressed-to-calm breaks at +30 are secondary (5.0). All are corrected by BH together with the S2 tests of rule 5b. |
| G11 | Power (5.11) | Simulated on each detector's break count. Per-break return = delta + e with e ~ N(0, 1); each break's pool is 200 N(0, 1) values. Two-sided test as G1-G2 with 10,000 draws at the first Holm step 0.05 / 4; 200 simulations per delta. The minimum detectable delta (power >= 0.80) is reported in SD units of a break's 30-minute return. |

**Disclosed limitation (not changed).** The placebo distribution treats breaks as independent. Breaks that share market-wide moves on the same day are not modelled. This is how the test was pre-registered.

## Rule 3: synthetic check (must pass before the development run)

3a. **Generator.** The Section 6 synthetic generator (`s6_synth_validation.gen_era`). Null "indep" and "vol": 200 replicates each. Planted ("vol"): 40 replicates.
3b. **Planted effect.** In every confirmed calm-to-stressed break, each available asset's one-minute returns in (T, T + 30] are shifted by mu_a = c_a x sigma_a, where sigma_a is the generator's base one-minute SD.
  - c = +0.05 for TLT, -0.05 for HYG, +0.05 for gold, 0 for USD (a planted null).
  - Target: 30 x mu_a.
3c. **Accepted when all hold:**
  - under each null, each of the 4 primary tests rejects at 0.05 in at most 8.1% of replicates;
  - planted TLT, HYG and gold are within the larger of two standard errors and 10% of the target;
  - planted TLT and gold are rejected in at least 80% of replicates.
3d. If 3c fails, work stops and the user is told.

## Rule 4: A32's statistic, exploratory

- A32's deseasonalised |return| statistic (A32 rules 1-3; primary window +30; +5, +15, +60; descriptive -30) is computed and reported as **exploratory**: uncorrected (5.0: "exploratory uncorrected"), outside Holm and BH.
- It is labelled "specified after seeing the H3/H4/A30 development results".

## Rule 5: S1, S2, E1, E2 (as A32)

5a. **S1:** covered by H4a and A30 (A32 4a).
5b. **S2:** detector dependence as A32 4b, on the rule 1 statistic. The rule 1 test is run with every detector's breaks; the Holm verdicts are reported side by side; the other detectors' p-values join the G10 BH family.
5c. **E1:** footprint taxonomy exactly as A32 4c (descriptive).
5d. **E2:** deferred to future work (A32 4d).

## Rule 6: order

6a. A33 is hashed before its code and adopted on the user's pre-approval: status line, sidecar, ledger row, ledger tests.
6b. **Development run.**
  - Gaussian HMM and HSMM, development data only, detached.
  - It runs after rule 3 passes and power has run.
  - It refuses to start unless A28-A33 are ADOPTED and equal their sidecars.
  - Outputs are written once, with provenance.
6c. A33 is in the freeze manifest.

## Governs

H2's primary test and its gaps; the status of A32's statistic. H3, H4, A30, A31 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.
