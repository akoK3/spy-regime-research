# Cold audit status

Written 2026-11-03T22:55:29.893522+00:00 UTC. Source: `section5_cold_audit.md` (sha256 `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062`), 22 findings. Cited by `AMENDMENT_A11.md`; updated by `AMENDMENT_A12.md` and later amendments, last by `AMENDMENT_A16.md` (the A15 version is preserved as `COLD_AUDIT_STATUS_v5_A15.md`; earlier ones as v1-v4) (the A11 version is preserved as `COLD_AUDIT_STATUS_v1_A11.md`). Status values: resolved (fixed and tested, or covered by an amendment that removes the problem), disclosed (stated in a dated record, problem remains), open (not addressed). Facts only.

Totals: resolved 10, disclosed 4, open 8.

| # | Severity | Finding | Status | Evidence |
|---|---|---|---|---|
| 1 | Critical | H1(a) scores zero-effect breaks above chance | **disclosed** | Cause fixed (A8 item 1: scale in the detector's units, unit-tested; placebo gaps no longer positive across the board). Residual: the R=1 gate failed on LEGACY 29 and is documented, not resolved (A8.3, A8.4, protocol 5.15); the unexplained f3 excess on LEGACY 25 was not re-measured; the chance term in the metric is unchanged. |
| 2 | Critical | A7 decided after test curves were seen | **disclosed** | A8 item 2 and protocol 5.14: A7 stays; RAW 3 is on the contamination list and excluded from confirmatory H1. |
| 3 | High | Evidence sits inside earlier folds' test blocks | **resolved** | A8 item 2: sessions touched by any pilot or diagnostic are listed mechanically; folds whose test segment intersects the list are excluded from confirmatory H1; all-folds sensitivity reported. Reopened by cold audit 2 (the first audit's LEGACY 25 run was unregistered; the registry test could not fail) and resolved by A15 rules 2-3: 8 of 34 folds excluded (LEGACY 23, 24 added), `check_registry` unit-tested to fail on an unregistered script. |
| 4 | High | H1(a) crashes on 8 LEGACY folds; 19 usable | **resolved** | `build_specs_safe` skips instead of crashing (A8 item 3, unit-tested). Disclosed remainder: the 5.9 block bootstrap runs over the evaluable folds in order, so gaps between skipped folds are not respected; the protocol does not define this. |
| 5 | High | Feature pool selected on all of TRAIN (N.3) | **disclosed** | A8 item 4: justification (label-free screening); limits stated; no in-fold recomputation. |
| 6 | Medium | EM stopping is relative, not the 1e-4 of 5.4 | **resolved** | A12 finding 6 (absolute tolerance on the total training log-likelihood, cap recorded), as amended by A13 item 1: an EM run converges when the change of the total log-likelihood divided by the number of real training updates is below 1e-6; cap 500 iterations; `fit_info.converged`; unit-tested. A12 machinery rerun (under the A12 rule): of 239 EM starts on RAW 3, 56 reached the cap; of 187 on LEGACY 29, 30. |
| 7 | Medium | Old state re-based in the refractory period | **resolved** | A12 finding 7: the old state is no longer re-based inside the refractory period (loop detectors and vectorised sweep agree; unit-tested). |
| 8 | Medium | Null splices carry natural shifts as large as small breaks | **disclosed** | A8.1: the placebo, not the null splice, is the zero-effect reference; the null construction is unchanged. |
| 9 | Medium | Break tau capped at 13:55 for all cells | **resolved** | A12 finding 9: `tau_cap`: permanent breaks and nulls to slot 299 (14:30), sandwiches to availability 14:00 and in-session end (slot <= 269 / 264); unit-tested on a synthetic panel. The A8 gate scripts keep the historical G_MAX. |
| 10 | Medium | Fold-level Lee-Mykland threshold never used | **open** | No change; affects the sensitivity set only. |
| 11 | High | Checkpoint keys omit the code version | **resolved** | Reopened by cold audit 2 (the version hashed 7 files and missed the model, event, sweep and backend code; A12 and A13 shared a version) and resolved by A15 rule 4: version = hash of every result-affecting module (import closure) with scheme tag A15, keys carry backend kind and budget; unit-tested. |
| 12 | Low | '25 of 25 checks' overstates coverage | **open** | Record only (A15 rule 7: Medium to Low). No change made to those checks; no test checks the splice builder for leakage. |
| 13 | Medium | +/-0.05 threshold robustness undefined under A7 | **open** | No amendment defines it. |
| 14 | Low | Hit window counts pre-seam evidence | **resolved** | A12 finding 14: a hit needs T_d strictly after tau and T_c within 60 min (`hit_in_window`, sweeps); unit-tested. Feature look-back windows still contain pre-seam bars. |
| 15 | Low | Unconfirmed alarms not counted | **resolved** | A12 finding 15: candidates open at the close are returned as dropped by the loop detectors and by the sweeps (`return_dropped`), and the backend reports the share at the calibrated threshold; unit-tested. |
| 16 | Low | Seeds, versions and shares not recorded | **open** | Partly: run summaries record the code version; seeds, library versions and abstention/skip shares are not recorded, nor (A15 rule 7, wider scope) flagged Student-t fit counts and EM cap hits. |
| 17 | Medium | Input hashes not checked at run time | **open** | A15 rule 7: Low to Medium. The freeze now records the hashes of the protocol, every integrated amendment, the cited inputs and the market-data files (A15 rule 6c); data files are still not verified against them when loaded. |
| 18 | Low | Student-t states ordered by scale, not variance | **open** | No change made. |
| 19 | Low | A bad Student-t start can win silently | **resolved** | A14 (reporting) and A14.2 (rule): the kept fit is the highest-likelihood start among those satisfying the 1% rule; if none does, the best fit is kept and flagged; flagged fits are counted and an H1 sensitivity excludes folds with flagged Student-t fits; unit-tested. Low residual (cold audit 2 finding 10): when all 10 attempts of a start fail, the last attempt, not the best, is kept for that start. |
| 20 | Low | Superseded code paths still live | **open** | No change made (`V.events_for`, hard-coded RAW in `s5_d2.py`). |
| 21 | Low | Sensitivity pool not limited to RAW in code | **open** | No change made. |
| 22 | Low | Unamended choices and records | **resolved** | A14, A14.1: HSMM pseudo-count 0.5 (hazard smoothing), hazard clip, probability floors, weight guard and the duration cap 78 (= full-session updates) are documented as named constants with unit tests, results unchanged; the `s5_fast.py` docstring credit is corrected; `PILOT_REPORT_LEGACY_FILES.md` gives the file hashes the LEGACY report lacks (its writer script is not recoverable); the protocol no longer says DRAFT (frozen). |

Findings 6, 7, 9, 14 and 15 were fixed by A12; 22 by A14/A14.1. Fixed by A14.2: 19. Reopened and resolved by A15: 3, 11. Still open: 10, 13, 17 (Medium), 12, 16, 18, 20, 21 (Low); disclosed: 1 (residual), 2, 5, 8; resolved with a disclosed remainder: 4 (gap handling).


## Cold audit 2 (`section5_cold_audit_2.md`, sha256 `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602` with the re-audit after A15 appended (the first part, sha256 `700a09fc527f00d532021deafdcd725641b9eea900caf03065bcdc11f011d942`, is byte-identical to the version A15 cites); 21 findings: 15 in the audit, 16-21 = the re-audit's new problems 1-6; A15, A16)

Totals: resolved 15, open 6. The re-audit confirmed findings 1-9 as fixed (3, 4 and 5 with the residuals 16-21).

| # | Severity | Finding | Status | Evidence |
|---|---|---|---|---|
| 1 | Critical | Baseline never tuned; inherits the feature model's K/lambda | **resolved** | A15 rule 1: baseline tuned on validation with the identical grid, 3 starts and tie rule (`base_params`); unit-tested. |
| 2 | High | LEGACY 23 and 24 in the confirmatory set | **resolved** | A15 rule 2: audit-1 scripts registered; regenerated list: 8 excluded, 26 confirmatory, 98 H1(c) events; unit-tested. |
| 3 | High | Registry test could not fail; 3 scripts unregistered | **resolved** | A15 rule 3: `check_registry` (plain pattern, backend constructors included), shown to fail on an unregistered script; scripts registered. |
| 4 | High | Checkpoint version omits model, event, sweep, backend code | **resolved** | A15 rule 4 (see audit 1 finding 11). |
| 5 | High | No main-run path; freeze thresholds not era-level | **resolved** | A15 rule 5: `s5_main.MainBackend`, clean folds only with the frozen-protocol hash, era thresholds via `EraBackend` after a complete run, `run_all` loads the contamination list; unit-tested without data. |
| 6 | Medium | Holm drops a non-evaluable family from m | **resolved** | A15 rule 6a: missing p enters as 1; unit-tested. |
| 7 | Medium | Failed H1(a) splice construction recorded as a zero effect | **resolved** | A15 rule 6b: recorded as a failure with its reason, listed in reports; unit-tested. |
| 8 | Medium | Freeze records no data-input hashes and no amendment after A10 | **resolved** | A15 rule 6c; unit-tested. |
| 9 | Medium | 5.14 unbounded for label-free statistics | **resolved** | A15 rule 6d: label-free analyses do not touch sessions; unit-tested. |
| 10 | Low | Student-t keeps the last attempt when all 10 fail | **open** | No change. |
| 11 | Low | Greedy adds features on non-finite QLIKE | **open** | No change. |
| 12 | Low | Block bootstrap crosses the era boundary | **open** | No change; extends the disclosed remainder of audit 1 finding 4. |
| 13 | Low | Flagged-fit counts and EM cap hits missing from run_summary.json | **open** | No change (see audit 1 finding 16). |
| 14 | Low | Feature caches have no version key | **open** | No change. |
| 15 | Low | 5.16 overstates the backend session guard | **open** | No change. |
| 16 | Medium | Era calibration guard was a public flag; EraBackend callable directly | **resolved** | A16 rule 1: EraBackend needs the hash-checked completion record of a main run over 34 folds; unit-tested (`s5_tests_a16.py`). |
| 17 | Medium | Contamination list supplied by the caller; freeze did not compare lists | **resolved** | A16 rule 2: one canonical list, checked against its sidecar and protocol 5.14 everywhere; unit-tested (`s5_tests_a16.py`). |
| 18 | Medium | Registry pattern missed era_context(, splice_batch(, pool initialisers | **resolved** | A16 rule 3: pattern extended; unit-tested; unit-tested (`s5_tests_a16.py`). |
| 19 | Low | run_all(files=...) could narrow the checkpoint version | **resolved** | A16 rule 4: argument removed; unit-tested (`s5_tests_a16.py`). |
| 20 | Low | Nothing blocked re-scoring after the era calibration | **resolved** | A16 rule 5: ERA_CALIBRATION.lock written before the first era fit blocks selection and scoring; unit-tested (`s5_tests_a16.py`). |
| 21 | Low | Protocol hash checked once; freeze stored any string; checkpoints ignored it | **resolved** | A16 rule 6: run_all verifies it, checkpoint version includes it, freeze re-verifies against the completion record; unit-tested (`s5_tests_a16.py`). |
