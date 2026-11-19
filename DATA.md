# Data

No market data is in this repository, and none may be added. This file lists every dataset the code reads, its source,
whether it can be redistributed, and how to obtain and verify it. Expected SHA-256 values are in `DATA_SHA256SUMS`
(verify with `sha256sum -c DATA_SHA256SUMS` from the repository root, after placing the files at the listed paths).

## 1. Files the analysis code reads

The detection (Section 5) and cross-asset (Section 6) code reads four canonical files. Their paths are fixed in
`step3_all_in_one.py` (`CONFIG`) and `section5/s5_eval_loader.py` (`PANELS`), and every guarded read rechecks their
hashes (`section5/s5_preflight_data_hashes.py`).

| Path | SHA-256 | Contents |
|---|---|---|
| `section3_10_alignment_results/canonical_panel_LEGACY_1m.csv.gz` | `b5967d96…098df` | 5-asset 1-min panel, 2003-01-02..2022-03-04 |
| `section3_10_alignment_results/canonical_panel_RAW_1m.csv.gz` | `f1b1c498…91184` | 5-asset 1-min panel, 2022-03-07..2026-10-12 |
| `section3_4_etf_results/etf_observed_SPY_LEGACY.csv.gz` | `7cd10dfb…c83f7` | SPY observed bars, LEGACY |
| `section3_4_etf_results/etf_observed_SPY_RAW.csv.gz` | `6c37b279…7928d` | SPY observed bars, RAW |

These are derived from the source files in §2. **The Section 2–3 scripts that build them are not yet in this
repository** (see "Known gaps" in `README.md`), so at present the canonical files can be verified but not rebuilt from
public downloads.

## 2. Source datasets

| Dataset | Used for | Source | Redistributable here? | What to do |
|---|---|---|---|---|
| HF Data Library, 1-min OHLCV, **Clean** archive of 2026-10-03 (SPY, TLT, HYG; LEGACY rows from PiTrading) | LEGACY era, all three ETFs | Elkassabgi, A. (2026). *HF Data Library: High-Frequency U.S. Equity Data (1-Minute OHLCV)*, Zenodo, [doi:10.5281/zenodo.19501604](https://doi.org/10.5281/zenodo.19501604) | **No.** The compilation is CC BY 4.0, but the bars are subject to the IEX Historical Data Terms of Use, and the pre-2022 rows are vendor (PiTrading) data the provider no longer distributes. | Cannot be re-downloaded: the PiTrading history was withdrawn. The exact copy used is retained by the author and identified by its hash (`DATA_SHA256SUMS`); contact the author. |
| HF Data Library, **Raw** SPY archive of 2026-10-13 (IEX trades only) | RAW era, SPY | same record | **No** (IEX terms) | Download the Raw 1-min SPY file from the HF Data Library (see the Zenodo record's README). Later releases differ; check the hash. |
| HF Data Library, TLT and HYG Raw 1-min files | RAW era, TLT and HYG | same record | **No** (IEX terms) | As above. |
| HF Data Library, Raw and Clean SPY archives of 2026-11-11 | A38 filter check only | same record | **No** | As above; hashes are also fixed in `AMENDMENT_A38.md`. |
| Dukascopy XAU/USD 1-min bid and ask, 2007-04-11..2026-10-02 | Gold (bid/ask midpoint) | Dukascopy Bank SA historical data feed | **No.** We found no published licence permitting redistribution; treat as not redistributable. | Download bid and ask 1-min candles for this span from Dukascopy and check the hashes. The ask files were hashed on 2026-11-12, after first use (paper Appendix F.2). |
| Dukascopy Dollar Index (DOLLAR.IDX/USD) 1-min bid and ask, 2017-12-01..2026-10-02 | USD (bid/ask midpoint) | Dukascopy | **No** (as above) | As above. |
| FOMC statement dates and times | H1(c), H3 positive control, Fed splits | Federal Reserve Board web pages (`fomccalendars.htm`, `fomchistorical{YEAR}.htm`); Lucca and Moench (2015) schedule | **Yes.** US government works are public domain; the derived schedules are committed (`section5/results/h1c_schedule_times*.json`, `fomc_clock.json`, `d6_fomc_dates.json`). | Nothing to fetch. |
| Bloomberg Book1/Book2 1-min bars, 2026-03-18..2026-09-30 | Post-evaluation timing check only (no result depends on it) | Bloomberg terminal | **No** (licensed) | Not reproducible without a Bloomberg licence. Only summary statistics are committed (`section5/results/bloomberg_comparison.json`). |

Place source files under `data/source/` (git-ignored) to use `sha256sum -c DATA_SHA256SUMS`. Their original local
paths are recorded in `section2_audit_results/inventory.csv` (not in git).

## 3. Derived, git-ignored artefacts

| Path | Built from | How to rebuild |
|---|---|---|
| `section5/cache/{LEGACY,RAW}_features.npz`, `_bases.npz` | canonical files (§1) | Built automatically by the Section 5 loader on first use; checked against `section5/results/cache_stamp.json`. Needed for `fig6_seasonality` and any model refit. |


The frozen models (`section5/results/frozen_models/`, 8 pickles + `manifest.json`) are committed; each was checked
against the manifest and the `model_sha256` in `evaluation_{LEGACY,RAW}.json` before it was added.

## 4. What is committed instead of data

Result files with summary statistics, per-fold and per-break detector outputs (`section5/results/breaks/breaks.csv`:
detection times, states and thresholds, no prices), feature metadata (`section431_step3_all_in_one_results/*matrix*.csv`:
one row per feature column, coverage shares) and session-level availability flags (`section6/results/coverage/`).
None contains price, quote or volume series.
