# A8 item 1: R = 1 gate result: FAILED (stopped as specified)

Written 2026-11-02. Governed by `AMENDMENT_A8.md` (sha256 `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931`), committed before the code. Validation sessions only; seed 777; 200 alarm-rate nulls (N1), 200 hit nulls (N2), 200 R = 1 placebo breaks; pAUC over null alarm rate 0-0.5; pass = placebo pAUC inside the 95% bootstrap interval of the N2 pAUC. Scripts `section5/s5_a8_gate.py`, `section5/s5_fast.py` (`in_units_of_A`), `section5/s5_a6.py`; results `section5/results/a8_gate_{LEGACY29,RAW3}_seed777.json`.

| Fold | stable validation days | detectors inside | outside |
|---|---|---|---|
| LEGACY 29 | 7 | 4 of 8 | Student-t HMM f3 (placebo .089 vs null .010 [.001,.023]), HSMM f3 (.016 vs .037 [.019,.058]), BOCPD base (.030 vs .005 [.000,.015]), BOCPD f3 (.013 vs .055 [.030,.084]) |
| RAW 3 | 16 | 3 of 8 | Gaussian HMM base (.045 vs .017 [.005,.032]) and f3 (.018 vs .065 [.040,.095]), Student-t HMM f3, HSMM f3, BOCPD f3 |

All pAUCs are small (0.005-0.09, the chance level for this metric is about 0.03-0.05).

## What was fixed and checked
- f is now computed from B's post-tau variance in A's baseline units (`in_units_of_A`). Unit tests (34 run, 0 failures): A's own values in A's units equal the native deseasonalised variance; R = 1, 3 up and 3 down splices have a realised ratio of 1 (6 decimals) in the detector's units; `build_specs_safe` skips without error.
- Per-feature realised shifts (median |log ratio after/before|): placebo 0.125 (LEGACY 29) and 0.143 (RAW 3) against null 0.124 and 0.142; largest placebo shift 0.37 / 0.32 (`momentum30_endpoint`).

## Reading (inference, not tested)
- The direction changed from the audit's finding: with the fix the f3-minus-base pAUC gap at zero effect is -.017 / +.080 / -.004 (BOCPD -.017) on LEGACY 29 and -.026 / -.009 / -.012 (BOCPD -.008) on RAW 3, no longer positive across the board. The placebo now often scores below the null splices.
- The failures are mostly placebo below null, consistent with audit finding 8: null splices (two different stable days) carry natural variance shifts that the R = 1 placebo does not, so the two are not the same population. A null set of two days is not a valid zero-effect reference for this gate as written. The gate as defined fails; it was not re-drawn, relaxed or re-seeded.

## Stopped
Items 2-5 of A8 (contamination list code, H1(c) code) were not implemented; the amendment text stands. No change to the gate rule was made. Decision needed: how the zero-effect reference should be defined (e.g. placebo versus placebo, or placebo splices of the same day pair with R = 1 on both sides).
