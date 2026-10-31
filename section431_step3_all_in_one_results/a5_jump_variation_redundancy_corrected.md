# A5 G3 redundancy: corrected run

Status: **PASS**. Step 13 ranked columns by the A4-run coverage. After the w/(w-1) scaling about half of the jump_variation values are exactly 0, so the median baseline is 0 on many slots and jump_variation_w__sadj is undefined there; its coverage fell. The corrected run uses the coverage of the current data.

Share of exactly-zero values among finite RAW values: {'jump_variation_15': 0.4941, 'jump_variation_30': 0.4663, 'jump_variation_60': 0.4348}.

RAW coverage changes (percent): jump_variation_15__sadj: 86.82 -> 55.836; jump_variation_30__sadj: 80.579 -> 61.209; jump_variation_60__sadj: 72.342 -> 61.527

RAW sensitivity (113 columns): kept 83 / dropped 30. A4 run: kept 83 / dropped 30. Original G3: kept 83 / dropped 30.
Changes versus the A4 run: newly kept none; newly dropped none.
Changes versus the original G3 result: newly kept none; newly dropped none.

Primary set: unchanged: no jump_variation column is in the primary pool.
