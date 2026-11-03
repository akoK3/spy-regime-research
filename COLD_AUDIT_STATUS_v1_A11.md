# Cold audit status

Written 2026-11-03T21:55:42.400510+00:00 UTC. Source: `section5_cold_audit.md` (sha256 `fc3b4a3fa8facb6a901b2916ecad4b9d45b407c9a23a736bfd86943d7c1fb062`), 22 findings. Cited by `AMENDMENT_A11.md`. Status values: resolved (fixed and tested, or covered by an amendment that removes the problem), disclosed (stated in a dated record, problem remains), open (not addressed). Facts only.

Totals: resolved 3, disclosed 4, open 15.

| # | Severity | Finding | Status | Evidence |
|---|---|---|---|---|
| 1 | Critical | H1(a) scores zero-effect breaks above chance | **disclosed** | Cause fixed (A8 item 1: scale in the detector's units, unit-tested; placebo gaps no longer positive across the board). Residual: the R=1 gate failed on LEGACY 29 and is documented, not resolved (A8.3, A8.4, protocol 5.15); the unexplained f3 excess on LEGACY 25 was not re-measured; the chance term in the metric is unchanged. |
| 2 | Critical | A7 decided after test curves were seen | **disclosed** | A8 item 2 and protocol 5.14: A7 stays; RAW 3 is on the contamination list and excluded from confirmatory H1. |
| 3 | High | Evidence sits inside earlier folds' test blocks | **resolved** | A8 item 2: sessions touched by any pilot or diagnostic are listed mechanically; folds whose test segment intersects the list (6 of 34) are excluded from confirmatory H1; all-folds sensitivity reported. |
| 4 | High | H1(a) crashes on 8 LEGACY folds; 19 usable | **resolved** | `build_specs_safe` skips instead of crashing (A8 item 3, unit-tested). Disclosed remainder: the 5.9 block bootstrap runs over the evaluable folds in order, so gaps between skipped folds are not respected; the protocol does not define this. |
| 5 | High | Feature pool selected on all of TRAIN (N.3) | **disclosed** | A8 item 4: justification (label-free screening); limits stated; no in-fold recomputation. |
| 6 | Medium | EM stopping is relative, not the 1e-4 of 5.4 | **open** | No change made. |
| 7 | Medium | Old state re-based in the refractory period | **open** | No change made; the code differs from the literal A6 wording. |
| 8 | Medium | Null splices carry natural shifts as large as small breaks | **disclosed** | A8.1: the placebo, not the null splice, is the zero-effect reference; the null construction is unchanged. |
| 9 | Medium | Break tau capped at 13:55 for all cells | **open** | No change made; the gate restricted null tau only for comparability (A8). |
| 10 | Medium | Fold-level Lee-Mykland threshold never used | **open** | No change; affects the sensitivity set only. |
| 11 | Medium | Checkpoint keys omit the code version | **resolved** | `s5_run.py` keys every unit with a code-version hash (A9, A10; unit-tested). The old pilot scripts keep their old keys and are not used for the run. |
| 12 | Medium | '25 of 25 checks' overstates coverage | **open** | No change made to those checks; the A10 machinery check adds its own (guards, resume, finiteness). |
| 13 | Medium | +/-0.05 threshold robustness undefined under A7 | **open** | No amendment defines it. |
| 14 | Low | Hit window counts pre-seam evidence | **open** | No change made. |
| 15 | Low | Unconfirmed alarms not counted | **open** | No change made (5.5 says dropped and counted). |
| 16 | Low | Seeds, versions and shares not recorded | **open** | Partly: run summaries record the code version; seeds, library versions and abstention/skip shares are not recorded in them. |
| 17 | Low | Input hashes not checked at run time | **open** | The backend records input hashes for the freeze but does not verify the data files against them. |
| 18 | Low | Student-t states ordered by scale, not variance | **open** | No change made. |
| 19 | Low | A bad Student-t start can win silently | **open** | No change made. |
| 20 | Low | Superseded code paths still live | **open** | No change made (`V.events_for`, hard-coded RAW in `s5_d2.py`). |
| 21 | Low | Sensitivity pool not limited to RAW in code | **open** | No change made. |
| 22 | Low | Unamended choices and records | **open** | Resolved part: the protocol no longer says DRAFT (frozen). Open: HSMM 0.5 pseudo-count and the duration cap of 78 were never amended; the s5_fast docstring credit and the LEGACY report's missing writer script and hash table are unchanged. |

Still open or only disclosed findings that bear on confirmatory H1 results: 1 (residual), 6, 7, 9, 14, 15. They are not fixed by A11; fixing any of them changes alarm behaviour and needs its own amendment before the main run.
