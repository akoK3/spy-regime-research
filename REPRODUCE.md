# Reproduce

How to check and rerun the results. Every value here is taken from `REPRODUCIBILITY_FACTS.md`, which takes precedence if they differ, and from the files it cites.

## 1. Environment

| Item | Value |
|---|---|
| Python | 3.12.10 (64-bit) |
| numpy / pandas / scipy | 2.5.4 / 3.1.0 / 1.18.1 |
| scikit-learn | 1.9.1 |
| hmmlearn | 0.3.3. Installed but not used: the models are in `section5/s5_models.py`. |
| OS / hardware used | Windows 11 Home 10.0.26200; AMD Ryzen 7 7435HS, 15.7 GB RAM; single process |

```
py -3.12 -m venv research_hmm_env
research_hmm_env\Scripts\pip install numpy==2.5.4 pandas==3.1.0 scipy==1.18.1 scikit-learn==1.9.1
```

## 2. Data (not in git)

The canonical panels and source files are git-ignored. Obtain them, put them at the paths below (relative to the repository root), and check every SHA-256 against `REPRODUCIBILITY_FACTS.md` §3:

- `section3_10_alignment_results/canonical_panel_{LEGACY,RAW}_1m.csv.gz`
- `section3_4_etf_results/etf_observed_SPY_{LEGACY,RAW}.csv.gz`
- the HF data library zips, the TLT and HYG raw CSVs, and the Dukascopy gold and dollar-index bid and ask files

`section5/s5_preflight_data_hashes.py` checks the data hashes. Every guarded read reruns it.

The frozen models (`section5/results/frozen_models/`) are git-ignored too. A backup with its SHA-256 is listed in `REPRODUCIBILITY_FACTS.md` §8.

## 3. Verify without rerunning

```
sha256sum section5/results/section5_freeze.json        # 846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94
sha256sum section5/results/frozen_models/manifest.json # edb78798544a8896c88f5a6b02857591d96f6764ed0d7f498685cbdbc0ac06dd
cd section5 && python -c "import s5_guard as G; print(G.code_version())"   # a0323ed24d68e896
python s5_tests_ledger.py                                                    # METHODS_LEDGER.md matches its sidecar
```

Every result file has a `.sha256` sidecar next to it, and every amendment has one too (`AMENDMENT_*.sha256`).

## 4. Rerun order (what produced the results)

| # | Command (directory) | Output | Duration on the machine above |
|---|---|---|---|
| 1 | `python s5_freeze_run.py run --confirm section5_freeze.json` (`section5/`) | `section5_freeze.json`, `freeze_run_record.json`, `frozen_models/`, `ERA_CALIBRATION.lock` | 4 h 13 min |
| 2 | `python s6_fingerprint.py write` (`section6/`) | `section6/results/s6_fingerprint.json` | 1 s |
| 3 | `python s6_eval.py run <abs>\section5\results\section5_freeze.json <freeze sha256>` (`section6/`) | `evaluation_{LEGACY,RAW}.json`; `coverage_evaluation.json`, `s6_evaluation_gaussian_hmm.json`, `h2_evaluation_gaussian_hmm.json`, `a34_evaluation_gaussian_hmm.json` | about 7 h active |
| 4 | `python s5_a38.py run <abs>\section5\results\section5_freeze.json <freeze sha256>` (`section5/`) | `a38_filter_check.json` | 19 min |

Steps 2–4 ran as one chain that stops at the first non-zero exit (`section6/results/eval_chain_status.txt`).

## 5. Guards: why a rerun in place is refused

- **Evaluation reads go through `section5/s5_eval_loader.py`.** It checks the freeze, the token (the freeze's SHA-256), the amendment list, the era-calibration lock, the data hashes and the Section 6 fingerprint. Every read is logged in `section5/results/eval_access_log.txt`.
- **One-shot markers** (`evaluation_{LEGACY,RAW}_RAN.marker`, `a38_*_RAN.marker`) are written before the first evaluation read. The freeze, the record, the fingerprint and the results are write-once.

So repeating steps 1–4 in this checkout is refused by design. To reproduce, run them in a **fresh copy** of the repository at the freeze commit (`3b9e68d`, freeze; `34ec7d1`, evaluation results), with the data from §2. Then compare the outputs' SHA-256s with the committed sidecars.

## 6. Independent check

`tools/acceptance_repro.py` was written separately from the research code, in the MarketLens repository, and is copied here unchanged apart from a provenance header; its MarketLens dependencies and hash-locked copies of the frozen model and code are in `tools/regime/`. It reloads the RAW panel and copies of the frozen model and code. Run it from the repository root with `python tools/acceptance_repro.py .` once the RAW panel and SPY file of §2 are in place; it writes `acceptance/acceptance_report.json`. It reproduces every Gaussian HMM run in `section5/results/evaluation_RAW.json` exactly (344 runs, 445 sessions). That read happened outside the guard and is disclosed in the ledger row of 2026-11-14.
