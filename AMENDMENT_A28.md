# Amendment A28 (Section 6 cross-asset study: H2 unchanged; H3 tripwire and H4 confirmation as co-primary families)

Dated 2026-11-09T17:00:00+00:00 UTC (2026-11-09T12:00:00-05:00 New York). Status: DRAFT, pending the user's approval; becomes ADOPTED only when the user approves and it is committed with its hash sidecar, its ledger row and the status line changed. Written before any Section 6 code, before any cross-asset coverage check and before any Section 6 result exists. Decided by the user on 2026-11-09; it carries out A26 rule 3b (H3 by its own amendment). Disclosed: no cross-asset return, volatility or coverage of TLT, HYG, XAUUSD or DOLLARIDX has been computed in Section 5; the Section 2-3 data audits (availability, missingness, vendor forensics) have been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (FROZEN through A20; H2 in 5.0, Holm in 5.11) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A26.md` (ADOPTED; rule 1 labels, rule 3b) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |

Section 4 limitation 40 (`SECTION4_COMPLETE.md`): "Later cross-asset timing must report legacy -1/0/+1 minute scenarios; primary clock remains conditional". Cold audit 2 findings 12 (block bootstrap crosses the era boundary) and 14 (feature caches keyed by column name only), both open (`COLD_AUDIT_STATUS.md`).

## Rule 1: definitions

1a. Assets: TLT, HYG, gold (XAUUSD, Dukascopy mid quote) and USD (DOLLARIDX, Dukascopy mid quote). Volatility is measured on NYSE regular trading hours (RTH, 09:30-16:00 ET) for every asset, from 1-minute log returns (sum of squares).
1b. Breaks: confirmed calm-to-stressed SPY alarms (entry into the higher-variance state) of the primary detector at its Section 6 threshold (A6 item 3, A7: 0.2 confirmed alarms per session on the fold's real validation sessions), with the main event rule (A27 does not change it). Primary detector: the H2 detector chosen at the 5.12 freeze; H3 and H4 use the same detector. The other detectors are secondary (rule 7a). Stressed-to-calm breaks are secondary.
1c. Times: S = availability time of the first update of the confirming run (T_d); T = 0 at confirmation (T_c, availability time). Every quantity at a prediction time t uses only data available at t.
1d. Placebos as H2: times matched on time-of-day slot, era and SPY volatility decile, drawn from the same split and more than 60 minutes from any confirmed alarm; each placebo carries the S-to-T gap of its matched break. 20 placebos per break for the H3 and H4 models; 10,000 draws for H2 as frozen.
1e. Availability: HYG and gold from 2007-04-11, USD from 2017-12-01, TLT throughout. Per-asset tests use the years where the asset is available. A session counts as available for an asset when the label-free coverage check (rule 6b) passes it.
1f. Periods: development = the test segments of the uncontaminated folds; joint evaluation = the 5.13 evaluation periods, every result labelled "adaptive/exploratory (previously exposed period)" (A26 rule 1d).

## Rule 2: H2 unchanged

H2 as stated in `SECTION5_PROTOCOL.md` 5.0, with S1, S2, E1 and E2, and its own Holm family across the 4 assets (5.11). Nothing in A28 changes it.

## Rule 3: H3, tripwire (co-primary)

3a. Question: after calm-to-stressed SPY breaks, is each asset's next-day RTH realised volatility higher than after matched placebo times, beyond the asset's own history? Primary outcome: log RV of the next RTH session. Secondary: log RV from T to 16:00 the same day (rest-of-day), only when at least 30 minutes remain.
3b. Per asset a and outcome y: OLS of y on the asset's own controls known at T (log RV of the prior hour, log RV of the prior RTH session, own return from S to T and its absolute value), estimated on breaks and placebos together; then the same model plus the break indicator. Statistic: the break coefficient gamma; H0 gamma <= 0, one-sided.
3c. p-value: week-block bootstrap (calendar weeks, blocks never cross the era boundary: the cold audit 2 finding 12 fix), 9,999 resamples, centred, add-one. The primary p-value of each asset is that of the next-day outcome.
3d. H3 is the tripwire: it asks whether a cross-asset response exists at all and is reported first. It does not gate H4; both are in one Holm (rule 5).

## Rule 4: H4, confirmation (co-primary)

4a. Confirmation score C(t): the share of available assets (at least 2) whose absolute own return over the window up to t exceeds the 90th percentile of the same quantity over that break's matched placebos. Windows: at S, the 15 minutes before S; at T = 0 and T + 15, from S to t.
4b. H4a (primary), at S: confirm versus fizzle. Units: SPY runs whose first update crosses the threshold at S, labelled by whether the run confirms or resets (fizzles).
4c. H4b (primary), at T = 0: real versus false break. Secondary: the same comparison at S and at T + 15.
4d. Real break: the next RTH session's deseasonalised SPY RV is above the 80th percentile of the deseasonalised RV of the prior 20 sessions. Deseasonalised RV of a session = the mean over its RTH minutes of r² divided by the causal 20-session slot median of r² (the `__sadj` construction; minutes with an undefined slot median are left out), times 390. Secondary 5-day label: the mean deseasonalised RV of the next 5 sessions, same rule. Sensitivity: the 70th and 90th percentiles.
4e. Each H4 test: logistic model of the label on SPY's own information at t (SPY return from S to t, log RV of the prior hour) versus the same model plus C(t); statistic: the gain in AUC; H0 gain <= 0, one-sided; p from the week-block bootstrap of 3c.
4f. Confirmation status is unknown at S. The comparison is retrospective: labels use information after t, and H4 does not claim a real-time classifier.
4g. Descriptive: the curve of C(t) and of each asset's mean absolute return, break minus placebo, at every 5-minute step from S to T + 15.

## Rule 5: multiple testing

5a. H2: its own Holm family across the 4 assets, unchanged.
5b. Primary Holm family, 6 tests: H3 next-day for TLT, HYG, gold and USD; H4a (confirm versus fizzle at S); H4b (real versus false at T = 0).
5c. Everything else is secondary, BH-adjusted and labelled "secondary": H3 rest-of-day; H4 at S and T + 15; the 5-day label; the 70th and 90th percentile labels; stressed-to-calm breaks; the 2007+ sensitivity (rule 7f); and the analyses of rule 7.

## Rule 6: order and integrity

6a. A28 is hashed (sidecar) before any cross-asset coverage check.
6b. Coverage check, label-free: per asset and RTH session, the share of minutes with a usable price, stale-quote and zero-return shares, and gaps, computed without break times, alarms or outcomes. It fixes the per-asset available sessions (1e) before any result.
6c. A28 is adopted and frozen before any Section 6 development result is inspected.
6d. Power check from SPY break counts only: the numbers of breaks, fizzled runs and placebos and their calendar-week structure per period set the simulated sample; outcomes are simulated, and no asset outcome is read. Minimum detectable gamma (H3) and AUC gain (H4) at alpha 0.05 after the 6-test Holm, reported before the development results.
6e. Before the joint evaluation, the Section 6 code is fingerprinted (sha256 of every Section 6 script and the result-module code version). Any later change is reported as a deviation with its reason.
6f. Code: the cold audit 2 finding 12 fix (bootstrap blocks within era) and finding 14 fix (caches keyed by column name, feature-code hash and panel hash) are in new Section 6 code, outside `s5_lib`, `s5_run` and `s5_backend`. Code version `a0323ed24d68e896` must stay unchanged; if a fix needs a closure change, work stops and the user decides.

## Rule 7: further analyses (exploratory, descriptive)

7a. Detector dependence: H3 and H4 with each of the four families' breaks, and with T = 0 moved to S (alternative anchor).
7b. Footprint taxonomy (E1): the sign and size pattern of the four assets' responses per break, with Cieslak and Pang cited.
7c. Fed split: breaks with S inside [release, release + 60 min] on FOMC days versus all others.
7d. Sanity checks: (i) positive control: Fed breaks raise TLT rest-of-day RV above placebo; (ii) null control: 200 sets of random times drawn like placebos replace the breaks, and the H3 and H4 rejection rate at 0.05 must be at most 0.10. A failed sanity check stops the work before the joint evaluation and is reported.
7e. LEGACY timing (limitation 40): every LEGACY result also under SPY clock offsets -1 and +1 minute relative to the asset clocks; 0 is primary and conditional.
7f. 2007+ sensitivity: the 6 primary tests repeated on sessions from 2007-04-11 on, where TLT, HYG and gold are all available.

## Governs

The Section 6 hypotheses H3 and H4, their tests and multiplicity, the order of the Section 6 work, and the new Section 6 code. H2 and every Section 5 result are unchanged. No freeze, no era calibration under this amendment.
