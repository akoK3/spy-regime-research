# Section 4.3 closing report: addendum (116-column pool)

**SECTION_4_3_CLOSED** (unchanged; this adds results, it does not reopen the section)

Added 2026-10-31T01:34:02.519551+00:00 UTC (2026-10-30T21:34:02.519551-04:00 New York). The closing report `section_4_3_closing_report_section4_20261031T011136Z.json` (SHA-256 `4541880b1ac88d866cab7119e148143871ee0678a68b08c2b8e06730a27b2bff`) is not edited.

A3's 4.3.7 and 4.3.8 rules, unchanged, applied to the 116-column pool under note N2 (`note_4_3_N2_20261031T011552Z.json`, SHA-256 `3f5b7978e642298ad70a91dfafd8ebaa77504bb2bc1da5f2fb12990759d28e34`), which was committed before the run. 4.3.7: PASS. 4.3.8: PASS.

| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |
|---|---|---|---|---|---|
| Primary | 30 | 15 | 15 | 14 / 1 | 6 / 9 |
| RAW sensitivity | 116 | 68 | 48 | 58 / 10 | 22 / 26 |

Adjusted columns kept in the primary set: raw_volume__sadj. In the RAW sensitivity set: intrabar_range_log__sadj, raw_volume__sadj, rv15_partial90__sadj, amihud_15__sadj, volume_adjusted_range_15__sadj, bipower_30__sadj, amihud_30__sadj, volume_adjusted_range_30__sadj, rv60_partial90__sadj, amihud_60__sadj.

## Known limitations added

1. Eligibility: every adjusted column has its raw column's coverage in both eras (check PASS), so the primary pool is 30 columns: the 20 raw plus 10 adjusted counterparts of the primary scale features.
2. The tie-break position of the adjusted columns (80-115, raw wins ties) is the only element not in A3. It was decided by the repository owner, and it decides which member of a redundant raw/adjusted pair is kept.
3. Raw/adjusted correlations in RAW sit close to the 0.95 threshold for many pairs (12 of 36 lie between 0.94 and 0.96), so which adjusted columns survive depends on the threshold. Adjusted columns survive mainly for seasonally strong volume-type features.
4. Same TRAIN-only scope, medians and Spearman definition as the A3 run; the A3 limitations in the closing report remain in force.

## Output hashes (SHA-256)

| Output | File | SHA-256 |
|---|---|---|
| 4.3.7 pool eligibility | sec4_3_7_8_pool116_eligibility.json | `7dd15ee7dd3b56367826a6c079dfeab203956a80ebf72902f571a0825bf1c587` |
| 4.3.8 pool redundancy outcome | sec4_3_7_8_pool116_redundancy.json | `dae50c4a24373910799fcc98ecb777a1906a0370922afee31e033d3b07b5b6e5` |
| Spearman, 116 columns, RAW | sec4_3_7_8_pool116_spearman_RAW.csv | `43b442b49dcbfd28d6e358e04629fcb40ea43cddf0f3a2460502b68f3cec240d` |
| Spearman, primary pool, LEGACY | sec4_3_7_8_pool116_spearman_primary_LEGACY.csv | `d94080a7ad1023c2f913ba066828f5b08231180d103c7c68e0add5d79c66c2a2` |
| pairwise overlap, RAW | sec4_3_7_8_pool116_overlap_RAW.csv | `0df52213409026c53926c4bcd4957a875df0df8ea1e223d90b1371b51e5fbd3e` |
| pairwise overlap, LEGACY primary pool | sec4_3_7_8_pool116_overlap_primary_LEGACY.csv | `a928593b2a2590b833b23600b30f7c872740712e5def5f9026a73ffab945557c` |
| pool matrix (116 rows) | sec4_3_7_8_pool116_matrix.csv | `818904b452f03b51b150d48b827a48d134ed8206ca3217f8d989b39c5f3be7c5` |
| report | sec4_3_7_8_pool116_report.json | `ee0d431475dfb839e075448774c82e7ff1ae8c309c66e8d722ef06bd8fdcbe48` |
