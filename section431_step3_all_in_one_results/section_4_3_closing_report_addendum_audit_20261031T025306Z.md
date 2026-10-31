# Section 4.3 closing reports: addendum from the cold audit (#3, #4, #6 disclosed; #7 corrected)

**SECTION_4_3_CLOSED** (unchanged; the closed reports are not edited)

Added 2026-10-31T02:53:06.969094+00:00 UTC (2026-10-30T22:53:06.969094-04:00 New York). Audit `cold_audit_20261030.md` SHA-256 `d720d46e238a22e5b93da93db14c3a42001e91cb55f9f7813200f5e4665412ac`. Amendment A4 `amendment_4_3_A4_20261031T021111Z.json` SHA-256 `1960e83752b4dd5fa25dd022792e8a57f89ba79e9c79df02a50fceba96747304`.

Amends: `section_4_3_closing_report_section4_20261031T011136Z.json` (`4541880b1ac88d866cab7119e148143871ee0678a68b08c2b8e06730a27b2bff`); `section_4_3_1_closing_report_20261031T002814Z.json` (`f7cfb9f3ae39629319088f69b27156849a06c2c7349fae58453fd2969865515a`)

## Disclosure #3: Features are selected on all of TRAIN, outside the folds.

Protocol rule: Within each fold select using inner train/validation only; refit on preceding 252 sessions before outer development diagnostics. All features/scalers/models train chronologically; no selection on retrospective 2025-2026 or target reactions.

- 4.3.7 and 4.3.8 (A3 run and 116-column pool run) use every TRAIN row of each era; no fold boundary enters the selection.
- A3 run, primary set: 6 drops, smallest |rho| with the kept partner over both eras 0.999803.
- 116-column pool run: primary pool 30 columns with 15 drops; RAW sensitivity pool 116 columns with 48 drops.

After A4: A4 reruns 4.3.4, 4.3.7 and 4.3.8 (causal baseline, 113-column pool): primary pool 27 columns, keep 19, drop 8; RAW sensitivity pool 113, keep 83, drop 30. It still selects on all of TRAIN; the folds of F1 are not used by the selection. Selections stay descriptive until recomputed inside each fold.

## Disclosure #4: Era-crossing decisions contradict the project's own rule.

- Rule: A3 general_rules: Eras are computed separately; no value, statistic or window crosses the LEGACY/RAW boundary (P1 R3).
- Rule: P1 R3: LEGACY (through 2022-03-04) and RAW (from 2022-03-07) are loaded and computed separately. No return, window, volume history (including the relative-volume baseline), scaler, fit or state crosses the boundary. The first 10 sessions of each era have no relative volume.

- A3 4.3.7 primary requires at least 80% in both eras; A3 4.3.8 calls a pair redundant if |rho| > 0.95 in either era. Both combine the two eras in one decision.
- intrabar_range_log__sadj left the primary pool because of LEGACY: rho with intrabar_range_log 0.959782 (LEGACY), versus 0.938401 in RAW.
- Step 6: 60 columns are BELOW the floor in LEGACY only; the lowest RAW coverage of any column is 82.704%. The LEGACY coverage therefore removes 60 columns from RAW's primary set.
- In the primary set the RAW correlations feed decisions on LEGACY columns, and the reverse.

## Disclosure #6: Two of the three replacement delay checks cannot fail.

Replacement test as defined: Add an extra 1-minute delay: every bar becomes available at t+2 minutes instead of t+1. Then (V) all 80 detector feature values, NaN pattern included, are identical to the undelayed run; (A) the available_at of every finite feature value equals t+2 minutes; (P) in a point-in-time replay, at decision time t+2 minutes the features computed from only the visible bars equal the full-run value at row t, and at decision time t+1 minute row t is not yet visible.

- Functions among construct, relative_volume, construct_additions, construct_deferred that access the 'available' key of the data: none. The 'all feature values identical' check therefore compares features computed from the same bars and cannot differ.
- The 'available_at = t+2 minutes' check is computed from the t and available arrays, not from any feature value, so it holds by construction.
- The point-in-time replay is the only check that exercises the data, and it covers 3 rows per dataset.
- Audit-reported, not reproduced here: shifting all 80 features one bar into the future left the first two checks passing, while the replay failed on 76, 73 and 72 of 80 outputs.
- The 4.3.1 closing report disclosed this only as: 'Prefix and isolation tests use a 40-session slice (last 15 sessions compared), not full-era recomputation. Formula checks against the independent oracle ran on one synthetic panel; only spot checks ran on real data. The delay-test replay used 3 rows per dataset, and its value-identity check holds partly by construction because the feature code never reads the availability field.'

## Correction #7: The closing report's statement about later development days and the evaluation period is false as worded.

Original statement (`section_4_3_closing_report_section4_20261031T011136Z.json`, `4541880b1ac88d866cab7119e148143871ee0678a68b08c2b8e06730a27b2bff`): Everything is TRAIN-only (LEGACY to 2018-12-21, RAW to 2024-12-23). The frozen development days after those dates, the boundary days around 2022-03-04/07 and the evaluation period were never in an audited or analysed span.

- The 4.3.1 builder (summary created 2026-10-29T03:32:18.785324+00:00) built 1875150 LEGACY rows (2003-01-02 to 2022-03-04, 4827 sessions) and 275820 RAW rows (2022-03-07 to 2024-12-31, 710 sessions): 2150970 rows.
- The 4.3.1 closing report records the same total: '35 candidate features built on the development rows (REPORT.md: 2,150,970 minute rows)'.
- The manifest puts LEGACY 2018-12-24 to 2018-12-31 in EMBARGO (5 sessions) and 2019-01-02 to 2022-03-04 in EVALUATION_EXPOSED (800 sessions); RAW EMBARGO is 2024-12-24 to 2024-12-31 (5 sessions) and RAW EVALUATION_EXPOSED starts 2025-01-02.
- The builder's yearly coverage table (builder_feature_coverage_development.csv) lists LEGACY years 2003 to 2022 and RAW years 2022 to 2024, so features for LEGACY 2019-2022 and the RAW embargo days were built and summarised by year.

Corrected statement: The LEGACY sessions 2018-12-24 to 2022-03-04 and the RAW embargo sessions 2024-12-24 to 2024-12-31 were inside the span on which the 4.3.1 builder constructed features and summarised coverage by year. Steps 3 to 6 and Sections 4.3.4 to 4.3.9 used TRAIN rows only. No feature matrix was built for the RAW evaluation period (2025-01-02 onward): the builder's runs end at 2024-12-31.
