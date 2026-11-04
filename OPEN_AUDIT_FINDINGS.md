# Open cold-audit findings after A16 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`, `_v2_A14.md`, `_v3_A14_2.md`, `_v4_A15.md`)

Written 2026-11-04T01:25:48.634155+00:00 UTC. Sources: `section5_cold_audit.md` (audit 1), `section5_cold_audit_2.md` (sha256 `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602`, with the re-audit after A15; the A15 version `700a09fc527f00d532021deafdcd725641b9eea900caf03065bcdc11f011d942` is its first part) (audit 2), `COLD_AUDIT_STATUS.md`. Reclassified by `AMENDMENT_A15.md` rule 7. Facts only.

## Audit 1

Eight findings are open: 3 Medium (10, 13, 17), 5 Low (12, 16, 18, 20, 21). Findings 3 and 11 were reopened by audit 2 and resolved by A15. None changes the primary H1 detection or QLIKE computation.

| # | Severity | Finding | What it affects |
|---|---|---|---|
| 10 | Medium | Fold-level Lee-Mykland threshold never used (`s5_lib.py:127,195-201`) | The `lee_mykland_jump60` feature uses the global simulated threshold, not the Student-t fit on the fold's inner train (5.1). Affects only the RAW sensitivity set (the flag is sensitivity-only, 5.2). Primary H1 does not use it. |
| 12 | Low | '25 of 25 checks passed' overstates coverage (`s5_legacy_pilot.py:127-140,187-188`, `s5_pilot.py:152-187`) | Record only: some pilot checks cannot fail and the splice integrity check never touches `regime_panel`. No effect on any computed result; the A10/A12 machinery checks add guards, resume and finiteness tests but not a leakage test of the splice builder. |
| 13 | Medium | +/-0.05 threshold robustness undefined under A7 (`SECTION5_PROTOCOL.md` 5.10) | Affects only the 5.10 robustness analysis: thresholds are log-odds (0-30) or a drop size, so '+/-0.05' has no meaning; the analysis cannot be run until an amendment defines it. |
| 16 | Low | Seeds, library versions, abstention and skip shares not recorded in run outputs (`s5_a7.py`, `s5_legacy_pilot.py`, `VERSIONS` unused) | Reporting and reproducibility of 5.3 (abstention and skip shares) and 5.4 (seeds, versions). Run summaries record the code version and EM `fit_info` but not these. No effect on results. A15 (wider scope): flagged Student-t fit counts and EM cap hits are not in `run_summary.json` either. |
| 17 | Medium | Input hashes not verified at run time (`s5_lib.py:58,149,112-117`) | Data provenance: the freeze records the hashes of the protocol, every integrated amendment, the cited inputs and the market-data files (A15 rule 6c), but the loaders do not verify the data files against them; a silent change of a data file between runs would not be caught. |
| 18 | Low | Student-t states ordered by scale, not variance (`s5_models.py:40,139`) | State labels in outputs (5.5 orders by return variance). The A6 event rule uses the argmax state and QLIKE state values do not depend on the order, so detection and QLIKE results are not affected; any report that names states by order would be. |
| 20 | Low | Superseded code paths still live (`V.events_for`, hard-coded RAW in `s5_d2.py` `_init`) | Risk of accidental use of the pre-A6 event rule or of RAW-only loading. The data backend and orchestration do not call them; only old pilot and diagnostic scripts do. |
| 21 | Low | Sensitivity pool not limited to RAW in code (`s5_lib.py:79-80`) | 5.10 sensitivity run only: a LEGACY run with the 80-column pool would be accepted although 5.2 limits it to RAW. Primary analysis unaffected. |

Disclosed (problem remains, stated in a dated record): 1 (residual: the R=1 gate failed on LEGACY 29, protocol 5.15), 2, 5, 8; resolved with a disclosed remainder: 4 (gap handling in the block bootstrap).

## Audit 2

Six findings are open, all Low (10-15). The re-audit's new problems (findings 16-21) are resolved by A16. None changes the primary H1 detection or QLIKE computation; 12 concerns the H1 p-value (block bootstrap) and extends the disclosed remainder of audit 1 finding 4.

| # | Severity | Finding | What it affects |
|---|---|---|---|
| 10 | Low | Student-t keeps the last attempt, not the best, when all 10 attempts of a start fail (`s5_models.py:198-209`) | Only fits that end flagged (A14.2); those are counted and excluded in the 5.10 sensitivity. |
| 11 | Low | Greedy selection adds features when QLIKE is non-finite (`s5_select.py:37-38`) | Only a degenerate objective (all losses infinite). |
| 12 | Low | Block bootstrap blocks can span LEGACY 26 -> RAW 0 (`s5_h1.py`) | H1 p-values (5.9); same class as audit 1 finding 4's remainder. |
| 13 | Low | Flagged-fit counts and EM cap hits not in `run_summary.json` (`s5_run.py`) | Reporting (5.4); per-fold scores carry the flags. |
| 14 | Low | Feature caches `{era}_features.npz`, `{era}_bases.npz` keyed by column name only (`s5_lib.py:112-116`, `s5_fast.py:16-23`) | A change of feature code or panel would reuse cached columns. |
| 15 | Low | 5.16 says the backend reads no session outside a fold's segments; it reads the whole era panel for past-session baselines | Record accuracy only; no model is fitted outside the fold's inner train. |
