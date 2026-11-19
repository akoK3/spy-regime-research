SECTION 3.9 — TIMEFRAME AGGREGATION
==================================

INSTALL IF MISSING:
    python -m pip install pandas numpy pandas_market_calendars

SAVE THE SCRIPT IN Downloads, THEN RUN:
    python "$HOME\Downloads\section3_9_timeframe_aggregation.py"

OPTIONAL BUILT-IN TEST ONLY:
    python "$HOME\Downloads\section3_9_timeframe_aggregation.py" --self-test

This step uses previously created datasets (read-only):
  Downloads\section3_4_etf_results\etf_observed_*.csv.gz
  Downloads\section3_5_quote_quality_results\quote_quality_rth_*.csv.gz

It processes 6 ETF source/epoch panels plus gold and dollar quote panels
at 2, 3, 4, 5, 10 and 15 minutes each. On a typical Windows PC this may
run for several minutes and writes sizable .csv.gz files. It DOES NOT run
an HMM, edit raw input data, interpolate prices or create overnight returns.

Please upload only these files from Downloads\section3_9_aggregation_results:
  REPORT.md
  summary.json
  frequency_comparison.csv

Keep the large bars_*.csv.gz outputs locally for later Section 3.10.

What is measured:
  - complete scheduled windows vs partly observed windows
  - endpoint-anchored returns measured over EXACT k minutes
  - stricter returns requiring every one-minute constituent in both bars
  - quote-quality-filtered complete-window returns
  - irregular shortened final windows kept but NOT called k-minute returns

A k-minute return from accurate endpoints is mathematically legitimate,
but it does not reconstruct missing intermediate one-minute observations.
The original 1-minute dataset remains the primary reference; we will review
results before choosing any coarser alternative for robustness checks.
Historical legacy minute labeling remains an explicitly recorded uncertainty.
