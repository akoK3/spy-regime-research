# Cold audit of `section5/`: 22 problems, 2 critical

**I found no look-ahead in the features, filters or event logic, and no evaluation-period or cross-era data in any Section 5 run.** The problems are elsewhere. The H1(a) metric rewards feature models when there is no break at all, and test data shaped the protocol. Also, the H1(a) code crashes on 8 of the 30 LEGACY folds.

The audit covers `SECTION5_PROTOCOL.md` as amended by A6 and A7, at commit `889d6cc`. All cited hashes match. Nothing was fixed, and the only file added to the repo is this report.

**Severity:**
- **Critical:** can produce a wrong confirmatory conclusion without any error.
- **High:** breaks a protocol rule on leakage, or blocks the planned run.
- **Medium:** a real deviation or risk with a limited or conditional effect.
- **Low:** small, currently inactive, or record-keeping.

**Evidence labels:** "Measured" means I ran it on real data for this audit. "Read" means I established it from the code or documents.

## Critical

### 1. H1(a) scores zero-effect breaks well above chance, and it favours feature models (measured)
**Where:** `section5/s5_a6.py:62-64`, `section5/s5_d2.py:90-91`, `section5/s5_d2_stable.py:13-15`; deseasonalising in `section5/s5_a7.py:110`

**The mismatch**
- The scale factor `f` is computed from each session's own 20-session baseline: A's pre-tau variance against A's baseline, and B's post-tau variance against B's baseline.
- The detector sees both sides through session A's baseline only (5.6 and A6 item 5).
- So the labelled ratio R is not the ratio the detector receives.

Realised ratio divided by target, in A's units, across the test break specs (no detector was run):

| Fold | 5th-95th percentile | Off by more than 1.5x |
|---|---|---|
| RAW 3 | 0.44 to 2.26 | 37.5% |
| LEGACY 29 | 0.18 to 6.68 | 62.3% |

**Placebo test:** I built R = 1 breaks through the exact break code path, so no variance change was intended. Validation days only, 200 placebo splices against the 200 calibration nulls. Each cell lists Gaussian HMM / Student-t HMM / HSMM.

| Data | pAUC base | pAUC f3 | f3 minus base at zero effect | Chance pAUC, f3 |
|---|---|---|---|---|
| LEGACY 29, seed 777 | .203 / .088 / .181 | .287 / .242 / .264 | **+.084 / +.154 / +.083** | .055 / .031 / .045 |
| LEGACY 29, seed 778 | .202 / .084 / .168 | .269 / .261 / .252 | **+.067 / +.177 / +.084** | same |
| LEGACY 25, seed 777 | .024 / .023 / .032 | .091 / .087 / .088 | **+.067 / +.064 / +.056** | .052 / .062 / .056 |
| RAW 3, seed 777 | .052 / .054 / .050 | .058 / .055 / .045 | +.006 / +.001 / -.005 | .044 / .035 / .038 |
| RAW 3, seed 778 | .074 / .056 / .042 | .060 / .054 / .061 | -.014 / -.002 / +.019 | same |

**How to read this**
- On LEGACY 29, real breaks (R = 3, 5, 10, permanent) score only .298-.350 for f3, against .242-.287 for the zero-effect placebo. On that fold the metric barely separates real breaks from no break.
- The feature-minus-base gap at zero effect is +.056 to +.177 on LEGACY. The RAW fold 3 pilot reported +.058 to +.115 for the H1 families, so an artefact on LEGACY could be as large as the effect H1(a) is meant to detect.
- With pairs restricted to the same volatility tercile, the RAW gap is mostly positive but unstable: +.032 / +.018 / +.030 (seed 777) and +.032 / -.023 / +.039 (seed 778).

**Root cause, partly confirmed:** recomputing `f` in A's units on LEGACY 29 (seed 778) takes pAUC to about chance for base (.202 to .054, .084 to .019, .168 to .041) and mostly for f3 (.269 to .072, .261 to .108, .252 to .039). It does not explain the f3 excess on LEGACY 25 (.091 to .084). That excess is unexplained.

**The chance term contributes too:** A6's metric does not subtract chance, and chance pAUC itself favours f3 by .011-.043 on RAW 3 and LEGACY 25.

**Limits:** LEGACY 29 has 7 stable validation days and LEGACY 25 has 11, so pairs repeat heavily. The size varies by fold. Only these two LEGACY folds were tested.

### 2. A7 widened the primary metric after the test-segment results were out, and the f3-minus-base result moved towards H1 (measured from stored results)
**Where:** `AMENDMENT_A7.md:14`, `AMENDMENT_A6.md:36,40`; test scoring at `section5/s5_pilot.py:118-121`, `section5/s5_a6.py:175-187`, `section5/s5_a7.py:122-123`, `section5/s5_a7_sweep.py:52-56`

- A6 says "no protocol change based on the pilot's performance". A7 cites that pilot as its reason, and the pilot's curves come from RAW fold 3 test splices.
- A7 was committed at 12:57:00, 3 minutes 11 seconds after the A6 pilot commit at 12:53:49.
- Partial-area difference, f3 minus base, on the same test splices:

| Family | A6 | A7 |
|---|---|---|
| Gaussian HMM | **-.025** | **+.063** (sign flipped) |
| Student-t HMM | +.016 | +.058 |
| HSMM | +.027 | +.115 |

- 5.6 says to score test sessions once. RAW fold 3's test segment has been scored four times: `s5_pilot.py`, `s5_a6.py`, `s5_a7.py` and `s5_a7_sweep.py`.
- `AMENDMENT_A6.md:36` says no rule was chosen from pilot performance. Yet item 2 replaces the H1(a) metric citing hit rates "on the pilot fold", and A6 lists `PILOT_REPORT.md` as evidence, whose table at lines 63-72 shows test hit rates.
- A7's other motive, the 0.2-per-session target on validation, is legitimate, and the target and window did not change. A7 may be the right design. But it is no longer independent of the test data it will be judged on, and it is declared "machinery" without saying how these folds count in H1.

## High

### 3. The real-data evidence behind A6 sits inside RAW fold 2's test block (read)
**Where:** `section5/s5_pilot.py:12`, `section5/s5_d2.py:66-68`, `section5/s5_lib.py:154`, and every D-series script

- D2, D3, D5 part C, the fix tests, CUSUM and the extreme-splice diagnostic are labelled "VALIDATION only". That means validation for fold 3.
- RAW fold 3 validation (58 sessions, 2024-06-14 to 2024-09-06) lies entirely inside RAW fold 2's test segment (121 sessions, 2024-03-15 to 2024-09-06). That is 48% of fold 2's test block.
- Those sessions are cited evidence for A6's H1(a) metric (D2), its return baseline (D3) and its Section 6 threshold rule (D5 part C). A6's event rule rests on synthetic tests (D3 test 1, D4), so it is not affected.
- Fold 3's inner train, used to fit the diagnostic models, also overlaps the test blocks of folds 1 and 2.
- 5.8 says "the test segment never informs selection". No amendment or report mentions this overlap.
- LEGACY fold 29 has the same geometry with fold 28, but no protocol change came from it.

### 4. The H1(a) code crashes on 8 of 30 LEGACY folds, and only 19 are usable (measured)
**Where:** `section5/s5_a6.py:49-54`, `section5/s5_legacy_pilot.py:205-208`

- `build_specs` raises `RuntimeError: null pair` on LEGACY folds 5, 8, 9, 12, 14, 15, 18 and 19. Each has at most 3 stable validation days, so no volatility tercile holds two.
- Those validation splices serve only the secondary BOCPD rule, but they are built first, so the crash stops primary H1(a) scoring too. A6 has no rule for this case.
- A further 3 folds (4, 11, 17) have fewer than 8 stable test days, and fold 18 is in both groups. Usable folds: 0-3, 6, 7, 10, 13, 16, 20-29.
- The `evaluable` flag at `section5/s5_a7.py:102` and `section5/s5_legacy_pilot.py:206` is recorded but stops nothing.
- The gaps affect 5.9's block-3 bootstrap over consecutive folds. The protocol doesn't say how to handle them.
- Only 29.1% of LEGACY sessions pass the "390 bars, at least 98% finite closes" gate, against 99.0% of RAW. Stable days per fold: 1-11 validation and 3-19 test on LEGACY; 16-24 and 18-45 on RAW.
- The 400 null splices are few independent observations: 30 distinct pairs on LEGACY 29 and 90 on RAW 3.

### 5. The feature pool was still selected on all of TRAIN, including every fold's test sessions (read; disclosed)
**Where:** `section5/s5_lib.py:57-62`, `METHODS_LEDGER.md:143,170`, `SECTION5_PROTOCOL.md:37`

- The 19-column pool comes from a matrix built on all TRAIN sessions.
- Ledger item N.3 (recompute inside each fold) is still open, and nothing in `section5/` does it. 5.7 says there is no screening beyond Section 4, so the open item and the protocol now conflict.
- Era-crossing keep/drop decisions also remain, with no open item (ledger line 143).

## Medium

### 6. EM stopping is relative, which changes thresholds and treats models unequally (measured)
**Where:** `section5/s5_models.py:125,190,280`, `SECTION5_PROTOCOL.md:27,31`

- 5.4 says "tol 1e-4". The code tests `tol * max(1, |ll|)`, so the real tolerance is about 1.7-7.0 nats.
- Fits stop after 9-59 iterations. Read as an absolute tolerance, the same fits run 47-200 iterations, gain 14-334 nats, and 5 of 12 reach the 200 cap.
- Thresholds move by up to 2.81 (Gaussian HMM f3 on RAW: 11.49 to 14.30).
- Feature models get a looser tolerance than baselines: about 7 nats against 1.9 on RAW. 5.2 requires the same budget.
- `PILOT_REPORT.md:40` says tol was "reached before the 200 cap in every fit". That holds only under the relative reading.

### 7. The old state is re-based during the refractory period, which A6 doesn't allow (measured)
**Where:** `section5/s5_events.py:117,158`, `section5/s5_sweep.py:27`, `AMENDMENT_A6.md:24`

- A6: old state = argmax at updates 1-2 and at each alarm. The code also resets it at every real update inside the refractory period.
- With a literal version, the bisected threshold changes for 7 of 12 HMM/HSMM detectors, by up to 1.50 (HSMM f3 on LEGACY 29: 10.73 to 9.23).
- Validation rates at the code's threshold become .155-.224, against the target of 0.2.

### 8. Null splices contain breaks as large as the smaller labelled cells (measured)
**Where:** `section5/s5_a6.py:49-55`

- In A's units, 45% of RAW 3 nulls and 68% of LEGACY 29 nulls have a natural post/pre ratio of at least 1.5x in either direction. For a ratio of at least 2x, the shares are 19.5% and 51%.
- A "null" can therefore be a bigger shift than an R = 1.5 or R = 2 break, which distorts the low-ratio power figures.

### 9. Break tau stops at 13:55 for every cell (measured)
**Where:** `section5/s5_d2.py:17`, `section5/s5_a6.py:59`, `AMENDMENT_A6.md:25`

- A6 sets the 11:05-14:30 grid, with a cap of 14:00 for sandwiches only.
- `G_MAX = 264` applies to all breaks, including permanent ones, and gives 13:55. Maximum slot is 264 for breaks and 299 for nulls.
- So breaks and nulls have different tau ranges, and the 14:00 sandwich slot is unreachable.

### 10. The fold-level Lee-Mykland threshold is never used (read)
**Where:** `section5/s5_lib.py:127,195-201`, `section5/s5_pilot.py:44-46`, `step3_all_in_one.py:111,128`

- 5.1 says inner train fits this threshold. The function runs once in the pilot and only the result is logged.
- `lee_mykland_jump60` is built with the global simulated threshold. RAW fold 3 gave 9.56 from the Student-t fit, against 4.61 for the global threshold.
- This takes effect only when the sensitivity set runs.

### 11. Checkpoint keys omit what determines the result (read)
**Where:** `section5/s5_lib.py:36`, `section5/s5_legacy_pilot.py:165,202,211,219,250`, `section5/s5_pilot.py:69,80`

- The docstring says the key must encode every input. Keys such as `splice_chunk|LEGACY|29|0|1704` and `fit|LEGACY|29|hsmm|f3` omit the code version, seed, K, feature names and data hash.
- A fix to finding 1 keeps the same spec count, so the resumed run would silently reuse the old splices.
- Fold-level selection would also collide under one `sname`.

### 12. "25 of 25 checks passed" overstates the coverage (read)
**Where:** `section5/s5_legacy_pilot.py:127,128-140,187-188`, `section5/s5_pilot.py:152-187`

- Line 127 compares `te.max()` to a maximum that already includes it, so it cannot fail.
- Lines 128-140 overwrite sessions after inner train, then read only inner-train rows of features that were already computed, so they cannot detect leakage from those sessions.
- The checks at lines 187-188 restate conditions that already hold: events are only raised on real updates, and `available == t + 1 min` is asserted at load.
- The splice integrity test never touches `regime_panel`, which builds every H1(a) break. My probes passed there, so this is a coverage gap and not a defect.

### 13. The ±0.05 threshold robustness check has no meaning under A7 (read)
**Where:** `SECTION5_PROTOCOL.md:43`, `AMENDMENT_A7.md:18`

- Thresholds are now log-odds, up to 12.55, which is a probability above 0.99999. BOCPD uses a drop size. A7 did not define what ±0.05 means on either scale.

## Low

14. **Hit window counts pre-seam evidence (measured):** `section5/s5_sweep.py:36,56` and `section5/s5_a7.py:111` accept T_c equal to tau, which uses A's data only. Validation hits at alarm rate 0.2: 0-1 at exactly tau, and up to 8 of 48 with T_d at or before tau.
15. **Unconfirmed alarms aren't counted (read):** `section5/s5_events.py:125,148,169` always return 0, and the sweeps track nothing. 5.5 says dropped and counted, and A6 doesn't repeal this.
16. **Seeds, versions and shares aren't recorded (measured from stored results):** `section5/s5_a7.py:134-135` and `section5/s5_legacy_pilot.py:253-254` omit seeds and versions (5.4). `VERSIONS` at `section5/s5_models.py:10` is unused. Abstention and skip shares (5.3) are missing from A6/A7 outputs and only partly present in LEGACY's.
17. **Input hashes aren't checked at run time (read):** `section5/s5_lib.py:58,149` and the caches at `:112-117` load without verification, though the protocol cites inputs by hash. All 6 matched today, and the cached features equal a fresh recompute.
18. **Student-t states are ordered by scale, not variance (measured):** `section5/s5_models.py:40,139` ignore nu/(nu-2) (5.5). The order was the same on the two pilot folds I checked (f3 and base), and A6's rule doesn't use it.
19. **A bad Student-t start can win silently (read):** `section5/s5_models.py:185-195` keeps a start that still has an under-1% state after 10 attempts. Only a counter records this.
20. **Superseded paths are still live (read):** `V.events_for` at `section5/s5_eval.py:128-131` applies the pre-A6 rule. `section5/s5_d2.py:47` hard-codes RAW, and `s5_legacy_pilot.py` works around it.
21. **Sensitivity pool not limited to RAW (read):** `section5/s5_lib.py:79-80` would accept it on LEGACY, against 5.2.
22. **Unamended choices and records (read):**
    - The HSMM 0.5 pseudo-count (`section5/s5_models.py:265`) and the fixed duration cap of 78 (`section5/s5_eval.py:23`) are listed at `PILOT_REPORT.md:95` but were never amended, against 5.4.
    - The protocol still says "DRAFT pending pilot" (`SECTION5_PROTOCOL.md:3`).
    - `section5/s5_fast.py:4` credits the equivalence check to `s5_fixes.py`, but it is in `s5_bench.py`.
    - `PILOT_REPORT_LEGACY.md` has no writer script and no file hash table.

## Checked and clean
- **Mid-session look-ahead:** corrupting all bars after a cut on 5 real sessions per era moved none of the 19 features at or before the cut, and all 19 moved after it. This closes the end-of-session blind spot from the 30 October audit.
- **Evaluation and cross-era data:** panels load inside TRAIN cutoffs and every fold session is asserted TRAIN. LEGACY ends 2018-12-21 and RAW starts 2022-03-07, so COVID is out of scope. No script mixes eras.
- **Fold fitting:** preprocessing and models fit on inner train only. All 34 folds pass the embargo assertions. The 20-session baselines use past sessions only.
- **Splices:** edits to B before tau don't change the regime panel, and neither do edits to A after tau on permanent breaks. Fast and slow feature paths match exactly on regime panels, which the repo had not tested. All OHLCV fields are replaced after tau.
- **Filters and sweeps:** I traced the HMM, Student-t and HSMM recursions and the BOCPD update by hand and found no error. The sweeps match the loop implementations. QLIKE targets start after the decision bar.
- **Reproduction:** all 16 stored A7 and LEGACY thresholds reproduce exactly. All 31 unit tests pass.
- **Bisection:** rates aren't strictly monotone, with up to 8 reversals, but bisection still found the highest rate at or below 0.2 on every detector, to scan resolution.
- **Log skips:** out-of-sample non-positive values are negligible (at most 0.055% of bars in the folds checked).

## Not implemented, so not audited
- 5.8 selection and final setups
- 5.9 bootstrap, Wilcoxon and sign tests
- H1(b) out-of-sample scoring
- All of H2, S1, S2, E1, E2 and D1
- 5.10 robustness, including the 1- and 15-minute grids (78 slots is hard-coded)
- The LEGACY -1/0/+1 minute clock check
- 5.11 Holm and BH corrections, and the power simulations
- 5.12 freeze and 5.13 refit

Findings 1-5 should be settled before any of these run on top of the current code.

## Audit limits
- **Test exposure:** no detector was scored on a test segment. Findings 1, 4, 8 and 9 use test sessions, but only for session counts and splice-construction statistics. Detector runs used validation sessions of RAW 3 and LEGACY 29, and placebo and null splices only on LEGACY 25. All validation segments are also test data for an earlier fold, as finding 3 explains.
- **Reach:** the placebo covers 2 of 30 LEGACY folds and 1 of 4 RAW folds, with 2 seeds on the folds where it was repeated. The size of finding 1 varies by fold and is not established overall.
- **Not separated:** finding 1's f3 excess on LEGACY 25 has no identified cause.
- **Sandwich probe:** changing A's bars inside a sandwich did move the panel. This is expected, because the tail is shifted to stay continuous with A's path. It affects price level only.
- **Vendor timing:** LEGACY clock semantics stay unresolved. No code here can test them (ledger limitation 8).

Audit scripts and results are in `C:\Users\kakij\AppData\Local\Temp\claude\C--Users-kakij-Downloads\ecaf89dd-ec92-4242-8d19-98496b806596\scratchpad`.
