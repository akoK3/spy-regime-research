# Amendment A30 (Section 6: lead-lag description of the cross-asset response around calm-to-stressed breaks)

Dated 2026-11-10T15:02:30+00:00 UTC (2026-11-10T10:02:30-05:00 New York). Status: ADOPTED 2026-11-10T15:02:50Z (user pre-approval 2026-11-10: "Write and adopt A30, pre-approved as specified"; the draft, sha256 8e68c36c91556029..., is unchanged apart from this status line). Written before its code.
- Requested and pre-approved by the user on 2026-11-10: "Write and adopt A30, pre-approved as specified (descriptive, secondary, no Holm): for each calm-to-stressed break, the first 5-min bar in [S-30min, T+60min] where each asset's |return| exceeds its placebo 90th pct; report distributions of that time relative to S and T=0 per asset, share of breaks where SPY's S comes first, and Fed/non-Fed split. Regular hours only; skip windows crossing the close."
- No Section 6 development result exists. No cross-asset lead-lag quantity has been computed.
- Numbered A30, after A31, as the user asked.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A28.md` (ADOPTED; units 1, clock 1c, placebos 1d, Fed flag, availability) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A31.md` (DRAFT, rule 3 revised; rule 1 placebo exclusion) | its rule 3 revision is in the ledger rows of 2026-11-10 (about 15:01Z) |

## Rule 1: units and window

1a. **Units.** The H3 units: confirmed calm-to-stressed breaks of the detector analysed, burn-in passed (A28 1g). S is the streak start and T = T_c (T = 0 in the A28 notation) the confirmation time, both in minutes after 09:30 on the SPY clock (A28 1c).
1b. **Window.** [S - 30, T + 60], regular hours only. A break whose window starts before 09:30 (S - 30 < 0) or crosses the close (T + 60 > 390) is skipped and counted as skipped.
1c. **Bars.** Consecutive 5-minute bars aligned to S: bar k covers (S - 30 + 5(k - 1), S - 30 + 5k], for every bar ending at or before T + 60. A bar's time is its end.
1d. LEGACY clock offset 0 (the rule 7e offsets are not applied here).

## Rule 2: first exceedance per asset

2a. For each asset (TLT, HYG, gold, dollar index) available that session (coverage rule), the bar's |cumulative log return|.
2b. **Reference.** The same bar, relative to S, at each of the unit's placebos (the H3 placebos: A28 1d with A31 rule 1), where the placebo's bar lies within the session. The cutoff is the 90th percentile of the available placebo values. A bar with fewer than 10 placebo values is not evaluable.
2c. **First exceedance** t_a: the time of the first evaluable bar whose value exceeds the cutoff. A break with no exceedance in the window is counted as "none".

## Rule 3: reports (descriptive, secondary)

3a. Per asset:
  - number of breaks evaluated, skipped (rule 1b), unavailable, and with an exceedance;
  - distribution of t_a - S and of t_a - T among breaks with an exceedance: mean, 10th, 25th, 50th, 75th and 90th percentiles, and counts per bar.
3b. **SPY first.** Per asset, the share of breaks where SPY's S comes first: t_a > S, or no exceedance. A bar ending at or before S counts as the asset first. Across assets, the share of breaks where S comes first for every available asset.
3c. **Fed / non-Fed.** Every quantity of 3a and 3b is also reported for Fed breaks and non-Fed breaks separately (the A28 Fed flag: S within the 60 minutes after an H1(c) release).
3d. **Chance reference (descriptive).** Each of a break's placebos is put through rules 1-2 against the unit's other placebos, so the same quantities are reported for the placebos. A 90th-percentile exceedance somewhere in a window of 18 or more bars is common by chance; the reference shows how common.

## Rule 4: status

4a. Descriptive and secondary. No test, no p-value, no interval; outside Holm (A28 5b) and BH. It never stops a run.
4b. Computed inside the Section 6 development run (`s6_run.analyse`, key `a30_lead_lag`) for the detector analysed (Gaussian HMM and HSMM), on the development data only (TRAIN-span test segments of the uncontaminated folds). It is not part of the A31 rule 4 synthetic acceptance.

## Rule 5: order

5a. A30 is hashed into the ledger before its code.
5b. Adopted on the user's pre-approval: status line changed, sidecar written, ledger row, ledger tests.
5c. A30 is in the freeze manifest. The development run refuses to start unless A28, A29, A30 and A31 are ADOPTED and equal their sidecars.

## Governs

The lead-lag description of the cross-asset response around calm-to-stressed breaks. A28, A29, A31, H2 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.
