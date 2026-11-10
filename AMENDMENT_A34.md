# Amendment A34 (per-asset placebo pools for E1, the |return| statistic and an H3 sensitivity; A26 label enforced in code)

Dated 2026-11-10T23:27:00+00:00 UTC (2026-11-10T18:27:00-05:00 New York). Status: ADOPTED 2026-11-10T23:27:21Z (user decision 2026-11-10: "HYG: option 1 for E1 and the |return| statistic"; the draft, sha256 35657c68dd093490..., is unchanged apart from this status line). Written before its code.
- **Decided by the user on 2026-11-10:** "HYG: option 1 for E1 and the |return| statistic (per-asset placebo pools from sessions with that asset's data, same matching), labeled post-diagnosis. H3 primary unchanged; add the per-asset-pool H3 as a pre-specified secondary sensitivity for all assets. Write as A34, adopt, recompute only the affected dev parts. Also make sure Fable L3 (exploratory label on evaluation-period outputs) is enforced in code before the freeze."
- **Disclosed: this is post-diagnosis.**
  - The label-free HYG diagnosis (`section6/results/hyg_gap/hyg_gap.json`) showed the cause of the gap: 78-81% of HYG placebo windows fall on sessions without HYG data, because A28 1d / A31 placebos are matched on SPY only.
  - Before that diagnosis, the E1, A32 and H3 development results computed with the common placebos had been seen.
  - Every quantity below is labelled "post-diagnosis". The H3 sensitivity is specified here before it is computed; it is still post-diagnosis, not pre-registered.
- No freeze, no O8, no era calibration.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `section6/results/hyg_gap/hyg_gap.json` (label-free diagnosis) | `c93141b19d44df3fcccc4a11bdd641483600c12db9bbf59dc60666e4fa096f68` |
| `AMENDMENT_A31.md` (rule 1: placebo matching, past alarms only) | `1efd5a1f338b31c6f7459c8d328c854450eed6800052d2be261f83d240ef036f` |
| `AMENDMENT_A33.md` (rule 4: A32 statistic exploratory; rule 5c: E1 as A32 4c) | `f101adce416ed256499fe779f5c0152de4c26d6bfbd9324a7a2546ecf9506747` |
| `FABLE_AUDIT.md` (L3: the A26 label is never attached) | `005129986659b5827f94bf491f4120ae19db3ec674d25d78b50974f2ecc7db57` |

## Rule 1: per-asset placebo pool

1a. For a unit and an asset a, the per-asset placebos are drawn exactly as the A31 rule 1 placebos, with one added condition: asset a is available (coverage rule) in the placebo's session. Every A31 condition still applies:
  - same era;
  - an earlier session;
  - the same 30-minute slot of S;
  - the same SPY prior-hour-RV decile, with cut points from all candidate times of earlier sessions, as before (the added condition does not change the cut points);
  - no confirmed alarm in [T_p - 60, T_p);
  - T_p <= 390;
  - 20 per unit.
1b. The seed is fixed per (unit, asset). Units are the A32 / H3 units: confirmed calm-to-stressed breaks, burn-in passed.
1c. For E1's chance reference only, a joint pool is drawn the same way, with TLT and HYG both available in the placebo's session (E1 needs both).

## Rule 2: recomputed parts (development, Gaussian HMM and HSMM; labelled "post-diagnosis")

2a. **The A32 deseasonalised |return| statistic** (A33 rule 4: exploratory, uncorrected).
  - Per asset, with that asset's per-asset placebos; otherwise exactly A32 rules 2-3.
  - Windows +5, +15, +30, +60 (tested); (T - 30, T] descriptive.
2b. **E1** (descriptive), with these differences from A32 4c:
  - each asset's "unusual" cutoff uses that asset's per-asset placebo windows;
  - the placebo shares classify each joint-pool placebo, with each asset's cutoff from that asset's per-asset placebos (excluding the classified time if it is among them).
  Categories and their order are unchanged.
2c. **H3 sensitivity (secondary, outside Holm).**
  - H3 next-day, per asset (TLT, HYG, gold, USD), exactly as A28 3b-3c (controls; week-block bootstrap within era, 9,999 resamples), with the per-asset placebos.
  - BH across the 4 assets, as its own small secondary family.
  - **The H3 primary (common placebos) is unchanged and remains the primary.**
2d. Only these parts are recomputed. Every other development result, and its file, is unchanged. Outputs go to `section6/results/a34_development_{detector}.json`, written once with provenance.

## Rule 3: A26 label enforced in code (FABLE_AUDIT L3)

3a. **Section 6.** `s6_run.write_once` refuses any result whose `period` is not "development" unless both hold:
  - it carries `a26_label` = "adaptive/exploratory (previously exposed period)";
  - it carries `confirmatory` = false.
  `s6_h2` writes through the same function.
3b. **Section 5.** The 5.13 writer (`s5_freeze.run_confirmatory`) is in the frozen result-module closure (code version a0323ed24d68e896) and is not edited. A new module outside the closure, `section5/s5_eval_label.py`, adds two things:
  - `run_confirmatory_labelled(...)`: the only sanctioned entry to 5.13. It wraps the caller's `run_fn`, so every per-era evaluation result carries the label and `confirmatory = false` before the closure writes it.
  - `verify_labelled(results_dir)`: refuses if any evaluation-period result file lacks the label.

  It is registered in the contamination registry. `s5_eval_loader.eval_guard` refuses unless `s5_eval_label` imports and its label equals the A26 rule 1d text in `AMENDMENT_A26.md`, so the module is in place before any evaluation-period read.
3c. Unit tests show a refusal for an unlabelled evaluation-period output, and that a labelled one passes.

## Rule 4: order

4a. A34 is hashed into the ledger before its code. It is adopted on the user's approval: status line, sidecar, ledger row, ledger tests.
4b. A34 is added to the freeze manifest. The A34 development computation refuses to start unless A28-A34 (and A33.1) are ADOPTED and equal their sidecars.

## Governs

Per-asset placebo pools for E1, the A32 statistic and the H3 sensitivity; the enforcement of the A26 label in code. The H2 and H3 primaries, H4, A30 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.
