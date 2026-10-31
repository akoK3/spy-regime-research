# Section 4.3.0 exposure audit and Section 4.3.1 construction

Completed locally on October 28, 2026 (America/New_York). Original Downloads scripts, data and saved experiments were preserved.

**Finding:** Sections 4.8C and 4.8D both used the proposed 2025–2026 holdout for inner training and validation. The original dates are retained as **exposed retrospective evaluation**. They cannot be described as an untouched independent final test. Rebuilding earlier development data does not erase prior knowledge of later data.

## Evidence of exposure

Both scripts use RAW fold 6, whose nominal training block is **2025-03-12 through 2025-12-09**, followed by validation **2025-12-10 through 2026-03-12**. Training sampled 63 sessions at stride 3 (last sampled training date **2025-12-05**); validation sampled 32 sessions at stride 2. Exact dates are in [prior_exposure_sessions.csv](prior_exposure_sessions.csv), with nominal and sampled boundaries in [prior_fold_windows.csv](prior_fold_windows.csv).

- 4.8C has **99** saved RAW fold 6 candidate-fit rows, with explicit 2025-12-10/2026-03-12 validation dates.
- 4.8D has **45** saved RAW fold 6 frequency/state/seed fit rows. Its source checksums and the shared fold-generation code establish the same session windows.
- 4.8C's summary stores `states: 4`, but actual saved score rows contain state counts **2, 3, 4**. The audit uses the saved rows.
- 4.8A/B RAW fold 6 also overlaps this period; 4.7 exports 2025–2026 holdout feature correlations. Whole-era feature/missingness diagnostics extend beyond March 2026. The previous-tick study also inspected TLT/HYG availability and returns, without establishing an event-study effect.

The older `outer_test_untouched` flags refer to which subset a particular local fit scored. They do not certify that every date in 2025–2026 was globally unseen. Across rolling folds, dates used as an earlier outer block can also enter a later training block. Computational exposure is established; exactly which results influenced the researcher is not recoverable from files alone. V1 exposure mentioned in the draft is not independently reconstructed, and no clean-period claim depends on assuming it absent.

See [exposure_audit.json](exposure_audit.json), [evidence_inventory.csv](evidence_inventory.csv), and the preserved [evidence](evidence) directory.

## Final historical boundaries

All dates below are inclusive NYSE session dates. Nontrading January 1 is omitted from actual session endpoints.

| Role | Source | First session | Last session | Sessions |
|---|---|---|---|---:|
| Development | PiTrading LEGACY | 2003-01-02 | 2022-03-04 | 4,827 |
| Development | IEX-labelled RAW | 2022-03-07 | 2024-12-31 | 710 |
| Exposed retrospective evaluation | RAW | 2025-01-02 | 2026-10-12 | 445 |

The two legacy sessions 2002-12-30/31 are excluded. The draft calendar development start remains 2003-01-01; the first actual trading session is January 2. The draft evaluation calendar start remains 2025-01-01; the first actual trading session is January 2. No favorable outcome was used to move these dates.

TLT/HYG can use the frozen panel through **2026-10-12**; GOLD/DOLLAR stop at **2026-10-01**. These are panel availability endpoints, not promises of complete coverage. Pairwise eligible masks remain separate; do not truncate all assets to a five-way common panel. Later standalone TLT/HYG observations through October 14 do not extend the frozen SPY panel. October 13–28 is not certified unexposed and is not substituted as a clean test.

No existing date period is certified as an unexposed confirmatory test. A new period requires a separate complete model/analysis lock and exposure audit before its outcomes are accessed. This artifact freezes the split and feature construction, not an unfinished detector or event study.

## Provider and clock rules

Keep legacy and RAW separate: no cross-provider return, rolling window, volume baseline, scaler, HMM fit or state recursion across **2022-03-04 / 2022-03-07**. No extra dividend scaling is applied to RAW. Raw/log volume are diagnostic candidates; cross-era pooling of raw volume is prohibited.

Use the inherited XNYS regular-session grid, including DST and early closes. A start-labelled candle becomes available at its stamp plus 60 seconds. No overnight return, interpolation, forward fill or backward fill is introduced. Legacy timestamp semantics and possible upstream centered cleaning remain unresolved; computational causality does not prove vendor causality. Subsequent timing work must report the legacy ±1-minute sensitivity.

Development folds are explicit in [development_nested_folds.csv](development_nested_folds.csv): 252 preceding sessions, split 189/63 for inner training/validation; outer development blocks advance by 126 sessions, with a minimum terminal block of 63 sessions. There are **40** folds (36 legacy, 4 RAW), using every session rather than old speed-up strides. RAW's final outer development block has 80 sessions. The 39-session legacy terminal fragment is excluded from outer scoring; it remains development data. All future fitted scalers, thresholds and model choices must use training/inner validation only.

## Frozen protocol

Final file: [protocol_20261029T032641Z.json](protocol_20261029T032641Z.json)  
Frozen New York: **2026-10-28T23:26:41.858198-04:00**  
Frozen UTC: **2026-10-29T03:26:41.858198+00:00**  
SHA-256: `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b`

The `.sha256` sidecar hashes the exact UTF-8 JSON bytes. The protocol also records original input hashes, evidence/fold hashes and implementation hashes. A timestamp and hash establish local content identity; they are not an independent timestamp authority or proof of historical nonexposure.

Revision 1 is retained with its implementation in `implementation_v1`. Its first full-data run failed before feature construction because NumPy 2.5 does not support Unicode array min/max. Revision 2 changes that endpoint check to first/last on already sorted data and adds a loader regression test. **No scientific dates, features or selection rules changed.** See the amendment log in the final protocol and [results/FAILED_RUN.json](results/FAILED_RUN.json). Do not edit frozen JSON; amend under a new timestamp/hash.

## Section 4.3.1 completed

Built **35 candidate features** on **2,150,970 development minute rows** (1,875,150 LEGACY + 275,820 RAW). Output rows include availability timestamps, source/session flags and observed-count/volume-baseline diagnostics. No 2025–2026 feature matrix was constructed; gzip source streams necessarily decode chunks containing other dates, which are discarded before feature construction. No target-return columns are requested by the builder.

Candidates cover exact one-minute return and absolute return; strict RV, downside RV, strict momentum and exact-endpoint momentum at 5/10/15/30/60 minutes; 90% partial RV at those windows; 15-minute partial downside; exact five-minute-sampled 60-minute RV; bar range; raw/log volume and prior-session relative/log-relative volume; and a current-return shock standardized by the previous 60-return median/MAD. Exact definitions are frozen in the JSON and [section4_3_1_candidates.py](section4_3_1_candidates.py).

Partial RV is a missing-variance extrapolation proxy, not recovered truth. Five-minute sampled RV is a different estimator. Zero MAD produces an unavailable shock feature; zero volume produces an unavailable log. Warmups and history requirements are retained without filling.

Availability below uses each feature's scheduled calendar opportunities after its intraday warmup. Volume history warmup is retained in its denominator; this is a feasibility table, not a model ranking.

| Feature | LEGACY | RAW development |
|---|---:|---:|
| return_1m | 95.61% | 99.82% |
| rv15_strict | 80.43% | 99.42% |
| rv60_strict | 45.50% | 98.11% |
| rv15_partial90 | 82.41% | 99.47% |
| rv60_partial90 | 86.39% | 99.83% |
| rv60_sampled5_exact | 69.97% | 99.44% |
| relative_volume20 | 96.81% | 98.44% |
| shock_prior60_mad | 44.87% | 98.08% |

Full year-by-year coverage is in [feature_coverage_development.csv](results_v2/feature_coverage_development.csv). [common_support_development.csv](results_v2/common_support_development.csv) records comparison-tier intersections. Later model comparisons must match both training and evaluation support within each tier; different tiers are not directly paired.

Generated matrices:

- [candidate_features_LEGACY_DEVELOPMENT.csv.gz](results_v2/candidate_features_LEGACY_DEVELOPMENT.csv.gz)
- [candidate_features_RAW_DEVELOPMENT.csv.gz](results_v2/candidate_features_RAW_DEVELOPMENT.csv.gz)

## Verification and continuation

**PASS:** six independent unit/regression tests cover formulas, loader dates/availability, missing endpoints, partial-window counts, session/early-close resets, prior-only volume, future edits/deletion and zero scales. Actual-data prefix deletion verifies all features causally; full saved matrices were read back for row counts, date boundaries, availability and feature completeness. Original source/evidence hashes still match. See [validation_tests.txt](validation_tests.txt), [completion_verification.json](completion_verification.json) and [summary.json](results_v2/summary.json).

No HMM was fitted and no feature winner was selected. Next work is development-only feasibility/normalization and nested candidate comparison under the frozen support rules. Before any independent confirmatory claim, separately freeze the complete detector, reaction windows, endpoints, inference/multiplicity rules and a genuinely unexposed data-collection period.

Reproduce in a new output directory with the existing research Python:

```powershell
& "C:\Users\kakij\Downloads\research_hmm_env\Scripts\python.exe" -B -m unittest -v test_candidates
& "C:\Users\kakij\Downloads\research_hmm_env\Scripts\python.exe" -B section4_3_1_candidates.py --protocol protocol_20261029T032641Z.json --out-dir results_reproduction
```

Run from this artifact directory. Sources remain in Downloads; outputs are confined to this workspace.
