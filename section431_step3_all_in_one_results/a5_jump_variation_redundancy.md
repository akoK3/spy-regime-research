# jump_variation scaling: redundancy rerun (A5 G3)

Status: **PASS**. Changed columns: jump_variation_15, jump_variation_30, jump_variation_60, jump_variation_15__sadj, jump_variation_30__sadj, jump_variation_60__sadj.

RAW sensitivity pool: kept 83 / dropped 30 (before: kept 83 / dropped 30). Newly kept: none. Newly dropped: none.
Primary pool contains a changed column: no -> unchanged (no jump_variation column is in the primary pool).

Bias check (simulated Gaussian windows, mean of RV - BV):

- w=15: unscaled 0.9934, scaled -0.007 (PASS)
- w=30: unscaled 0.9985, scaled -0.0024 (PASS)
- w=60: unscaled 1.0148, scaled 0.015 (PASS)
