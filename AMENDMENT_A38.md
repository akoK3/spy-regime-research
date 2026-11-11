# Amendment A38 (filter checks of H1 before the freeze: primary, HF Clean vs Raw on the RAW evaluation period; secondary, the RAW-era effects)

Dated 2026-11-11T04:32:00+00:00 UTC (2026-11-10T23:32:00-05:00 New York). Status: ADOPTED 2026-11-11T04:33:42Z (user approval 2026-11-11: "approved as drafted. Adopt, hash, ledger row, add to freeze manifest", given as "A37" for this draft; the draft, sha256 dbdb257ebd02f7ee..., is unchanged apart from this status line). Written before the 5.12 freeze, before any evaluation-period output exists and before its code.
- **Requested by the user on 2026-11-10:** "Draft A37 (interpretation rule, before freeze): the RAW-era evaluation (2025-2026, unfiltered IEX) is reported as the filter-free check. The H1 conclusion is called robust to the LEGACY Clean filter only if the RAW-era effect has the same sign with its 95% interval excluding 0; otherwise LEGACY-era results are reported as possibly filter-dependent."
- **Numbered A38, not A37.** A35, A36 and A37 already exist and are adopted. A37 covers the TRAIN refits at the freeze (commit 81eb166).
- **Revised on the user's instruction of 2026-11-11** before adoption. The first draft (sha256 `cf9d7c6b1198499be1339bdeb366d02645ca963991822f52e6e7bafc1d829226`, ledger row of 2026-11-11 04:28Z) is superseded:
  > "1. Add a primary filter check: run the frozen setups on the RAW evaluation period (2025-01-02 to 2026-10-12) twice, once on the 2026-11-11 HF Raw file and once on the same-release HF Clean file. Report the H1(a) and H1(b) differences (Clean minus Raw) with day-cluster bootstrap 95% intervals. Same period and exchange, so the difference isolates the filter. Keep the current RAW-era criterion as secondary. 2. Add a power note: report the minimum detectable effect beside each robustness result, and add to the reading that "possibly filter-dependent" may also reflect limited power in the RAW evaluation period. Keep choices 1-5 as drafted."

## Background (facts)

- **Two HF versions, one per era.** The LEGACY panel (sessions to 2022-03-04) is built from the PiTrading rows of the HF Data Library **Clean** file of 2026-10-03. The RAW panel (from 2022-03-07) is built from the HF **Raw** IEX files. `section3_4_etf_results/summary.json` records these inputs.
- **HF's Clean pipeline looks ahead.** HF's documentation (read 2026-11-10) describes step 8 of Clean as "|close − median| > 3 × MAD, computed over a 50-bar centered window", which uses later bars.
- **The label-free check confirms it on IEX data** (`section5/results/hf_cleaning/hf_cleaning_spy.json`; SPY, release 2026-11-11, 2022-03-07 to 2024-12-23):
  - Clean removes 2.60% of Raw bars, all step-8 candidates;
  - removed bars reverse within 1-5 bars more often than kept bars of the same size, by +0.10 to +0.19, all 95% intervals above 0.
- **The LEGACY rows cannot be checked against an unfiltered copy.**
  - HF no longer offers history before 2022-03-07.
  - The HF Zenodo record (concept DOI 10.5281/zenodo.19501604, versions 1.0-1.2) holds only a README, with no data files. Versions 1.0 and 1.1 state "Earlier history is no longer offered."
  - Whether the PiTrading rows passed through the same filter is open (Section 2, D2-10).
- **Where the H1 evidence comes from.**
  - The 26 confirmatory development folds are LEGACY except RAW 0.
  - The RAW evaluation period (2025-01-02 to 2026-10-12, A26 1c, A36 1a) uses HF Raw only.
- **What the primary check can and cannot show.** The 2026-11-11 Raw and Clean files cover the RAW evaluation period from the same release and exchange (IEX). Running the frozen models on both isolates the effect of HF's documented Clean filter on H1 there. **It is HF's filter on IEX data, not necessarily PiTrading's processing of the LEGACY rows**: it is the closest available proxy.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A26.md` (labels; evaluation results not confirmatory) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `AMENDMENT_A36.md` (rules 1e, 4a, 5d-5g) | `f110e14f3633d764d8048bb67b192c6fff9b68d2540c85d0297d53448ff227db` |
| `AMENDMENT_A37.md` (frozen models loaded, one-shot marker) | `cd3cfdea7d75c3a0b9f5f819395cc6b4da37631b89572e0a9c7525a6e5af5b2e` |
| `section5/results/hf_cleaning/hf_cleaning_spy.json` | `d7a0b9b7e069fe78d57a8f78c024998111119b44519c6ee4d4aae7d5f95e9147` |
| `hfdatalibrary_raw_1min_1tickers_2026-11-11.zip` (SPY Raw, release 2026-11-11) | `b6e9da59a38deca77be6d5819c3608645dfe87ec785ca98c6eb45b2554b2feaf` |
| `hfdatalibrary_clean_1min_1tickers_2026-11-11.zip` (SPY Clean, same release) | `58f8f11245f398937cd23ab2d06ec5b170c4f7598521cfe402bc6bf2ac624c9d` |

## Rule 1: primary filter check, HF Clean vs Raw on the RAW evaluation period

1a. **Runs.** After the official 5.13 RAW run (A36 rule 5, A37), the frozen setups are run on the RAW evaluation period (2025-01-02 to 2026-10-12) twice:
  - on SPY from the 2026-11-11 HF **Raw** file;
  - on SPY from the 2026-11-11 HF **Clean** file.
1b. **Models and thresholds.** The frozen models are those A37 rule 2 loads: TRAIN-fitted, not refitted. The frozen feature thresholds and the baseline thresholds are those of the official run, used unchanged. Nothing is retuned.
1c. **Panels.**
  - Each run builds its SPY one-minute panel from its own file, with the Section 3/4 code paths that built the study panel: regular-hours grid, eligibility rules, features. A bar the file lacks is a missing minute, as in the study panel.
  - The look-back history of A36 4a (the TRAIN sessions before 2025-01-02, embargo sessions skipped as in A36 1e) comes from the same file.
  - H1 uses SPY only; no other asset is read.
  - These panels are separate files. The study panels are not touched.
1d. **Paired design.**
  - **H1(a):** the stable days, splice specifications and taus are those of the Raw run, applied unchanged to the Clean run.
  - **H1(b):** QLIKE is compared on the decision bars common to both runs and both models.
  - A unit not evaluable in either run is dropped from both, and counted.
1e. **Statistics.** Per family (Gaussian HMM, Student-t HMM, HSMM; BOCPD secondary): Delta(a) = H1(a) effect on Clean minus on Raw, and Delta(b) likewise. Each comes with a 95% percentile interval from a paired day-cluster bootstrap: 2,000 resamples, seed 513, the same day draws for both runs (A36 5g). The two effects on each file are also reported.
1f. **Reading.**
  - **Filter-sensitive on IEX data:** for a family, if either 95% interval of Delta excludes 0. Its sign is reported.
  - **No detectable filter effect:** if both include 0, reported with the minimum detectable Delta (rule 3).
  - This is descriptive under the A26 label. It is not a confirmatory test.
1g. **Reproducibility note.** The Raw-file run is also compared with the official RAW evaluation, which is built from the study's Raw downloads of 2026-10-13. Any difference, from vendor revisions between releases, is reported. The official run stays the reported 5.13 result.

## Rule 2: secondary check, the RAW-era effects (the first draft's criterion)

2a. The official 5.13 results on the RAW evaluation period (`section5/results/evaluation_RAW.json`) are reported as the filter-free RAW-era check. They keep the A26 label and change no development verdict.
2b. **Families.** Each H1 family whose MR2 development verdict is REJECT (Gaussian HMM, HSMM). Student-t HMM was not rejected; its RAW-era effects are reported without a robustness label. BOCPD is secondary and also gets no label.
2c. **Robust.** The family's H1 conclusion is called **robust to the LEGACY Clean filter** only if **both** RAW-era effects, H1(a) and H1(b), are positive, the sign of the development effects, **and** both 95% day-cluster intervals (A36 5g) exclude 0. Both are required because H1 is an intersection-union test of the two.
2d. **Otherwise** (either effect negative or zero, either interval including 0, or either effect not evaluable, e.g. H1(a) skipped for fewer than 8 stable days): the family's LEGACY-era results are reported as **possibly filter-dependent**. That covers the development folds in LEGACY and the LEGACY evaluation period.
2e. **H1(c)** (FOMC hit rates, secondary) is reported for the RAW era beside the criterion, but does not enter it.
2f. **The development RAW fold (RAW 0)** is also filter-free. Its effects are reported beside the RAW evaluation for reference. They do not enter the criterion: the development folds already enter the verdict.

## Rule 3: power

3a. Beside every result of rules 1 and 2, the minimum detectable effect is reported: the smallest true effect, or Delta, that the 95% interval would exclude 0 for with 80% power.
  - MDE = (1.96 + 0.84) x the day-cluster bootstrap standard error of that statistic: the SD of its 2,000 resamples, as computed in rules 1e and 2c.
  - Development effects are reported beside it for scale.
3b. The MDE is computed from the evaluation data's own bootstrap distribution. It is descriptive and changes no label.

## Rule 4: reading

4a. **"Possibly filter-dependent" is not a finding of dependence.** It may also reflect **limited power in the RAW evaluation period**: about 1.8 years of sessions against 25 LEGACY development folds. The MDE of rule 3 shows how large an effect could have been missed. The RAW era also differs from LEGACY in period, market regime, volume source (IEX only) and sample size.
4b. **"Robust" (rule 2) means only** that the conclusion holds where no Clean filter was applied. **"No detectable filter effect" (rule 1)** means that HF's Clean filter did not move H1 on IEX data by more than the MDE. Neither shows that the processing of the LEGACY rows had no effect.
4c. **Section 6** results are not governed by this amendment. Any filter check for H2, H3 and H4 needs its own amendment.

## Rule 5: guards and order

5a. The rule 1 runs read evaluation-period data. They therefore run only after the official 5.13 RAW run, through a guarded entry that requires:
  - the freeze, the era-calibration lock and the Section 6 fingerprint where applicable;
  - the A26 label on every output, with `confirmatory = false`;
  - its own one-shot marker per file, written immediately before the first evaluation-period read, so each run happens once.

  The two HF files are read only through that entry. They are registered as inputs with their hashes above, and they stay outside the study data.
5b. **Order.**
  - A38 is hashed into the ledger as a DRAFT.
  - On the user's approval: status line, sidecar, ledger row; A38 is added to the freeze manifest (`freeze_ready` then requires it ADOPTED).
  - The code for rule 1 (new modules only, registered; no result module changed; code version a0323ed24d68e896) is written after adoption, unit-tested on synthetic data, and run only after the official RAW evaluation.
5c. Adoption must precede the 5.12 freeze and any evaluation-period output.

## Governs

The filter checks of the H1 conclusions (primary: HF Clean vs Raw on the RAW evaluation period; secondary: the RAW-era effects), their power reporting and their reading. No development test, statistic or verdict changes. No freeze, no O8, no era calibration under this amendment.
