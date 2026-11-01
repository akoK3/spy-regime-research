# Amendment A6 (DRAFT, NOT APPLIED)

**Status: DRAFT. Not applied. No run is governed by this document until it is dated, hashed and approved.**

Drafted 2026-11-01T02:31:58.269481+00:00 UTC against `SECTION5_PROTOCOL.md` sha256 `8abd20f3557dac0991e30ea8c2807aee35be9d7de1c79b199d7f371397c97479`. Evidence: `PILOT_REPORT.md`, `PILOT_REPORT_2.md`, `section5/results/fixes_results.json`.

## Proposed changes

1. 5.2 count: the sensitivity pool is 80 columns, not 83 (83 kept in matrix v2 minus jump_variation_15/30/60__sadj dropped by 5.2).
2. 5.6 threshold grid: add 0.995, 0.999, 0.9995, 0.9999 above 0.99 for all families. Evidence: with the grid capped at 0.99 no threshold meets the false-alarm target for any 3-feature model; with the extension all four families are feasible at f3 (0.999-0.9999).
3. 5.2 / 5.3 return input: replace the 5-min return by the 5-min return divided by the causal slot scale (median |return| of the same grid slot over the previous 20 sessions, >= 10 finite). Evidence: makes return-only baselines feasible at lower thresholds (Gaussian HMM 0.99 to 0.90, HSMM none to 0.95, BOCPD 0.70 to 0.85); gain for feature models is nil without item 2. Applies to baselines and feature models alike.
4. 5.6 miss rule: delays are censored at 60 min for misses; report hit rate and the delay among hits next to the censored median. Evidence: censored median is 60 min in every pilot cell because hit rates are below 50%, so the median-delay comparison in H1(a) is uninformative at the current hit rates.
5. 5.5 BOCPD persistence: T_c additionally requires P(run length <= hold + 2) >= threshold at the third update after T_d. Evidence: small gain (return-only threshold 0.70 to 0.55; f3 hit rate up to 0.11).
6. 5.6 reporting: report the chance rate (confirmed event in [tau, tau+60 min] of null splices at the same threshold) beside every hit rate.
7. 5.5 definitions to state explicitly (currently chosen in the pipeline, see PILOT_REPORT.md): T_c is the third real update after T_d; BOCPD alarm = rising edge; refractory starts at T_c.

## Open points this draft does not settle (decision needed)

- Hit rates at the 1-per-20 false-alarm target are 0.00-0.11 in every tested configuration (the highest is in the fixes table of PILOT_REPORT_2.md). H1(a) as specified has little power at 200 breaks per fold. Untested options: shorter hold, looser false-alarm target, longer hit window, split by direction.
- f6 (6 features) is infeasible for three of four families in every configuration; the 5.8 greedy search to 6 features will often hit infeasible setups unless the false-alarm target or grid is revised.
- BOCPD regime-conditional QLIKE forecast (two regimes from P(changepoint within 3)) is a pipeline choice; the protocol should define it.

## Not applied

Nothing above has been applied to code defaults or to the protocol. The extended grid and the persistence rule exist as off-by-default options (`thr_grid(extended=True)`, `persistence=True`).
