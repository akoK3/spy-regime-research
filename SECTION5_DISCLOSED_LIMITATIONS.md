# Section 5: disclosed limitations (from O9 and the close-out)

Dated 2026-11-08 (UTC). This is a disclosure list for the paper. It changes no rule, setup, result or verdict. Source: `O9_AUDIT.md` (sha256 `8b31a38b23e21b6c2ffa0b7eaaa512c75e75d1cb475b493f265d6ff8f4407c8d`) and the close-out diagnostics. Earlier disclosures stay in force: protocol open items, cold audits 1 and 2, the A-amendment disclosures and Section 4 limitations 1-24.

## D1. LEGACY feature models update on fewer bars than their baselines (O9 M2)

On a decision bar where any input feature is undefined, the feature model has no real update; the return-only baseline keeps the bar (`s5_lib.build_sequence`: real = all inputs finite). Share of 5-minute grid bars with an undefined value:

| Feature | LEGACY | RAW |
|---|---|---|
| rv10_partial90__sadj (era final feature in LEGACY, all three H1 families) | 15.1% | 4.3% |
| downside10_strict__sadj | 17.2% | 4.4% |
| rv5_strict__sadj, downside5_strict__sadj | 10.7% | 3.0% |
| abs_return_1m__sadj | 4.9% | 1.6% |
| intrabar_range_log__sadj | 3.3% | 1.6% |

Almost all of the missingness comes from the base feature's own validity window (LEGACY base NaN 3.0-14.9%). A zero causal slot median (D2) accounts for 0.2-0.5% of LEGACY bars and 1.4% of RAW bars. MR2 compares feature and baseline models with these different update sets, as run and in every comparison (H1(a), H1(b) on common bars only, H1(c), D7). The difference is larger in LEGACY than in RAW. Counts: `section5/results/o9/sadj_nan_attribution.txt`.

## D2. Zero slot medians: the 47 LEGACY D7 days with an undefined variance ratio (close-out item 3)

All 47 LEGACY days that D7 skipped under A21 (rule 1, an undefined variance ratio) have the same cause:

- **Weights.** The D7 injections are measured in the detector's units, w = 1 / baseline. The baseline of a bar is the causal median of r² for the same minute slot over the previous 20 sessions, as `step11_a4_rerun_4_3_4_7_8.adjust` builds it; `s5_fast.in_units_of_A` uses the same construction as every __sadj feature.
- **Why it is undefined.** `adjust` leaves the baseline undefined unless it is finite and > 0. A median of r² is exactly 0 whenever more than half of those 20 minutes had a zero 1-minute return.
- **In the D7 windows.** On each of the 47 days, 1 to 5 of the 60 bars after tau (median 1) have such a zero median. Of the previous 20 minutes in that slot, 53-71% were flat. No bar had fewer than 10 finite values and no return was missing. One undefined w makes S0 = sum w r² undefined, so the variance ratio is undefined for every price-path injection (jumps, trend, momentum). Liquidity injections are unaffected because they leave the price path untouched.
- **Why LEGACY.** Tick discreteness: 7-24% of LEGACY 1-minute returns are exactly 0, by year (2004 24%, 2005 24%, 2006 23%, 2018 7%).
- **Where the days fall.** 2004-2007: 30; 2009-2014: 17. By fold: LEGACY 2 has 8; LEGACY 0, 5 and 16 have 5 each; the rest have 1-4.
- **Not this cause.** A 48th LEGACY day was skipped for another reason: no tau with a complete 61-bar window.
- **Consequence.** The A21 exclusion stands: those days are invalid for the price-path injections. D7 on the remaining days is unchanged.
- **Record.** `section5/results/d7_nan_diag/d7_nan_diag.json`; script `section5/s5_d7_nan_diag.py` (LABEL_FREE; same tau rng as `s5_d7.fold_unit`).

## D3. Grid sensitivity conflates resolution with an update-counted event rule (O9 M3)

See `section5/results/a22/grids_NOTE.md`.

## D4. Smaller items (O9 Low)

- **D7 MDE (A22 4b).** The simulation draws null and injected hits independently; the real statistic pairs them by day and tau, so the MDE is conservative.
- **D7 liquidity gate i.** It passes by construction (the variance ratio is 1 because the price path is untouched); it tests nothing for liquidity.
- **A18 objective.** The predictive NLL of the return is averaged over subset-dependent bar sets (sessions start at the first bar with all inputs present). This can favour fewer features; it applies to both A18 runs.
- **A18 backend kind.** The MR1 and MR2 A18 runs share the backend kind `a18-580bb98e81eb453b`; their completion records are told apart by directory only.
- **Grid code.** The 5-minute grid (78 slots, HSMM Dmax 78) is hard-coded in `s5_backend`, `s5_fast.ret5_matrix` and `s5_step2`; only the A22 grid path overrides it.
- **Delay scoring.** The A22 delay result scored delayed alarms on shifted data times (O9 M1); the corrected scoring is in amendment A25.
- **Clock.** Centred vendor cleaning inside a LEGACY bar cannot be detected here (A24 rule 1d).
