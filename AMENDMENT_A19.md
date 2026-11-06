# Amendment A19 (pre-registered: D8 non-volatility change census, D7 non-volatility response test, Step 2 matched detectors, daily-VIX extension, 5.10 robustness and 5.11 power as run)

Dated 2026-11-06T18:52:00+00:00 UTC (2026-11-06T13:52:00-05:00 New York). Status: ADOPTED when committed with its hash sidecar; pre-registered: written before any D7, D8, Step 2, VIX, 5.10 or 5.11 result exists and before the code it governs. Decided by the user after A17 and A18. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `0b0669b5f341b3d6a660473e83850e8947b5e36da19f8323400ad36137e97fe9` |
| `AMENDMENT_A17.md` | `3778a860320e11db1de520162adf36899cd3dd1b249bb8f9050b8f5f3566f874` |
| `AMENDMENT_A18.md` | `f9b8f371090c2db2e6467c250622b527c9bbf255b09e37d6478379d07a9673b0` |
| `section5/results/main_run/run_complete.json` | `e6f56ae2e19bbc0f56c1437adc04edfa425e2b86c9334065b8d0d3c034630dc1` |
| `section5/results/contamination_list.json` | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/results/a17/a17_results.json` | `aedc00b1b17f7320b6f3bc530eb26464f5cc30e11677ead3b184e19c57d8d5b4` |
| `section5/results/a18/a18_results.json` | `a791c379fbbbfa220342e0b479ad7adaf11afc4002baa2b290fb56c61b6a23cf` |
| `section5/s5_d2_stable.py` | `600a3a5ea0815a91cd7b9681d2412f69fa60ef7079038f47e41059e5eb0b53db` |
| `section5/s5_stats.py` | `aa40e5e6d34a1a648e73ff5f70a2255df8e2b9bf32ca3e9e7f0e9d11c65950f7` |
| `OPEN_AUDIT_FINDINGS.md` | `baebff93a472c6c335cbe22147236890056a53224420cf3670a9ec2dbef83e9f` |

Notation: r = SPY 1-min log return (the panel's `r`, NaN where not `valid`); dv = deseasonalised 1-min variance (`s5_d2_stable.des_variance`: r^2 / median r^2 of the same slot over the previous 20 sessions, >= 10 finite); dvol = deseasonalised 1-min volume (volume / median volume of the same slot over the previous 20 sessions, >= 10 finite, the same `adjust` function); jump = the Section 4 Lee-Mykland flag `lee_mykland_jump60` (frozen threshold, label-free). W = a 60-min window of bars [s, s+60), P = the prior 60 bars [s-60, s).

## Rule 1: D8 (descriptive census; no detector, no model, no outcome)

1a. Sessions: the post-embargo VALIDATION sessions of all 34 folds (30 LEGACY, 4 RAW), each session counted once per era (folds overlap); only sessions with 390 bars and >= 98% finite closes.
1b. Windows: s in {60, 65, ..., 330} (minutes after 09:30; 55 windows per session, overlapping at the 5-min grid). A window is used when W and P each have >= 50 finite r.
1c. Statistics per window: variance ratio VR = mean dv(W) / mean dv(P); drift t = sqrt(60) * mean(r) / sd(r) (60-min signed return in units of its own noise), reported for W and as dt = t(W) - t(P); lag-1 autocorrelation change drho = rho1(W) - rho1(P) (pairs with both returns finite); volume ratio VOL = mean dvol(W) / mean dvol(P); jump count J(W) = number of flagged bars in W, and dJ = J(W) - J(P).
1d. Reports, per era and pooled: 50th/90th/99th percentiles of VR and VOL (and of 1/VR, 1/VOL), of |t(W)|, |dt|, |drho|, J(W) and dJ; signed medians; window and session counts.
1e. "Large" non-volatility change (fixed now): trend |dt| >= 3.64 (= 2.576 * sqrt 2, the two-sided 1% point of the difference of two i.i.d. t statistics); momentum |drho| >= 0.47 (= 2.576 * sqrt(2/60), the i.i.d. 1% point); liquidity VOL >= 2 or VOL <= 0.5; jumps dJ >= 1. Variance-stable: VR in [0.8, 1.25]. Reported per type and era: P(large), P(large and variance-stable), P(large | variance-stable), P(variance-stable | large).
1f. "Occurs" (the D8 gate for Step 2): P(large | variance-stable) >= 0.02 in BOTH eras. The i.i.d. reference for trend and momentum is about 0.01; liquidity and jumps have none.
1g. Contamination: D8 runs no detector or regime model and uses no detector outcome; it reads validation sessions the main run already used for selection. Registry category DESCRIPTIVE (as D6); the canonical list is not regenerated.

## Rule 2: D7 (do the main-run detectors respond to non-volatility changes?)

2a. Models: the A17 saved fits (main-run fold setups, feature and baseline models, all four families), confirmatory 26 folds; no refit. Thresholds: the A17 fold-level A7 thresholds (0.2 confirmed alarms per validation session).
2b. Days: the fold's stable TEST days (5.6 rule). Per day one tau drawn uniformly from the 5.6 permanent-break grid (slots 94-299), seed 1907 per fold; the same day and tau serve the null and every type.
2c. Injection after tau (prices rebuilt from modified returns, open = previous close, high/low = max/min(open, close) plus the original wicks scaled by the same factor as the returns; features recomputed as in 5.6; session history unchanged), each level variance-neutral over the 60 min after tau (rescaled so mean dv over [tau, tau+60) equals the unmodified value):
- liquidity: volume after tau times 2 and times 0.5 (prices unchanged);
- trend: a constant drift added to r over [tau, tau+60) with t = 2 and t = 4 (sign = sign of the day's id parity, fixed by the seed), then rescaled;
- momentum: AR(1) filter on r over [tau, tau+60) with rho = 0.2 and 0.4, then rescaled;
- jumps: 1 and 3 jumps of 6 local sd (bipower scale of the 60 bars before tau) at random minutes in (tau, tau+60), remaining returns rescaled.
Primary level per type: volume x2, t = 4, rho = 0.4, 3 jumps. The other level is reported.
2d. Hit = a confirmed alarm within 60 min after tau whose T_d is available strictly after tau (5.6 rule). Null hit rate = the same on the unmodified day with the same tau.
2e. Decision rule: a detector "responds" to a type when hit rate minus null hit rate >= 0.10 AND its day-clustered 95% CI excludes 0 (percentile bootstrap over (era, day) clusters pooled across folds, 10,000 resamples, seed 1907). Evaluated per family, feature model and baseline separately; feature minus baseline reported with the same CI.
2f. A type is "missed" when no H1 family's FEATURE model (Gaussian HMM, Student-t HMM, HSMM) responds at the primary level.
2g. Gates (all must pass, else D7 is reported as failed for that type and that type cannot trigger Step 2): (i) variance neutrality: for >= 95% of injected days the realised VR over [tau, tau+60) vs the unmodified day is in [0.95, 1.05]; (ii) positive control: a 5.6 variance splice of ratio 3 (permanent) at the same days and taus makes every H1 family's feature model respond; (iii) null sanity: null hit rate <= 0.30 per family; (iv) >= 100 stable test days pooled.
2h. Contamination: POST_MAIN_RUN (A17 rule 6); test segments already scored by the main run.

## Rule 3: Step 2 (matched detectors; only where needed)

3a. Triggered only for types that D7 misses (2f, gates passed) AND D8 shows occur (1f). No trigger, no Step 2.
3b. Per triggered type, the 5.8 machinery is rerun (same families, primary 19 pool, greedy, 1% rule, at most 6 features, K/lambda tuning, return-only baseline tuned identically) with the validation objective matched to the type, a regime-conditional forecast of the next 60 min from each decision bar at or before 15:00:
- liquidity: next-60-min mean dvol, loss QLIKE;
- trend: next-60-min signed return, loss squared error;
- momentum: next-60-min lag-1 autocorrelation of r, loss squared error;
- jumps: next-60-min jump count, loss Poisson deviance.
3c. Evaluation: test-segment loss versus the baseline per fold (block bootstrap as 5.9) and the D7 rule (2e) on that type's splices. Secondary: BH across triggered types x families; not part of H1; does not change 5.12.

## Rule 4: daily-VIX extension

4a. Feature vix_prev = log of the previous trading day's CBOE VIX close, constant within a session, available at the open (never the same-day close). Source file and its sha256 recorded in a ledger row before any fit uses it; a session without a previous-day value is a skipped update for the whole session.
4b. Use: secondary sensitivity. 5.8 selection rerun with the pool = primary 19 + vix_prev; H1(a)/(b), IU and Holm reported beside the main run, confirmatory and all folds; the share of folds selecting vix_prev. Does not change the 5.8 setups, H1 verdicts or 5.12. Contamination POST_MAIN_RUN.

## Rule 5: 5.10 robustness (as planned; definitions fixed now)

On the main-run fold setups (A17 fits), confirmatory folds, reported beside the main H1: by era; Student-t HMM excluding flagged fits (A14.2); LEGACY decision delay +5 and +10 min (alarm times shifted, hit windows unchanged); 3 seeds (seeds 1, 2, 3 for starts and splices; refits); 1-min and 15-min grids (final setups only, 5.3); RAW sensitivity pool (80, RAW folds only; resolves open finding 21 by restriction to RAW); threshold +/-0.05 defined as the A7 calibration target 0.2 +/- 0.05 confirmed alarms per session (0.15 and 0.25; resolves open finding 13). H1(a) is unaffected by the target (sweep); the target changes H1(c) and the realised test alarm rate, both reported. No verdict changes.

## Rule 6: 5.11 power (as planned)

Per H1 family and component, `s5_stats.mde` with sd = the confirmatory fold-effect sd of the main run, n_folds = 26, alpha = 0.05 / 3 (Holm's first step) and 0.05, power 0.8, nsim 400, nboot 500, seed 0; reported with the observed mean effect. Also for D7: the smallest hit-rate difference detectable at 80% power by the 2e rule given the pooled day count and the null hit rate (binomial simulation, 2,000 draws, seed 1907).

## Order and status

D8 runs first (this commit's successor). D7, Step 2, VIX, 5.10 and 5.11 need their code and a ledger row before they run. All are secondary or descriptive; none changes H1, the 5.8 setups or 5.12. Not integrated into `SECTION5_PROTOCOL.md` (A16 rule 6, as A17/A18); the freeze call must list A17, A18 and A19.

## Governs

`s5_d8.py` (and later `s5_d7.py`, Step 2, VIX, robustness and power scripts), registry entries, unit tests; results under `section5/results/d8/` and later folders.
