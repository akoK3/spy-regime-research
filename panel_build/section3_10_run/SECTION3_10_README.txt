SECTION 3.10 — CROSS-ASSET ALIGNMENT (1-MINUTE)

Preferred: download section3_10_cross_asset_alignment.py into Downloads.
Run from Windows PowerShell:
    python "$HOME\Downloads\section3_10_cross_asset_alignment.py"

If downloading ZIP, extract into Downloads:
    Expand-Archive "$HOME\Downloads\section3_10_alignment_package.zip" -DestinationPath "$HOME\Downloads\section3_10_run" -Force
    python "$HOME\Downloads\section3_10_run\section3_10_cross_asset_alignment.py"

Self-test only:
    python "$HOME\Downloads\section3_10_cross_asset_alignment.py" --self-test

Prerequisites:
- pandas and numpy; pandas_market_calendars OR exchange_calendars (previous Section 3.9 uses these).
- ALL EIGHT Section 3.6 outputs in:
    Downloads\section3_6_return_results\returns_1m_SPY_LEGACY.csv.gz
    Downloads\section3_6_return_results\returns_1m_TLT_LEGACY.csv.gz
    Downloads\section3_6_return_results\returns_1m_HYG_LEGACY.csv.gz
    Downloads\section3_6_return_results\returns_1m_SPY_RAW.csv.gz
    Downloads\section3_6_return_results\returns_1m_TLT_RAW.csv.gz
    Downloads\section3_6_return_results\returns_1m_HYG_RAW.csv.gz
    Downloads\section3_6_return_results\returns_1m_GOLD.csv.gz
    Downloads\section3_6_return_results\returns_1m_DOLLAR.csv.gz

The script reads these files and creates outputs only in:
    Downloads\section3_10_alignment_results\

Upload these outputs to ChatGPT:
    REPORT.md
    summary.json
    pairwise_coverage.csv
    five_asset_coverage.csv

Keep compressed full-year-joined canonical_panel_LEGACY_1m.csv.gz and
canonical_panel_RAW_1m.csv.gz locally for modeling.

Design notes:
- Preserves full NYSE RTH calendar and every missing-minute mask.
- Pairwise overlap independent of unrelated assets; 5-asset overlap separately reported.
- Same-interval returns never establish lead-lag; causal event tests come later.
- Legacy timestamps remain uncertified; no 2022 provider bridging.
- Section 3.9 5m alternatives are not re-aligned here; primary is 1m.
- All inputs READ ONLY. Reports are regenerable and can be overwritten on rerun.
