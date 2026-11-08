# Note to `grids.json` (O9 finding M3; added 2026-11-08 at the user's request; `grids.json` itself is unchanged)

The grid sensitivity of A22 rule 3g changes the decision resolution but keeps two things fixed, as the rule states:

1. **Event rule counted in updates.** A run is 3 consecutive real updates, the first 2 silent (`s5_sweep` run = 3, warm = 2); the refractory period is 30 min. The time from first detection to confirmation is therefore 2 min on the 1-min grid, 10 min on the 5-min grid and 30 min on the 15-min grid.
2. **Splice taus on the 5-min stamps.** `s5_eval.TAU_SLOTS` = 94 + 5k. On the 15-min grid the first bar after tau mixes pre- and post-change minutes, and the 60-min hit window holds only 4 decision bars.

The H1(a) x-axis is the null alarm rate per session (pAUC over 0 to 0.5 alarms per session). On the 1-min grid there are 5 times as many updates per session, so the same alarm rate is reached only at much stricter thresholds. Grid results therefore describe the 5-min-tuned final setups under this rule at each resolution. They do not measure the information content of the inputs at that resolution.

In particular, the 1-min Gaussian HMM H1(a) of -0.055 (15 of 22 folds negative, p_IU 1.0) contradicts MR2 for these setups and this rule at 1 min. It is not a finding that the volatility feature carries no information at 1 min. The absolute feature and baseline areas on the 1-min and 5-min grids are in the post-hoc descriptive `section5/results/posthoc_grid_pauc/` (close-out item 2).

No implementation error was found in the grid path: grid patching, the deseasonalising matrix of grid width, HSMM Dmax = 390 / G, Diebold-Mariano lag 60 / G, and splices built through `session_grid`.
