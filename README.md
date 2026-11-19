# spy-regime-research

Code, pre-registered protocol, amendments, frozen-model records and results for the preprint
**"Is SPY an Intraday Tripwire? Detecting Volatility Regime Shifts and Testing Their Cross-Market Reach"**
(Akaki Jvarsheishvili, Caldwell University, 2026).

## Purpose

The study asks two questions about intraday SPY volatility regimes:

1. Do feature-based regime detectors (Gaussian HMM, Student-t HMM, HSMM; BOCPD as secondary), updated every five
   minutes, detect SPY volatility-regime switches and forecast next-hour volatility better than the same models
   fed returns only (H1)?
2. Do SPY regime switches carry information about Treasuries (TLT), high-yield credit (HYG), gold and the US dollar
   (H2 returns, H3 next-day volatility, H4 confirmation)?

The work is pre-registered and amendment-driven: every protocol change is a dated, SHA-256-hashed amendment; every
step is a row in `METHODS_LEDGER.md` (sidecar `METHODS_LEDGER.sha256`; rows only via `section5/s5_ledger.py add`);
detectors were selected and frozen on training data before the evaluation periods were read through a guarded,
logged, one-shot loader.

## Results in one paragraph

In walk-forward development (2003–2024, 26 uncontaminated folds), adding a time-of-day-adjusted 10-minute realized
volatility feature improved both planted-break detection and next-hour volatility forecasts over returns-only
baselines for the Gaussian HMM (Holm p 0.0014) and the HSMM (Holm p 0.0003), but not significantly for the Student-t
HMM (p 0.103). In a retrospective replication with the frozen models on 2019–March 2022 and 2025–October 2026, all
three hidden-state detectors improved on both criteria, with every 95% interval excluding zero, including on
unfiltered IEX data. The gains depend on requiring a new state to persist, and absolute sensitivity is limited to
large variance increases (the Gaussian HMM caught 24% of planted tripled-variance changes within an hour, 4% of
1.5-fold rises). **A post hoc benchmark on the development folds changes how these gains should be read: a simple
volatility-change rule detected planted shifts better than every regime detector (mean metric 0.333 vs 0.182–0.235),
and a HAR regression forecast next-hour volatility better in 25 of 26 folds; the detectors did better only on Federal
Reserve statements, and only against the first rule.** The cross-asset hypotheses found no support: no primary H2–H4
test rejected after Holm adjustment, in development or evaluation, and next-day TLT and gold volatility was lower,
not higher, after SPY switches. The results are consistent with SPY reacting alongside other markets rather than
leading them. Evaluation results are labelled exploratory (`confirmatory: false`, A26) because those periods were
seen in earlier exploratory work.

## Reproduce the paper's tables and figures

Requirements: Python 3.12.10 (64-bit; `.python-version`), about 1 GB of disk, no data for tables and figures 1–5.

```
git clone https://github.com/akoK3/spy-regime-research.git
cd spy-regime-research
py -3.12 -m venv .venv                       # Linux/macOS: python3.12 -m venv .venv
.venv\Scripts\pip install -r requirements-paper.lock   # Linux/macOS: .venv/bin/pip ...
.venv\Scripts\python reproduce_paper.py      # add --build-cache once the data of DATA.md §1 is in place (Figure 6)
```

`reproduce_paper.py` regenerates Tables 3, 4, 5, A3, A4 and A5 (`paper/tables/TABLES.md`, with every value's source
file and key in `tables.json`) and the six figures (`paper/figures/`), then runs `paper/check_paper_values.py`, which
compares 237 values with the manuscript (`paper/expected_values.json`: the 223 table values plus the 14 benchmark
numbers quoted in §6.2, which are also checked against `section5/results/posthoc_benchmark/BENCHMARK_FACTS.md`) and each regenerated figure with its
committed inputs and PNG. Tables A1 and A2 are text tables with no computed values.

| What | Needs data? | Runtime on the reference laptop |
|---|---|---|
| Environment install from `requirements-paper.lock` | no | about 1.5 min |
| Tables + figures 1–5 + checks | no | about 6 s |
| Feature cache for Figure 6 (`--build-cache`, once) | yes (DATA.md §1) | 14 min alone, up to 27 min with other jobs running (LEGACY 11.5–24 min, RAW 2.7 min; about 1.4 GB RAM) |
| Full rerun of the freeze, evaluation and A38 (`REPRODUCE.md` §4) | yes, in a fresh copy at the freeze commit | about 15.5 h (freeze 4 h 13 min; evaluation about 7 h active; A38 19 min) plus earlier development runs |

Reference machine: AMD Ryzen 7 7435HS, 15.7 GB RAM, Windows 11, single process.

Figure numbering: the files are named in the order they were made, not the paper's order.

| Paper | File |
|---|---|
| Figure 1 (time-of-day pattern) | `fig6_seasonality` |
| Figure 2 (H1(a) gain) | `fig1_h1a_pauc_gain` |
| Figure 3 (FOMC hit rates) | `fig2_fomc_hit_rates` |
| Figure 4 (detection by break size) | `fig3_detection_by_break_size` |
| Figure 5 (H3 γ) | `fig4_h3_gamma` |
| Figure 6 (lead-lag timing) | `fig5_a30_timing` |

**Verify without rerunning:** `REPRODUCE.md` §3. **Rerun the analysis:** `REPRODUCE.md` §4–5 (the guards refuse a rerun
in place by design; use a fresh copy at the freeze commit `3b9e68d`). **Tests:** each `section5/s5_tests*.py` and
`section6/s6_tests*.py` runs standalone (`unittest`, no pytest), from its own directory; several write their report
into `section5/results/`, so run them in a fresh copy. In a fresh copy, 309 of the 320 tests pass. The other 11
(in `s5_tests_a14`, `_a15`, `_a16` and `s5_tests_run`) are refused by design, because they start model selection or
scoring and the post-freeze lock `section5/results/ERA_CALIBRATION.lock` (A16 rule 5) forbids that; with the lock
moved aside in a throwaway copy they pass.

## Data

No market data is in this repository. `DATA.md` lists every dataset the code reads, its source, whether it can be
redistributed, and fetch notes; `DATA_SHA256SUMS` holds the expected SHA-256 of every file
(`sha256sum -c DATA_SHA256SUMS`).

| Dataset | Source | Redistributed? |
|---|---|---|
| SPY, TLT, HYG 1-min bars (LEGACY Clean 2003–2022, PiTrading rows; RAW IEX 2022–2026) | HF Data Library (Elkassabgi, 2026), [doi:10.5281/zenodo.19501604](https://doi.org/10.5281/zenodo.19501604) | No (IEX Historical Data Terms; PiTrading history withdrawn by the provider) |
| Gold (XAU/USD) and Dollar Index 1-min bid/ask | Dukascopy | No |
| FOMC statement times | Federal Reserve Board; Lucca and Moench (2015) | Yes, derived schedules committed |
| Bloomberg 1-min bars (post-evaluation timing check only) | Bloomberg | No; summary statistics only |

**Limit: the pre-2022 data cannot be re-obtained.** The LEGACY era (2003-01-02 to 2022-03-04, all development folds
except RAW and the 2019–2022 evaluation period) rests on the PiTrading rows of the HF Data Library Clean file
downloaded on 2026-10-03. The provider has withdrawn that history and no longer distributes it, so nobody can download
it again; it can only be verified against its SHA-256 (`b6754832…`, `DATA_SHA256SUMS`) using the copy the author
retains. The RAW-era files can still be downloaded, but the library is updated regularly, so current downloads may
differ from the hashed files.

## Pre-registration, amendments and code version

| Record | SHA-256 |
|---|---|
| Result-module code version (`section5/s5_guard.py` `code_version`, 16 hex) | `a0323ed24d68e896` |
| Section 4.3.0 frozen protocol v2 (`frozen_documents/protocol_20261029T032641Z.json`) | `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b` |
| Section 5 detection protocol (`SECTION5_PROTOCOL.md`; superseded versions `SECTION5_PROTOCOL_v*_FROZEN_*.md`) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| Freeze document / evaluation token (`section5/results/section5_freeze.json`) | `846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94` |
| Frozen-model manifest (8 models; `section5/results/frozen_models/manifest.json`) | `edb78798544a8896c88f5a6b02857591d96f6764ed0d7f498685cbdbc0ac06dd` |
| Methods ledger at this commit (`METHODS_LEDGER.md`) | `779db1f53bab182306ddd63c6d654378e3d567be29d024b9099b6f42170004b7` |
| Forward-test pre-registration v2.1 (MarketLens `regime/FORWARD_TEST_PREREGISTRATION_v2_1.md`; supersedes v2 `05e5ee40…`, v1 `7f0da937…`) | `f1e2a1332fa1b212db2d8947fce8dfbcc7f9fac4bb9bd3b3bcfd989c0015ed1a` |

Amendments: 43 adopted amendments, A6 to A38, adopted between 2026-11-01 17:48Z and 2026-11-11 04:33Z (the paper's
"43 amendments between 1 and 11 November"), plus the A6 draft of 2026-11-01 02:31Z, which was never applied and is
kept on record (ledger row of that time; superseded by A6). Each file has a `.sha256` sidecar; all 44 matched on
2026-11-19. The 19 in force at the freeze are listed with their hashes in `section5_freeze.json`, key `amendments`.

| Amendment | SHA-256 | Amendment | SHA-256 |
|---|---|---|---|
| A6 | `db787ec0071b5b6c0ff4048cd281bf54e95e0c60b5f25e89fb6f02d55d5744a5` | A19.3 | `7269d2cb5034cec52e9f42a006e26f93e7662825c3a89f065df4553735a8f7e2` |
| A7 | `e64c8647fd3fac01ff2a64de71f25c53e6b9c8814271df9e66b3ab01835d8267` | A20 | `828e14b7d8b3445eb499fdcd7a32e1e0a5bd41dfc80b5d3224186c6a85481160` |
| A8 | `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931` | A21 | `b4ed40509480b6a69e621c3be309ab28d397e8e2b53b25bd459d4da305b5eda0` |
| A8.1 | `bd7a854ed681c16b5bddadda1791fb66087aeecc63e4341e05c95da8de48fbd8` | A22 | `3ce7b683a1369659b14b22c068bcc25c6a7b14a7a6b15758946c7050f8a15217` |
| A8.2 | `c85e40ba4484d648e44a2eda9f4900f29ffbf0bff0751b38c2f878455e96c157` | A23 | `c81f5c0523e7dc578f66e19f24ea199fe0331429ba050ee66d33063ee871a411` |
| A8.3 | `8867dc3e526285ce24768480bbfe200d1e37f68a2e86bbeea425dc31740d52a1` | A24 | `45ff565e8ca78abf8756379250dbc66586eb101a0aca342055207347db951651` |
| A8.4 | `f57a8734aaf28fd1bac378edc7ec0f13a8f48dc7ea375e491b42612bb56d89e5` | A25 | `c71d9ea0369739ee72b93e58199a1ef1fc5501fc352287bef624472bd82c1247` |
| A9 | `d915f7c90a38a0236a3962857235d7e1096b16f54065bb8104d3795ee4947bb0` | A26 | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| A10 | `73d0a99fdb9d5e5a753bba8f1a85c3f2ecc5629a5b03ae8f3d6bcfe8f52c4763` | A27 | `8325cfdbe71a9033b4bc53e1f1c6d93fd1d7d917ba14745ff6ab29564be6cd19` |
| A11 | `297551fb2e58b1f84939e66a6b67104e4c71db6ad30bb2534a7fd5ac6235f97c` | A28 | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| A12 | `dd90c6b22b85851c61e1a88be82d294ecd95d9f8893c2f246fd78278927ff96a` | A29 | `304f27252b29d27649eeb68a0507f127fe24a602cd9556f5d43687bf24822715` |
| A13 | `301be6ed93fdf80d9a3841664faf8398d2a8b5d30073ad00ba9f88d20e7c5755` | A30 | `1c421aa7ced0c8748648e9fe5fc723fa14c606a67943001fc482372d3990b9da` |
| A14 | `1707ec30b9ad3f1a9b76d70e63807b92dd37179e47288191982677bed83709de` | A31 | `1efd5a1f338b31c6f7459c8d328c854450eed6800052d2be261f83d240ef036f` |
| A14.1 | `d7cdaef27c572a4890aaf7306b2dc5f5f4a674bb58b8120e200062d81bd95ada` | A32 | `d222539ced84ceb2d4336d3c3c35f73bf57300fc82794f3694f8b7447c424c1b` |
| A14.2 | `d4f27c5d2b439a18629730c1cdce0bb4a867a04cef7a27f37bd8a903b9e248fd` | A33 | `f101adce416ed256499fe779f5c0152de4c26d6bfbd9324a7a2546ecf9506747` |
| A15 | `15de695a9f16445a17271773e37e9089ff852f5304fd2ca90549b3e9267ddc2d` | A33.1 | `c87e7aea319e3b121996d9893397a03f483038afee73223a17e4b1f75cdb355b` |
| A16 | `35b2b802a59d855229816be3d8919aef5b871c4304376d1b891d2318ffac7bf0` | A34 | `a2c58b4560eba9320fd78564a5d7f39031c09f4825cca822d75c0d2ec9484faa` |
| A17 | `3778a860320e11db1de520162adf36899cd3dd1b249bb8f9050b8f5f3566f874` | A35 | `dc5289d6a46178427f3acf04d0327628628bde3d3bbe099cf3298fe33dcabc7f` |
| A18 | `f9b8f371090c2db2e6467c250622b527c9bbf255b09e37d6478379d07a9673b0` | A36 | `f110e14f3633d764d8048bb67b192c6fff9b68d2540c85d0297d53448ff227db` |
| A19 | `ecfd437ee575bfc3d6c256e4db48c024b8006aedf9163dd57595cbbcd21569ec` | A37 | `cd3cfdea7d75c3a0b9f5f819395cc6b4da37631b89572e0a9c7525a6e5af5b2e` |
| A19.1 | `bffed0e9f8acf7aea9d98ae83950624d7cb3f4b95e37c15997fccda584eed0a0` | A38 | `067c1de7bc508ff5f079387977c037e83bcb000bf1f3c5990853f96d725ae532` |
| A19.2 | `619d32de48aeaa8a1fd9054fcb676982a84c7028fc27d1c673a38af001480b27` | A6 draft (not applied) | `379f0c01bd9c19d0432e59d597a16840d6fe4be83e5a4c62c44554f58a298c00` |

Key commits: freeze `3b9e68d`; evaluation results `34ec7d1`; later commits add only corrections and post-evaluation notes.

## Repository structure

| Path | Contents |
|---|---|
| `step*.py`, `write_*.py`, `section431_step3_all_in_one_results/`, `frozen_documents/`, `SECTION4_COMPLETE.md`, `FEATURES_REFERENCE.md` | Section 4: causal feature construction, audits, the frozen feature matrix and nested folds |
| `SECTION5_PROTOCOL.md`, `AMENDMENT_A6.md`…`AMENDMENT_A38.md` | Section 5 protocol and every amendment, each with a `.sha256` sidecar |
| `panel_build/` | Sections 2–3: data audit and canonical-panel build from the vendor files (own environment, `requirements-panel.lock`; not in the code version) |
| `section5/` | Detection code (models `s5_models.py`, events `s5_events.py`, guards `s5_guard.py`, freeze `s5_freeze*.py`, evaluation `s5_eval513.py`) and results `section5/results/` |
| `section6/` | Cross-asset tests H2–H4 (`s6_*.py`) and results |
| `paper/` | `RESULTS_FACTS.md` (every result number with its source), `make_tables.py`, `make_figures.py`, `check_paper_values.py`, figures and tables |
| `*_REPORT.md`, `cold_audit_*.md`, `FABLE_*AUDIT.md`, `POST_EVAL_AUDIT.md`, `*_DISCLOSED_LIMITATIONS.md` | Pilots, diagnostics, independent audits, disclosed limitations |
| `REPRODUCIBILITY_FACTS.md`, `REPRODUCE.md`, `DATA.md` | Environment, hashes, run order, data |

## Known gaps

- The Section 2–3 scripts that build the canonical panels are in `panel_build/`, unchanged and with a dated SHA-256
  manifest. They are NOT part of code version `a0323ed24d68e896` and were not tracked before 2026-11-19; they ran
  under Python 3.14.3, numpy 2.3.5 and pandas 2.3.3 (`requirements-panel.lock`), and they assume the author's folder
  layout. Their outputs are accepted only if they match `DATA_SHA256SUMS` (`panel_build/PANEL_BUILD.md`).
- The LEGACY source (PiTrading rows of the HF Data Library Clean file of 2026-10-03) is no longer distributed (see Data).
- The frozen models are `section5/results/frozen_models/*.pkl` (Python pickles). Load them only after checking their
  SHA-256 against `manifest.json`; unpickling runs code.
- Some committed records contain absolute paths from the author's machine (Windows user folder); they are left
  unchanged because those records are hashed.

## Licence

Code: MIT (`LICENSE`). Documents, result files, frozen models and figures: CC BY 4.0; the full licence text is in
`LICENSE-docs.md`. No data is licensed here; the providers' terms apply (`DATA.md`).

## Citation

See `CITATION.cff`. Until the preprint has a DOI:

> Jvarsheishvili, A. (2026). *Is SPY an Intraday Tripwire? Detecting Volatility Regime Shifts and Testing Their
> Cross-Market Reach.* Preprint. Code and records: https://github.com/akoK3/spy-regime-research (code version
> `a0323ed24d68e896`).

## Use of AI tools

Generative AI tools (Anthropic's Claude) drafted and edited much of the prose, which the author revised, and assisted
with drafting and reviewing analysis code and with finding and checking citations. The author designed the study,
established the evaluation protocol, made all final methodological decisions, reviewed all generated material, and
takes responsibility for the work.
