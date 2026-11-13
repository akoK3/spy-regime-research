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

## S6-D4. "Calm-to-stressed" in Section 6 follows A28 1b, not protocol 5.5 (post-evaluation, 2026-11-13)

**What differs.** The breaks feeding H2-H4 are labelled by the A28 1b definition, "entry into the higher-variance state" (`AMENDMENT_A28.md:18`, adopted 2026-11-09 19:22Z). The break export (`section5/s5_break_export.py`) applies it:
- the new state is the argmax state at the confirming update;
- the old state is the reference state of the event rule;
- the label is calm_to_stressed when new > old in the family's variance order;
- BOCPD uses the predictive-variance ratio.

Protocol 5.5 defines direction differently (`SECTION5_PROTOCOL.md:64`; `section5/s5_events.py:74-82`): the ratio of mean squared SPY 1-minute returns over (T_d, T_c] to the 60 bars before T_d, with > 1 meaning calm to stressed. No amendment or ledger row says that A28 1b replaces 5.5 for Section 6. The export rule was committed in 01ac960 and recorded at `METHODS_LEDGER.md:488` without a description of the rule.

**What the label means.** "Calm-to-stressed" means any move to a higher-variance state, not only a move out of the calmest state. In the development export, 280 of the 600 Gaussian HMM confirmed calm-to-stressed breaks start in state 0; the other 320 start in state 1 or 2.

**How far the two rules agree** (`section5/results/direction_rule_agreement.json`; descriptive, development data only):
- Protocol 5.5 was applied to all 1,149 confirmed calm-to-stressed Gaussian HMM and HSMM breaks of `section5/results/breaks/breaks.csv`.
- **975 (84.9%) are also calm-to-stressed under 5.5, 160 are stressed-to-calm under 5.5, and 14 are undefined** (fewer than 30 valid reference bars). Agreement on the 1,135 defined breaks is 85.9%.

| Family, era | Breaks | 5.5 calm-to-stressed | 5.5 stressed-to-calm | Undefined | Agreement of defined |
|---|---|---|---|---|---|
| Gaussian HMM, LEGACY | 586 | 488 | 92 | 6 | 84.1% |
| Gaussian HMM, RAW | 14 | 11 | 3 | 0 | 78.6% |
| HSMM, LEGACY | 536 | 467 | 61 | 8 | 88.4% |
| HSMM, RAW | 13 | 9 | 4 | 0 | 69.2% |

| Gaussian HMM, by old state | Breaks | Agreement of defined |
|---|---|---|
| Old state 0 | 280 | 79.0% |
| Old state 1 | 277 | 86.9% |
| Old state 2 | 43 | 97.7% |

Median 5.5 ratio: 1.91 (interquartile range 1.26-3.12).

**Label counts of confirmed breaks in the development export** (all four detectors; no confirmed break is labelled same_state or left without a direction):

| Detector | LEGACY calm-to-stressed / stressed-to-calm | RAW calm-to-stressed / stressed-to-calm |
|---|---|---|
| Gaussian HMM | 586 / 120 | 14 / 2 |
| Student-t HMM | 493 / 185 | 14 / 0 |
| HSMM | 536 / 88 | 13 / 0 |
| BOCPD (variance ratio) | 409 / 162 | 17 / 9 |

**Consequence.** The evaluation used the A28 1b labels throughout. About one in seven of these breaks would carry the other direction under protocol 5.5. No Section 6 result is recomputed under 5.5.
