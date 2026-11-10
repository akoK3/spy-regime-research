# Open audit findings, 2026-11-10 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`, `_v2_A14.md`, `_v3_A14_2.md`, `_v4_A15.md`, `_v5_A16.md`)

Written 2026-11-10T23:15:00Z (UTC). Sources:
- `section5_cold_audit.md` (audit 1);
- `section5_cold_audit_2.md` (audit 2, sha256 `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602`);
- `O9_AUDIT.md` (sha256 `8b31a38b23e21b6c2ffa0b7eaaa512c75e75d1cb475b493f265d6ff8f4407c8d`);
- `FABLE_AUDIT.md` (sha256 `005129986659b5827f94bf491f4120ae19db3ec674d25d78b50974f2ecc7db57`);
- `COLD_AUDIT_STATUS.md` (this date), which lists every finding with its status and the fixing amendment or commit.

Facts only. Resolved and disclosed findings are not repeated here.

## Summary

| Audit | Open | Resolved since the A16 list |
|---|---|---|
| Audit 1 | 6: 1 Medium (10), 5 Low (12, 16 partly, 18, 20, 21) | 13 (A22 rule 3c), 17 (data-hash preflight: commits 55cfc4e, 01ac960, 9124c67) |
| Audit 2 | 5, all Low (10, 11, 12, 13 partly, 15) | 14 (cache stamp and Section 6 cache: commit 9124c67) |
| O9 | 0 (M1, L1, L3, L8, L9 resolved; M2, M3, L2, L4-L7 disclosed in `SECTION5_DISCLOSED_LIMITATIONS.md`) | all, by A25 and commit f03a505 |
| Fable | 4, all Low (L2, L3, L7, L9) | M1-M4, L4-L6, L12 (commit 9124c67); M5, L1, L10 (AMENDMENT_A31); L5 (manifest, through A33.1) |

None of the open findings changes the primary H1 detection or QLIKE computation, or a Section 6 primary result as computed.

## Audit 1 (open)

| # | Severity | Finding | What it affects |
|---|---|---|---|
| 10 | Medium | Fold-level Lee-Mykland threshold never used (`s5_lib.py`) | The `lee_mykland_jump60` feature, in the RAW sensitivity set only. Primary H1 does not use it. |
| 12 | Low | '25 of 25 checks passed' overstates coverage | Record only. No test checks the splice builder for leakage. |
| 16 | Low | Seeds, library versions, abstention and skip shares, EM cap hits not recorded in run outputs | Reporting (5.3, 5.4). Partly addressed: A22 aggregates flagged Student-t fits (0). |
| 18 | Low | Student-t states ordered by scale, not variance | State labels in outputs only. Detection and QLIKE are not affected. |
| 20 | Low | Superseded code paths still live (`V.events_for`, hard-coded RAW in `s5_d2.py`) | Risk of accidental use. No current runner calls them. |
| 21 | Low | Sensitivity pool not limited to RAW in code | 5.10 sensitivity only. The A22 RAW-pool run used RAW only (its runner), but the code does not enforce it. |

## Audit 2 (open)

| # | Severity | Finding | What it affects |
|---|---|---|---|
| 10 | Low | Student-t keeps the last attempt, not the best, when all 10 attempts of a start fail | Only fits that end flagged. MR2 has 0 flagged fits (A22). |
| 11 | Low | Greedy selection adds features on non-finite QLIKE | Only a degenerate objective. |
| 12 | Low | H1 block bootstrap blocks can span LEGACY 26 -> RAW 0 | Section 5 H1 p-values (5.9). The result modules are frozen. Section 6 resamples within era. |
| 13 | Low | EM cap hits not in `run_summary.json` | Reporting. Partly addressed: flagged-fit counts aggregated by A22. |
| 15 | Low | 5.16 says the backend reads no session outside a fold's segments; it reads the whole era panel for past-session baselines | Record accuracy only. |

## Fable audit (open)

| # | Severity | Finding | What it affects |
|---|---|---|---|
| L2 | Low | Section 6 H3/H4 matched sets are split across bootstrap blocks; placebo rows can be duplicated | H3/H4 p-values, which are week-block resamples of rows. Not changed. |
| L3 | Low | The A26 rule 1d label is defined but never attached | Any evaluation-period output. None exists. The label must be attached before the joint run. |
| L7 | Low | Ledger integrity relies on git; dates come from the file's own stamp | Record dating. Two stamp errors were found and corrected by ledger rows on 2026-11-10. |
| L9 | Low | Rule 7c "FOMC days" are only the 98 H1(c)-eligible events | The Fed / non-Fed split in Section 6 (secondary) and A30 / E1 descriptions. |

## Also open, outside the audits (from the Section 6 development results)

- **The HYG data gap.** E1 and the A32 statistic use far fewer HYG breaks than the H2 primary. Diagnosed on 2026-11-10, label-free: see `reply_latest.md` and `section6/results/hyg_gap/`.
