# Amendment A14 to SECTION5_PROTOCOL.md (audit findings 19 and 22: documentation and reporting)

Dated 2026-11-04T00:19:49.802248+00:00 UTC (2026-11-03T19:19:49.802248-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Facts only.

## Evidence cited (hashes before this amendment's changes)

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `258e07d85aff0167ef44daa2577ba193e0cbad21997b359a7a3538427a3f3fb8` |
| `AMENDMENT_A13.md` | `301be6ed93fdf80d9a3841664faf8398d2a8b5d30073ad00ba9f88d20e7c5755` |
| `OPEN_AUDIT_FINDINGS.md` | `c9ab21ab5c395eaa157eb8d2a5683889189a507d49c407d23035eb5b380d169d` |
| `section5_cold_audit.md` | `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062` |
| `section5/s5_models.py` | `6b9cf16098003be764c116a57a622ffdc9cc20805691756185ba4b7378c502ac` |
| `section5/s5_eval.py` | `d37ea9b0fe6ecc6ae650790f67a4e1caf5512a2433b542ca1dfd7ec9b9af3ef6` |
| `section5/s5_fast.py` | `4c4bc525402d6d84aa7e889e59961ba9fa466b03c370246f6d6971f2eb03af33` |
| `PILOT_REPORT_LEGACY.md` | `8b4f675258ad85035a7e5286a8e5d237a9b24128b122a1bb0975426ca00f4901` |
| `section5/results/a14_student_t_occupancy_RAW3_K3.json` | `cc7def0227f81683a76ffb26a5e1041f6faf14a5caef78683339ab1e4467dbea` |
| `section5/results/a14_student_t_occupancy_RAW3_K4.json` | `f7db66b4d6b57361fcf5a850d2998831b59237caeb19adb0516a6732b64835b3` |
| `section5/results/a14_student_t_occupancy_LEGACY29_K3.json` | `25ef3328b2fc0e200d43b94c71687e8a1edc7f230d3aa29168d0ae6575485a3a` |
| `section5/results/a14_student_t_occupancy_LEGACY29_K4.json` | `921ce009f02e24671d8754b392bb92f9452c25e4a2b06232fa5baf114f1b320a` |

## Finding 22: parameters that exist in the code but not in the protocol (documentation; no behaviour change)

- HSMM hazard update (`s5_models.py`, M-step): for state k and elapsed duration d, h[k, d] = (leave[k, d] + 0.5 x h0) / (leave[k, d] + stay[k, d] + 0.5), where leave and stay are the expected counts of leaving and staying from the E-step and h0 = (sum of leave + 1e-9) / (sum of leave + sum of stay + 1e-9) is the pooled hazard. This is a pseudo-observation of weight 0.5 at the pooled hazard (smoothing of sparse duration bins). The last duration bin is set to 1 and h is clipped to [1e-6, 1].
- Floors: the initial-state and transition probabilities of all three EM models get +1e-12 before normalisation (HSMM transition: off-diagonal only); the emission variance floor 1e-6 is already in 5.4.
- Duration cap: the HSMM duration axis has Dmax = 78 bins of one grid interval (5 minutes). A full session has 78 decision updates (390 minutes / 5), so Dmax equals the session's scheduled updates for full sessions, as 5.4 requires. On early-close sessions fewer updates exist and durations beyond the session are unreachable; the cap is not shortened for them.
- These values are made named constants in `s5_models.py` (`HSMM_HAZARD_PSEUDO`, `HAZARD_CLIP`, `PROB_FLOOR`, `DUR_CAP`) and the hazard update becomes a function `hsmm_hazard_update`, with unit tests that fix the values and the formula; results are unchanged.
- Record gaps: the docstring of `s5_fast.py` credits the fast-versus-slow splice equivalence check to `s5_fixes.py`; it is in `s5_bench.py`; the docstring is corrected. `PILOT_REPORT_LEGACY.md` (closed record, not edited) has no writer script and no file hash table: the writer script cannot be recovered; `PILOT_REPORT_LEGACY_FILES.md` lists the hashes of the files it relies on as of this date, and states which code files have changed since the pilot.

## Finding 19: Student-t HMM restarts (reporting; one design choice left open)

- 5.4: restart if a state is under 1% occupancy. The code restarts with a new initialisation up to 10 attempts per start; if the 10th attempt still has a state under 1%, that fit is kept without a record of the failure.
- Measured on the inner-train data of the contaminated folds (`s5_a14_diag.py`, Student-t HMM, 1 start as in the greedy search, return-only model and each of the 19 single candidate features, K = 3 and K = 4 on RAW 3 and LEGACY 29): 1 of 80 fits needed any restart (LEGACY 29, K = 4); none used all 10 attempts; none was kept with a state under 1%. Multi-feature subsets and the 3-start tuning fits were not measured.
- Reporting fix (mechanical): `fit_info` records, per start, the number of attempts and whether the kept fit satisfies the 1% rule; the machinery and run reports state the number of starts that fail it. Behaviour is unchanged.
- **Not decided here (design choice, asked of the user):** what to do when all attempts fail: reject the fit (model unusable for that subset), keep it flagged (current behaviour), or raise the attempt cap; and whether a start that satisfies the rule should be preferred over a start with a higher likelihood that violates it. Until decided, the current behaviour stands and finding 19 stays open.

## Governs

The documentation, constants, docstring and reporting changes above, their unit tests, the protocol re-freeze (previous text preserved as `SECTION5_PROTOCOL_v4_FROZEN_A13.md`) and ledger rows. No change to any fitted value, detector rule or data. No evaluation data.
