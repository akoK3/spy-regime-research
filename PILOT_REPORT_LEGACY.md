# Machinery pilot, smallest LEGACY fold (LEGACY fold 29)

Written 2026-11-01. Same design and checks as `PILOT_REPORT_A7.md` (Amendment A7 thresholds, A6 rules), LEGACY fold 29: 189 train / 58 validation / 111 test sessions (after the 5-session embargoes). Fixed a-priori sets, K = 3, lambda = 39. TRAIN sessions only (LEGACY 2003-01-02..2018-12-21); no evaluation-period data, no selection, no protocol change. Machinery outputs, not evidence. Script `section5/s5_legacy_pilot.py`; results `section5/results/legacy_pilot_results_run_1793580880.json`, `legacy_build.json`, `legacy_mem.json`, `legacy_resume_check.json`.

## Checks: 25 of 25 PASS
- Exclusions: 12/12 (pools 19 and 80, fixed sets, TRAIN/LEGACY only, 7 negative controls rejected).
- Fold isolation: 5/5 (segments disjoint and ordered, embargo > 5 sessions, dates match the fold table, no later session used; Prep and deseasonalisation fit on inner train are identical when every later session's features are overwritten with 1e9).
- Missing data: finite inputs at all real updates (train/val/test: 0 non-finite); all detector outputs finite on validation; no alarm confirmed on a skipped update.
- Causal availability: deseasonalisation scale ignores later sessions; filtered output independent of later updates (8 detectors); alarm time = bar stamp + 1 min and hold respected (314 events); splice integrity on real LEGACY data (3 splices x 8 checks).
- Checkpoint recovery: run 1 killed externally (`taskkill /F /T`) with 6 of 18 splice chunks, 8 fits and 8 bisections stored (22 checkpoint files, no partial `.tmp`); run 2 resumed with 34 checkpoint hits and 20 new units (12 chunks, 8 sweeps). Five splices of a chunk stored by the killed run equal a fresh recomputation exactly. Not done: a full uninterrupted comparison run.

## Missing data in this fold
- 3 of 358 fold sessions are short (early close); 235 have < 98% finite closes (minimum 91.5%); 4.3% of fold bars are flagged invalid.
- Skipped decision updates: base set 5.4-6.5%, 3-feature set 9.0-10.2%.
- Stable days (A6 definition; needs >= 98% finite closes): 7 validation, 11 test (>= 8, so H1(a) is evaluable here). Many LEGACY folds may fall below 8; not measured.

## Results (machinery, not interpreted)
| detector | threshold (A7) | val rate | test rate realized | pAUC all | hit @0.1 | hit @0.2 |
|---|---|---|---|---|---|---|
| gaussian_hmm base | 3.31 | 0.19 | 0.31 | 0.167 | 0.13 | 0.17 |
| gaussian_hmm f3 | 9.21 | 0.19 | 0.31 | 0.266 | 0.21 | 0.28 |
| student_t_hmm base | 4.10 | 0.19 | 0.31 | 0.167 | 0.13 | 0.19 |
| student_t_hmm f3 | 6.94 | 0.19 | 0.33 | 0.280 | 0.26 | 0.29 |
| hsmm base | 3.82 | 0.19 | 0.29 | 0.164 | 0.13 | 0.17 |
| hsmm f3 | 10.73 | 0.19 | 0.25 | 0.271 | 0.23 | 0.30 |
| bocpd base | m = 36.2 | 0.19 | 0.18 | 0.100 | 0.02 | 0.11 |
| bocpd f3 | m = 44.2 | 0.19 | 0.20 | 0.169 | 0.02 | 0.11 |

All 8 bisections converged (none flagged); run-2 rule feasible for all 8. Test-session rates exceed the 0.2 target by 0.05-0.13 for the HMM/HSMM detectors (A7 RAW pilot: 0.13-0.30). hit(0.2) >= hit(0.1) everywhere.

## Timing, memory
| item | value |
|---|---|
| One-time LEGACY feature build (1,562,460 rows, 4,022 sessions) | 1,108 s = 18.5 min (19 features + LM: 562 s; `__sadj` bases: 542 s; ret5 matrix + deseasonalised variance: 4 s); caches 238 + 72 MB |
| Build peak memory | 1,668 MB |
| Machinery run (excluding build) | 3.9 min resumed segment; 2 workers; load from cache 14 s, 8 fits 5.3 s (HSMM base 3.3 s), bisections 4 s, vectorised sweeps 24 s |
| Splice features | 1,704 splices; about 84 s (6 chunks, run 1) + 165 s (12 chunks, run 2) on 2 workers; about 0.29 s per splice CPU (estimate; RAW 0.23) |
| Peak memory, run | parent 1,516 MB, each of 2 workers 806 MB; system free RAM fell from about 3.0 GB to 560 MB |

## Failures and choices
- Workers: 2, not 3. Three workers would need about 0.8 GB more than the free RAM left (560 MB minimum with 2). The user's limit is "at most 3".
- No check failed. Nothing excluded. No protocol change.

## Revised full-run projection (estimates; selection times carried over from `READOUT_AND_PROJECTION_A7.md`, not measured on LEGACY)
- Per LEGACY fold CPU: splices about 500 s + fixed stages about 35 s + selection 179 s = about 715 s (about 950 s with BOCPD selection). RAW folds: 608 s (841 s).
- 30 LEGACY + 4 RAW: about 6.7 CPU h (8.9 h with BOCPD selection). Wall on 2 workers (memory-bound; assumed speedup about 1.9): about 3.5 h (4.7 h). The earlier 4-worker figure (1.8-2.4 h) does not apply to LEGACY.
- One-time LEGACY build 18.5 min is already done and cached.
- The H1(a) evaluability rule (>= 8 stable test days) may exclude LEGACY folds with fewer stable days; not measured for the other 29 folds.
