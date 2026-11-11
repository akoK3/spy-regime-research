# FABLE_REAUDIT: read-only re-audit of what changed since FABLE_AUDIT.md, before the pre-registration freeze

Written 2026-11-10 (New York). Auditor: Claude Fable 5.2, read-only. Nothing was edited, committed or run against market data. Only data-free unit-test suites were executed; the working tree and the ledger hash were identical before and after. Repository HEAD: `b5d293c` (2026-11-10 18:32 -05:00). The previous audit was at `1a4505e`; 19 commits lie between them.

Scope as requested: amendments A29-A34 (including A33.1), every fix made for the FABLE_AUDIT findings, the Section 6 H2 code, and the enforcement of the A26 evaluation label. Findings use the same format as FABLE_AUDIT.md. The last section answers whether anything blocks the freeze.

Not re-audited: Section 5 code inside the closure (unchanged, code version `a0323ed24d68e896`), the era calibration and `s5_run.freeze_step`. The finding-17 data-hash preflight was not re-run because it hashes the data files.

---

## Summary

| Severity | Count | One-line summary |
|---|---|---|
| High | 0 | No path was found that reads 2019-2022 or 2025-2026 data, and no statistic was found to be misreported. No freeze, lock, fingerprint or evaluation access log exists. |
| Medium | 4 | The Gaussian HMM failed the A28 7d null control, and A28 says that stops the work before the joint evaluation; it was disposed in a report only (M1). The joint-evaluation path for H2, H3 and H4 is neither written nor specified, and an amendment after the freeze invalidates the freeze (M2). The A26 label enforcement can be bypassed on both sides (M3). NaN bootstrap resamples understate the H4 p-value, by 12% for the test that failed the null control (M4). |
| Low | 10 | Section 6 registry scan runs only in a unit test (L1); the A31 rule 3 control flags real break effects, not only filter bias (L2); H2 detector dependence recomputes the analysed detector with another seed (L3); the H2 synthetic acceptance uses raw p, the test uses Holm (L4); A32 was rewritten after adoption and A33 cites the old hash (L5); H4a covers under half of the H3 breaks (L6); `s6_coverage.py` kept its old guard and writer (L7); the label wrapper can burn the one-shot evaluation run (L8); the evaluation guard does not compare the fingerprint with the current code (L9); H2 gap choices were made after related results were seen (L10, disclosed). |

**Freeze answer in one line:** the mechanical gate passes (`freeze_ready: yes`, A21-A34 ADOPTED with equal sidecars), but M1 and M2 should be settled first, and M3 and M4 are cheap to settle first, because any amendment adopted after the freeze makes `load_eval` refuse.

---

## Medium

### M1. The Gaussian HMM failed the A28 7d null control; A28 says this stops the work before the joint evaluation; the disposal is a report sentence

**Where.** `AMENDMENT_A28.md:68` (rule 7d: "A failed sanity check stops the work before the joint evaluation and is reported"); `section6/results/s6_development_gaussian_hmm.json` (`sanity.null_control`: H4b 0.105, `passed: false`); `reply_latest.md:431,477` ("I recommend no amendment: report them as caveats").

**What.** The 200 null sets reject H4b in 10.5% of sets for the Gaussian HMM, against the limit of 10%. The HSMM passes at 8.0%. Both are well above the nominal 5%: at 200 sets the standard error at a true 5% is 1.5 points, so 10.5% is 3.6 standard errors above nominal and 8.0% is 2. The report's reading, "within noise of the limit", is true of the 10% limit but not of the 5% size. No amendment and no ledger row records a decision on the failed check. H1 is rejected for the Gaussian HMM and the HSMM, so either can become the primary detector at the freeze.

**Failure scenario.** The freeze selects the Gaussian HMM (lowest median validation QLIKE, or a tie, which goes to the simpler model). The Section 6 joint evaluation then runs on the detector whose sanity check failed, against the text of A28. A reviewer reads rule 7d and the result file and finds no dated decision that permits it. Fixing this after the freeze needs an amendment, which changes the manifest and makes `load_eval` refuse (`s5_eval_loader.py:74-75`).

**Mitigation observed.** The failure is reported openly in the result file and the report. H4b is not significant for either detector. M4 below is one measured contributor.

### M2. The joint-evaluation path for H2, H3 and H4 is not written and not specified, and the freeze closes the amendment list

**Where.** `section6/s6_run.py:46` (`load_era` refuses every period but development), `:479` (`main` refuses `joint`); `section6/s6_h2.py:321-329` (modes: synth, check, power, development only); `section6/s6_a34.py:93`; `section5/s5_freeze.py:44` (`run_confirmatory` takes injected `fit_fn` and `run_fn`; the only callers are tests and `s5_dry_run.py`); `section5/s5_eval_loader.py:74-75`.

**What.** No code computes any Section 6 quantity on the evaluation periods, and no driver supplies `fit_fn` and `run_fn` for 5.13. The amendments define the statistics but leave open several choices that only arise in the joint run:
- whether a placebo pool for an evaluation-period break may hold development sessions (A33 G6 says "the era's sessions"; A31 1c says "a session before the unit's session");
- whether decile cut points, the 60-session burn-in and the 20-session medians restart at the evaluation period or carry over;
- the label-free coverage of the evaluation sessions, which `load_era`'s own refusal message says must come first;
- the break export for the evaluation periods (the current one covers 2004-01-09 to 2023-09-06, development only);
- whether "joint" pools development and evaluation rows in one test or reports the evaluation period alone.

`eval_guard` requires the freeze's amendment list to equal the current manifest. An amendment adopted after the freeze therefore blocks every evaluation read until a new freeze exists, and `write_freeze` never overwrites.

**Failure scenario.** The freeze is written now. The joint code is written afterwards, and the developer has to choose whether evaluation-period breaks draw placebos from 2003-2018. Either choice is made after the freeze, with the development results known, and cannot be recorded by an amendment without invalidating the freeze. The choice ends up in code and a commit message only.

**Mitigation observed.** A28 6e fingerprints the Section 6 code before the joint evaluation, so the code cannot change silently after the fingerprint. Every evaluation-period result is exploratory by A26. Neither fixes when the choices are made.

### M3. The A26 label enforcement can be bypassed on both sides without touching the guard

**Where.** `section6/s6_run.py:466` (`write_once`); `section5/s5_eval_label.py:14-17` (`ready`), `:30-33` (`run_confirmatory_labelled`); `section5/s5_eval_loader.py:70-71`; `section5/s5_freeze.py:44-56`.

**What.** Three separate gaps.
1. Section 6: `write_once` applies the label rule only when the result's own `period` field is something other than `None` or `"development"`. The check trusts a field the caller writes. A result with no `period` key passes unlabelled; six existing output types have none.
2. Section 5: `run_confirmatory_labelled` is described as "the only sanctioned entry", but `s5_freeze.run_confirmatory` stays public and nothing refuses a direct call. `verify_labelled` is called only from inside the wrapper.
3. `eval_guard` calls `ready()`, which checks only that the label string appears in `AMENDMENT_A26.md`. It does not check who is calling or what will be written.

**Failure scenario.** The 5.13 driver is written after the freeze and calls `FZ.run_confirmatory(...)` directly, as `s5_dry_run.py:48` and the build tests do. Its `run_fn` calls `load_eval`, which passes. `evaluation_LEGACY.json` is written with no `a26_label`, and the per-era marker prevents a rerun, so the unlabelled file is the only evaluation result. On the Section 6 side, a joint writer that builds its result dict and forgets `period`, or copies `period="development"` from `s6_h2.development`, writes an unlabelled evaluation result with a valid sidecar.

**Mitigation observed.** The unit tests show the refusals that are implemented (`s6_tests_a34.py`, 5/5 pass). No evaluation writer exists yet, so nothing has been written unlabelled. A26 1d also covers tables, figures and sentences, which no code check reaches.

**Fix that stays outside the closure.** Have `load_eval` set a module flag when it allows a read, and have `write_once` require the label whenever the flag is set, whatever `period` says. Add a registry-style test that fails if any file other than `s5_eval_label.py` and the tests calls `run_confirmatory(`. Call `verify_labelled` from the Section 6 fingerprint or freeze-verification step as well.

### M4. NaN bootstrap resamples count as "not exceeding", which understates the H4 p-value: by 12% for the Gaussian H4b

**Where.** `section6/s6_lib.py:55` (`exceed` counts finite resamples only; the divisor is `nboot + 1`); `section6/s6_lib.py:216` (NaN when a fold is empty or a training set has one class); `AMENDMENT_A29.md:30` (rule 1d).

**What.** A29 1d prescribes this, so the code is compliant. FABLE_AUDIT noted it as harmless unless many resamples are NaN. The development run now gives the numbers:

| Test | Reported p | Valid resamples of 9,999 | p on valid resamples only |
|---|---|---|---|
| Gaussian H4a | 0.2842 | 9,651 | 0.2944 |
| Gaussian H4b | 0.5768 | 8,841 | 0.6523 |
| HSMM H4a | 0.1888 | 9,960 | 0.1895 |
| HSMM H4b | 0.0844 | 9,685 | 0.0871 |

The folds are contiguous in time and asset coverage starts late, so the earliest fold holds few usable rows and is the one a resample empties. The invalid resamples are therefore not random.

**Failure scenario.** In the joint evaluation an H4b p-value of 0.0078 is below the first Holm step, 0.0083, and is reported as a rejection. With 11.6% invalid resamples the p-value on valid resamples is 0.0088, which is not. The verdict depends on a convention that the real data show to be anti-conservative, in the same test that failed the null control (M1).

**Mitigation observed.** `n_valid_resamples` is in every result. No verdict in the development run changes.

---

## Low

### L1. The Section 6 registry scan runs only inside a unit test

`section5/s5_contamination.py:70-80` scans `section6/` only when `check_registry` is called with no folder. Every runtime caller passes a folder (`C.check_registry(HERE)` in `s5_mr2.py:29`, `s5_a22.py:83` and ten others), which scans `section5/` only. No Section 6 runner calls it at all (`s6_run.main`, `s6_h2.development`, `s6_a34.development`); the single no-argument call is `section6/s6_tests.py:172`. Scenario: a new `section6/s6_scratch.py` reads `load_development` and is never registered; every run still starts, and the gap shows only if someone runs `s6_tests.py`. Scripts in the repository root are not scanned in either mode.

### L2. The A31 rule 3 control flags real break effects, so a flag does not isolate the alarm filter

`section6/s6_run.py:299-325`. The reference set is drawn with the placebo matching and no alarm condition (`rule="none"`, line 308). It therefore holds times shortly after real alarms, which carry the break's own effect. The synthetic check shows this: with H4 planted and no filter bias, the control flags 12.5-22.5% of replicates per asset (`synth_validation_a31r.json`, `effect_h4`), against 4-7% under no effect. On the real data the Gaussian TLT flag is delta +0.030 [+0.008, +0.052], the sign expected if post-alarm times share the negative H3 gamma (-0.164). A31 3d reads a flag as "the alarm filter, not the break, moves the H3 outcome"; the report repeats that reading (`reply_latest.md:432`). The two sets also overlap, which shrinks delta towards 0. Scenario: the TLT flag is reported as a filter artefact that biases gamma down by 0.03, when it is at least partly the break effect appearing in the reference set.

### L3. H2 detector dependence recomputes the analysed detector with a different seed

`section6/s6_h2.py:185` seeds the primary with `"{detector}|primary"`; `:191` seeds the same detector's entry in `detector_dependence` with `"{fam}|dep"`. The two p-values differ by Monte Carlo noise: Gaussian TLT 0.904 against 0.876, gold 0.0370 against 0.0360; HSMM TLT 0.085 against 0.093. `verdict_agreement` (`:192`) is built from the second set. Scenario: in the joint run a primary p just under a Holm step is a rejection while the same detector's row in the agreement table says no rejection.

### L4. The H2 synthetic acceptance counts raw rejections; the test it certifies uses Holm

`section6/s6_h2.py:279-283` uses `reject_raw_0_05` for both the size and the "rejected in at least 80%" criteria. The primary is the Holm family of 4. In the first run (c = 0.05) raw rejection was 75% (TLT) and 80% (gold), and Holm rejection 62.5% and 65%. A33.1 then raised the planted shift to 0.08, after the failure, and the rerun passed at 95-97.5% on both counts. The change is disclosed and touches only the synthetic check. Scenario: the phrase "synthetic check PASS 13/13" is read as showing 80% power at the size first specified; at that size the Holm power was about 63%.

### L5. A32 was rewritten after adoption; A33 cites the superseded hash

A32 was adopted in commit `cde894d` with sha256 `d222539c...`. Commit `8821487` changed its "Dated" stamp and rewrote the sidecar; the file is now `7bc90d60...`. Ledger row 552 records the correction. `AMENDMENT_A33.md:27` cites A32 as `d222539c...`, which no file on disk matches. Scenario: an auditor checking A33's evidence table finds a hash mismatch and must go to git history to resolve it. It also shows that an adopted, hashed amendment can be changed in place and re-hashed; only git and a voluntary ledger row record it (FABLE_AUDIT L7, still open).

### L6. H4a covers fewer than half of the Gaussian H3 breaks

`section6/s6_run.py:72,87`: H4a units need `old_state == "0"`, the lowest-variance state. With K up to 4, "calm-to-stressed" in the break export means any move to a higher-variance state. Of 600 confirmed Gaussian calm-to-stressed breaks, 280 start in state 0; 277 start in state 1 and 43 in state 2. For the HSMM it is 365 of 549. H3 and H4b use all 600 and 549. This follows A31 2a as written. Scenario: H4a and H4b are read as two looks at the same breaks; for the Gaussian HMM, 53% of the H4b breaks are outside H4a.

### L7. `s6_coverage.py` kept the substring guard and the unconditional writer

`section6/s6_coverage.py:22` still tests `"Status: ADOPTED" not in`; `:57` and `:64` overwrite `coverage_sessions.csv` and `coverage_summary.json` with no sidecar, no provenance and no refusal. These files fix asset availability for every Section 6 result. `COLD_AUDIT_STATUS.md` lists FABLE M3 ("every Section 6 output") and L12 as resolved. The same substring guard remains in `s5_a23.py:21`, `s5_a24_clock.py:35`, `s5_a25_delay.py:21` and `s5_a27_confirm.py:23`, whose runs are finished. Scenario: a rerun of `s6_coverage.py` with changed thresholds silently replaces the availability table; development results then cannot be reproduced and nothing records the change. The result files record the script hashes but not the hash of `coverage_sessions.csv`.

### L8. The label wrapper can consume the one-shot evaluation run without a result

`section5/s5_eval_label.py:20-22` raises `TypeError` when `run_fn` returns anything but a dict. `s5_freeze.run_confirmatory` writes the per-era marker before `fit_fn` (`s5_freeze.py:53`). Scenario: `run_fn` returns a tuple or a results object; the era is fitted, the evaluation data are read, the wrapper raises, no result file is written, and the marker refuses a second run. A dry run of the wrapper with the real `run_fn`'s return type on development data would catch it.

### L9. The evaluation guard checks the fingerprint's sidecar, not the current code

`section5/s5_eval_loader.py:79-81` requires the fingerprint file to exist and to equal its sidecar. It does not call `s6_fingerprint.verify()`, so a Section 6 script changed after the fingerprint does not block an evaluation read. A28 6e only requires a later change to be reported as a deviation, so this is compliant. A32 6c relies on the fingerprint to cover the H2 code "before any evaluation-period run". Scenario: `s6_h2.py` is edited after the fingerprint; `load_eval(..., section6=True)` still passes, and the deviation is found only if someone runs `verify`.

### L10. The H2 gap choices were made after related results had been seen (disclosed)

A32 replaced the pre-registered H2 after the H3, H4 and A30 development results were known; A33 restored the protocol 5.0 statistic seven minutes later and made A32's statistic exploratory. The restoration is the right outcome. The 11 gap choices of A33 rule 2 (two-sided p, no burn-in, slot of T, pool from earlier and later sessions, no alarm exclusion) were still made after those results, as A33 states. The exploratory A32 statistic gives p of 0.0001-0.0005 for TLT and gold while the primary gives 0.04-0.90. Scenario: a reader gives the exploratory result the weight of the primary. The labels in the result files are correct; the risk is in the write-up.

---

## Status of the FABLE_AUDIT findings

| # | Claimed | Verified | Notes |
|---|---|---|---|
| M1 | resolved | Yes | `load_eval` and `eval_guard` take no override arguments; a test asserts both signatures and that an extra keyword raises. Residual: module constants can still be patched by any caller, and a direct `read_csv` of the panels is unguarded (now matched by the registry pattern, see L1). |
| M2 | resolved | Yes | `holm_family`: m = 6 always, non-evaluable p = 1; the test reproduces the audit scenario. `holm4` does the same with m = 4. |
| M3 | resolved | Mostly | `provenance()` and `write_once` are in every result writer except `s6_coverage.py` (L7). All 20 result files with sidecars verify. Ledger rows exist for the Section 6 code. |
| M4 | resolved | Partly | The pattern and the scan exist and the test can fail. The scan is not a runtime guard (L1). |
| M5 | resolved | Yes for rule 1 | `draw_placebos` uses alarms in [T_p - 60, T_p) only; a test checks that a later alarm is never used. The rule 3 control has the caveat in L2. |
| L1 | resolved | Yes | H4a placebos drawn with gap 0 for every unit; tested. |
| L2 | open | Open | Unchanged for H3 and H4. |
| L3 | resolved | Partly | See M3 of this audit. |
| L4 | resolved | Yes | `load_era` refuses before any read; tested. |
| L5 | resolved | Yes | Manifest lists A21-A34 with A33.1; a test pins them. |
| L6 | resolved | Yes | `load_era` caches through `Cache`; tested for a hit and for no stale hit. The Section 5 cache stamp exists with a sidecar; its preflight row was not re-run here. |
| L7 | open | Open | See L5 of this audit for a new instance. |
| L8 | disclosed | Yes | Recorded in A29. |
| L9 | open | Open | The Fed split and the positive control still use the 98 H1(c) events. |
| L10 | resolved | Yes | No post-S direction filter for H4a. See L6 for what the new sample covers. |
| L11 | disclosed | Yes | |
| L12 | resolved | Partly | `a29_guard` uses the manifest regex and sidecar. Five scripts keep the substring test (L7). |

---

## Code versus amendments A29-A34

| Amendment | Status / sidecar | Code checked | Match | Notes |
|---|---|---|---|---|
| A29 | ADOPTED, equal | `s6_lib.py:195-227`, `s6_run.py:154-165,425,449-454` | Yes | Per-fold AUC gain, weighted mean, folds fixed on original weeks, descriptive in-sample gain and both out-of-fold AUCs reported, 3c diagnostic untested. 1d has the measured cost in M4. The 3b intervals were computed post hoc and labelled so; all four lie below 0. |
| A30 | ADOPTED, equal | `s6_run.py:328-383` | Yes | Window [S - 30, T + 60], 5-minute bars aligned to S, 90th percentile of at least 10 placebo values, skipped windows counted, Fed split, chance reference from each placebo against the others. No test, outside Holm and BH. |
| A31 | ADOPTED, equal | `s6_lib.py:116-141`, `s6_run.py:72-100,276-325`, `s6_check_synth.py` | Yes | Rule 1, rule 2 (every state-0 streak start, label afterward, gap 0) and rule 3 as revised. The rule 4 check passed 29 of 29 under tag a31r; the first run's failure is kept on record. Rule 3 was revised after that failure, on the user's decision, and the amendment says so. |
| A32 | ADOPTED, equal (rewritten once, L5) | `s6_h2.py:26-120` | Yes, as exploratory | Deseasonalised absolute return with causal 20-session median, at least 10 sessions and 10 placebos, breaks resampled with their placebos. E1 categories and order as written. Superseded as primary by A33. |
| A33 | ADOPTED, equal | `s6_h2.py:124-200,224-318` | Yes | G1-G11 each implemented: mean signed return, one placebo per break per draw, two-sided add-one p, own session excluded, cut points from all candidates of the era, no alarm exclusion, fewer than 5 breaks not evaluable, m = 4 always, secondary horizons and other detectors in one BH family of 31. The planted window `R[T:T+30]` equals (T, T + 30] on the A28 clock. See L3 and L4. |
| A33.1 | ADOPTED, equal | `s6_h2.py:22` | Yes | Planted shift 0.08; first run kept. |
| A34 | ADOPTED, equal | `s6_a34.py`, `s6_lib.py:127`, `s6_run.py:463-470`, `s5_eval_label.py`, `s5_eval_loader.py:70-71` | Rules 1-2 yes; rule 3 partly | Per-asset mask applied after the SPY cut points; default draw unchanged (tested); joint TLT-and-HYG pool for the E1 chance reference; H3 sensitivity with BH of 4, outside Holm; results labelled post-diagnosis. Rule 3 is implemented as written, but what is written does not close the gaps in M3. |

Development results on disk agree with the report: no Holm rejection in the 6-test family or in the H2 family for either detector; H3 gamma negative for every asset; the positive control passes for both.

---

## Reproducibility: what was verified

- Sidecars of A21-A34 (15 files) equal the files. `s5_amendment_manifest.py --check` prints `freeze_ready: yes`.
- `METHODS_LEDGER.sha256` equals the ledger (9e586eff..., 589 lines), before and after the tests.
- `SECTION5_PROTOCOL.md` is unchanged (15be2570...). `COLD_AUDIT_STATUS.md` and `OPEN_AUDIT_FINDINGS.md` equal their sidecars. `FABLE_AUDIT.md` equals the hash cited in A31 and A34 (00512998...).
- No `section5_freeze.json`, no `ERA_CALIBRATION.lock`, no `eval_access_log.txt`, no `s6_fingerprint.json`, no `evaluation_*` file. The break export ends 2023-09-06.
- Every Section 6 result written since commit `9124c67` has a matching sidecar and a provenance block. The two A34 results carry the current code hashes. Earlier results carry the hashes of the code at their time, which differ from the current `s6_run.py` and `s6_lib.py` because A34 edited both; reproducing them needs the commit they were made at.
- Unit tests run (data-free): `s5_tests_ledger.py` 2/2, `s5_tests_freeze_prep.py` 12/12, `s6_tests.py` 30/30, `s6_tests_h2.py` 10/10, `s6_tests_a34.py` 5/5. All pass.
- Working tree: clean for tracked files; six untracked result and log files, as before the tests.

---

## Is anything blocking a pre-registration freeze?

Mechanically, no. Substantively, two items should be settled first and two more are cheap to settle first. The reason for doing all four before the freeze is the same: the freeze records the amendment list, and `load_eval` refuses if that list later changes.

**Settle before the freeze**
1. **M1.** Record a dated decision on the failed 7d null control: an amendment that either accepts the Gaussian H4b deviation with its reason, or states what happens if the Gaussian HMM is selected. A28 as written stops the work.
2. **M2.** Specify the joint-evaluation choices by amendment (placebo pools across the development and evaluation boundary, cut points, burn-in, evaluation coverage, evaluation break export, pooled or evaluation-only tests). Writing the joint code and its 5.13 driver before the freeze is better still, since a dry run on development data would also cover L8.

**Cheap to settle before the freeze**
3. **M3.** Tie the label check to an actual evaluation read and forbid direct calls to `run_confirmatory`. You asked for this to be enforced before the freeze; at present it is enforced only for callers that cooperate.
4. **M4.** Decide whether H4 p-values use the valid-resample divisor, or report both with one named as the verdict. This needs an amendment to A29 1d.

**Not blocking.** L1-L10. Of these, L3 (one seed for the analysed detector) and L7 (sidecar and write-once for the coverage files, plus their hash in the results) are small code changes that are easier before the Section 6 fingerprint than after it.
