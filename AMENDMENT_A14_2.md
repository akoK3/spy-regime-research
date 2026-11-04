# Amendment A14.2 to AMENDMENT_A14.md (Student-t start selection and flagged fits; decides the open choice of finding 19)

Dated 2026-11-04T00:27:53.564003+00:00 UTC (2026-11-03T19:27:53.564003-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Decided by the user after A14 left the choice open. Facts only.

## Evidence cited (hashes before this amendment's changes)

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `82bc1c81527128fe35249c0e9d5d31ec6174e9f882b6e977d04f5edc00cda56f` |
| `AMENDMENT_A14.md` | `1707ec30b9ad3f1a9b76d70e63807b92dd37179e47288191982677bed83709de` |
| `AMENDMENT_A14_1.md` | `d7cdaef27c572a4890aaf7306b2dc5f5f4a674bb58b8120e200062d81bd95ada` |
| `OPEN_AUDIT_FINDINGS.md` | `5fa9d38452a760c055beca1fc1a9e37d6decede12486124d86181cc85a437ee7` |
| `section5/s5_models.py` | `0ac30d807db251d709032b1f69b397881528766fe406b15d6a46df236847037d` |
| `section5/s5_h1.py` | `77abab1f748237a4f95e298c19d3d0f6634cea74874099a54941799ac2a99f1d` |
| `section5/s5_backend.py` | `c3eacc10bda7932f32161f63c49633f09570d49bd029140c02fcd18021e75267` |
| `section5/s5_run.py` | `9119bbf2b6a1fa3b9c5369f66c6816094adb5444bf384f2357b199a8ac1b0603` |
| `section5/s5_tests_a14.py` | `94b718848abc31a427fcc61aaae9e91a71445eee183896705eaf4934853d577f` |

## Rule

- Why: 5.4 restarts a Student-t HMM start whose fit leaves a state under 1% occupancy; A14 recorded when that fails but left open which start to keep. Evidence that it is rare: 1 of 80 inner-train fits on RAW 3 and LEGACY 29 needed any restart and none was kept with a state under 1% (A14, `OPEN_AUDIT_FINDINGS.md` finding 19).
- Among the starts of one fit, the kept fit is the one with the highest final log-likelihood among the starts whose kept attempt satisfies the 1% rule (every state at 1% or more). If no start satisfies the rule after its 10 attempts, the fit with the highest log-likelihood is kept and flagged (`kept_fit_occupancy_ok` = False). Before: the highest log-likelihood regardless of the rule.
- Reporting: every machinery and run report states the number of Student-t fits that are flagged (kept fits failing the rule) and the number of starts that failed it.
- Sensitivity excluding flagged fits (H1, Student-t HMM): the backend marks a fold's Student-t result as flagged if the kept feature model or the kept baseline model of that fold is flagged; `family_result` adds a third analysis, 'excluding_flagged_fits', computed on the confirmatory folds that are not flagged (same tests as the confirmatory analysis). The confirmatory analysis itself is not changed by flags. Other families have no flags.

## Governs

The start-selection change in `s5_models.py`, the flag plumbing in `s5_backend.py`, `s5_run.py` and `s5_h1.py`, unit tests, the protocol re-freeze (previous text preserved as `SECTION5_PROTOCOL_v5_FROZEN_A14_1.md`) and ledger rows. Finding 19 is then resolved. No evaluation data, no clean fold.
