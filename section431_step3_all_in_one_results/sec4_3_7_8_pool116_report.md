# 4.3.7 and 4.3.8 on the 116-column pool (A3 unchanged, note N2)

Run 2026-10-31T01:33:29.652176+00:00 UTC. TRAIN only, RAW then LEGACY. N2 `note_4_3_N2_20261031T011552Z.json` SHA-256 `3f5b7978e642298ad70a91dfafd8ebaa77504bb2bc1da5f2fb12990759d28e34`.

| Set | Pool | Kept | Dropped | Kept (raw / adjusted) | Dropped (raw / adjusted) |
|---|---|---|---|---|---|
| Primary | 30 | 15 | 15 | 14 / 1 | 6 / 9 |
| RAW sensitivity | 116 | 68 | 48 | 58 / 10 | 22 / 26 |

4.3.7: PASS. 4.3.8: PASS. Overall: **PASS**.

## Primary set kept

intrabar_range_log, raw_volume, raw_volume__sadj, relative_volume20, close_location_proxy, return_1m, abs_return_1m, momentum5_endpoint, rv5_strict, downside5_strict, momentum10_endpoint, rv10_partial90, downside10_strict, momentum15_endpoint, momentum30_endpoint

## Primary set dropped

- log_raw_volume: redundant with raw_volume (rho 1.0, LEGACY)
- intrabar_range_log__sadj: redundant with intrabar_range_log (rho 0.959782, LEGACY)
- log_relative_volume20: redundant with relative_volume20 (rho 1.0, LEGACY)
- relative_volume20__sadj: redundant with relative_volume20 (rho 0.999955, LEGACY)
- abs_return_1m__sadj: redundant with abs_return_1m (rho 0.977563, LEGACY)
- momentum5_strict: redundant with momentum5_endpoint (rho 0.999803, LEGACY)
- rv5_partial90: redundant with rv5_strict (rho 1.0, LEGACY)
- rv5_strict__sadj: redundant with rv5_strict (rho 0.961812, LEGACY)
- downside5_strict__sadj: redundant with downside5_strict (rho 0.975438, LEGACY)
- rv5_partial90__sadj: redundant with rv5_strict (rho 0.961812, LEGACY)
- rv10_partial90__sadj: redundant with rv10_partial90 (rho 0.957999, LEGACY)
- rv10_strict: redundant with rv10_partial90 (rho 1.0, LEGACY)
- momentum10_strict: redundant with momentum10_endpoint (rho 0.999935, LEGACY)
- rv10_strict__sadj: redundant with rv10_partial90 (rho 0.958128, LEGACY)
- downside10_strict__sadj: redundant with downside10_strict (rho 0.967047, LEGACY)

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
