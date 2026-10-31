# Audit of `spy-regime-research`: 12 problems, 3 high severity

**I found no feature window that reads future bars.** The look-ahead I did find comes from fitted statistics and selection decisions made on the full sample. The repo has no model, labels or backtest, so no performance result is contaminated yet, but the High items will carry into Section 5.

"Disclosed" below means the ledger already records the issue. "Inferred" means I couldn't confirm it from tracked files alone.

## High
1. **Look-ahead in the `__sadj` columns has already reached a decision.**
   - **Where:** `step8_sections_4_3_4_to_4_3_9.py:148-152`, `step10_pool116_eligibility_redundancy.py:42-46,52,56,73`
   - Each value is divided by a median taken over all TRAIN rows, including later years. `raw_volume__sadj` keeps the volume level: its LEGACY yearly median runs 0.33 (2003), 3.06 (2008), 0.51 (2017).
   - A 2003 value therefore depends on data up to 15 years later, and this column is in the kept primary set.
   - `write_amendment_4_3_A3.py:86` calls these medians a descriptive-step statistic, and the fold-recompute rule (ledger limitation 15) doesn't cover Step 10, which used them for keep/drop decisions.

2. **The frozen folds appear to overlap the LEGACY evaluation block (inferred).**
   - **Where:** `write_closing_report_section4_3.py:59`, `frozen_documents/protocol_20261029T032641Z.json:86-99`, A1 line 19
   - The report restates 40 folds (36 LEGACY, 4 RAW) after A1 moved 2019-2022 into evaluation.
   - Those counts match the old 4,827 and 710 session spans exactly. LEGACY TRAIN's 4,022 sessions would give only 30 folds, so about 6 LEGACY folds would sit in evaluation. RAW's last fold would also run into the 5-session embargo.
   - No document re-cuts the folds, and the fold CSV isn't tracked, so I inferred this from the arithmetic.

3. **Features are selected on all of TRAIN, outside the folds.**
   - **Where:** `step8_sections_4_3_4_to_4_3_9.py:236-252`, `step10_pool116_eligibility_redundancy.py:54,72-74`
   - The protocol (line 96) says to select within each fold using inner train/validation only. Instead, a matrix built from 2003-2018 and 2022-2024 applies to every fold.
   - The impact on the 80-column primary set is small: all 6 drops have rho of at least 0.9998 in both eras. The 116-column pool is more exposed, with 48 drops in the RAW sensitivity set and 15 in the primary set.

## Medium
4. **Era-crossing decisions contradict the project's own rule.**
   - **Where:** rule at `write_amendment_4_3_A3.py:71`, `step5_policy.py:86`; behaviour at `write_amendment_4_3_A3.py:98,104`, `step8_sections_4_3_4_to_4_3_9.py:250`
   - `intrabar_range_log__sadj` left the primary pool only because of LEGACY (rho 0.9598, versus 0.9384 in RAW).
   - LEGACY coverage also removes 60 columns from RAW's primary set. RAW's 2022-2024 correlations likewise feed decisions on LEGACY columns.

5. **The Lee-Mykland threshold is on the wrong scale.**
   - **Where:** `step3_all_in_one.py:66-70,103,108`, `write_amendment_4_3_1_A2.py:40-41`
   - The statistic includes π/2, which makes it a z-score, but the threshold of 5.467 is meant for the version without π/2.
   - On 40,000 simulated no-jump sessions, 0.0575% were flagged against a design rate of 1%, about 17× too few.
   - A correctly scaled threshold of about 4.36 flags 2.31%, so it would need its own calibration for the short 60-bar window.
   - The oracle copies the same formula (`step3_all_in_one.py:323`), so Step 3 couldn't catch this. `lee_mykland_jump60` is kept in the RAW sensitivity set.

6. **Two of the three replacement delay checks cannot fail.**
   - **Where:** `step5_policy.py:286-294,332`
   - I shifted all 80 features one bar into the future. "Values identical" and "available_at = t+2" both still passed.
   - Only the replay failed, on 76, 73 and 72 of 80 outputs, and it covers 3 rows per dataset.
   - So 6 of the 9 counted delay rows are empty, and `visibility_ok` is effectively true by construction too. `write_closing_report_4_3_1.py:115` discloses this only as "partly by construction" for one check.

7. **The closing report makes a false claim about the evaluation period.**
   - **Where:** `write_closing_report_section4_3.py:77`
   - It says the evaluation period and later development days were "never in an audited or analysed span".
   - But `write_closing_report_4_3_1.py:99` records 2,150,970 rows built, which equals both full development spans. That includes LEGACY 2019-2022 and the RAW embargo days.
   - `section4_3_1_candidates.py:227-232` also summarises coverage by year over those rows.

8. **The real-data tests can't see errors in `amihud_*`.**
   - **Where:** `step3_all_in_one.py:27,128,148`
   - The absolute tolerance is 1e-10, while LEGACY's typical yearly median is about 1e-11. A 5× error at that level passes both the prefix and isolation tests; RAW passes a 20% error at about 4e-10.
   - NaN patterns are still compared, and Step 4 and the synthetic oracle use stricter tolerances.

## Low
9. **Look-ahead probes have blind spots.**
   - **Where:** `step3_all_in_one.py:418-420`, `step4_extract_parameters.py:27,231-233`
   - Real-data prefix cuts fall only at session ends, so they can't catch same-session look-ahead.
   - Step 4's future probe sits in the last session and reaches only 6 bars ahead.

10. **Protocol conflicts remain in the selected features.**
    - `raw_volume` is kept as primary, but `protocol_20261029T032641Z.json:75` says raw volume is for diagnostics only.
    - Every frozen comparison tier needs an `rv15_*` column, and none is primary-eligible, so no tier can run on the primary set.

11. **The splits and some formulas rest on weak foundations.**
    - **TRAIN cutoffs:** 2018-12-21 and 2024-12-23 are hardcoded (`step3_all_in_one.py:20-21`) and appear in no frozen document. No calendar-generated split manifest exists (disclosed).
    - **Availability check:** `section4_3_1_candidates.py:70` tests a column built on the same minute-start assumption, so it is circular. RAW has no clock sensitivity test.
    - **`jump_variation_w`:** it is biased upward by about one bar's variance even without jumps, because bipower uses w-1 pairs unscaled (`section431_additions.py:28-30`).
    - **`amihud_*` (inferred):** if LEGACY closes are back-adjusted, their price level embeds later dividends. I can't confirm this from tracked files.

12. **Reproducibility and record-keeping gaps.**
    - `step6_coverage.py:21` and `write_closing_report_4_3_1.py:45-46` read a folder that isn't in the repo.
    - `step8_sections_4_3_4_to_4_3_9.py:18` points at an old session's temp directory and deletes it at the end.
    - Steps 3, 4, 6, 8 and 10 overwrite frozen outputs without refusing, unlike the `write_*` scripts.
    - `step8_sections_4_3_4_to_4_3_9.py:296` hardcodes a check to `True`.
    - `step5_final_sha256.txt` no longer matches `step5_policy.py` or `step5_delay_diagnosis.py`.

## Disclosed and still open
- LEGACY clock semantics and possible centered vendor cleaning could mean real look-ahead that no code here can detect.
- None of A1's six required items has been verified, and no leakage audit has been run.
- The overnight exclusion is declared only, with no code enforcing it.

## Audit limits
- **Reviewed:** I read all 23 `.py` files and the protocol and amendment documents. Generated reports and CSVs were checked by script or by targeted reads, not line by line.
- **Hashes:** the only failures against current files are the two in item 12. Other non-matching citations were superseded versions or files not in the repo.
- **Replays:** the redundancy results reproduce exactly from the tracked correlation CSVs.
- **Not rerun:** I did not read market data or rerun the pipeline, so item 2 and the `amihud_*` point in item 11 stay inferred.

I fixed nothing and the working tree is unchanged. The audit scripts are in the session scratchpad, at `C:\Users\kakij\AppData\Local\Temp\claude\C--Users-kakij-Downloads\8fd76ec5-05e6-479f-95a7-e0506ede90fa\scratchpad\a1.py` and `C:\Users\kakij\AppData\Local\Temp\claude\C--Users-kakij-Downloads\8fd76ec5-05e6-479f-95a7-e0506ede90fa\scratchpad\a2.py`.
