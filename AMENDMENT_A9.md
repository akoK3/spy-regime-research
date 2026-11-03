# Amendment A9 to SECTION5_PROTOCOL.md (Holm families, H2 simplicity order, confirmed implementation choices)

Dated 2026-11-03T14:51:02.996739+00:00 UTC (2026-11-03T09:51:02.996739-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code changes it governs. Facts only.

## Evidence cited (hashes of the files before this amendment's changes)

| Document | SHA-256 |
|---|---|
| `SECTION5_PROTOCOL.md` | `8abd20f3557dac0991e30ea8c2807aee35be9d7de1c79b199d7f371397c97479` |
| `AMENDMENT_A6.md` | `db787ec0071b5b6c0ff4048cd281bf54e95e0c60b5f25e89fb6f02d55d5744a5` |
| `AMENDMENT_A8.md` | `c22db3add937f4b47ff9fb7054a95e32e6a5a7722803e3bfc3d1023ed8d22931` |
| `AMENDMENT_A8_4.md` | `f57a8734aaf28fd1bac378edc7ec0f13a8f48dc7ea375e491b42612bb56d89e5` |
| `section5/s5_h1.py` | `7a085b73acde7666c21c81c5162ae9c90618a3597436cb1abe12e94d359f251e` |
| `section5/s5_freeze.py` | `b475099f19c1ed281eb2e8425b7aa9d9ea340c60ecf137b9059e6cfea3894f73` |
| `section5/s5_select.py` | `7fe092a3e602792a497a71943e8cc255a4c410d1f9e231f0169c4fed0cfc5a32` |
| `section5/s5_stats.py` | `13b0d952726068691f11bf6b38f0489d4a75639e3e39a69c4533e3f5323bd262` |
| `section5/s5_tests_build.py` | `fd96838efa62153ab433f22f739618bc05aa461fffe15381b74b187084c2e0a3` |

## 1. Holm across three H1 families

- A6 item 4: BOCPD is secondary, outside H1 and outside its Holm family; Holm in 5.11 runs across three families (Gaussian HMM, Student-t HMM, HSMM). `s5_h1.py` (code written after A8.4) ran Holm over four families, which contradicts A6 item 4.
- Now: `s5_h1.h1_decision` applies Holm to the three H1 families only; BOCPD is scored and reported with its intersection-union p-value, unadjusted, as secondary (A6 item 4). `FAMILIES` is split into `H1_FAMILIES` (three) and `SECONDARY_FAMILIES` (BOCPD). The unit test `test_h1_decision_holm_over_families` is corrected to three families.

## 2. H2 simplicity order

- 5.12: the H2 primary detector is the family passing H1 with the lowest median validation QLIKE; ties go to the simpler model. Order fixed: Gaussian HMM < Student-t HMM < HSMM (simplest first). BOCPD is not an H1 family and cannot be the H2 primary detector. This replaces the order chosen in `s5_freeze.py` (Gaussian HMM, BOCPD, Student-t HMM, HSMM), which was an unconfirmed implementation choice.

## 3. Implementation choices confirmed

- The block-bootstrap p-value (blocks of 3 consecutive folds, centred, one-sided, add-one correction) is the primary p-value of each H1 component; Wilcoxon and sign consistency are reported beside it (5.9).
- The final-setup feature count (5.8) is the median across folds, rounded half up.

## 4. Code under this amendment

- `section5/s5_run.py`: the orchestration of a full run (per-fold selection, H1(a)/(b) scoring, statistics, freeze, guarded refit) against an injected backend, with code-version-keyed checkpoints (audit finding 11) and the confirmatory fold exclusions of A8 item 2.
- `section5/s5_dry_run.py`: a dry run on synthetic data only (synthetic backend with known effects, temporary directories). No market data, no test or evaluation data.
- A data backend that connects the orchestration to the fitted models, splices and QLIKE series is not part of this amendment; it needs its own dated amendment before any run on data.

## Governs

The three changes above and the orchestration code with its synthetic dry run. No run on market data, test segments or evaluation periods.
