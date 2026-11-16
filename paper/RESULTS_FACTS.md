# Results facts for the paper

**Status.** Compiled 2026-11-16, read-only, from the written result files cited in each section. No result was recomputed. Two kinds of number here were computed for the figures only: the development intervals in Figure 1 and the evaluation Wilson intervals in Figure 2. Both are marked "figure-only" (§12).

**Conventions.**
- **Families.** Gaussian HMM (G), Student-t HMM (T), HSMM (H). BOCPD (B) is secondary.
- **Effects.**
  - H1(a): pAUC of the feature model minus pAUC of the returns-only baseline, on synthetic splices of stable test days.
  - H1(b): mean QLIKE of the baseline minus mean QLIKE of the feature model (next 60 min).
  - H1(c): FOMC hit rate of the feature model minus that of the baseline, in [release, release + 60 min].
- **Development p-values.** p = 0.0001 is the floor of the block bootstrap with 9,999 resamples. "p_IU" is the intersection-union p, the larger of the H1(a) and H1(b) p-values. Holm is applied over G, T and H (m = 3); BOCPD is outside Holm.
- **Development folds.**
  - 34 folds: LEGACY 0–29 and RAW 0–3.
  - 8 are contaminated and excluded from the confirmatory tests: LEGACY 23, 24, 27, 28, 29 and RAW 1, 2, 3.
  - That leaves 26 confirmatory folds (25 LEGACY, 1 RAW). H1(a) is evaluable in 22 of them; the rest lack enough stable test days.
- **Evaluation numbers** are labelled "adaptive/exploratory (previously exposed period)", `confirmatory: false` (A26). They have 95% day-cluster percentile bootstrap intervals (2,000 resamples, seed 513) and no p-values (A36 5g).
- **Code version** for every Section 5 result: `a0323ed24d68e896`. Freeze `section5/results/section5_freeze.json`, SHA-256 `846c1aaa…`.

---

## 1. H1, development (MR2 main run; protocol 5.8–5.11 under A20)

Source: `section5/results/main_run_2/run_summary.json` (keys `family_results`, `holm`, `final_setups`, `median_validation_qlike`).

### 1a. Confirmatory folds

| Family | H1(a) folds | H1(a) mean | p (block bootstrap) | Sign consistency | H1(b) folds | H1(b) mean | p | Sign consistency | p_IU | Holm p | Holm |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Gaussian HMM | 22 | +0.1049 | 0.0001 | 0.86 | 26 | +0.0256 | 0.0007 | 0.85 | 0.0007 | **0.0014** | reject |
| Student-t HMM | 22 | +0.0682 | 0.0001 | 0.64 | 26 | +0.0050 | 0.1034 | 0.42 | 0.1034 | 0.1034 | no |
| HSMM | 22 | +0.1107 | 0.0001 | 0.95 | 26 | +0.0342 | 0.0001 | 0.92 | 0.0001 | **0.0003** | reject |
| BOCPD (secondary) | 22 | 0.0000 | 1.0 | 0.00 | 26 | 0.0000 | 1.0 | 0.00 | 1.0 | – | – |

**All-folds sensitivity (30 H1(a) / 34 H1(b) folds).**

| Family | H1(a) mean | H1(b) mean | p_IU | Holm p | Holm |
|---|---|---|---|---|---|
| Gaussian HMM | +0.1112 | +0.0292 | 0.0001 | 0.0003 | reject |
| Student-t HMM | +0.0759 | +0.0089 | 0.0485 | 0.0485 | reject |
| HSMM | +0.1178 | +0.0393 | 0.0001 | 0.0003 | reject |
| BOCPD | +0.0003 | +0.0001 | 0.0448 | – | – |

**Freeze.** The freeze carries the confirmatory verdicts (`h1_verdicts`):
- G and H pass; T does not.
- H2 primary detector: Gaussian HMM (`h2_primary_detector`).

**Era final setups (5.13).** These are identical in LEGACY and RAW.

| Family | Feature | K | Baseline K |
|---|---|---|---|
| G | `rv10_partial90__sadj` | 4 | 4 |
| T | `rv10_partial90__sadj` | 4 | 4 |
| H | `rv10_partial90__sadj` | 3 | 3 |
| B | none | λ = 12 | λ = 12 |

**Selection frequency of `rv10_partial90__sadj`** (folds selecting it):

| Family | LEGACY (of 30) | RAW (of 4) |
|---|---|---|
| G | 23 | 3 |
| T | 10 | 2 |
| H | 27 | 3 |

T selected `intrabar_range_log__sadj` in 8 LEGACY folds.

**Median validation QLIKE:** G 0.211, T 0.206, H 0.217, B 0.331.

### 1b. QLIKE gain as % of the baseline, development test segments

Source: `section5/results/mr2/a17/a17_results.json`, key `qlike_test_pct`.

| Family | Confirmatory median [IQR] | Pooled | Range |
|---|---|---|---|
| G | 5.85% [3.06, 8.64] | 10.23% | −2.31 to 30.99 |
| T | 0.00% [0.00, 3.20] | 2.19% | |
| H | 10.47% [7.45, 14.50] | 13.06% | |
| B | 0 | 0 | |

### 1c. H1(c), FOMC releases, development (A17-style; secondary; outside Holm)

- 98 events (LEGACY 94, RAW 4).
- Thresholds: 0.2 alarms per validation session.
- Source: `section5/results/mr2/a17/a17_results.json`, key `h1c`.

| Family | Hit rate, feature (Wilson 95%) | Hit rate, baseline (Wilson 95%) | Diff | Feature only / baseline only | p (two-sided paired) |
|---|---|---|---|---|---|
| G | 0.622 (0.524–0.712) | 0.378 (0.288–0.476) | +0.245 | 31 / 7 | 0.0001 |
| T | 0.469 (0.374–0.567) | 0.255 (0.179–0.350) | +0.214 | 24 / 3 | <0.0001 |
| H | 0.622 (0.524–0.712) | 0.357 (0.269–0.456) | +0.265 | 32 / 6 | <0.0001 |
| B | 0.398 (0.307–0.497) | 0.398 | 0.000 | 0 / 0 | 1.0 |

Reference alarm rates (feature, non-FOMC sessions, same window): G 0.044, T 0.035, H 0.035, B 0.073.

**Post hoc, R=1-net H1(a)** (same file, key `posthoc_r1_net_h1a`; confirmatory mean): G +0.1098, T +0.0693, H +0.1216. Mean gap to the main H1(a): −0.005, −0.001 and −0.011.

---

## 2. H1, evaluation (5.13; frozen models; nothing fitted on the evaluation path)

Sources: `section5/results/evaluation_LEGACY.json` and `evaluation_RAW.json`, key `families`.
- LEGACY: 800 sessions, 2019-01-02..2022-03-04; 79 stable days.
- RAW: 445 sessions, 2025-01-02..2026-10-12; 115 stable days.
- Splices: 400 null and 960 break per era.

### 2a. LEGACY evaluation

| Family | H1(a) [95% CI] | H1(b) [95% CI] | H1(b) % of baseline | H1(c) [95% CI] | FOMC hits, feature / baseline (24 events) | Alarms per session, feature / baseline |
|---|---|---|---|---|---|---|
| G | +0.084 [0.053, 0.116] | +0.049 [0.036, 0.065] | 12.6% | +0.42 [0.21, 0.62] | 0.71 / 0.29 | 0.214 / 0.141 |
| T | +0.087 [0.058, 0.117] | +0.031 [0.021, 0.043] | 8.4% | +0.42 [0.17, 0.62] | 0.71 / 0.29 | 0.215 / 0.168 |
| H | +0.049 [0.027, 0.075] | +0.101 [0.085, 0.120] | 21.5% | +0.37 [0.12, 0.58] | 0.67 / 0.29 | 0.159 / 0.101 |
| B | 0 | 0 | 0 | 0 | 0.33 / 0.33 | 0.186 / 0.186 |

Note: HSMM H1(b) LEGACY is +0.101, not 0.102 (audit flag F1, `POST_EVAL_AUDIT.md`).

### 2b. RAW evaluation

| Family | H1(a) [95% CI] | H1(b) [95% CI] | H1(b) % of baseline | H1(c) [95% CI] | FOMC hits, feature / baseline (14 events) | Alarms per session, feature / baseline |
|---|---|---|---|---|---|---|
| G | +0.194 [0.152, 0.241] | +0.118 [0.083, 0.159] | 27.1% | +0.14 [0.00, 0.36] | 0.71 / 0.57 | 0.137 / 0.276 |
| T | +0.204 [0.166, 0.242] | +0.041 [0.029, 0.056] | 11.6% | −0.29 [−0.57, 0.00] | 0.50 / 0.79 | 0.117 / 0.310 |
| H | +0.186 [0.152, 0.219] | +0.091 [0.068, 0.117] | 20.9% | +0.14 [−0.21, 0.50] | 0.79 / 0.64 | 0.200 / 0.306 |
| B | 0 | 0 | 0 | 0 | 0.29 / 0.29 | 0.187 / 0.187 |

**Frozen thresholds** (feature / baseline, log-odds; `thresholds`):

| Era | G | T | H | B |
|---|---|---|---|---|
| LEGACY | 16.427 / 4.491 | 11.813 / 4.591 | 15.743 / 7.561 | 51.301 / 51.301 |
| RAW | 16.982 / 3.278 | 14.163 / 4.958 | 11.585 / 3.987 | 54.078 / 54.078 |

- Every frozen feature threshold was reproduced on recomputation (`frozen_threshold_reproduced`).
- The calibration rate was 0.190 alarms per session.

**Confirmed breaks** (`n_breaks_by_family_kind`):

| Era | G | T | H | B |
|---|---|---|---|---|
| LEGACY | 171 | 172 | 127 | 149 |
| RAW | 61 | 52 | 89 | 83 |

Confirmation lag (T_c − T_d), Gaussian HMM, LEGACY: median 10 min (`posthoc_absolute_detection.json`, key `evaluation`).

**Independent reproduction.** MarketLens reproduces all 344 Gaussian HMM runs of `evaluation_RAW.json` exactly (ledger rows of 2026-11-14; `README.md`).

---

## 3. Robustness, development (A22–A27; secondary; no verdict changed unless stated)

### 3a. A22 rule 3e: seeds 1–3 for starts and splices (seed 0 = MR2)

Source: `section5/results/a22/seeds.json`, key `spread`.

| Family | H1(a) range across seeds | H1(b) range | Holm rejections (of 4 seeds) |
|---|---|---|---|
| G | 0.1035–0.1063 | 0.0221–0.0256 | 4 |
| T | 0.0676–0.0713 | 0.0050–0.0053 | 0 |
| H | 0.1097–0.1144 | 0.0334–0.0342 | 4 |

Gaussian HMM Holm p by seed: 0.0014, 0.0080, 0.0026, 0.0026. Student-t Holm p: 0.103, 0.096, 0.095, 0.105.

### 3b. A22 rule 3c: threshold target 0.15 / 0.20 / 0.25 alarms per session (H1(c) at 98 events)

Source: `section5/results/a22/thresholds.json`.

| Target | G feature / baseline (diff) | T | H | B |
|---|---|---|---|---|
| 0.15 | 0.612 / 0.337 (+0.276) | 0.439 / 0.214 (+0.224) | 0.571 / 0.276 (+0.296) | 0.286 / 0.286 |
| 0.20 | 0.622 / 0.378 (+0.245) | 0.469 / 0.255 (+0.214) | 0.622 / 0.357 (+0.265) | 0.398 / 0.398 |
| 0.25 | 0.673 / 0.408 (+0.265) | 0.500 / 0.276 (+0.224) | 0.673 / 0.408 (+0.265) | 0.480 / 0.480 |

At 0.20 the run reproduces the MR2 thresholds, alarms and H1(c) exactly.

### 3c. A22 rules 3a/3b: era split and flagged Student-t fits

Source: `section5/results/a22/era_flagged.json`.

**LEGACY confirmatory folds (21 H1(a) / 25 H1(b)).**

| Family | H1(a) | H1(b) | Holm p | Holm |
|---|---|---|---|---|
| G | +0.1054 | +0.0258 | 0.0028 | reject |
| T | +0.0691 | +0.0048 | 0.1505 | no |
| H | +0.1129 | +0.0350 | 0.0003 | reject |

**RAW.**
- The single confirmatory fold is not testable: G +0.0933 / +0.0214, T +0.0485 / +0.0104, H +0.0648 / +0.0144.
- All 4 RAW folds:

  | Family | H1(a) | H1(b) | p_IU |
  |---|---|---|---|
  | G | +0.1459 | +0.0401 | 0.0001 |
  | T | +0.0923 | +0.0087 | 0.0001 |
  | H | +0.1280 | +0.0343 | 0.0001 |

**Flagged Student-t fits:** 0, so the "excluding flagged" result is identical to MR2.

### 3d. A22 rule 3f: RAW 80-column sensitivity pool (69 columns under A20)

Source: `section5/results/a22/raw80.json`.

All 4 RAW folds:

| Family | H1(a) | H1(b) | p_IU |
|---|---|---|---|
| G | +0.1496 | +0.0416 | 0.0001 |
| T | +0.1147 | +0.0089 | 0.0001 |
| H | +0.1172 | +0.0361 | 0.0001 |
| B | +0.0107 | +0.0005 | 0.0001 |

All-folds Holm: G, T and H reject. On the confirmatory fold (RAW 0) the pool gives the same setup as MR2 (Gaussian HMM `intrabar_range_log__sadj`, H1(a) +0.0933).

### 3e. A22 rule 3g: decision grid 1 / 5 / 15 min on the era final setups (confirmatory folds)

Source: `section5/results/a22/grids.json` and `grids_NOTE.md`.

| Grid | G H1(a) / H1(b) | T H1(a) / H1(b) | H H1(a) / H1(b) | Holm |
|---|---|---|---|---|
| 5 min (reference) | +0.1379 / +0.0334 | +0.1314 / +0.0055 | +0.1208 / +0.0351 | G, H reject; T p 0.068 |
| 15 min | +0.1201 / +0.0556 | +0.1106 / +0.0511 | +0.1178 / +0.0585 | G, T, H reject |
| 1 min | −0.0550 / +0.0320 (p_IU 1.0) | +0.0166 / −0.0072 (p_IU 0.80) | not run (projected 47.7 h) | none |

**Reading of the 1-min result.** The note in `grids_NOTE.md` says the 1-min Gaussian H1(a) of −0.055 is a property of the 5-min-tuned rule at 1 min, not evidence that the feature carries no information at 1 min. On the 1-min grid there are 5× as many updates per session, and confirmation takes 2 min.

**Post hoc absolute pAUC, 1 vs 5 min** (`section5/results/posthoc_grid_pauc/posthoc_grid_pauc.json`):

| Grid | Family | Feature | Baseline |
|---|---|---|---|
| 1 min | G | 0.082 | 0.137 |
| 1 min | T | 0.175 | 0.158 |
| 5 min | G | 0.248 | 0.110 |
| 5 min | T | 0.242 | 0.111 |

### 3f. A22 rule 3d → A25: LEGACY decision delay +5 / +10 min, scored by data time used

Source: `section5/results/a25/delay_datatime.json`. It supersedes `a22/delay.json`; delay 0 reproduces MR2 exactly.

| Delay | G H1(a) | T H1(a) | H H1(a) | H1(b) | Holm | H1(c) G diff | H1(c) H diff |
|---|---|---|---|---|---|---|---|
| 0 | +0.1049 | +0.0682 | +0.1107 | as MR2 | G, H reject | +0.245 | +0.265 |
| +5 min | +0.1068 | +0.0706 | +0.1122 | unchanged | G, H reject | +0.276 | +0.265 |
| +10 min | +0.1077 | +0.0722 | +0.1129 | unchanged | G, H reject | +0.286 | +0.276 |

**Post hoc absolute pAUC at the delays** (`section5/results/a25/abs_pauc.json`; 21 LEGACY confirmatory folds), feature / baseline:

| Delay | G | T | H |
|---|---|---|---|
| 0 | 0.219 / 0.114 | 0.183 / 0.114 | 0.237 / 0.124 |
| +10 | 0.204 / 0.095 | 0.166 / 0.093 | 0.219 / 0.104 |

### 3g. A24: LEGACY clock −1 / 0 / +1 min (H1(c) only)

Source: `section5/results/a24/clock.json`. H1(a), H1(b), D7, D8 and the A7 thresholds are invariant to a common offset.

At target 0.20:

| Offset | G feature / baseline | T feature / baseline | H feature / baseline |
|---|---|---|---|
| −1 min | 0.622 / 0.378 | 0.469 / 0.255 | 0.622 / 0.357 |
| 0 | 0.622 / 0.378 | 0.469 / 0.255 | 0.622 / 0.357 |
| +1 min | 0.622 / 0.347 | 0.469 / 0.245 | 0.622 / 0.357 |

Every difference stays positive at targets 0.15, 0.20 and 0.25 (p ≤ 0.0001). Offset 0 reproduces MR2.

### 3h. A27: confirmation count r = 1, 2, 3 (main), 4

Source: `section5/results/a27/confirm_count.json`. H1(b) does not depend on r.

| r | G H1(a) | T H1(a) | H H1(a) | Holm rejects | Detection-to-confirmation (G) | Mean pAUC G feature / baseline |
|---|---|---|---|---|---|---|
| 1 | −0.0002 | +0.0226 | +0.0368 | none (H p 0.207) | 0 min | 0.122 / 0.122 |
| 2 | +0.0365 | +0.0470 | +0.0751 | G, H | 5 min | 0.166 / 0.129 |
| 3 (main) | +0.1049 | +0.0682 | +0.1107 | G, H | 10 min | 0.220 / 0.116 |
| 4 | +0.1139 | +0.0709 | +0.1185 | G, H | 15 min | 0.218 / 0.104 |

At r = 1, the Gaussian HMM feature threshold sits at the bisection upper bound (median 30.0; `s5_a7.py:13`) and 16 folds were flagged. r = 3 reproduces MR2 exactly.

### 3i. A22 rule 4: 5.11 power (observed fold SD; MDE at power ≈ 0.84, first Holm step α = 0.0167)

Source: `section5/results/a22/power.json`.

| Family | H1(a) MDE | Observed / MDE | H1(b) MDE | Observed / MDE |
|---|---|---|---|---|
| G | 0.039 | 2.66 | 0.025 | 1.01 |
| T | 0.036 | 1.91 | 0.013 | 0.39 |
| H | 0.034 | 3.24 | 0.022 | 1.54 |

D7 MDE (hit-rate difference at power ≈ 0.81, 258 days): 0.12 for G, T and H.

---

## 4. Diagnostics (development; descriptive or secondary)

### 4a. D7 (A19.3, A21 rule 1): variance-neutral planted changes, MR2 fits

Source: `section5/results/mr2/d7_a21/d7_results.json`.

**Setup.** 258 days. LEGACY days with an undefined variance ratio (zero slot median) are excluded under A21. Their cause is in `section5/results/d7_nan_diag/d7_nan_diag.json`: 47 days.

**Gates.** All passed: positive control (ii), null sanity (iii), days (iv).

**Hit-rate change** (planted − null), feature model, 95% CI. "Responds" uses the protocol rule.

| Type | G | T | H | B |
|---|---|---|---|---|
| Variance ×3 (positive control) | +0.337 [0.287, 0.386] responds | +0.237 responds | +0.316 responds | +0.085 |
| Variance ×5.29 (positive control) | +0.534 responds | +0.462 responds | +0.581 responds | +0.135 responds |
| Liquidity, volume ×2 | +0.003 [−0.003, 0.010] | −0.002 | +0.004 | 0 |
| Liquidity, volume ×0.5 | +0.004 | +0.010 | +0.009 | 0 |
| Trend t4 | +0.020 | +0.022 | +0.007 | +0.107 responds |
| Momentum ρ 0.4 | +0.030 | +0.030 | +0.013 | +0.045 |
| Jumps 2 × 5 SD | +0.242 responds | +0.112 responds | +0.254 responds | +0.047 |
| Jumps 2 × 4 SD | +0.052 | +0.032 | +0.082 | +0.051 |

**Feature minus baseline** at variance ×3: G +0.178, T +0.119, H +0.191 (all CIs exclude 0).

**Verdicts** (key `verdict`):
- Liquidity, trend and momentum: "missed" by every feature model.
- Liquidity also "occurs" in D8, which triggered Step 2.

**Earlier diagnosis on RAW 3** (`section5/results/d7_diag_raw3.json`; ledger row 2026-11-06). With raw (unadjusted) features, the feature models' states track time of day:
- Cramér's V: 0.20 / 0.18 / 0.23 vs baselines 0.05 / 0.03 / 0.06.
- Positive control at ×3: +0.12 / +0.05 / +0.08 with `__sadj` features vs −0.10 / 0.00 / −0.13 with raw features.

The ledger row reads this as support for "raw seasonal features make the 'old state' a time-of-day state". A20 then restricted the scale inputs to `__sadj` columns.

### 4b. D8 (A19 rule 1): descriptive census of large non-variance changes in variance-stable windows

Source: `section5/results/d8/d8_results.json`.

**Sample.** 38,308 windows of 60 min in 697 validation sessions. Variance-stable share 0.334 (variance ratio in [0.8, 1.25]).

**Large-change shares**, "large" and "large given variance-stable" (n large in parentheses):

| Type | Pooled | LEGACY | RAW |
|---|---|---|---|
| Trend | 0.0054 / 0.0051 (205) | 0.0046 / 0.0044 | 0.0068 / 0.0064 |
| Momentum | 0.0123 / 0.0109 (470) | 0.0131 / 0.0108 | 0.0105 / 0.0110 |
| Liquidity | 0.0642 / 0.0369 (2,460) | 0.0671 / 0.0301 | 0.0584 / 0.0500 |
| Jumps | 0.0728 / 0.0381 (2,787) | 0.0632 / 0.0354 | 0.0921 / 0.0433 |

"Occurs" means a share of at least 0.02 given variance-stable. Liquidity and jumps occur; trend and momentum do not.

**D8b sensitivity** (`d8b_results.json`; does not change D8):
- The primary run is reproduced.
- Strict thresholds (S1): liquidity and jumps no longer occur.
- 30-min windows: jumps no longer occur.
- 120-min windows and LEGACY completeness at 90%: no change.

**D8c overlap breakdown** (`d8c_results.json`; pooled). 10,055 of 38,308 windows (26.2%) have at least one large change. Of those:

| Pattern | Share |
|---|---|
| Volatility only | 52.3% |
| Liquidity only | 12.1% |
| Jumps only | 13.4% |
| Combined | 22.2% |
| — volatility + liquidity | 7.9% |
| — volatility + jumps | 9.8% |
| — liquidity + jumps | 1.3% |
| — all three | 3.2% |

### 4c. Step 2: liquidity detection (A21 rule 3)

Source: `section5/results/step2_liquidity/step2_results.json`.

**Setup.** The objective is QLIKE on the dollar-volume target; A20 pool; 4 families.

| Family | Confirmatory mean gain (26 folds) | p | Sign consistency | QLIKE % median (pooled) | Final feature (LEGACY, RAW) |
|---|---|---|---|---|---|
| G | +0.0078 | 0.0001 | 0.88 | 5.92% (8.33%) | `relative_volume20`, K 4 |
| T | +0.0050 | 0.0001 | 0.77 | 3.97% (5.51%) | `relative_volume20`, K 4 / 3 |
| H | +0.0086 | 0.0001 | 0.92 | 9.13% (8.81%) | `relative_volume20`, K 3 |
| B | 0 | 1.0 | – | 0 | none |

**BH.** G, T and H reject (q 0.00013).

**D7 on the Step 2 models:**
- Volume ×2 does not "respond" (G +0.058 [0.031, 0.087], T +0.061, H +0.081), although every CI excludes 0.
- The variance positive control at ×3 responds: G +0.201, T +0.136, H +0.157.

### 4d. A18 rerun on A20 inputs: selection by one-step-ahead predictive log-likelihood

Source: `section5/results/mr2/a18/a18_results.json`.

**H1, confirmatory folds:**

| Family | H1(a) | H1(b) | p_IU | Holm p | Holm |
|---|---|---|---|---|---|
| G | +0.0267 | +0.0061 | 0.128 | 0.384 | no rejection |
| T | −0.0175 | −0.0156 | 0.885 | 0.885 | no rejection |
| H | +0.0127 | +0.0057 | 0.136 | 0.384 | no rejection |

**Selection.** Mean features per fold: G 0.12, T 0.35, H 0.06. Folds with no feature: G 30/34, T 24/34, H 32/34.

**Non-volatility share** (all folds; MR2 value in parentheses): G 0.00 (0.09), T 0.24 (0.06), H 0.00 (0.12). T selected `momentum5_endpoint` in 8 folds.

### 4e. A23: combined volatility + volume model (EXPLORATORY)

Source: `section5/results/a23/a23_results.json`.

**Setup.** `rv10_partial90__sadj` + `relative_volume20` forced in.

**H1, confirmatory folds:**

| Family | H1(a) | H1(b) | p_IU | Holm |
|---|---|---|---|---|
| G | +0.1266 | +0.0284 | 0.0004 | reject (Holm p 0.0008) |
| T | +0.1138 | +0.0062 | 0.0415 | reject |
| H | +0.0995 | +0.0354 | 0.0001 | reject |
| B | +0.0613 | −0.0004 | 0.918 | – |

**H1(c)** (98 events), feature / baseline:

| Family | Feature | Baseline | Diff |
|---|---|---|---|
| G | 0.673 | 0.378 | +0.296 |
| T | 0.694 | 0.255 | +0.439 |
| H | 0.694 | 0.357 | +0.337 |
| B | 0.449 | 0.398 | +0.051, p 0.47 |

**Liquidity QLIKE**, median confirmatory gain (positive folds of 26):

| Family | Median gain | Positive folds |
|---|---|---|
| G | +0.0053 | 24 |
| T | +0.0028 | 23 |
| H | +0.0084 | 25 |
| B | −0.0002 | 8 |

**D7 volume ×2:** G +0.018 [0.005, 0.034], T +0.014, H +0.016, B +0.051. None "responds".

### 4f. 5.5 direction rule vs A28 1b

Source: `section5/results/direction_rule_agreement.json`.

- 1,149 confirmed development breaks: 975 calm-to-stressed and 160 stressed-to-calm under 5.5, 14 undefined.
- Agreement on defined breaks: 85.9% (Gaussian HMM 84.0%, HSMM 88.0%).
- Disclosure S6-D4.

---

## 5. Cross-asset H2–H4, development

Sources:
- `section6/results/h2_development_{gaussian_hmm,hsmm}.json`;
- `s6_development_{gaussian_hmm,hsmm}.json`;
- `posthoc/h3_ci_a29_3b.json`;
- `a34_development_*.json`;
- `a35_null_control_*.json`.

Full definitions are in `SECTION7_FACTS.md` §2–6.

**Breaks** (confirmed calm-to-stressed, LEGACY / RAW):
- Gaussian HMM: 586 / 14 (600).
- HSMM: 536 / 13 (549).

### 5a. H2: same-window return over (T, T+30]; two-sided; Holm m = 4

| Asset | G: n | G: p | G: Holm | H: n | H: p | H: Holm |
|---|---|---|---|---|---|---|
| TLT | 397 | 0.904 | 1.0 | 335 | 0.085 | 0.272 |
| HYG | 280 | 0.952 | 1.0 | 242 | 0.461 | 0.461 |
| Gold | 418 | 0.037 | 0.148 | 364 | 0.068 | 0.272 |
| USD | 13 | 0.640 | 1.0 | 12 | 0.082 | 0.272 |

- No rejection.
- Secondary (31 tests): TLT pre-30 is the only BH survivor for each detector (raw p 0.0002, BH 0.0062).

### 5b. H3 (next-day log RV; one-sided H0 γ ≤ 0) and H4 (AUC gain; one-sided); Holm m = 6

| Test | G: n | G: γ or gain | G: p | H: n | H: γ or gain | H: p |
|---|---|---|---|---|---|---|
| H3 TLT | 402 | −0.164 (95% −0.220, −0.107) | 1.000 | 339 | −0.139 (−0.206, −0.070) | 1.000 |
| H3 HYG | 243 | −0.071 | 0.975 | 205 | −0.043 | 0.844 |
| H3 gold | 420 | −0.185 (−0.242, −0.129) | 1.000 | 373 | −0.156 (−0.223, −0.089) | 1.000 |
| H3 USD | 9 | −0.282 | 0.733 | 11 | −0.213 | 0.755 |
| H4a | 1,853 (280 confirm) | +0.016 | 0.284 (A35: 0.294) | 2,480 (365) | +0.013 | 0.189 (A35: 0.190) |
| H4b | 597 (203 real) | −0.009 | 0.577 (A35: 0.652) | 545 (198) | +0.050 | 0.084 (A35: 0.087) |

- All Holm p ≥ 0.506; no rejection.
- **95% intervals.** They are post hoc (A29 3b): two-sided basic week-block bootstrap, 9,999 resamples. They were computed for TLT and gold only. Both lie wholly below 0, which is read as a "transient cross-asset response", not a calming effect.
- **Out-of-fold AUC, with C / SPY only:** H4a G 0.602 / 0.586, H 0.624 / 0.611; H4b G 0.515 / 0.524, H 0.552 / 0.502.
- **Secondary.** No BH survivor. Smallest raw p: G 0.084 (detector dependence, HSMM H4b); H 0.0092 (LEGACY offset +1, H4b).
- **Power** (first Holm step):
  - H3 γ MDE: 0.15 SD.
  - H4a MDE: G 0.067, H 0.035; H4b MDE not reached.
  - H2 MDE: 0.15 SD of the 30-min return.
  - Sources: `power_*.json`, `h2_50_power_*.json`.

### 5c. Development secondary and descriptive

| Item | G | H |
|---|---|---|
| A34 H3 sensitivity, γ TLT / HYG / gold / USD (all BH 1.0) | −0.112 / −0.069 / −0.170 / −0.033 | −0.119 / −0.072 / −0.152 / −0.155 |
| A32 exploratory statistic, G (raw p) | TLT +0.293 (0.0001); HYG +0.240 (0.0012); gold +0.566 (0.0001) | TLT +0.374; HYG +0.364; gold +0.702 |
| E1: breaks classified; SPY-only share, breaks vs placebos | 56; 55.4% vs 60.3% | 43; 76.7% vs 61.1% |
| A30: SPY's S first for every available asset | 36.8% of 394 windows | 39.9% of 343 |
| A30: breaks with an exceedance vs placebo chance, TLT / HYG / gold | 60.3 vs 61.9 / 20.4 vs 23.4 / 64.9 vs 70.7% | 61.7 vs 65.9 / 16.8 vs 20.9 / 60.8 vs 70.7% |
| Fed breaks, H3 TLT γ (n) | −0.229 (39) | −0.431 (32) |

**2007+ sensitivity** (key `sens_2007`). The H3 tests are identical to the primary. H4:

| Test | n | Gain | p |
|---|---|---|---|
| G H4a | 1,572 | +0.026 | 0.192 |
| G H4b | 439 | +0.008 | 0.284 |
| H H4a | 1,979 | +0.014 | 0.168 |
| H H4b | 393 | +0.037 | 0.201 |

All are secondary; none survives BH.

---

## 6. Cross-asset H2–H4, evaluation (Gaussian HMM; LEGACY and RAW combined; 218 breaks: LEGACY 171, RAW 47)

Sources: `section6/results/h2_evaluation_gaussian_hmm.json`, `s6_evaluation_gaussian_hmm.json`, `a34_evaluation_gaussian_hmm.json`.

### 6a. H2 (Holm m = 4)

| Asset | n | M | Placebo mean | p | Holm |
|---|---|---|---|---|---|
| TLT | 208 | −1.85e-5 | −1.99e-5 | 0.986 | 1.0 |
| HYG | 191 | +1.02e-4 | +4.32e-5 | 0.550 | 1.0 |
| Gold | 206 | −2.65e-4 | +1.58e-5 | 0.053 | 0.213 |
| USD | 193 | +9.85e-6 | +5.46e-6 | 0.930 | 1.0 |

- **By era p:**
  - LEGACY: TLT 0.749, HYG 0.491, gold 0.059, USD 0.285.
  - RAW: TLT 0.391, HYG 0.868, gold 0.397, USD 0.038 (Holm 0.150).
- **Secondary (39 tests).** Two BH survivors: HYG pre-30 (raw 0.0002, BH 0.0078) and USD pre-30 (raw 0.0008, BH 0.0156).
- **Detector dependence:** no Holm rejection for any detector.
- **E1** (184 breaks), breaks vs placebos:

  | Category | Breaks | Placebos |
  |---|---|---|
  | Flight to safety | 0.5% | 1.2% |
  | Credit stress | 5.4% | 5.6% |
  | Dollar-driven | 6.0% | 5.4% |
  | SPY-only | 51.1% | 62.0% |
  | Other | 37.0% | 25.6% |

### 6b. H3/H4 (Holm m = 6)

| Test | n (placebos) | γ or gain | p | Holm |
|---|---|---|---|---|
| H3 TLT | 208 (4,220) | −0.053 | 0.872 | 1.0 |
| H3 HYG | 184 (3,927) | −0.095 | 0.974 | 1.0 |
| H3 gold | 206 (4,077) | −0.106 | 0.987 | 1.0 |
| H3 USD | 157 (2,885) | −0.212 | 1.000 | 1.0 |
| H4a | 294 (80 confirm) | −0.012 | 0.857 | 1.0 |
| H4b | 218 (69 real) | −0.028 | 0.853 | 1.0 |

- No interval was computed for the evaluation γ.
- Out-of-fold AUC, with C / SPY only: H4a 0.635 / 0.648; H4b 0.503 / 0.531. Valid share 1.0.
- **Secondary (76 tests).** No BH survivor. Smallest raw p: BOCPD H3 gold +0.134 (n 155, p 0.018, BH 0.795); Fed-split H4b +0.293 (n 27, p 0.021, BH 0.795).
- **Rest of day, H3 γ (p):** TLT −0.066 (0.868), HYG +0.064 (0.116), gold −0.054 (0.822), USD −0.050 (0.754).
- **A34 H3 per-asset pools, γ:** TLT −0.043, HYG −0.085, gold −0.129, USD −0.239 (all BH 1.0).

### 6c. Sanity checks (reported, not gates, on the evaluation; A36 2c)

| Check | Development G | Development H | Evaluation G |
|---|---|---|---|
| Positive control (Fed breaks, TLT rest-of-day): n, γ, p | 39, +0.590, 0.0001 | 33, +0.583, 0.0002 | 27, +0.479, 0.0014 |
| Null control, TLT / HYG / gold / USD / H4a / H4b (A35; limit 0.10) | 0.040 / 0.055 / 0.005 / 0.065 / 0.045 / 0.065 | 0.025 / 0.010 / 0.000 / 0.040 / 0.000 / 0.040 | **0.110** / 0.050 / **0.305** / 0.060 / 0.010 / 0.030 (**failed**; S6-D5) |
| A31 filter control | TLT flagged (+0.030 [0.008, 0.052]) | none | TLT flagged (+0.028 [0.007, 0.049]) |

Because the evaluation null control failed for TLT and gold, the evaluation H3 results are not reliable.

---

## 7. A30 lead-lag (descriptive; no test)

Sources: `section6/results/s6_development_gaussian_hmm.json` and `s6_evaluation_gaussian_hmm.json`, key `a30_lead_lag`.

**Measure.** The first 5-min bar in [S − 30, T + 60] where the asset's |cumulative return| exceeds its placebo 90th percentile.

**Gaussian HMM, development** (600 breaks; 538 windows, 62 skipped). Median timing relative to S:

| Asset | n with exceedance | Share | Median relative to S (IQR) | Median relative to T |
|---|---|---|---|---|
| TLT | 223 | 60.3% | −5 min (−20 to +5) | −15 min |
| HYG | 53 | 20.4% | | |
| Gold | 253 | 64.9% | | |
| USD | 8 | | | |

**Evaluation** (218 breaks; 201 windows, 17 skipped):

| Asset | n with exceedance | Share vs placebo chance | Median relative to S (IQR) | Median relative to T |
|---|---|---|---|---|
| TLT | 173 | 87.4% vs 81.7% | −5 min (−20 to +5) | −15 min |
| HYG | 151 | 83.4% vs 79.7% | | |
| Gold | 175 | 89.3% vs 77.8% | | |
| USD | 158 | 86.3% vs 84.9% | | |

SPY's S comes first for every available asset in 7.0% of evaluation windows; development figure in §5c. Distributions: Figure 5.

---

## 8. A38: filter check, RAW evaluation, HF Raw vs HF Clean SPY (2026-11-11 files)

Source: `section5/results/a38_filter_check.json`.

**Panel.**
- Raw: 446,647 observed minutes, 445,410 eligible returns.
- Clean: 435,166 observed minutes, 428,633 eligible returns.

**Splices.** 136 of 1,360 cannot be built on Clean (33 of 400 null, 103 of 960 break). The Raw run applied to the remaining splices gives the paired base.

**Clean − Raw, 95% CI (MDE):**

| Family | H1(a) delta | H1(b) delta | Reading |
|---|---|---|---|
| G | −0.014 [−0.037, +0.010] (MDE 0.034) | −0.004 [−0.008, +0.001] (MDE 0.007) | no detectable filter effect |
| T | −0.001 [−0.030, +0.035] (0.047) | −0.003 [−0.009, +0.002] (0.008) | no detectable filter effect |
| H | −0.011 [−0.042, +0.022] (0.046) | −0.001 [−0.005, +0.003] (0.006) | no detectable filter effect |
| B | 0 | 0 | no detectable filter effect |

- **Rule 2 labels:** G and H "robust to the LEGACY Clean filter"; T and B have none, because their development verdict was not a rejection.
- **Reproducibility (rule 1g).** The 2026-11-11 Raw file reproduces the official H1(a) exactly and H1(b) within 5e-15.
- A38 rule 4 reading: "no detectable filter effect" does not show that the processing of the LEGACY rows had no effect.

---

## 9. Post hoc analyses (labelled post hoc in the ledger; change no frozen, MR2 or evaluation result)

### 9a. 3-start feature selection (2026-11-14)

Source: `section5/results/posthoc_mr2_starts3.json`; `reply_latest.md` block of 2026-11-14.

**Setup.** MR2 5.8 forward selection with 3 k-means++ starts instead of 1, over 34 folds × 3 families. It ran for 548 min. Every unit reproduced the 1-start MR2 trace value exactly.

**Era final setups.** All 6 era-family cells are unchanged (`rv10_partial90__sadj`; K 4 / 4 / 3).

**Fold selections.** 4 of 102 change, all in LEGACY, and all from one feature to none:

| Family | Fold | 1 start | 3 starts | Fold type |
|---|---|---|---|---|
| G | LEGACY 20 | `relative_volume20` | none | confirmatory |
| T | LEGACY 14 | `rv10_partial90__sadj` | none | confirmatory |
| T | LEGACY 24 | `intrabar_range_log__sadj` | none | contaminated |
| T | LEGACY 25 | `intrabar_range_log__sadj` | none | confirmatory |

HSMM: 0 changes.

### 9b. Absolute detection performance

Source: `section5/results/posthoc_absolute_detection.json` and `.md`. Development confirmatory folds use the saved A17 models; the evaluation part uses written outputs only.

**Absolute pAUC** (mean over folds), feature / baseline:

| Family | LEGACY (21/25 folds scored) | RAW (1 fold) |
|---|---|---|
| G | 0.219 / 0.114 | 0.251 / 0.157 |
| T | 0.183 / 0.114 | 0.166 / 0.117 |
| H | 0.237 / 0.124 | 0.193 / 0.128 |
| B | 0.054 / 0.054 | 0.044 / 0.044 |

The two axes are in different units, so there is no chance level.

**Hit within 60 min of onset, LEGACY development, feature model** (2,016 splices per cell), up / down:

| Variance ratio | G | T | H | B |
|---|---|---|---|---|
| ×1.5 | 0.04 / 0.01 | 0.04 / 0.02 | 0.04 / 0.01 | 0.02 / 0.01 |
| ×2 | 0.10 / 0.03 | 0.10 / 0.03 | 0.09 / 0.02 | 0.03 / 0.01 |
| ×3 | 0.24 / 0.05 | 0.20 / 0.06 | 0.22 / 0.06 | 0.04 / 0.01 |
| ×5 | 0.46 / 0.11 | 0.37 / 0.11 | 0.48 / 0.13 | 0.05 / 0.01 |
| ×10 | 0.63 / 0.16 | 0.53 / 0.16 | 0.69 / 0.21 | 0.09 / 0.02 |

**Median delay of those hits** (min; IQR in the source), variance up, ×1.5 → ×10:

| Family | Median delay |
|---|---|
| G | 40 → 20 |
| T | 35 → 20 |
| H | 35 → 20 |

RAW, ×10 up: G 0.83 (n = 96 per cell).

**Alarm rates**, null splices (alarms per splice) and real test sessions (A17), feature / baseline:

| Era | Family | Null splices | Real test sessions |
|---|---|---|---|
| LEGACY | G | 0.177 / 0.231 | 0.202 / 0.231 |
| LEGACY | T | 0.208 / 0.213 | 0.193 / 0.224 |
| LEGACY | H | 0.149 / 0.216 | 0.214 / 0.232 |
| RAW | G | 0.052 / 0.085 | 0.212 / 0.254 |
| RAW | T | 0.048 / 0.207 | 0.225 / 0.229 |
| RAW | H | 0.033 / 0.133 | 0.222 / 0.212 |

**FOMC hit rates, development by era**, feature / baseline:

| Family | LEGACY (94 events) | RAW (4 events) |
|---|---|---|
| G | 0.49 / 0.34 | 0.50 / 0.75 |
| T | 0.30 / 0.24 | 0.50 / 0.50 |
| H | 0.38 / 0.34 | 1.00 / 0.50 |

---

## 10. Bloomberg data check (post-evaluation; descriptive)

Source: `section5/results/bloomberg_comparison.json`.

**Setup.** RAW panel 1-min log returns vs Bloomberg 1-min trade bars (Book1 SPY, Book2 HYG), 2026-03-18..2026-09-30, 136 sessions in both. One guarded RAW read was logged.

| | SPY | HYG |
|---|---|---|
| Best lag k | 0 | 0 |
| Correlation at k = 0 | 0.950 | 0.795 |
| Correlation at k = −1 / +1 | 0.049 / 0.020 | 0.120 / 0.008 |
| Matched minutes | 52,904 | 43,958 |
| Median abs diff (bp) | 0.45 | 0.62 |
| 99th percentile abs diff (bp) | 3.41 | 2.49 |
| Within 1 bp | 79.8% | 84.7% |
| Abs diff ≥ 10 bp (minutes) | 11 | 0 |
| Per-session sum abs diff: median / max (bp) | 1.10 / 5.40 | 2.50 / 13.79 |

**Reading.** Both sources use bar-start labels, which supports the Section 3 minute-start assumption for RAW in this window. No price levels were compared, because the panel holds returns only.

---

## 11. Time-of-day seasonality (descriptive; Figure 6)

**Adjustment** (Section 4.3.4, A4 F2). `__sadj` = raw / median of the same minute slot over the previous 20 sessions of the era (at least 10 finite). The checks passed in both eras (`section431_step3_all_in_one_results/a4_sec4_3_4_checks.json`):
- brute force: 105,000 cells, 0 mismatches;
- prefix invariance: 0 mismatches.

**Figure 6.** It shows per-minute medians over full 390-bar TRAIN sessions from the development feature cache (`section5/cache/{LEGACY,RAW}_features.npz`; slots from `section5/results/session_bars.json`). Each curve is divided by its median over minutes:
- the raw `|1-min return|` and `rv10_partial90` have the U-shape;
- the `__sadj` versions are flat at 1.

No number from Figure 6 is a reported result. TRAIN-pooled per-slot medians of the raw features: `section431_step3_all_in_one_results/sec4_3_4_slot_medians_{LEGACY,RAW}.csv`.

---

## 12. Figures

Location: `paper/figures/`; script `paper/make_figures.py`; input hashes in `figure_sources.json`; figure-only statistics in `figure_stats.json`.

| Figure | Content | Figure-only computation |
|---|---|---|
| `fig1_h1a_pauc_gain` | H1(a) pAUC gain by family: (a) development, 22 confirmatory fold effects with the mean; (b) evaluation LEGACY and RAW with stored 95% CIs | (a) 95% percentile bootstrap of the fold mean, 10,000 resamples, seed 0: G [0.079, 0.132], T [0.044, 0.092], H [0.087, 0.134]. Not the protocol test (which is the block bootstrap p in §1a) |
| `fig2_fomc_hit_rates` | FOMC hit rates, feature vs baseline: development (98 events, stored Wilson 95%), evaluation LEGACY (24) and RAW (14) | Evaluation Wilson 95% intervals computed from the stored hit rates × events (the stored evaluation CI is for the difference only) |
| `fig3_detection_by_break_size` | Hit within 60 min by planted variance ratio (up and down) and median delay (IQR), feature and baseline, LEGACY development confirmatory folds | none |
| `fig4_h3_gamma` | H3 next-day γ by asset: development G and H, evaluation G | none. Intervals only where stored (development TLT and gold, post hoc A29 3b); other points have none |
| `fig5_a30_timing` | A30 distribution of the first exceedance bar relative to S, per asset, development vs evaluation (Gaussian HMM) | none (normalised stored counts) |
| `fig6_seasonality` | Per-minute median of raw vs `__sadj` features, LEGACY and RAW TRAIN | descriptive medians of the development feature cache |

**Rendering.** Made with system Python 3.12.10 / matplotlib 3.11.2, because the research environment has no matplotlib and is left unchanged. Plotting computes nothing that enters a result.

**Palette.** The first three categorical slots of the dataviz reference palette, validated for all pairs: G blue `#2a78d6`, T orange `#eb6834`, H aqua `#1baf7a`. Markers differ by family, so identity is not carried by colour alone.
