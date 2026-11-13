# Report, 2026-11-12 21:00 New York: audit corrections, post-evaluation queue, Bloomberg comparison

## Bottom line

- **Audit flags F1 and F2 are corrected.** The ledger has an appended correction row; old rows are unchanged. The fixes and additions to the evaluation report below are in commit 978c9ce:
  - corrected the two numbers;
  - added the alarm rates beside H1(c);
  - added a list of tests that were not evaluable or nearly empty.
- **`REPRODUCIBILITY_FACTS.md`:**
  - the pending items are filled;
  - it explains why there are 3 allowed reads per era;
  - it explains how the 5.13 files link to the freeze;
  - it notes that two result files contain NaN (not strict JSON);
  - it records the extra read made for the Bloomberg check.
- **Direction rule (development data).** On the A28 1b calm-to-stressed breaks of Gaussian HMM and HSMM, protocol 5.5 agrees on **85.9%** of the 1,135 breaks where it is defined; 14 more are undefined. This is now disclosed as S6-D4, together with the label counts. Commit 3351f94.
- **Section 5 disclosures:**
  - D5: the A19 rule 4 VIX sensitivity was pre-registered but never run;
  - D6: the July–September 2026 daily HMM pilot gave prior exposure to both evaluation periods.

  Commit 3351f94.
- **Bloomberg comparison (run).** The panel and Bloomberg both **label a bar by its start minute**. Returns agree closely for SPY and less closely for HYG.

## Bloomberg vs the RAW panel, 2026-03-18..2026-09-30 (136 sessions in both)

**Setup:**
- Bloomberg data: Book1 (SPY) and Book2 (HYG), 1-minute trade bars.
- Panel data: `canonical_panel_RAW_1m.csv.gz`, read through the guard. The access log records one ALLOWED RAW read at 01:45:42Z.
- The panel holds returns only, no prices, so the comparison uses 1-minute close-to-close log returns.

**Timestamp convention.** Panel minute m was matched to Bloomberg bar m + k:

| k (minutes) | -2 | -1 | **0** | +1 | +2 |
|---|---|---|---|---|---|
| SPY correlation | -0.002 | 0.049 | **0.950** | 0.020 | -0.001 |
| HYG correlation | -0.009 | 0.120 | **0.795** | 0.008 | -0.004 |

The match is clearly at k = 0. Bloomberg's regular-hours bars run from 09:30 to 15:59 in all 136 sessions, so Bloomberg labels each bar by its start minute. The panel's `utc_minute_start_assumed` therefore uses the same convention. **This supports the Section 3 minute-start assumption for RAW** over this window.

**Return agreement at k = 0:**

| | SPY | HYG |
|---|---|---|
| Matched minutes | 52,904 | 43,958 |
| Correlation | 0.950 | 0.795 |
| Median absolute difference | 0.45 bp | 0.62 bp |
| 99th percentile of the difference | 3.4 bp | 2.5 bp |
| Share of minutes within 1 bp | 79.8% | 84.7% |
| Minutes with a difference of 10 bp or more | 11 | 0 |
| Per-session sum of matched returns: median / maximum difference | 1.1 / 5.4 bp | 2.5 / 13.8 bp |

**Reading:**
- The two sources are the same series on the same clock, but they are not identical.
- The minute-level differences fit a single-venue trade feed compared with Bloomberg's consolidated trade bars. This is an interpretation: the files do not show venue.
- HYG's median difference of 0.62 bp is about half a cent on a $78 share (one cent is about 1.3 bp).
- RAW has 43,977 eligible HYG minutes against 52,988 Bloomberg bars.

**Not done:**
- No price levels were compared, because the panel has no prices.
- No result was recomputed.
- This is a data check only.

Output: `section5/results/bloomberg_comparison.json` (with sidecar). Script: `diagnostics/bloomberg_compare.py`, whose hash was recorded in the ledger before the run. A dry run on a synthetic panel recovered a planted −1 minute shift.

**Still open:** the LEGACY source zip `hfdatalibrary_clean_1min_5tickers_2026-10-03.zip` has no backup.

---

# Report, 2026-11-12 20:30 New York: evaluation chain complete (5.13, Section 6, A38)

## Bottom line

- **The chain finished without error.** Fingerprint, `s6_eval.py run`, and `s5_a38.py run` all exited 0. Every stderr log is empty, and Section 6 raised no alert. Start 09:01, end 20:09 NY. Paused 09:25-11:33, 12:54-14:22 and 17:52-18:08 (all on your request).
- **All evaluation results carry the A26 label "adaptive/exploratory (previously exposed period)", confirmatory = false.**
- **H1 out of sample (5.13): the feature models beat the baseline in both eras** for Gaussian HMM, Student-t HMM and HSMM, on H1(a) and H1(b). All 95% intervals exclude 0. BOCPD is 0 by construction: its frozen model selected no features, so it is the baseline.
- **H2 (primary detector gaussian_hmm): no asset rejects.** Holm of 4, smallest adjusted p = GOLD 0.213.
- **H3/H4: nothing rejects.** Holm of 6, every adjusted p = 1.0. All four H3 gammas are negative.
- **A38: "no detectable filter effect" for all four families.** Rule 2: Gaussian HMM and HSMM are labelled "robust to the LEGACY Clean filter".

## 5.13: H1 on the evaluation periods (effect, 95% day-cluster interval; 2,000 resamples)

LEGACY 2019-01-02..2022-03-04, 800 sessions. RAW 2025-01-02..2026-10-12, 445 sessions.

| Family | H1(a) pAUC gain, LEGACY | H1(a), RAW | H1(b) QLIKE gain, LEGACY | H1(b), RAW | H1(c) FOMC hit-rate gain, LEGACY (n 24) | H1(c), RAW (n 14) |
|---|---|---|---|---|---|---|
| Gaussian HMM | 0.084 (0.053, 0.116) | 0.194 (0.152, 0.241) | 0.049 (0.036, 0.065) | 0.118 (0.083, 0.159) | 0.42 (0.21, 0.63) | 0.14 (0.00, 0.36) |
| Student-t HMM | 0.087 (0.058, 0.117) | 0.204 (0.166, 0.242) | 0.031 (0.021, 0.043) | 0.041 (0.029, 0.056) | 0.42 (0.17, 0.63) | -0.29 (-0.57, 0.00) |
| HSMM | 0.049 (0.027, 0.075) | 0.186 (0.152, 0.219) | 0.101 (0.085, 0.120) | 0.091 (0.068, 0.117) | 0.38 (0.13, 0.58) | 0.14 (-0.21, 0.50) |
| BOCPD | 0 | 0 | 0 | 0 | 0 | 0 |

No fitted model was flagged. By design, 5.13 reports no p-values (A36 5g). *(Corrected 2026-11-13: HSMM H1(b) LEGACY is 0.101, file value 0.10146. It was first written as 0.102 here, in ledger row `METHODS_LEDGER.md:683` and in commit 34ec7d1.)*

**Realized alarm rates per session, beside H1(c)** (feature model vs baseline; both thresholds were calibrated on TRAIN to about 0.19 per session):

| Family | H1(c) LEGACY | Alarms LEGACY, feature / baseline | H1(c) RAW | Alarms RAW, feature / baseline |
|---|---|---|---|---|
| Gaussian HMM | 0.42 | 0.214 / 0.141 | 0.14 | 0.137 / 0.276 |
| Student-t HMM | 0.42 | 0.215 / 0.168 | -0.29 | 0.117 / 0.310 |
| HSMM | 0.38 | 0.159 / 0.101 | 0.14 | 0.200 / 0.306 |
| BOCPD | 0 | 0.186 / 0.186 | 0 | 0.187 / 0.187 |

H1(c) is a gain in hit rate at fixed thresholds, so it depends on these alarm rates.
- In LEGACY the feature models alarm more often than the baseline.
- In RAW they alarm less often, and the baselines run well above the 0.19 calibration rate.

So the RAW H1(c) gains are measured against a baseline that alarms about twice as often. H1(a) is a pAUC and does not depend on these thresholds.

## Section 6, primary detector gaussian_hmm

**Breaks:** 218 confirmed calm-to-stressed (LEGACY 171, RAW 47). None was removed by burn-in.

**H2, primary (window 0-30 min, Holm of 4):**

| Asset | Breaks | p | Holm p |
|---|---|---|---|
| TLT | 208 | 0.986 | 1.0 |
| HYG | 191 | 0.550 | 1.0 |
| GOLD | 206 | 0.053 | 0.213 |
| DOLLAR | 193 | 0.930 | 1.0 |

By era: smallest per-era p is LEGACY GOLD 0.059 and RAW DOLLAR 0.038 (Holm 0.150). Nothing rejects.

**H3/H4, primary (Holm of 6):**

| Test | n | Statistic | p | Holm p |
|---|---|---|---|---|
| H3 TLT | 208 | gamma -0.053 | 0.872 | 1.0 |
| H3 HYG | 184 | gamma -0.095 | 0.974 | 1.0 |
| H3 GOLD | 206 | gamma -0.106 | 0.987 | 1.0 |
| H3 DOLLAR | 157 | gamma -0.212 | 1.000 | 1.0 |
| H4a | 294 | AUC gain -0.012 | 0.857 | 1.0 |
| H4b | 218 | AUC gain -0.028 | 0.853 | 1.0 |

**Secondary (BH; not confirmatory):**
- In the H2 family, two survive BH: HYG pre-30 (BH p 0.008) and DOLLAR pre-30 (BH p 0.016). These measure the 30 minutes before the break, not the response after it.
- In the H3/H4 family (76 tests), nothing survives BH. The smallest raw p is the BOCPD detector's H3 GOLD: p 0.018, gamma +0.134, n 155, BH 0.795 (Holm within that detector 0.108). The next is FOMC-day H4b, p 0.021, BH 0.795. *(Corrected 2026-11-13: this line first gave FOMC-day H4b as the smallest; ledger correction row.)*
- A34 per-asset placebo sensitivity for H3: every BH p = 1.0, so the primary result is unchanged.

**Not evaluable or near-empty tests (none is primary):**

| Test | Status |
|---|---|
| Section 6, H4b with T0 anchored at S | Not evaluable: 0 valid resamples (valid share 0.0); gain NaN, p null |
| Section 6, detector dependence, BOCPD H4a | Not evaluable: n 0 |
| Section 6, FOMC-day H4a | Evaluated, but flagged low valid share (0.326); n 11 (8 positive); out-of-fold AUC 0.5 and 0.5 |
| Section 6, secondary H3 stressed-to-calm HYG | Near-empty: n 1, p null |
| H2, secondary stressed-to-calm HYG (30 min) | Near-empty: n 4; statistic and p null |
| H2 E1 footprint | 184 breaks used; 7 skipped (window past close), 27 skipped (TLT or HYG not evaluable) |
| A34 E1 footprint | 187 breaks used; 7 and 24 skipped, for the same two reasons |

Descriptive by design, not tested (p null):
- Section 6 H3 prior hour before S (4 assets);
- A32 exploratory pre-30 X tests in H2 and A34 (4 each).

**Asset availability:** RAW HYG is unavailable on 177 of 445 evaluation sessions (40%). This is why RAW H2 HYG uses only 25 breaks.

## A38 (RAW evaluation period; Clean vs Raw filter)

- **Splices:** 1,360 total; 136 dropped (10.0%), none buildable on the Clean panel. There are 115 stable days.
- **H1(a) Clean minus Raw, with 95% interval and MDE:**

  | Family | Delta | 95% interval | MDE |
  |---|---|---|---|
  | Gaussian HMM | -0.014 | (-0.037, 0.010) | 0.034 |
  | Student-t HMM | -0.001 | (-0.030, 0.035) | 0.047 |
  | HSMM | -0.011 | (-0.042, 0.022) | 0.045 |
  | BOCPD | 0 | 0 | 0 |

- **H1(b):** every interval includes 0.
- **Reading (A38 rule 4):** "No detectable filter effect" does not show that processing the LEGACY rows had no effect.

## Files

- `section5/results/evaluation_{LEGACY,RAW}.json` and `section6/results/coverage_evaluation.json`.
- `section6/results/{s6,h2,a34}_evaluation_gaussian_hmm.json` and `section5/results/a38_filter_check.json`, each with a sha256 sidecar.
- One-shot markers are written, so these runs cannot be repeated.

**Audit:** see `POST_EVAL_AUDIT.md`. Flags F1 and F2 are corrected above.

---

# Report, 2026-11-12 09:00 New York: the real 5.12 freeze (stopped at the freeze, as ordered)

## Bottom line

- **The freeze is written and passed every check.** `section5/results/section5_freeze.json` (sha256 846c1aaa...), with sidecar, run record and lock. Started 23:09 on 11 Nov, finished 03:22 on 12 Nov (4 h 13 min; fitting 3 h 39 min). Nothing was written to the error log.
- **Detector chosen by the freeze rule (H2 primary): Gaussian HMM.** The families that pass H1 are the HSMM (Holm-adjusted p 0.0003) and the Gaussian HMM (0.0014). Student-t fails (0.103), and BOCPD is secondary. Of the two that pass, the Gaussian HMM has the lower median validation QLIKE (0.2106 against 0.2175).
- **All 8 thresholds matched.** Each era threshold equals the one recomputed on the 5.13 path at the fit, difference 0.0 in all 8 pairs (tolerance 0.001; BOCPD 0.5).
- **Not run, as ordered:** the Section 6 fingerprint, `s6_eval.py`, and A38. No evaluation-period data were read.

## Thresholds (era threshold = 5.13 recomputation)

| Family | LEGACY | RAW |
|---|---|---|
| Gaussian HMM | 16.4273 | 16.9821 |
| Student-t HMM | 11.8130 | 14.1632 |
| HSMM | 15.7434 | 11.5851 |
| BOCPD | 51.3008 | 54.0781 |

## Other checks in the run record

- Feature parity passed in both eras: LEGACY 4,022 TRAIN sessions (2003-01-02 to 2018-12-21), RAW 705 (2022-03-07 to 2024-12-23).
- The staging models were fitted fresh, not reused. They were moved to `section5/results/frozen_models/` (8 models; manifest sha256 edb78798...), and their hashes were checked against the freeze document.
- The freeze document lists 19 amendments, and the code version is a0323ed24d68e896. The `ERA_CALIBRATION.lock` lock now exists (`section5/results/`).
- `frozen_models/` is git-ignored, so it is on this machine only. Like the LEGACY zip, it has no backup.

**Next, only on your instruction:** `s6_fingerprint.py write`, then `s6_eval.py run FREEZE TOKEN`, then `s5_a38.py run FREEZE TOKEN`.

---

# Report, 2026-11-11 21:00 New York: A38 fix and A38-only rehearsal rerun (development data only; no real freeze)

## Bottom line

- **The A38-only rerun PASSED** (`section6/results/dress_rehearsal_a38.json`; 6 min). With the full rehearsal's earlier stages, every B1 condition is now met, in two runs.
- **A38 note N1-N4** (commit d647c8e, before the code): Raw splices that cannot be built on the Clean panel are dropped from both runs, so H1(a) stays paired; the count, share and reasons are reported.
- **Code** (commit dd96fa2): `s5_a38.py` only; tests 12/12; all suites pass; code version a0323ed24d68e896.
- **One deviation from your order, forced by A38 rule 5a.** Whether a splice can be built on the Clean panel is only known from the Clean data, and the Clean marker must come immediately before that read. So the check on the Clean data cannot precede the marker. What runs ahead of the marker: the saved Raw run and every splice specification are checked; if that fails, no marker is written. Right after the read, the screen runs first, and every kept splice is built inside error handling. An unbuildable splice is now dropped and recorded, never a crash.

## A38-only rerun (fake RAW tail, 120 sessions, 28 stable days)

- **Dropped:** 169 of 1,360 splices (12.4%): 32 of 400 null (8.0%), 137 of 960 break (14.3%). Every one failed the endpoint rule (`s5_d2.finite_ok`); no build errors.
- **H1(a) evaluated for all four families**, on the Clean run and on the Raw run restricted to the same splices.
- Labelled; 1 ALLOWED A38 read, 0 refused; real paths untouched.
- Rule 1 readings on the fake tail (development data; plumbing only, not results): Gaussian HMM, Student-t HMM, BOCPD "no detectable filter effect"; HSMM "filter-sensitive" (Delta(a) -0.029, 95% interval -0.059 to -0.007).

**Disclosed substitutions, temporary folder only:**
- The temporary Section 6 fingerprint was rewritten for the changed code. In the real order the fingerprint is written after this change.
- The amendment-list check compared against the temporary freeze's list, allowed only because the sole difference is A38's hash (before and after the note).
- The crashed run's Clean marker was renamed, not deleted. In a real run it would block a second Clean read, by design.
- The Raw run was reused from the saved file of the full rehearsal (written by the previous code; the Raw path did not change).

## B1 pass condition, now

| Condition | Met |
|---|---|
| H1(a) evaluated in both eras, in 5.13 | Yes (full run) |
| H1(a) evaluated in A38 | Yes (A38-only rerun) |
| Frozen thresholds reproduced, all 8 pairs | Yes (full run) |
| Real paths untouched | Yes (both) |
| No error | Yes in the A38-only rerun; the full run's only error was the A38 crash now fixed |

**Note for the paper:** 14% of break splices are dropped in the Clean comparison. The Clean filter removes bars near some splice points, so the paired H1(a) Delta is on a subset (reported beside the Raw run on all splices).

**Next, only on your instruction:** the real freeze (`s5_freeze_run.py run --confirm section5_freeze.json`), then the fingerprint, `s6_eval.py run`, `s5_a38.py run`.

---

# Report, 2026-11-11 20:45 New York: full dress rehearsal result (development data only; no real freeze)

## Bottom line

- **The full dress rehearsal did not pass. It crashed in its last stage, the A38 Clean-file run. Blocker B1 stays open.**
- **Every earlier stage passed.** Result: `section6/results/dress_rehearsal.json` (`passed: false`; 7 h 49 min; peak memory 2.5 GB). Real paths untouched.
- **Cause of the crash.** The Clean run reuses the Raw run's splice specifications (A38 rule 1d). HF's Clean filter removes about 2.6% of bars, so some spliced endpoint bars are missing on the Clean panel. `s5_eval.make_splice` (closure) asserts that both endpoint closes are finite and positive, and failed. The Clean one-shot marker had been written before the crash. **In the real run this would have lost A38's primary check for good** (residual R2).
- **Your decision (option 1):** a dated note to A38. Splices that cannot be built on the Clean panel are dropped from both runs, so the comparison stays paired, and the count and share dropped are reported. The build-every-splice check goes ahead of the Clean marker. Then only the A38 part is rerun.

## Stages

| Stage | Time | Outcome |
|---|---|---|
| Freeze driver (both eras) | 5 h 29 min | Parity passed; staged fits; all 8 era thresholds equal to the 5.13-path recomputation; models moved; lock only in the temporary folder |
| 5.13 LEGACY and RAW (120-session fake tails) | 25 min | Labelled; sessions equal the fake tails; frozen thresholds reproduced for all 8 era-family pairs; **H1(a) evaluated in both eras** (12 and 28 stable days) |
| Section 6 (9,999 resamples, 200 null sets, 10,000 draws, 3 workers) | 1 h 46 min | Coverage, H3/H4, H2 and A34 written and labelled |
| A38 | crashed | Raw run done and saved; Clean run crashed at the splice rebuild, after its marker |

- **Alert, as designed (A37 rule 4):** the A28 7d(i) positive control failed (p = 0.57; only 6 Fed breaks in the fake tails). It is a reported check, not a gate.
- H1(a) effects on the fake tails (development data; not results): Gaussian HMM +0.10 (LEGACY) and +0.11 (RAW); HSMM +0.03 and +0.08. They are reported only to show the path ran.

## B1 pass condition, item by item

| Condition | Met |
|---|---|
| `passed: true` | **No** |
| H1(a) evaluated in both eras, in 5.13 | Yes |
| H1(a) evaluated in A38 | **No** (crash) |
| Frozen thresholds reproduced, all 8 pairs | Yes |
| Real paths untouched | Yes |
| No error | **No** |

---

# Report, 2026-11-11: PREFREEZE_AUDIT fixes (no real freeze)

## Bottom line

- **All six items are done.** Code commit 2d548e0.
- **The full dress rehearsal is running detached** (step 4; started 12:42 New York). The development-only smoke version **passed end to end**. The full result is added at the end of this report when it finishes.
- **Code version is a0323ed24d68e896, unchanged.**
  - **Disclosed:** I briefly edited `s5_main.py`'s docstring (audit H1 asked for it). That file is in the frozen closure, and the code-version test caught it at once. I restored it byte for byte from git before anything else ran.
  - The H1 ban test now lists `s5_main.py` as a text-only mention. **The audit's "fix the `s5_main.py` docstring" cannot be done** without changing the code version.
- No real freeze, no lock, no evaluation-period read. The real lock, freeze, frozen-model directory, access log and fingerprint do not exist, and were checked untouched by the rehearsal.

## 1. H1: single freeze driver (`section5/s5_freeze_run.py`)

- **The only sanctioned 5.12 entry:** `freeze(backend, summ, results_dir, amendments)`. `run --confirm section5_freeze.json` does the real freeze. `check` is read-only.
- **Pinned to MR2:** `load_summary()` reads `main_run_2` only.
- **`s5_freeze_models.freeze_with_models` now delegates** to the driver.
- **Ban test** (`s5_tests_freeze_run.py`): fails if any script other than these calls `freeze_step(`:
  - the definition and the driver;
  - the temp-dir rehearsals (`s5_dry_run`, `s5_machinery_run`, `s5_rehearsal`);
  - the unit tests;
  - `s5_main.py` (docstring text only; closure).
- **Rehearsed in a temp directory:** the real composition (driver → staged `write_models` → unchanged `s5_run.freeze_step` → move) with a stub main backend. 7/7 tests pass. The real composition on development data passed in the smoke dress rehearsal (section 4).
- **`check` on the real MR2 run** (read-only, no fit, no write):
  - prechecks pass;
  - H1 passing families: HSMM and Gaussian HMM;
  - expected H2 primary detector: `gaussian_hmm`;
  - no lock exists.

## 2. M1: atomic, retryable freeze

The order is:
1. **Prechecks before any fit:** no freeze and no evaluation output; the amendment list equals `freeze_ready()`; the completion record verifies; protocol, contamination, code-version and fold checks; a setup for every era and family.
2. **Feature parity** (M2).
3. **TRAIN refits into a staging directory.** A staged set that verifies (manifest sidecar, hashes, setups, code version, TRAIN sessions) is **reused, never refitted**. An unverifiable one is discarded and refitted.
4. **`freeze_step` with the era calibration**, through a wrapper that adds the staged hashes and checks every era threshold (M2). A mismatch stops **before** the freeze document is written.
5. **Only then**, move the staged models to `frozen_models/`, recheck their hashes against the document, and require `load_frozen` to succeed for both eras.
6. **Crash recovery:** a crash between 4 and 5 is completed by a rerun. An unverifiable freeze file refuses.

The era calibration's lock does not block a retry: `calibrate` appends to it and does not refuse.

**Tests:**
- a crash in the era calibration, then a retry: the staged models are reused (no second fit), the freeze is written and the models are moved;
- a threshold mismatch: no document;
- prechecks fail before any fit;
- an interrupted move is completed by a rerun;
- unverifiable staging is refitted.

## 3. M2: feature path vs main-run context

- **Now, on development data** (`section5/results/feature_parity.json`): **passed for both eras.**
  - RAW: 705 TRAIN sessions. LEGACY: 4,022.
  - Every A20-pool column, the Lee-Mykland input, the deseasonalised target, the 5-minute return matrix and every session's grid rows are equal (NaN masks identical; values within 1e-10).
- **Inside the freeze driver:** the same check before fitting, and the era-threshold comparison before the document is written.
  - Smoke rehearsal: all four RAW era thresholds equal the 5.13-path recomputation exactly (difference 0.0; tolerance 0.001, or 0.5 for BOCPD).

## 4. M3: dress rehearsal (development data only; `section6/s6_dress_rehearsal.py`)

- **Setup:** per era, the real TRAIN sessions are split into fake TRAIN (all but the last 125), 5 fake embargo sessions and a 120-session fake evaluation tail. Spans, split map, lock, fingerprint, access log, FOMC list (the development schedule on the fake tail) and every output are redirected to a temporary directory.
- **What runs, on real code and real loaders:** the freeze driver on the real main backend (MR2 completion record and setups, era calibration on the main-run context cut to fake TRAIN), then the joint driver (5.13 via the labelled entry, coverage, H3/H4, H2, A34), then the A38 entry.
- **Smoke run** (RAW only, 30-session tail, 199 resamples; `dress_rehearsal_smoke.json`): **PASSED in 51 minutes.**

  | Stage | Time | Outcome |
  |---|---|---|
  | Freeze driver | 2,641 s, of which 2,373 s fitting | parity passed; thresholds equal; models moved; lock only in temp |
  | 5.13 RAW | 2.5 min | labelled; sessions equal the fake tail exactly; frozen thresholds reproduced for all four families |
  | Section 6 | about 6 s | H3/H4, H2, A34 and coverage written and labelled. The positive control is reported **"not evaluable"** (one Fed break in 30 sessions), which exercises the L2 fix |
  | A38 | 256 s | both HF files through `authorise_a38` (2 ALLOWED A38 log lines), labelled output |
  | Real paths | | untouched |

- **Full run, detached** (both eras, 120-session tails, 9,999 resamples, 200 null sets, 10,000 H2 draws, 3 workers): started 12:42 New York.
  - From the smoke timings, LEGACY's fits on about 3,900 sessions should take several hours.
  - Its result goes to `section6/results/dress_rehearsal.json`, and is added below.

## 5. M4: the A38 entry (`section5/s5_a38.py`; tests `s5_tests_a38.py` 8/8)

- **HF panel builder:** the study grid (Section 3.10 canonical sessions and minutes), with prices from the HF file.
  - A bar is observed when it is on the grid, its source is `iex`, and its OHLCV passes the Section 3.4 validity rule.
  - The return into a bar is eligible when the bar and the previous minute are both observed.
  - **Checked exactly:** on RAW TRAIN, the builder run on the study's own Raw file reproduces the canonical RAW panel. Over 705 sessions, close, range, volume, open, high, low, return values and eligibility masks are identical; 19 off-grid HF rows are dropped.
- **Guard:** `s5_eval_loader.authorise_a38` runs every Section 6 guard check (freeze, token, amendment list, lock, data-hash preflight, fingerprint), plus A38 adopted and the official RAW result present and labelled. It is logged as A38, and needs neither the labelled 5.13 entry nor a `section6=True` pretence.
- **Per-file safeguards:** a hash check against A38's recorded hashes, then a one-shot marker immediately before that file's first evaluation read. Arrays are saved after each run, so the comparison never re-reads.
- **Statistics:**
  - Delta = Clean minus Raw for H1(a) (Raw run's splices reused) and H1(b) (bars common to both runs and both models);
  - paired day-cluster intervals (2,000 resamples, seed 513) and MDE = 2.8 x bootstrap SD;
  - the rule 1f reading; the rule 2 labels with an approximate MDE; the rule 1g reproducibility comparison.
- **Registered** as EVALUATION. **`hfdatalibrary_`** is added to the registry's data-load pattern. `s5_a38.py` is in `s6_fingerprint.HELPERS`. All of this is written **before** the freeze and before any RAW result exists.

## 6. Lows

| # | Fix |
|---|---|
| L1 | A dated disclosure note appended to `AMENDMENT_A35.md` (rules unchanged; sidecar rewritten; ledger row): rule 1a can only lower the null rejection rates, Gaussian H4b moved 0.105 → 0.065, and the Gaussian pass is partly due to the convention change. Every H4 p now reports `valid_share` = V/B and flags it below 0.9 (`low_valid_share`) |
| L2 | A NaN or None positive-control p is reported as "not evaluable", never "failed" (`s6_run.sanity` and `s6_eval.alerts_of`) |
| L3 | A38 added to the driver's amendment list (results' provenance records it) |
| L4 | The 5.13-writer scan matches any reference (alias, `getattr`, spaced call), not just `run_confirmatory(`. `write_once` refuses an unlabelled payload that cites an evaluation result file |
| L5 | `hfdatalibrary_` is in the registry pattern. The HF cleaning check now discards out-of-window rows while streaming (its 2026-11-11 result is unchanged; not rerun) |
| L6 | Overnight-type features are set to NaN on the first session after the embargo gap. None is in the A20 pool or its bases, so nothing the models use changes. The 20-session baselines spanning the gap are as A36 4a states (disclosed) |
| L7 | A detector chosen by the A28 1b fallback (e.g. Student-t) needs its own passing, reproducing A35 rerun, or work stops for your decision |
| L8 | FABLE_REAUDIT L3 closed: H2 detector dependence reuses the analysed detector's primary result. FABLE_REAUDIT L7 closed: the coverage guard uses the manifest regex, and `coverage_sessions.csv` is write-once |
| L9 | No rebinding of the model bundle inside the 5.13 loop |

**Tests (all pass):**
- Section 5: freeze prep 13, freeze driver 7, A38 8, HF check 3, ledger 2.
- Section 6: base 30, H2 10, A34 5, A35 10, A36 18, A37 9.

## Before the real freeze

1. Read the full dress-rehearsal result (below when done).
2. Then `s5_freeze_run.py run --confirm section5_freeze.json`, then the Section 6 fingerprint, then `s6_eval.py run`, then `s5_a38.py run`. Each is only on your instruction.

---

# Report, 2026-11-11: data provenance and freeze-readiness checks (read-only; nothing changed)

## (a) Why 2002-12-30 and 2002-12-31 are excluded

- **Record:** the frozen split protocol `frozen_documents/protocol_20261029T032641Z.json` (sha256 `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b`, equals its sidecar).
  - Its `exclusions` list gives: first_session 2002-12-30, last_session 2002-12-31, reason **"Two-session legacy stub; excluded without inspecting outcomes"**.
  - The same entry is repeated in amendment 4.3.0-A1 (`protocol_amendment_4_3_0_A1_20261029T034121Z.json`, sha256 `a57d55cc...`, equals its sidecar).
- **Frozen report** (`frozen_documents/REPORT.md`, "Final historical boundaries"): "The two legacy sessions 2002-12-30/31 are excluded. The draft calendar development start remains 2003-01-01; the first actual trading session is January 2. ... No favorable outcome was used to move these dates."
- **Context:** the HF/PiTrading SPY history starts on 2002-12-30, so those two sessions are an isolated stub before the 2003 calendar start. The LEGACY development span is 2003-01-02 to 2022-03-04 (4,827 sessions).

## (b) LEGACY provider, HF version and source file

- **Provider:** PiTrading. The rows carry `source` = `pitrading`, distributed inside the HF Data Library file.
- **HF version: Clean.** The panel uses the pitrading rows only. The other versions:
  - LEGACY uses neither HF Raw nor any Filled version;
  - HF does not distribute a Filled version ("This library does not distribute a gap-filled version", Data Versions page);
  - no Raw file we hold contains pitrading rows.
- **Source files.** The LEGACY ETF step (`section3_4_etf_cleaning.py`; recorded in `section3_4_etf_results/summary.json`, `dataset/*_LEGACY/source`) read the extracted copies below, keeping rows with `source` = `pitrading`:

  | File | Bytes | SHA-256 (recorded in `section2_audit_results/inventory.csv`) |
  |---|---|---|
  | `C:\Users\kakij\OneDrive\Desktop\data\raw\SPY_clean_1min.csv` | 145,098,632 | `718a1219bae3d8021ba473d4a3db73431dab45b183360121f08a780567454369` |
  | `...\TLT_clean_1min.csv` | 124,315,432 | `cd1336671d202f4845b2b91d1e1b53cf937e238700be556c63381acbcae815df` |
  | `...\HYG_clean_1min.csv` | 100,147,742 | `35e6540d4d9792c997dee736dda03872269246fbfdeb01bf67135bddb0364770` |

- **Origin of those copies:** each is byte-identical to the member of the same name in `C:\Users\kakij\Downloads\hfdatalibrary_clean_1min_5tickers_2026-10-03.zip` (545,272,441 bytes). The zip's recorded SHA-256 (`b6754832051ad5ff0a265439e35e100cc1fbef56cd3c067ff9b3ed50aa5d55ce`, Section 2 inventory) equals its current hash.
- **SPY in that file:** 1,819,919 pitrading bars (2002-12-30 to 2022-03-04) and 434,064 iex bars (2022-03-07 onward, not used for LEGACY).
- **Naming caution:** Section 2 labels the zip "HF IEX CLEAN" and the copies "HF legacy/PiTrading-processed". In our code "LEGACY" and "RAW" are era names: the LEGACY era uses the HF **Clean** file, and the RAW era uses the HF **Raw** IEX files.

## (c) Does HF Raw contain pre-March-2022 rows? No (docs and metadata only; no new download)

- **Docs** (`hfdatalibrary.com/pages/docs`): "Begin March 7, 2022 — IEX Exchange HIST data only"; "every bar is `iex`". PiTrading is not mentioned.
- **Data Versions page:** Raw is "One-minute bars built from IEX trades between 09:30 and 16:00 ET". Only Raw and Clean exist; no Filled version is distributed.
- **API** (`api.hfdatalibrary.com/v1/symbols/SPY`): Raw 9,025,023 bytes, Clean 8,816,589 bytes, both last modified 2026-11-10. The endpoints report sizes and timestamps only, no coverage dates or sources.
- **Files already held** (inspected, not downloaded for this): every Raw SPY file starts 2022-03-07 and is all `iex`:
  - 2026-10-13: 448,465 bars;
  - 2026-11-11: 456,265 bars.
- **Consequence:** HF offers no unfiltered PiTrading series. The 2026-10-03 Clean download, and the OneDrive copies of it, are the only record of the LEGACY history from HF.

## (d) Does the Zenodo record have downloadable files? Only a README

- **Record:** concept DOI 10.5281/zenodo.19501604, "HF Data Library: High-Frequency U.S. Equity Data (1-Minute OHLCV)", open access, read through the Zenodo API.
- **Versions:**
  - 1.0 (record 19501605, 2026-04-10);
  - 1.1 (23149900, 2026-10-05);
  - 1.2 (23288426, 2026-10-10, latest).
- **Files:** each version holds **one file only**, `zenodo_README.md` (about 5 kB). There are no CSV, Parquet or zip data files; the data are distributed through hfdatalibrary.com.
- **Coverage:** all three descriptions state coverage from March 7, 2022. Versions 1.0 and 1.1 add "Earlier history is no longer offered."

## (e) Refit timing and the H3/H4 detector: both done, in code, tested

**Refit timing (AMENDMENT_A37, adopted 2026-11-11T02:14:37Z; commit 81eb166):**
- **At the freeze:** `section5/s5_freeze_models.py` fits the final setups and baselines of all four families on TRAIN sessions only, through the audited loader, checked against the split manifest.
  - The baseline A11 threshold is also computed on TRAIN.
  - The pickles and a manifest are hashed into the freeze document (`input_hashes["frozen_models"]`).
- **At evaluation:** `section5/s5_eval513.py` only loads and checks these models (`load_frozen`).
  - Its backend raises "no model is fitted on the evaluation path (A37 2b)" on any fit outside the frozen set, and refuses selection, fold scoring and era thresholds.
  - `fit_fn` hands over the loaded state, and `run_fn` starts with the guarded evaluation read, so the one-shot marker is written immediately before the first evaluation read.
- **Tests:** `section6/s6_tests_a37.py` 9/9 pass on 2026-11-11 (rerun now). They cover backend delegation, load refusals, the fit refusal, fit_fn hand-over, the precheck reading nothing, write-once, and alerts.
- **Not run yet:** no frozen models exist (`section5/results/frozen_models/` is absent) because no freeze has been written.

**H3/H4 detector (A28 1b, A35 rule 3, A36 2d), not hard-coded:**
- `section6/s6_eval.py::h34_primary(fz)` reads the detector from the freeze document: `fz["h2_primary_detector"]`, set by `s5_freeze.h2_primary` (A9 item 2).
  - If none is set, the fallback is the H1 family with the lowest median validation QLIKE in the freeze, ties to the simpler model; BOCPD never.
  - A35 rule 3 is then applied from the stored null-control reruns (`section6/results/a35_null_control_{gaussian_hmm,hsmm}.json`, each checked against its sidecar). A Gaussian HMM that failed is replaced by the HSMM; an HSMM that failed, or a rerun that does not reproduce, stops the work.
  - The guards log the chosen detector and the reason.
- **Tests:** `section6/s6_tests_a36.py` 18/18 pass (rerun now). `test_h34_primary` covers every branch: freeze detector kept; Gaussian replaced by HSMM on failure; Student-t and HSMM kept; the 3d and 2d stops; the fallback tie to the simpler model.
- **The literal family names** in `s6_eval.py` appear only in the A35 replacement rule ("gaussian_hmm" -> "hsmm") and the H1 ordering tuple, as A35 3a specifies. No detector is fixed for H3/H4.
- **The development runs used both Gaussian HMM and HSMM** by approval (ledger 2026-11-10 03:42Z), because no freeze existed. The evaluation path takes the detector from the freeze.

## Not changed

- No file, test, amendment or result was modified for this report. The two test files were only run.
- Note: A35-A37 were written and adopted in another session on 2026-11-10/11. A38 (filter checks of H1) was adopted on 2026-11-11 04:33Z (commit 7263a5a).

---

# Report, 2026-11-10 23:15 New York: A35 null-control rerun finished; A37

## Bottom line

- **A35(b) rerun: both detectors pass. A35 rule 3c applies: nothing changes.** The Gaussian HMM stays the H3/H4 primary (A28 1b stands). Rules 3a and 3d do not apply.
- **Reproduction check (rule 2d) passes for both.** The rates under the old p convention equal the stored development-run rates exactly.
- **A37: adopted 2026-11-11 02:14:37Z and in the freeze manifest (A21-A37, `freeze_ready: yes`).** TRAIN refits happen at the 5.12 freeze; the evaluation step only loads the frozen, hashed models; the one-shot marker is written immediately before the first evaluation read. Unit tests 9/9; synthetic end-to-end 20/20.
- **Evaluation positive-control alert:** built into the driver. A failed or unevaluable A28 7d(i) positive control becomes the first field of the evaluation file and the first item of the report. No evaluation has run, so there is no such alert.
- `FABLE_AUDIT.md` and `FABLE_REAUDIT.md` are whitelisted and committed (`81eb166`).
- **No freeze. No evaluation-period row has been read.** No O8, no era calibration.

## Needs you

Nothing blocks. The next step under the protocol is the 5.12 freeze, which I have not done.

## A35(b) 7d null-control rerun (200 null sets per detector, seed 7, 9,999 resamples, limit 0.10; 202 min)

| Test | Gaussian HMM | HSMM |
|---|---|---|
| H3 TLT | 0.040 | 0.025 |
| H3 HYG | 0.055 | 0.010 |
| H3 GOLD | 0.005 | 0.000 |
| H3 DOLLAR | 0.065 | 0.040 |
| H4a | 0.045 | 0.000 |
| H4b | 0.065 | 0.040 |
| Passed | yes | yes |
| Reproduces development run | yes | yes |

- The Gaussian H4b rate was 10.5% under the old convention (NaN resamples counted as non-exceedances). With valid resamples only (A35(a)) it is 6.5%. Re-audit finding M1 is resolved by A35 as adopted before the rerun.
- Files: `section6/results/a35_null_control_{gaussian_hmm,hsmm}.json` (with sidecars), per-set rows `a35_null_reps_{gaussian_hmm,hsmm}.jsonl`, log `a35_log.txt`. Ledger rows added with `s5_ledger.py add`; ledger tests pass.

## A37 (`AMENDMENT_A37.md`, sha `cd3cfdea...`)

- `section5/s5_freeze_models.py`: per era and family, the final setup and the return-only baseline are fitted on every TRAIN session (checked against the split manifest), saved once with a manifest and sidecar, and the hashes go into the freeze document as `input_hashes["frozen_models"]` via a delegating backend wrapper. No frozen closure module changed (code version `a0323ed24d68e896`).
- `section5/s5_eval513.py`: `load_frozen` checks file hashes, setups, TRAIN sessions and the manifest; a preflight runs before the marker; the evaluation backend refuses any fit.
- `EL.precheck` logs PRECHECK only (no read, no ALLOWED).
- Synthetic end-to-end: 40 fits at the freeze, 0 during evaluation; a tampered model is refused before any marker; the alert fired on the synthetic positive control (0 Fed breaks, not evaluable), as designed.
- Caveat: the driver has only run on synthetic data. On real data, 5.13 work after the read can still fail and use up that era's one run (A37 3c, by design).

## Note

Another session committed `cc8948d` (HF Data Library Raw vs Clean check) during the rerun. I did not touch it.

---

# Report, 2026-11-10 night: re-audit follow-up (A35, A36 and the joint evaluation driver, A32 restored, disclosures, label guards)

## Bottom line

- **A35(a): done.** H4 bootstrap p-values use valid resamples only.
- **A35(b): running detached** since 19:52 New York; about 75 of 200 sets done per detector at 20:58. Rule (c) was adopted before it started. This report is updated when it finishes.
- **A32: adopted text restored** (the only post-adoption change was the date stamp).
- **A31 control: disclosed as not specific to the filter**, with one correction to the order's wording (below).
- **A36: adopted on your six decisions and in the freeze manifest.** The joint driver is written. Unit tests pass 18/18. The synthetic end-to-end run passes 14/14.
- **Evaluation FOMC list: built and hashed** before any evaluation read (38 meetings, all 14:00).
- **Label guards: closed where the frozen code allows; the rest disclosed.**
- All data-free suites pass. Code version `a0323ed24d68e896` is unchanged. `freeze_ready: yes` on A21-A36.
- **No evaluation-period row has been read.** No access log, no evaluation output, no lock, no fingerprint and no freeze exist.
- Committed and pushed: everything from this session except the rerun's result, which follows in a second commit when it finishes.

## Needs you

Nothing blocks. Two things to know: (1) the choices listed under A36 below were mine, inside your decisions; (2) the rerun result decides which of A35 3a / 3c / 3d applies, and the driver reads it from the result file.

## A36 (`AMENDMENT_A36.md`, adopted 2026-11-11 01:11:23Z) and the joint driver

Your six decisions, as implemented:

| Decision | Rule | Implementation |
|---|---|---|
| 1. Evaluation-only; eras combined by era terms; each era alone as secondary | 1b-1d | Tests run on evaluation units only. The two eras are combined exactly as LEGACY and RAW are in development. Each era alone is computed for the H2 family and the six H3/H4 tests and joins BH, never Holm. |
| 2. Full analyses, all labelled | 2a-2c | The whole development set is mirrored. Not repeated: the 2007+ sensitivity, which equals the primary on these periods. Sanity checks are reported, not gates, since nothing follows the evaluation. |
| 3. BOCPD secondary | 2d | BOCPD enters detector dependence only. |
| 4. Look-back | 4a-4d | Section 5 features run their causal baselines across the TRAIN / evaluation boundary. Section 6 puts the last 60 TRAIN sessions before each evaluation era as history. Units, candidates, placebo draws, cut points, pools and alarms come from evaluation sessions only. |
| 5. FOMC times | 3a-3d | Same parsers and order of evidence as development; built first; the builder refuses after any allowed evaluation read. |
| 6. One joint driver | 5, 6, 7 | `section6/s6_eval.py run FREEZE TOKEN`: guards, 5.13 per era, evaluation coverage, Section 6. |

**Choices I made inside your decisions. Each is stated in A36; say if any should change.**
- **Embargo sessions are never read** (rule 1e). Histories skip the five sessions between TRAIN and each evaluation period.
- **Baseline threshold** (rule 5c). The freeze stores an era threshold for the feature model only. H1(c) needs one for the baseline, so it is set by the same A11 rule on TRAIN data. The feature threshold is recomputed the same way as a reproduction check; the frozen value is the one used.
- **Intervals** (rule 5g). 95% percentile, day-cluster bootstrap, 2,000 resamples: stable days for H1(a), sessions for H1(b), events for H1(c). No p-value, fold test, Holm or verdict is computed on the evaluation periods.
- **Burn-in.** With 60 history sessions, every evaluation unit passes the 60-session burn-in. Early breaks still have few earlier candidates, so some have no placebos.
- **Fingerprint** (rule 7c, re-audit L9). A Section 6 evaluation read is now refused when any fingerprinted file differs from the fingerprint. The fingerprint also covers the Section 5 helpers of this path.

**Code** (all outside the frozen closure; closure classes are subclassed, not edited):
- `section5/s5_eval513.py`: the 5.13 `fit_fn` / `run_fn`. Loads TRAIN then evaluation, fits the frozen setups on full TRAIN, computes H1(a), (b), (c) with intervals, and exports the breaks Section 6 needs.
- `section6/s6_eval.py`: the driver. The H3/H4 primary detector follows A28 1b and A35 rule 3, read from the rerun's result file.
- `section5/s5_h1c_eval_times.py`: the FOMC list builder.
- `section6/s6_eval_synth.py`: the synthetic end-to-end run.
- Small additions to `s6_run.analyse` and `s6_h2.analyse` (evaluation options; defaults leave the development run unchanged) and to `s5_eval_loader` (`authorise`, `fingerprint_check`).

**Synthetic end-to-end run** (`section6/results/a36_synth_e2e.json`; 190 TRAIN + 110 evaluation sessions per era, generated; 24 minutes): PASS 14/14.
- Both 5.13 results and the three Section 6 results are written once, labelled, with sidecars.
- No p-value appears in the 5.13 results.
- **Thresholds calibrated on TRAIN alone are reproduced exactly on the joined panel**, for all four families and both eras. That shows evaluation rows do not leak into TRAIN quantities.
- Breaks, units, candidates and placebos lie in evaluation sessions only.
- One ALLOWED log line per read; a second run reads nothing; the marker blocks a second 5.13; an unlabelled write is refused after a read.
- The real access log does not exist afterwards.
- A first, smaller try was stopped by the new fingerprint guard because I added a test file while it ran. That is the guard working as written; the recorded run is on unchanged code.

**Evaluation FOMC list** (`section5/results/h1c_schedule_times_evaluation.json`, sha256 `39136645...`):
- 38 scheduled meetings with a statement: LEGACY 24, RAW 14.
- All 38 statement pages state 14:00; none excluded. With development, 96 Fed pages state a time from 2013 on, all 14:00.
- The two unscheduled March 2020 statements are not scheduled meetings and are not events, as in development.

**Not yet exercised on real data, by design:** the driver itself. On real panels the 5.13 step refits four families on every TRAIN session per era, so expect hours. The one-shot marker is written before the fit, so a crash in that step consumes the era's run; the synthetic run is the safeguard against that.

## A35 (`AMENDMENT_A35.md`, adopted 2026-11-11 00:13:42Z)

- **Rule 1 (a).** For every H4 test, p = (1 + exceedances among valid resamples) / (V + 1). V = 0 means not evaluable (p = 1 in Holm). Each H4 result also reports V and the old-convention p.
  - H3 is unchanged (9,997-9,999 valid resamples).
  - Earlier results are not recomputed; A35's table gives their H4 p-values under the new rule (largest change: Gaussian H4b 0.577 to 0.652). No verdict differs. Power was not rerun.
- **Rule 2 (b).** The rerun: 200 sets, seed 7, same seeds throughout, 9,999 resamples, both detectors, limit 0.10. Added check: the old-convention rates from the same resamples must equal the stored development-run rates exactly.
- **Rule 3 (c), written before the rerun.** Gaussian over 0.10 on any test: ineligible as H3/H4 primary, HSMM is the H3/H4 primary, Gaussian stays eligible for H2. Gaussian passes: nothing changes. HSMM over 0.10: A28 7d applies as written (you did not specify this case; I kept the existing rule).

**Rerun: pending.** Started 19:52 New York by `section6/run_a35.ps1` (preflight PASS 17/17, gate passed). Progress: `section6/results/a35_log.txt`; finished sets: `a35_null_reps_{detector}.jsonl`.

## A32

- The only post-adoption change was the "Dated" stamp. File and sidecar are back to the adopted bytes (`d222539c...`), the hash A33 cites.
- Disclosed: results written between the two states record A32 as `7bc90d60...`; same text apart from the stamp.

## A31 control (`SECTION6_DISCLOSED_LIMITATIONS.md`, S6-D1)

- **Correction to the order's wording.** The 12.5-22.5% flag rate is with H4 planted and no filter bias. With no effect at all, the control flags 4.0-7.0%, which is calibrated.
- **Disclosed.** The comparison set holds times just after real alarms, which carry the break's own effect. When breaks move the assets, the control flags the break, not the filter.
- The earlier report sentence that read the Gaussian TLT flag as a filter bias of 0.03 is withdrawn.

## Label guards (re-audit M3)

Closed, outside the frozen closure:
- a Section 5 evaluation read is refused outside `run_confirmatory_labelled`;
- Section 6 writes require the label once any evaluation read has been allowed in the process;
- every evaluation read is refused while any script calls the 5.13 writer directly;
- a non-dict `run_fn` result is wrapped, not refused (re-audit L8).

Not closed, disclosed in S6-D2: the 5.13 writer stays callable; direct panel reads bypass the guards; `s6_coverage.py` does not use `write_once`; the guards are module attributes; tables, figures and sentences are labelled by hand.

## Tests (data-free)

| Suite | Result |
|---|---|
| `s5_tests_ledger.py` | 2/2 |
| `s5_tests_freeze_prep.py` | 13/13 |
| `s5_tests_a15.py` | 19/19 |
| `s6_tests.py` | 30/30 |
| `s6_tests_h2.py` | 10/10 |
| `s6_tests_a34.py` | 5/5 |
| `s6_tests_a35.py` (new) | 10/10 |
| `s6_tests_a36.py` (new) | 18/18 |

## Not done from the re-audit

- L1: the registry scan is now called at run time by `s6_a35.py` and `s6_eval.py`; the other Section 6 runners still do not call it.
- L3, L4, L6, L7, L10: unchanged.

---

# Report, 2026-11-10 late: A34 (per-asset placebo pools; A26 label enforced in code)

## Bottom line

- **A34 is written, hashed before its code, and adopted.**
  - E1 and the |return| statistic are recomputed with per-asset placebo pools: same matching, plus the asset available in the placebo session. Both are labelled post-diagnosis.
  - The per-asset-pool H3 is added as a secondary sensitivity for all 4 assets.
  - **The H3 primary is unchanged.** Nothing else was recomputed, and no earlier result file was touched.
- **The HYG gap is closed for E1 and the |return| statistic.** HYG breaks used: 44 -> 234 (Gaussian), 29 -> 204 (HSMM). E1 classifiable breaks: 56 -> 271 and 43 -> 240.
- **The H3 sensitivity agrees with the primary:** negative gamma for every asset and both detectors, no rejection.
  - TLT gamma is smaller with per-asset pools: -0.112 vs -0.164 (Gaussian) and -0.119 vs -0.139 (HSMM). Gold barely moves.
- **Fable L3 is enforced in code** (A34 rule 3). An evaluation-period output without the A26 label is now refused in Section 6 and in Section 5.
- A34 is in the freeze manifest. All tests pass. Code version a0323ed24d68e896 is unchanged.
- No freeze, no O8, no era calibration.

## 1. A34 (`AMENDMENT_A34.md`, adopted 23:27Z; code commit 37ae229)

- **Rule 1.** Per-asset pool = A31 matching (earlier session, 30-min slot of S, SPY decile with earlier cut points, past alarms only, T_p <= 390, 20 per break) **plus the asset available in the placebo session**.
  - The cut points are unchanged.
  - E1's chance reference uses a joint TLT-and-HYG pool.
  - The default draw is unchanged; a test shows it is identical.
- **Rule 2.** Recompute only E1, the A32 statistic (exploratory, uncorrected) and the H3 sensitivity (secondary, BH of 4, outside Holm), all labelled post-diagnosis.
- **Rule 3 (Fable L3).**
  - **Section 6:** `s6_run.write_once` refuses any non-development result unless it carries the A26 label and `confirmatory = false`. `s6_h2` and `s6_a34` write through it.
  - **Section 5:** the 5.13 writer is in the frozen closure, so A34 adds `s5_eval_label.py` outside it.
    - `run_confirmatory_labelled` wraps the caller's `run_fn`, so every per-era result is labelled before the closure writes it.
    - `verify_labelled` refuses unlabelled evaluation files.
    - `s5_eval_loader.eval_guard` now requires `s5_eval_label.ready()` before any evaluation-period read.
  - **Tests** (`s6_tests_a34.py` 5/5): unlabelled refused, labelled accepted, the guard refuses without the module.
- **Caveat:** "sanctioned entry" is a code path, not a lock. Calling `s5_freeze.run_confirmatory` directly would still write unlabelled files. `verify_labelled` would catch them afterwards, but nothing blocks the direct call, because the closure can't be edited.

## 2. Recomputed development parts (`section6/results/a34_development_{gaussian_hmm,hsmm}.json`; about 1 min each)

**Placebos per break with per-asset pools:**
- the median is 20 for TLT, HYG and gold;
- USD has none for most breaks (it has data only in 2018);
- the 10th percentile is 0, for breaks before the asset's coverage.

**H3 next-day sensitivity (secondary; one-sided; BH of 4)**

| Asset | Gaussian: breaks / placebos, gamma, p (BH) | Primary gamma | HSMM: breaks / placebos, gamma, p (BH) | Primary gamma |
|---|---|---|---|---|
| TLT | 402 / 7,232, -0.112, 1.00 (1.00) | -0.164 | 339 / 6,249, -0.119, 1.00 (1.00) | -0.139 |
| HYG | 243 / 4,088, -0.069, 0.94 (1.00) | -0.071 | 205 / 3,589, -0.072, 0.93 (1.00) | -0.043 |
| Gold | 420 / 8,328, -0.170, 1.00 (1.00) | -0.185 | 373 / 7,404, -0.152, 1.00 (1.00) | -0.156 |
| USD | 9 / 172, -0.033, 0.58 (1.00) | -0.282 | 11 / 193, -0.155, 0.72 (1.00) | -0.213 |

- HYG now has about 17 placebos per break, against 6 in the primary. Its gamma is almost unchanged.
- TLT's negative gamma shrinks by about a third (Gaussian), so part of the primary TLT gamma depends on which placebo sessions were available. The sign and conclusion are unchanged.

**|return| statistic (exploratory; uncorrected; post-diagnosis): deseasonalised |return| breaks minus placebos, +30 min**

| Asset | Gaussian: n, G, p | HSMM: n, G, p |
|---|---|---|
| TLT | 383, +0.29, 0.0001 | 321, +0.37, 0.0001 |
| HYG | **234**, +0.24, 0.0012 | **204**, +0.36, 0.0003 |
| Gold | 405, +0.57, 0.0001 | 349, +0.70, 0.0001 |
| USD | 9, +1.55, 0.0006 | 10, +1.33, 0.030 |

- The same pattern holds at +5, +15 and +60, and in the pre-30 window (descriptive, about +0.6 to +0.9).
- The caveat stands: this may reflect market-wide volatility at the break.

**E1 footprint (descriptive; post-diagnosis): breaks vs placebo shares**

| Category | Gaussian (271 breaks / 5,310 placebos) | HSMM (240 / 4,707) |
|---|---|---|
| SPY-only | 60.2% vs 65.8% | 55.4% vs 65.8% |
| Credit stress | 7.0% vs 5.4% | 8.8% vs 5.9% |
| Flight to safety | 1.5% vs 0.9% | 0.4% vs 1.2% |
| Dollar-driven | 0.4% vs 0.1% | 0.4% vs 0.1% |
| Other | 31.0% vs 27.8% | 35.0% vs 27.0% |

- Breaks are SPY-only less often than placebos, by 6-10 points. They show credit stress and "other" patterns more often.
- Flight to safety stays rare. USD is almost never evaluable.

## 3. Audit documents

- `COLD_AUDIT_STATUS.md`: Fable L3 is marked resolved (A34 rule 3, commit 37ae229). Fable totals: 12 resolved / 2 disclosed / 3 open.
- `OPEN_AUDIT_FINDINGS.md`: L3 is removed, and the HYG note is updated.
- Both are recopied to `project_upload`, with A34 and the ledger.

---

# Report, 2026-11-10 evening: audit status refreshed, HYG data gap diagnosed, freeze manifest

## Bottom line

- **Both audit documents are refreshed and recopied to `project_upload`.**
  - `COLD_AUDIT_STATUS.md` now lists every finding with its status and the fixing amendment or commit.
  - `OPEN_AUDIT_FINDINGS.md` lists what is still open: 15 items, all Low except audit-1 #10. None affects a primary computation.
- **The HYG data gap comes from the placebo rule, not the HYG data.**
  - A31 placebos are matched on SPY only and drawn from earlier sessions. HYG coverage only starts in 2008-2010, so most HYG placebo windows fall in sessions with no HYG data.
  - My earlier guess (HYG's many zero returns) was **wrong**.
  - No test was changed.
- **A32, A33 and A33.1 were already in the freeze manifest** (added when each was written).
  - `freeze_ready()` now passes: all 14 amendments A21-A33.1 are ADOPTED with matching sidecars. That is a check only; no freeze was written.
  - A test now pins them (`s5_tests_freeze_prep.py` 12/12).
- No freeze, no O8, no era calibration.

## 1. Audit status (snapshots of the A16 versions kept as `COLD_AUDIT_STATUS_v6_A16.md` and `OPEN_AUDIT_FINDINGS_v5_A16.md`)

| Audit | Resolved | Disclosed | Open |
|---|---|---|---|
| Cold audit 1 (22) | 12 (new: #13 by A22 rule 3c; #17 by the data-hash preflight, commits 55cfc4e / 01ac960 / 9124c67) | 4 | 6: #10 Medium; #12, #16 (partly), #18, #20, #21 Low |
| Cold audit 2 (21) | 16 (new: #14, cache stamp and Section 6 cache, commit 9124c67) | 0 | 5 Low: #10, #11, #12 (Section 5 only), #13 (partly), #15 |
| O9 (12) | 5: M1 (A25), L1, L3, L8, L9 (commit f03a505) | 7: M2, M3, L2, L4-L7 (`SECTION5_DISCLOSED_LIMITATIONS.md`) | 0 |
| Fable (17) | 11: M1-M4, L4-L6, L12 (commit 9124c67); M5, L1, L10 (A31); L5 (manifest through A33.1) | 2: L8 (in A29), L11 (A27 row) | 4 Low: L2, L3, L7, L9 |

**Before any evaluation-period run:** Fable L3 (the A26 label must be attached to joint outputs) is the open item that matters.

## 2. HYG data gap (label-free; `section6/s6_hyg_gap.py`, hashed before it ran; output `section6/results/hyg_gap/hyg_gap.json`)

Counts only: no return comparison, no test, no H2 code change. TLT and gold are counted the same way for contrast.

**Where breaks are lost** (Gaussian / HSMM; the 30-minute window after T):

| | HYG | TLT | Gold |
|---|---|---|---|
| Breaks (A32 units, burn-in passed) | 600 / 549 | 600 / 549 | 600 / 549 |
| Asset unavailable in the break's own session | 300 / 283 | 183 / 190 | 162 / 161 |
| Window past the close | 20 / 24 | 20 / 24 | 20 / 24 |
| Fewer than 10 earlier sessions with data | 22 / 18 | 6 / 8 | 1 / 1 |
| **Fewer than 10 usable placebos** | **214 / 195** | 163 / 111 | 106 / 94 |
| Used by the A32 statistic | 44 / 29 | 228 / 216 | 311 / 269 |
| Placebo windows with the asset unavailable | **78% / 81%** | 61% / 62% | 51% / 51% |
| Usable placebos per usable break (median, 10th-90th pct) | 6 (1-11) / 5 (1-10) | 10 (4-15) / 11 (5-16) | 13 (5-19) / 13 (5-19) |
| E1 evaluable | 59 / 44 | 250 / 222 | 315 / 269 |

**Cause.**
- A31 / A28 1d placebos are drawn from **earlier sessions of the era**, matched on SPY alone, so they are not conditioned on the asset being available.
- HYG coverage starts late: LEGACY 6 available sessions in 2008, 71 in 2009, 141 in 2010, then about 215-250 per year.
- So for HYG breaks, most earlier-session placebos fall before HYG coverage, or on unavailable days. Only 5-6 usable placebos remain per break, below the 10 that E1 and the A32 statistic require.
- The H2 primary (A33 G6) draws its pool from **all sessions of the era where the asset is available**, so it keeps 242-280 HYG breaks.

**Not the cause.**
- HYG's zero returns: no window had a flat median, and flat 30-minute windows are 0-2.5% by year.
- Missing minutes: windows with no data are 0%.
- HYG's share of exactly-zero one-minute returns is high (43-62% in LEGACY, 18-36% in RAW), but no exclusion rule was triggered by it.

**Also affected, without a minimum to show it.** H3 uses the same placebos with no per-break minimum: HYG has 243 breaks with 1,523 placebos (6.3 per break; TLT 10.1, gold 12.9). The H3 HYG result was computed as specified, but rests on few placebos per break.

**Options (your decision; nothing changed):**
1. **Recommended:** an amendment for the **descriptive and exploratory parts only** (E1 and the A32 statistic). Draw each asset's placebos from sessions where that asset is available, with the same matching and causal rule. Recompute only those parts, labelled as changed after the diagnosis. Primary tests untouched.
2. Lower the minimum of 10 placebos for E1 and A32. This keeps more breaks, but each reference is noisier.
3. Leave as is and disclose: HYG E1 and A32 rest on 29-59 breaks, and H3 HYG on about 6 placebos per break.

## 3. Freeze manifest

`s5_amendment_manifest.AMENDMENTS` = A21-A31, A32, A33, A33_1.
- `freeze_ready()` passes. It also checks that the required results exist. This is a readiness check only; nothing was frozen.
- The Section 6 fingerprint (not yet written) covers every `section6/*.py`, including `s6_h2.py` and `s6_hyg_gap.py`.

## Files

- `COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md` (+ sidecars, v6/v5 snapshots), copied to `project_upload/`.
- `section6/s6_hyg_gap.py`; `section6/results/hyg_gap/hyg_gap.json`.
- Ledger rows for each.

---

# H2 report, 2026-11-10 (A33 / A33.1 chain done 17:23 New York)

## Bottom line

**H2 (protocol 5.0 test, as pre-registered) is not rejected for any asset, with either detector.**
- No detector rejects any asset under Holm, BOCPD and Student-t included.
- The strongest result is gold drifting up after breaks: Gaussian +0.027% vs placebo +0.002%, raw p 0.037, Holm 0.15.
- This is development (TRAIN-span) data only. No freeze, no O8, no era calibration.

## Chain

| Time (NY) | Step |
|---|---|
| 16:48 | First synthetic check (planted 0.05) failed: planted TLT rejected 75% < 80%. Kept on record |
| 17:17 | A33.1 adopted (your decision): planted 0.08, criteria unchanged, disclosed as raised after the 75% |
| 17:22 | Synthetic check **PASS 13/13**; gate A28-A33.1 passed |
| 17:22 | Power done (0.5 min) |
| 17:23 | H2 dev run done for Gaussian HMM and HSMM, about 70 s each, exit 0 |

## Synthetic check (10,000 draws; 200 null / 40 planted)

- **No effect:** rejection 4.5-7.5% (independent) and 4.5-5.5% (vol-clustered).
  - These are the same numbers as the first run: same seeds, and the null does not depend on the planted size.
- **Planted:** TLT 95%, HYG 97.5%, gold 97.5% rejected; USD (planted null) 5%.
- **Planted bias:** within tolerance for every asset.
  - The bias is identical to the first run, because an additive shift moves the estimate and the target equally.
  - Targets: TLT 0.00144, HYG -0.00096, gold 0.00192.

## Power (A33 G11, two-sided at 0.05/4, 10,000 draws)

| | Gaussian (600 breaks) | HSMM (549 breaks) |
|---|---|---|
| Power at delta = 0.10 / 0.15 / 0.20 SD | 0.45 / 0.85 / 0.995 | 0.455 / 0.855 / 0.985 |
| Minimum detectable shift | 0.15 SD of a break's 30-minute return | 0.15 SD |

This is an upper bound: only 280-420 breaks per asset have the asset available.

## H2 primary: (T, T+30], signed cumulative log return; Holm m = 4

| Asset | Gaussian: n, break mean vs placebo mean, p (Holm) | HSMM: n, break vs placebo, p (Holm) |
|---|---|---|
| TLT | 397, +0.0036% vs +0.0024%, p 0.90 (1.00) | 335, -0.019% vs +0.001%, p 0.085 (0.27) |
| HYG | 280, -0.0029% vs -0.0025%, p 0.95 (1.00) | 242, -0.011% vs -0.004%, p 0.46 (0.46) |
| Gold | 418, **+0.027%** vs +0.002%, p **0.037** (0.15) | 364, **+0.025%** vs +0.002%, p 0.068 (0.27) |
| USD | 13, -0.009% vs +0.001%, p 0.64 (1.00) | 12, -0.049% vs -0.005%, p 0.082 (0.27) |

- Placebo pools average about 800-1,400 matched candidate times per break (65-70 for USD).
- USD has only 12-13 breaks (2018 LEGACY only): not informative.

## Secondary (BH over the horizons, stressed-to-calm and other detectors)

- **Only one survives BH: TLT over (T - 30, T], for both detectors.**
  - TLT rises before the confirmation: Gaussian +0.055% (p 0.0002, BH 0.006); HSMM +0.070% (p 0.0002, BH 0.006).
  - This is the window between the streak start and confirmation: TLT moves up while SPY's break is still being confirmed.
- **Other raw p < 0.05, not significant after BH:**
  - HYG pre-30 down (p 0.004 / 0.036);
  - gold +60 up (Gaussian, p 0.021);
  - gold +5 and +15 up (HSMM, p 0.006 / 0.008).
- **Gold is positive at every post-T horizon for both detectors** (+5 to +60).
- **Detector dependence (S2):**
  - gold's direction is positive for all four detectors (raw p 0.036-0.074);
  - no Holm verdict on any detector, so the verdicts agree.

## Exploratory (A33 rule 4): A32 deseasonalised |return|, specified after seeing the H3/H4/A30 results; uncorrected

- **Breaks show larger absolute moves than placebos after T:**
  - TLT +0.36 / +0.36 at +30 (Gaussian / HSMM; p 0.0004 / 0.0005);
  - gold +0.53 / +0.73 (p 0.0001);
  - similar at +5, +15 and +60.
- **The pre-window (T - 30, T] is larger still:** about +1.0 for TLT and gold (descriptive).
- **Read with care:**
  - Breaks are, by construction, times when SPY moves into a high-volatility state. The placebos are matched on SPY volatility before S, not at T.
  - So larger asset |returns| may reflect market-wide volatility at the break rather than an asset-specific response.
  - The signed test (H2 primary) shows no consistent direction.
- **HYG is thin here:** only 29-49 breaks have a defined deseasonaliser, likely because of HYG's many zero one-minute returns.

## E1 footprint taxonomy (descriptive): thin

- Only 56 (Gaussian) and 43 (HSMM) breaks are classifiable. 482-524 have no evaluable TLT or HYG move (HYG data), and 20-24 have a window past the close.

| Category | Gaussian breaks vs placebos | HSMM breaks vs placebos |
|---|---|---|
| SPY-only | 55% vs 60% | 77% vs 61% |
| Credit stress | 9% vs 7% | 7% vs 5% |
| Flight to safety | 2% vs 0.4% | 2% vs 2% |
| Dollar-driven | 0% vs 0% | 2% vs 1% |
| Other | 34% vs 33% | 12% vs 31% |

- No clear footprint beyond chance on this sample.

## For your attention

1. **The HYG and E1 data gap.** The primary H2 uses 242-280 HYG breaks, but E1 and the exploratory statistic use only 29-56. Both need HYG data in the placebo windows and in the prior 20 sessions. I can diagnose the cause, label-free, if you want.
2. **The TLT pre-T rise** is the one secondary result that survives correction. It is consistent with the A30 lead-lag description (TLT often moves before S).

## Files

- `section6/results/`:
  - `h2_50_synth_a33.json` / `h2_50_synth_check_a33.json` (first run, FAIL, kept);
  - `h2_50_synth_a33p08.json` / `h2_50_synth_check_a33p08.json` (PASS);
  - `h2_50_power_{gaussian_hmm,hsmm}.json`;
  - `h2_development_{gaussian_hmm,hsmm}.json`;
  - `h2_log.txt`.
- Each is written once, with a sidecar and provenance (code hashes; A28-A33.1 manifest).
- Code version a0323ed24d68e896 is unchanged.

---

# H2 report, 2026-11-10 (A33 chain stopped 16:48 New York)

## Bottom line

- **The H2 chain stopped at the synthetic check, as your rule requires.** 12 of 13 criteria pass. The one failure is planted TLT, rejected in 75% of replicates against the required 80%.
- **Nothing was run on real data:** no H2 power and no H2 dev run, so no H2 output on real data exists.
- **The earlier A32 chain** was stopped at 16:39 during its synthetic step, at your request. Its partial synthetic file was not opened.
- No freeze, no O8, no era calibration.

## A33 synthetic check (protocol 5.0 test; 10,000 draws; 200 null and 40 planted replicates)

| Check | TLT | HYG | Gold | USD | Criterion |
|---|---|---|---|---|---|
| No effect, independent: rejection at 0.05 | 7.0% | 7.5% | 4.5% | 6.5% | <= 8.1%: pass |
| No effect, vol-clustered: rejection at 0.05 | 5.5% | 4.5% | 5.0% | 5.5% | <= 8.1%: pass |
| Planted: mean estimate minus target | -0.000003 (target 0.0009) | +0.00004 (target -0.0006) | +0.00009 (target 0.0012) | (planted null) | within max(2 SE, 10% of target): pass |
| Planted: rejection at 0.05 | **75%: FAIL** | 65% | 80%: pass | 5% | TLT and gold >= 80% |

- **Any Holm rejection:** 6.0% (independent) and 2.5% (vol-clustered) with no effect, and 85% with the planted effect.
- **What the failure means:** the test is calibrated under the null, and it recovers the planted effect without bias. TLT's 75% reflects the effect size I chose in A33 rule 3b: a per-minute shift of 0.05 x the base SD, about 0.27 SD of a 30-minute return. With about 220 TLT breaks per replicate, that gives roughly 75-80% power. With 40 replicates the Monte Carlo SE of 75% is about 7 points. It is not a defect of the test, but it fails the criterion as written.

## Decision for you

1. **Recommended:** amend A33 rule 3b to a planted shift of c = 0.08 (TLT +, HYG -, gold +; USD 0), keeping every criterion, and rerun under a new tag. Disclosed: this is chosen after seeing the 75%.
2. Or rerun with the same planted size and 200 planted replicates, so the rejection rate is estimated precisely. If the true rate is about 0.77, it would fail again.
3. Or accept the check as is (a deviation from rule 3c, with your approval).

After your decision the chain reruns from the synthetic step with `powershell -NoProfile -ExecutionPolicy Bypass -File section6
un_h2.ps1 -Tag <new tag>`. Synthetic is about 4 min; then power and the H2 dev run (Gaussian, HSMM; TRAIN only).

Files: `section6/results/h2_50_synth_a33.json`, `h2_50_synth_check_a33.json` (written once, sidecars), `h2_log.txt`.

---

# Report, 2026-11-10 (chain done 15:55 New York; addendum 16:40)

## Addendum 1: A29 3b intervals for H3 (post-hoc reporting only, at your request)

These are two-sided 95% basic week-block intervals, computed within era with 9,999 resamples and seed 0, as in the primary H3 test.
- They come from `section6/s6_posthoc_h3_ci.py`, which was hashed in the ledger before it ran.
- The script rebuilds the H3 rows exactly. Each rebuilt gamma equals the stored dev-run gamma, and so does each n.
- No test was changed. The p-values, Holm and BH results stand as written.

| | Gaussian HMM | HSMM |
|---|---|---|
| H3 TLT | gamma -0.164 [-0.220, -0.107] (402 breaks) | -0.139 [-0.206, -0.070] (339) |
| H3 gold | -0.185 [-0.242, -0.129] (420) | -0.156 [-0.223, -0.089] (373) |

- **All four intervals lie wholly below 0.** Under A29 3b this is reported as a **transient cross-asset response**: same-day TLT and gold moves that the next day does not continue beyond the prior-hour control. It is not a calming effect.
- Read with H4 (A29 3b), H4 shows no confirmation gain.
- **Gaussian TLT caveat:** the placebo-filter control flagged TLT, with delta +0.030 [+0.008, +0.052]. Even shifting gamma by that amount leaves the interval below 0: the upper end goes from -0.107 to about -0.08.
- Output: `section6/results/posthoc/h3_ci_a29_3b.json`, written once, with a sidecar.

## Addendum 2: H2 was not run, and is not yet runnable

**Why it is not in the report:**
- **Out of scope by design.** A28 rule 2 says "H2 unchanged". `s6_run.py` states "H2 is not computed here". The dev run approved in the ledger (2026-11-10 03:42Z) covers H3 and H4 only.
- **It belongs to the final evaluation.** H2 is a primary hypothesis of protocol 5.0, with its own Holm family across the 4 assets (5.11). It is run with the **H2 primary detector chosen at the 5.12 freeze** (A9 item 2) at the 5.13 era-level thresholds, and A26 labels that evaluation-period run.
- **No H2 code exists.** The cold audit lists "All of H2, S1, S2, E1, E2 and D1" as not implemented. Nothing has been written since.

**What is needed before the freeze:**
1. **An H2 amendment fixing what 5.0 leaves open**, decided by you before any code. Only the 30-minute slot is fixed so far (ledger 03:42Z).
   - **Test statistic:** how breaks are aggregated (for example, the mean cumulative return over breaks against the 10,000-draw placebo distribution of that mean), sidedness, and the p-value rule.
   - **Horizons:** which one is primary. 5.0 names T to T+30 as the primary window and lists -30 and +5/15/30/60 min; the status of the others needs fixing.
   - **Placebo draws:** A28 1d says H2 keeps its pre-registered placebo distribution exactly, so the before-the-break and past-alarm rules do not apply. Eligibility still needs fixing:
     - the pool: which sessions are eligible, and whether later sessions may be used;
     - alarm proximity;
     - whether a placebo may cross the close.
   - **T and the asset clock:** T = T_c, and the LEGACY offset.
   - **S1, S2, E1, E2:** operational definitions. E2 (overnight gaps) needs its own data definition.
2. **Code, unit tests, a synthetic check and a power check**, as done for H3 and H4.
3. **The H2 code in place before the freeze and the Section 6 fingerprint.** It has to be hashed with the rest of the Section 6 code before any evaluation output exists, so it cannot adapt to results.
4. **Optional:** a TRAIN-only development run of H2 on Gaussian and HSMM, as for H3 and H4. This needs your approval.

Until then the freeze manifest is ready on A21-A31, but H2 cannot run after the freeze.

**Decision for you:** may I draft the H2 amendment (items in 1) for your approval?

## Bottom line

**The Section 6 dev run is done for Gaussian HMM and HSMM. No primary test is rejected for either detector.**
- **H3** (next-day cross-asset volatility after a break): gamma is negative for every asset. TLT and gold have one-sided p of about 1.
- **H4a / H4b** (cross-asset confirmation): out-of-fold AUC gains are small and not significant. The closest is HSMM H4b, at +0.050, p = 0.084 (Holm 0.51).
- **Gaussian HMM fails two checks:**
  - the A28 7d null control: H4b rejects 10.5% of null sets, against a limit of 10%;
  - the A31 placebo-filter control flags TLT.
- **HSMM passes every check.**
- No freeze, no O8, no era calibration. TRAIN-span development data only. Results are labelled development; nothing read evaluation-period data.

## Done today, in order (all committed and pushed)

| Time (NY) | Step |
|---|---|
| 10:01 | A31 rule 3 revised to your decision (filtered vs matched placebos with no alarm exclusion; fully unfiltered = descriptive), hashed before code |
| 10:01 | A29 adopted as drafted (rule 3c kept): sidecar, ledger row |
| 10:02-10:04 | A30 written, hashed, adopted on your pre-approval; then its code |
| 10:31 | A31 rule 4 synthetic checks **PASS 29/29** (tag a31r); A31 adopted by the chain |
| 10:31 | Chain stopped at the gate by **my bug** (PowerShell split the inline gate code at spaces). All four amendments were in fact adopted. Fixed, ledger row, resumed at the gate (10:32) |
| 11:43 | Your instruction: the chain's PowerShell parent was replaced so that the dev run starts with 2 x 3 workers. The power check (2 x 7) was not touched |
| 12:04 | Power done (no crash, no restart); dev run starts |
| 14:55-15:15 | Dev run paused at your request (processes suspended), then resumed |
| 15:55 | Dev run done: 231.8 min including the 20-minute pause; exit 0 for both detectors; no tracebacks |

**Memory headroom during the dev run:**
- 5,255 MB free of 16,069 MB at the start;
- 2,504 to 3,802 MB free over the first 30 minutes;
- about 4,700 MB free at 13:43.

## A31 synthetic checks (rule 4, 999 resamples, 200 null / 40 effect replicates)

| Check | Independent | Vol-clustered | Limit |
|---|---|---|---|
| Six primary tests, rejection under no effect | 0.5-4.5% | 0-5.5% | 8.1% |
| Revised rule 3 control, flag rate (TLT/HYG/gold/USD) | 6.0/6.0/4.0/4.5% | 5.5/5.0/4.5/7.0% | 8.1% |
| Rule 3 control, mean delta | -0.001 to +0.002 | -0.001 to +0.002 | |
| Fully unfiltered comparison (descriptive): mean delta | +0.033 to +0.036 | +0.046 to +0.050 | not a criterion |

**Planted effects recovered:**
- H4a: 0.207 vs target 0.207.
- H4b: 0.266 vs 0.268.
- H3 TLT / HYG / gold: 0.242 / 0.115 / 0.245 vs 0.252 / 0.126 / 0.252.

## Power (A29 1f, A31 units; 200 simulations, 999 resamples, first Holm step 0.05/6)

| | Gaussian HMM | HSMM |
|---|---|---|
| Breaks / H4a units / weeks | 600 / 1,853 / 394 | 549 / 2,480 / 365 |
| H3: minimum detectable gamma | 0.15 SD (power 0.87) | 0.15 SD (power 0.855) |
| H4a: minimum detectable AUC gain | 0.067 | 0.035 |
| H4b: minimum detectable AUC gain | **not reached** (power 0.735 at gain 0.104) | **not reached** (power 0.585 at gain 0.102) |

H4b is underpowered: a null H4b result says little.

## Development run: primary tests (9,999 resamples, Holm m = 6)

| Test | Gaussian: n, estimate, p (Holm) | HSMM: n, estimate, p (Holm) |
|---|---|---|
| H3 TLT | 402 breaks, gamma -0.164, p 1.00 (1.00) | 339, -0.139, p 1.00 (1.00) |
| H3 HYG | 243, -0.071, p 0.97 (1.00) | 205, -0.043, p 0.84 (1.00) |
| H3 gold | 420, -0.185, p 1.00 (1.00) | 373, -0.156, p 1.00 (1.00) |
| H3 USD | 9, -0.282, p 0.73 (1.00) | 11, -0.213, p 0.75 (1.00) |
| H4a | 1,853 (280 confirmed), gain +0.016, p 0.28 (1.00) | 2,480 (365), +0.013, p 0.19 (0.94) |
| H4b | 597 (203 real), gain -0.009, p 0.58 (1.00) | 545 (198), +0.050, p 0.084 (0.51) |

**How to read these:**
- **H3 is negative, not merely null.** A29 3b says a negative gamma is reported as a transient cross-asset response, never as calming, and only when gamma's two-sided 95% interval lies wholly below 0.
  - That interval is not in the dev-run output: `h3_test` reports only the one-sided p. One-sided p of about 1 for TLT and gold means the bootstrap almost never reached 0, but I have not computed the 3b interval.
  - **Decision for you:** may I compute it? It is post-hoc reporting from the saved inputs, with no change to any test.
- **The A29 3c diagnostic** (prior-hour control before S) moves gamma toward 0, for example TLT -0.164 to -0.141 (Gaussian) and -0.139 to -0.110 (HSMM). Part of the negative gamma sits in the S-to-T window, as A29 3a anticipated.
- **USD** has only 9 or 11 breaks (it is available only in 2018 in LEGACY), so it carries no information.
- **About 27% of breaks** (162/600 and 159/549) have no cross-asset data at all, because no asset is covered before 2007.

## Checks

| Check | Gaussian HMM | HSMM |
|---|---|---|
| A28 7d(i) positive control (Fed breaks, TLT rest of day) | gamma 0.59, p 0.0001: **pass** | gamma 0.58, p 0.0002: **pass** |
| A28 7d(ii) null sets (200), rejection per test <= 0.10 | H3 0.5-6.5%, H4a 4.5%, **H4b 10.5%: FAIL** | max 8.0% (H4b): **pass** |
| A31 rule 3 control (filtered vs matched without alarm exclusion) | **TLT flagged**: delta +0.030 [+0.008, +0.052]; HYG, gold, USD not flagged | none flagged (TLT +0.012 [-0.010, +0.032]) |
| A31 3e fully unfiltered comparison (descriptive) | delta +0.010 to +0.025 | delta -0.051 to +0.019 |

**What the Gaussian failures mean (rules as written; nothing amended):**
- **H4b null rejection 10.5% vs 10%.** At 200 sets the Monte Carlo SE is about 2.1 points, so this is within noise of the limit. It still fails the rule as written, and the Gaussian H4b result is read with that caveat. The H4b result is not significant either way.
- **TLT flag.** The alarm filter raises the placebos' next-day TLT volatility by about 0.03. That pushes the Gaussian H3 TLT gamma downward by about that much. It does not change the sign or the conclusion (gamma -0.164).

## Secondary analyses (BH)

**Nothing survives BH:** 0 of 68 tests (Gaussian) and 0 of 69 (HSMM).
- Smallest raw p: HSMM LEGACY offset +1 H4b, p 0.009, and HSMM H4b at the 70th percentile, p 0.064.
- **Since 2007:** H3 is identical to the primary results, because no asset has data before 2007. H4 differs slightly.
- **Fed vs non-Fed:**
  - H3 gamma is more negative on Fed breaks: TLT -0.23 / -0.43, gold -0.43 / -0.41.
  - n = 26-43 Fed breaks; no test significant.
- **Detector dependence (A28 7a):**
  - every detector gives negative H3 for TLT and gold, BOCPD included (-0.07);
  - Student-t is the only detector with a positive HYG gamma, +0.038, p 0.18.

## A30 lead-lag description (descriptive, no test)

- **Windows:** 538 of 600 breaks (Gaussian) and 485 of 549 (HSMM) were evaluated; the rest crossed the open or the close.
- **Breaks look like the chance reference.** Each placebo was put through the same calculation against the other placebos.

**Share of breaks where SPY's S comes first:**

| | Gaussian, breaks | Gaussian, chance | HSMM, breaks | HSMM, chance |
|---|---|---|---|---|
| All available assets | 0.37 | 0.38 | 0.40 | 0.39 |
| TLT | 0.56 | 0.60 | 0.56 | 0.59 |
| HYG | 0.89 | 0.85 | 0.87 | 0.87 |
| Gold | 0.59 | 0.54 | 0.61 | 0.55 |

- **Timing:** the median first exceedance is 0 to 10 minutes before S for TLT and gold, against 5 to 10 minutes before S under chance.
  - At least one exceedance occurs in 60-65% of windows (chance 62-71%).
  - So there is no sign that cross-asset moves cluster around the break beyond chance.
- **Fed breaks, the one visible difference:** gold moves first more often.

  | Gold, Fed breaks | Breaks | Chance |
  |---|---|---|
  | SPY first (Gaussian / HSMM) | 0.33 / 0.24 | 0.53 / 0.55 |
  | Exceedance rate | 79% / 82% | 69-76% |

  - With n = 42 / 38 this is descriptive only.
- **HYG** exceeds in only about 20% of windows, against 23% by chance, so its first-exceedance numbers are thin. That is probably HYG's many zero 1-minute returns: an exceedance must be strictly above the 90th percentile.

## Decisions for you

1. **A29 3b interval for H3:** done; see Addendum 1.
2. **The Gaussian failures stand as written:**
   - the null-set check (H4b 10.5%);
   - the TLT flag.

   I recommend no amendment: report them as caveats.

## Files

- **Results:** `section6/results/s6_development_{gaussian_hmm,hsmm}.json` and `power_{gaussian_hmm,hsmm}.json`, each with a sha256 sidecar. Each records its provenance: code hashes and the A28-A31 manifest.
- **Synthetic checks:** `synth_validation_a31r.json`, `synth_check_a31r.json`.
- **Chain:** `section6/results/overnight_log.txt`.
- Code version a0323ed24d68e896 is unchanged.
- **Not opened:** the old `q_power_*` logs from the stopped run.
