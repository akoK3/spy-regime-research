# Report, 2026-11-10 evening: audit status refreshed, HYG data gap diagnosed, freeze manifest

## Bottom line

- **Both audit documents are refreshed and recopied to `project_upload`.**
  - `COLD_AUDIT_STATUS.md` now lists every finding with its status and the fixing amendment or commit.
  - `OPEN_AUDIT_FINDINGS.md` lists what is still open: 15 items, all Low except audit-1 #10. None affects a primary computation.
- **The HYG data gap comes from the placebo rule, not the HYG data.**
  - A31 placebos are matched on SPY only and drawn from earlier sessions. HYG coverage only starts in 2008-2010, so most HYG placebo windows fall in sessions with no HYG data.
  - My earlier guess (HYG's many zero returns) was **wrong**.
  - No test was changed.
- **A32, A33 and A33.1 were already in the freeze manifest** (added when each was written).
  - `freeze_ready()` now passes: all 14 amendments A21-A33.1 are ADOPTED with matching sidecars. That is a check only; no freeze was written.
  - A test now pins them (`s5_tests_freeze_prep.py` 12/12).
- No freeze, no O8, no era calibration.

## 1. Audit status (snapshots of the A16 versions kept as `COLD_AUDIT_STATUS_v6_A16.md` and `OPEN_AUDIT_FINDINGS_v5_A16.md`)

| Audit | Resolved | Disclosed | Open |
|---|---|---|---|
| Cold audit 1 (22) | 12 (new: #13 by A22 rule 3c; #17 by the data-hash preflight, commits 55cfc4e / 01ac960 / 9124c67) | 4 | 6: #10 Medium; #12, #16 (partly), #18, #20, #21 Low |
| Cold audit 2 (21) | 16 (new: #14, cache stamp and Section 6 cache, commit 9124c67) | 0 | 5 Low: #10, #11, #12 (Section 5 only), #13 (partly), #15 |
| O9 (12) | 5: M1 (A25), L1, L3, L8, L9 (commit f03a505) | 7: M2, M3, L2, L4-L7 (`SECTION5_DISCLOSED_LIMITATIONS.md`) | 0 |
| Fable (17) | 11: M1-M4, L4-L6, L12 (commit 9124c67); M5, L1, L10 (A31); L5 (manifest through A33.1) | 2: L8 (in A29), L11 (A27 row) | 4 Low: L2, L3, L7, L9 |

**Before any evaluation-period run:** Fable L3 (the A26 label must be attached to joint outputs) is the open item that matters.

## 2. HYG data gap (label-free; `section6/s6_hyg_gap.py`, hashed before it ran; output `section6/results/hyg_gap/hyg_gap.json`)

Counts only: no return comparison, no test, no H2 code change. TLT and gold are counted the same way for contrast.

**Where breaks are lost** (Gaussian / HSMM; the 30-minute window after T):

| | HYG | TLT | Gold |
|---|---|---|---|
| Breaks (A32 units, burn-in passed) | 600 / 549 | 600 / 549 | 600 / 549 |
| Asset unavailable in the break's own session | 300 / 283 | 183 / 190 | 162 / 161 |
| Window past the close | 20 / 24 | 20 / 24 | 20 / 24 |
| Fewer than 10 earlier sessions with data | 22 / 18 | 6 / 8 | 1 / 1 |
| **Fewer than 10 usable placebos** | **214 / 195** | 163 / 111 | 106 / 94 |
| Used by the A32 statistic | 44 / 29 | 228 / 216 | 311 / 269 |
| Placebo windows with the asset unavailable | **78% / 81%** | 61% / 62% | 51% / 51% |
| Usable placebos per usable break (median, 10th-90th pct) | 6 (1-11) / 5 (1-10) | 10 (4-15) / 11 (5-16) | 13 (5-19) / 13 (5-19) |
| E1 evaluable | 59 / 44 | 250 / 222 | 315 / 269 |

**Cause.**
- A31 / A28 1d placebos are drawn from **earlier sessions of the era**, matched on SPY alone, so they are not conditioned on the asset being available.
- HYG coverage starts late: LEGACY 6 available sessions in 2008, 71 in 2009, 141 in 2010, then about 215-250 per year.
- So for HYG breaks, most earlier-session placebos fall before HYG coverage, or on unavailable days. Only 5-6 usable placebos remain per break, below the 10 that E1 and the A32 statistic require.
- The H2 primary (A33 G6) draws its pool from **all sessions of the era where the asset is available**, so it keeps 242-280 HYG breaks.

**Not the cause.**
- HYG's zero returns: no window had a flat median, and flat 30-minute windows are 0-2.5% by year.
- Missing minutes: windows with no data are 0%.
- HYG's share of exactly-zero one-minute returns is high (43-62% in LEGACY, 18-36% in RAW), but no exclusion rule was triggered by it.

**Also affected, without a minimum to show it.** H3 uses the same placebos with no per-break minimum: HYG has 243 breaks with 1,523 placebos (6.3 per break; TLT 10.1, gold 12.9). The H3 HYG result was computed as specified, but rests on few placebos per break.

**Options (your decision; nothing changed):**
1. **Recommended:** an amendment for the **descriptive and exploratory parts only** (E1 and the A32 statistic). Draw each asset's placebos from sessions where that asset is available, with the same matching and causal rule. Recompute only those parts, labelled as changed after the diagnosis. Primary tests untouched.
2. Lower the minimum of 10 placebos for E1 and A32. This keeps more breaks, but each reference is noisier.
3. Leave as is and disclose: HYG E1 and A32 rest on 29-59 breaks, and H3 HYG on about 6 placebos per break.

## 3. Freeze manifest

`s5_amendment_manifest.AMENDMENTS` = A21-A31, A32, A33, A33_1.
- `freeze_ready()` passes. It also checks that the required results exist. This is a readiness check only; nothing was frozen.
- The Section 6 fingerprint (not yet written) covers every `section6/*.py`, including `s6_h2.py` and `s6_hyg_gap.py`.

## Files

- `COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md` (+ sidecars, v6/v5 snapshots), copied to `project_upload/`.
- `section6/s6_hyg_gap.py`; `section6/results/hyg_gap/hyg_gap.json`.
- Ledger rows for each.

---

# H2 report, 2026-11-10 (A33 / A33.1 chain done 17:23 New York)

## Bottom line

**H2 (protocol 5.0 test, as pre-registered) is not rejected for any asset, with either detector.**
- No detector rejects any asset under Holm, BOCPD and Student-t included.
- The strongest result is gold drifting up after breaks: Gaussian +0.027% vs placebo +0.002%, raw p 0.037, Holm 0.15.
- This is development (TRAIN-span) data only. No freeze, no O8, no era calibration.

## Chain

| Time (NY) | Step |
|---|---|
| 16:48 | First synthetic check (planted 0.05) failed: planted TLT rejected 75% < 80%. Kept on record |
| 17:17 | A33.1 adopted (your decision): planted 0.08, criteria unchanged, disclosed as raised after the 75% |
| 17:22 | Synthetic check **PASS 13/13**; gate A28-A33.1 passed |
| 17:22 | Power done (0.5 min) |
| 17:23 | H2 dev run done for Gaussian HMM and HSMM, about 70 s each, exit 0 |

## Synthetic check (10,000 draws; 200 null / 40 planted)

- **No effect:** rejection 4.5-7.5% (independent) and 4.5-5.5% (vol-clustered).
  - These are the same numbers as the first run: same seeds, and the null does not depend on the planted size.
- **Planted:** TLT 95%, HYG 97.5%, gold 97.5% rejected; USD (planted null) 5%.
- **Planted bias:** within tolerance for every asset.
  - The bias is identical to the first run, because an additive shift moves the estimate and the target equally.
  - Targets: TLT 0.00144, HYG -0.00096, gold 0.00192.

## Power (A33 G11, two-sided at 0.05/4, 10,000 draws)

| | Gaussian (600 breaks) | HSMM (549 breaks) |
|---|---|---|
| Power at delta = 0.10 / 0.15 / 0.20 SD | 0.45 / 0.85 / 0.995 | 0.455 / 0.855 / 0.985 |
| Minimum detectable shift | 0.15 SD of a break's 30-minute return | 0.15 SD |

This is an upper bound: only 280-420 breaks per asset have the asset available.

## H2 primary: (T, T+30], signed cumulative log return; Holm m = 4

| Asset | Gaussian: n, break mean vs placebo mean, p (Holm) | HSMM: n, break vs placebo, p (Holm) |
|---|---|---|
| TLT | 397, +0.0036% vs +0.0024%, p 0.90 (1.00) | 335, -0.019% vs +0.001%, p 0.085 (0.27) |
| HYG | 280, -0.0029% vs -0.0025%, p 0.95 (1.00) | 242, -0.011% vs -0.004%, p 0.46 (0.46) |
| Gold | 418, **+0.027%** vs +0.002%, p **0.037** (0.15) | 364, **+0.025%** vs +0.002%, p 0.068 (0.27) |
| USD | 13, -0.009% vs +0.001%, p 0.64 (1.00) | 12, -0.049% vs -0.005%, p 0.082 (0.27) |

- Placebo pools average about 800-1,400 matched candidate times per break (65-70 for USD).
- USD has only 12-13 breaks (2018 LEGACY only): not informative.

## Secondary (BH over the horizons, stressed-to-calm and other detectors)

- **Only one survives BH: TLT over (T - 30, T], for both detectors.**
  - TLT rises before the confirmation: Gaussian +0.055% (p 0.0002, BH 0.006); HSMM +0.070% (p 0.0002, BH 0.006).
  - This is the window between the streak start and confirmation: TLT moves up while SPY's break is still being confirmed.
- **Other raw p < 0.05, not significant after BH:**
  - HYG pre-30 down (p 0.004 / 0.036);
  - gold +60 up (Gaussian, p 0.021);
  - gold +5 and +15 up (HSMM, p 0.006 / 0.008).
- **Gold is positive at every post-T horizon for both detectors** (+5 to +60).
- **Detector dependence (S2):**
  - gold's direction is positive for all four detectors (raw p 0.036-0.074);
  - no Holm verdict on any detector, so the verdicts agree.

## Exploratory (A33 rule 4): A32 deseasonalised |return|, specified after seeing the H3/H4/A30 results; uncorrected

- **Breaks show larger absolute moves than placebos after T:**
  - TLT +0.36 / +0.36 at +30 (Gaussian / HSMM; p 0.0004 / 0.0005);
  - gold +0.53 / +0.73 (p 0.0001);
  - similar at +5, +15 and +60.
- **The pre-window (T - 30, T] is larger still:** about +1.0 for TLT and gold (descriptive).
- **Read with care:**
  - Breaks are, by construction, times when SPY moves into a high-volatility state. The placebos are matched on SPY volatility before S, not at T.
  - So larger asset |returns| may reflect market-wide volatility at the break rather than an asset-specific response.
  - The signed test (H2 primary) shows no consistent direction.
- **HYG is thin here:** only 29-49 breaks have a defined deseasonaliser, likely because of HYG's many zero one-minute returns.

## E1 footprint taxonomy (descriptive): thin

- Only 56 (Gaussian) and 43 (HSMM) breaks are classifiable. 482-524 have no evaluable TLT or HYG move (HYG data), and 20-24 have a window past the close.

| Category | Gaussian breaks vs placebos | HSMM breaks vs placebos |
|---|---|---|
| SPY-only | 55% vs 60% | 77% vs 61% |
| Credit stress | 9% vs 7% | 7% vs 5% |
| Flight to safety | 2% vs 0.4% | 2% vs 2% |
| Dollar-driven | 0% vs 0% | 2% vs 1% |
| Other | 34% vs 33% | 12% vs 31% |

- No clear footprint beyond chance on this sample.

## For your attention

1. **The HYG and E1 data gap.** The primary H2 uses 242-280 HYG breaks, but E1 and the exploratory statistic use only 29-56. Both need HYG data in the placebo windows and in the prior 20 sessions. I can diagnose the cause, label-free, if you want.
2. **The TLT pre-T rise** is the one secondary result that survives correction. It is consistent with the A30 lead-lag description (TLT often moves before S).

## Files

- `section6/results/`:
  - `h2_50_synth_a33.json` / `h2_50_synth_check_a33.json` (first run, FAIL, kept);
  - `h2_50_synth_a33p08.json` / `h2_50_synth_check_a33p08.json` (PASS);
  - `h2_50_power_{gaussian_hmm,hsmm}.json`;
  - `h2_development_{gaussian_hmm,hsmm}.json`;
  - `h2_log.txt`.
- Each is written once, with a sidecar and provenance (code hashes; A28-A33.1 manifest).
- Code version a0323ed24d68e896 is unchanged.

---

# H2 report, 2026-11-10 (A33 chain stopped 16:48 New York)

## Bottom line

- **The H2 chain stopped at the synthetic check, as your rule requires.** 12 of 13 criteria pass. The one failure is planted TLT, rejected in 75% of replicates against the required 80%.
- **Nothing was run on real data:** no H2 power and no H2 dev run, so no H2 output on real data exists.
- **The earlier A32 chain** was stopped at 16:39 during its synthetic step, at your request. Its partial synthetic file was not opened.
- No freeze, no O8, no era calibration.

## A33 synthetic check (protocol 5.0 test; 10,000 draws; 200 null and 40 planted replicates)

| Check | TLT | HYG | Gold | USD | Criterion |
|---|---|---|---|---|---|
| No effect, independent: rejection at 0.05 | 7.0% | 7.5% | 4.5% | 6.5% | <= 8.1%: pass |
| No effect, vol-clustered: rejection at 0.05 | 5.5% | 4.5% | 5.0% | 5.5% | <= 8.1%: pass |
| Planted: mean estimate minus target | -0.000003 (target 0.0009) | +0.00004 (target -0.0006) | +0.00009 (target 0.0012) | (planted null) | within max(2 SE, 10% of target): pass |
| Planted: rejection at 0.05 | **75%: FAIL** | 65% | 80%: pass | 5% | TLT and gold >= 80% |

- **Any Holm rejection:** 6.0% (independent) and 2.5% (vol-clustered) with no effect, and 85% with the planted effect.
- **What the failure means:** the test is calibrated under the null, and it recovers the planted effect without bias. TLT's 75% reflects the effect size I chose in A33 rule 3b: a per-minute shift of 0.05 x the base SD, about 0.27 SD of a 30-minute return. With about 220 TLT breaks per replicate, that gives roughly 75-80% power. With 40 replicates the Monte Carlo SE of 75% is about 7 points. It is not a defect of the test, but it fails the criterion as written.

## Decision for you

1. **Recommended:** amend A33 rule 3b to a planted shift of c = 0.08 (TLT +, HYG -, gold +; USD 0), keeping every criterion, and rerun under a new tag. Disclosed: this is chosen after seeing the 75%.
2. Or rerun with the same planted size and 200 planted replicates, so the rejection rate is estimated precisely. If the true rate is about 0.77, it would fail again.
3. Or accept the check as is (a deviation from rule 3c, with your approval).

After your decision the chain reruns from the synthetic step with `powershell -NoProfile -ExecutionPolicy Bypass -File section6
un_h2.ps1 -Tag <new tag>`. Synthetic is about 4 min; then power and the H2 dev run (Gaussian, HSMM; TRAIN only).

Files: `section6/results/h2_50_synth_a33.json`, `h2_50_synth_check_a33.json` (written once, sidecars), `h2_log.txt`.

---

# Report, 2026-11-10 (chain done 15:55 New York; addendum 16:40)

## Addendum 1: A29 3b intervals for H3 (post-hoc reporting only, at your request)

These are two-sided 95% basic week-block intervals, computed within era with 9,999 resamples and seed 0, as in the primary H3 test.
- They come from `section6/s6_posthoc_h3_ci.py`, which was hashed in the ledger before it ran.
- The script rebuilds the H3 rows exactly. Each rebuilt gamma equals the stored dev-run gamma, and so does each n.
- No test was changed. The p-values, Holm and BH results stand as written.

| | Gaussian HMM | HSMM |
|---|---|---|
| H3 TLT | gamma -0.164 [-0.220, -0.107] (402 breaks) | -0.139 [-0.206, -0.070] (339) |
| H3 gold | -0.185 [-0.242, -0.129] (420) | -0.156 [-0.223, -0.089] (373) |

- **All four intervals lie wholly below 0.** Under A29 3b this is reported as a **transient cross-asset response**: same-day TLT and gold moves that the next day does not continue beyond the prior-hour control. It is not a calming effect.
- Read with H4 (A29 3b), H4 shows no confirmation gain.
- **Gaussian TLT caveat:** the placebo-filter control flagged TLT, with delta +0.030 [+0.008, +0.052]. Even shifting gamma by that amount leaves the interval below 0: the upper end goes from -0.107 to about -0.08.
- Output: `section6/results/posthoc/h3_ci_a29_3b.json`, written once, with a sidecar.

## Addendum 2: H2 was not run, and is not yet runnable

**Why it is not in the report:**
- **Out of scope by design.** A28 rule 2 says "H2 unchanged". `s6_run.py` states "H2 is not computed here". The dev run approved in the ledger (2026-11-10 03:42Z) covers H3 and H4 only.
- **It belongs to the final evaluation.** H2 is a primary hypothesis of protocol 5.0, with its own Holm family across the 4 assets (5.11). It is run with the **H2 primary detector chosen at the 5.12 freeze** (A9 item 2) at the 5.13 era-level thresholds, and A26 labels that evaluation-period run.
- **No H2 code exists.** The cold audit lists "All of H2, S1, S2, E1, E2 and D1" as not implemented. Nothing has been written since.

**What is needed before the freeze:**
1. **An H2 amendment fixing what 5.0 leaves open**, decided by you before any code. Only the 30-minute slot is fixed so far (ledger 03:42Z).
   - **Test statistic:** how breaks are aggregated (for example, the mean cumulative return over breaks against the 10,000-draw placebo distribution of that mean), sidedness, and the p-value rule.
   - **Horizons:** which one is primary. 5.0 names T to T+30 as the primary window and lists -30 and +5/15/30/60 min; the status of the others needs fixing.
   - **Placebo draws:** A28 1d says H2 keeps its pre-registered placebo distribution exactly, so the before-the-break and past-alarm rules do not apply. Eligibility still needs fixing:
     - the pool: which sessions are eligible, and whether later sessions may be used;
     - alarm proximity;
     - whether a placebo may cross the close.
   - **T and the asset clock:** T = T_c, and the LEGACY offset.
   - **S1, S2, E1, E2:** operational definitions. E2 (overnight gaps) needs its own data definition.
2. **Code, unit tests, a synthetic check and a power check**, as done for H3 and H4.
3. **The H2 code in place before the freeze and the Section 6 fingerprint.** It has to be hashed with the rest of the Section 6 code before any evaluation output exists, so it cannot adapt to results.
4. **Optional:** a TRAIN-only development run of H2 on Gaussian and HSMM, as for H3 and H4. This needs your approval.

Until then the freeze manifest is ready on A21-A31, but H2 cannot run after the freeze.

**Decision for you:** may I draft the H2 amendment (items in 1) for your approval?

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

1. **A29 3b interval for H3:** done; see Addendum 1.
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
