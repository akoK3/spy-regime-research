# Post-evaluation audit, 2026-11-12 (read-only)

**Scope.** This is a read-only audit of the evaluation chain run on 2026-11-12 (09:01 to 20:09 New York time). The audit opened only the result files, the access log, the one-shot markers, the freeze, the fingerprint and the code. It read no market data, re-ran nothing, and changed nothing except writing this file. The check script is `C:\Users\kakij\AppData\Local\Temp\claude\013256dc0f49afb7\a7e6433a-3300-44f7-8175-facddf1268cf\scratchpad\audit.py`.

## Flags

| # | Severity | Finding |
|---|---|---|
| F1 | **Error in the report** | HSMM H1(b), LEGACY. The file gives 0.10146, which rounds to **0.101**. `reply_latest.md` (line 20), ledger row `METHODS_LEDGER.md:683`, the commit message of 34ec7d1 and the chat summary all say 0.102. Its interval (0.085, 0.120) is correct. |
| F2 | **Error in the report** | The H3/H4 secondary family (BH over 76 tests). The smallest raw p is **detector_dependence.bocpd.H3_GOLD: p 0.018, gamma +0.134, n 155, BH 0.795** (Holm within that detector 0.108). It is not FOMC-day H4b (p 0.021, BH 0.795). The report (line 53) and the s6 ledger row are wrong. The conclusion is unchanged: no secondary survives BH. |
| F3 | Not an error | The access log has **3 allowed reads per era, not 1**. Each era has one 5.13 read (A36 4a), one Section 6 coverage read (`s6_eval.coverage`, A36 6a) and one Section 6 data read (`s6_eval.eval_era`, A36 4b). These are three distinct purposes in the code path, not reruns (details below). |
| F4 | Minor | Three exact halves are rounded half-up in the report: 0.625 to 0.63, 0.125 to 0.13 and 0.375 to 0.38. Python's `round` would give 0.62, 0.12 and 0.37. This is a rounding convention, not an error. |
| F5 | Minor | `s6_evaluation_gaussian_hmm.json` contains 5 `NaN` tokens (the not-evaluable anchor_T0_at_S H4b entry). `coverage_evaluation.json` contains 3,873 `NaN` tokens (metrics of missing data). Python reads both files, but they are not strict JSON. |
| F6 | Minor | The two 5.13 files (`evaluation_{LEGACY,RAW}.json`) do not record the freeze hash or the code version. The link to the freeze runs through the one-shot markers (which hold the freeze hash) and the per-family `model_sha256`. `a38_filter_check.json` records the freeze hash but not the code version. |

To correct F1 and F2 you would need a correction row in the ledger (it is append-only) and an edit to `reply_latest.md`. Neither has been done: this audit is read-only.

## (1) Report numbers against the result files

All other numbers in the evaluation section of `reply_latest.md` match the files at the precision shown (78 checks). They cover:
- **5.13:** H1(a), H1(b) and H1(c) effects and 95% intervals for 3 families × 2 eras; BOCPD = 0; H1(c) n 24 and 14; 800 and 445 sessions.
- **Section 6:** breaks 171/47/218; 0 removed by burn-in; no alerts.
- **H2 primary:** n, p and Holm p for 4 assets; per-era minima LEGACY GOLD 0.059 and RAW DOLLAR 0.038 (Holm 0.150).
- **H3/H4 primary:** n, gamma or gain, p and Holm p for 6 tests.
- **H2 secondary:** BH survivors exactly HYG pre30 (0.0078) and DOLLAR pre30 (0.0156), out of 39.
- **H3/H4 secondary:** no BH survivor among 76; fed H4b p 0.021, BH 0.79.
- **A34:** H3 sensitivity BH all 1.0.
- **A38:** 1,360 splices, 136 dropped (10.0%), 115 stable days; H1(a) delta, interval and MDE for 4 families; H1(b) intervals all include 0; rule 2 labels.

The exceptions are F1, F2 and F4 above.

**Description check.** "136 dropped, none buildable on the Clean panel": all 136 have reason `not buildable on the Clean panel (s5_d2.finite_ok)`. Of these, 33 are null splices and 103 are break splices; there are no build errors.

## (2) Access log (`section5/results/eval_access_log.txt`, 20 lines, all on 2026-11-12/13 UTC)

| UTC | Event | Era / kind | Purpose |
|---|---|---|---|
| 14:01:21-24 | PRECHECK, PRECHECK PASSED | LEGACY | A37 2a checks before the marker (no read) |
| 14:01:25 | ALLOWED | LEGACY | 5.13 panel (SPY panel and ETF file, evaluation span), section6=False |
| 14:18:40-42 | PRECHECK, PRECHECK PASSED | RAW | as above |
| 14:18:43 | ALLOWED | RAW | 5.13 panel, section6=False |
| 16:38:02 | ALLOWED | LEGACY | Section 6 coverage columns (5 assets plus GOLD/DOLLAR stale flags), section6=True |
| 16:38:07 | ALLOWED | RAW | Section 6 coverage columns, section6=True |
| 16:38:11 | ALLOWED | LEGACY | Section 6 return columns, section6=True |
| 16:38:16 | ALLOWED | RAW | Section 6 return columns, section6=True |
| 00:49:58 (13 Nov) | ALLOWED A38 | kind=raw | `hfdatalibrary_raw_1min_1tickers_2026-11-11.zip` |
| 01:01:26 (13 Nov) | ALLOWED A38 | kind=clean | `hfdatalibrary_clean_1min_1tickers_2026-11-11.zip` |

- **Refusals:** 0 REFUSED lines.
- **Reruns:** no request appears twice for the same purpose.
- **A38:** exactly one raw read and one clean read.
- **5.13:** exactly one read per era.
- **Section 6:** two reads per era. In `section6/s6_eval.py`, `coverage()` (line 72) reads once per era and only if `coverage_evaluation.json` does not exist yet. `eval_era()` (line 88) reads the return columns once per era. Both are in the single `s6_eval.py run` (F3).

## (3) Labels; no p-values or verdicts in 5.13

- **Labels:** all 7 evaluation outputs carry `a26_label = "adaptive/exploratory (previously exposed period)"`, `confirmatory = false` and `period = "evaluation"`. The 7 files are `evaluation_LEGACY`, `evaluation_RAW`, `coverage_evaluation`, `s6_evaluation_gaussian_hmm`, `h2_evaluation_gaussian_hmm`, `a34_evaluation_gaussian_hmm` and `a38_filter_check`.
- **No p-values or verdicts in 5.13:** neither 5.13 file has any key named p, p_*, *_p, holm*, reject*, verdict*, pass(ed), significan* or decision. The words "p-value" and "Holm" each appear once in each file, only inside the `statistics` string "...no p-value, no fold test, no Holm (A36 5g)". Each file has only effects, 95% intervals, counts, thresholds and alarm rates.

## (4) Freeze, markers, fingerprint, code version

- **Freeze:** `section5/results/section5_freeze.json` has sha256 `846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94`, which equals the run token and its sidecar. Its mtime is 2026-11-12 03:22:26 NY (the freeze). There are no uncommitted changes to tracked files; it was last committed in 3b9e68d.
- **Lock:** `ERA_CALIBRATION.lock` has sha256 `db42bedef5c28b915e042a2494b60657d2be62948ba9453bd73b6daf2aad6e67`, mtime 03:22:26 NY. This matches `REPRODUCIBILITY_FACTS.md`.
- **Code version:** `s5_guard.code_version()` now returns `a0323ed24d68e896`, the same as in the freeze. The `provenance.code` of s6, h2, a34 and coverage also equals `a0323ed24d68e896`.
- **Fingerprint:** `section6/results/s6_fingerprint.json` has sha256 `815c77623d6f14896becaef56356f2f55df5bfc9292281c4da6af876349e5de8`, created 2026-11-12T14:01:12Z. All 31 file hashes equal `s6_fingerprint.current()` on disk: no difference.
- **Frozen models:** the 8 `model_sha256` values in the 5.13 files (4 families × 2 eras) are all present in `section5/results/frozen_models`. In both eras the frozen feature threshold equals its recomputation.
- **One-shot markers (each holds the freeze hash):**

  | Marker | Written (NY) |
  |---|---|
  | `evaluation_LEGACY_RAN.marker` | 09:01:24 |
  | `evaluation_RAW_RAN.marker` | 09:18:42 |
  | `a38_raw_RAN.marker` | 19:49:58 |
  | `a38_clean_RAN.marker` | 20:01:26 |

  Each matches its ALLOWED line in the access log. No other marker exists. Section 6 relies on write-once outputs rather than a marker.

## (5) Realized quantities

**Alarm rates per session in 5.13** (feature model vs baseline; the calibration target at TRAIN was about 0.19):

| Family | LEGACY feature | LEGACY baseline | RAW feature | RAW baseline |
|---|---|---|---|---|
| Gaussian HMM | 0.214 | 0.141 | 0.137 | 0.276 |
| Student-t HMM | 0.215 | 0.168 | 0.117 | 0.310 |
| HSMM | 0.159 | 0.101 | 0.200 | 0.306 |
| BOCPD | 0.186 | 0.186 | 0.187 | 0.187 |

In LEGACY the feature models alarm more often than the baseline. In RAW they alarm less often, and the baselines run well above the 0.19 calibration rate. H1(a) is a pAUC, so it is not tied to these thresholds. H1(c) hit rates are, so read them with these alarm rates in mind.

**Stable days:**
- 5.13 H1(a): LEGACY 79, RAW 115. All are used in splices: 400 null and 960 break splices per family.
- A38: 115, the same RAW days. 1,360 splices, 136 dropped (33 null, 103 break; 10.0%), so H1(a) is paired on 367 null and 857 break splices.

**Breaks in 5.13** (confirmed / fizzle / open at close):

| Family | LEGACY | RAW |
|---|---|---|
| Gaussian HMM | 171 / 503 / 7 | 61 / 278 / 5 |
| Student-t HMM | 172 / 439 / 10 | 52 / 190 / 1 |
| HSMM | 127 / 481 / 12 | 89 / 401 / 6 |
| BOCPD | 149 / 230 / 42 | 83 / 94 / 16 |

**Breaks in Section 6** (Gaussian HMM, confirmed calm-to-stressed):
- **LEGACY 171.** Every LEGACY confirmed break is labelled calm-to-stressed. All 171 have at least 3 assets available (18 with 3, 153 with 4). 3 breaks have fewer than 20 placebos. H4a calm-streak starts: 64 confirmed, 165 fizzle, 4 open.
- **RAW 47 of 61 confirmed.** Available assets: 4 with 2, 20 with 3, 23 with 4. 3 breaks have fewer than 20 placebos. H4a calm-streak starts: 16 confirmed, 45 fizzle.
- **Burn-in:** 0 removed in either era.

**H2 breaks skipped per asset** (of 218): TLT 10, HYG 27, GOLD 12, DOLLAR 25.

**Asset availability on evaluation sessions** (coverage file; unavailable / total):

| Era | SPY | TLT | HYG | GOLD | DOLLAR |
|---|---|---|---|---|---|
| LEGACY | 6/800 | 6/800 | 6/800 | 16/800 | 86/800 |
| RAW | 3/445 | 50/445 | **177/445** | 11/445 | 42/445 |

RAW HYG is unavailable on 40% of sessions. This is why RAW H2 HYG has only 25 breaks.

**Not evaluable or not tested:**
- `s6 anchor_T0_at_S.H4b`: not evaluable. 0 valid resamples (valid share 0.0), gain NaN, p null.
- `s6 detector_dependence.bocpd.H4a`: not evaluable, n 0.
- `s6 fed_split.fed.H4a`: evaluable but flagged low valid share (0.326; n 11, 8 positive; out-of-fold AUC 0.5 and 0.5).
- `s6 secondary.H3_stressed_to_calm_HYG`: n 1, p null.
- `h2 secondary.H2_stressed_to_calm_HYG_h30`: n 4, M and p null.
- Descriptive by design, not tested (p null, labelled "descriptive, not tested"): `s6 h3_prior_hour_before_S` (4 assets) and `exploratory_a32.X_*_pre30` in h2 and a34 (4 each).
- E1 footprint skips: h2 has 7 windows past close and 27 TLT/HYG not evaluable (n 184); a34 has 7 and 24 (n 187).
- 5.13: no family flagged; all H1(a), H1(b) and H1(c) cells were evaluated.

**A38 reproducibility (rule 1g):** the official 5.13 RAW H1(a)/H1(b) equal the A38 Raw-file rerun. The H1(a) difference is 0.0; the H1(b) difference is at most 4.3e-15 in absolute value (HSMM).
