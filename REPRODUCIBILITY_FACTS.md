# Reproducibility facts

Written 2026-11-12 (New York), while the joint evaluation (`s6_eval.py run`) was still running Section 6; A38 had not yet run. Facts only, each with its source. Items that change when the evaluation and A38 finish are marked **(pending)**.

## 1. Repository

| Item | Value | Source |
|---|---|---|
| Repository | https://github.com/akoK3/spy-regime-research | `git remote -v` |
| Branch | `main` | `git status` |
| Commit at the time of writing | `af1b7918dd86f7605b1c12d8e59f52bb7352815d` (2026-11-12 12:22:48 -0500) | `git log -1` |
| Commit of the freeze | `3b9e68d` (freeze document, run record, lock, ledger row); `c49d728` (ledger sidecar) | `git log` |
| Final commit after the evaluation and A38 | **(pending)** | |

Not in git (git-ignored, local only): the canonical panels, the source zip files, and `section5/results/frozen_models/` (`.gitignore`; `git check-ignore`).

## 2. Code version and frozen artefacts

| Item | SHA-256 | Source |
|---|---|---|
| Result-module code version (16 hex characters; hash over the result-module closure, `s5_guard.code_version`, `section5/s5_guard.py:86-90`) | `a0323ed24d68e896` | `section5/results/section5_freeze.json` key `code_version` |
| Freeze document `section5/results/section5_freeze.json` (= the CONFIRM_TOKEN) | `846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94` | `section5/results/section5_freeze.sha256` |
| Freeze run record `section5/results/freeze_run_record.json` | `26d865e97d0da4ff4ad94362001522aa807d180447028cc73ccf04150837fae2` | `section5/results/freeze_run_record.sha256` |
| Frozen-model manifest `section5/results/frozen_models/manifest.json` (8 models: 2 eras x Gaussian HMM, Student-t HMM, HSMM, BOCPD) | `edb78798544a8896c88f5a6b02857591d96f6764ed0d7f498685cbdbc0ac06dd` | `section5/results/frozen_models/manifest.sha256`; `freeze_run_record.json` key `frozen_models_manifest_sha256` |
| Era-calibration lock `section5/results/ERA_CALIBRATION.lock` (8 entries, 2026-11-12 08:02:57Z..08:22:26Z) | `db42bedef5c28b915e042a2494b60657d2be62948ba9453bd73b6daf2aad6e67` | file on disk (committed in `3b9e68d`) |
| Section 6 fingerprint `section6/results/s6_fingerprint.json` (created 2026-11-12T14:01:12Z) | `815c77623d6f14896becaef56356f2f55df5bfc9292281c4da6af876349e5de8` | `section6/results/s6_fingerprint.sha256` |
| Section 5 protocol `SECTION5_PROTOCOL.md` | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` | `section5_freeze.json` key `protocol_sha256` |
| Contamination registry | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` | `section5_freeze.json` key `contamination_sha256` |
| Completion record | `19812f9f619f029b949bdc9e123c78007a4e71bf668f214569a5bbe12577079a` | `section5_freeze.json` key `completion_record_sha256` |
| Amendments in the freeze | 19 entries, each with its SHA-256 and a matching sidecar | `section5_freeze.json` key `amendments` |
| Evaluation FOMC schedule `section5/results/h1c_schedule_times_evaluation.json` | `391366459f83a89e2442f05479774b49f8efac1479a92daf9ceda0e0d36b6865` | `section5/results/h1c_schedule_times_evaluation.sha256` |

Freeze outcome (from `freeze_run_record.json`): H1 passing families: HSMM, Gaussian HMM. H2 primary detector: Gaussian HMM. All 8 era thresholds equal their 5.13-path recomputation (abs diff 0.0). Feature parity passed: LEGACY 4,022 TRAIN sessions (2003-01-02..2018-12-21), RAW 705 (2022-03-07..2024-12-23).

## 3. Data files

Canonical panels and ETF files, checked by the finding-17 data-hash preflight (`section5/s5_preflight_data_hashes.py`; last saved result `section5/results/data_hash_preflight/data_hash_preflight.json`, 2026-11-09T00:51Z, verdict PASS; the preflight is rerun inside every guarded read, `section5/s5_eval_loader.py` `_checks`):

| File | SHA-256 |
|---|---|
| `section3_10_alignment_results/canonical_panel_LEGACY_1m.csv.gz` | `b5967d9691c547a3b8a277f97fe2a95e1b1c4a49e4d6476c008a08076ce098df` |
| `section3_10_alignment_results/canonical_panel_RAW_1m.csv.gz` | `f1b1c498dc76c7ef11e53a31fec655abacaf6458d8f3b9dd1827f9dd8ec91184` |
| `section3_4_etf_results/etf_observed_SPY_LEGACY.csv.gz` | `7cd10dfb3e5896b9574a53f35914ce43053705cff9c5ef7029ccb2b88a6c83f7` |
| `section3_4_etf_results/etf_observed_SPY_RAW.csv.gz` | `6c37b2798d3cc5740d71de94c34343d315fa274b95e50a5a7df081c1b7a5928d` |
| `section431_step3_all_in_one_results/a4_sec4_3_9_frozen_matrix_v2.csv` | `9378f93f79e358f98d9dcad3992c269cb9a823a15bf28e8a21dbe319763ebe86` |
| `section431_step3_all_in_one_results/a4_development_nested_folds_TRAIN.csv` | `06258e5a1645327a64aa07d155b59d20949c11c81ce657a26e4d44c27882adfc` |
| (four further Section 4 files) | listed in `data_hash_preflight.json` |

Panel paths: `section5/s5_eval_loader.py:21` (`PANELS`).

Source files (Section 2 inventory, `section2_audit_results/inventory.csv`, 2026-10-14):

| File | SHA-256 | Used for |
|---|---|---|
| `hfdatalibrary_clean_1min_5tickers_2026-10-03.zip` | `b6754832051ad5ff0a265439e35e100cc1fbef56cd3c067ff9b3ed50aa5d55ce` | LEGACY era (SPY, TLT, HYG Clean) |
| `hfdatalibrary_raw_1min_1tickers_2026-10-13.zip` | `a70a4d4cac85036e89746de1820bb0c066d581dddb2ee5310f057ac54ec0da37` | RAW era (SPY Raw) |
| `TLT_raw_1min.csv` | `c2b79b08235f21fb1c2f514f87a58bbfdbaebc3999566342696c496eb98bf0d1` | TLT RAW |
| `HYG_raw_1min.csv` | `543a7c194539c96844b266064b95f2b5dc12ec184e605caf93fe846128a7b9bf` | HYG RAW |
| `xauusd-m1-bid-2007-04-11-2026-10-02 - Copy.csv` | `6ab53e9dd2ecc668e14d951738ab20ac1c14cf0c86721664d00a7cb5c45ce198` | gold |
| `dollaridxusd-m1-bid-2017-12-01-2026-10-02.csv` | `d8f2dbcc13ed3a0b335afe415a42127c53b3a49140d9800829e06c834e77320d` | USD index |

A38 files (`AMENDMENT_A38.md:33-34`; checked in `section5/s5_a38.py` `HF` before each read):

| File | SHA-256 |
|---|---|
| `hfdatalibrary_raw_1min_1tickers_2026-11-11.zip` | `b6e9da59a38deca77be6d5819c3608645dfe87ec785ca98c6eb45b2554b2feaf` |
| `hfdatalibrary_clean_1min_1tickers_2026-11-11.zip` | `58f8f11245f398937cd23ab2d06ec5b170c4f7598521cfe402bc6bf2ac624c9d` |

Periods: LEGACY evaluation 2019-01-02..2022-03-04; RAW evaluation 2025-01-02..2026-10-12 (`section5/s5_eval_loader.py` `EVAL`).

## 4. Software

| Item | Value |
|---|---|
| Interpreter | `C:\Users\kakij\Downloads\research_hmm_env\Scripts\python.exe`, Python 3.12.10 (tags/v3.12.10:0cc8128, MSC v.1943, 64-bit) |
| numpy | 2.5.4 |
| pandas | 3.1.0 |
| scipy | 1.18.1 |
| scikit-learn | 1.9.1 |
| hmmlearn | 0.3.3 (installed but not imported by any `section5/*.py`; the models are implemented in `section5/s5_models.py`) |
| OS | Microsoft Windows 11 Home 10.0.26200 |

Source: `importlib.metadata` in the environment above, 2026-11-12.

## 5. Hardware

AMD Ryzen 7 7435HS, 16 logical processors, 15.7 GB RAM (`Win32_Processor`, `Win32_ComputerSystem`). All runs single process (`s6_eval.py` default `--workers 1`).

## 6. Run commands, in order

| # | Command (working directory) | Started | Finished | Duration | Output |
|---|---|---|---|---|---|
| 1 | `python s5_freeze_run.py run --confirm section5_freeze.json` (`section5/`) | 2026-11-12 04:09:25Z | 08:22:26Z | 4 h 13 min (fitting 3 h 39 min) | `section5_freeze.json`, `freeze_run_record.json`, `frozen_models/`, `ERA_CALIBRATION.lock` |
| 2 | `python s6_fingerprint.py write` (`section6/`) | 14:01:11Z | 14:01:12Z | 1 s | `section6/results/s6_fingerprint.json` |
| 3 | `python s6_eval.py run <abs path>\section5\results\section5_freeze.json 846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94` (`section6/`) | 14:01:12Z | **(pending)** | 5.13 LEGACY written 14:18:40Z; 5.13 RAW written 16:38:01Z (process suspended 14:25-16:33Z on the user's request, so about 12 min of RAW computing); Section 6 running | `section5/results/evaluation_LEGACY.json`, `evaluation_RAW.json`; `section6/results/coverage_evaluation.json`; further Section 6 files **(pending)** |
| 4 | `python s5_a38.py run <abs path>\section5\results\section5_freeze.json 846c1aaa...` (`section5/`), only if step 3 exits 0 | **(pending)** | | | `section5/results/a38_filter_check.json` |

Steps 2-4 run as one detached chain (a runner script outside the repository) that stops at the first non-zero exit; its log is `section6/results/eval_chain_status.txt`, with per-step stdout/stderr in `section6/results/eval_chain_*_stdout.txt` / `_stderr.txt`. The freeze's stdout/stderr: `section5/results/freeze_run_stdout.txt` / `freeze_run_stderr.txt` (stderr empty).

Earlier rehearsal (development data, temporary folder): full dress rehearsal freeze 5 h 29 min; A38-only rerun 6 min (`section6/results/dress_rehearsal.json`, `dress_rehearsal_a38.json`).

## 7. Guards and one-shot markers

- **Guarded read** (`section5/s5_eval_loader.py`, `_checks`): the A26 label module is ready, and a Section 5 read must come from inside `s5_eval_label.run_confirmatory_labelled`. The freeze must verify, the token must equal the freeze's SHA-256, and the amendment list must equal `s5_amendment_manifest.freeze_ready()`. The era-calibration lock must exist, the data-hash preflight must exit 0, the Section 6 fingerprint must match (Section 6 reads) and the era must be known. Each read is logged in `section5/results/eval_access_log.txt` (ALLOWED / REFUSED / PRECHECK).
- **Pre-marker check** (A37 rule 2a): `precheck` runs the same checks without reading, before any marker.
- **One-shot markers**, written immediately before the first evaluation read and containing the freeze SHA-256:
  - `section5/results/evaluation_LEGACY_RAN.marker` and `evaluation_RAW_RAN.marker` (path `section6/s6_eval.py:167`). Both exist. A marker without a result stops the driver.
  - A38: `section5/results/a38/a38_raw_RAN.marker` and `a38_clean_RAN.marker` (`section5/s5_a38.py:30`). **(pending)**
- **Written once**: the freeze, the record, the fingerprint (`section6/s6_fingerprint.py` `write` refuses if it exists), the evaluation results and the A38 result (`write_once`).
- **Code version** `a0323ed24d68e896` is checked by the freeze and the fingerprint (`section6/s6_fingerprint.py` `CODE_VERSION`).

## 8. Backups

| Item | Location | SHA-256 | Note |
|---|---|---|---|
| Frozen models + manifest + sidecar, freeze document + sidecar (12 files) | `C:\Users\kakij\Downloads\freeze_backup_20261112.zip` | `478c90491911b539142797dbe9b3c87fba07c7d77acd193523a0f4b2ec0e00b4` | Same disk as the originals; git-ignored |
| Code, results, amendments, ledger | GitHub `akoK3/spy-regime-research` | per commit | Data and frozen models not included |
| LEGACY source zip `hfdatalibrary_clean_1min_5tickers_2026-10-03.zip` | `C:\Users\kakij\Downloads` only | `b6754832...` | **No backup**; only partial extracted CSVs (SPY, TLT, HYG) in `OneDrive\Desktop\data\raw` |

Ledger of every step: `METHODS_LEDGER.md` (with `METHODS_LEDGER.sha256`).
