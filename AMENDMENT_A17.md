# Amendment A17 (deterministic reproduction of the main-run fits; H1(c); post-hoc R=1-net H1(a); test-segment QLIKE percent)

Dated 2026-11-06T03:40:38.888371+00:00 UTC (2026-11-05T22:40:38.888371-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs and before any of its results. Decided by the user after the main run. Facts only.

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

Main run: completion record sha256 `e6f56ae2e19bbc0f56c1437adc04edfa425e2b86c9334065b8d0d3c034630dc1`, results sha256 `7cd6a5926442b8e6640073ecd6e72c50f6fdc8dadec7ba13b095b1fbf4e2ccdc`, code version `b22b29ffacca13b4`, protocol `0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9`.

## Rules

1. Reproduction. Before anything else the script verifies the main-run completion record (A16 rule 1) and that the current code version equals the record's. Per fold (34, consecutive order) and family (4), it calls the main path's `score_fold` with the stored setup (features, params, base_params; 3 starts, seed 0, the same backend). Every field of the result (H1(a) effect and skip/failure reason, H1(b) effect, n, DM statistic, validation QLIKE, flag) must equal the stored checkpoint value exactly (NaN equal to NaN); on any mismatch the run stops with the details recorded and exit code 4, and nothing further (including A18) runs. The fitted feature and baseline models are saved (pickle, sha256 in a committed manifest; the pickles themselves stay local).
   - WHY: H1(c), the placebo gap and the test QLIKE levels need the fitted models, which the main run did not store; an exact match shows the models are the main run's. EVIDENCE: `posthoc_main_run.json` (not computable from stored outputs); the fits are deterministic (seed 0, same code version).
2. Alarm times. Per fold and family, a threshold for the feature model and one for the baseline model are set by the A7 rule on that fold's real validation sessions (bisection to 0.2 confirmed alarms per session; bounds theta [0, 30], m [1, 80]; flags as A7) - the fold-level reading of 'the frozen alarm frequency' (the era-level thresholds of 5.13 do not exist before the freeze). Confirmed alarms on every test session are saved: minute of T_d and T_c after 09:30 (slot + 1, the availability minute). Detectors: `detect_old_state_logodds` (HMM, HSMM), `detect_bocpd_map` (BOCPD).
3. H1(c) as pre-registered (A8 item 5, A11 item 3, A12 item 2): the 98 eligible events of the canonical contamination list with their release minutes; a hit = a confirmed alarm with availability in [release, release + 60 min]; features versus baseline per family; paired exact sign test (two-sided, `s5_h1c.paired_sign`), Wilson 95% intervals; reference rate = share of the same fold's non-FOMC test sessions with an alarm in the same clock window, averaged over events; outside Holm (secondary). All four families reported.
4. POST HOC, labelled as such: per-fold R=1 placebo gap. Placebo splices are built from the fold's stable test days exactly as the A8.1/A8.2 gate builds them (`build_specs` with ratio 1, direction up, durations permanent/30/60/120, 50 per duration = 200, seed 777); the null alarm rate x comes from the fold's H1(a) null splices; gap = pAUC_placebo(features) - pAUC_placebo(baseline); net H1(a) = H1(a) - gap; folds skipped for H1(a) are skipped. Net H1(a) is tested with the 5.9 machinery (block bootstrap, Wilcoxon, sign) and reported beside H1(a); no decision changes.
5. Test-segment QLIKE percent: per fold, 100 x (mean baseline QLIKE - mean feature QLIKE) / mean baseline QLIKE on the common scored test bars (the bars H1(b) uses); median, quartiles and pooled value per family; confirmatory and all folds.
6. Contamination: these runs fit models on, and score detectors on, the main run's fold segments after the confirmatory H1 had been scored. Registry category POST_MAIN_RUN: does not mark sessions touched for the frozen 5.14 list (it protects the H1 fold scores, which precede these runs); no fold-level confirmatory use of these outputs. No era calibration, no lock, no freeze, no evaluation data.

## Governs

`s5_a17.py`, `s5_a17_a18_common.py`, registry entries, unit tests, the overnight wrapper; results under `section5/results/a17/`. Not integrated into `SECTION5_PROTOCOL.md` now: integrating it would change the protocol hash, and A16 rule 6 binds the main run's checkpoints and completion record to that hash, so the main run would have to be redone before the freeze. The amendment is adopted as this dated, hashed file; integration is deferred until after the 5.12 freeze, and the freeze call must list it in its amendments argument (the freeze's input hashes cover only amendments the protocol integrates).
