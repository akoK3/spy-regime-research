# Open cold-audit findings after A14 (the A13 list is preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`)

Written 2026-11-03T23:41:52.081352+00:00 UTC. Source: `section5_cold_audit.md` (sha256 `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062`) and `COLD_AUDIT_STATUS.md` (sha256 `ddcaf3538968b31f551c183ee95a53ad3d50891c2635e1f2aa9b0a8f983c762b`). Written under `AMENDMENT_A13.md` item 3. Facts only; none of these is fixed by A13.

Nine findings are open after A14: 3 Medium, 6 Low (22 was resolved by A14/A14.1). None changes the primary H1 detection or QLIKE computation except possibly 19 (Student-t fits).

| # | Severity | Finding | What it affects |
|---|---|---|---|
| 10 | Medium | Fold-level Lee-Mykland threshold never used (`s5_lib.py:127,195-201`) | The `lee_mykland_jump60` feature uses the global simulated threshold, not the Student-t fit on the fold's inner train (5.1). Affects only the RAW sensitivity set (the flag is sensitivity-only, 5.2). Primary H1 does not use it. |
| 12 | Medium | '25 of 25 checks passed' overstates coverage (`s5_legacy_pilot.py:127-140,187-188`, `s5_pilot.py:152-187`) | Record only: some pilot checks cannot fail and the splice integrity check never touches `regime_panel`. No effect on any computed result; the A10/A12 machinery checks add guards, resume and finiteness tests but not a leakage test of the splice builder. |
| 13 | Medium | +/-0.05 threshold robustness undefined under A7 (`SECTION5_PROTOCOL.md` 5.10) | Affects only the 5.10 robustness analysis: thresholds are log-odds (0-30) or a drop size, so '+/-0.05' has no meaning; the analysis cannot be run until an amendment defines it. |
| 16 | Low | Seeds, library versions, abstention and skip shares not recorded in run outputs (`s5_a7.py`, `s5_legacy_pilot.py`, `VERSIONS` unused) | Reporting and reproducibility of 5.3 (abstention and skip shares) and 5.4 (seeds, versions). Run summaries record the code version and EM `fit_info` but not these. No effect on results. |
| 17 | Low | Input hashes not verified at run time (`s5_lib.py:58,149,112-117`) | Data provenance: the protocol cites inputs by hash but the loaders do not check them; the backend records hashes for the freeze only. All hashes matched when checked by hand (audit); a silent change of a data file would not be caught. |
| 18 | Low | Student-t states ordered by scale, not variance (`s5_models.py:40,139`) | State labels in outputs (5.5 orders by return variance). The A6 event rule uses the argmax state and QLIKE state values do not depend on the order, so detection and QLIKE results are not affected; any report that names states by order would be. |
| 19 | Low | A bad Student-t start can win silently (`s5_models.py`) | Student-t HMM fit quality. A14 records per-start attempts and the 1% occupancy flag (reporting). Measured on 80 inner-train fits of the contaminated folds: 1 restart, none exhausted, none kept with a state under 1%. Open design choice: behaviour when all 10 attempts fail, and whether a valid start is preferred over a higher-likelihood violating start. |
| 20 | Low | Superseded code paths still live (`V.events_for`, hard-coded RAW in `s5_d2.py` `_init`) | Risk of accidental use of the pre-A6 event rule or of RAW-only loading. The data backend and orchestration do not call them; only old pilot and diagnostic scripts do. |
| 21 | Low | Sensitivity pool not limited to RAW in code (`s5_lib.py:79-80`) | 5.10 sensitivity run only: a LEGACY run with the 80-column pool would be accepted although 5.2 limits it to RAW. Primary analysis unaffected. |

Disclosed (problem remains, stated in a dated record): 1 (residual: the R=1 gate failed on LEGACY 29, protocol 5.15), 2, 4 (gap handling in the block bootstrap), 5, 8.
