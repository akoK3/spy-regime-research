# Amendment A25 (O9 finding M1: the A22 LEGACY delay scored by the data time each alarm used)

Dated 2026-11-08T23:10:00+00:00 UTC (2026-11-08T18:10:00-05:00 New York). Status: ADOPTED 2026-11-09T16:11:26+00:00 UTC (user approval given in another session, confirmed in this one: "A25 and A26 were approved in another session"; the draft, sidecar d11818ca..., committed in f03a505, is unchanged apart from this status line). Written before any code it governs and before any of its results exist. Decided by the user after O9 (finding M1). Disclosed: the A22 delay results (H1(a) and H1(c) at +0/+5/+10 min) have been seen. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (frozen through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A22.md` | `3ce7b683a1369659b14b22c068bcc25c6a7b14a7a6b15758946c7050f8a15217` |
| `O9_AUDIT.md` (finding M1) | `8b31a38b23e21b6c2ffa0b7eaaa512c75e75d1cb475b493f265d6ff8f4407c8d` |
| `section5/results/a22/delay.json` (A22 rule 3d result, kept unchanged as a record) | `3c34ce81db367f6e1cc5a0e5d3b4510eeb013aafe59f71b219615e865d4b6b3b` |
| `section5/results/mr2/a17/a17_results.json` (MR2 models manifest, alarms) | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/s5_sweep.py` | `41353c22f222d4f85cf64c25ced24991f0ceb17ed1b9cc5b8c1ab9b37afb4f4e` |

## The problem (O9 M1)

A22 rule 3d shifted every alarm availability by delta and kept the hit test "T_d + delta strictly after tau, T_c + delta <= tau + 60 min". A detection whose decision bar is at or before tau uses only pre-change data, yet becomes a hit once delta moves it past tau. In H1(c), shifting T_c admits confirmations up to delta minutes before the release. A decision delay postpones when an alarm can be acted on; it does not change which data the alarm used.

## Rule 1: corrected delay scoring

1a. Data times are never shifted. For a delay delta (5 or 10 min), an alarm is a hit iff its data times meet the undelayed condition and its delayed action time is still inside the window:
- H1(a): T_d strictly after tau (unshifted) and T_c + delta <= tau + 60 min. Equivalently, the A7/A19.2 sweep on unshifted times with the hit window 60 - delta minutes. Null alarm counts are unchanged (they do not depend on tau and a uniform shift leaves refractory spacing intact).
- H1(c): T_c >= release (unshifted, the A17 rule) and T_c + delta <= release + 60 min, i.e. the A17 window shortened to [release, release + 60 - delta]. Reference rates use the same shortened window on non-FOMC sessions.
1b. Scope as A22 rule 3d: the 25 confirmatory LEGACY folds, the MR2 A17-style models (pickles hash-checked against the manifest), the MR2 splice specs (rebuilt, seed 4242), RAW 0 unchanged; H1(b) unaffected; fold tests, IU and Holm as 5.9 / 5.11; H1(c) at the 0.20 target from the stored MR2 alarms.
1c. No refit. H1(c) is rescored from the stored alarm records (no data). H1(a) needs the per-threshold detection times on the splices, which are not stored: the saved models are re-filtered on the rebuilt splices (as the A22 delay phase did) and swept with the shortened window.
1d. Reproduction check: delta = 0 must reproduce the MR2 H1(a) fold effects and the MR2 A17-style H1(c) exactly, else stop (exit 4).
1e. The A22 delay result stays in the record unchanged and is labelled superseded by A25 for interpretation; the A25 result is reported beside it.

## Rule 2: runtime, contamination, order

2a. H1(c): under 1 minute. H1(a): about 1.7 h (the A22 delay phase took 1.74 h for the same filtering). Preflight on the contaminated LEGACY 29 fold only: delta = 0 reproduction, plus a unit test that a detection at tau - 5 min confirmed at tau + 5 min is a hit under A22 at delta = 10 but not under A25, and that a detection at tau + 5 min confirmed at tau + 45 min is a hit at delta 0/5/10 under both.
2b. Script `section5/s5_a25_delay.py` (registry POST_MAIN_RUN), tests `section5/s5_tests_a25.py`; results `section5/results/a25/delay_datatime.json`. Runs before the freeze. No protocol re-freeze, no 5.12 freeze, no era calibration.

## Governs

`section5/s5_a25_delay.py`, `section5/s5_tests_a25.py`, `section5/results/a25/`.
