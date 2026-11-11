# Section 6: disclosed limitations (from the Fable re-audit)

Dated 2026-11-11T00:54:00+00:00 UTC (2026-11-10T19:54:00-05:00 New York). This is a disclosure list for the paper. It changes no rule, result or verdict. Source: `FABLE_REAUDIT.md` (sha256 `11cf11db13e41f9d811b31820b6d411903425425a40dfb6a106af0feb4b48a19`) and the user's order of 2026-11-10. The Section 5 list is `SECTION5_DISCLOSED_LIMITATIONS.md`.

## S6-D1. The A31 rule 3 placebo-filter control is not specific to the alarm filter (re-audit L2)

The control compares a break's filtered placebos with times drawn by the same matching but without the alarm exclusion. A31 3d reads a flag as "the alarm filter, not the break, moves the H3 outcome". The synthetic check of A31 rule 4 shows that reading is too strong.

Flag rate per asset in `section6/results/synth_validation_a31r.json` (sha256 `afc02b55e2d7b78167445e3aba9e4e0c8e21ea025573c8b49aa1dd0b1b29d939`):

| Scenario | Replicates | TLT | HYG | Gold | USD | Mean delta |
|---|---|---|---|---|---|---|
| No effect, "indep" | 200 | 6.0% | 6.0% | 4.0% | 4.5% | about 0 |
| No effect, "vol" | 200 | 5.5% | 5.0% | 4.5% | 7.0% | about 0 |
| H3 planted | 40 | 0% | 0% | 7.5% | 0% | -0.002 to -0.006 |
| **H4 planted** | 40 | **22.5%** | **17.5%** | **20.0%** | **12.5%** | **+0.023 to +0.027** |

- **Under no effect the control is calibrated** (4.0-7.0% against a nominal 5%). That is what A31 rule 4b required, and it passed.
- **With H4 planted it flags 12.5-22.5% of replicates, although the generator has no filter bias.** The planted effect is a same-hour asset move at each break. The comparison set has no alarm exclusion, so it contains times shortly after real alarms, and those carry the break's own effect. The control then measures the break, not the filter.
- **The control is therefore miscalibrated as a test of filter bias whenever breaks have a cross-asset effect.** A flag shows that filtered and unfiltered matched times differ. It does not show which of the two causes is at work.
- **Consequence for the reported flag.** The Gaussian HMM TLT flag (delta +0.030, interval +0.008 to +0.052) has the size and sign the planted-H4 scenario produces (+0.026). It is not evidence that the filter biases the Gaussian H3 TLT gamma by 0.03. The sentence in the report of 2026-11-10 that said so is withdrawn.
- The two sets also overlap, since an unfiltered draw can pass the filter. That shrinks delta towards 0.
- Unchanged: A31 rule 3 and its results stand as written. No H3 or H4 verdict depends on the control; it is a check outside Holm and BH.

## S6-D2. What the A26 label guards do not cover (re-audit M3)

Closed on 2026-11-10 without touching the frozen closure (code version `a0323ed24d68e896`):
- a Section 5 evaluation-period read through `s5_eval_loader` is refused unless it happens inside `s5_eval_label.run_confirmatory_labelled`;
- `s6_run.write_once` requires the label on every result once the process has been allowed any evaluation-period read, whatever the result's `period` field says;
- `s5_eval_label.ready()`, which every evaluation read calls first, refuses while any script in `section5/`, `section6/` or the repository root calls the 5.13 writer directly;
- a `run_fn` result that is not a dict is wrapped and labelled instead of raising after the one-shot marker.

Not closed:
- **The 5.13 writer stays callable.** `s5_freeze.run_confirmatory` is in the closure and cannot be edited. A caller in a folder that is not scanned, or an interactive session, can still call it. Such a call cannot read evaluation rows through the guarded loader, and its output fails `verify_labelled`, but the call itself is not blocked.
- **Reads that bypass the loader.** A direct read of the panel files is outside every label guard. The contamination registry pattern matches it in `section5/` and `section6/` only.
- **Section 6 writers that do not use `write_once`.** `s6_coverage.py` writes its two files directly (re-audit L7). It reads development spans only.
- **Module state.** The guards are Python module attributes. Code that sets `ACTIVE` or clears `EVAL_READS` by hand defeats them; nothing in the repository does.
- **Tables, figures and sentences.** A26 1d applies to them. No code checks them; they are labelled by hand.
- **Unserialisable results.** A `run_fn` result that JSON cannot write still fails inside the closure after the marker. A dry run of the real `run_fn` on development data is the safeguard.

## S6-D3. Records that predate the A35 and A32 corrections

- **H4 p-values in the development results.** `s6_development_{gaussian_hmm,hsmm}.json` were written under the A29 1d convention and are not recomputed (A35 1f). Their H4 p-values under A35 rule 1 are in the table of `AMENDMENT_A35.md`. No verdict differs.
- **Power.** The A29 1f power check was not rerun under A35 rule 1. Its simulated data have no missing values, so invalid resamples are rare there.
- **A32 hash in provenance blocks.** Result files written between 2026-11-10 21:44Z and 23:31Z (`h2_*`, `hyg_gap`, `a34_*`) record `AMENDMENT_A32.md` as `7bc90d60...`. That was the text with the corrected date stamp. The adopted text, `d222539c...`, was restored on 2026-11-11; the two differ in the "Dated" stamp only.
