# Amendment A14.1 to AMENDMENT_A14.md (one more undocumented guard)

Dated 2026-11-04T00:21:18.357421+00:00 UTC (2026-11-03T19:21:18.357421-05:00 New York). Status: ADOPTED when committed with its hash sidecar. Facts only.

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A14.md` | `1707ec30b9ad3f1a9b76d70e63807b92dd37179e47288191982677bed83709de` |
| `section5/s5_models.py` (before this change) | `837b2c9206c91ae3ff472bd7652866a6c91a2ec3c07acdce318edfda0505a640` |

- Found while testing A14: the three EM M-steps divide by state weights with a numerical guard (`weight + 1e-12`: Gaussian HMM and Student-t HMM state weights, Student-t scale weights, HSMM state weights) and the Student-t occupancy is computed with `max(total weight, 1e-12)`. A14 listed the 1e-12 added to initial-state and transition counts but not these denominator guards.
- Documented now as `WEIGHT_GUARD = 1e-12` in `s5_models.py`, used at all five places; values and results unchanged; a unit test fixes the value and that no bare 1e-12 remains outside the named constants.

## Governs

The constant and its test only.
