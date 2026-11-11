# Amendment A37 (TRAIN refits at the freeze; the evaluation step only loads frozen models; one-shot marker immediately before the first evaluation read; positive-control flag)

Dated 2026-11-11T02:14:37+00:00 UTC (2026-11-10T21:14:37-05:00 New York). Status: ADOPTED 2026-11-11T02:14:37Z (user order 2026-11-10: "Move the TRAIN refits of the final setups into the freeze step (5.12) ... Record this in A36 (or A37 if A36 can't change post-adoption) before the freeze"; the draft, sha256 dd176bacb0df7ff8..., is unchanged apart from this status line). Written before its code.
- **Ordered by the user on 2026-11-10 (New York):**

  > 1. Move the TRAIN refits of the final setups into the freeze step (5.12): fit, save and hash the models there. The evaluation step must only load those frozen models. Write the one-shot marker immediately before the first evaluation-data read, not before any fit. Record this in A36 (or A37 if A36 can't change post-adoption) before the freeze.
  > 3. If an evaluation-period positive control fails, flag it at the top of the report.

- **Why A37 and not A36.** A36 is ADOPTED and hashed (sha256 `f110e14f3633d764d8048bb67b192c6fff9b68d2540c85d0297d53448ff227db`), and the freeze manifest records it by that hash. An adopted amendment is not edited in place (the A32 correction of 2026-11-11 restored exactly that rule). A37 amends A36 where they differ.
- **What it fixes.** Under A36 rules 5a-5c, the 5.13 step fitted the frozen setups on full TRAIN and calibrated the baseline threshold after the frozen runner had already written the era's one-shot marker. A crash in those fits would have used up the era's only evaluation run without reading a single evaluation row.
- **Disclosed: what had been seen.** As for A36. No evaluation-period row has been read; no evaluation access log, freeze, lock or fingerprint exists.
- No freeze, no O8, no era calibration under this amendment.

## Evidence cited

| Document | SHA-256 |
|---|---|
| `AMENDMENT_A36.md` (ADOPTED; rules 5a-5c, 5i, 7b superseded or extended here) | `f110e14f3633d764d8048bb67b192c6fff9b68d2540c85d0297d53448ff227db` |
| `AMENDMENT_A16.md` (rule 5: era-calibration lock; rule 1: completion record) | `35b2b802a59d855229816be3d8919aef5b871c4304376d1b891d2318ffac7bf0` |
| `AMENDMENT_A26.md` (rule 1: label; 2c: no change to the closure) | `50bcbc04433f8c1d4ad7ad48bda4c29dcb2807bc6fa814b4cb33183cf4b6c5ea` |
| `AMENDMENT_A28.md` (rule 7d(i): positive control) | `7c6bd4bdee8bd839b1ff4c2346d81f15fd2b6b29af7a0d4b5e11738d9b673ac2` |
| `SECTION5_PROTOCOL.md` (FROZEN; 5.12, 5.13) | `15be2570a592279e71f3f76fbe62113b4c3263a9d9e4715eaf4d61294eaf4df3` |

## Rule 1: the TRAIN refits happen at the freeze (replaces the fit in A36 5a-5b and the baseline calibration in A36 5c)

1a. **When.** At the 5.12 freeze, after the completion record of the main run exists and before the freeze document is written.
1b. **What, per era and per family (all four families of the freeze):**
  - the frozen final setup (features, K or lambda) and the return-only baseline with its frozen parameters, each fitted on every TRAIN session of the era with the main run's fit (3 starts, seed 0);
  - the preprocessing (A20; zero-variance drop, logs, winsorisation, z-scores) fitted on TRAIN rows only, saved with the models;
  - the baseline model's era-level threshold by the A11 item 1 rule on TRAIN data only (fit on sessions 0 to n - 64, 5 embargo sessions, the last 58 as calibration, A7 bisection to 0.2 alarms per session);
  - the feature model's threshold recomputed by the same rule and code path, kept as a reproduction value. The frozen era threshold of 5.12 remains the one used.
1c. **Data.** TRAIN sessions only, through the audited Section 4 loader with the era's TRAIN span; every session is checked to be TRAIN in the split manifest. No evaluation or embargo session is read.
1d. **Saved and hashed.** One file per era and family, holding the two fitted models, the preprocessing, the setup, the thresholds of 1b, the code version and the list of TRAIN sessions. A manifest lists every file with its sha256 and has its own sidecar.
1e. **Recorded in the freeze.** The manifest's sha256 and every file's sha256 enter the freeze document under `input_hashes["frozen_models"]`.
  - Route: `s5_run.freeze_step` stores whatever `backend.input_hashes()` returns. A delegating wrapper around the main backend adds the model hashes to that dictionary. No module of the code-version closure changes (A26 2c).
1f. **Failure.** If any fit or calibration fails, no freeze is written and the error is reported. Nothing is fitted after the freeze document exists.

## Rule 2: the evaluation step only loads (replaces A36 5b-5c on the evaluation side)

2a. Before the era's one-shot marker can be written, the driver:
  - loads every model file of the era and checks its sha256 against the freeze document, and the manifest against its sidecar;
  - checks that each file's setup equals the freeze's final setup for that era and family;
  - records the feature-threshold reproduction (recomputed against frozen). A difference is reported as a deviation; the frozen value is used;
  - runs the evaluation guard's checks without reading: freeze and token, amendment list, era-calibration lock, data-hash preflight, label module. This is logged as PRECHECK, not ALLOWED.
  Any failure stops the driver with no marker written.
2b. **No model is fitted on the evaluation path.** The evaluation backend holds the frozen models and the frozen preprocessing and refuses any fit.

## Rule 3: the one-shot marker (replaces A36 5a's order)

3a. The frozen runner (`s5_freeze.run_confirmatory`, in the closure) writes the era's marker and then calls `fit_fn`. Under this amendment:
  - `fit_fn` returns the state that rule 2a already loaded and verified. It fits nothing and reads no file or data;
  - the first action of `run_fn` is the guarded evaluation read.
3b. The marker is therefore written immediately before the first evaluation-data read. Between the two, only the loader's own guard runs, and the precheck of 2a passed it seconds earlier.
3c. Work after the read (features on the joined panel, splices, scoring) can still fail. That consumes the run, by design: 5.13 is one run per era on the evaluation data.

## Rule 4: positive-control flag (adds to A36 2c)

4a. If the evaluation-period positive control of A28 7d(i) fails (p >= 0.05) or cannot be evaluated, the Section 6 evaluation result carries this in an `alerts` field placed first in the file, the driver logs it, and the report of the evaluation opens with it.
4b. It stays a reported check, not a gate (A36 2c).

## Rule 5: order

5a. A37 is hashed into the ledger before its code and adopted on the user's order; it is added to the freeze manifest. The joint driver requires A28-A37 ADOPTED with matching sidecars.
5b. The synthetic end-to-end run of A36 7a is rerun under A37. Added checks:
  - the model files exist and are hashed into the freeze before any evaluation read;
  - no model is fitted during the evaluation step;
  - the marker exists at the first evaluation read, and nothing was fitted after it;
  - a tampered model file is refused before any marker is written.
5c. The Section 6 fingerprint (A28 6e, A36 7b) also covers the freeze-model module.

## Governs

When and where the 5.13 TRAIN refits and the baseline threshold are computed; what the evaluation step may do before and after the marker; the positive-control flag. A36 is otherwise unchanged. Every development result and the frozen closure (code version a0323ed24d68e896) are unchanged. No freeze, no O8, no era calibration under this amendment.
