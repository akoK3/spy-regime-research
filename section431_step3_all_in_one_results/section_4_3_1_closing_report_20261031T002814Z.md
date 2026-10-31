# Section 4.3.1 closing report

**SECTION_4_3_1_CLOSED**

Closed 2026-10-31T00:28:14.568670+00:00 UTC (2026-10-30T20:28:14.568670-04:00 New York). Repository HEAD before this commit: `f183975f948ec25cf83cc1509fdceab173f32e44`.

Closed means the construction and audit of the 4.3.1 features are complete and recorded. It does not settle the open decisions listed at the end.

## Steps 1-6

| Step | Scope | Result |
|---|---|---|
| 1 | Baseline inputs (the label 'Step 1' is not defined in any file; this lists what Steps 2-6 rely on) | Frozen protocol v2 with 35 candidate features built on the development rows (REPORT.md: 2,150,970 minute rows); test_candidates.py 6/6 pass; panel audit PASS in both eras (TRAIN rows LEGACY 1,562,460, RAW 274,050); additional-family prototype (section431_additions.py) and feasibility diagnostics. |
| 2 | Missingness, calendar and family-coverage audit (coverage amendment frozen before that run read data, but written after aggregate coverage had already been seen) | 11 feature families screened against the 80% floor in each era: 7 meet it (bipower_variation, jump_variation, drawdown, amihud_illiquidity, close_location, directional_efficiency, overnight_return); 4 are below it in LEGACY (lee_mykland_jumps, skewness_and_kurtosis, variance_ratio, volatility_of_volatility), all strict-60-return families (LEGACY 37.735%, RAW 82.982%). Family proxies only; verification then pending. |
| 3 | Implementation audit of 81 outputs per era (35 original, 46 additional) | RAW PASS and LEGACY PASS, 8 of 8 checks each: inventory, formula_all_outputs (independent per-row oracle, synthetic panel), formula_spot_checks, real_train_prefix_invariance, prior_session_isolation, numerical_sanity, deferred_implementations, provider_isolation. Prefix and isolation tests use the 40-session slice method. Phase-A baseline: test_candidates 6 pass; the prototype test_additions.py runs no tests. |
| 4 | Lookback, minimum valid observations and warmup extracted from the code, compared with the frozen protocol and A2 | 80 PASS, 0 FAIL, 1 EXCLUDED (overnight_return_open). Before A2 the same comparison gave 35 PASS, 1 FAIL (overnight contradicts the frozen 'No overnight returns') and 45 NO_SPEC. No output reads bars after t. |
| 5 | Causality and boundary policy P1, with verification | R1 usable at t+1 minute, R2 session reset, R3 no LEGACY/RAW crossing, R4 overnight excluded: all PASS against saved Step 3/4 results. The original one-bar shift test FAILED and is retained, labeled MIS-SPECIFIED (not counted). Replacement test (identical values, available_at = t+2 min, point-in-time replay) PASS on a synthetic panel, a RAW slice and a LEGACY slice. |
| 6 | TRAIN-only coverage of the 80 detector outputs (descriptive) | Frozen coverage amendment: denominator all TRAIN grid rows per era, 80% floor in each era; numerator = the column's own finite values (user decision). 20 PASS, 60 BELOW, all 60 below in LEGACY only; RAW is at least 82.7% everywhere. No PASS column has a LEGACY year under 80%. |

## Amendments and policies

| Document | Dated | SHA-256 | Location |
|---|---|---|---|
| Frozen protocol v2 (35 candidate features, split, clocks) (`protocol_20261029T032641Z.json`) | frozen 2026-10-29T03:26:41Z | `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b` | original: Desktop\data\section4_3_rebuild_20261028 |
| Frozen protocol v1 (superseded) (`protocol_20261029T032504Z.json`) | 2026-10-29T03:25:04Z | `6df8667a5c8e60f73a994ce4553adceca3000dbb4dd59ed60f41968689a43661` | original: same folder |
| Amendment 4.3.0-A1 (proposal, NOT approved) (`protocol_amendment_4_3_0_A1_20261029T034121Z.json`) | 2026-10-29T03:41:21Z | `a57d55ccc760c2359d2d5d14c12d52a3fb1ba29a1bd3e222a71e6284886724ae` | original: ...\section4_3_rebuild_20261028\results |
| Coverage amendment 4.3.1-A2-post-screening (80% floor, denominator) (`protocol_amendment_431_A2_FROZEN_coverage.json`) | 2026-10-30 | `d20c1b2cf65a85f30a6b77a94a55ed89677ad8044ca6967dc1c62b4e951b5faf` | original: Downloads\section431_step2_final_audit\protocol_amendment_431_A2_FROZEN.json |
| Amendment 4.3.1-A2 (45 added outputs, cap, overnight exclusion) (`amendment_4_3_1_A2_20261030T231344Z.json`) | 2026-10-30T23:13:44.794567+00:00 | `2e2beb61489203c62988fda83ec0b1b7696f2a4d3bb1aa7f68a85275cae93ad5` | this repo |
| Policy 4.3.1-P1 (causality and boundary) (`policy_4_3_1_P1_20261030T233123Z.json`) | 2026-10-30T23:31:23.585756+00:00 | `580b9c9c4f4df578ba3f4aeda61556d73d8aaed486ec7866a11f93eaf103f75c` | this repo |
| Policy addendum 4.3.1-P1-A (delay test replaced) (`policy_4_3_1_P1_addendum_20261030T234021Z.json`) | 2026-10-30T23:40:21.718133+00:00 | `4e27eb3a3b8db6529788ad10804e185242a19e4426b5a6ea13a360430d53c719` | this repo |

Other hashed records: Step 3 reports, Step 4 table, verification reports, coverage and the diagnosis are listed in the inventory below and in each step's `*_sha256.txt`.

## Feature dictionary (80 detector outputs and the excluded one)

| Output | Specified by | Lookback (bars / sessions) | Min valid | Warmup | Step 4 | LEGACY % | RAW % | Coverage |
|---|---|---|---|---|---|---|---|---|
| return_1m | frozen protocol | 1 / 0 | 1 returns | slot 1 / session 0 | PASS | 95.238 | 99.562 | PASS |
| abs_return_1m | frozen protocol | 1 / 0 | 1 returns | slot 1 / session 0 | PASS | 95.238 | 99.562 | PASS |
| intrabar_range_log | frozen protocol | 0 / 0 | 1 bars | slot 0 / session 0 | PASS | 96.927 | 99.850 | PASS |
| raw_volume | frozen protocol | 0 / 0 | 1 bars | slot 0 / session 0 | PASS | 96.927 | 99.850 | PASS |
| log_raw_volume | frozen protocol | 0 / 0 | 1 bars | slot 0 / session 0 | PASS | 96.927 | 99.850 | PASS |
| relative_volume20 | frozen protocol | 0 / 20 | 10 sessions | slot 0 / session 10 | PASS | 96.678 | 98.427 | PASS |
| log_relative_volume20 | frozen protocol | 0 / 20 | 10 sessions | slot 0 / session 10 | PASS | 96.678 | 98.427 | PASS |
| rv5_strict | frozen protocol | 5 / 0 | 5 returns | slot 5 / session 0 | PASS | 89.502 | 98.423 | PASS |
| downside5_strict | frozen protocol | 5 / 0 | 5 returns | slot 5 / session 0 | PASS | 89.502 | 98.423 | PASS |
| momentum5_strict | frozen protocol | 5 / 0 | 5 returns | slot 5 / session 0 | PASS | 89.502 | 98.423 | PASS |
| rv5_partial90 | frozen protocol | 5 / 0 | 5 returns | slot 5 / session 0 | PASS | 89.502 | 98.423 | PASS |
| momentum5_endpoint | frozen protocol | 5 / 0 | 2 bars | slot 5 / session 0 | PASS | 93.166 | 98.533 | PASS |
| rv10_strict | frozen protocol | 10 / 0 | 10 returns | slot 10 / session 0 | PASS | 82.990 | 97.003 | PASS |
| downside10_strict | frozen protocol | 10 / 0 | 10 returns | slot 10 / session 0 | PASS | 82.990 | 97.003 | PASS |
| momentum10_strict | frozen protocol | 10 / 0 | 10 returns | slot 10 / session 0 | PASS | 82.990 | 97.003 | PASS |
| rv10_partial90 | frozen protocol | 10 / 0 | 9 returns | slot 10 / session 0 | PASS | 85.072 | 97.057 | PASS |
| momentum10_endpoint | frozen protocol | 10 / 0 | 2 bars | slot 10 / session 0 | PASS | 91.645 | 97.247 | PASS |
| rv15_strict | frozen protocol | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| downside15_strict | frozen protocol | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| momentum15_strict | frozen protocol | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| rv15_partial90 | frozen protocol | 15 / 0 | 14 returns | slot 15 / session 0 | PASS | 78.828 | 95.638 | BELOW |
| momentum15_endpoint | frozen protocol | 15 / 0 | 2 bars | slot 15 / session 0 | PASS | 90.356 | 95.960 | PASS |
| rv30_strict | frozen protocol | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| downside30_strict | frozen protocol | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| momentum30_strict | frozen protocol | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| rv30_partial90 | frozen protocol | 30 / 0 | 27 returns | slot 30 / session 0 | PASS | 77.653 | 92.110 | BELOW |
| momentum30_endpoint | frozen protocol | 30 / 0 | 2 bars | slot 30 / session 0 | PASS | 86.707 | 92.102 | PASS |
| rv60_strict | frozen protocol | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| downside60_strict | frozen protocol | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| momentum60_strict | frozen protocol | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| rv60_partial90 | frozen protocol | 60 / 0 | 54 returns | slot 60 / session 0 | PASS | 72.527 | 84.416 | BELOW |
| momentum60_endpoint | frozen protocol | 60 / 0 | 2 bars | slot 60 / session 0 | PASS | 79.393 | 84.388 | BELOW |
| downside15_partial90 | frozen protocol | 15 / 0 | 14 returns | slot 15 / session 0 | PASS | 78.828 | 95.638 | BELOW |
| rv60_sampled5_exact | frozen protocol | 60 / 0 | 13 bars | slot 60 / session 0 | PASS | 58.624 | 84.092 | BELOW |
| shock_prior60_mad | frozen protocol | 61 / 0 | 61 returns | slot 61 / session 0 | PASS | 37.078 | 82.704 | BELOW |
| close_location_proxy | A2 (4.3.1-A2) | 0 / 0 | 1 bars | slot 0 / session 0 | PASS | 96.325 | 99.672 | PASS |
| overnight_return_open | A2 exclusion | 65 / 1 | 2 bars | slot 0 / session 1 | EXCLUDED | - | - | excluded |
| bipower_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| jump_variation_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| drawdown_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| amihud_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| skew_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.882 | 95.584 | BELOW |
| kurtosis_excess_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.882 | 95.584 | BELOW |
| variance_ratio2_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.882 | 95.584 | BELOW |
| directional_efficiency_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.882 | 95.584 | BELOW |
| vol_of_vol_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| extreme_loss_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| volume_variability_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| volume_adjusted_range_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.883 | 95.584 | BELOW |
| reversal_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.157 | 95.569 | BELOW |
| return_autocorr1_15 | A2 (4.3.1-A2) | 15 / 0 | 15 returns | slot 15 / session 0 | PASS | 76.882 | 95.584 | BELOW |
| bipower_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| jump_variation_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| drawdown_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| amihud_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| skew_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| kurtosis_excess_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| variance_ratio2_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| directional_efficiency_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| vol_of_vol_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| extreme_loss_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| volume_variability_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| volume_adjusted_range_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| reversal_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.666 | 91.357 | BELOW |
| return_autocorr1_30 | A2 (4.3.1-A2) | 30 / 0 | 30 returns | slot 30 / session 0 | PASS | 60.763 | 91.358 | BELOW |
| bipower_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| jump_variation_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| drawdown_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| amihud_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| skew_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| kurtosis_excess_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| variance_ratio2_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| directional_efficiency_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| vol_of_vol_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| extreme_loss_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| volume_variability_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| volume_adjusted_range_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| reversal_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.726 | 82.982 | BELOW |
| return_autocorr1_60 | A2 (4.3.1-A2) | 60 / 0 | 60 returns | slot 60 / session 0 | PASS | 37.735 | 82.982 | BELOW |
| lee_mykland_approx60 | A2 (4.3.1-A2) | 61 / 0 | 61 returns | slot 61 / session 0 | PASS | 37.135 | 82.704 | BELOW |
| lee_mykland_jump60 | A2 (4.3.1-A2) | 61 / 0 | 61 returns | slot 61 / session 0 | PASS | 37.135 | 82.704 | BELOW |

### Definitions

Frozen protocol (verbatim, `windows_minutes` 5, 10, 15, 30, 60):

- **return_1m**: ln(C_t/C_(t-1)); exact consecutive within-session closes, decimals
- **strict**: For W in 5,10,15,30,60: require W eligible returns ending at t, slot>=W. RV=sqrt(sum(r^2)); downside=sqrt(sum(min(r,0)^2)); strict momentum=sum(r)
- **endpoint_momentum**: ln(C_t/C_(t-W)) for W in 5,10,15,30,60; exact two closes and same session. Interior gaps allowed; not an RV estimator
- **partial90**: sqrt(W/n * sum(observed r^2)) with full W-minute clock window and n>=ceil(.90 W). All five W; downside variant at W=15. Proxy, no assertion of random gaps or unbiasedness
- **sampled5**: rv60_sampled5_exact: sqrt(sum of twelve exact five-minute log returns squared), closes at t,t-5,...,t-60. Sliding phase; a different sampling-scale estimator
- **range**: ln(High/Low) of current completed bar
- **volume**: Raw and natural-log volume; log undefined for zero. relative_volume20=current volume/median positive same-slot volume from previous 20 scheduled sessions, at least 10 positives. Current zero ratio=0; log ratio unavailable
- **shock**: (r_t-median(previous 60 exact returns))/(1.4826*MAD(previous 60)); require 61 consecutive eligible returns including current and positive MAD. No epsilon/fill for zero scale
- **abs_return_1m**: absolute value of return_1m

A2 (w = the window in the output name: 15, 30 or 60; `lee_mykland_*` use 60 prior returns):

- **close_location**: (Close-Low)/(High-Low) of the current completed bar; defined only if High>Low and the bar has Close>0, High>=Close>=Low, Low>0, Volume>=0, all finite
- **bipower**: (pi/2)*sum of |r_i||r_(i-1)| over the w-1 adjacent pairs of the w returns ending at t
- **jump_variation**: max(0, sum of r_i^2 over the w returns - bipower_w)
- **drawdown**: Close_t / max(Close over t-w..t) - 1, from w+1 exact closes; zero or negative
- **amihud**: mean over the w bars of |r_i| / (Volume_i*Close_i); needs all volumes finite and dollar volume > 0
- **skew**: mean(z^3) with z=(r-mean)/sd over the w returns, population sd (ddof=0); needs sd>0
- **kurtosis_excess**: mean(z^4)-3 with the same z; needs sd>0
- **variance_ratio2**: mean((r_i+r_(i-1))^2) over adjacent pairs / (2*mean(r_i^2)); needs positive variance
- **directional_efficiency**: |ln(Close_t/Close_(t-w))| / sum|r_i| over the w returns; undefined if sum|r_i|=0
- **vol_of_vol**: sample SD (ddof=1) of the w/5 non-overlapping 5-return realized volatilities sqrt(sum r^2) in the window
- **extreme_loss**: min(r_i) over the w returns
- **volume_variability**: SD(ddof=1)/mean of Volume over the w bars; needs mean>0; also requires the w returns to be finite
- **volume_adjusted_range**: mean over the w bars of ln(High/Low)/Volume; needs all Volume>0 and finite ranges; also requires the w returns to be finite
- **reversal**: 1.0 if sign(sum of first w//2 returns) != sign(sum of the rest), else 0.0; undefined if either sum is 0
- **return_autocorr1**: Pearson correlation of (r_i, r_(i-1)) over the w-1 adjacent pairs; needs both SDs > 0
- **lee_mykland_approx60**: r_t / sqrt((pi/2) * (1/59) * sum of |r_i||r_(i-1)| over the 59 adjacent pairs of the 60 prior returns); the current return is excluded from the scale; needs 60 finite prior returns, finite r_t and scale>0
- **lee_mykland_jump60**: 1.0 if |lee_mykland_approx60| > c0 - s0*ln(-ln(1-alpha)) with n=390, alpha=0.01 (threshold 5.4667), else 0.0; undefined where the statistic is undefined; c0=sqrt(2 ln n)/sqrt(2/pi)-(ln pi+ln ln n)/(2*sqrt(2/pi)*sqrt(2 ln n)), s0=1/(sqrt(2/pi)*sqrt(2 ln n))
- **overnight_return_open** (excluded): log(Open of the session's first bar / Close of the previous session's last bar), assigned to every bar of the session; NaN for the era's first session or if either price is missing/non-positive

Cap (A2): a detector feature may use the returns of the 60 bars before t and of bar t itself; Step 4 lookback limit 61. Missing data: no interpolation or fill, NaN is never zero.

## Known limitations

1. 60 of the 80 detector outputs are BELOW the 80% coverage floor in LEGACY (every 15-, 30- and 60-minute window output and shock_prior60_mad, lee_mykland_*). Closing this section does not decide whether to drop, keep or re-window them; that is an open model-selection decision.
2. The coverage amendment is 'post-screening': aggregate coverage had been inspected before it was written. It defines numerators only for 11 families through proxies; using each column's own finite values is an extension chosen by the user. Step 2 family proxies differ from the real windowed columns (for example drawdown proxy 96.9% vs drawdown_15 76.9%, drawdown_60 37.7% in LEGACY). Earlier availability figures in REPORT.md use a different denominator and are not comparable.
3. Step 3 audited TRAIN spans only (LEGACY 2003-01-02..2018-12-21, RAW 2022-03-07..2024-12-23). The frozen development spans extend to 2022-03-04 (LEGACY) and 2024-12-31 (RAW); the days around the 2022-03-04/2022-03-07 boundary and the evaluation period were never in an audited span. R3 rests on era-separate loading and the first-10-sessions check.
4. Prefix and isolation tests use a 40-session slice (last 15 sessions compared), not full-era recomputation. Formula checks against the independent oracle ran on one synthetic panel; only spot checks ran on real data. The delay-test replay used 3 rows per dataset, and its value-identity check holds partly by construction because the feature code never reads the availability field.
5. The 45 outputs added by A2 were specified after implementation and are not ex ante. Their formulas come from section431_additions.py and, for close_location_proxy and lee_mykland_*, were ported from section-4.3.1.py because build_features_4_3_1.py does not exist; lee_mykland_jump60 was added as a fourth output. Two different documents carry the name 'A2' (4.3.1-A2 here and 4.3.1-A2-post-screening for coverage).
6. The cap '60 prior bars' is defined on return-bars (Step 4 lookback limit 61). A literal cap that counts the reference close as a bar would exclude shock_prior60_mad (frozen) and lee_mykland_*. Amendment 4.3.0-A1 remains an unapproved proposal; its 60-minute lookback and 5-session embargo do not cover the 20-session relative-volume history, and this conflict is unresolved.
7. overnight_return_open is excluded declaratively (A2, Step 4 check). The audit script still computes it and no detector code exists to enforce the exclusion. The overnight analysis itself is not specified.
8. LEGACY historical clock semantics and possible centered vendor cleaning remain unresolved; a past-only implementation does not certify vendor causality. Later timing work must report the legacy -1/0/+1 minute sensitivity.
9. Cumulative-sum features (strict RV, downside, momentum) carry about 1e-13 of absolute floating-point noise that depends on earlier bars in the session; harmless for modelling, formulas unchanged.
10. The original delay test failed at clock-position edge rows (partial90 at slot W; relative volume after an early close). It was replaced after the failure was seen; the replacement was therefore not set ex ante.
11. No 2025-2026 period is an unexposed test. The git repository was created in Downloads during Step 3 onward; the frozen documents are copied into frozen_documents/ with hashes verified identical to the originals, which remain where they were.

## Decisions not taken

- Which BELOW-floor outputs to keep, drop or re-window
- The overnight analysis and its specification
- Approval or rejection of amendment 4.3.0-A1 and the embargo
- Any detector, scaler or HMM fit
- Legacy timing sensitivity

## SHA-256 inventory of tracked files (before the closing commit)

| Path | SHA-256 |
|---|---|
| .gitignore | `e8e6cf258cbd152c66ed56ec2057a847cb908f846884c344c7b9238ac24a25d5` |
| frozen_documents/protocol_20261029T032504Z.json | `6df8667a5c8e60f73a994ce4553adceca3000dbb4dd59ed60f41968689a43661` |
| frozen_documents/protocol_20261029T032504Z.sha256 | `94b426982e8ebe38db3957f7f1288eb68c65fe75082d754e5663bfc8e396337f` |
| frozen_documents/protocol_20261029T032641Z.json | `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b` |
| frozen_documents/protocol_20261029T032641Z.sha256 | `fd0063afe115667742aab8196fdb0a878f3dce6f48bc533950ff3584fa5f4b1d` |
| frozen_documents/protocol_amendment_431_A2_FROZEN_coverage.json | `d20c1b2cf65a85f30a6b77a94a55ed89677ad8044ca6967dc1c62b4e951b5faf` |
| frozen_documents/protocol_amendment_4_3_0_A1_20261029T034121Z.json | `a57d55ccc760c2359d2d5d14c12d52a3fb1ba29a1bd3e222a71e6284886724ae` |
| frozen_documents/protocol_amendment_4_3_0_A1_20261029T034121Z.sha256 | `84ab69f8d9c1ecbc6e29e1a3a7c5d88135ea11d02fed9313552bbf991424aebc` |
| section431_step3_all_in_one_results/amendment_4_3_1_A2_20261030T231344Z.json | `2e2beb61489203c62988fda83ec0b1b7696f2a4d3bb1aa7f68a85275cae93ad5` |
| section431_step3_all_in_one_results/amendment_4_3_1_A2_20261030T231344Z.sha256 | `c3e72a665423b3018b7c658704a376bf3590a40cf75d69cec01d2ccc82abe095` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_20261030T233123Z.json | `580b9c9c4f4df578ba3f4aeda61556d73d8aaed486ec7866a11f93eaf103f75c` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_20261030T233123Z.sha256 | `fb51a88ad4376ad5bc397276405a7b99b460ccdf010de0f405a99d12f0978133` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_addendum_20261030T234021Z.json | `4e27eb3a3b8db6529788ad10804e185242a19e4426b5a6ea13a360430d53c719` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_addendum_20261030T234021Z.sha256 | `ac26d7a63fb06f80dcc47b9994f86babf990f7c32c509539e670067ed36ba3cd` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_20261030T233210Z.json | `ebef788e7fab08254a6bd4828bf0cf10f176dbf3757604da61be4d44f72d32a2` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_20261030T233210Z.md | `6a3e33f77802cd0738bb565bed3435d73026eaf9997f2cb504db32896566223e` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_20261030T233210Z.sha256 | `c02989d289b0b0f508566f14e4e3f43f172bc2347f971590d618341d80f9d737` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_v2_20261030T234138Z.json | `6bad34c84d3bc71e1a9e234323a6b279223634188b217d2fff5bc51eafd3800e` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_v2_20261030T234138Z.md | `69e63806838fbeeb6d2cb0030b7cd72177fd8229b5edbcbb4c223217f4d08378` |
| section431_step3_all_in_one_results/policy_4_3_1_P1_verification_v2_20261030T234138Z.sha256 | `8cac838a01248ccdda48e838d6b08c4c7bed1adcaf89ffb80df409ea2a4a5614` |
| section431_step3_all_in_one_results/run_log_LEGACY_final.txt | `dc723c905f8e3188a55000b0316b2340908517e2f6a25774bed282975ca9bde0` |
| section431_step3_all_in_one_results/run_log_RAW_final.txt | `85f4c99d4916711f7421026e4351eaf378f3bdcd88cfb36fef6da7af92060be6` |
| section431_step3_all_in_one_results/step3_LEGACY_report.json | `35461cda5821c1038d05add319afb8fc808c756df47b9919b32fea6988182f3c` |
| section431_step3_all_in_one_results/step3_RAW_report.json | `b586ee682467f3ac978884dd1895e7b1078713a7b173f7a419246b459dafc61b` |
| section431_step3_all_in_one_results/step3_final_sha256.txt | `fdb0e12571948e39a72f0dac06d70a6cadac40bc718f489d50aba84394da8406` |
| section431_step3_all_in_one_results/step3_summary.json | `1383736104cdc65604c38b80bafa0e510f06bacfb0d0abc3109da7e76eb9804f` |
| section431_step3_all_in_one_results/step4_final_sha256.txt | `7067313388a40df8538ef55c2ce37d8557af2d0633291f3cda71cc0fe89be030` |
| section431_step3_all_in_one_results/step4_parameter_table.json | `f8ca6c42300b6118a0abe038221cf6fda9fbfa8864ed47001212ad35dcf73df9` |
| section431_step3_all_in_one_results/step4_parameter_table.md | `64595890b91584c677824473a7c47c22ff778005b70cbaf85cfcc4d32c47f4e6` |
| section431_step3_all_in_one_results/step4_run_log.txt | `c425eed87514f3262a37aa2693f295baedf7d1483c65e55f108f6453627c62d4` |
| section431_step3_all_in_one_results/step5_delay_failure_diagnosis.json | `3677fc1766078aa0e4fcb0a15202cd83863211dba28f1aab5f2be0b8b3c04f95` |
| section431_step3_all_in_one_results/step5_delay_failure_diagnosis.sha256 | `b1ebdbee34e80621f2fa538f16fef58677ad4ae11c0df0de6d12df0670dd6f4a` |
| section431_step3_all_in_one_results/step5_diagnosis_log.txt | `3f3742d0c7d56186cc869e0cc98239b6b32f8cdee190d402ea2467a7a7f0aee7` |
| section431_step3_all_in_one_results/step5_final_sha256.txt | `373c0e7fa2312b234b54d4041a67f0e5a2f636c75325c5074cd66efdeac3891a` |
| section431_step3_all_in_one_results/step5_v2_final_sha256.txt | `eb67e9805bf3c7433fbf7d6f35e03335a206a82e34ef907e19ae4503442f43e1` |
| section431_step3_all_in_one_results/step5_verify2_log.txt | `024364f135f2ca96922ec1e5401ad1d653af3a239c718d5d0d88b9630eef9be6` |
| section431_step3_all_in_one_results/step5_verify_log.txt | `9efdedaf22686c67eec3c736933bb99ed3bf0b204578bcc801d7c0aeea571be9` |
| section431_step3_all_in_one_results/step6_coverage_LEGACY_by_year.csv | `eeb9ea92c911b8462780d640c4048405fef0af3f5398280f3d879629c181745d` |
| section431_step3_all_in_one_results/step6_coverage_TRAIN.csv | `990d8a9cc24cc140817d967d61bcbd4b3d5d63a30a1ec8a8d3879c79d55a97cc` |
| section431_step3_all_in_one_results/step6_coverage_TRAIN.json | `a033c150005b8e4deed62398d984973e8b7242829827185f513855098db7d58d` |
| section431_step3_all_in_one_results/step6_coverage_TRAIN.md | `040f89ca8239106a9c43f4737a6dff0be8ed1b4a5a4d7b4d854c63e55ecbac33` |
| section431_step3_all_in_one_results/step6_coverage_TRAIN.sha256 | `a8535ffa88fe52d03ed9752e64b7bfb7ff2581f693f7bd44fd39ba67dce74300` |
| section431_step3_all_in_one_results/step6_final_sha256.txt | `2cdf244da4b71e03f285a8bab4e84049902684f9acb01eb27e89cb2196c251db` |
| section431_step3_all_in_one_results/step6_run_log.txt | `acb41002dd81a4fec6583f85d73e7021b61a07951a36e63c56817703e4f5f351` |
| section431_step3_verification/prototype_sources/section431_additions.py | `c8a550f7777abcfdd3e46132f76c25748ed62be15b430d40a5c23556f6308448` |
| section431_step3_verification/prototype_sources/section4_3_1_candidates.py | `4c8d2b528ff8b86a2885426d974e9be97fbc3d264d60b4e2bf38f16981204878` |
| section431_step3_verification/prototype_sources/test_additions.py | `ca52b4ca95b42380d622b622155264de5c0650ca1bea6a6d3a73e5bcde50faf2` |
| section431_step3_verification/prototype_sources/test_candidates.py | `cab8833a1b104fe1d4f9c01ebfde8f69a7d1fb4359744ea0bfe23e4a71e1db12` |
| step3_431_verification.py | `d56f65caad0364d60a7f4dca32e9e97c10fc52c0371528f8104ea6796f8ad9ce` |
| step3_all_in_one.py | `f42150ccc1a45fb44a184c58b31e93f57e00f1e6318756f871ba3fb15cf5f40d` |
| step4_extract_parameters.py | `8a62f1dae57a6c26451860d0015300c7d22954afa53016268f48b28e807e18b1` |
| step5_delay_diagnosis.py | `c419cc059709873c7d417182c6def28d2ac2d2bd18470b4369ac7a0d361ed546` |
| step5_policy.py | `3a8efb3789b67a1aabb51bbb346f81b60d985a0a21369e9639e43c53ccec9cf6` |
| step6_coverage.py | `4a19af8a7d6b3e45dec0896ac2ec13d54635c302acb01befb393b5b8236dc169` |
| write_amendment_4_3_1_A2.py | `338ba691a2fd26798070f6d3538a69656bfccd97d8bd494b09b6ebf6a6d3dd80` |
| write_closing_report_4_3_1.py | `b164559f22105efd3d1d0c848b9a5d92a0aaca6829f42d385fd81ff5bc0a4904` |
