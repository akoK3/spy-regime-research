# Prefix and isolation rerun (A4 F4)

Run 2026-10-31T03:27:07.630373+00:00 UTC. Relative tolerance rtol 1e-9, atol 0. Overall: **PASS**.

| Test | Status |
|---|---|
| RAW prefix (relative tolerance, session-end and mid-session cuts) | PASS |
| RAW isolation (full-session and mid-session blanking) | PASS |
| RAW tolerance power check (1e-6 relative error detected) | PASS |
| LEGACY prefix (relative tolerance, session-end and mid-session cuts) | PASS |
| LEGACY isolation (full-session and mid-session blanking) | PASS |
| LEGACY tolerance power check (1e-6 relative error detected) | PASS |

## RAW

Prefix cuts: {'session_end': 5, 'mid_session': 5}. Rows compared per cut: 5670-5850.
Isolation blankings: 8. Power check: 81 features, not detectable: none.

## LEGACY

Prefix cuts: {'session_end': 5, 'mid_session': 5}. Rows compared per cut: 5550-5850.
Isolation blankings: 8. Power check: 81 features, not detectable: none.
