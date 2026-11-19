# Panel build (Sections 2–3)

**These scripts are NOT part of code version `a0323ed24d68e896`.** That code version is a SHA-256 over the 25
result modules found by `section5/s5_guard.result_modules()` (Section 4 feature code and `section5/`); no file in this
folder is among them, and no code-version record holds their hashes. They are included so the canonical panels can be
rebuilt from the vendor files. Their outputs are what the analysis reads, and those outputs are verified by hash in
`DATA_SHA256SUMS` (repository root), not by this code.

## Contents and provenance

17 files, copied unchanged on 2026-11-19 from where they were run (repository root, `section3_9_run/`,
`section3_10_run/`). SHA-256 of every file: `SHA256SUMS_2026-11-19` in this folder (check with
`sha256sum -c SHA256SUMS_2026-11-19` from inside `panel_build/`). They were not tracked in git before this date.

| Step | Script | Role | Main output (relative to the home `Downloads` folder) |
|---|---|---|---|
| 2 | `section2_complete_data_audit.py`, `section2_targeted_remaining_checks.py` | Source inventory and data audit | `section2_audit_results/`, `section2_followup_results/` |
| 3.2 | `section3_2_timestamp_alignment.py`, `section3_2_quote_alignment_fix.py` | Timestamp convention and quote alignment | `section3_2_timestamp_results/` |
| 3.3 | `section3_3_missingness_flags.py` | Missing-minute flags | `section3_3_missingness_results/` |
| 3.4 | `section3_4_etf_cleaning.py` | ETF bars on the NYSE grid | `section3_4_etf_results/etf_observed_*.csv.gz` (**SPY files hashed in `DATA_SHA256SUMS`**) |
| 3.5 | `section3_5_quote_quality.py` | Gold and dollar-index bid/ask midpoint, quote quality | `section3_5_quote_quality_results/` |
| 3.6 | `section3_6_return_construction.py`, `section3_6_eight_jump_validation.py` | 1-min returns; jump validation | `section3_6_return_results/returns_1m_*.csv.gz` |
| 3.7 | `section3_7_overnight_handling.py` | Overnight returns (kept separate; not detector inputs) | `section3_7_overnight_results/` |
| 3.8 | `section3_8_corporate_actions.py`, `section3_8_full_verification.py`, `section3_8_final_four_checks.py` | Corporate actions and verification only | `section3_8_*_results/` |
| 3.9 | `section3_9_run/section3_9_timeframe_aggregation.py` | Coarser-bar alternatives (robustness only) | `section3_9_aggregation_results/` |
| 3.10 | `section3_10_run/section3_10_cross_asset_alignment.py` | Five-asset 1-min alignment | `section3_10_alignment_results/canonical_panel_{LEGACY,RAW}_1m.csv.gz` (**hashed in `DATA_SHA256SUMS`**) |

The `SECTION3_9_README.txt` and `SECTION3_10_README.txt` files are the original run notes, kept unchanged.

## Build environment

| Item | Value | Source |
|---|---|---|
| Python | 3.14.3 (64-bit, Windows 11) | `section3_final_closeout_results/environment.json`; `section3_2_timestamp_results/summary.json` |
| numpy | 2.3.5 | same records |
| pandas | 2.3.3 | same records |
| pandas_market_calendars | 5.5.0 | `section3_2_timestamp_results/summary.json` |
| Other dependencies | `requirements-panel.lock` | installed versions in that interpreter, all installed on or before 2026-10-07 and unchanged since; not recorded at run time |

This is a different environment from the research environment (`requirements.lock`, Python 3.12.10).

## Running them

The scripts were written for one machine and are kept byte-for-byte as run, so:
- they read the vendor files from `~/OneDrive/Desktop/data/raw` (`section2_complete_data_audit.py` line 47 names that
  folder as an absolute Windows path) and write to `~/Downloads/<step>_results/`;
- run them in step order with the vendor files of `DATA.md` §2 in that folder, then compare the outputs with
  `DATA_SHA256SUMS`. A mismatch means the inputs or the environment differ; the analysis must not be run on such files.
- The Section 3.8 verification scripts also fetch public pages at run time (issuer distribution pages from SSGA and
  iShares, a PiTrading page, Yahoo Finance dividend data). These checks do not feed the panels.

The LEGACY source (PiTrading rows of the HF Data Library Clean file of 2026-10-03) is no longer distributed, so the
LEGACY panel can be rebuilt only from the retained copy identified in `DATA_SHA256SUMS`.
