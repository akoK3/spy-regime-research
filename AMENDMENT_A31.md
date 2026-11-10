# Amendment A31 (Section 6: causal placebo eligibility; label-independent H4a placebos and direction; a null control that can detect placebo asymmetry)

Dated 2026-11-10T05:30:00+00:00 UTC (2026-11-10T00:30:00-05:00 New York). Status: DRAFT, awaiting the user's approval. Written before its code. No Section 6 development result exists; the development run and the power check have not run with any outcome (the power run stopped on 2026-11-09 at 23:17 New York wrote no result file, and none of its outputs has been opened). Requested by the user on 2026-11-10 after `FABLE_AUDIT.md` findings M5, L1 and L10. There is no A30 in the repository; this amendment is numbered A31 as the user asked.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `FABLE_AUDIT.md` (M5, L1, L10) | `005129986659b5827f94bf491f4120ae19db3ec674d25d78b50974f2ecc7db57` |
| `AMENDMENT_A28.md` (ADOPTED; rules 1d, 4a, 4b, 7d) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A29.md` (DRAFT; H4 statistic) | `1bcb5ee1df4b08e0a6488a7450f521f729bc1b1970240f85d803add5bc16e2f7` |
| `section6/s6_lib.py` (`draw_placebos`: the future-alarm filter) | `0eb3b2d743dbb85ab9cb56fb6e04874419da74cd6b7fdce2ffc00cf98e008601` |
| `section6/s6_run.py` (units, gap, H4a filter, null control) | `bd3f8aa36e7d8fe5525123d94b53894cdcb875d99f42e5f2f056075c690ee187` |
| `section5/s5_break_export.py` (direction from the run's last update) | `b2956c2d813465ea829bdb2b6131ead9866a0376df5f674affd8f56609287ec3` |

**What the audit found.**
- **M5:** A28 1d makes a placebo eligible only if no confirmed SPY alarm lies within 60 minutes of its S or of S + gap, in either direction. Alarms after the placebo's own decision time are future information. They guarantee the placebo arm a SPY-quiet next hour, which the break arm by definition does not have.
  - The A28 7d null control draws its fake breaks with the same filtered rule. Both of its arms carry the same conditioning, so it cannot show the asymmetry.
- **L1:** H4a placebos carry the unit's gap: 10 for confirmed runs, 0 for fizzles. So eligibility, and with it the 90th-percentile cutoff in C(S), depends on the label.
- **L10:** H4a keeps calm-to-stressed runs, with the direction taken from the run's last update. That is T_c for confirmed runs and the fizzling update for fizzles, both after S.

## Rule 1: causal placebo eligibility for H3 and H4 (replaces the alarm clause of A28 1d; H2 unchanged)

1a. **Decision time.** A placebo's decision time is T_p = S_p + gap, where gap is that of its matched unit (rule 2a sets gap = 0 for H4a).
  A placebo is eligible only on information available at T_p:
  - same era;
  - a session before the unit's session;
  - the same 30-minute slot of S;
  - the same SPY prior-hour-RV decile, with cut points from earlier sessions (A28 1d);
  - T_p <= 390, a schedule condition known in advance;
  - no confirmed SPY alarm with T_c in (T_p - 60, T_p] of that session.
  Alarms after T_p, and any later detector state, are not used.
1b. **Symmetry.** The past-hour condition of 1a applies to the units as well. A break (H3, H4b) whose T, or a run (H4a) whose S, lies within the 60 minutes after an earlier confirmed alarm of the same session is excluded from H3 and H4. With the 30-minute refractory period this can happen 30 to 60 minutes after an alarm. Removals are counted per era (A28 6h).
1c. **Comparison with A28.** H3 and H4 are also run under the A28 1d rule (future filter), labelled "secondary: A28 placebo rule, retained for comparison" and BH-adjusted under A28 5c. The difference between the two rules is reported per test.

## Rule 2: H4a without label-dependent filters

2a. **One placebo pool for both classes.** H4a placebos are drawn with gap = 0 for confirmed and fizzled runs alike, so T_p = S_p. C(S) uses only (S - 15, S] (A28 4a), so the gap plays no role in the score. The pool, and the 90th-percentile cutoffs, are the same for both classes. H3 and H4b keep the unit's gap, since all their units are confirmed.
2b. **Direction at S.** H4a selects runs by their direction at S, from filtered probabilities at the run's first update above threshold:
  - HMM / HSMM: calm-to-stressed if the most likely state at that update has a higher variance index than the old state;
  - BOCPD: calm-to-stressed if the predictive variance at that update exceeds the one at the update before.
  The break export adds a field `direction_at_S`. Its rerun must still reproduce the MR2 alarm records exactly in every fold (exit 4 otherwise). H3 and H4b keep the A28 direction at T_c, which is known at their decision time T.

## Rule 3: a null control that can detect placebo asymmetry (replaces A28 7d(ii); 7d(i) unchanged)

3a. **Fake units.** Each null set replaces every real unit with one fake unit, drawn from the SPY update times by the unit-side rule only:
  - same era, slot and decile as the real unit, from earlier sessions;
  - the past-hour condition of 1b;
  - no condition on later alarms.
  Each fake unit then gets placebos by the rule in force (rule 1). Fake units and placebos are drawn from the same population on the same information, so any asymmetry in placebo selection shows as excess rejection.
3b. **The control must be able to see the problem.** The same fake units are also matched with A28-rule placebos (future filter), and those rejection rates are reported beside the rule 1 rates. An excess under the A28 rule and none under rule 1 shows the asymmetry and its removal. No excess under either says the asymmetry is immaterial in these data.
3c. **Pass rule (as A28 7d).** 200 sets. Under the rule in force, the rejection rate at 0.05 must be at most 0.10 for each primary test and for H3 rest-of-day. A failure stops the work before the joint evaluation and is reported.

## Rule 4: synthetic acceptance check before adoption

4a. **Generator.** The A29 synthetic generator is extended with the mechanism of M5: common intraday volatility bursts that raise SPY's volatility, and so trigger SPY runs and alarms, and the assets' volatility within the same hour and, through persistence, the next day. There is no break-specific asset response.
4b. **Runs, at 999 resamples.** The rule 3 null control and the A29 null scenarios are run under rule 1 and under the A28 rule, 200 replicates each. Planted H3 and H4 effects are run under rule 1, 40 replicates each.
4c. **Accepted when:**
  - under rule 1, rejection at 0.05 is at most 0.081 for each of the six primary tests and for H3 rest-of-day;
  - planted effects are recovered within two standard errors of their targets (A29 rule 2c);
  - the rule 3 control shows a larger rejection rate under the A28 rule than under rule 1 when the mechanism is present.
  If the third point fails, the control cannot detect the asymmetry. Work then stops and the user decides.

## Rule 5: order

5a. A31 is hashed into the ledger before its code. Code follows the user's approval of this text. Adoption follows a passing rule 4 check.
5b. The Section 6 development run refuses to start unless A28, A29 and A31 are all ADOPTED and equal their sidecars. This is already enforced in `s6_run.a29_guard`, and A31 is in the freeze manifest.
5c. The A29 1f power rerun follows A31's adoption, because rule 2b changes the H4a unit counts.

## Governs

Placebo eligibility for H3 and H4, the H4a unit and placebo definitions, the Section 6 null control, and its synthetic acceptance check. H2's pre-registered placebo distribution is unchanged. A28 and A29 are otherwise unchanged. Every Section 5 result is unchanged. No freeze, no O8, no era calibration under this amendment.
