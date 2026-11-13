# Section 7 facts: cross-asset methods and results (H2, H3, H4)

**Status.** Compiled 2026-11-13 UTC (2026-11-12 New York), read-only, from the amendments, the result files and the disclosure lists cited in each row. Facts only: no interpretation beyond what the cited documents state. Every evaluation-period number carries the A26 label "adaptive/exploratory (previously exposed period)" with `confirmatory` = false (A26 1d; A36 1a).

**Notation.**
- **Primary detectors.** Development results are given for the two detectors run in development: Gaussian HMM ("G") and HSMM ("H"). Evaluation results use the frozen primary detector, Gaussian HMM, for H2 and for H3/H4.
- **p-values.**
  - H2: two-sided.
  - H3 and H4: one-sided.
  - "Holm" is the Holm-adjusted p of each primary family; "BH" is the Benjamini-Hochberg-adjusted p of the secondary family.

---

## 1. Data sources per asset

| Asset | Instrument | Source (Section 2) | Source file(s) (`REPRODUCIBILITY_FACTS.md` section 3) | Documented start |
|---|---|---|---|---|
| SPY (trigger) | SPDR S&P 500 ETF | HF Data Library, 1-minute OHLCV | LEGACY: `hfdatalibrary_clean_1min_5tickers_2026-10-03.zip` (Clean); RAW: `hfdatalibrary_raw_1min_1tickers_2026-10-13.zip` (Raw) | 2002-12-30 |
| TLT | iShares 20+ Year Treasury Bond ETF | HF Data Library, 1-minute OHLCV | LEGACY: the Clean 5-ticker zip; RAW: `TLT_raw_1min.csv` | 2002-12-30 |
| HYG | iShares iBoxx $ High Yield Corporate Bond ETF | HF Data Library, 1-minute OHLCV | LEGACY: the Clean 5-ticker zip; RAW: `HYG_raw_1min.csv` | 2007-04-11 |
| Gold | XAU/USD spot (not GLD) | Dukascopy, 1-minute bid/ask OHLC, midpoint | `xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv` | 2007-04-11 |
| USD | Dukascopy Dollar Index `dollaridxusd` (not the ICE DXY) | Dukascopy, 1-minute bid/ask OHLC, midpoint | `dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv` | 2017-12-01 |

Sources: `Section_2_Data_Sources_Decision_Notebook.md:16-20,24`; `REPRODUCIBILITY_FACTS.md` section 3.
- Gold and USD are labelled "Provisional" in the Section 2 table.

**Gold and USD prices are the bid/ask midpoint.** This was checked in the code on 2026-11-13, read-only. Only the bid files are listed in the Section 2 inventory and in `REPRODUCIBILITY_FACTS.md`, but the panel's gold and USD returns are built from both the bid and the ask files. The chain is:

1. **Section 3.5** (`section3_5_quote_quality.py`):
   - It reads both sides of each instrument: `xauusd-m1-bid-...` and `xauusd-m1-ask-2007-04-11-2026-10-02.csv`; `dollaridxusd-m1-bid-...` and `dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv` (lines 32-38). It reads the columns `timestamp, open, high, low, close` (line 92).
   - Midpoint = (bid close + ask close) / 2, only on exact-minute paired minutes where both sides are valid (`compute_quality`, lines 142-147). It is written as `mid_close` (line 304). Bid-only and ask-only minutes are marked BID_ONLY / ASK_ONLY (lines 172-173), so they have no midpoint.
   - The run record `section3_5_quote_quality_results/summary.json` names both source files per asset (key `assets.{GOLD,DOLLAR}.quote_files.bid/ask`). It gives `midpoint_definition` = "(bid CLOSE + ask CLOSE)/2 only for exact-minute matched, valid side OHLC; indicative asynchronous quote proxy".
2. **Section 3.6** (`section3_6_return_construction.py`):
   - For GOLD and DOLLAR it reads `mid_close` from the 3.5 output (lines 177, 186; input path line 152) and computes log(price_t / price_{t-1}) on eligible endpoints (line 94).
   - The endpoint mask is `baseline_paired_non_crossed` (line 187). The price type is recorded as `INDICATIVE_PAIRED_CLOSE_MIDPOINT` (line 260).
3. **Section 3.10** (`section3_10_run/section3_10_cross_asset_alignment.py`):
   - It reads `log_return_1m` and the eligibility fields from `section3_6_return_results/returns_1m_{GOLD,DOLLAR}.csv.gz` (lines 106, 113) and requires `source_epoch` = "dukascopy" (lines 120-122).
   - It writes them unchanged as `GOLD_log_return_1m` / `DOLLAR_log_return_1m` and `*_return_eligible` (lines 313-314). The file `section3_final_run/reference_sources/section3_10_cross_asset_alignment.py` is byte-identical.
4. **Section 6** reads only `{asset}_return_eligible` and `{asset}_log_return_1m` from the canonical panel:
   - development: `section6/s6_run.py:53`, used at line 29;
   - evaluation: `section6/s6_eval.py:87`;
   - coverage: `section6/s6_coverage.py:43,58` and `s6_eval.py:70`, which also read `{GOLD,DOLLAR}_causal_flat_age_ge15_flag`.

   It uses the baseline mask `*_return_eligible`, **not** `GOLD/DOLLAR_strict_quote_return_eligible`. The strict mask (spread at most 50 bp and joint flat age below 15) is not used by any Section 6 test.

**Hash gap.** The ask files are not in the Section 2 inventory. Their SHA-256 on disk (`OneDrive\Desktop\data\raw\`) was computed 2026-11-12 (New York) and was not recorded at the Section 3.5 run. Both hashes are now in `REPRODUCIBILITY_FACTS.md` section 3:
- `xauusd-m1-ask-2007-04-11-2026-10-02.csv`: `dfadecccb5b08bc0a75d39f84f250d4c79c66f814c1f35a207b4376564e0e8ed`;
- `dollaridxusd-m1-ask-2017-12-01-2026-10-02.csv`: `764966e3cbdbe9ed4607ecbe584e43f9f4d787ef7f1c4b6ffbd82879e8a2d163`.

**Row-count check.** The Section 3.5 run record lists paths and row counts but no hashes. The data rows in each file now (excluding the header) equal the record's `total`:
- gold ask: 8,504,432;
- dollar ask: 2,696,661.

The record's regular-hours counts (1,889,774 and 803,292) were not recomputed. Matching totals are consistent with the files being unchanged since that run, but do not prove it.

**Measurement (A28 1a, 1c).**
- Volatility is measured on NYSE regular hours (09:30-16:00 ET) for every asset, from 1-minute log returns.
- A bar stamped at minute m is available at m + 60 s, for SPY and for every asset. This is the Section 3 minute-start assumption, conditional for LEGACY.
- All assets come from the canonical panels: `section3_10_alignment_results/canonical_panel_{LEGACY,RAW}_1m.csv.gz`.

**Availability rule (A28 1e, 6b).** A session counts as available for an asset when the label-free coverage check passes it. The thresholds were approved by the user on 2026-11-09:
- at least 80% usable minutes;
- largest gap at most 30 minutes;
- stale-quote share at most 25% (`section6/results/coverage/coverage_summary.json` key `rule`).

### 1a. Coverage by era: available sessions

| Asset | LEGACY TRAIN span (4,022 sessions, 2003-01-02..2018-12-21) | RAW TRAIN span (705, 2022-03-07..2024-12-23) | LEGACY evaluation (800, 2019-01-02..2022-03-04) | RAW evaluation (445, 2025-01-02..2026-10-12) |
|---|---|---|---|---|
| SPY | 3,984 (99.1%) | 699 (99.1%) | 794 (99.3%) | 442 (99.3%) |
| TLT | 2,736 (68.0%) | 507 (71.9%) | 794 (99.3%) | 395 (88.8%) |
| HYG | 2,158 (53.7%; first available year 2008) | 550 (78.0%) | 794 (99.3%) | **268 (60.2%)** |
| Gold | 2,894 (72.0%; from 2007) | 698 (99.0%) | 784 (98.0%) | 434 (97.5%) |
| USD | 232 (5.8%; from 2017) | 649 (92.1%) | 714 (89.3%) | 403 (90.6%) |

Sources:
- TRAIN spans: `section6/results/coverage/coverage_summary.json`, written 2026-11-10 03:42Z over the whole TRAIN span. Development tests use the test segments of the uncontaminated folds inside these spans (A28 1f).
- Evaluation: `section6/results/coverage_evaluation.json`, rows per era, asset and session.

---

## 2. Breaks (A28 1b; A33 G4; A35 3)

**Definition.** Confirmed calm-to-stressed SPY alarms of the detector analysed, at its Section 6 threshold (0.2 confirmed alarms per session on the fold's validation sessions; A6 item 3, A7), with the main event rule.
- "Calm-to-stressed" is A28 1b's "entry into the higher-variance state". The break export implements it (`section5/s5_break_export.py`): new state = argmax at the confirming update; old state = the event rule's reference state; calm-to-stressed when new > old in the family's variance order; BOCPD uses the predictive-variance ratio.
- This is not protocol 5.5's return-variance ratio (disclosure S6-D4).

**Times.**
- S = the availability time of the first update of the confirming run (T_d).
- T = 0 at confirmation (T_c).

**Burn-in.**
- H3 and H4: at least 60 prior sessions in the era (A28 1g).
- H2: no burn-in (A33 G4).
- In the evaluation, each era is preceded by its last 60 TRAIN sessions as history (A36 4b), so every evaluation unit passes the burn-in.

**Primary detector.**
- H2: the H2 primary detector of the freeze (A9 item 2). This is the Gaussian HMM (`section5/results/section5_freeze.json`; freeze 2026-11-12).
- H3 and H4: the same detector unless A35 rule 3a applied. It did not: the A35 rerun gave "A35 3c: the Gaussian HMM passes; nothing changes" (`section6/results/a35_null_control_gaussian_hmm.json`).

### 2a. Break counts

| | Gaussian HMM | HSMM |
|---|---|---|
| **Development**, confirmed calm-to-stressed, LEGACY / RAW | 586 / 14 (total 600) | 536 / 13 (total 549) |
| Development: removed by burn-in | 0 | 0 |
| Development, LEGACY: breaks by number of available assets (0 / 1 / 2 / 3 / 4) | 162 / 21 / 130 / 273 / 0 | 159 / 33 / 104 / 240 / 0 |
| Development, RAW: same | 0 / 0 / 2 / 5 / 7 | 0 / 0 / 4 / 3 / 6 |
| Development: breaks with fewer than 20 placebos, LEGACY / RAW | 9 / 6 | 8 / 3 |
| Development H4a units (calm-state streak starts): confirmed / fizzle / open, LEGACY | 276 / 1,476 / 29 | 352 / 1,914 / 29 |
| Development H4a units, RAW | 4 / 65 / 3 | 13 / 169 / 3 |
| **Evaluation**, confirmed calm-to-stressed, LEGACY / RAW | 171 / 47 (total 218) | not run (not primary) |
| Evaluation: removed by burn-in | 0 | |
| Evaluation, LEGACY: breaks by number of available assets (0 / 1 / 2 / 3 / 4) | 0 / 0 / 0 / 18 / 153 | |
| Evaluation, RAW: same | 0 / 0 / 4 / 20 / 23 | |
| Evaluation: breaks with fewer than 20 placebos, LEGACY / RAW | 3 / 3 | |
| Evaluation H4a units: confirmed / fizzle / open, LEGACY | 64 / 165 / 4 | |
| Evaluation H4a units, RAW | 16 / 45 / 0 | |

Sources: `section6/results/s6_development_{gaussian_hmm,hsmm}.json` and `s6_evaluation_gaussian_hmm.json`, key `counts`. The 5.13 break exports have all kinds and directions: `section5/results/evaluation_{LEGACY,RAW}.json` key `n_breaks_by_family_kind`.

**Development export, confirmed breaks by label, all detectors** (`section5/results/breaks/breaks.csv`). No confirmed break is labelled same_state or left without a direction.

| Detector | LEGACY calm-to-stressed / stressed-to-calm | RAW calm-to-stressed / stressed-to-calm |
|---|---|---|
| Gaussian HMM | 586 / 120 | 14 / 2 |
| Student-t HMM | 493 / 185 | 14 / 0 |
| HSMM | 536 / 88 | 13 / 0 |
| BOCPD | 409 / 162 | 17 / 9 |

---

## 3. Placebos

| Use | Rule | Conditions |
|---|---|---|
| **H3, H4b** | A28 1d with A31 rule 1 | Same era; a session **before** the unit's session; the same 30-minute slot of S; the same SPY prior-hour-RV decile, with cut points from earlier sessions only; **no confirmed SPY alarm with T_c in [T_p - 60, T_p)** (past alarms only); T_p = S_p + gap of the matched unit, at most 390; 20 per unit. |
| **H4a** | A31 rule 2b | As above with gap = 0 for every unit, so the placebos do not depend on the label. |
| **H2 primary** | A33 G5-G7 | Candidates: the SPY update times (5-minute grid) of the era's sessions with detector output, excluding the break's own session. Earlier **and later** sessions count. Matched on the 30-minute slot of T, the SPY prior-hour-RV decile at T (cut points from all candidates of the era) and the era. **No alarm exclusion.** 10,000 draws, one placebo per break per draw, uniform with replacement. |
| **A34 per-asset pools** (E1, the A32 statistic, the H3 sensitivity) | A34 rule 1 | A31 rule 1 plus: asset a is available in the placebo's session. Cut points are unchanged. Seed fixed per (unit, asset). For E1's chance reference, a joint pool with TLT and HYG both available. |
| **Evaluation** | A36 4c, 4d | Units, candidates, placebo draws, decile cut points, H2 pools and the alarms used for exclusion come from evaluation sessions only. History sessions serve only the causal medians, H3's prior-day control and the burn-in count. A break with fewer than 10 earlier candidates has no placebos. |

**Why A34 exists** (A34 preamble). In the label-free diagnosis `section6/results/hyg_gap/hyg_gap.json`, 78-81% of HYG placebo windows fell on sessions without HYG data, because the A28/A31 placebos are matched on SPY only. A34 is labelled "post-diagnosis".

---

## 4. Hypotheses: exact statistics and families

### 4a. H2: same-window cross-asset return (A33; protocol 5.0 restored)

- **Statistic (A33 rule 1, G1, G3).** M = the mean over breaks of the signed cumulative 1-minute log return of the asset over (T, T + 30] (minute indices T..T+29). Each of the 10,000 draws computes the same mean with one matched placebo per break.
- **p-value (G2).** Two-sided: p = min(1, 2 min(P_lo, P_hi)), where P_lo = (1 + #{M_b <= M}) / 10,001 and P_hi = (1 + #{M_b >= M}) / 10,001.
- **Use (G8).** A break is not used for an asset when T + 30 > 390, when the asset is unavailable that session, or when its pool is empty. With fewer than 5 breaks the test is not evaluable.
- **Family.** Holm across the 4 assets (TLT, HYG, gold, USD), m = 4 always. A non-evaluable test enters with p = 1 (G9).
- **Secondary (BH; G10).** Horizons -30 (T - 30, T], +5, +15 and +60. Stressed-to-calm at +30. S2 detector dependence: the same test on every detector's breaks, with the Holm verdict per detector shown side by side.
- **Exploratory (A33 rule 4).** The A32 statistic: per break, deseasonalised |r| = |r| / sqrt(m), where m is the causal median of the same window's RV over the asset's previous 20 sessions (at least 10). The per-break contribution is the break value minus the mean over its placebos. G is the mean over breaks; one-sided week-block bootstrap, 9,999 resamples. Uncorrected and labelled "specified after seeing the H3/H4/A30 development results". From A34 it uses per-asset pools.
- **Disclosed limitation (A33).** The placebo distribution treats breaks as independent.
- **History of the definition.** A32 (2026-11-10 21:33Z) briefly replaced H2 by the |return| statistic. A33 (21:40Z) restored the pre-registered 5.0 H2 before any H2 statistic had been computed on real data. A33.1 raised the synthetic planted shift from 0.05 to 0.08 per minute after the first check missed one criterion (planted TLT rejected in 75% against the required 80%). That run stays on record (`section6/results/h2_50_synth_check_a33.json`).

### 4b. H3: next-day volatility tripwire (A28 rule 3; A29 rule 3)

- **Outcome.** The log of the next regular-hours session's RV of the asset. Secondary: log RV from T to 16:00 the same day, when at least 30 minutes remain.
- **Model (A28 3b).** OLS on breaks and placebos together:
  - the outcome on the asset's own controls known at T: log RV of the prior hour (T - 60, T], log RV of the prior session, own return from S to T, and its absolute value;
  - then the same model plus a break indicator.

  Statistic: the indicator's coefficient gamma. H0: gamma <= 0, one-sided.
- **p-value (A28 3c).** Week-block bootstrap: calendar weeks, blocks within era, 9,999 resamples, centred, add-one.
- **Reading (A29 3a-3c).**
  - H3 and H4 are not independent: the prior-hour control contains (S, T].
  - A gamma < 0 is never a rejection. When its two-sided 95% interval lies wholly below 0, it is reported as a "transient cross-asset response", not a calming effect.
  - Descriptive diagnostic: the prior-hour control taken over (S - 60, S].

### 4c. H4: confirmation (A28 rule 4; A29 rule 1; A31 rule 2; A35 rule 1)

- **Score C(t) (A28 4a).** The share of available assets whose |own return| over the window up to t exceeds the 90th percentile of the same quantity over the unit's placebos. Window at S: the 15 minutes before S. At T = 0 and at T + 15: from S to t.
- **H4a (primary), at S.**
  - Units: every streak start S with the detector in its lowest-variance state (`old_state` = 0), whatever follows (A31 2a).
  - Label: 1 if the streak confirms, 0 if it fizzles or is open at the close.
  - Not defined for BOCPD.
- **H4b (primary), at T = 0.**
  - Units: the confirmed calm-to-stressed breaks.
  - Label "real break": the next session's deseasonalised SPY RV is above the 80th percentile of the prior 20 sessions (A28 4d).
- **Statistic (A29 1a-1c).**
  - Two logistic models, fitted by Newton with ridge 1e-6: SPY's own information at t (return from S to t; log RV of the prior hour), and the same plus C(t).
  - Folds: K = 5 contiguous blocks of calendar weeks per era. Each fold is evaluated with models fitted on the other four.
  - Within each fold: AUC (midranks) with C minus AUC without C. The statistic is the mean of the fold gains weighted by units per fold; single-class folds are left out.
  - H0: gain <= 0, one-sided.
- **p-value (A35 1a).** p = (1 + #{valid b: G*_b - G >= G}) / (V + 1), on the V valid (finite) resamples of the A28 3c bootstrap. V = 0 means not evaluable (p = 1 in Holm). V/B is reported, and V/B < 0.9 is flagged `low_valid_share` (A35 disclosure).
- **Size (A29 1g).** Read from the out-of-fold AUC of the model with C next to the SPY-only model's AUC.

### 4d. Families

| Family | Tests | Correction |
|---|---|---|
| H2 primary | TLT, HYG, gold, USD at +30 | Holm, m = 4 (A33 rule 1; protocol 5.11) |
| H3/H4 primary | H3 next-day TLT, HYG, gold, USD; H4a; H4b | Holm, m = 6 (A28 5b) |
| H2 secondary | -30, +5, +15, +60 per asset; stressed-to-calm +30; S2 detector dependence; each evaluation era alone (A36 1d) | BH (A33 G10) |
| H3/H4 secondary | H3 rest-of-day; H4b at S and T + 15; 5-day label; 70th/90th percentile labels; stressed-to-calm; Fed split; LEGACY clock offsets ±1 min; anchor T0 at S; detector dependence; each evaluation era alone | BH (A28 5c, rule 7; A36 1d) |
| A34 H3 sensitivity | H3 next-day per asset with per-asset pools | BH of 4, outside Holm (A34 2c) |
| Exploratory and descriptive | A32 statistic (uncorrected); E1; A30; curve and taxonomy; A29 3c; A31 rule 3 control | none |

Evaluation (A36 1b, 1c): every statistic uses evaluation units only. The two eras are combined as in development, with every within-era rule applied per era. Development results are never pooled with evaluation results.

---

## 5. Secondary and descriptive analyses: definitions

- **A30 lead-lag (descriptive; no test).**
  - Units are the H3 units; window [S - 30, T + 60] in 5-minute bars aligned to S. A window that starts before 09:30 or crosses the close is skipped.
  - Per asset: the first bar whose |cumulative return| exceeds the 90th percentile of the same bar over the unit's placebos (at least 10 values).
  - Reported: the time of that bar relative to S and to T; the share where SPY's S comes first; Fed/non-Fed; a chance reference from the placebos.
- **E1 footprint taxonomy (descriptive; A32 4c, A34 2b; Cieslak and Pang).**
  - Breaks with TLT and HYG available. The move over (T, T + 30] is "unusual" when it is beyond the asset's placebo 90th percentile.
  - Categories, in order: flight to safety (TLT up, HYG down); credit stress (HYG down, TLT not up); dollar-driven (USD up); SPY-only (none unusual); other.
  - Shares for breaks are reported against placebo shares.
- **E2** (overnight gaps): deferred to future work (A32 4d).
- **S1** (return between T_d and T_c): covered by H4a and A30 (A32 4a).
- **Detector dependence (A28 7a; A32 4b / A33 5b).** H2, H3 and H4 recomputed with each of the four families' breaks. Also, for H3/H4, T = 0 moved to S (alternative anchor).
- **Fed split (A28 7c; A36 3d).** Breaks with S inside [release, release + 60 min] on FOMC days, against all others. Evaluation FOMC list: `section5/results/h1c_schedule_times_evaluation.json`.
- **LEGACY clock offsets (A28 7e).** The SPY clock shifted by -1 and +1 minute relative to the asset clocks; 0 is primary.
- **2007+ sensitivity (A28 7f).** Development only. On the evaluation it equals the primary by construction (A36 2b).

---

## 6. Sanity checks and A35

- **Positive control (A28 7d(i)).** Fed breaks should raise TLT rest-of-day RV above placebo.
- **Null control (A28 7d(ii)).**
  - 200 sets of random times drawn like placebos replace the breaks.
  - The rejection rate at 0.05 must be at most 0.10 for each of the six primary tests.
  - In development a failure stops the work. On the evaluation periods it is reported, not a gate (A36 2c).
- **A31 rule 3 placebo-filter control.** Per asset, the H3 next-day regression compares filtered placebos with matched times drawn without the alarm exclusion. It is flagged when the 95% interval of delta excludes 0. It is a check outside Holm and BH; see S6-D1 for why a flag is not specific to the filter.
- **A35.**
  - Rule 1: the H4 p is computed on valid resamples only.
  - Rule 2: the development null control was rerun with the same 200 sets and seeds. It reproduced the stored A29-convention rates exactly.
  - Rule 3: had the Gaussian HMM failed, HSMM would have become the H3/H4 primary.
  - Disclosure: rule 1 can only lower null rejection rates.

| Check | Gaussian HMM, development | HSMM, development | Gaussian HMM, evaluation |
|---|---|---|---|
| Positive control: n breaks, gamma, p | 39, +0.590, 0.0001 (passed) | 33, +0.583, 0.0002 (passed) | 27, +0.479, 0.0014 (passed) |
| Null control (dev run, A29 convention): TLT / HYG / gold / USD / H4a / H4b | 0.040 / 0.055 / 0.005 / 0.065 / 0.045 / **0.105** (failed) | 0.025 / 0.010 / 0.000 / 0.040 / 0.000 / 0.080 (passed) | n/a |
| Null control, A35 rule 1 (valid resamples) | 0.040 / 0.055 / 0.005 / 0.065 / 0.045 / **0.065** (passed) | 0.025 / 0.010 / 0.000 / 0.040 / 0.000 / 0.040 (passed) | **0.110** / 0.050 / **0.305** / 0.060 / 0.010 / 0.030: **failed** (H3 TLT and H3 gold above 0.10) |
| A31 rule 3 filter control flags (delta) | **TLT flagged** (+0.030, 95% +0.008 to +0.052); HYG, gold, USD not | none | **TLT flagged** (+0.028, 95% +0.007 to +0.049); HYG, gold, USD not |

Sources:
- `section6/results/s6_development_{gaussian_hmm,hsmm}.json` and `s6_evaluation_gaussian_hmm.json`, keys `sanity` and `placebo_filter_control`;
- `section6/results/a35_null_control_{gaussian_hmm,hsmm}.json`.

The evaluation file states `sanity_note` = "reported, not a gate, on the evaluation periods (A36 2c)".

**Not reported until now.** The evaluation null-control failure (H3 TLT 0.110, H3 gold 0.305) was not in the evaluation report of 2026-11-12 in `reply_latest.md`, nor in `POST_EVAL_AUDIT.md`.

---

## 7. Results: development (TRAIN-span test segments of the uncontaminated folds)

### 7a. H2 primary (+30; Holm of 4)

| Asset | G: breaks used | G: p | G: Holm | H: breaks used | H: p | H: Holm |
|---|---|---|---|---|---|---|
| TLT | 397 | 0.904 | 1.0 | 335 | 0.085 | 0.272 |
| HYG | 280 | 0.952 | 1.0 | 242 | 0.461 | 0.461 |
| Gold | 418 | 0.037 | 0.148 | 364 | 0.068 | 0.272 |
| USD | 13 | 0.640 | 1.0 | 12 | 0.082 | 0.272 |

- No rejection, either detector.
- H2 secondary family (31 tests): one BH survivor per detector, **TLT pre-30** (raw p 0.0002, BH 0.0062).
- Holm verdict agreement across the four detectors: no rejection for any detector or asset.
- Source: `section6/results/h2_development_{gaussian_hmm,hsmm}.json`.

### 7b. H3/H4 primary (Holm of 6)

| Test | G: n | G: gamma or gain | G: p | G: Holm | H: n | H: gamma or gain | H: p | H: Holm |
|---|---|---|---|---|---|---|---|---|
| H3 TLT | 402 | -0.164 | 1.000 | 1.0 | 339 | -0.139 | 1.000 | 1.0 |
| H3 HYG | 243 | -0.071 | 0.975 | 1.0 | 205 | -0.043 | 0.844 | 1.0 |
| H3 gold | 420 | -0.185 | 1.000 | 1.0 | 373 | -0.156 | 1.000 | 1.0 |
| H3 USD | 9 | -0.282 | 0.733 | 1.0 | 11 | -0.213 | 0.755 | 1.0 |
| H4a | 1,853 (280 confirm) | +0.016 | 0.284 | 1.0 | 2,480 (365) | +0.013 | 0.189 | 0.944 |
| H4b | 597 (203 real) | -0.009 | 0.577 | 1.0 | 545 (198) | +0.050 | 0.084 | 0.506 |

- **Out-of-fold AUC, with C / SPY only.**
  - H4a: G 0.602 / 0.586; H 0.624 / 0.611.
  - H4b: G 0.515 / 0.524; H 0.552 / 0.502.
- **H4 p under A35 rule 1** (`AMENDMENT_A35.md` table; the stored files keep the A29 1d convention, A35 1f): G H4a 0.294, G H4b 0.652, H H4a 0.190, H H4b 0.087.
- **No rejection.** The H3/H4 secondary family has no BH survivor for either detector. The smallest raw p is:
  - G: detector dependence, HSMM H4b, 0.084;
  - H: LEGACY offset +1, H4b, 0.0092.
- **A29 3b intervals.** The 95% interval of the H3 next-day gamma lies wholly below 0 for TLT and gold, for both detectors, so both are reported as a "transient cross-asset response" (`section6/results/posthoc/h3_ci_a29_3b.json`, post-hoc reporting):

  | | TLT gamma (95% interval) | Gold gamma (95% interval) |
  |---|---|---|
  | Gaussian HMM | -0.164 (-0.220, -0.107) | -0.185 (-0.242, -0.129) |
  | HSMM | -0.139 (-0.206, -0.070) | -0.156 (-0.223, -0.089) |

- **2007+ sensitivity (A28 7f; key `sens_2007`).** The four H3 tests are identical to the primary: same n, gamma and p. H4 differs:

  | Test | n | Gain | p |
  |---|---|---|---|
  | G H4a | 1,572 | +0.026 | 0.192 |
  | G H4b | 439 | +0.008 | 0.284 |
  | H H4a | 1,979 | +0.014 | 0.168 |
  | H H4b | 393 | +0.037 | 0.201 |

  These are secondary (BH), and none survives.
- **Power (A28 6d, A29 1f; before the development results; first Holm step).** MDE for H3 gamma: 0.15 SD units (both detectors). MDE for the H4a AUC gain: G 0.067, H 0.035. H4b's MDE was not reached. H2 MDE: 0.15 SD of a break's 30-minute return (both detectors).
  - Sources: `section6/results/power_{gaussian_hmm,hsmm}.json`, `h2_50_power_{gaussian_hmm,hsmm}.json`.
- **Sources:** `section6/results/s6_development_{gaussian_hmm,hsmm}.json`.

### 7c. Development secondary and descriptive (selected; full content in the cited files)

| Item | Gaussian HMM | HSMM |
|---|---|---|
| A34 H3 sensitivity (per-asset pools): gamma, BH p for TLT / HYG / gold / USD | -0.112, -0.069, -0.170, -0.033; all BH 1.0 | -0.119, -0.072, -0.152, -0.155; all BH 1.0 |
| A32 exploratory statistic (+30, per-asset pools): G and raw p | TLT +0.293 (0.0001); HYG +0.240 (0.0012); gold +0.566 (0.0001) | TLT +0.374 (0.0001); HYG +0.364 (0.0003); gold +0.702 (0.0001) |
| E1, common placebos (`h2_development_*`): breaks classified; SPY-only share, breaks vs placebos | 56; 55.4% vs 60.3% | 43; 76.7% vs 61.1% |
| A30: share of windows where SPY's S comes first for every available asset | 36.8% (394 windows with an asset) | 39.9% (343) |
| A30: breaks with an exceedance, vs placebo chance reference, TLT / HYG / gold | 60.3% vs 61.9% / 20.4% vs 23.4% / 64.9% vs 70.7% | 61.7% vs 65.9% / 16.8% vs 20.9% / 60.8% vs 70.7% |
| Fed split, Fed breaks: H3 TLT gamma (n) | -0.229 (39) | -0.431 (32) |
| Detector dependence, H3/H4 smallest p | Student-t H3 HYG 0.183; HSMM H4b 0.084 | same |

Sources: `section6/results/a34_development_{gaussian_hmm,hsmm}.json`; `s6_development_*` keys `a30_lead_lag`, `fed_split` and `detector_dependence`; `h2_development_*` key `E1`. The A32/A34 exploratory statistic is uncorrected and labelled post-diagnosis or specified after seeing results (A33 rule 4, A34).

---

## 8. Results: evaluation (Gaussian HMM; LEGACY 2019-01-02..2022-03-04 and RAW 2025-01-02..2026-10-12 combined)

Run: `s6_eval.py run`, Section 6 files written 2026-11-13 00:48:41-00:49:46Z, no alert. 218 breaks (LEGACY 171, RAW 47).

### 8a. H2 primary (+30; Holm of 4)

| Asset | Breaks used | Skipped | M | Placebo mean | p | Holm |
|---|---|---|---|---|---|---|
| TLT | 208 | 10 | -1.85e-5 | -1.99e-5 | 0.986 | 1.0 |
| HYG | 191 | 27 | +1.02e-4 | +4.32e-5 | 0.550 | 1.0 |
| Gold | 206 | 12 | -2.65e-4 | +1.58e-5 | 0.053 | 0.213 |
| USD | 193 | 25 | +9.85e-6 | +5.46e-6 | 0.930 | 1.0 |

- **By era (secondary).** LEGACY p: TLT 0.749, HYG 0.491, gold 0.059, USD 0.285. RAW p: TLT 0.391, HYG 0.868, gold 0.397, USD 0.038 (Holm 0.150). No rejection.
- **H2 secondary family (39 tests).** Two BH survivors: **HYG pre-30** (raw p 0.0002, BH 0.0078) and **USD pre-30** (raw p 0.0008, BH 0.0156). Pre-30 is the window (T - 30, T].
- **Detector dependence, H2 p by detector** (TLT / HYG / gold / USD):
  - Student-t HMM: 0.525 / 0.835 / 0.184 / 0.672;
  - HSMM: 0.604 / 0.747 / 0.091 / 0.263;
  - BOCPD: 0.896 / 0.522 / 0.186 / 0.418.
  - Holm verdict agreement: no rejection for any detector.
- **E1** (184 breaks classified; 7 skipped past the close, 27 with TLT or HYG not evaluable), breaks vs placebo shares:

  | Category | Breaks | Placebos |
  |---|---|---|
  | Flight to safety | 0.5% | 1.2% |
  | Credit stress | 5.4% | 5.6% |
  | Dollar-driven | 6.0% | 5.4% |
  | SPY-only | 51.1% | 62.0% |
  | Other | 37.0% | 25.6% |

- Source: `section6/results/h2_evaluation_gaussian_hmm.json`.

### 8b. H3/H4 primary (Holm of 6)

| Test | n | gamma or gain | p | Holm |
|---|---|---|---|---|
| H3 TLT | 208 (4,220 placebos) | -0.053 | 0.872 | 1.0 |
| H3 HYG | 184 (3,927) | -0.095 | 0.974 | 1.0 |
| H3 gold | 206 (4,077) | -0.106 | 0.987 | 1.0 |
| H3 USD | 157 (2,885) | -0.212 | 1.000 | 1.0 |
| H4a | 294 (80 confirm) | -0.012 | 0.857 | 1.0 |
| H4b | 218 (69 real) | -0.028 | 0.853 | 1.0 |

- **Out-of-fold AUC, with C / SPY only:** H4a 0.635 / 0.648; H4b 0.503 / 0.531.
- **Valid share:** 1.0 for both H4 tests.
- No rejection.
- Source: `section6/results/s6_evaluation_gaussian_hmm.json`.

### 8c. Evaluation secondary and descriptive

**H3/H4 secondary family:** 76 tests; no BH survivor. Smallest raw p values:
- detector dependence, BOCPD H3 gold: gamma +0.134, n 155, p 0.018, BH 0.795;
- Fed-split H4b: gain +0.293, n 27, p 0.021, BH 0.795.

**Detector dependence, H3/H4 p** (TLT / gold / H4a / H4b):
- Student-t HMM: 0.942 / 0.998 / 0.270 / 0.380;
- HSMM: 0.992 / 0.749 / 0.057 / 0.839;
- BOCPD: 0.408 / 0.018 / not evaluable (n 0) / 0.969.

**Fed split, Fed breaks:** H3 TLT -0.218 (n 27); H3 gold +0.009 (25); H4a n 11, low valid share 0.326; H4b +0.293 (27), p 0.021.

**Other H3/H4 secondaries:**
- LEGACY clock offsets ±1: H3 gammas within 0.007 of the primary; H4b p 0.947 (-1) and 0.482 (+1).
- Anchor T0 at S: H4b not evaluable (0 valid resamples); H3 gammas -0.007 to -0.169.
- H3 rest-of-day: TLT -0.066 (0.868), HYG +0.064 (0.116), gold -0.054 (0.822), USD -0.050 (0.754).
- H3 prior-hour control over (S - 60, S] (A29 3c, descriptive): TLT -0.026, HYG -0.040, gold -0.079, USD -0.193.

**A34:**
- H3 sensitivity with per-asset pools, gamma: TLT -0.043, HYG -0.085, gold -0.129, USD -0.239; all BH 1.0.
- E1 per-asset: 187 breaks classified.

**A30:**
- 201 windows (17 skipped). The share where SPY's S comes first for every available asset is 7.0%.
- Breaks with an exceedance vs the placebo chance reference: TLT 87.4% vs 81.7%; HYG 83.4% vs 79.7%; gold 89.3% vs 77.8%; USD 86.3% vs 84.9%.

**Not evaluable or near-empty:**
- Anchor-at-S H4b (0 valid resamples);
- BOCPD H4a (n 0);
- Fed H4a (valid share 0.326);
- H3 stressed-to-calm HYG (n 1);
- H2 stressed-to-calm HYG (n 4).

**Sources:** `section6/results/s6_evaluation_gaussian_hmm.json`, `h2_evaluation_gaussian_hmm.json`, `a34_evaluation_gaussian_hmm.json`; `POST_EVAL_AUDIT.md`; the corrected report in `reply_latest.md`.

---

## 9. Disclosures (`SECTION6_DISCLOSED_LIMITATIONS.md`)

- **S6-D1. The A31 rule 3 control is not specific to the alarm filter.**
  - The synthetic check (`section6/results/synth_validation_a31r.json`) shows the control calibrated under no effect: flag rates 4.0-7.0%.
  - With H4 planted it flags 12.5-22.5% of replicates, although the generator has no filter bias.
  - The Gaussian HMM TLT flag (delta +0.030) has the size and sign of the planted-H4 scenario (+0.026). It is not evidence of a filter bias of 0.03.
- **S6-D2. What the A26 label guards do not cover.**
  - The 5.13 writer stays callable outside the scanned folders.
  - Direct reads of the panel files bypass the label guards.
  - `s6_coverage.py` does not use `write_once`.
  - The guards are module attributes.
  - Tables, figures and sentences are labelled by hand.
  - Unserialisable results fail after the marker.
- **S6-D3. Records that predate the A35 and A32 corrections.**
  - The development H4 p values in the stored files use the A29 1d convention; the A35 table gives the corrected values, and no verdict differs.
  - The power check was not rerun under A35.
  - Files written 2026-11-10 21:44Z-23:31Z record `AMENDMENT_A32.md` as `7bc90d60...` (date-stamp-only difference from the adopted `d222539c...`).
- **S6-D4. "Calm-to-stressed" follows A28 1b, not protocol 5.5.**
  - 280 of 600 Gaussian HMM development breaks start in state 0.
  - Protocol 5.5's direction rule agrees on 85.9% of the 1,135 defined breaks (975 calm-to-stressed, 160 stressed-to-calm, 14 undefined of 1,149; `section5/results/direction_rule_agreement.json`).
  - No Section 6 result is recomputed under 5.5.

**Related Section 5 disclosures** (`SECTION5_DISCLOSED_LIMITATIONS.md`): D6, a July-September 2026 daily-data HMM pilot (SPY, TLT, HYG, GLD, DXY; 2007-05-01..2025-12-31) gave prior exposure to cross-asset behaviour in both evaluation periods.
