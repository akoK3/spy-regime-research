# Report, 2026-11-10 (chain done 15:55 New York)

## Bottom line

**The Section 6 dev run is done for Gaussian HMM and HSMM. No primary test is rejected for either detector.**
- **H3** (next-day cross-asset volatility after a break): gamma is negative for every asset. TLT and gold have one-sided p of about 1.
- **H4a / H4b** (cross-asset confirmation): out-of-fold AUC gains are small and not significant. The closest is HSMM H4b, at +0.050, p = 0.084 (Holm 0.51).
- **Gaussian HMM fails two checks:**
  - the A28 7d null control: H4b rejects 10.5% of null sets, against a limit of 10%;
  - the A31 placebo-filter control flags TLT.
- **HSMM passes every check.**
- No freeze, no O8, no era calibration. TRAIN-span development data only. Results are labelled development; nothing read evaluation-period data.

## Done today, in order (all committed and pushed)

| Time (NY) | Step |
|---|---|
| 10:01 | A31 rule 3 revised to your decision (filtered vs matched placebos with no alarm exclusion; fully unfiltered = descriptive), hashed before code |
| 10:01 | A29 adopted as drafted (rule 3c kept): sidecar, ledger row |
| 10:02-10:04 | A30 written, hashed, adopted on your pre-approval; then its code |
| 10:31 | A31 rule 4 synthetic checks **PASS 29/29** (tag a31r); A31 adopted by the chain |
| 10:31 | Chain stopped at the gate by **my bug** (PowerShell split the inline gate code at spaces). All four amendments were in fact adopted. Fixed, ledger row, resumed at the gate (10:32) |
| 11:43 | Your instruction: the chain's PowerShell parent was replaced so that the dev run starts with 2 x 3 workers. The power check (2 x 7) was not touched |
| 12:04 | Power done (no crash, no restart); dev run starts |
| 14:55-15:15 | Dev run paused at your request (processes suspended), then resumed |
| 15:55 | Dev run done: 231.8 min including the 20-minute pause; exit 0 for both detectors; no tracebacks |

**Memory headroom during the dev run:**
- 5,255 MB free of 16,069 MB at the start;
- 2,504 to 3,802 MB free over the first 30 minutes;
- about 4,700 MB free at 13:43.

## A31 synthetic checks (rule 4, 999 resamples, 200 null / 40 effect replicates)

| Check | Independent | Vol-clustered | Limit |
|---|---|---|---|
| Six primary tests, rejection under no effect | 0.5-4.5% | 0-5.5% | 8.1% |
| Revised rule 3 control, flag rate (TLT/HYG/gold/USD) | 6.0/6.0/4.0/4.5% | 5.5/5.0/4.5/7.0% | 8.1% |
| Rule 3 control, mean delta | -0.001 to +0.002 | -0.001 to +0.002 | |
| Fully unfiltered comparison (descriptive): mean delta | +0.033 to +0.036 | +0.046 to +0.050 | not a criterion |

**Planted effects recovered:**
- H4a: 0.207 vs target 0.207.
- H4b: 0.266 vs 0.268.
- H3 TLT / HYG / gold: 0.242 / 0.115 / 0.245 vs 0.252 / 0.126 / 0.252.

## Power (A29 1f, A31 units; 200 simulations, 999 resamples, first Holm step 0.05/6)

| | Gaussian HMM | HSMM |
|---|---|---|
| Breaks / H4a units / weeks | 600 / 1,853 / 394 | 549 / 2,480 / 365 |
| H3: minimum detectable gamma | 0.15 SD (power 0.87) | 0.15 SD (power 0.855) |
| H4a: minimum detectable AUC gain | 0.067 | 0.035 |
| H4b: minimum detectable AUC gain | **not reached** (power 0.735 at gain 0.104) | **not reached** (power 0.585 at gain 0.102) |

H4b is underpowered: a null H4b result says little.

## Development run: primary tests (9,999 resamples, Holm m = 6)

| Test | Gaussian: n, estimate, p (Holm) | HSMM: n, estimate, p (Holm) |
|---|---|---|
| H3 TLT | 402 breaks, gamma -0.164, p 1.00 (1.00) | 339, -0.139, p 1.00 (1.00) |
| H3 HYG | 243, -0.071, p 0.97 (1.00) | 205, -0.043, p 0.84 (1.00) |
| H3 gold | 420, -0.185, p 1.00 (1.00) | 373, -0.156, p 1.00 (1.00) |
| H3 USD | 9, -0.282, p 0.73 (1.00) | 11, -0.213, p 0.75 (1.00) |
| H4a | 1,853 (280 confirmed), gain +0.016, p 0.28 (1.00) | 2,480 (365), +0.013, p 0.19 (0.94) |
| H4b | 597 (203 real), gain -0.009, p 0.58 (1.00) | 545 (198), +0.050, p 0.084 (0.51) |

**How to read these:**
- **H3 is negative, not merely null.** A29 3b says a negative gamma is reported as a transient cross-asset response, never as calming, and only when gamma's two-sided 95% interval lies wholly below 0.
  - That interval is not in the dev-run output: `h3_test` reports only the one-sided p. One-sided p of about 1 for TLT and gold means the bootstrap almost never reached 0, but I have not computed the 3b interval.
  - **Decision for you:** may I compute it? It is post-hoc reporting from the saved inputs, with no change to any test.
- **The A29 3c diagnostic** (prior-hour control before S) moves gamma toward 0, for example TLT -0.164 to -0.141 (Gaussian) and -0.139 to -0.110 (HSMM). Part of the negative gamma sits in the S-to-T window, as A29 3a anticipated.
- **USD** has only 9 or 11 breaks (it is available only in 2018 in LEGACY), so it carries no information.
- **About 27% of breaks** (162/600 and 159/549) have no cross-asset data at all, because no asset is covered before 2007.

## Checks

| Check | Gaussian HMM | HSMM |
|---|---|---|
| A28 7d(i) positive control (Fed breaks, TLT rest of day) | gamma 0.59, p 0.0001: **pass** | gamma 0.58, p 0.0002: **pass** |
| A28 7d(ii) null sets (200), rejection per test <= 0.10 | H3 0.5-6.5%, H4a 4.5%, **H4b 10.5%: FAIL** | max 8.0% (H4b): **pass** |
| A31 rule 3 control (filtered vs matched without alarm exclusion) | **TLT flagged**: delta +0.030 [+0.008, +0.052]; HYG, gold, USD not flagged | none flagged (TLT +0.012 [-0.010, +0.032]) |
| A31 3e fully unfiltered comparison (descriptive) | delta +0.010 to +0.025 | delta -0.051 to +0.019 |

**What the Gaussian failures mean (rules as written; nothing amended):**
- **H4b null rejection 10.5% vs 10%.** At 200 sets the Monte Carlo SE is about 2.1 points, so this is within noise of the limit. It still fails the rule as written, and the Gaussian H4b result is read with that caveat. The H4b result is not significant either way.
- **TLT flag.** The alarm filter raises the placebos' next-day TLT volatility by about 0.03. That pushes the Gaussian H3 TLT gamma downward by about that much. It does not change the sign or the conclusion (gamma -0.164).

## Secondary analyses (BH)

**Nothing survives BH:** 0 of 68 tests (Gaussian) and 0 of 69 (HSMM).
- Smallest raw p: HSMM LEGACY offset +1 H4b, p 0.009, and HSMM H4b at the 70th percentile, p 0.064.
- **Since 2007:** H3 is identical to the primary results, because no asset has data before 2007. H4 differs slightly.
- **Fed vs non-Fed:**
  - H3 gamma is more negative on Fed breaks: TLT -0.23 / -0.43, gold -0.43 / -0.41.
  - n = 26-43 Fed breaks; no test significant.
- **Detector dependence (A28 7a):**
  - every detector gives negative H3 for TLT and gold, BOCPD included (-0.07);
  - Student-t is the only detector with a positive HYG gamma, +0.038, p 0.18.

## A30 lead-lag description (descriptive, no test)

- **Windows:** 538 of 600 breaks (Gaussian) and 485 of 549 (HSMM) were evaluated; the rest crossed the open or the close.
- **Breaks look like the chance reference.** Each placebo was put through the same calculation against the other placebos.

**Share of breaks where SPY's S comes first:**

| | Gaussian, breaks | Gaussian, chance | HSMM, breaks | HSMM, chance |
|---|---|---|---|---|
| All available assets | 0.37 | 0.38 | 0.40 | 0.39 |
| TLT | 0.56 | 0.60 | 0.56 | 0.59 |
| HYG | 0.89 | 0.85 | 0.87 | 0.87 |
| Gold | 0.59 | 0.54 | 0.61 | 0.55 |

- **Timing:** the median first exceedance is 0 to 10 minutes before S for TLT and gold, against 5 to 10 minutes before S under chance.
  - At least one exceedance occurs in 60-65% of windows (chance 62-71%).
  - So there is no sign that cross-asset moves cluster around the break beyond chance.
- **Fed breaks, the one visible difference:** gold moves first more often.

  | Gold, Fed breaks | Breaks | Chance |
  |---|---|---|
  | SPY first (Gaussian / HSMM) | 0.33 / 0.24 | 0.53 / 0.55 |
  | Exceedance rate | 79% / 82% | 69-76% |

  - With n = 42 / 38 this is descriptive only.
- **HYG** exceeds in only about 20% of windows, against 23% by chance, so its first-exceedance numbers are thin. That is probably HYG's many zero 1-minute returns: an exceedance must be strictly above the 90th percentile.

## Decisions for you

1. **A29 3b interval for H3** (TLT, gold, both detectors): may I compute it post hoc, as reporting only? Without it the negative H3 cannot be labelled a "transient cross-asset response" under 3b.
2. **The Gaussian failures stand as written:**
   - the null-set check (H4b 10.5%);
   - the TLT flag.

   I recommend no amendment: report them as caveats.

## Files

- **Results:** `section6/results/s6_development_{gaussian_hmm,hsmm}.json` and `power_{gaussian_hmm,hsmm}.json`, each with a sha256 sidecar. Each records its provenance: code hashes and the A28-A31 manifest.
- **Synthetic checks:** `synth_validation_a31r.json`, `synth_check_a31r.json`.
- **Chain:** `section6/results/overnight_log.txt`.
- Code version a0323ed24d68e896 is unchanged.
- **Not opened:** the old `q_power_*` logs from the stopped run.
