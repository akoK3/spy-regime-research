# Amendment A38 (interpretation rule before the freeze: the RAW-era evaluation as the filter-free check of H1)

Dated 2026-11-11T04:28:00+00:00 UTC (2026-11-10T23:28:00-05:00 New York). Status: DRAFT, awaiting the user's approval. Interpretation only: no code, no data, no result changes. Written before the 5.12 freeze and before any evaluation-period output exists.
- **Requested by the user on 2026-11-10:** "Draft A37 (interpretation rule, before freeze): the RAW-era evaluation (2025-2026, unfiltered IEX) is reported as the filter-free check. The H1 conclusion is called robust to the LEGACY Clean filter only if the RAW-era effect has the same sign with its 95% interval excluding 0; otherwise LEGACY-era results are reported as possibly filter-dependent."
- **Numbered A38, not A37.** A35, A36 and A37 already exist and are adopted. A37 covers the TRAIN refits at the freeze (commit 81eb166).

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
  - The RAW evaluation period (2025-01-02 to 2026-10-12, A26 1c, A36 1a) uses HF Raw only, so no Clean filter has touched it.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A26.md` (labels; evaluation results not confirmatory) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `AMENDMENT_A36.md` (rule 5g: per-era effects with 95% day-cluster intervals, no p) | `f110e14f3633d764d8048bb67b192c6fff9b68d2540c85d0297d53448ff227db` |
| `AMENDMENT_A37.md` (current last amendment) | `cd3cfdea7d75c3a0b9f5f819395cc6b4da37631b89572e0a9c7525a6e5af5b2e` |
| `section5/results/hf_cleaning/hf_cleaning_spy.json` | `d7a0b9b7e069fe78d57a8f78c024998111119b44519c6ee4d4aae7d5f95e9147` |
| `section5/s5_hf_cleaning_check.py` | `d5165916aba0d70544928a66eef5c174ce51295477d99aa1c8198fdef2e78edc` |

## Rule 1: the RAW-era evaluation is the filter-free check

1a. The 5.13 results on the RAW evaluation period (A36 rule 5, `section5/results/evaluation_RAW.json`) are reported as **the filter-free check** of the development H1 conclusions: unfiltered HF Raw IEX data, no Clean filter.
1b. They keep the A26 label "adaptive/exploratory (previously exposed period)". The check is descriptive. It is not a confirmatory test and changes no development verdict.

## Rule 2: robustness criterion (per H1 family the development run rejected)

2a. **Families.** Each H1 family whose MR2 development verdict is REJECT (Gaussian HMM, HSMM). Student-t HMM was not rejected; its RAW-era effects are reported without a robustness label. BOCPD is secondary and also gets no label.
2b. **Effects.** The RAW-era H1(a) effect (pAUC features minus baseline) and H1(b) effect (mean QLIKE baseline minus features), each with its 95% day-cluster bootstrap interval (A36 5g: 2,000 resamples, seed 513).
2c. **Robust.** The family's H1 conclusion is called **robust to the LEGACY Clean filter** only if **both** RAW-era effects are positive, the sign of the development effects, **and** both 95% intervals exclude 0. Both are required because H1 is an intersection-union test of the two.
2d. **Otherwise** (either effect negative or zero, either interval including 0, or either effect not evaluable, e.g. H1(a) skipped for fewer than 8 stable days): the family's LEGACY-era results are reported as **possibly filter-dependent**. That covers the development folds in LEGACY and the LEGACY evaluation period.
2e. **H1(c)** (FOMC hit rates, secondary) is reported for the RAW era beside the criterion, but does not enter it.

## Rule 3: reading

3a. **"Possibly filter-dependent" is not a finding of dependence.** The RAW era also differs from LEGACY in period, market regime, volume source (IEX only) and sample size. A RAW-era effect whose interval includes 0 may reflect those differences or low power.
3b. **"Robust" means only** that the conclusion holds where no Clean filter was applied. It does not show the filter had no effect on the LEGACY numbers.
3c. **Reported side by side.** The development RAW fold (RAW 0) is also filter-free. Its effects are reported beside the RAW evaluation for reference. They do not enter the criterion: the development folds already enter the verdict.
3d. **Section 6** results are not governed by this rule. Any filter-robustness reading for H2, H3 and H4 needs its own amendment.

## Rule 4: order

4a. A38 is hashed into the ledger as a DRAFT. On the user's approval:
  - the status line is changed;
  - the sidecar is written;
  - a ledger row is added;
  - A38 is added to the freeze manifest (`freeze_ready` then requires it ADOPTED).
4b. Adoption must precede the 5.12 freeze and any evaluation-period output.

## Governs

The interpretation and wording of the H1 conclusions with respect to the LEGACY Clean filter. No test, statistic, verdict, data or code changes under this amendment. No freeze, no O8, no era calibration.
