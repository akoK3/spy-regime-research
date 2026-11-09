# Amendment A27 (confirmation-count sensitivity: 1, 2, 3, 4 consecutive updates; thresholds recalibrated to 0.2 alarms per session; saved models, no refit; main rule stays 3)

Dated 2026-11-09T17:00:00+00:00 UTC (2026-11-09T12:00:00-05:00 New York). Status: ADOPTED 2026-11-09T19:22:10+00:00 UTC (user approval 2026-11-09: "A27 and A28 approved"; the final draft, sha256 79cd385a..., is unchanged apart from this status line). Written before any code it governs and before any of its results exist. Decided by the user on 2026-11-09. Disclosed: MR2, its A17-style phase, D7 (A21), Step 2, all A22 results (including the grid results and the M3 note on the update-counted event rule), A24, the O9 audit and the first A25 folds have been seen; A23 has not produced results. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` (FROZEN through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A26.md` (ADOPTED) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `section5/results/mr2/a17/a17_results.json` (MR2 models manifest, A7 thresholds, alarms) | `9c8d29f150f9668701bba0080458b9291740e17c404c8dd164f7cc196beb07d4` |
| `section5/s5_sweep.py` (run = 3, warm = 2; BOCPD hold = 3) | `41353c22f222d4f85cf64c25ced24991f0ceb17ed1b9cc5b8c1ab9b37afb4f4e` |

## Rule 1: what changes

1a. The confirmation count r (consecutive real updates above threshold needed to confirm an alarm: `run` in `s5_sweep.sweep_old_state` / the HMM event rule; `hold` in `s5_sweep.sweep_map` / the BOCPD rule) takes the values 1, 2, 3 and 4. Everything else in the event rule is unchanged: warm = 2 updates, refractory 30 min, hit window 60 min, a hit needs T_d strictly after tau (A12 finding 14).
1b. Main rule unchanged: r = 3 stays the rule for every verdict, setup, threshold and the 5.12 freeze. A27 is a secondary sensitivity; it changes no verdict.
1c. Saved models only: the MR2 A17-style models (pickles hash-checked against the manifest), feature and baseline, all four families. No selection, no refit, no tuning.
1d. Thresholds recalibrated per r: on each fold's real validation sessions, the A7 bisection to 0.2 confirmed alarms per session, run with confirmation count r (feature and baseline models separately). Secondary targets 0.15 and 0.25 are not computed.

## Rule 2: outcomes and scope

2a. Scope: development folds only, the 26 confirmatory folds (LEGACY 0-22, 25, 26; RAW 0), 4 families. No evaluation-period session is read.
2b. Outcomes per r: H1(a) (the pAUC sweep with confirmation count r; null alarm axis from the same sweep), fold tests, IU and Holm as 5.9 / 5.11; H1(c) at the recalibrated 0.2 thresholds on the test segments (98 events, [release, release + 60 min], reference rates as A17); test alarm counts per session; time from first detection to confirmation. H1(b) does not depend on the event rule and is not recomputed.
2c. Reproduction check: r = 3 must reproduce the MR2 H1(a) fold effects, the A17 thresholds, the stored test alarms and the A17-style H1(c) exactly, else stop (exit 4).

## Rule 3: implementation, runtime, order

3a. New code only: `section5/s5_a27_confirm.py` (registry POST_MAIN_RUN) and `section5/s5_tests_a27.py`; results `section5/results/a27/`. The confirmation count is passed to the existing sweep and detection functions as a parameter from the new code. No module in the code-version closure changes (code version `a0323ed24d68e896`). If r cannot be passed without such a change, work stops and the user decides.
3b. Preflight on the contaminated RAW 3 and LEGACY 29 only: unit tests (r = 1 confirms on the first update above threshold; r = 4 needs four), the r = 3 reproduction, timing.
3c. Runtime: one filtering pass of the saved models over validation, test and splice sessions per fold (as the A22 thresholds and delay phases); about 3-4 h for all four values of r, checkpointed per fold.
3d. A27 must finish before the 5.12 freeze: the freeze is not written while A27 is running or unfinished. No protocol re-freeze, no 5.12 freeze, no era calibration under this amendment.

## Governs

`section5/s5_a27_confirm.py`, `section5/s5_tests_a27.py`, `section5/results/a27/`.
