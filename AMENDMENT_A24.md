# Amendment A24 (LEGACY clock -1/0/+1 minute sensitivity; ledger open item 5)

Dated 2026-11-08T22:30:00+00:00 UTC (2026-11-08T17:30:00-05:00 New York). Status: ADOPTED 2026-11-08T23:05:00+00:00 UTC (user approval "A24: approved"; the draft, sidecar bdf1f0cb..., committed in 5e85e8e, is unchanged apart from this status line). Written before any code it governs and before any of its results exist. Numbered A24 because the user named the combined volume model A23; this amendment is the earlier item (4) of the Section 5 close-out and runs before the freeze. Disclosed: MR2, its A17-style phase, D7 (A21), Step 2 and all A22 results, including the A22 LEGACY delay +5/+10 min, have been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A22.md` | `3ce7b683a1369659b14b22c068bcc25c6a7b14a7a6b15758946c7050f8a15217` |
| `section5/results/main_run_2/run_complete.json` (MR2) | `19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a` |
| `section5/results/mr2/a17/a17_results.json` (MR2 alarms, H1(c)) | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/results/a22/thresholds.json` (alarms at targets 0.15 / 0.25) | `42edd9d065e5aec4905c3855cd1bab107c4930ca29b11a94d8db3086addc0f09` |
| `section5/results/contamination_list.json` (98 H1(c) events, release minutes) | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/results/h1c_schedule_times.json` | `053f7372d1c560ce2205f8d72be8295f4db83ad002a1894749946a7d16047957` |
| `section5/s5_a22.py` (h1c with per-fold shifts) | `b65494aa1b7cc9fbbb6c7ba3136e9552484a8a82b06c269d33c72477021ee1ba` |

Source of the item: ledger rows 8, 19, 40 and 41 (Section 4.3 closing report and addendum). The frozen 4.3 protocol inherits the minute-start assumption (bar stamped t holds minute [t, t+1), available at t + 60 s) and requires that later timing work report LEGACY -1/0/+1 minute scenarios; RAW has no clock test; nothing in the repository checks the bar label against an independent clock.

## Rule 1: what a clock offset can change (fixed now)

1a. A LEGACY clock offset c moves every LEGACY bar (returns, features, volume, availability) together, so it changes nothing measured on the data's own clock: the 5.8 setups, H1(a) (splices, tau, alarms and the 60-minute hit window are all on the data clock), H1(b) (targets and forecasts on the same bars), D7, D8 and the A7 thresholds are invariant to c by construction. They are not recomputed; this is stated in the result.
1b. Only comparisons with an external clock change. In Section 5 that is H1(c): FOMC release minutes come from federalreserve.gov schedules, independent of the vendor clock.
1c. Scenarios: c = -1 (the vendor stamp is the minute end: every LEGACY alarm is truly available 1 minute earlier than assumed), c = 0 (the assumption; MR2), c = +1 (the stamp is 1 minute early: every LEGACY alarm is truly available 1 minute later; this is the look-ahead direction).
1d. Centred vendor cleaning (look-ahead inside a bar) cannot be detected by any check here and remains disclosed as open (ledger row 8).

## Rule 2: computation

2a. H1(c) exactly as A17 (98 events, hit = a confirmed alarm with availability T_c in [release, release + 60 min], reference rate from the fold's non-FOMC test sessions in the same clock window, paired exact sign test, Wilson 95% intervals), with T_c + c for every alarm of the 25 confirmatory LEGACY folds (feature and baseline models alike; RAW 0 unchanged). Reference rates use the same shifted alarms. Unlike the A22 delay, a clock offset moves T_d and T_c together and the hit criterion here uses T_c only, so no pre-event detection is credited beyond what the offset itself implies.
2b. Alarms: the stored MR2 A17-style test alarms at the 0.20 target (primary), and the A22 alarms at 0.15 and 0.25 (secondary). No model is fitted, filtered or rethresholded.
2c. Reproduction check: c = 0 at 0.20 must equal the MR2 A17-style H1(c) exactly, and c = 0 at 0.15 / 0.25 must equal the A22 threshold-phase H1(c) exactly, else stop (exit 4).
2d. Reported per family (Gaussian HMM, Student-t HMM, HSMM; BOCPD as secondary): feature and baseline hit rates, paired difference, p value, reference rates, and the number of events whose hit status changes between c = 0 and c = -1 / +1. Descriptive sensitivity; multiplicity none (as A17 H1(c)). Nothing changes the MR2 verdicts, setups or 5.12.

## Rule 3: runtime, contamination, order

3a. Runtime: reading 136 stored A17-style records and 26 A22 threshold checkpoints and recomputing H1(c) 9 times (3 offsets x 3 targets): under 2 minutes; no data panel is loaded. Preflight: unit test that c = 0 reproduces (rule 2c) and that a synthetic alarm at release - 1 min becomes a hit at c = +1 and one at release + 60 min stops being a hit at c = +1; run on the stored records of the contaminated LEGACY 29 fold (its own events, if any, else the synthetic test only).
3b. Script `section5/s5_a24_clock.py` (registry POST_MAIN_RUN), tests in `section5/s5_tests_a24.py`; result `section5/results/a24/clock.json`. Runs before the freeze (user instruction). No protocol re-freeze, no 5.12 freeze, no era calibration.

## Governs

`section5/s5_a24_clock.py`, `section5/s5_tests_a24.py`, `section5/results/a24/`.
