# A4 results report

Written 2026-10-31T03:34:15.476840+00:00 UTC (2026-10-30T23:34:15.476840-04:00 New York). A4 `amendment_4_3_A4_20261031T021111Z.json` SHA-256 `1960e83752b4dd5fa25dd022792e8a57f89ba79e9c79df02a50fceba96747304`. Overall: **PASS**.

| Item | Status | Detail | Evidence |
|---|---|---|---|
| 1 F1 folds (#2) | PASS | LEGACY 30 folds, RAW 4 folds from TRAIN only; sessions touching EMBARGO/EVALUATION_EXPOSED/EXCLUDED: 0 and 0. The frozen v2 file had 36 LEGACY folds (7 with a window after TRAIN) and 4 RAW folds (1 with a window after TRAIN). | a4_folds_check.json |
| 2 F2 seasonal baseline (#1): 4.3.4, 4.3.7, 4.3.8 | PASS | 4.3.4 PASS (brute-force cells per era 105000, mismatches 0); 4.3.7 PASS, primary pool 27; 4.3.8 PASS: primary keep 19 (raw 13, adjusted 6) / drop 8; RAW sensitivity pool 113 keep 83 (raw 57, adjusted 26) / drop 30. | a4_sec4_3_4_7_8_report.json |
| 3 F3 Lee-Mykland threshold (#5) | PASS | threshold 4.6113 (95% CI 4.5998 to 4.6245); false-alarm rate at the threshold 1.0005% (seed 43105) and 1.0400% (seed 43106); the old 5.4667 flags 0.0655%. Step 3 formula check on the current code: PASS, 81/81, independent simulated false-alarm rate 0.9900%. | a4_lm_threshold_calibration.json |
| 4 F4 tolerances and mid-session cuts (#8, #9) | PASS | RAW prefix (relative tolerance, session-end and mid-session cuts): PASS; RAW isolation (full-session and mid-session blanking): PASS; RAW tolerance power check (1e-6 relative error detected): PASS; LEGACY prefix (relative tolerance, session-end and mid-session cuts): PASS; LEGACY isolation (full-session and mid-session blanking): PASS; LEGACY tolerance power check (1e-6 relative error detected): PASS. Relative tolerance rtol 1e-9, atol 0. Run once per era in separate processes (each era with its own fixed seed) to limit memory; features were spilled to float64 files, float32 was not used because it would coarsen the tolerance. | a4_prefix_isolation_report.json |
| 5 F5 protocol conflicts (#10) | PASS | raw_volume, log_raw_volume and raw_volume__sadj are out of the detector set; pool 78 raw + 35 adjusted = 113. The rv10 proposal is approved in amendment A5 (G5). In the A4 primary run rv10_strict is: dropped: redundant with rv10_partial90. | a4_sec4_3_4_7_8_report.json |
| 6 F6 addendum for #3, #4, #6, #7 | PASS | section_4_3_closing_report_addendum_audit_20261031T025306Z.json; the closed reports are unchanged; every number is read from a file. | section_4_3_closing_report_addendum_audit_20261031T025306Z.json |
| 7 F7 cleanup (#12) | PASS | a_in_repository_inputs: PASS; b_own_temp_directory: PASS; c_overwrite_guards: PASS; d_computed_hash_check: PASS; scripts_compile: PASS; e_step5_v2_hash_file_matches_current_files: PASS. step5_final_sha256.txt (the v1 state) no longer matches: ['step5_policy.py', 'step5_delay_diagnosis.py']; step5_v2_final_sha256.txt matches all current files. The older file is left unedited. | step5_v2_final_sha256.txt |

## History

- The first F2/F5 rerun was killed during the LEGACY feature pass (no outputs); a restart failed on this repository's own overwrite guard (a kept log matched its pattern, no analysis ran); the third attempt completed.
- The first F4 attempt was stopped for low system memory; F4 was rerun per era with features spilled to disk.
- A4 F7(e): step5_final_sha256.txt was left as the record of the v1 state.
- The first evaluation of the F7 checks gave FAIL because of two defects in the checker, not in the code: it matched the old folder name in a text label instead of in path-building code, and it compiled an untracked unrelated file (test_431_additional_feasibility.py, with a byte-order mark). The checker was corrected (path-building code only; tracked scripts only) and the records regenerated. The A4 criterion 'each item is in place, the scripts compile, the hashes match' was not changed.

## Not addressed in this pass

- audit #9: the look-ahead probe in step4_extract_parameters.py
- audit #11: TRAIN cutoffs not in a frozen document, circular availability check, jump_variation_w bias, amihud back-adjustment
- the audit's 'disclosed and still open' items
