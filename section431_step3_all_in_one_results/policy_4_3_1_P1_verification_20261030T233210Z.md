| Rule / test | Status | Failed checks |
|---|---|---|
| R1 usable at t+1 minute | PASS | - |
| R2 session reset | PASS | - |
| R3 no LEGACY/RAW crossing | PASS | - |
| R4 overnight excluded | PASS | - |
| delay by 1 minute shifts every feature exactly 1 bar: synthetic panel | FAIL | rv10_partial90, rv15_partial90, rv30_partial90, rv60_partial90, downside15_partial90 |
| delay by 1 minute shifts every feature exactly 1 bar: RAW 40-session slice | FAIL | relative_volume20, log_relative_volume20, rv10_partial90, rv15_partial90, rv30_partial90, rv60_partial90 |
| delay by 1 minute shifts every feature exactly 1 bar: LEGACY 40-session slice | FAIL | rv10_partial90, rv15_partial90, rv30_partial90, rv60_partial90, downside15_partial90 |
