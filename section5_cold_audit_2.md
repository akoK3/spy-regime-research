# Second cold audit of `section5/`: 15 problems, 1 critical, 4 high

**Before the main run, the contamination guard, the checkpoint versioning and the run path itself need fixing.** First, two folds that the protocol's own rule excludes are still in the confirmatory set. Second, the unit test meant to catch unregistered data scripts can never fail. Third, a resumed run can silently reuse results from older model code. Fourth, the baseline gets no hyperparameter tuning of its own, which biases H1 towards the feature models. Finally, no code yet exists to run the main analysis or to set the era-level thresholds for the freeze.

I found no look-ahead in the filters, events, targets, deseasonalisation or preprocessing. I also found no leakage from test into selection inside a fold.

**Scope:** `SECTION5_PROTOCOL.md`, frozen through A14.2, at commit `bedc2ce`. The protocol's sha256 `313fd3db…bd453` matches its sidecar. I also reviewed `OPEN_AUDIT_FINDINGS.md` and `COLD_AUDIT_STATUS.md`. Nothing was fixed. The only file added is this report. The working tree was clean before and after.

**Severity** (same scale as `section5_cold_audit.md`):
- **Critical:** can produce a wrong confirmatory conclusion without any error.
- **High:** breaks a protocol rule on leakage, or blocks the planned run.
- **Medium:** a real deviation or risk with a limited or conditional effect.
- **Low:** small, currently inactive, or record-keeping.

**Evidence:** "Measured" means I ran it for this audit. "Read" means I established it from the code or documents. No data were scored: I fitted no model and ran no detector, and I read no test or evaluation output.

## Critical

### 1. The baseline is never tuned; it inherits the K/lambda tuned for the feature model (read)
**Where:** `section5/s5_backend.py:99`, `section5/s5_run.py:45-49`, `section5/s5_select.py:44-51`; protocol 5.2, 5.8

- 5.2 says baselines get the "same architecture and hyperparameter budget".
- `select_fold` tunes K (or lambda) over the grid, with 3 starts, for the selected feature set only.
- `score()` then fits the baseline with the parameters chosen to minimise the feature model's validation QLIKE: `self.fit(family, (), params, 3)`. The baseline never gets its own search over the {2, 3, 4} / {2, 3} / {12, 39, 78} grid.
- So the baseline has a tuning budget of zero, and the K it gets is selected for the opponent. Both H1(a) and H1(b) are features-minus-baseline contrasts, so any K mismatch counts as feature skill.
- I did not measure the size. It is zero in folds where the baseline's own best K happens to equal the feature model's, and it is never negative in expectation.

## High

### 2. Two LEGACY folds the protocol excludes are in the confirmatory set: 23 and 24 (measured)
**Where:** `section5/s5_contamination.py:16-23` (registry), `section5/results/contamination_list.json`; protocol 5.14

- The first cold audit fitted all detectors on LEGACY fold 25's inner train (2015-07-09 to 2016-04-07). It then scored them on placebo and null splices built from fold 25's validation stable days (2016-04-08 to 2016-07-07). Its scripts are `x4_placebo.py:55-84` and `x5_robust.py:14-28` in that audit's scratchpad. The results are the LEGACY 25 rows of `section5_cold_audit.md` finding 1, which led to A8 item 1.
- Under 5.14, that run touched those sessions on three counts: it fitted models on them, it scored detectors on splices built from them, and it used them for a statistic that informed a protocol decision.
- The run is in no registry. Re-running `s5_contamination.touched` and `exclusions` with it added (fold 25, train and validation) excludes **LEGACY 23 and LEGACY 24** (121 touched test sessions each), as well as the current six.
- The confirmatory set should be 26 folds, not 28. H1(c) loses the 8 eligible events in those folds (4 + 4), leaving 98 of 106.
- At minimum LEGACY 24 is affected: fold 25's validation block lies entirely inside fold 24's test block. LEGACY 23 is affected through the inner-train fit.

### 3. The contamination registry's unit test can never fail, and three data-loading scripts are unregistered (measured)
**Where:** `section5/s5_tests.py:413`, `section5/s5_contamination.py:16-23`

- The regex on line 413 contains two literal backspace bytes (0x08), before `fold_segments` and before `load_era`; `od -c` shows `r"\bfold_segments\(|\bload_era\("` with real `\b` characters. It was probably written through a non-raw string by a writer script.
- So the regex matches no file. `test_every_data_loading_script_is_registered` passes without checking anything (it runs and reports OK).
- With the intended regex, three files load data and are missing from `REGISTRY`:
  - `s5_a8_gate_seeds.py` (A8.3 runs: RAW 3, LEGACY 29)
  - `s5_a8_loo.py` (A8.4 runs: LEGACY 29)
  - `s5_backend.py`
- Scripts that load data through `DataBackend` (`s5_machinery_run.py`, `s5_a14_diag.py`) don't match the regex even when it works.
- Today this changes nothing: every unregistered run I found touched only RAW 3 and LEGACY 29, which are already excluded. But the guard 5.14 relies on is not working. This is why finding 2 went unnoticed. Finding 3 of the first audit should not be marked resolved (see the classification section).

### 4. Checkpoint versions omit the model, event, sweep and backend code, so stale fits can be reused (measured)
**Where:** `section5/s5_run.py:18` (`CODE_FILES`), `:32`

- `CODE_FILES` covers `s5_select, s5_stats, s5_h1, s5_freeze, s5_run, s5_a6, s5_eval`. It leaves out the files that determine every fitted number: `s5_models.py`, `s5_events.py`, `s5_sweep.py`, `s5_backend.py`, `s5_lib.py`, `s5_fast.py`, `s5_d2.py`, `s5_d2_stable.py` and `s5_a7.py`. It also leaves out the feature caches, which are discussed under finding 14.
- **Evidence:** A13 changed only `s5_models.py` among result-determining files (EM tolerance 1e-6 per observation, cap 500). The A12 and A13 machinery runs on RAW 3 have the same `code_version` (`3807921739fee3b8`) and identical checkpoint filenames.
- A13 used a fresh directory, so nothing was reused. Had it resumed in `a12_machinery_RAW3/`, all 8 units would have been served from the A12 code without any error.
- A14.2 changed `s5_models.py` and `s5_backend.py` as well. The current version `7e21c579…` differs from A13's only because `s5_run.py` and `s5_h1.py` also changed.
- The key also leaves out the backend's identity and `budget` (`select|fold|family`). A synthetic run and a real run in the same directory would therefore collide.
- So finding 11 of the first audit ("resolved") is only partly fixed.

### 5. The main run and the freeze have no code path; the existing one would set thresholds on the wrong sessions (read)
**Where:** `section5/s5_backend.py:21-23,106-113`, `section5/s5_run.py:58,74-78`, `section5/s5_era_threshold.py`; protocol 5.12, 5.13

- `DataBackend` raises `PermissionError` for every fold not on the contaminated list (line 23), whatever `allowed` is set to. It also serves one fold (`folds() -> [self.id]`).
- No multi-fold real-data backend exists; the only other one is `SyntheticBackend`. The main run therefore needs new code that this audit and the earlier ones have not seen.
- `freeze_step` calls `backend.final_thresholds(e, fam, …)` for every era `e` on the single backend it is given. `DataBackend.final_thresholds` ignores its `era` argument and bisects on its own fold's validation sessions.
- 5.12 and 5.13 require the era-level rule (A11 item 1) instead: `EraBackend.calibrate` on the last 58 TRAIN sessions. `freeze_step` never calls `EraBackend`. Unless the new backend routes `final_thresholds` to `EraBackend`, the freeze document would record fold-validation thresholds. For a multi-era backend, LEGACY setups could also be calibrated on another era's sessions.
- `run_all(excluded=())` defaults to no exclusions. Nothing forces the caller to pass `excluded_from_contamination(...)`. If the argument is omitted, the "confirmatory" verdict silently covers all folds.

## Medium

### 6. Holm drops a non-evaluable family from m, which makes it less conservative than "across the three families" (measured)
**Where:** `section5/s5_stats.py:35`, `section5/s5_h1.py:44-46`; protocol 5.11

- A NaN IU p-value is removed from the family count. With p = .020 / .024 / NaN, both remaining families are rejected (adjusted p .04). With the third family at p = .90, neither is rejected (adjusted p .06).
- A family's p-value is NaN when either component has fewer than 2 finite fold effects. That is unlikely with 26-28 folds, but it is not a rule the protocol states.

### 7. H1(a) records a zero effect, not a skip, when splice construction fails on a fold with 8 or more stable days (measured)
**Where:** `section5/s5_backend.py:80,101-102`, `section5/s5_h1.py:20`

- If `build_specs_safe` returns no specs (for example, "break pair" after 500 failed draws) while `n_stable >= 8`, the backend sets both curves to `[]`. `h1a_fold_effect` then returns `effect = pauc([]) - pauc([]) = 0.0` with `skipped=None`.
- The reason string `why` is discarded. The fold enters the bootstrap as a true zero.

### 8. The freeze records no data-input hashes and no amendment after A10 (read)
**Where:** `section5/s5_backend.py:115-119`; protocol 5.12

- `input_hashes()` hashes the protocol, A6-A10 and the folds CSV.
- It leaves out:
  - A11, A12, A13, A14, A14.1 and A14.2
  - five of the six cited input files: the 4.3.9 matrix v2 and its views, `a4_folds_check.json` and the LM calibration
  - the market-data panels and the feature caches
- 5.12 freezes "final setups, thresholds … and hashes". The `OPEN_AUDIT_FINDINGS.md` text for finding 17 ("the backend records hashes for the freeze only") overstates what is recorded.

### 9. 5.14's "used it for a statistic that informed a protocol decision" is unbounded for label-free statistics (read)
**Where:** protocol 5.14; `section5_cold_audit.md` finding 4

- The first audit counted stable test days on every LEGACY fold's test segment (finding 4), and that count fed A8 item 3.
- Read literally, 5.14 would make every fold's test segment touched. Read as intended, label-free counts (no detector, no outcome) are exempt.
- The protocol doesn't say which reading applies, and the contamination code implements the second one without saying so. One sentence in an amendment would settle it.

## Low

10. **The Student-t model keeps the last attempt, not the best one, when all 10 fail the 1% rule (read):** in `section5/s5_models.py:198-209`, the state saved per start is the 10th attempt's. A14.2 says "the highest-likelihood fit is kept and flagged".
11. **Greedy selection adds features on non-finite QLIKE (measured):** at `section5/s5_select.py:37-38`, if the current and best QLIKE are both `inf`, `gain` is NaN, so `gain < 0.01` is False and the feature is added. An all-`inf` objective selects 6 features.
12. **The block bootstrap crosses the era boundary (read):** `family_result` passes LEGACY then RAW folds as one sequence (`section5/s5_h1.py:35`), so a block of 3 can span LEGACY 26 → RAW 0. This extends the disclosed remainder of finding 4, which mentions only gaps from skipped folds.
13. **Flagged-fit counts and EM cap hits are missing from `run_summary.json` (measured):** `section5/s5_run.py:64-71`. 5.4 requires flagged fits to be "counted in every report" and cap hits "reported per family". Only `s5_machinery_run.py` computes them, from backend internals, and `_per_fold` is added after the summary is written.
14. **Feature caches have no version key (read):** `section5/s5_lib.py:112-116` and `section5/s5_fast.py:16-23` (`{era}_features.npz`, `{era}_bases.npz`) are keyed by column name only. If the feature code or the panel changes, the cached columns are reused.
15. **5.16 overstates the backend guard (read):** it says the backend "refuses … any session outside a fold's own segments". `section5/s5_backend.py:35` builds grid rows for every session of the era. This is needed for the 20-session deseasonalising history and is not leakage, but the statement is wrong.

## Are the 8 open findings classified correctly?

| # | Listed | My view | Why |
|---|---|---|---|
| 10 | Medium, open | Agree | Affects the sensitivity set only; the code is unchanged (`s5_lib.py:195-201` is still never called). |
| 12 | Medium, open | **Low** | It is a record-only overstatement with no effect on any computed result, which is Low on this scale. Coverage still has a gap: no test checks the splice builder for leakage. |
| 13 | Medium, open | Agree | It blocks only the 5.10 ±0.05 analysis. |
| 16 | Low, open | Agree, **wider scope** | Flagged-fit counts and EM cap hits are also missing from run outputs (finding 13 above). `VERSIONS` holds numpy only and is unused, and `L.shares()` is never called by the backend. |
| 17 | Low, open | **Medium** | The freeze document records no data-input hashes and no amendment after A10 (finding 8). The "What it affects" text is inaccurate. |
| 18 | Low, open | Agree | Event, QLIKE and direction rules don't depend on state order. |
| 20 | Low, open | Agree | The main path doesn't call `V.events_for`. The backend overwrites `D2._W`, so `s5_d2._init`'s hard-coded RAW isn't reached. |
| 21 | Low, open | Agree | `assert_pool(..., "sensitivity")` has no era argument. |

**Findings marked resolved that are not:**
- **11 (checkpoint keys): reopen as High.** Finding 4 above shows that `CODE_FILES` misses the model, event and backend code, with A12 and A13 sharing a version.
- **3 (evidence inside earlier test blocks): reopen as High.** The mechanism has a gap (finding 2: LEGACY 23/24), and its regression test is vacuous (finding 3).
- **19 (bad Student-t start): resolved, with a Low residual** (finding 10 above).

**Statements in the records that are now wrong:**
- `OPEN_AUDIT_FINDINGS.md` and protocol "Open items": "None of the open ones changes the primary detection or QLIKE computation". That is true of the 8 as listed, but not once 11 is reopened.
- Protocol 5.14: "28 folds confirmatory" and "106 eligible events". The rule gives 26 and 98.
- `COLD_AUDIT_STATUS.md` row 6 still describes "absolute tolerance 1e-4 nats … 200 cap", which A13 superseded (1e-6 per observation, cap 500).
- The protocol and status list count "4 disclosed" but list five numbers (1, 2, 4, 5, 8). Finding 4 is marked resolved in the table and disclosed in the summary line.

## Checked and clean
- **Look-ahead in model code:** all four filters are forward-only. HMM, Student-t and HSMM skips are transition- or hazard-only, and BOCPD skips are hazard-only with statistics unchanged. Session reset uses `pi` at duration 1. The QLIKE target uses bars s0+1 … s0+60, after the decision bar's availability, and the target window ends at 15:00 (12:00 on early closes).
- **Fold isolation:** `Prep` (winsorisation, log rule, Amihud, z-score) is fitted on inner-train rows only. `state_values` come from inner-train filter output. Selection reads only validation, and the test segment is read only in `score()`, after selection. The deseasonalising scale uses the previous 20 sessions only.
- **Events and sweeps:** `detect_old_state_logodds` and `sweep_old_state` match 5.5 and A12 (no re-basing in refractory, T_d strictly after tau, open runs counted). The BOCPD MAP rule matches 5.5. pAUC implements y(x) = max y at rate ≤ x over [0, 0.5].
- **Splices:** `regime_panel` scales B's returns, ranges and prices by f after tau and leaves volume unchanged. Sandwich tails are price-continuous. f uses A's units (A8 item 1). `tau_cap` matches A12 finding 9.
- **Statistics:** the IU p-value is the max of the two components, the DM test uses Newey-West lag 12, the Wilson interval is correct, and the sign test is exact and two-sided. The A9 simplicity order is in `h2_primary`, and the final-setup median uses round half up.
- **Era split:** `era_split` gives fit 0…n-64, a 5-session embargo and 58 calibration sessions, as A11 states.
- **H1(c):** the release-time hierarchy follows A11 and A12 (statement page, then press-conference page, then 14:15 before April 2011 or 14:00 from 2013, otherwise excluded). Each date counts once, and only 390-bar days are used.
- **Freeze guards:** no overwrite, refusal if `evaluation_*` exists, the token must equal the freeze sha256, and there is one marker per era.
- **Unit tests:** `s5_tests_run`, `_a11`, `_a12`, `_a13`, `_a14` and `_build`, plus `s5_tests.TestA8Items25`, all pass (the last vacuously, see finding 3). The tree was unchanged afterwards.

## Not audited
- The future main-run backend and its `fit_fn` / `run_fn` for `run_confirmatory`: they don't exist yet (finding 5).
- H2, S1, S2, E1, E2 and D1, the 5.10 robustness runs, and the power simulations, none of which is implemented.
- Section 4 feature code and LEGACY clock semantics (outside `section5/`). Both were covered by the 30 October audit.
- The size of finding 1: measuring it would need a scored run on a fold, and I ran none.

## Suggested order before the main run
1. Settle findings 1 and 5. Both change the code the run depends on.
2. Add the first audit's LEGACY 25 run to the registry. Fix the regex and register `s5_backend.py`, `s5_a8_gate_seeds.py`, `s5_a8_loo.py`, and the backend-mediated scripts. Regenerate the contamination list.
3. Version checkpoints with every result-determining file and the feature caches.
4. Amend the records for the reclassifications above, under the protocol's dated, hashed amendment rule.


---

# Re-audit after A15 (commit `b3c400d`): 9 of 9 items fixed, 3 only in part; 6 new problems, none critical

**Every item 1-9 is fixed as A15 states it. Three fixes have gaps: the registry check (item 3), the checkpoint version (item 4) and the main-run guards (item 5).** The guards protecting the main run can be bypassed by calling a lower-level class, by passing a different contamination list, or by setting a flag. None of the new problems changes a number the code computes when the documented entry points are used as intended.

**Scope:** only what A15 changed, which is the diff `bedc2ce..b3c400d` in `section5/` plus the regenerated contamination list. I checked items 1-9 above against that code. Nothing was fixed. Same severity scale and evidence labels as above. No data were loaded: I fitted no model and ran no detector. The probes used lazy backends, the synthetic backend and temporary files. All 9 unit-test suites passed at `b3c400d` (123 tests).

## Items 1-9

| # | Item | Verdict | Evidence |
|---|---|---|---|
| 1 | Baseline never tuned | **Fixed** | `s5_run.py` `select_fold` calls `SEL.tune((), obj, grid)` with the same grid, 3 starts and tie rule as the feature tuning. `s5_backend.py` `score()` fits the baseline with `setup["base_params"]`, and A14.2 flags now come from that model. Old setups have no `base_params` and would raise `KeyError`, but they cannot be reached: the A15 version tag invalidates them. (Read; `s5_tests_a15` rule-1 tests.) |
| 2 | LEGACY 23/24 in the confirmatory set | **Fixed** | Regenerated list: 8 excluded (LEGACY 23, 24, 27, 28, 29; RAW 1, 2, 3), 26 confirmatory, 98 H1(c) events. Removing the `cold_audit_1/x5_robust.py` entry brings back LEGACY 23 and 24 (measured). The footprints of the first audit's scripts come from my reading of their scratchpad copies, which are not in the repository, so the registry entry can't be re-checked from the repo alone. The 31 October re-audit ran no Section 5 detector (read). |
| 3 | Registry test could not fail | **Fixed, with a gap** | The pattern has no control characters, the test calls `check_registry`, and the check fails on a planted script (measured). The 3 scripts are registered. Gap: see new problem 3. The pattern misses `era_context(`, which A15 itself added and which loads a whole era, as well as `splice_batch(` and the `_init` pool initialisers. A planted script using them passes the check (measured). |
| 4 | Checkpoint version too narrow | **Fixed, with a gap** | The closure covers 23 modules, including the model, event, sweep, backend and Section 4 code. There are no name collisions across the three search directories and no dynamic imports in the closure (measured). A change to `s5_models.py` changes the version (test). Gap: see new problem 4. `run_all(files=...)` still accepts a hand-picked list (measured). |
| 5 | No main-run path | **Fixed, with gaps** | `MainBackend` serves the 34 folds in order, one fold in memory at a time. Freeze thresholds come from `EraBackend.calibrate`, and `DataBackend.era_thresholds` refuses. `run_all` reads the list itself (read; tests). Gaps: see new problems 1, 2 and 6. Each guard sits at one entry point only. |
| 6 | Holm drops a missing p | **Fixed** | NaN enters as 1, counts in m and is never rejected. With p = .02 / .024 / NaN, nothing is rejected (adjusted p .06), the same as with p = 1 (test). |
| 7 | Failed H1(a) recorded as zero | **Fixed** | With 8 or more stable days and no specs (or an empty curve), the result is `effect=None` with `failed=<reason>`. Failed folds are listed per family, in `run_summary.json` and in the freeze document (read; test). |
| 8 | Freeze hashes incomplete | **Fixed** | `freeze_input_hashes` covers the protocol, all 16 amendments integrated in it, the 6 cited inputs, the folds CSV, the split manifest, the contamination list, the H1(c) times and the 4 market-data files (test). The feature caches the run actually reads are not hashed (open audit 2 finding 14). |
| 9 | 5.14 unbounded for label-free analyses | **Fixed** | Protocol 5.14 and the `LABEL_FREE` / `MAIN_RUN` registry categories match. `touched()` ignores both (test). |

## New problems in the A15 code

### Medium

**1. The era-calibration guard covers only `MainBackend`; `EraBackend` can be called directly (measured)**
- **Where:** `section5/s5_era_threshold.py:20-23` (`__init__`), `section5/s5_main.py` `era_thresholds` and `mark_scoring_complete`
- A15 rule 5c refuses the era calibration until every fold has been selected and scored, because the calibration fits models on sessions 0 to n-64. Those sessions include every fold's test segment.
- That refusal exists only in `MainBackend.era_thresholds`. `ET.EraBackend("LEGACY")` builds without the protocol hash and without a completed run, and `calibrate()` can then be called on it.
- Inside `MainBackend`, the completion check is a public flag: `mark_scoring_complete()` can be called by hand before any fold is scored.
- If either path ran before the fold scoring, every confirmatory fold's test segment would have been touched by a model fit. No error would appear, and no registry entry would show it, because `s5_era_threshold.py` is registered as `LIBRARY` and `s5_main.py` as `MAIN_RUN`.

**2. The contamination list is supplied by the caller, and the freeze doesn't check which list the run used (measured)**
- **Where:** `section5/s5_backend.py` `DataBackend.__init__` (`contamination=`), `section5/s5_run.py` `run_all(contamination=...)` and `freeze_step`, `section5/s5_main.py` `MainBackend(contamination=...)`
- `DataBackend("LEGACY", 0, allowed={"LEGACY|0"}, contamination=<file marking it excluded>)` serves a clean fold without the frozen-protocol hash. The fold counts as "contaminated", so the machinery path lets it through.
- `run_all` takes its exclusions from whatever file it is given. `MainBackend` and `run_all` each take their own path, and nothing checks that the two agree.
- `freeze_step` writes the run's `contamination_sha256` next to `input_hashes`, which hashes the canonical list, but never compares them. A freeze built from a run on a different list is written without error (measured with the synthetic backend).
- Rule 5d ("`run_all` loads the contamination list itself") holds only when the default path is used.

**3. The registry check misses a loader that A15 itself added (measured)**
- **Where:** `section5/s5_contamination.py` `DATA_LOAD`
- `era_context(` (new in `s5_backend.py`), `splice_batch(` and the pool initialisers `F._init` / `D2._init` all call `load_era` internally. A script that uses only these passes `check_registry`. A planted script calling `BK.era_context` and `F.splice_batch` is not reported.
- This is the same class of gap as item 3, and it was reopened by the A15 change itself.

### Low

**4. `run_all(files=...)` can still narrow the checkpoint version (measured):** passing a short list (for example `["s5_run.py"]`) brings back the pre-A15 behaviour. `run_summary.json` records the version but not whether it came from the full closure. Only the tests use this argument.

**5. Nothing stops a fold re-run after the era calibration (read):** after `freeze_step`, the era fits have touched every fold's test segment. A later `run_all` with changed code would miss every checkpoint and re-score all folds on touched sessions. The contamination list wouldn't record it, because `MAIN_RUN` doesn't mark sessions as touched. The freeze-file guard blocks a second freeze, but not a second scoring.

**6. The protocol hash is checked once, at backend construction (read):**
- `freeze_step(protocol_hash=...)` stores whatever string it is given. It doesn't compare it with the file, or with the hash `MainBackend` verified.
- The checkpoints don't carry the protocol hash. A run resumed after a later amendment that left the code unchanged would reuse its fold results under the new protocol text, and nothing would record this.

## Classification update
- Audit 2 items 1, 2, 6, 7, 8 and 9: resolved as recorded.
- Items 3, 4 and 5: resolved as recorded, but each has a residual, listed as new problems 3, 4, and 1, 2, 6 respectively.
- None of the six new problems was in the 15 findings above. If carried, they would be audit 2 findings 16-21: Medium for 1-3 and Low for 4-6. Open audit 2 findings 10-15 are unchanged by A15.
