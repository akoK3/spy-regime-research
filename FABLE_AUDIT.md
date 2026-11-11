# FABLE_AUDIT: independent read-only audit of Sections 5 and 6 since MR2, before the pre-registration freeze

Written 2026-11-10 (UTC). Auditor: Claude Fable 5.1, read-only. Nothing was edited, committed or run against market data; only the standard-library and synthetic unit-test suites were executed (ledger, freeze prep, A24, A25, A27, Section 6). Repository HEAD at audit time: `1a4505e` (2026-11-09 23:41 -05:00); working tree clean apart from four untracked result/log files under `section5/results/`.

Scope as requested: (1) look-ahead and leakage, (2) evaluation-period guard, (3) code versus amendments A21-A30, (4) statistics, (5) reproducibility. Findings are listed by severity with `file:line` and a concrete failure scenario. Items already recorded in `O9_AUDIT.md` (M1-M3, L1-L9) or `COLD_AUDIT_STATUS.md` are not repeated unless the state changed.

Note on scope: **AMENDMENT_A30.md does not exist** in the repository. A29 exists as a DRAFT (revised 2026-11-10 04:19Z) with no sidecar, which is the expected state for a draft. The audit therefore covers A21-A29.

---

## Summary

| Severity | Count | One-line summary |
|---|---|---|
| High | 0 | No path was found that reads 2019-2022 or 2025-2026 data, uses post-decision data in a feature, threshold, placebo or control in a way that is not pre-specified, or misreports a statistic. |
| Medium | 5 | Evaluation-data guard is advisory, not enforced (M1); Section 6 Holm silently shrinks the family (M2); Section 6 result files do not record their own code or A29 hash, and the ledger has no row for the current `s6_lib.py` / `s6_run.py` (M3); the contamination registry does not cover Section 6 or the new loaders (M4); Section 6 placebo filter conditions on SPY's future alarms and the null control cannot detect the resulting asymmetry (M5). |
| Low | 12 | Label-dependent placebo eligibility in H4a (L1); matched sets split across bootstrap blocks (L2); A26 label constant never attached (L3); joint-period loader order (L4); A29 absent from the freeze manifest (L5); finding-14 "fix" has no call site and Section 5 cache still keyed by name (L6); ledger integrity relies on git, not a chain, and dates follow the file stamp (L7); A29 statistic revised after a synthetic smoke test (L8); Fed flag limited to the 98 H1(c) events (L9); H4a sample filtered on post-S direction (L10); A27 r = 1 thresholds hit the bound (L11); "Status: ADOPTED" guards are substring checks (L12). |

Freeze-readiness state observed: `s5_amendment_manifest.py --check` prints `freeze_ready: yes` (A21-A28 ADOPTED, sidecars equal, A23 and A27 results present). No `ERA_CALIBRATION.lock`, no `section5_freeze.json`, no `eval_access_log.txt` (the evaluation loader has never been invoked). Code version is `a0323ed24d68e896`, equal to the MR2 completion record. Data-hash preflight: PASS 10/10 (2026-11-10 03:57Z). Pending before the Section 6 development run, per A29 rule 4c: A29 adoption, then the rule 1f power rerun (the queue log records the A28-statistic power run as stopped; no `power_*.json` exists).

---

## Medium

### M1. The evaluation-period guard is a convention, not an enforcement; two bypasses need no code change to the guard

**Where.** `section5/s5_eval_loader.py:60-80` (`eval_guard`, `load_eval`); `section5/s5_eval_loader.py:18` (`PANELS`); `section5/s5_contamination.py:58-68` (`DATA_LOAD`, `check_registry`).

**What.** The only code that refuses evaluation rows is `load_eval`. Its five checks (freeze sidecar and token, amendment list, era-calibration lock, finding-17 data-hash preflight, Section 6 fingerprint) are all injectable through keyword arguments: `load_eval(era, cols, fz, tok, preflight=lambda: 0, lock=<any existing file>, fingerprint=<any file with a matching sidecar>)` passes with no freeze-time state present. The tests use exactly this (`s5_tests_freeze_prep.py:65-77`). `s5_guard.py` follows the opposite principle ("paths are fixed module constants; tests patch them, callers cannot pass others", `s5_guard.py:3`). Separately, the panel files `section3_10_alignment_results/canonical_panel_*_1m.csv.gz` hold development and evaluation sessions in one file with no access control; any `pd.read_csv` of them returns 2019-2022 and 2025-2026 rows.

**Failure scenario.** A helper written for a Section 6 figure calls `EL.load_eval("LEGACY", cols, freeze, token, preflight=lambda: 0, lock=Path("results/coverage/coverage_summary.json"))` because the real preflight takes a minute; or a notebook reads the LEGACY panel directly to "check coverage in 2019". Either reads 800 exposed LEGACY sessions before the freeze. Nothing logs the second case; the first is logged as ALLOWED.

**Mitigation observed.** No production caller passes these kwargs; `s6_run.load_era` (`section6/s6_run.py:36`) calls `load_eval` without them, and `s6_run.main` refuses `joint` before any load (`s6_run.py:290`). `s5_lib.load_era` goes through `step3_all_in_one.CONFIG` spans and `assert_train_only` against the split manifest, which marks 2019-01-02..2022-03-04 and 2025-01-02..2026-10-12 as `EVALUATION_EXPOSED` (verified). `check_dev_spans` ties the loader's `DEV` to the same CONFIG text.

### M2. Section 6 Holm removes non-evaluable tests from the family instead of counting them

**Where.** `section6/s6_run.py:156-158` (`primary`); `section6/s6_lib.py:208-211` (`holm`).

**What.** `primary` collects the six primary p-values, keeps only those that are not `None` and finite, and runs Holm over that subset. `h3_test` returns `p=None` when fewer than 5 breaks have a usable row (`s6_run.py:103`), and `h4_test` returns `p=None` for fewer than 10 units (`s6_run.py:136`). The Section 5 convention (A15 rule 6a, `section5/s5_stats.py:33-38`) is that a missing p enters as 1 and counts in m. A28 rule 5b fixes the primary family at 6 tests.

**Failure scenario.** In the 2007+ sensitivity, the per-era Fed split, or a LEGACY-only offset run, USD (available from 2017-12-01) yields 4 breaks with next-day rows. Its H3 test is dropped and the remaining five are adjusted with m = 5: the first Holm step becomes 0.05/5 = 0.010 instead of 0.05/6 = 0.0083. A p-value of 0.009 on H3 TLT is rejected where the pre-registered 6-test family would not reject. The output does not say that m was 5.

### M3. Section 6 result files do not record the hash of the code or of A29, and the ledger has no row for the current `s6_lib.py` / `s6_run.py`

**Where.** `section6/s6_run.py:298` (writes `amendment_sha256` of A28 only); `METHODS_LEDGER.md` (the only Section 6 code row is `section6/s6_coverage.py`, line 487); `AMENDMENT_A29.md:11-12` (cites `s6_lib.py` 440201823..., `s6_run.py` 9bead281..., the A28-era code).

**What.** The current files hash to `s6_lib.py` 0eb3b2d7..., `s6_run.py` 3f59fed5... (the A29 code). These hashes appear only inside `section6/results/synth_validation_a29.json` (`code_sha256`), not in the ledger and not in any result that `s6_run.py` will write. A28 rule 6e fingerprints the code only before the joint evaluation, so the development run, which produces the results A28 6c protects, will be the one run without a code-hash record. `s6_run.main` records the A28 hash but not A29, although the statistic it computes is A29's.

**Failure scenario.** A later edit to `auc_gain_cv` (for example changing `POOL_OOF` at `s6_lib.py:204`) followed by a rerun of `s6_run.py development hsmm` overwrites `s6_development_hsmm.json` (`s6_run.py:299` writes unconditionally, no sidecar, no refusal to overwrite). Nothing in the result or the ledger shows which statistic produced the numbers in the paper.

### M4. The contamination registry does not scan `section6/` and does not match the new loaders

**Where.** `section5/s5_contamination.py:58` (`DATA_LOAD` regex), `:61-68` (`unregistered`, `check_registry` scan `folder=HERE` = `section5/` only).

**What.** `DATA_LOAD` matches `fold_segments(`, `load_era(`, `era_context(`, `splice_batch(`, `DataBackend(`, `EraBackend(`, `MainBackend(` and the `_init` calls. It does not match `load_development(`, `load_eval(` or `read_csv(`. `check_registry` globs `section5/*.py` only. `s6_run.py`, `s6_coverage.py`, `s6_power.py`, `s6_synth_validation.py` read data (or break records) and are not in the registry, and could not be flagged if they were missing because the scan never reaches them. A15 rules 2-3 made this registry the mechanism that resolved cold-audit finding 3 (unregistered scripts touching test segments).

**Failure scenario.** A new `section6/s6_scratch.py` calls `EL.load_development("LEGACY", cols)` and plots asset RV around the SPY breaks of every fold, including the contaminated ones, before A29 is adopted. `check_registry` passes in every Section 5 and Section 6 guard; the contamination list is not updated; the Section 6 development result is later reported as computed on uninspected data.

### M5. Section 6 placebo times are conditioned on SPY's future alarms, and the rule-7d null control cannot detect the asymmetry

**Where.** `section6/s6_lib.py:116` (`far` filter: `abs(S - a) > 60 and abs(S + gap - a) > 60` for every confirmed T_c of that session); `section6/s6_run.py:210-226` (`sanity`, null control draws fake breaks with `draw_placebos`).

**What.** A placebo at time S is eligible only if no SPY alarm confirms within 60 minutes after S (and after S + gap). This uses detector output from after the placebo's own decision time to define the control group. It is what A28 rule 1d specifies ("more than 60 minutes from any confirmed alarm"), so it is not a code defect, but it is a look-ahead inside the control construction: the placebo arm is guaranteed SPY-quiet for the next hour, the break arm is by definition not. The rule-7d null control replaces the breaks with times drawn by the same `draw_placebos` rule, so both arms of the null control are conditioned identically and the control cannot reveal a bias that comes from the asymmetry.

**Failure scenario.** Asset and SPY volatility co-move within the hour. For H3 rest-of-day (secondary) the placebo arm's post-T hour has no SPY confirmation and systematically lower asset RV; gamma is positive even if assets do not respond to SPY breaks beyond common volatility. The next-day primary outcome is affected through volatility persistence, more weakly. The 7d null control rejects at about 5% and is declared passed.

**Mitigation observed.** H3 controls include the asset's own prior-hour and prior-day RV and the S-to-T return, which absorb part of this. The synthetic validation's "vol" generator (runs cluster on high-volatility days) gave H3 null rejection 2.5-6.0%, but the generator has no intraday SPY-asset co-movement beyond the daily factor, so it does not exercise this mechanism.

---

## Low

### L1. H4a placebo eligibility depends on the label (gap = 10 for confirmed runs, 0 for fizzles)

`section6/s6_run.py:62` sets `gap = T0 - S` for confirmed units and 0 for fizzles; `s6_lib.py:113` requires `cand["S"] + gap <= 390` and `s6_lib.py:116` requires distance > 60 min from alarms at both S and S + gap. For the H4a test at point S, confirmed and fizzled units therefore draw their placebos under different filters, and the 90th-percentile cutoff that defines C(S) comes from a slightly different pool per class. Quantified from `breaks.csv`: the gap is exactly 10 minutes for every confirmed Gaussian break (722 of 722), and 67 confirmed breaks have S > 330, so the extra filter bites only for candidates within 60 minutes of an alarm at S + 10 but not at S, and for the last 10 minutes of the session. A28 1d ("each placebo carries the S-to-T gap of its matched break") prescribes this, so it is compliant; the synthetic null (gap always 10) gave H4a 5.0-5.5% rejection with the A29 statistic. Scenario: under a stronger alarm clustering in real data, confirmed units' placebo pools are quieter at S + 10, their cutoffs lower, C(S) higher, and H4a shows a gain that is a placebo-construction artefact.

### L2. Matched sets are split across bootstrap blocks; placebo rows can be duplicated

`section6/s6_run.py:102` assigns each row its own day's week, so a break and its 20 placebos (from earlier sessions) sit in different blocks and are resampled independently; the matched design is not preserved by the week-block bootstrap (`s6_lib.py:46-56`). The same candidate time can be drawn for several breaks (RAW has 14 confirmed Gaussian calm-to-stressed breaks drawing 20 placebos each from the same slot and decile pool), producing identical rows. Identical rows share a week and are resampled together, so the variance is partly accounted for, but the OLS n is overstated and the regression treats the 20 placebos per break as independent of the break. Scenario: in RAW, 280 placebo rows come from perhaps 150 distinct times; the reported `n_placebos` overstates the design, and the p-value's calibration rests on the week blocks absorbing the duplication.

### L3. The A26 rule 1d label is defined but never attached

`section6/s6_run.py:19` defines `LABEL_EVAL = "adaptive/exploratory (previously exposed period)"`; it is not referenced anywhere else in `section6/`. A26 1d requires every evaluation-period table, figure and sentence to carry it. Scenario: when the `joint` path is enabled, the result JSON carries `period="joint"` and no label, and a table built from it omits the required wording.

### L4. `load_era` loads evaluation rows before it refuses the joint period

`section6/s6_run.py:36-38`: for `period != "development"` it calls `EL.load_eval(...)` and only then raises `PermissionError("joint period: evaluation-period coverage must be computed through the guarded loader first")`. `main` refuses `joint` earlier (`s6_run.py:290`), so this is unreachable today. Scenario: once `main`'s refusal is lifted, a call with a valid freeze and token reads and discards the evaluation panel, is logged ALLOWED, and then fails; the access log shows an evaluation read that produced nothing, which a later auditor must explain.

### L5. A29 is not in the freeze manifest

`section5/s5_amendment_manifest.py:13` lists A21-A28. The freeze document will not record A29's status or hash, and `eval_guard` (`s5_eval_loader.py:64-65`) compares against that list. The Section 6 joint run depends on A29 (its statistic) but the dependency is enforced only by `s6_run.a29_guard` (`s6_run.py:279-282`), which checks the file at run time, not at freeze time. Scenario: the freeze is written with A29 still a DRAFT (A26 2b says it must not be, for amendments the 5.13 run depends on); A29 is then revised and adopted; the freeze cannot show which A29 text the joint run used.

### L6. Finding 14 "fix" has no call site; the Section 5 feature cache is still keyed by column name

`section6/s6_lib.py:16-32` defines `Cache` (key = column, code hash, panel hash) and `s6_tests.py:12-16` tests it, but no Section 6 module instantiates it (Section 6 computes nothing it caches). A28 6f states the finding-14 fix is "in new Section 6 code"; the statement is true but vacuous. `section5/s5_lib.py:127-131` still loads `cache/{era}_features.npz` by column name alone, and `s5_fast.load_bases` (`s5_fast.py:16-23`) likewise. Scenario: a change to `step3_all_in_one.construct` that alters a feature's values is not reflected in Section 5 runs until the npz is deleted by hand; the code version changes (the module is in the closure) so checkpoints are invalidated, but the cached features are not, and a "reproduction" recomputes with stale inputs.

### L7. Ledger integrity relies on git; dates come from the file's own stamp

`section5/s5_ledger.py:30-31` rewrites the sidecar after every `add`; rows are not chained (no row carries the previous row's hash), and `s5_tests_ledger.py` checks only that the sidecar equals the current bytes. `date_of` (`s5_ledger.py:15-22`) takes the "Dated" stamp inside the file, so the revised A29 draft (hash 1bcb5ee1..., added after the 04:19Z revision) is dated 2026-11-10 04:12:35Z, the same as the first draft's row. Scenario: a row edited in place and re-hashed with `s5_ledger add` passes the ledger test; only `git log -p METHODS_LEDGER.md` shows it. An auditor reading the two A29 rows sees identical times and cannot order the revision from the ledger alone. (O9 L9 noted the related first-timestamp issue; this is its other side.)

### L8. The A29 statistic was changed after a synthetic smoke test, in the same commit as its code

Commit `72e0d46` revises A29 rules 1b, 1c and 1g (pooled out-of-fold AUC to per-fold weighted mean; new size-reporting rule) and adds the code implementing them. `AMENDMENT_A29.md:3` discloses that the revision followed "a diagnostic made during the rule 2 smoke test" on a planted-H4 synthetic replicate. No real data was involved and A29 4a ("hashed into the ledger before its code") was met for the first draft. Scenario: a reader of the ledger row dated 04:12:35Z for the revised draft takes the per-fold statistic as the pre-specified one; the record of why it changed is only in the amendment text and the commit message. Recommend the adoption row cite the smoke-test numbers already in A29 1g.

### L9. Rule 7c "FOMC days" are only the 98 H1(c)-eligible events

`section6/s6_run.py:173-176` reads `h1c_event_release_minute_after_0930` from the contamination list; that dictionary holds release minutes for the 98 eligible events only (confirmatory folds, full 390-bar sessions, documented release time). FOMC days in contaminated folds, or with an unavailable release time, are treated as non-Fed. Scenario: the Fed-versus-non-Fed split (7c) and the positive control (7d-i) exclude Fed days whose release time was not documented, and the non-Fed arm contains Fed days; the positive control is weaker than intended and could fail for the wrong reason, stopping the work under 7d.

### L10. H4a units are filtered on a direction computed after S

`section5/s5_break_export.py:97` sets `direction` from the most likely state at the run's last update (T_c for confirmed, the fizzling update for fizzles); `section6/s6_run.py:152` keeps only `calm_to_stressed` runs for H4a. Both classes are filtered with post-S information, so the sample is defined retrospectively (consistent with A28 4f's disclaimer for labels, but 4b does not say the direction filter is also post-S). Scenario: a run that crosses the threshold at S towards the stressed state and then fizzles back to calm may be classified by its last update as `stressed_to_calm` and dropped, while the same run confirmed is kept; the fizzle class is thinned asymmetrically.

### L11. A27 r = 1 thresholds hit the search bound in 16 Gaussian and 16 HSMM folds

Recorded in the ledger row of 2026-11-10 04:33:52Z and in `results/a27/confirm_count.json` (`flagged`): at r = 1 the A7 bisection cannot reach 0.2 alarms per session within theta <= 30 (`section5/s5_a7.py:13,18`), and the realised test rate is 0.28/0.25. The r = 1 H1(c) differences are therefore computed at a higher alarm rate than r = 2, 3, 4 and are not comparable with them. The result file carries the flags; the ledger summary states the rates. Scenario: a table of H1(c) by r that omits the flagged folds' realised rates reads r = 1 as a stronger detector.

### L12. Adoption guards are substring checks

`section6/s6_run.py:281`, `section6/s6_coverage.py:22`, `section5/s5_a27_confirm.py:23`, `s5_a25_delay.py:21`, `s5_a24_clock.py:35`, `s5_a23.py:21` test `"Status: ADOPTED" in text`. `s5_amendment_manifest.STATUS` (`s5_amendment_manifest.py:15`) uses a regex anchored on the first `Status:` of a line, which is stricter. Scenario: a DRAFT amendment whose evidence table quotes another amendment's status line verbatim ("Status: ADOPTED 2026-11-09...") satisfies the substring guard and the run proceeds while the manifest still says DRAFT; the two guards disagree.

---

## Code versus amendments A21-A29 (item 3)

| Amendment | Status / sidecar | Code checked | Match | Notes |
|---|---|---|---|---|
| A21 | ADOPTED, sidecar equal | `s5_d7.py:62,109-110` (rule 1), `s5_mr2.py:80-82` (rule 2), `s5_step2.py` (rule 3) | Yes | NaN-ratio days skipped before any detector row is built; jump label distinguishes NaN from zero; Step 2 objective, pool, selection (`RUN.select_fold`), score (a) fold tests and BH over 4 families, score (b) gates i/iii/iv required and ii reported, all as written. |
| A22 | ADOPTED, sidecar equal | `s5_a22.py` all phases, `s5_d8c.py` | Yes | 3c thresholds and 0.20 reproduction; 3d delay (superseded by A25 for interpretation, kept as record); 3e seeds replace both start and splice seeds (`SeedMain(ph, s, s)`); 3f 69-column pool asserted; 3g grids (`Grid`, `dmax=390//g`, DM lag `60//g`); 3h projection gate; 4a `mde` with n = 26 (O9 L1, fixed by `s5_power_observed_n.py`); 4b binomial D7 MDE as disclosed; 1b D8c cutoffs 2 / 0.5. |
| A23 | ADOPTED, sidecar equal | `s5_a23.py` | Yes | Forced inputs, not-evaluable rule, 5.8 tuning via validation objective with 3 starts, baseline equality, A7 thresholds, 1e reproduction checks (same-setup effects, baseline QLIKE mean on MR2's bar set, baseline alarms), H1 on 34 folds with Holm, D7 on 26 confirmatory folds only, H1(c) and liquidity QLIKE secondary. Labelled EXPLORATORY in the result and ledger. |
| A24 | ADOPTED, sidecar equal | `s5_a24_clock.py` | Yes | T_c + c on LEGACY folds for feature and baseline, RAW 0 unchanged, reference rates with the same shift, 0.20 primary and 0.15/0.25 secondary, c = 0 reproduction, changed-event counts. |
| A25 | ADOPTED, sidecar equal | `s5_a25_delay.py` | Yes | H1(a): unshifted times, window 60 - delta (`sweep_old_state(..., window=)`), null counts computed once; H1(c): window [release, release + 60 - delta] for hits and reference rates; delta 0 reproduction; A22 result cited by hash and labelled superseded. |
| A26 | ADOPTED, sidecar equal | `s5_amendment_manifest.py`, `s5_run.freeze_step` (unchanged), `s5_freeze.build_freeze` | Partial | 2b/2c: manifest produced outside the closure and passed through the existing `amendments` argument; closure unchanged (code version verified). 1d label: no code attaches it (L3). 2b lists A21-A28 (A27/A28 added later), not A29 (L5). |
| A27 | ADOPTED, sidecar equal | `s5_a27_confirm.py`, `s5_tests_a27.py` | Yes | r passed as `run=` / `hold=` to existing functions; thresholds re-bisected per r on validation; H1(a) and null axis from the same sweep; H1(b) taken from MR2; H1(c) at recalibrated thresholds; r = 3 reproduction of thresholds, alarms, effects, fold tests and H1(c); development folds only. Result exists (`results/a27/confirm_count.json`, ledger row). |
| A28 | ADOPTED, sidecar equal | `s6_lib.py`, `s6_run.py`, `s6_coverage.py`, `s6_power.py`, `s6_fingerprint.py`, `s5_break_export.py` | Mostly | 1c clock and 1d placebo rules, 3b controls, 3c week-block bootstrap within era, 4a C(t) windows, 4d label, 5a-5c multiplicity structure, 6b label-free coverage, 6e fingerprint, 7a-7f analyses are implemented as written. Deviations: Holm family shrinks when a test is not evaluable (M2); coverage thresholds (0.80 / 30 min / 25%) and the 30-minute placebo slot are not in A28 and were set by the code then approved (ledger row 2026-11-10 03:42Z, consistent with 6g); finding-14 fix is a class with no call site (L6); 7c Fed definition narrower than "FOMC days" (L9); 6d power check not yet produced (pending A29 1f). |
| A29 | DRAFT, no sidecar (expected) | `s6_lib.py:169-204`, `s6_run.py:130-141,253,279-282` | Yes | 1a contiguous week blocks per era (`cv_folds`); 1b/1c per-fold AUC gain, weighted mean, one-class folds dropped (`POOL_OOF = False`); 1d bootstrap keeps each row's fold and counts NaN as not exceeding; 1e every H4 test routes through `h4_test`; 1g both models' out-of-fold AUC and the in-sample gain reported; 3c descriptive H3 with the prior-hour control over (S - 60, S]; 4b development run refuses until ADOPTED with sidecar. Rule 2 acceptance check run and passed (`synth_validation_a29.json`: H4a 5.0% / 5.5%, H4b 1.5% / 1.0%, planted H4 bias -0.003 / +0.002). 1f power rerun pending. |
| A30 | absent | n/a | n/a | No such file. |

---

## Statistics (item 4)

- **Holm** (`s5_stats.py:33-38`): step-down with running maximum and the A15 6a rule (NaN enters as 1, counts in m, never rejected). Correct. `s6_lib.holm` (`s6_lib.py:208-211`): adjusted values correct (`[0.01,0.04,0.03] -> [0.03,0.06,0.06]`), but the caller drops non-evaluable tests (M2).
- **Benjamini-Hochberg** (`s5_stats.py:41-48`, `s6_lib.bh`): descending cumulative minimum of p·m/rank. Correct. Section 5 drops NaN p from m, which is the usual BH convention; Section 6 is applied over all finite secondary p-values (`s6_run.py:264-265`).
- **Intersection-union** (`s5_stats.py:28-30`): p = max(p_a, p_b), NaN if either missing. A valid level-alpha IU test. Used on the two block-bootstrap p-values (`s5_h1.py:42`).
- **Block bootstrap** (`s5_stats.py:10-17`): moving blocks of 3 consecutive folds, non-circular, centred fold effects, one-sided p with add-one, 10,000 resamples, seeds 0 (H1a) and 1 (H1b). Correct; with 22 folds, 8 blocks of 3 are drawn and truncated to 22, which is standard. The Section 6 variant (`s6_lib.week_block_bootstrap`) resamples calendar weeks within era, centred (`(s - t) >= t`), add-one, NaN counted as not exceeding (anti-conservative only if many resamples are NaN; `n_valid_resamples` is reported). Correct as specified by A28 3c and A29 1d.
- **Minimum detectable effect** (`s5_stats.mde`): simulated normal fold effects, the same block bootstrap at 500 resamples, 400 simulations. Correct. O9 L1 (n = 26 instead of 22) is addressed by `s5_power_observed_n.py`.
- **Cross-validated AUC (A29)** (`s6_lib.auc_gain_cv`, `cv_folds`): both logistic models (Newton, ridge 1e-6, 50 iterations, clip at ±30) fitted on four folds, evaluated on the fifth; per-fold AUC by midranks (`scipy.stats.rankdata`); weighted mean by fold size; folds with one label class skipped; NaN if a training set has one class or a fold is empty. Matches A29 1a-1d. Two numerical notes, both minor: inputs are not standardised, so the uniform ridge acts about 1% on the SPY-return coefficient (scale 1e-3) and essentially not at all on log RV and C; Newton has no step control, so a separable fold can produce huge coefficients, which the clip turns into a finite but degenerate AUC rather than NaN. Unit test `test_oof_gain_unbiased_under_null_and_detects_signal` passes (null mean within 0.01 of 0; signal gain > 0.1).
- **Diebold-Mariano** (`s5_eval.py:199-206`): Newey-West HAC with Bartlett weights, lag 12 (60 min / 5 min), one-sided normal p. Correct; reported per fold, not used for inference.
- **Day-clustered CI for D7** (`s5_d7.cluster_diff`): multinomial resampling of clusters, percentile interval. Correct.

---

## Evaluation-period guard (item 2): paths checked

| Path | Reads which sessions | Guard | Verdict |
|---|---|---|---|
| `s5_lib.load_era` -> `step3_all_in_one.load_development` with `CONFIG` spans (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23) + `assert_train_only` against `section430_executable_split_manifest.csv` (TRAIN only; EMBARGO and EVALUATION_EXPOSED refused) | Development only | Enforced by assertion | Safe |
| `s5_backend.DataBackend` / `MainBackend` / `EraBackend` (fold segments from the A4 folds CSV; latest outer_development_last 2018-12-21 / 2024-12-23) | Development only | Fold table + `assert_train_only` | Safe |
| `s5_eval_loader.load_development` (chunked, rows outside DEV discarded, `check_dev_spans` ties DEV to CONFIG text) | Development only | Date filter + consistency check | Safe |
| `s5_eval_loader.load_eval` | Evaluation | Five checks, all injectable by kwargs; access log | Advisory (M1); never invoked (no access log) |
| `s6_coverage`, `s6_run development`, `s6_power`, `s5_break_export` | Development only (`load_development`, break records of confirmatory folds, test segments) | Inherits the above | Safe |
| `s5_freeze.run_confirmatory` | Injected `fit_fn` / `run_fn`; no implementation exists yet | Freeze sidecar, token, per-era marker | Not yet reachable |
| Direct `pd.read_csv` of the panels | Anything | None | Possible by construction (M1, M4) |

---

## Reproducibility (item 5): what was verified

- Amendment sidecars A21-A28 equal the files on disk (recomputed). A29 has no sidecar (DRAFT). The hash cited for A22 inside A23/A24/A25/A26 (3ce7b683...) and for A26 inside A27/A28 (50bcbc04...) equal the files on disk. A28 cited in A29 (7c6bd4bd...) equals the file.
- `METHODS_LEDGER.sha256` equals the ledger bytes before and after running the ledger tests (0b8fb148...). Both ledger tests pass. The A29 rows carry a1383b6e... (first draft) and 1bcb5ee1... (revised draft, equal to the file on disk).
- `SECTION5_PROTOCOL.md` is FROZEN with sidecar 15be2570..., equal to the MR2 completion record's `protocol_sha256` and to the hash in every amendment's evidence table. The contamination list sidecar f6d67a57... equals the file and the hash stated in protocol 5.14.
- Code version recomputed from the 25-module closure: `a0323ed24d68e896`, equal to the MR2 record, to `s6_fingerprint.CODE_VERSION` and to the value every post-MR2 checkpoint tag carries. MR2 `run_complete.json` equals its sidecar (19812f9f...).
- Data-hash preflight (finding 17): PASS 10/10 at 2026-11-10 03:57Z, recorded in `results/breaks_preflight/data_hashes.json`.
- Section 6 code on disk equals the hashes recorded by the A29 acceptance run (`synth_validation_a29.json`), so the acceptance check ran on the code that would run development. Git working tree is clean for tracked files.
- Unit tests run (data-free): `s5_tests_ledger.py` 2/2, `s5_tests_freeze_prep.py` 11/11, `s5_tests_a24.py` 2/2, `s5_tests_a25.py` 5/5, `s5_tests_a27.py` 6/6, `section6/s6_tests.py` 19/19. All pass.
- Break export: ledger row states every fold's confirmed runs equal the MR2 A17-style alarm records (asserted in `s5_break_export.fold_rows:116`, exit 4 on mismatch); 15,199 runs, days 2004-01-09..2023-09-06 (development only).

Gaps: Section 6 development results will not carry their own code hash (M3); the ledger has no row for the current `s6_lib.py`, `s6_run.py`, `s6_power.py`, `s6_synth_validation.py` or `s6_fingerprint.py`; no sidecars are written for `s6_run` outputs and the file is overwritten on rerun; Section 5 feature caches are keyed by name (L6).

---

## Verified, no finding (look-ahead and leakage, item 1)

- A25 delay scoring: data times unshifted, hit window shortened (fixes O9 M1). A24 moves T_c only, against the external FOMC clock. A27 recalibrates thresholds on validation and scores on test splices with the saved models. A23 tunes on validation, scores on test; the forced inputs were chosen after MR2 and Step 2 results and the amendment says so (EXPLORATORY).
- D7 (A21): the NaN-ratio exclusion is applied before any detector sees the day and depends only on the injection's arithmetic, not on outcomes. Positive-control splices use post-tau data only to set the injected ratio (by design).
- Section 6 clock: `rv`/`cumret` use returns with index i where i + 1 <= t (bar stamped m available at m + 1); H3 controls at T use (T - 60, T], the prior session, and S-to-T; C(S) uses (S - 15, S); C(T) uses (S, T]; SPY information at t uses data to t. `test_h3_controls_and_c_score` confirms that later values do not move them. Decile cut points for placebo matching come from candidates in sessions before the break's session; `test_future_does_not_move_deciles` confirms it.
- Labels: the real-break label uses the next session by construction and A28 4f discloses it; the deseasonalised RV baseline is the causal 20-session median.
- Section 6 placebo and candidate construction never reads asset data; coverage is label-free (`test_label_free`).
- Break export direction and size use TRAIN-fitted parameters and filtered probabilities; `prior_calm_min` uses filtered states before S.
- The era-calibration path (`s5_era_threshold.py`) uses the last 58 TRAIN sessions with a 5-session embargo and writes the lock before the first fit.

---

## Recommendations before the freeze (ordered by the severity they address)

1. (M1, M4) Add `load_development(`, `load_eval(` and `read_csv(` of the panel paths to `DATA_LOAD`, scan `section6/` as well as `section5/`, register the Section 6 scripts, and either remove the guard kwargs from `load_eval` (patch module constants in tests, as `s5_guard` does) or make them refuse outside a test runner.
2. (M2) In `s6_run.primary`, enter a non-evaluable primary test as p = 1 with m = 6 (the A15 6a rule), and write m into the result.
3. (M3) Have `s6_run.main` record sha256 of `s6_lib.py`, `s6_run.py`, A28 and A29 in the result, write a sidecar, refuse to overwrite, and add ledger rows for the current Section 6 code before the development run.
4. (M5, L1, L2) State in the Section 6 write-up that placebo times are conditioned on no SPY confirmation in the following hour, that the null control shares this conditioning, that matched sets are not preserved by the week-block bootstrap, and report the number of distinct placebo times per era.
5. (L3, L5) Attach `LABEL_EVAL` to every joint-period output and add A29 to `AMENDMENTS` once adopted so the freeze records it.
6. (L7, L8) Add the smoke-test numbers to the A29 adoption row and consider writing the previous ledger sidecar hash into each new row (a minimal chain).
