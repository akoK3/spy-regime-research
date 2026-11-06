# Amendment A19.1 (D8b: sensitivity of the D8 census; under A19)

Dated 2026-11-06T19:02:00+00:00 UTC (2026-11-06T14:02:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before any D8b result and before its code. Decided by the user after D8. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A19.md` | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` |
| `section5/s5_d8.py` | `986f33aa1a03a992900591a2dff8ef1220ff9647ea54317b55abd15507584dc3` |
| `section5/results/d8/d8_results.json` | `540bfb5c924600811a7ac19a91c1bef64958eaf0c77b1080f74a7b2b8a0a7098` |

## Rule

1. Status: sensitivity only. D8's primary results and "occurs" verdicts (A19 rule 1f) stand and alone gate Step 2. D7's injection sizes (A19 rule 2c) are unchanged. D8b reports only whether any "occurs" verdict would change.
2. Everything as A19 rule 1 except one factor at a time (each variant against the D8 primary):
   - (S1) stricter "large": the i.i.d. two-sided 0.1% points instead of 1% (z = 3.291): trend |dt| >= 4.65 (= 3.291 sqrt 2); momentum |drho| >= 0.60 (= 3.291 sqrt(2/60)); liquidity VOL >= 3 or <= 1/3; jumps dJ >= 2.
   - (S2) window length w = 30 and w = 120 min: W = [s, s+w), P = [s-w, s), s on the 5-min grid from w to 390 - w; a window needs >= ceil(50 w / 60) finite returns in W and in P; t = sqrt(w) mean / sd; momentum threshold 2.576 sqrt(2/w) (30: 0.665; 120: 0.333); trend, liquidity, jump and variance-band thresholds unchanged.
   - (S3) LEGACY session completeness >= 90% finite closes (390 bars still required); RAW unchanged.
3. The "occurs" rule (P(large | variance-stable) >= 0.02 in both eras) is applied unchanged to each variant. Registry: DESCRIPTIVE (as D8).

## Governs

`section5/s5_d8b.py`; results `section5/results/d8/d8b_results.json`.
