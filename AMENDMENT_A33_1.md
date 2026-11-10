# Amendment A33.1 (H2 synthetic check: planted shift raised from 0.05 to 0.08 per minute)

Dated 2026-11-10T22:17:30+00:00 UTC (2026-11-10T17:17:30-05:00 New York). Status: ADOPTED 2026-11-10T22:17:36Z (user decision 2026-11-10: "Option 1: amend A33 to plant 0.08 per minute"; the draft, sha256 b97305ad8985fd02..., is unchanged apart from this status line). Written before its code.
- **Decided by the user on 2026-11-10:** "Option 1: amend A33 to plant 0.08 per minute, criteria unchanged, disclose that it was raised after the 75% result, keep the 0.05 result on record. Rerun the synthetic check, then continue the chain (power, H2 dev run on Gaussian and HSMM). Stop if any check fails."
- **Disclosed: this size was raised after the first run had been seen.**
  - The first A33 rule 3 run, with c = 0.05, failed one criterion: planted TLT was rejected in 75% of replicates, against the required 80%.
  - Every other criterion passed: null rejection 4.5-7.5%, and planted bias within tolerance for TLT, HYG and gold.
  - That run stays on record, unchanged: `section6/results/h2_50_synth_a33.json` and `h2_50_synth_check_a33.json`.
- No H2 statistic has been computed on real data. No freeze, no O8, no era calibration.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A33.md` (ADOPTED; rule 3b planted shift c = 0.05) | `f101adce416ed256499fe779f5c0152de4c26d6bfbd9324a7a2546ecf9506747` |
| `section6/results/h2_50_synth_a33.json` (first run, c = 0.05) | `c3ad69930d75add50568e3fd8fcd4c6f8ca9132a2077dbc2d3e9718867835818` |
| `section6/results/h2_50_synth_check_a33.json` (FAIL: TLT 0.75 < 0.80) | `2e56c83c777e0cce682deeac41c5fa19aa7392861104e993a20e380fa5f174c4` |

## Rule 1

1a. **The only change.** A33 rule 3b's planted shift becomes c = +0.08 for TLT, -0.08 for HYG, +0.08 for gold, and 0 for USD (a planted null), times the generator's base one-minute SD. The target is 30 x mu_a, as before.
1b. **Unchanged:** the generator, the replicate counts (200 null per generator, 40 planted), the 10,000 draws and the rule 3c criteria.
1c. The rerun uses a new tag (a33p08). The chain continues to power and the H2 development run only if it passes. The development run requires A28-A33 and A33.1 ADOPTED.

## Governs

The planted effect size of the H2 synthetic check. Everything else in A33 is unchanged.
