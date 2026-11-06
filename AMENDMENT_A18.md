# Amendment A18 (pre-registered sensitivity: selection by one-step-ahead predictive log-likelihood of the next 5-min SPY return)

Dated 2026-11-06T03:40:38.888371+00:00 UTC (2026-11-05T22:40:38.888371-05:00 New York). Status: ADOPTED when committed with its hash sidecar; pre-registered: decided before any of its results exist, written before the code it governs. Decided by the user after the main run. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9` |
| `AMENDMENT_A16.md` | `35b2b802a59d855229816be3d8919aef5b871c4304376d1b891d2318ffac7bf0` |
| `section5/results/main_run/run_complete.json` | `e6f56ae2e19bbc0f56c1437adc04edfa425e2b86c9334065b8d0d3c034630dc1` |
| `section5/results/main_run/run_summary.json` | `eeb68a4c9e78a62ebe8a76f7b7a5799635b5401a190adfbd2ec1305343af7e44` |
| `section5/results/contamination_list.json` | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/results/posthoc_main_run.json` | `577eb11bc1fca45ff6b18ad6016ae82fb3f50a040ba54bc58b446622efc3afe5` |
| `section5/s5_backend.py` | `4a077d86a7d2881b821c32a655724db6bd27dbbbb28e60149b0b9f1e88da0773` |
| `section5/s5_run.py` | `a8487083212de0ad5ddffccaca67c75cb392e66624347e0aa5aebd8a69184536` |
| `section5/s5_h1c.py` | `275fcbc950947755f09c05d5f35596a1acae1d2432bc18c1b125f0bf727a2b9c` |

## Rule

1. Per fold, 5.8 selection is rerun with one change: the validation objective is the mean negative one-step-ahead predictive log-likelihood (nats per scored bar) of the next decision bar's deseasonalised 5-min SPY return, in the inner-train-fitted preprocessing scale (the return column after winsorisation and z-scoring; identical for every candidate of a fold). Lower is better. Everything else is identical: greedy forward from the return-only model at K=3 / lambda=39 with 1 start, the 1% relative-gain stop (gain = (current - candidate) / |current|), at most 6 features, K/lambda tuning with 3 starts, the baseline tuned the same way (A15 rule 1), tie rules, scoring (H1(a) pAUC, H1(b) QLIKE), tests, Holm.
2. Predictive density at bar t+1 given updates up to t, within a session, for t+1 >= 2nd update and a finite return at t+1: Gaussian and Student-t HMM: filtered state probabilities at t times the transition matrix, mixed over the states' marginal density of the return column (Normal; Student-t with the state's df and scale); HSMM: the one-step prediction of the expanded (state, duration) forward variable, mixed over the states' Normal return marginal; BOCPD: the run-length posterior after t mixed over each run length's Student-t predictive of the return column. Skipped updates follow 5.3 (transition or hazard only).
3. Reports: per model family the selected features and feature families (D1 style, the name-stem families of `s5_posthoc_main.py`); H1(a)/(b) fold tests, IU and Holm under these setups, confirmatory (26 folds) and all folds; the share of folds selecting at least one non-volatility feature. Volatility families (fixed now): rv, downside, abs_return, intrabar_range. Non-volatility families: momentum, return, relative_volume, close_location.
4. Status: sensitivity analysis. It does not replace the 5.8 setups, the H1 verdicts or the setups to be frozen in 5.12. Runs after A17 in the same unattended wrapper. Contamination category POST_MAIN_RUN (A17 rule 6). Its run directory gets a completion record with backend kind 'a18-<script hash>', which can never verify as a main record.

## Governs

`s5_a18.py`, `s5_a17_a18_common.py`, registry entries, unit tests, the overnight wrapper; results under `section5/results/a18/`. Not integrated into `SECTION5_PROTOCOL.md` now: integrating it would change the protocol hash, and A16 rule 6 binds the main run's checkpoints and completion record to that hash, so the main run would have to be redone before the freeze. The amendment is adopted as this dated, hashed file; integration is deferred until after the 5.12 freeze, and the freeze call must list it in its amendments argument (the freeze's input hashes cover only amendments the protocol integrates).
