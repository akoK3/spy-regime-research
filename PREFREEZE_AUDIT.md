# PREFREEZE_AUDIT: read-only audit of everything since FABLE_REAUDIT.md, before the 5.12 freeze

Written 2026-11-10 (New York). Auditor: Claude Opus 5.5, read-only. Nothing was edited, committed or run against market data, and no evaluation-period row was read. Only data-free unit-test suites were executed. The working tree (`git status --porcelain`) and `METHODS_LEDGER.md` (sha256 `2b3ec721...`, equal to its sidecar) were identical before and after the tests. This file is the only one written.

Scope, as requested: A35, A36 and A37; the evaluation driver (`section5/s5_eval513.py`, `section6/s6_eval.py`); the refit timing and the one-shot marker (`section5/s5_freeze_models.py`, `section5/s5_freeze.py`); the label guards (`section5/s5_eval_label.py`, `section5/s5_eval_loader.py`, `section6/s6_run.py:write_once`); and the detector-selection logic (`s5_freeze.h2_primary`, `s6_eval.h34_primary`). A38 and the HF cleaning check were committed in the same window, so they are covered too.

Commits audited: `13028d9`, `81eb166`, `cc8948d`, `8a53be1`, `cfb69a5`, `363d18a`, `c96947a`, `7263a5a` (FABLE_REAUDIT was at `b5d293c`). Another session committed `ec18a8f` (`reply_latest.md` only) while this audit was running. It changes no code or amendment.

---

## Answer

**Not yet. One High finding and four Medium findings should be fixed before the freeze.** Each one becomes either impossible or expensive to fix afterwards.

The statistical side is in order:
- A35-A38 are ADOPTED and equal their sidecars, and `freeze_ready: yes`.
- The detector choice that the freeze will produce is clear.
- The label guards close the re-audit's M3 as far as the closure allows.
- Every data-free suite passes.

The gaps are in the freeze step and in the parts of the real-data path that have never run. A failure in that path either produces a freeze that can never be used, or uses up an era's only evaluation run. The protocol has no clean way to recover from either.

| Severity | Count | One-line summary |
|---|---|---|
| High | 1 | No committed freeze entry point. The only documented path calls `freeze_step` directly, which writes a valid freeze with no frozen models. That freeze can never be overwritten, and the evaluation then refuses forever (H1). |
| Medium | 4 | A failed `freeze_step` after the model fit blocks every retry (M1). The 5.13 feature pipeline is first compared with the main run only after the freeze (M2). The real-data part of `run_fn` after the marker has never run on real data (M3). A38's evaluation entry is unbuilt, cannot pass the current guard, and may be written after the RAW result is seen (M4). |
| Low | 9 | Disclosure of how A35 rescued the Gaussian HMM, and no minimum V (L1). Alert labelling (L2). Driver amendment list (L3). Guard residues (L4). HF zips outside the registry (L5). Embargo-spanning features (L6). Untested fallback detector (L7). Re-audit L3 and L7 still open (L8). Nit (L9). |

**Expected detector outcome.** I checked this against `section5/results/main_run_2/run_summary.json`, the MR2 run. MR1 is refused because `verify_completion` requires the current code version.
- Holm rejects the Gaussian HMM and the HSMM. The Student-t HMM is not rejected.
- Median validation QLIKE: Gaussian 0.2106, HSMM 0.2175. So `h2_primary` gives `gaussian_hmm`.
- The Gaussian HMM passes the A35 rerun, so `h34_primary` also gives `gaussian_hmm` (A35 3c).

---

## High

### H1. No freeze driver exists. The documented freeze call writes a freeze without frozen models, and that freeze can never be replaced.

**Where.**
- `section5/s5_main.py:6`: the docstring's freeze recipe is `s5_run.freeze_step(b, s, RESULTS, AMENDMENTS)`, with no `FreezeBackend` and no model fit.
- `section5/s5_freeze_models.py:73-80`: `freeze_with_models`, the A37 entry. It has no caller outside a unit test that only checks its refusals (`s6_tests_a37.py:62-69`).
- `section5/s5_freeze.py:31-35`: `write_freeze` never overwrites.
- `section5/s5_eval513.py:214-215`: `load_frozen` refuses a freeze without `input_hashes["frozen_models"]`.
- `section6/s6_eval_synth.py:108-115`: the synthetic end-to-end run builds its freeze with `FZ.build_freeze` and `FZ.write_freeze` on a `Stub` backend. It never goes through `freeze_with_models` and `s5_run.freeze_step` together.

**What.**
- A37 rule 1 requires the TRAIN refits to happen inside the 5.12 step and to be hashed into the freeze document. The code for that exists, but no script performs the freeze.
- The only written recipe bypasses the code. It produces a valid, hashed `section5_freeze.json` that `freeze_step` accepts and that the A37 evaluation can never use.
- The composition `freeze_with_models(MainBackend, MR2 summary, results, AM.freeze_ready())` → `FreezeBackend` → `freeze_step` → `MainBackend.era_thresholds` → `EraBackend.calibrate` (which writes the lock) has never run, even on a stub main backend. `s5_rehearsal.py` rehearses `freeze_step` alone.

**Failure scenario.**
1. The freeze is run as `s5_main.py` documents. `section5_freeze.json` and `ERA_CALIBRATION.lock` are written.
2. `s6_eval.py run` stops in `preflight` → `load_frozen`: "the freeze document records no frozen models". That stop is safe: no marker is written and nothing is read.
3. But the freeze cannot be rewritten (`write_freeze`), and the lock now exists. The only way forward is to delete a hashed freeze and a lock by hand, which is the kind of action the whole guard design exists to prevent. A rescue amendment would itself change the amendment list that `eval_guard` compares against the freeze.

**Fix (before the freeze).**
- Write a freeze driver, say `section5/s5_freeze_run.py`. It should:
  - pin `main_run_2`;
  - build `MainBackend(frozen protocol hash)`;
  - pass `AM.freeze_ready()`;
  - call `FM.freeze_with_models`, and nothing else;
  - after writing, check that `input_hashes["frozen_models"]` is present and that `load_frozen` succeeds for both eras.
- Add a registry-style test, as `s5_eval_label.direct_callers` does for `run_confirmatory(`, that fails if any script other than `s5_freeze_models.py`, the rehearsals and the tests calls `freeze_step(`.
- Fix the `s5_main.py` docstring.
- Rehearse the real composition in a temporary directory with a stubbed `MainBackend`, on development data or a synthetic run, with the lock path redirected.

---

## Medium

### M1. Any failure in `freeze_step` after the model fit makes every retry of the freeze refuse.

**Where.** `section5/s5_freeze_models.py:46-49` (`write_models` refuses when a manifest exists) and `:79-80` (fit and write first, then `freeze_step`); `section5/s5_run.py:83-90` (protocol, contamination, code-version and summary checks, then the era calibration); `section5/s5_era_threshold.py:38` (the lock is written before the first era-calibration fit).

**What.** `freeze_with_models` fits and hashes all 8 era × family models (hours of HSMM fitting on 4,022 LEGACY sessions) and writes `frozen_models/manifest.json`, and only then calls `freeze_step`. `freeze_step` then runs checks that could have run first, followed by the era calibration, which writes the lock and fits again.

**Failure scenario.** A contamination-hash mismatch, a protocol-hash mismatch, or a crash or out-of-memory in the era calibration happens after the manifest is written. No freeze exists. A retry raises `FileExistsError: frozen models are written once`. To proceed, someone must delete the hashed models by hand, with the lock possibly already present, and nothing records that.

**Fix.**
- Run `freeze_step`'s cheap checks (lines 83-86, `freeze_ready()`) before fitting.
- On a retry with no freeze present, accept an existing manifest only if it verifies, and if its setups, code version and TRAIN sessions equal the current ones. Reuse it; do not refit.
- Alternatively, write the models to a staging directory and promote it once the freeze exists. The hashes can be computed in staging.

### M2. The 5.13 feature pipeline is first compared with the development pipeline only after the freeze.

**Where.** `section5/s5_freeze_models.py:21-29,39` (the TRAIN context is built by `S513._load_span` + `S513.context`, which runs `L.compute_features` on a fresh panel load); `section5/s5_main.py:39-43` (the frozen era threshold comes from `EraBackend` on the main backend's era context, i.e. the development caches); `section5/s5_eval513.py:226` (`frozen_threshold_reproduced`, which first appears at evaluation time and is only reported).

**What.**
- Every development result, and the frozen era threshold, used the main-run era context.
- The frozen models and every evaluation score use a second path that has never been compared with it on real data. In the synthetic run the comparison holds trivially, because both thresholds come from `S513.calibrate` (`s6_eval_synth.py:100-104`).
- At freeze time both thresholds exist: `feature_recomputed` in the bundle and the era threshold from `freeze_step`. Nobody compares them until after the freeze, when a mismatch can only be reported.

**Failure scenario.** The two paths differ slightly, for example in the cache dtype, the `__sadj` baseline or the Lee-Mykland input. The frozen feature threshold, calibrated on path-A features, is then applied to models fitted and scored on path-B features. The evaluation alarm rate drifts from 0.2 per session, H1(c) hit rates move with it, and the deviation is first seen in the evaluation result, where it cannot be fixed without an amendment that invalidates the freeze.

**Fix.**
- **Now, development data only:** check that `S513.context(era, TRAIN panel)` features equal the main-run era-context features for the A20 pool.
- **In the freeze driver (H1):** compare each `feature_recomputed` with the era threshold before writing the freeze document, and stop on a difference larger than the bisection tolerance.

### M3. The real-data part of the 5.13 run after the marker has never run on real data, models or setups.

**Where.**
- `section5/s5_eval513.py:58-64` (`panel`: `_load_span` on the evaluation span, then `check_partitions`) and `:32-36`.
- `section431_step3_verification/prototype_sources/section4_3_1_candidates.py:56-96`: about 20 `require(...)` invariants, including session length 210 or 390, `"Unexpected development endpoints"`, ETF rows on the grid, `source_epoch` equal to the era, and exact adjacent-close returns.
- `section5/s5_eval513.py:256-289` (`run_fn`), and `s5_freeze.py:53-55` (marker, then `fit_fn`, `run_fn`, `json.dumps`).
- The synthetic run stubs `_load_span` and `partitions` (`s6_eval_synth.py:90`) and uses one feature with K = 2.

**What.** A37 rule 3 moved the marker to just before the first read, and that part is correct. But everything after the read can still fail and use up the era's only run (A37 3c says so):
- The Section 4 invariants have never been checked on evaluation rows.
- The panel sessions must equal the 800 / 445 `EVALUATION_EXPOSED` sessions of the split manifest exactly.
- The joined-panel features (LEGACY: 4,822 sessions), the real HSMM and BOCPD frozen models in `qlike_on`, `h1a_matrices` and `test_alarms`, the `BX.session_rows` consistency assertion (`s5_break_export.py:88`) and the JSON serialisation of real results have all been exercised only on generated data.
- FABLE_REAUDIT L8 asked for a dry run of the real `run_fn` on development data. It has not been done.

**Failure scenario.** One LEGACY evaluation session violates a Section 4 invariant, for example a 210-bar day the panel has but the ETF file lacks a bar for, or `check_partitions` finds one extra session. Or `session_rows` raises `Mismatch` for an HSMM run that was never exercised. The run stops after the marker, and 5.13 LEGACY is gone for good.

**Fix (no evaluation data needed).** Run a development-only rehearsal of the exact `preflight` → `fit_fn` → `run_fn` path:
- On each era, split TRAIN into a pseudo-TRAIN and a pseudo-evaluation tail of about 150 sessions.
- Use the real `_load_span`, the real `check_partitions` with a patched partition map, real `fit_bundles` with the MR2 final setups (all four families), and the real `run_fn` and JSON write, into a temporary directory with the guard patched as the synthetic run does.
- Record its memory and run time.

This is the cheapest way to turn "fails after the marker" into "fails in rehearsal".

### M4. A38's guarded evaluation entry is unbuilt, cannot use the current guard, and may be written after the RAW result is known.

**Where.** `AMENDMENT_A38.md` rules 1c, 5a and 5b; `section5/s5_eval_loader.py:88` (a Section 5 evaluation read requires `s5_eval_label.ACTIVE`, i.e. a call inside `run_confirmatory_labelled`, whose per-era marker will already exist after the official RAW run); `section6/s6_fingerprint.py:10` (the fingerprint covers `s5_eval_loader.py` and `s5_eval_label.py`); `section5/s5_contamination.py:68` (`DATA_LOAD` does not match the `hfdatalibrary_*` files).

**What.**
- A38 rule 1 requires a "guarded entry" with the freeze, the lock, the label and its own one-shot marker per file. It reads SPY from two HF zips that are not canonical panels.
- Under the current guard that entry has three options:
  - it cannot pass `authorise(..., section6=False)`, because `ACTIVE` is False outside 5.13 and 5.13 RAW will already have run;
  - or it calls `authorise(..., section6=True)`, which misrepresents the read;
  - or it needs new code in two fingerprinted helpers, which is a reported deviation after the fingerprint.
- Nothing else stops the HF zips being read with no guard at all.
- A38 5b allows the code to be written after adoption and run after the official RAW evaluation. It does not require the code to exist before the RAW result is seen.
- Building an IEX panel from the HF zip layout "with the Section 3/4 code paths" involves real choices: timestamps and time zone, off-calendar bars, which 3.4, 3.6 and 3.10 steps apply, and the treatment of missing minutes.

**Failure scenario.** After the freeze and the official RAW run, with the RAW effects known, the A38 loader is written. Its panel choices are made knowing the official RAW H1 effects, and the result decides the "filter-sensitive" or "no detectable filter effect" reading in the write-up. The entry either bypasses `s5_eval_loader`, so no access-log line exists, or changes fingerprinted helpers.

**Fix.**
- Before the freeze, or at the latest before the fingerprint and 5.13, write the A38 rule 1 code: the HF panel builder, the entry with its marker and label, and synthetic tests.
- Add it to `s6_fingerprint.HELPERS`.
- Give `s5_eval_loader` an explicit A38 authorisation path that is logged, so it needs neither `ACTIVE` nor `section6=True`.
- Add `hfdatalibrary_` to `DATA_LOAD`.

If A38's wording forbids this order, a one-line clarification belongs in the manifest **before** the freeze, not after.

---

## Low

**L1. A35 rescued the Gaussian HMM by a convention change that could only lower rejection rates, and the write-up must say so. A35 also sets no minimum V.**
- The valid-only p in `section6/s6_lib.py:59`, (1 + E)/(V + 1), is at least (1 + E)/(B + 1) for every resample set. So A35 1a could only reduce the null-control rejection rates.
- The rerun shows the effect: Gaussian H4b moved from 0.105 under the pre-registered A29 1d convention to 0.065 (`a35_null_control_gaussian_hmm.json`). The other five tests did not change.
- Rule 3 was written before the rerun, but given 1a the outcome was largely set when 1a was adopted.
- `reply_latest.md:106` says this. The ledger row (`METHODS_LEDGER.md:642`) and the amendment do not.
- Separately, A35 sets no floor on V. On the shorter evaluation periods, with contiguous folds, V/B may be far below the development 0.88. Conditioning on validity is not random (re-audit M4).
- Scenario: a reviewer reads "the Gaussian HMM passes the 7d null control". Fix: state it in the write-up and report V/B beside every evaluation H4 p, flagging any below about 0.9. No amendment is needed.

**L2. The alert labels a NaN positive control "FAILED", not "not evaluable"** (`section6/s6_eval.py:105-106`; `section6/s6_run.py:299`). `alerts_of` tests `p is None`. A NaN p falls through to `not passed`. Either way an alert is raised, but its status text is wrong. Fix: treat a non-finite p as not evaluable.

**L3. The driver's amendment list omits A38** (`section6/s6_eval.py:23`, used by `a29_guard` and `provenance` at `:34`). `eval_guard` still compares the full manifest A21-A38 with the freeze, so nothing is unguarded. But the evaluation results' `provenance.amendments` will not record A38, which governs the reading of 5.13 RAW.

**L4. Residues in the label guard (disclosed in part).**
- `WRITER_CALL` (`s5_eval_label.py:22`) misses `run_confirmatory (` and `getattr(FZ, "run_confirmatory")`, and scans only `section5/`, `section6/` and the root.
- `ACTIVE` and `EVAL_READS` are patchable module state, and `EVAL_READS` lasts for one process only. A later process that turns `s6_evaluation_*.json` into a table writes through `write_once` with no read in that process, so only the `period` field is checked.
- Scenario: a report script derives an unlabelled evaluation table. Fix: have `write_once` also refuse when the payload cites an `evaluation_*` / `*_evaluation_*` input; label tables by hand (A26 1d).

**L5. The 2026-11-11 HF zips contain RAW evaluation-period rows and are outside the registry.** `section5/s5_hf_cleaning_check.py:45-52` loads the whole CSV into memory and then filters to 2022-03-07..2024-12-23. Nothing is computed on 2025-2026 rows, the same pattern as the chunked loaders, but there is no access-log line and `DATA_LOAD` does not match these files. See M4 for the fix.

**L6. The first evaluation session's features span the embargo** (`section5/s5_eval513.py:39-42`; A36 4a, 1e).
- `concat` puts 2019-01-02 directly after 2018-12-21, and 2025-01-02 after 2024-12-23.
- `overnight_return_open` for the first evaluation session is a 7-session return. The 20-session baselines treat the gap as adjacent.
- This is consistent with A36 ("histories skip over them") but not stated for the overnight feature. Disclose it.

**L7. The A28 1b fallback can choose a detector with no Section 6 development run** (`section6/s6_eval.py:49-52`). If no family passes H1, the lowest median QLIKE is the Student-t HMM (0.2058). It has no A35 rerun or 7d check, and `h34_primary` checks only the Gaussian HMM and the HSMM. This is moot under MR2, where two families pass.

**L8. FABLE_REAUDIT L3 and L7 are still open and easier to fix before the fingerprint.**
- `s6_h2.py:186` vs `:192`: a different seed for the analysed detector in `detector_dependence`. This now also feeds the evaluation H2 tables.
- `s6_coverage.py:22,57,64`: the substring guard and an unconditional overwrite of `coverage_sessions.csv`, which `eval_era` uses for history availability.
- Any change after the fingerprint is a deviation.

**L9. Nit.** `s5_eval513.py:269-275` rebinds `b` from the model bundle to the H1(b) result in the middle of the loop. There is no bug today, but a later edit that reads `b["thresholds"]` after line 274 would fail after the marker.

---

## Status of the FABLE_REAUDIT findings

| # | Claimed | Verified | Notes |
|---|---|---|---|
| M1 | resolved (A35) | Yes, with L1 | The rerun reproduces the development rates exactly under the old convention (2d), and both detectors pass under 1a. The pass comes from the convention change. |
| M2 | resolved (A36, A37) | Specified, yes. Executable, partly | All the open choices are fixed in A36 rules 1-6. The driver exists. The real-data path is not rehearsed (M3), and the freeze entry is missing (H1). |
| M3 | resolved | Mostly | Section 5 reads require `ACTIVE` (`s5_eval_loader.py:88`); `ready()` refuses direct callers; `write_once` keys on `EVAL_READS` (`s6_run.py:478-481`). Residues in L4. |
| M4 | resolved (A35 1a) | Yes | `week_block_bootstrap(valid_only=True)` used by every `h4_test`; V and the old-convention p are reported. |
| L3 | open | Open | See L8. |
| L7 | open | Open | See L8. |
| L8 | resolved | Yes | `label()` wraps a non-dict, and A37 moved the fit before the marker (`fit_fn` only hands over the state). |
| L9 | resolved | Yes | `fingerprint_check` compares every fingerprinted file and the code version with the code on disk. HELPERS includes `s5_freeze_models.py` (A37 5c). |

## Code vs amendments A35-A38

| Amendment | Status / sidecar | Code | Match | Notes |
|---|---|---|---|---|
| A35 | ADOPTED, equal | `s6_lib.py:46-60`, `s6_run.py:154-162,184-185,232-234`, `s6_a35.py`, `s6_eval.py:45-57` | Yes | 1a-1d, 2a-2e and 3a-3d as written. The result files equal their sidecars, and `reproduces_development_run` is true for both. See L1. |
| A36 | ADOPTED, equal | `s5_eval513.py`, `s6_eval.py`, `s5_h1c_eval_times.py` | Yes, as amended by A37 | Evaluation-only, era terms, per-era secondaries, BOCPD secondary, history of 60 TRAIN sessions, units, placebos and cut points from evaluation sessions only (`check_units`), FOMC list built first, effects with day-cluster intervals and no p. See M3 and L6. |
| A37 | ADOPTED, equal | `s5_freeze_models.py`, `s5_eval513.py:207-253`, `s5_eval_loader.py:76-82`, `s6_eval.py:102-107,161-171` | Rules 2-5 yes; rule 1 in code but not reachable from any freeze script | The marker comes after the precheck; `fit_fn` fits nothing; the backend refuses fits; `precheck` logs PRECHECK only. See H1, M1 and M2. |
| A38 | ADOPTED, equal | none (rule 5b: code after adoption) | n/a | See M4 and L3. |

## What was verified

- `s5_amendment_manifest.py --check`: `freeze_ready: yes` on A21-A38. The A35-A38 sidecars equal their files.
- No `section5_freeze.json`, `ERA_CALIBRATION.lock`, `eval_access_log.txt`, `s6_fingerprint.json`, `frozen_models/` or `evaluation_*` file exists.
- `a35_null_control_{gaussian_hmm,hsmm}.json` equal their sidecars. Rates: Gaussian max 0.065, HSMM max 0.040. Under the old convention Gaussian H4b is 0.105, equal to the development run.
- MR2 (`main_run_2`, code version `a0323ed24d68e896`) has `base_params` in every final setup, so `load_frozen`'s `base_params or params` fallback is not used. MR1 (`b22b29ff...`) would be refused by `verify_completion`.
- Split manifest: LEGACY has 4,022 TRAIN, 5 EMBARGO (2018-12-24..31), 800 EVALUATION_EXPOSED (2019-01-02..2022-03-04) and 2 EXCLUDED sessions. RAW has 705 TRAIN, 5 EMBARGO and 445 EVALUATION_EXPOSED (2025-01-02..2026-10-12). The SPY ETF files cover both evaluation spans (`section3_4_etf_results/summary.json`). Only metadata was read; no evaluation row was read.
- `Prep.mu` is a dict, so the preprocessing equality check in `build_eval_state` cannot raise. `test_alarms` fits with `starts=3`, matching the frozen-model key. `test_alarms` returns every test session, so the H1(c) events are not limited to sessions with an alarm.
- Unit tests (data-free), all pass: `s5_tests_ledger` 2/2, `s5_tests_freeze_prep` 13/13, `s5_tests_hf_cleaning` 3/3, `s6_tests` 30/30, `s6_tests_h2` 10/10, `s6_tests_a34` 5/5, `s6_tests_a35` 10/10, `s6_tests_a36` 18/18, `s6_tests_a37` 9/9.

## Before the freeze, in order

1. **H1:** write the freeze driver, ban direct `freeze_step(` calls, and rehearse the real composition.
2. **M1:** run the checks before the fit, and make the model write resumable or staged.
3. **M2:** check now that the two feature paths agree on development data, and compare the thresholds inside the freeze driver.
4. **M3:** run the development-only rehearsal of the real `preflight` → `run_fn` path, all four families, with real loaders.
5. **M4:** write the A38 entry, panel builder and tests, and fingerprint them. Register the HF files.
6. **Cheap, and better before the fingerprint:** L2, L3, L8 and L9. The disclosures for L1 and L6 can be written at any time.

---

## Recheck, 2026-11-11 13:25 New York (read-only; Claude Opus 5.5)

Scope: every finding above, against the fixes claimed in `reply_latest.md` (commits 2d548e0, cb9d7fc, 4392eab), and the dress rehearsal.
- Nothing was edited for this recheck, apart from this appended section.
- The data-free suites were rerun, and the state was read.
- The full dress rehearsal (PID 3284, started 12:42) **is still running**: it is in the LEGACY freeze-fit stage and has written no result yet.

### Answer: **not yet safe to freeze. One blocker: the full dress rehearsal must finish and pass.**

Every finding is fixed as claimed, except one item that cannot be done (the `s5_main.py` docstring, closure). But the rehearsal evidence so far does not yet cover the two paths M3 was raised for.

### State verified

- **Code version** `a0323ed24d68e896`. Working tree clean apart from untracked logs.
- **`freeze_ready()`** passes on A21-A38. A35 equals its new sidecar.
- **Registry** check passes. `s5_eval_label.direct_callers()` is empty. The new direct `freeze_step(` scan is empty.
- **No real `ERA_CALIBRATION.lock`**, `section5_freeze.json`, `eval_access_log.txt`, `frozen_models/`, `frozen_models.staging/` or `s6_fingerprint.json` exists.
- **Suites, all pass:**
  - Section 5: freeze prep 13/13, freeze driver 7/7, A38 8/8, HF check 3/3, ledger 2/2.
  - Section 6: base 30/30, H2 10/10, A34 5/5, A35 10/10, A36 18/18, A37 9/9.

### Findings

| # | Claimed | Verified | Notes |
|---|---|---|---|
| H1 | single driver, ban test, rehearsal | **Yes, one item not possible** | `s5_freeze_run.py` exists; `freeze_with_models` delegates to it; `check` passes on MR2 (passing: Gaussian HMM, HSMM; expected H2 primary `gaussian_hmm`; no lock); the ban test passes. The `s5_main.py` docstring still shows the bare call: the file is in the closure (an edit changed the code version; restored; ledger incident row 4392eab). The ban test lists it as text-only. Acceptable. |
| M1 | prechecks first, staged and retryable, move after | **Yes, with a residual (R1)** | Order as claimed (`freeze`: prechecks → parity → stage → `freeze_step` with checking wrapper → `promote`). Tests cover crash-retry without refit, mismatch, precheck refusal, interrupted move and unverifiable staging. See R1. |
| M2 | parity now and in the driver | **Yes** | `feature_parity.json`: RAW 705 and LEGACY 4,022 TRAIN sessions; every compared field equal. Driver threshold check: in the smoke run, all four RAW era thresholds equal the 5.13-path value exactly. |
| M3 | development-only rehearsal | **Partly; blocker (B1)** | The smoke run (`dress_rehearsal_smoke.json`) passed: real freeze driver, 5.13 through the labelled entry with real loaders, all four families, Section 6, the A38 entry, real paths untouched. But it ran RAW only, and with 7 stable days **H1(a) was skipped** in 5.13 and in A38. |
| M4 | A38 entry before the freeze | **Yes** | `s5_a38.py`: builder reproduces the canonical RAW panel exactly (705 sessions); `authorise_a38` logged; per-file hash and marker; saved arrays; tests 8/8; registered (EVALUATION); in `s6_fingerprint.HELPERS`; `hfdatalibrary_` in `DATA_LOAD`. |
| L1 | disclosure, V/B | **Yes** | A35 note appended (dated, rules unchanged, prior hash recorded, sidecar matches); `h4_test` reports `valid_share` and `low_valid_share`. |
| L2 | NaN = not evaluable | **Yes** | `sanity` and `alerts_of`. Seen in the smoke run ("not evaluable", 1 Fed break). |
| L3 | A38 in the driver list | **Yes** | `s6_eval.AMENDMENTS` ends A37, A38. |
| L4 | writer scan, `write_once` | **Yes, residue as before** | Any reference matches; test files exempt by pattern; `write_once` refuses unlabelled payloads that cite evaluation files. `ACTIVE` / `EVAL_READS` remain module state (not changed; disclosed). |
| L5 | registry, streaming | **Yes** | |
| L6 | overnight across the gap | **Yes** | `context(boundary=n_tr)`. No pool feature or base is overnight-type, so the models are unaffected. |
| L7 | fallback detector needs an A35 rerun | **Yes** | `h34_primary` stops otherwise. |
| L8 | FABLE_REAUDIT L3, L7 | **Yes** | H2 dependence reuses the primary; the coverage guard uses the manifest; write-once. |
| L9 | no rebinding | **Yes** | |

### Blocker

**B1. The full dress rehearsal must finish and pass before the freeze.**

It is the only run that exercises, on real data, models and loaders:
- **the whole LEGACY path:** the freeze-driver fits and era calibration on about 3,900 sessions, the LEGACY joined panel and the Section 4 invariants on its evaluation-shaped tail, and the LEGACY Section 6 history;
- **the H1(a) path:** stable-day splices on the evaluation segment, `h1a_matrices` with the frozen models, `ci_pauc_diff`, and A38's reuse of the Raw splices on the Clean run with `boot_pauc`. The smoke run skipped all of these (7 < 8 stable days);
- **the production resample settings:** 9,999 resamples, 200 null sets, 10,000 draws, with 3 workers and the memory they need.

**Pass condition:**
- `dress_rehearsal.json` `passed: true`;
- H1(a) evaluated (not skipped) for both eras in 5.13 and in A38;
- `frozen_thresholds_reproduced` true for all 8 era-family pairs;
- `real_paths_untouched` true;
- no error.

### Residuals (not blockers; to be stated or accepted)

- **R1. The era-threshold check (M2 in the driver) happens after the lock is written.** `EraBackend.calibrate` writes `ERA_CALIBRATION.lock` before its fit (closure, A16 rule 5), and the wrapper compares only the threshold it returns. A mismatch would therefore stop the freeze with a real lock and no freeze document: no further development scoring, and a retry would mismatch again. The probability is low, because the feature paths are equal on both eras and the smoke thresholds were equal to the bit. It cannot be removed without a closure change. Accept and disclose, or rehearse it first, which the full run does for all 8 pairs.
- **R2. A one-shot per A38 file.** If an HF file's read or panel build fails after its marker, that file's check is gone for good (A38 5a, by design). The full rehearsal exercises the RAW path once more.
- **R3. Process-local guard state (L4 residue).** Tables derived in a later process must be labelled by hand (A26 1d).
- **R4. Fingerprint order.** Any code change after `s6_fingerprint.py write` is a deviation. The fingerprint covers every `section6/*.py`, including the rehearsal scripts. Write it only after B1 passes and nothing else is pending.

### Order once B1 passes

1. `s5_freeze_run.py run --confirm section5_freeze.json`.
2. `s6_fingerprint.py write`.
3. `s6_eval.py run FREEZE TOKEN`.
4. `s5_a38.py run FREEZE TOKEN`.

Each step only on the user's instruction.
