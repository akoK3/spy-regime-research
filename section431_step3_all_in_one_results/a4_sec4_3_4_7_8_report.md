# 4.3.4, 4.3.7, 4.3.8 rerun under amendment A4 (causal seasonal baseline, 113-column pool)

Run 2026-10-31T02:52:21.954763+00:00 UTC. TRAIN only, RAW then LEGACY. A4 `amendment_4_3_A4_20261031T021111Z.json` SHA-256 `1960e83752b4dd5fa25dd022792e8a57f89ba79e9c79df02a50fceba96747304`.

F2 (4.3.4 checks): PASS. 4.3.7: PASS. 4.3.8: PASS. F5 (pool): PASS. Overall: **PASS**.

| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |
|---|---|---|---|---|---|
| Primary | 27 | 19 | 8 | 13 / 6 | 5 / 3 |
| RAW sensitivity | 113 | 83 | 30 | 57 / 26 | 21 / 9 |

## Primary set kept

intrabar_range_log, relative_volume20, intrabar_range_log__sadj, close_location_proxy, return_1m, abs_return_1m, abs_return_1m__sadj, momentum5_endpoint, rv5_strict, downside5_strict, rv5_strict__sadj, downside5_strict__sadj, momentum10_endpoint, rv10_partial90, rv10_partial90__sadj, downside10_strict, downside10_strict__sadj, momentum15_endpoint, momentum30_endpoint

## Primary set dropped

- log_relative_volume20: redundant with relative_volume20 (rho 1.0, LEGACY)
- relative_volume20__sadj: redundant with relative_volume20 (rho 0.951956, LEGACY)
- momentum5_strict: redundant with momentum5_endpoint (rho 0.999803, LEGACY)
- rv5_partial90: redundant with rv5_strict (rho 1.0, LEGACY)
- rv5_partial90__sadj: redundant with rv5_strict__sadj (rho 1.0, LEGACY)
- rv10_strict: redundant with rv10_partial90 (rho 1.0, LEGACY)
- momentum10_strict: redundant with momentum10_endpoint (rho 0.999935, LEGACY)
- rv10_strict__sadj: redundant with rv10_partial90__sadj (rho 0.998166, LEGACY)

## Output hashes (SHA-256)

| Output | File | SHA-256 |
|---|---|---|
| 4.3.7 eligibility, 113-column pool | a4_sec4_3_7_eligibility.json | `e89db674ac5c1c9121f96cfe09cd425a0ea2ec5686f529ae3a66766e2371ceb5` |
| 4.3.8 redundancy outcome, 113-column pool | a4_sec4_3_8_redundancy.json | `9da732a157a8b566782a412990e55200e2d3cbfe76f7d6e5acfa19531309bc49` |
| Spearman, 113 columns, RAW | a4_sec4_3_8_spearman_RAW_pool.csv | `74de3e77644b459fadba946376c8a2b0f0b5118af8da48a423152a96decdca2d` |
| Spearman, primary pool, LEGACY | a4_sec4_3_8_spearman_primary_LEGACY.csv | `89e85888aed9aaf4dbc37476f32c43825e864d3a376ed4713648b5948f80119c` |
| pairwise overlap, RAW | a4_sec4_3_8_overlap_RAW_pool.csv | `dfc8358a2a5ab2414eac73b3b3469f7ce199f10a19adca57a809c633a6bccf44` |
| pairwise overlap, LEGACY primary pool | a4_sec4_3_8_overlap_primary_LEGACY.csv | `a5cc321dfa71cfaa7586407a44848c70f929cdb4bff911fa72219f06eea71aaf` |
| 4.3.4 checks and coverage, causal baseline | a4_sec4_3_4_checks.json | `e05e6588bb074cefdd2a3333f3e5d1b0f552839b57cfb876219e5364ffb2bd36` |
| pool matrix (113 rows) | a4_sec4_3_pool_matrix.csv | `91eca14d2d65cdcac05428c454e5a48ff434ac7a8220d1ea45ea0e3f6b254b50` |
