# Amendment A35 (H4 bootstrap p-value on valid resamples only; rerun of the A28 7d null control; H3/H4 primary detector if the Gaussian HMM fails it)

Dated 2026-11-11T00:13:41+00:00 UTC (2026-11-10T19:13:41-05:00 New York). Status: ADOPTED 2026-11-11T00:13:42Z (user pre-approval 2026-11-10: "Order, pre-approved unless you must deviate: 1. A35(a) ... 2. A35(b) ... Write A35(c) before the rerun"; the draft, sha256 dbb027098adb9cf5..., is unchanged apart from this status line). Written before its code and before the rerun of rule 2.
- **Ordered and pre-approved by the user on 2026-11-10 (New York):**

  > Order, pre-approved unless you must deviate:
  > 1. A35(a): fix M4 (H4 bootstrap p uses valid resamples only).
  > 2. A35(b): rerun the A28 7d null control exactly as pre-registered: 200 null sets, same seeds, fixed statistic, both detectors. No extra sets, no recalibration. If Gaussian still exceeds 10% on any test, A35(c) applies: Gaussian is ineligible as H3/H4 primary and HSMM is the H3/H4 primary; Gaussian remains eligible for H2 by the freeze rule. Write A35(c) before the rerun.
- **Disclosed: what had been seen when this was written.**
  - The Section 6 development results of both detectors, including the 7d null control: Gaussian HMM H4b rejected 10.5% of the 200 null sets (limit 10%); HSMM at most 8.0%.
  - No primary test was rejected for either detector. H4b: Gaussian p = 0.577, HSMM p = 0.084.
  - The share of invalid (NaN) bootstrap resamples per H4 test (`FABLE_REAUDIT.md` M4).
  - Rule 3 therefore names its two detectors knowing which one failed. It is written before the rerun's result exists.
- No freeze, no O8, no era calibration. No evaluation-period data.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `FABLE_REAUDIT.md` (M1: failed 7d check not disposed; M4: NaN resamples) | `11cf11db13e41f9d811b31820b6d411903425425a40dfb6a106af0feb4b48a19` |
| `AMENDMENT_A28.md` (ADOPTED; rules 1b, 3c, 7d) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `AMENDMENT_A29.md` (ADOPTED; rule 1d) | `304f27252b29d27649eeb68a0507f127fe24a602cd9556f5d43687bf24822715` |
| `AMENDMENT_A9.md` (item 2: H2 primary detector at 5.12) | `d915f7c90a38a0236a3962857235d7e1096b16f54065bb8104d3795ee4947bb0` |
| `section6/results/s6_development_gaussian_hmm.json` (7d null control failed: H4b 0.105) | `831c8ec5972e8f39a6112b75e9c72b439c8a6f096c20ded26895518fe0a1207e` |
| `section6/results/s6_development_hsmm.json` (7d null control passed: max 0.080) | `504a22ebbfb48805b06630c171bda271b6fd719129642eb09f6a05833be02ba8` |

Invalid resamples in the development run (9,999 resamples; A29 1d counted them as not exceeding):

| Test | Reported p | Valid resamples | p on valid resamples only |
|---|---|---|---|
| Gaussian H4a | 0.2842 | 9,651 | 0.2944 |
| Gaussian H4b | 0.5768 | 8,841 | 0.6523 |
| HSMM H4a | 0.1888 | 9,960 | 0.1895 |
| HSMM H4b | 0.0844 | 9,685 | 0.0871 |

## Rule 1 (a): H4 p-value uses valid resamples only (replaces the last sentence of A29 1d)

1a. For every H4 test, p = (1 + #{valid b: G*_b - G >= G}) / (V + 1).
  - G is the A29 rule 1 statistic; G*_b is its value in resample b.
  - A resample is valid when G*_b is finite. V is the number of valid resamples.
  - A29 1d's sentence "NaN resamples count as not exceeding" no longer applies to H4. Everything else in A29 rule 1 is unchanged: the statistic, the folds, the blocks, 9,999 resamples, centred, add-one.
1b. V = 0: the test is not evaluable. It enters Holm with p = 1 (A15 rule 6a), as before.
1c. Scope: as A29 1e. That is H4a and H4b, every H4 secondary, sensitivity and check, and the 7d null control.
1d. Reported beside each H4 test, as descriptive: V, and the p-value under the A29 1d convention from the same resamples.
1e. **H3 is unchanged** (A28 3c). Its development-run bootstraps had 9,997 to 9,999 valid resamples of 9,999.
1f. **Earlier results are not recomputed.** The development result files stand as written; the table above gives their H4 p-values under this rule. The A29 1f power check is not rerun: its simulated data have no missing values. `s6_power` uses this rule for H4 from now on.

## Rule 2 (b): rerun of the A28 7d(ii) null control

2a. **Exactly as pre-registered and as run in the development run:**
  - 200 null sets per detector, set index 0 to 199;
  - the same seeds: null-control seed 7, and the same unit, placebo and bootstrap seeds as the development run;
  - 9,999 resamples;
  - Gaussian HMM and HSMM;
  - the six primary tests, with the rule 1 p-value for H4a and H4b. H3 is computed as before.
2b. **No extra sets and no recalibration.** Nothing else is recomputed.
2c. **Criterion, unchanged (A28 7d):** for each of the six tests, the share of null sets with p <= 0.05 must be at most 0.10.
2d. **Reproduction check.** From the same resamples, the rerun also records each test's p-value under the A29 1d convention. The rejection rates under that convention must equal the development run's stored rates exactly, for both detectors. If they do not, the rerun is not used, work stops and the user is told.
2e. Outputs: `section6/results/a35_null_control_{detector}.json`, written once with provenance. Development data only.

## Rule 3 (c): consequence for the H3/H4 primary detector (written before the rerun)

3a. **If the Gaussian HMM exceeds 0.10 on any of the six tests in the rule 2 rerun:**
  - the Gaussian HMM is ineligible as the H3/H4 primary detector;
  - the HSMM is the H3/H4 primary detector;
  - the Gaussian HMM remains eligible as the H2 primary detector by the 5.12 freeze rule (A9 item 2), which is unchanged.
3b. In that case rule 3a replaces two sentences of A28, for H3 and H4 only:
  - A28 7d, "A failed sanity check stops the work before the joint evaluation": the Gaussian failure no longer stops the work;
  - A28 1b, "H3 and H4 use the same detector" as H2: they use the HSMM, whichever detector the freeze selects for H2.
  The Gaussian HMM's H3 and H4 results stay in the A28 7a detector-dependence analysis, with the failed check stated beside them.
3c. **If the Gaussian HMM passes** (at most 0.10 on every test): nothing changes. A28 1b stands.
3d. **If the HSMM exceeds 0.10 on any test:** A28 7d applies as written. Work stops before the joint evaluation and the user decides.
3e. The rerun's result files are hashed into the ledger. Their rows state which of 3a, 3c or 3d applies.

## Rule 4: order

4a. A35 is hashed into the ledger before its code. It is adopted on the user's pre-approval: status line, sidecar, ledger row, ledger tests.
4b. A35 is added to the freeze manifest. The rerun refuses to start unless A28-A35 (with A33.1) are ADOPTED and equal their sidecars.
4c. The rerun follows the rule 1 code and its unit tests. It runs detached.

## Governs

The H4 bootstrap p-value; the rerun of the 7d null control; the H3/H4 primary detector when the Gaussian HMM fails that control. A28, A29 and A31 are otherwise unchanged. H2, A30, A34 and every Section 5 result are unchanged. No freeze, no O8, no era calibration under this amendment.

## Disclosure added 2026-11-11 (PREFREEZE_AUDIT L1; on the user's instruction; the rules above are unchanged)

- **Rule 1a can only lower the 7d null-control rejection rates.** For any set of resamples, the valid-only p, (1 + E) / (V + 1), is at least the A29 1d p, (1 + E) / (B + 1), because V <= B.
- **The rerun shows this.** The Gaussian HMM's H4b null rejection rate moved from 0.105 under the A29 1d convention (equal to the development run) to 0.065 under rule 1a (`section6/results/a35_null_control_gaussian_hmm.json`). The other five tests did not change.
- **So the Gaussian HMM passes the 7d null control partly because of the convention change.** Rule 3 was written before the rerun, but given rule 1a the outcome was largely set when rule 1a was adopted. The write-up states this.
- **No minimum V is set.** Every H4 p now reports V / B (`valid_share`, `s6_run.h4_test`), and V / B below 0.9 is flagged (`low_valid_share`), on the development and the evaluation runs alike.
- Text before this note: sha256 `bf84069e620e5b839c2f98b259b0740ef982b4a999a4f9252eb587808a21e1b3`.
