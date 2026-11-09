# Amendment A26 (final evaluation relabelled as a pre-specified retrospective replication; protocol stays frozen at A20 with A21-A26 cited separately; H2 unchanged, H3 by its own amendment)

Dated 2026-11-08 (UTC time stamped at adoption). Status: ADOPTED 2026-11-09T16:11:26+00:00 UTC (user approval given in another session, confirmed in this one: "A25 and A26 were approved in another session"; the draft, sha256 529b36b1..., never committed and without a sidecar, is unchanged apart from this status line). Written before the 5.12 freeze, before the 5.13 era-level calibration and before any evaluation-period output exists. Decided by the user after the Section 5 review of 2026-11-08 ("Decisions approved"). Disclosed: MR2, its A17-style phase, D7 (A21), Step 2, all A22 results, A24 and the O9 audit have been seen; A23 has not produced results; A25 is a DRAFT. Facts only.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `frozen_documents/protocol_20261029T032641Z.json` (Section 4.3.0 freeze v2) | `3d6f0c96fce1c05f8e94d1a8c6e6b14a5b5b1c9f013e6a95dd1e96498cbfff8b` |
| `SECTION5_PROTOCOL.md` (FROZEN through A20) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |
| `AMENDMENT_A21.md` | `b4ed40509480b6a69e621c3be309ab28d397e8e2b53b25bd459d4da305b5eda0` |
| `AMENDMENT_A22.md` | `3ce7b683a1369659b14b22c068bcc25c6a7b14a7a6b15758946c7050f8a15217` |
| `section431_step3_all_in_one_results/protocol_amendment_4_3_0_A1_20261029T034121Z.json` (4.3.0-A1: LEGACY evaluation 2019-01-02..2022-03-04, retrospective/previously exposed) | `a57d55ccc760c2359d2d5d14c12d52a3fb1ba29a1bd3e222a71e6284886724ae` |
| `section431_step3_all_in_one_results/section_4_3_closing_report_addendum_audit_20261031T025306Z.json` (audit #7: LEGACY 2019-2022 features built and summarised by year) | `01a5028ad59541818ac9e8796484f6e5fb53a9dbb2ffbb09eec9b9edcace69dd` |

The hashes of A23, A24, A25 and of this amendment are not stated here: A25 and A26 are drafts whose status lines change at adoption. They are recorded by rule 2b at the freeze.

## Rule 1: the 5.13 run is a pre-specified retrospective replication on previously seen periods

1a. Governing text, quoted verbatim from `frozen_documents/protocol_20261029T032641Z.json` (Section 4.3.0 freeze v2):

| Field | Text |
|---|---|
| `retrospective_evaluation.exposure` | "PRIOR_FEATURE_AND_MODEL_SELECTION_EXPOSURE" |
| `retrospective_evaluation.defensible_use` | "Descriptive temporal replication and prespecified sensitivity with explicit adaptive/exploratory label" |
| `retrospective_evaluation.disallowed_claim` | "Untouched, independent final test or selection-adjusted confirmatory significance" |
| `selection_guardrails[4]` | "No nominal confirmatory p-values from exposed retrospective evaluation" |
| `confirmatory_test.rule` | "A separate timestamped full-model/analysis lock and independent exposure audit must precede any new confirmatory period. Do not claim the current construction freeze locks an unbuilt detector." |

1b. Relabel. The sentence of `SECTION5_PROTOCOL.md` 5.13 "Fold tests are development evidence; 5.13 is confirmatory." is read as: "Fold tests are development evidence; 5.13 is a pre-specified retrospective replication on previously seen periods." The protocol file itself is not edited (rule 2a).

1c. Scope. The freeze v2 text governs the RAW evaluation period (`retrospective_evaluation`, source epoch RAW, 2025-01-02 to 2026-10-12). A26 applies the same rules to the LEGACY evaluation period 2019-01-02 to 2022-03-04, which 4.3.0-A1 labels retrospective/previously exposed; LEGACY 2019-2022 sessions were also used by 4.8C and 4.8D (LEGACY fold 35) and its features were built and summarised by the 4.3.1 builder (audit #7).

1d. Following 1a exactly, for every result computed on either evaluation period:
- It is reported as a descriptive temporal replication of the development results, or as a pre-specified sensitivity, and every table, figure and sentence that reports it carries the label "adaptive/exploratory (previously exposed period)".
- No p-value computed on an evaluation period is reported as confirmatory, enters a Holm family as confirmatory, or supports a confirmatory verdict. Effect sizes, intervals and descriptive statistics may be reported under the label.
- The paper does not describe either period as an untouched or independent final test, and claims no selection-adjusted confirmatory significance from it.
- The 5.12 freeze is not described as locking any detector beyond the setups, thresholds and code it hashes.

1e. Unchanged: everything else in 5.13 (era-level threshold per 5.13 and A11 item 1, refit of the frozen setup on full TRAIN per era, one guarded run per era, no retuning) and in 5.12. The MR2 verdicts and all development results keep their existing labels.

1f. A confirmatory test needs a new period with no prior exposure, preceded by a separate timestamped full-model/analysis lock and an independent exposure audit (1a, `confirmatory_test.rule`). That is outside Section 5 and is not planned by this amendment.

## Rule 2: protocol frozen at A20; A21-A26 cited as separate hashed amendments

2a. `SECTION5_PROTOCOL.md` stays FROZEN through A20 at sha256 `15be2570...` and is not re-frozen. Reason: 5.12 requires the freeze to record the FROZEN protocol hash, verified equal to the completion record's (A16 rule 6), and the MR2 completion record carries this hash; a re-freeze would change it.

2b. The 5.12 freeze document lists A21, A22, A23, A24, A25 and A26, each with its file name, its status at freeze time (ADOPTED or DRAFT) and the sha256 of the file on disk, which must equal its sidecar. Only ADOPTED amendments are in force. The freeze is not written while an amendment that the freeze or the 5.13 run depends on is a DRAFT.

2c. Implementation constraint: the listing in 2b is produced without changing any module in the code-version closure (`s5_guard.result_modules`; code version `a0323ed24d68e896`), so that the MR2 completion record and checkpoints still verify. How the existing freeze path receives the list is checked before any freeze code is written. If it cannot be done without such a change, work stops and a further amendment decides.

## Rule 3: H2 unchanged; H3 by its own amendment

3a. H2 as stated in `SECTION5_PROTOCOL.md` 5.0 is unchanged, including its secondary analyses S1, S2, E1 and E2.

3b. H3 (break persistence and cross-asset confirmation) will be added by its own dated, hashed amendment. No cross-asset analysis runs before that amendment is adopted. That includes H2, which uses TLT, HYG, gold and USD returns.

## Governs

The reading of `SECTION5_PROTOCOL.md` 5.13 (rule 1b), the labelling of all evaluation-period results (rule 1d), the contents of the 5.12 freeze document (rule 2b) and the order of the cross-asset work (rule 3b). No code, no data and no result changes under this amendment.
