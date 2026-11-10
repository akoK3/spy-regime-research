# Amendment A31 (Section 6: placebo exclusion from past alarms only; H4a sample = every calm-state streak start; placebo-filter null control)

Dated 2026-11-10T05:30:00+00:00 UTC (2026-11-10T00:30:00-05:00 New York). Status: DRAFT (revised 2026-11-10T06:05:00Z to the user's pre-approved specification; adopted when the rule 4 synthetic checks pass), awaiting adoption. Written before its code.
- The first draft (ledger row of 05:30Z) is superseded where it differs. Its unit-side alarm exclusion and its fake-unit null control are dropped. Its label-independent H4a placebos are kept, as part of rule 2.
- No Section 6 development result exists. The power run stopped on 2026-11-09 at 23:17 New York wrote no result file, and none of its outputs has been opened.
- Requested by the user on 2026-11-10 after `FABLE_AUDIT.md` findings M5, L1 and L10, with the specification: "a. Placebo exclusion may use only SPY alarms that occurred BEFORE the placebo time; never future alarms. b. H4a sample: every streak start S in a calm state, regardless of later outcome; label assigned afterward. c. New null control: compare filtered placebos vs fully unfiltered random times on the H3 outcome; flag if they differ beyond bootstrap tolerance."
- There is no A30 in the repository; this amendment is numbered A31 as the user asked.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `FABLE_AUDIT.md` (M5, L1, L10) | `005129986659b5827f94bf491f4120ae19db3ec674d25d78b50974f2ecc7db57` |
| `AMENDMENT_A28.md` (ADOPTED; rules 1d, 4b, 7d) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A29.md` (DRAFT; H4 statistic) | `1bcb5ee1df4b08e0a6488a7450f521f729bc1b1970240f85d803add5bc16e2f7` |
| `section5/s5_break_export.py` (`old_state` = the detector's reference state at S) | `b2956c2d813465ea829bdb2b6131ead9866a0376df5f674affd8f56609287ec3` |

## Rule 1: placebo exclusion uses past alarms only (spec a; replaces the alarm clause of A28 1d for H3 and H4; H2 unchanged)

1a. A placebo's time is T_p = S_p + gap, where gap is that of its matched unit (rule 2b sets gap = 0 for H4a).
1b. A placebo is excluded when a confirmed SPY alarm of its session has T_c in [T_p - 60, T_p), the 60 minutes BEFORE the placebo time. Alarms at or after T_p are never used.
1c. The other A28 1d conditions are unchanged:
  - same era;
  - a session before the unit's session;
  - the same 30-minute slot of S;
  - the same SPY prior-hour-RV decile, with cut points from earlier sessions;
  - T_p <= 390;
  - 20 placebos per unit.

## Rule 2: H4a sample (spec b; replaces A28 4b's unit definition and L10's post-S direction filter)

2a. **Units.** Every streak start S at which the detector is in a calm state, whatever happens later: confirmed, fizzled, or still open at the session close.
  - "Calm state" (HMM / HSMM): the detector's reference state at S is the lowest-variance state. That is the break export's `old_state` = 0; states are ordered by the variance of the 5-minute return.
  - BOCPD has no states. H4a is not defined for it and is reported as not evaluable in the rule 7a detector-dependence analysis.
  - The 60-session burn-in (A28 1g) applies.
2b. **Label.** Assigned afterward: 1 if the streak confirms, 0 otherwise (a fizzle, or open at the close).
  - The label plays no part in drawing the unit's placebos. They are drawn with gap = 0 for every H4a unit, so the placebo pool and the 90th-percentile cutoffs in C(S) do not depend on the label (FABLE_AUDIT L1).
2c. H3 and H4b keep their A28 units: confirmed calm-to-stressed breaks, with the direction at T_c, which is known at their decision time T.

## Rule 3: placebo-filter null control (spec c; added to A28 7d, whose parts (i) and (ii) are unchanged)

3a. **Two sets per H3 unit.**
  - (i) Its filtered placebos: rule 1, the placebos H3 uses.
  - (ii) 20 fully unfiltered random times: SPY update times drawn uniformly from the same era's sessions before the unit's session, with T = S + gap <= 390 and no slot, decile or alarm condition.
3b. Per asset, the H3 next-day regression (A28 3b controls) compares the two sets: an indicator for filtered (1) versus unfiltered (0), and its coefficient delta.
3c. **Tolerance.** The two-sided 95% basic week-block bootstrap interval for delta (A28 3c blocks, within era, 9,999 resamples). The control is flagged for an asset when the interval excludes 0.
3d. A flag is reported with its delta and interval beside the H3 result for that asset. It means the placebo construction, not the break, moves the H3 outcome beyond tolerance; that asset's H3 result is then read with that caveat. A flag does not stop the run. It is a check, not a test, and is outside Holm and BH.

## Rule 4: synthetic checks before adoption (must pass)

4a. **Runs.** The A29 synthetic design with rules 1-3 in force, at 999 resamples:
  - no-effect generators ("indep", "vol"), 200 replicates each;
  - planted H3 and planted H4, 40 replicates each.
  The synthetic runs include streaks still open at the close.
4b. **Accepted when all hold:**
  - under each no-effect generator, every one of the six primary tests rejects at 0.05 in at most 8.1% of replicates;
  - under each no-effect generator, the rule 3 control flags each asset in at most 8.1% of replicates;
  - planted H4a and H4b are within two standard errors of their targets (A29 2c) and rejected in at least 80% of replicates;
  - planted H3 (TLT, HYG, gold) is within the larger of two standard errors and 10% of its target; TLT and gold are rejected in at least 80% of replicates.
4c. If any of these fails, work stops and the user is told.

## Rule 5: order

5a. A31 is hashed into the ledger before its code.
5b. Adoption, when the rule 4 checks pass:
  - the status line is changed;
  - the sidecar is written;
  - a ledger row is added citing the check;
  - the ledger tests are run.
5c. The Section 6 development run refuses to start unless A28, A29 and A31 are ADOPTED and equal their sidecars (`s6_run.a29_guard`). A31 is in the freeze manifest.
5d. The A29 1f power rerun uses rule 2 for the H4a counts.

## Governs

Placebo eligibility for H3 and H4, the H4a sample and label, and the placebo-filter null control with its synthetic check. H2's pre-registered placebo distribution is unchanged. A28 and A29 are otherwise unchanged, and every Section 5 result is unchanged. No freeze, no O8, no era calibration under this amendment.
