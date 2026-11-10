# Cold audit status

Written 2026-11-10T23:15:00Z (UTC). Refreshed to the current status: resolved items name the fixing amendment and commit; the O9 and Fable audits are added below. The A16 version is preserved as `COLD_AUDIT_STATUS_v6_A16.md` (earlier ones as v1-v5). Source of audit 1: `section5_cold_audit.md` (sha256 `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062`), 22 findings.

Totals: resolved 12, disclosed 4, open 6 (one of them partly addressed).

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
| 13 | Medium | +/-0.05 threshold robustness undefined under A7 | **resolved** | A22 rule 3c defines it as the A7 bisection to 0.15 and 0.25 confirmed alarms per validation session; run with A22 (commit dad361d): 0.20 reproduces MR2 thresholds, alarms and H1(c) exactly; H1(c) diff stable at 0.15/0.25 (ledger 2026-11-08 21:26:41Z). |
| 14 | Low | Hit window counts pre-seam evidence | **resolved** | A12 finding 14: a hit needs T_d strictly after tau and T_c within 60 min (`hit_in_window`, sweeps); unit-tested. Feature look-back windows still contain pre-seam bars. |
| 15 | Low | Unconfirmed alarms not counted | **resolved** | A12 finding 15: candidates open at the close are returned as dropped by the loop detectors and by the sweeps (`return_dropped`), and the backend reports the share at the calibrated threshold; unit-tested. |
| 16 | Low | Seeds, versions and shares not recorded | **open** | Partly addressed: A22 5.10 (`a22/era_flagged.json`, commit dad361d) aggregates flagged Student-t fits (0 in MR2); run summaries record the code version. Seeds, library versions, abstention and skip shares and EM cap hits are still not recorded in `run_summary.json`. |
| 17 | Medium | Input hashes not checked at run time | **resolved** | Audit-1 #17 data-hash preflight `section5/s5_preflight_data_hashes.py` (commit 55cfc4e; PASS 10/10, ledger 2026-11-09 00:51Z): the 4 market-data files and the 6 cited inputs against their recorded hashes; run first by every runner since A27 (commit 01ac960) and inside `s5_eval_loader.load_eval`; group C (feature-cache stamp, finding 14) added in commit 9124c67 (17/17 PASS). |
| 18 | Low | Student-t states ordered by scale, not variance | **open** | No change made. |
| 19 | Low | A bad Student-t start can win silently | **resolved** | A14 (reporting) and A14.2 (rule): the kept fit is the highest-likelihood start among those satisfying the 1% rule; if none does, the best fit is kept and flagged; flagged fits are counted and an H1 sensitivity excludes folds with flagged Student-t fits; unit-tested. Low residual (cold audit 2 finding 10): when all 10 attempts of a start fail, the last attempt, not the best, is kept for that start. |
| 20 | Low | Superseded code paths still live | **open** | No change made (`V.events_for`, hard-coded RAW in `s5_d2.py`). |
| 21 | Low | Sensitivity pool not limited to RAW in code | **open** | No change made. |
| 22 | Low | Unamended choices and records | **resolved** | A14, A14.1: HSMM pseudo-count 0.5 (hazard smoothing), hazard clip, probability floors, weight guard and the duration cap 78 (= full-session updates) are documented as named constants with unit tests, results unchanged; the `s5_fast.py` docstring credit is corrected; `PILOT_REPORT_LEGACY_FILES.md` gives the file hashes the LEGACY report lacks (its writer script is not recoverable); the protocol no longer says DRAFT (frozen). |

Findings 6, 7, 9, 14 and 15 were fixed by A12; 22 by A14/A14.1. Fixed by A14.2: 19. Reopened and resolved by A15: 3, 11. Resolved since A16: 13 (A22), 17 (preflight, 55cfc4e / 01ac960 / 9124c67). Still open: 10 (Medium), 12, 16 (partly), 18, 20, 21 (Low); disclosed: 1 (residual), 2, 5, 8; resolved with a disclosed remainder: 4 (gap handling).


## Cold audit 2 (`section5_cold_audit_2.md`, sha256 `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602` with the re-audit after A15 appended (the first part, sha256 `700a09fc527f00d532021deafdcd725641b9eea900caf03065bcdc11f011d942`, is byte-identical to the version A15 cites); 21 findings: 15 in the audit, 16-21 = the re-audit's new problems 1-6; A15, A16)

Totals: resolved 16, open 5 (one partly addressed). The re-audit confirmed findings 1-9 as fixed (3, 4 and 5 with the residuals 16-21).

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
| 12 | Low | Block bootstrap crosses the era boundary | **open** | Section 5 (H1 block bootstrap, 5.9): no change; the result modules are frozen at code version a0323ed24d68e896. Section 6 does not share it: `s6_lib.week_block_bootstrap` resamples calendar weeks within each era separately (A28 3c). |
| 13 | Low | Flagged-fit counts and EM cap hits missing from run_summary.json | **open** | Partly addressed: flagged Student-t fits aggregated by A22 5.10 (0 in MR2; commit dad361d). EM cap hits are still not in `run_summary.json`. |
| 14 | Low | Feature caches have no version key | **resolved** | Commit 9124c67 (FABLE_AUDIT L6): Section 5 cache stamp `section5/s5_cache_stamp.py` keys `{era}_features.npz` / `_bases.npz` by sha256(feature code / panel / ETF), checked by the finding-17 preflight (group C) in every runner and in `load_eval`; Section 6 `load_era` caches through `s6_lib.Cache` (key = column / code hash / panel hash), unit-tested for a hit and for no stale hit. The result modules are unchanged. |
| 15 | Low | 5.16 overstates the backend session guard | **open** | No change. |
| 16 | Medium | Era calibration guard was a public flag; EraBackend callable directly | **resolved** | A16 rule 1: EraBackend needs the hash-checked completion record of a main run over 34 folds; unit-tested (`s5_tests_a16.py`). |
| 17 | Medium | Contamination list supplied by the caller; freeze did not compare lists | **resolved** | A16 rule 2: one canonical list, checked against its sidecar and protocol 5.14 everywhere; unit-tested (`s5_tests_a16.py`). |
| 18 | Medium | Registry pattern missed era_context(, splice_batch(, pool initialisers | **resolved** | A16 rule 3: pattern extended; unit-tested; unit-tested (`s5_tests_a16.py`). |
| 19 | Low | run_all(files=...) could narrow the checkpoint version | **resolved** | A16 rule 4: argument removed; unit-tested (`s5_tests_a16.py`). |
| 20 | Low | Nothing blocked re-scoring after the era calibration | **resolved** | A16 rule 5: ERA_CALIBRATION.lock written before the first era fit blocks selection and scoring; unit-tested (`s5_tests_a16.py`). |
| 21 | Low | Protocol hash checked once; freeze stored any string; checkpoints ignored it | **resolved** | A16 rule 6: run_all verifies it, checkpoint version includes it, freeze re-verifies against the completion record; unit-tested (`s5_tests_a16.py`). |

## O9 (`O9_AUDIT.md`, sha256 `8b31a38b23e21b6c2ffa0b7eaaa512c75e75d1cb475b493f265d6ff8f4407c8d`; read-only audit of 2026-11-08; 0 High, 3 Medium, 9 Low)

Totals: resolved 5, disclosed 7, open 0.

| # | Severity | Finding | Status | Evidence |
|---|---|---|---|---|
| M1 | Medium | A22 delay credits pre-tau detections | **resolved** | AMENDMENT_A25 (adopted commit 21b575c; results d6e22b1): delayed alarms scored by the data time used; delta 0 = MR2 exactly; H1(a) moved by at most 0.001, no verdict changed. A22 `delay.json` kept as a record. |
| M2 | Medium | Zero slot medians make __sadj values undefined on LEGACY bars | **disclosed** | `SECTION5_DISCLOSED_LIMITATIONS.md` D1 (feature models update on ~15% fewer LEGACY bars) and D2 (the 47 D7 NaN days, 47/47 zero slot medians) (commit f03a505). |
| M3 | Medium | Grid sensitivity conflates resolution with update-counted event timing | **disclosed** | `section5/results/a22/grids_NOTE.md` and limitations D3 (commit f03a505); post-hoc absolute pAUC (ledger 2026-11-09 04:50:55Z): the 1-min contradiction is the feature model collapsing at 1 min. |
| L1 | Low | H1(a) power uses 26 folds, not 22 | **resolved** | `section5/s5_power_observed_n.py`, `a22/power_observed_n.json` (commit f03a505): MDE unchanged at grid resolution. |
| L2 | Low | D7 MDE ignores day pairing | **disclosed** | A22 4b; limitations D4. |
| L3 | Low | D7 checkpoint tag lacks code version and protocol | **resolved** | Commit f03a505: tag includes both (future D7 runs; finished results unaffected). |
| L4 | Low | D7 liquidity gate i true by construction | **disclosed** | Limitations D4. |
| L5 | Low | A18 backend kind shared by the MR1 and MR2 reruns | **disclosed** | Limitations D4. |
| L6 | Low | A18 objective bar sets differ by subset | **disclosed** | Limitations D4. |
| L7 | Low | Hard-coded 78 slots | **disclosed** | Limitations D4 (only the A22 grid path overrides it). |
| L8 | Low | Stale comment in `s5_mr2.py` | **resolved** | Commit f03a505. |
| L9 | Low | Ledger `date_of` takes the first timestamp | **resolved** | Commit f03a505: uncommitted files dated by mtime. Residual (dates from the file's own stamp) is FABLE L7, open. |

## Fable audit (`FABLE_AUDIT.md`, sha256 `005129986659b5827f94bf491f4120ae19db3ec674d25d78b50974f2ecc7db57`; 2026-11-10; 0 High, 5 Medium, 12 Low)

Totals: resolved 12, disclosed 2, open 3. Fixes without amendment are in commit 9124c67 (approved by the user as not needing an amendment); the rest by AMENDMENT_A31.

| # | Severity | Finding | Status | Evidence |
|---|---|---|---|---|
| M1 | Medium | Evaluation-period guard bypassable without code change | **resolved** | Commit 9124c67: `load_eval` / `eval_guard` take no override arguments (lock, fingerprint, panels and preflight are module constants patched only by tests); a test asserts the signature. |
| M2 | Medium | Section 6 Holm drops non-evaluable tests from m | **resolved** | Commit 9124c67: `s6_run.holm_family` m = 6 always, non-evaluable p = 1; unit test reproduces the audit scenario. H2 (A33) uses m = 4 the same way. |
| M3 | Medium | Section 6 outputs lack code / amendment hashes; no ledger rows for s6 code | **resolved** | Commit 9124c67: `provenance()` (code hashes, code version, amendment manifest) and `write_once` (sidecar, no overwrite) in every Section 6 output; ledger rows for every Section 6 file. |
| M4 | Medium | Registry does not scan section6 or the new loaders | **resolved** | Commit 9124c67: data-load pattern adds `load_development(`, `load_eval(`, panel references; `section6/` scanned; every Section 6 script registered (incl. later `s6_posthoc_h3_ci.py`, `s6_h2.py`). |
| M5 | Medium | Placebos conditioned on SPY's future alarms; 7d null cannot detect it | **resolved** | AMENDMENT_A31 rule 1 (past alarms only) and rule 3 (placebo-filter null control, as revised by the user) (draft d1180ca, code ce307a7; adopted after the rule 4 check passed 29/29, commit e6eb407). |
| L1 | Low | H4a placebo eligibility depends on the label | **resolved** | AMENDMENT_A31 rule 2b: gap-0 placebos for every H4a unit. |
| L2 | Low | Matched sets split across bootstrap blocks | **open** | Section 6 H3/H4 unchanged. The A32 statistic (exploratory under A33) resamples breaks with their placebos; the H2 primary (A33) uses placebo draws, not a block bootstrap. |
| L3 | Low | A26 rule 1d label never attached | **resolved** | AMENDMENT_A34 rule 3 (commit 37ae229): `s6_run.write_once` refuses any non-development result without `a26_label` and `confirmatory = False`; Section 5 5.13 goes through `s5_eval_label.run_confirmatory_labelled` (wraps run_fn; `verify_labelled`), and `s5_eval_loader.eval_guard` requires `s5_eval_label.ready()` before any evaluation-period read; unit-tested (`s6_tests_a34.py`). |
| L4 | Low | `load_era` loads evaluation rows before refusing the joint period | **resolved** | Commit 9124c67: refused before any read; unit-tested. |
| L5 | Low | A29 not in the freeze manifest | **resolved** | Commit 9124c67 (A29, A31); A30 (8205928), A32 (cde894d), A33 (8821487), A33.1 (1fdb5f7) added when written; `freeze_ready` refuses until all are adopted. |
| L6 | Low | Finding-14 fix has no call site | **resolved** | Commit 9124c67 (see cold audit 2 #14). |
| L7 | Low | Ledger integrity relies on git; dates from the file's own stamp | **open** | No change. Two stamp errors were found and corrected by ledger rows on 2026-11-10 (A31 revision; A32 and A33 Dated lines ahead of adoption). |
| L8 | Low | A29 statistic changed after a synthetic smoke test, in the same commit as its code | **disclosed** | Recorded in `AMENDMENT_A29.md` (revision of rules 1b, 1c, 1g after the smoke-test diagnostic, before the rule 2 run). |
| L9 | Low | Rule 7c "FOMC days" are only the 98 H1(c)-eligible events | **open** | No change; the Fed split in the development results uses this list. |
| L10 | Low | H4a units filtered on a direction computed after S | **resolved** | AMENDMENT_A31 rule 2a: every calm-state streak start, any outcome; no post-S direction filter. |
| L11 | Low | A27 r = 1 thresholds hit the search bound | **disclosed** | A27 result row (ledger 2026-11-10 04:33:52Z) and `project_upload/RESULTS_SUMMARY.md`. |
| L12 | Low | Adoption guards are substring checks | **resolved** | Commit 9124c67: guards use the manifest regex and sidecar match. |
