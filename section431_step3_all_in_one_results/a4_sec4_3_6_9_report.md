# 4.3.6 and 4.3.9 regenerated under A4 and A5

Run 2026-10-31T04:03:11.097056+00:00 UTC. TRAIN only, RAW then LEGACY. Pool: 78 raw + 35 adjusted = 113 columns. Overall: **PASS**.

- 4.3.6 (descriptive): 2147 rows (19 era-years x 113 columns).
- 4.3.9: 113-row matrix; primary view 27 rows (kept 19, dropped 8); sensitivity view 113 rows (kept 83, dropped 30).

| Check | Result |
|---|---|
| matrix has 113 rows: 78 raw + 35 adjusted | PASS |
| raw_volume, log_raw_volume, raw_volume__sadj, overnight_return_open are not in the matrix | PASS |
| primary kept = 19 and sensitivity kept = 83 | PASS |
| corrected A5 G3 sensitivity outcome equals the A4 outcome (the jump_variation change moved no column) | PASS |
| primary eligibility recomputed from the 4.3.6 coverage equals the A4 primary pool | PASS |
| matrix outcomes equal the A4 pool matrix (primary and sensitivity) | PASS |
| 4.3.6 has one row per era, year and pool column | PASS |
| coverage recomputed from the 4.3.6 data differs from the A4 run only for jump_variation_w__sadj, and the RAW values equal the corrected G3 file | PASS |
| sidecar hashes of the cited amendments, notes, policy, approval and closing reports verify | PASS |
| matrix has all A3 fields | PASS |

## Output hashes (SHA-256)

| File | SHA-256 |
|---|---|
| a4_sec4_3_6_yearly_median_iqr.csv | `23be1e91de96635303eb80b86e3ff9f7307e74c6286a81d40480ad6fcaa1d642` |
| a4_sec4_3_9_frozen_matrix.csv | `63fd07251f68f45df75ada3addea643c2c1b4a284b85306d551ffe9c592daf35` |
| a4_sec4_3_9_matrix_primary_view.csv | `74f2c14fe15b0b7957283e66624a6352bab26e731535053371b0f8fd51243f25` |
| a4_sec4_3_9_matrix_sensitivity_view.csv | `33f3cc2a9fcf8baa9ea53753375880a965377e23c88b65b4a76967255b14be53` |

## Input hashes (SHA-256)

| Input | File | SHA-256 |
|---|---|---|
| approval_of_A1 | approval_4_3_0_A1_20261031T003131Z.json | `312d9807c41b5f780126029c15bf64d25ad7b50d161287b94fae0cbbacae09ef` |
| A2 | amendment_4_3_1_A2_20261030T231344Z.json | `2e2beb61489203c62988fda83ec0b1b7696f2a4d3bb1aa7f68a85275cae93ad5` |
| A3 | amendment_4_3_A3_20261031T003719Z.json | `34ebab1c19e007e5318e8da3dcc4eab38ad03cd2547c0358b53c4c944983b94d` |
| A4 | amendment_4_3_A4_20261031T021111Z.json | `1960e83752b4dd5fa25dd022792e8a57f89ba79e9c79df02a50fceba96747304` |
| A5 | amendment_4_3_A5_20261031T023320Z.json | `2637654bac921c171935011a9bc7d22bd7c2168f786397c2b2376d0d0179c35b` |
| P1 | policy_4_3_1_P1_20261030T233123Z.json | `580b9c9c4f4df578ba3f4aeda61556d73d8aaed486ec7866a11f93eaf103f75c` |
| N1 | note_4_3_N1_20261031T011048Z.json | `0a5ab480a7c44b422af67e4912bd461c80d745e7bb527212dbb88d09a74357a1` |
| N2 | note_4_3_N2_20261031T011552Z.json | `3f5b7978e642298ad70a91dfafd8ebaa77504bb2bc1da5f2fb12990759d28e34` |
| N3 | note_4_3_N3_20261031T034021Z.json | `65e79a680c6eef72445f1186b3ff8b8603b1870a7d2121fba7dbc30dace0d024` |
| closing_report_4_3_1 | section_4_3_1_closing_report_20261031T002814Z.json | `f7cfb9f3ae39629319088f69b27156849a06c2c7349fae58453fd2969865515a` |
| closing_report_4_3 | section_4_3_closing_report_section4_20261031T011136Z.json | `4541880b1ac88d866cab7119e148143871ee0678a68b08c2b8e06730a27b2bff` |
| a4_4_3_4_checks | a4_sec4_3_4_checks.json | `e05e6588bb074cefdd2a3333f3e5d1b0f552839b57cfb876219e5364ffb2bd36` |
| a4_4_3_7_eligibility | a4_sec4_3_7_eligibility.json | `e89db674ac5c1c9121f96cfe09cd425a0ea2ec5686f529ae3a66766e2371ceb5` |
| a4_4_3_8_redundancy | a4_sec4_3_8_redundancy.json | `9da732a157a8b566782a412990e55200e2d3cbfe76f7d6e5acfa19531309bc49` |
| a4_4_3_8_spearman_RAW_pool | a4_sec4_3_8_spearman_RAW_pool.csv | `74de3e77644b459fadba946376c8a2b0f0b5118af8da48a423152a96decdca2d` |
| a4_4_3_8_spearman_primary_LEGACY | a4_sec4_3_8_spearman_primary_LEGACY.csv | `89e85888aed9aaf4dbc37476f32c43825e864d3a376ed4713648b5948f80119c` |
| a4_4_3_8_overlap_RAW_pool | a4_sec4_3_8_overlap_RAW_pool.csv | `dfc8358a2a5ab2414eac73b3b3469f7ce199f10a19adca57a809c633a6bccf44` |
| a4_4_3_8_overlap_primary_LEGACY | a4_sec4_3_8_overlap_primary_LEGACY.csv | `a5cc321dfa71cfaa7586407a44848c70f929cdb4bff911fa72219f06eea71aaf` |
| a4_pool_matrix | a4_sec4_3_pool_matrix.csv | `91eca14d2d65cdcac05428c454e5a48ff434ac7a8220d1ea45ea0e3f6b254b50` |
| a4_4_3_4_7_8_report | a4_sec4_3_4_7_8_report.json | `00386b4feacebbceba4c63e8f19012d8a97b15be60c86b79e9051974d2cef0ef` |
| a5_jump_variation_redundancy | a5_jump_variation_redundancy.json | `3cce89c71abdc1e8d6588e80e92482b599cc36126fecb914b836e7855be0f0e0` |
| a5_jump_variation_redundancy_corrected | a5_jump_variation_redundancy_corrected.json | `69f9846bda8f42064e31766f27fe8530931afac941e0efcd28ac0004a07f2f24` |
| a5_jump_variation_spearman_RAW_pool_corrected | a5_jump_variation_spearman_RAW_pool_corrected.csv | `0b8beeb9f1f88575533246b30bbd1c484a1afb09cf3d5bb3973c3101fab8c3c8` |
| 4_3_6_first_run_log | a4_sec4_3_6_run_log.txt | `2a349df420d127a704f171bd6ae6cec2fa4eae8348047288c242e6c92b8dc2ba` |
