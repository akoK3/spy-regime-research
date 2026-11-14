# spy-regime-research

This repository asks two questions about intraday SPY volatility regimes:

1. Do feature-based regime detectors (HMM, Student-t HMM, HSMM; BOCPD as secondary) detect SPY volatility-regime breaks better than models that see only returns?
2. Do other markets (TLT, HYG, gold, USD) respond around the breaks they detect?

The work is pre-registered and amendment-driven:
- every protocol change is a dated, hashed amendment;
- every step is a row in `METHODS_LEDGER.md` (sidecar `METHODS_LEDGER.sha256`; rows only via `section5/s5_ledger.py add`);
- detectors were selected and frozen on training data before the evaluation periods were read through a guarded, logged, one-shot loader.

Facts below are quoted from the cited files. Where this README and a cited file disagree, the file is right.

## Data and eras

| Era | Source | Training (TRAIN) span | Evaluation span |
|---|---|---|---|
| LEGACY | HF data library "clean" 1-min bars (SPY, TLT, HYG) | 2003-01-02..2018-12-21 (4,022 sessions) | 2019-01-02..2022-03-04 (800 sessions) |
| RAW | HF data library "raw" 1-min bars, SPY from IEX (`section5/s5_a38.py`); TLT and HYG raw 1-min files | 2022-03-07..2024-12-23 (705 sessions) | 2025-01-02..2026-10-12 (445 sessions) |

- Gold is XAU/USD spot and USD is the Dukascopy dollar index, both as 1-min bid/ask midpoints (`SECTION7_FACTS.md` §1).
- Spans and session counts: `REPRODUCIBILITY_FACTS.md` §2–3, `section5/s5_eval_loader.py` (`DEV`, `EVAL`), `section5/results/evaluation_{LEGACY,RAW}.json`.
- The canonical panels and source zips are **not in git**. Their SHA-256s are in `REPRODUCIBILITY_FACTS.md` §3.

## Structure

| Path | Contents |
|---|---|
| `step*.py`, `write_*.py`, `section431_step3_all_in_one_results/`, `frozen_documents/`, `SECTION4_COMPLETE.md`, `FEATURES_REFERENCE.md` | Section 4: causal feature construction (1-min returns, realized-volatility windows, causal 20-session seasonal baselines `__sadj`, volume, jumps), audits, the frozen feature matrix and nested folds |
| `SECTION5_PROTOCOL.md`, `AMENDMENT_A6.md`…`AMENDMENT_A38.md` | Section 5 protocol and every amendment, each with a `.sha256` sidecar (the amendments in force at the freeze are listed in `section5_freeze.json`, key `amendments`) |
| `section5/` | Detection code: models `s5_models.py`, event rule `s5_events.py`, guards `s5_guard.py`, the freeze `s5_freeze*.py`, the evaluation driver `s5_eval513.py`; results in `section5/results/` |
| `section6/` | Cross-asset tests H2–H4 (`s6_*.py`); results in `section6/results/` |
| `*_REPORT.md`, `PILOT_REPORT*.md`, `D2_REPORT.md`…`D6_REPORT.md` | Pilots, gates and diagnostics in time order |
| `cold_audit_*.md`, `section5_cold_audit*.md`, `FABLE_*AUDIT.md`, `PREFREEZE_AUDIT.md`, `POST_EVAL_AUDIT.md`, `OPEN_AUDIT_FINDINGS*.md`, `COLD_AUDIT_STATUS*.md` | Independent audits and their follow-up status |
| `SECTION5_DISCLOSED_LIMITATIONS.md`, `SECTION6_DISCLOSED_LIMITATIONS.md` | Disclosed limitations |
| `SECTION7_FACTS.md` | Cross-asset methods and results, development and evaluation, with sources |
| `REPRODUCIBILITY_FACTS.md`, `REPRODUCE.md` | Environment, hashes, run order; how to verify and rerun |

## The freeze (2026-11-12)

Source: `section5/results/section5_freeze.json` (SHA-256 `846c1aaa…`) and `section5/results/freeze_run_record.json`.

- **H1 on development data** (Holm over the three H1 families; BOCPD is secondary): Gaussian HMM rejects (Holm p 0.0014), HSMM rejects (p 0.0003), Student-t HMM does not (p 0.103). Key `h1_verdicts`.
- **H2 primary detector:** Gaussian HMM. Key `h2_primary_detector`.
- **RAW Gaussian HMM setup:** K = 4; feature `rv10_partial90__sadj`, plus the 5-minute return; era threshold 16.98211669921875 (log-odds; bisection to 0.2 alarms per session on calibration sessions 2024-10-02..2024-12-23). Keys `setups`, `thresholds`.
- **Integrity:** code version `a0323ed24d68e896`. All 8 era thresholds equal their recomputation (absolute difference 0.0). Feature parity passed for both eras (`freeze_run_record.json`).

## Evaluation results

**These are not confirmatory.** Both evaluation periods carry the label "adaptive/exploratory (previously exposed period)", with `confirmatory: false` (A26; `AMENDMENT_A26.md`). The LEGACY period was previously exposed (4.3.0-A1). A July–September 2026 daily pilot overlapped both periods (ledger disclosure D6).

Effects use 95% day-cluster bootstrap intervals; there are no p-values on the evaluation path (A36 5g). Detector: frozen Gaussian HMM, feature model minus the returns-only baseline.

| | LEGACY 2019-01-02..2022-03-04 | RAW 2025-01-02..2026-10-12 |
|---|---|---|
| H1(a) pAUC gain on stable-day splices | +0.084 [0.053, 0.116] (79 stable days) | +0.194 [0.152, 0.241] (115) |
| H1(b) QLIKE gain, next 60 min | +0.049 [0.036, 0.065] (12.6% of baseline) | +0.118 [0.083, 0.159] (27.1%) |
| H1(c) FOMC hit-rate difference (secondary) | +0.42 [0.21, 0.63] | +0.14 [0.00, 0.36] |
| Alarms per session, feature / baseline | 0.214 / 0.141 | 0.137 / 0.276 |

Source: `section5/results/evaluation_LEGACY.json`, `evaluation_RAW.json`, key `families.gaussian_hmm`.

**Cross-asset (H2–H4, Gaussian HMM breaks):** no primary test rejected, in development or on the evaluation periods (218 breaks).
- **H2:** same-window return in TLT, HYG, gold or USD. Evaluation Holm p ≥ 0.213.
- **H3:** next-day volatility. In development, the gamma interval lies wholly below 0 for TLT and gold, reported as a transient response.
- **H4:** confirmation.
- **The evaluation-period null control failed** for H3 TLT (0.110) and H3 gold (0.305), so the evaluation H3 results are not reliable (S6-D5).

Source: `SECTION7_FACTS.md` §7–9; `section6/results/h2_evaluation_gaussian_hmm.json`, `s6_evaluation_gaussian_hmm.json`.

**Independent reproduction:** the MarketLens repository (`acceptance/acceptance_report.json`) reproduces all 344 Gaussian HMM runs of `evaluation_RAW.json` exactly from byte-identical copies of the frozen model and code (ledger rows of 2026-11-14).

## After the evaluation

- **Bloomberg data check:** RAW panel vs Bloomberg 1-min bars, correlation SPY 0.950 and HYG 0.795; `section5/results/bloomberg_comparison.json`.
- **Post hoc sensitivity analyses**, labelled as post hoc in the ledger.
- **A live forward test of the frozen RAW Gaussian HMM (MarketLens),** pre-registered in the ledger (v1, then v2: SPY bars from all IEX trades). Its first session is recorded in MarketLens's forward-test log.

## Reproducing

See `REPRODUCE.md`.
