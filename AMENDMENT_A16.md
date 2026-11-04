# Amendment A16 (re-audit after A15: guards of the main run made binding)

Dated 2026-11-04T01:34:38.727312+00:00 UTC (2026-11-03T20:34:38.727312-05:00 New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Decided by the user after the re-audit of A15 appended to `section5_cold_audit_2.md` (commit `cb4c45f`). Facts only.

## Record of the audit file's new hash

`section5_cold_audit_2.md` now holds the second cold audit and its re-audit after A15. Its sha256 is `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602` (commit `cb4c45f`). A15, the A15 protocol and the A15 audit status files cite the first version, sha256 `700a09fc527f00d532021deafdcd725641b9eea900caf03065bcdc11f011d942` (commit `b3c400d`, byte-identical to the first part of the current file); those citations stay as records of that version.

## Evidence cited (hashes before this amendment's changes)

| Document | SHA-256 |
|---|---|
| `section5_cold_audit_2.md` | `f6b2f00a474fffd1d9a278e2503cd8bbc2468f5560a27ad9904265aa14ea7602` |
| `SECTION5_PROTOCOL.md` | `a86cf099dfd6ed7af416fc2603a6951c18ce3e7fdf659a76599bf4f14bee5ea1` |
| `AMENDMENT_A15.md` | `15de695a9f16445a17271773e37e9089ff852f5304fd2ca90549b3e9267ddc2d` |
| `section5/results/contamination_list.json` | `f6d67a57ca30184bc6f2f00f5a4e3aafa0d8808a6e90784def110cdaf19d067b` |
| `section5/s5_run.py` | `27a601e532bd46562ee4d54449b0027947deb8a589a8e068acd96e5229f6c8fe` |
| `section5/s5_backend.py` | `c62a8c66e08ae9a1c3bb1cd1a3783f466c332e16c07a846dd8854671310a3563` |
| `section5/s5_main.py` | `7f25242c33f7a643734d3294a02adcc5de4f8ac90c0c5e8fc6a6f1655782c3d4` |
| `section5/s5_era_threshold.py` | `d64a8e04e6aa3fe02041394a579d0beb84c987f8d934747d5d14ca4d82f84517` |
| `section5/s5_contamination.py` | `04fbf33200e83fa8a1907d048fca0ccfaaec243e023659f5ef164670cc2eb42d` |

## Rules (re-audit new problems 1-6 = audit 2 findings 16-21)

1. Era calibration needs a completion record (finding 16). `run_all` writes `run_complete.json` with a sha256 sidecar into its run directory after every fold and family has been selected and scored. It holds the backend kind, the fold list, the code version, the verified protocol hash, the contamination list hash and the sha256 of all fold results. `EraBackend` cannot be constructed without a record whose sidecar matches, whose protocol and contamination hashes equal the current verified ones, whose code version equals the current one, whose backend is the main backend and whose folds are all 34 folds. `MainBackend` has no completion flag; `freeze_step` passes the record.
   - WHY: the A15 guard was a public flag on one class; `EraBackend` could be calibrated directly. EVIDENCE: re-audit new problem 1 (measured).
2. Canonical contamination list (finding 17). The list is the fixed file `section5/results/contamination_list.json`; no function takes another list. Every use (fold backend, main backend, `run_all`, `freeze_step`, freeze hashes) checks that its sha256 equals its sidecar and equals the hash stated in protocol 5.14; otherwise an error is raised. Regenerating the list therefore needs an amendment.
   - WHY: a caller-supplied list could serve a clean fold without the protocol hash and change the confirmatory set; the freeze did not compare lists. EVIDENCE: re-audit new problem 2 (measured).
3. Registry pattern (finding 18). `check_registry` also matches `era_context(`, `splice_batch(` and the pool initialisers of `s5_d2` and `s5_fast` (`D2._init`, `F._init`, with or without a call).
   - WHY: these load an era panel and passed the A15 check. EVIDENCE: re-audit new problem 3 (planted script not reported).
4. No version override (finding 19). `run_all` has no `files` argument; the checkpoint version is always the A15 closure. `code_version` takes only the base directory (for tests).
   - WHY: the override restored the narrow pre-A15 version. EVIDENCE: re-audit new problem 4 (measured).
5. Lock after era calibration (finding 20). Before its first model fit, `EraBackend.calibrate` writes `section5/results/ERA_CALIBRATION.lock` (era, time, protocol hash, completion record hash). While the lock exists, no selection or scoring can be computed: `run_all` raises on any checkpoint unit it would have to compute, and the fold backend refuses `objective` and `score`. Reading existing checkpoints stays possible. The lock is never removed by code.
   - WHY: the era fits touch every fold's test segment; a later re-scoring would use touched sessions without any record. EVIDENCE: re-audit new problem 5.
6. Protocol hash bound to results (finding 21). `run_all` verifies the protocol (FROZEN, sidecar match) itself; the checkpoint version combines the code version and that hash, so an amended protocol misses every checkpoint. The run summary and the completion record carry it. `freeze_step` takes no protocol argument: it verifies the protocol again and refuses unless the hash equals the one in the completion record (and the main backend's); the freeze records it.
   - WHY: `freeze_step` stored any string; checkpoints did not depend on the protocol. EVIDENCE: re-audit new problem 6.

## Governs

Code in a new `s5_guard.py` (no data access: protocol, contamination, completion record, lock, code version), `s5_run.py`, `s5_backend.py`, `s5_main.py`, `s5_era_threshold.py`, `s5_contamination.py` (pattern; list sidecar), `s5_dry_run.py`, `s5_machinery_run.py`; unit tests (`s5_tests_a16.py`; existing suites updated for the removed arguments); the contamination list sidecar; the protocol re-freeze (5.14 states the list's sha256; previous text preserved as `SECTION5_PROTOCOL_v7_FROZEN_A15.md`); audit status files (findings 16-21 added, audit-2 citation updated); ledger rows with WHY and EVIDENCE. No model is fitted, no detector run, no data read.
