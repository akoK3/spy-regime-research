# Sections 4.3.4-4.3.9 (amendment A3)

Run 2026-10-31T00:59:32.295378+00:00 UTC. A3 `amendment_4_3_A3_20261031T003719Z.json` SHA-256 `34ebab1c19e007e5318e8da3dcc4eab38ad03cd2547c0358b53c4c944983b94d`. TRAIN only, RAW then LEGACY.

| Section | Status | Result |
|---|---|---|
| 4.3.2/4.3.3 | CITED, NO WORK | A2, P1 and the 2026-10-29 synthetic audit are cited by hash |
| 4.3.4 Seasonality | PASS | 36 adjusted columns; per-slot median of every adjusted column equals 1 |
| 4.3.5 Stale closes | DESCRIPTIVE | RAW 5 flagged bars (0.0018% of grid rows, 0.0018% of observed); LEGACY 23188 (1.4841%, 1.5311%) |
| 4.3.6 Yearly median/IQR | DESCRIPTIVE | 2204 rows: 116 columns by era and year |
| 4.3.7 Eligibility | PASS | primary 20 columns; sensitivity 80 on RAW |
| 4.3.8 Redundancy | PASS | primary keep 14, drop 6; sensitivity (RAW) keep 58, drop 22 |
| 4.3.9 Frozen matrix | PASS | 80 rows, primary and sensitivity views |

Overall: **PASS**

## Readings stated

- 4.3.5 shares are given against both all TRAIN grid rows and observed bars (A3 does not name the denominator).
- 4.3.9: A3 specifies one matrix holding both sets; the primary and sensitivity matrices are views of it.

## Primary set: kept

intrabar_range_log, raw_volume, relative_volume20, close_location_proxy, return_1m, abs_return_1m, momentum5_endpoint, rv5_strict, downside5_strict, momentum10_endpoint, rv10_partial90, downside10_strict, momentum15_endpoint, momentum30_endpoint

## Primary set: dropped

- log_raw_volume: redundant with raw_volume (rho 1.0, LEGACY)
- log_relative_volume20: redundant with relative_volume20 (rho 1.0, LEGACY)
- momentum5_strict: redundant with momentum5_endpoint (rho 0.999803, LEGACY)
- rv5_partial90: redundant with rv5_strict (rho 1.0, LEGACY)
- rv10_strict: redundant with rv10_partial90 (rho 1.0, LEGACY)
- momentum10_strict: redundant with momentum10_endpoint (rho 0.999935, LEGACY)

## Sensitivity set (RAW, all 80): kept

intrabar_range_log, raw_volume, close_location_proxy, relative_volume20, return_1m, abs_return_1m, momentum5_endpoint, rv5_strict, downside5_strict, momentum10_endpoint, rv10_partial90, downside10_strict, momentum15_endpoint, downside15_partial90, bipower_15, jump_variation_15, drawdown_15, amihud_15, skew_15, kurtosis_excess_15, variance_ratio2_15, directional_efficiency_15, vol_of_vol_15, volume_variability_15, volume_adjusted_range_15, return_autocorr1_15, reversal_15, rv30_partial90, momentum30_endpoint, downside30_strict, jump_variation_30, drawdown_30, amihud_30, skew_30, kurtosis_excess_30, variance_ratio2_30, directional_efficiency_30, vol_of_vol_30, volume_variability_30, volume_adjusted_range_30, return_autocorr1_30, reversal_30, momentum60_endpoint, rv60_sampled5_exact, downside60_strict, jump_variation_60, drawdown_60, amihud_60, skew_60, kurtosis_excess_60, variance_ratio2_60, directional_efficiency_60, vol_of_vol_60, extreme_loss_60, volume_variability_60, volume_adjusted_range_60, reversal_60, lee_mykland_jump60

Dropped: 22 columns (see sec4_3_8_redundancy.json).

## Output hashes (SHA-256)

| Output | File | SHA-256 |
|---|---|---|
| 4.3.4 TRAIN median per slot, RAW | sec4_3_4_slot_medians_RAW.csv | `f5e32212641e956191742a591e7c92de1e33325d0199273bd9c28c3335a01db3` |
| 4.3.4 TRAIN median per slot, LEGACY | sec4_3_4_slot_medians_LEGACY.csv | `95b1f6518007bc978d551805fb01f648c2ece3ae1ed2aa337a80ca152d0e4237` |
| 4.3.5 flagged bars by era and year | sec4_3_5_stale_closes_by_year.csv | `562770c4124c720087e116bd717fee706f20f86081fd08d639a3f4b465ac7470` |
| 4.3.5 flagged bars by era and slot | sec4_3_5_stale_closes_by_slot.csv | `2793aa8ccc5c5c752995239ab3993c7ab79c53e5754102c615ab59860ca57edc` |
| 4.3.6 yearly median and IQR (80 raw + 36 adjusted columns) | sec4_3_6_yearly_median_iqr.csv | `d07b591a159f0803f623d5e33152023d356d3784bfc986d4cab795f4e65caf0a` |
| 4.3.7 eligibility sets | sec4_3_7_eligibility.json | `122e9544407d4bde5405921590ceb6fa8782409994357d839b850c12c1aacadd` |
| 4.3.8 Spearman, primary set, LEGACY | sec4_3_8_spearman_primary_LEGACY.csv | `8aae1dff6782c3172174690fd5a6506a5d207ea92f8f41077dcf4d6c50457f84` |
| 4.3.8 Spearman, all 80, RAW (primary RAW is a sub-block) | sec4_3_8_spearman_RAW_all80.csv | `e8c4658a2ca76ca34b94ae3dfd9adeae82cf1af258ba88679f4a5ccee7a98e7a` |
| 4.3.8 pairwise overlap counts, RAW | sec4_3_8_overlap_RAW_all80.csv | `388cc7eccf85dee768d1646954adffea95d6b957f0a89186702b16ffa1d793da` |
| 4.3.8 pairwise overlap counts, LEGACY primary | sec4_3_8_overlap_primary_LEGACY.csv | `e7d13c0092a782a9ec3a9cae6f645688add5552da9e7d70c601d2ad0eac6c9c8` |
| 4.3.8 redundancy outcome | sec4_3_8_redundancy.json | `babb83734529aaf3fb0b30daaa12ad3b5fdd87236da0fcf091ba3096879831fa` |
| 4.3.9 frozen matrix (A3: one matrix, both sets) | sec4_3_9_frozen_matrix.csv | `77aa2d92ac802faec9c5d251266eec600aa7243e5e5aad3763a316e8a4a2d2f8` |
| 4.3.9 primary view (20 eligible rows) | sec4_3_9_matrix_primary_view.csv | `39c72cfa6dfec66488c9addd65f9e2f8c1da8474fe4caeb3bac9b55eaf190d7d` |
| 4.3.9 sensitivity view (80 rows, RAW) | sec4_3_9_matrix_sensitivity_view.csv | `7fbd544faf9200e7de10a0d22068e8c7eb16daceae4fbd4eb2d58664f6e7309d` |
