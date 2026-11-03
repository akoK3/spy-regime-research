#!/usr/bin/env python3
"""Writes COLD_AUDIT_STATUS.md (+ sidecar): status of the 22 findings of section5_cold_audit.md. Facts only. Refuses to overwrite."""
import hashlib, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "COLD_AUDIT_STATUS.md"; assert OUT.exists() and (ROOT / "COLD_AUDIT_STATUS_v1_A11.md").exists()      # A12 rewrite; the A11 version is preserved
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = [
 (1, "Critical", "H1(a) scores zero-effect breaks above chance", "disclosed", "Cause fixed (A8 item 1: scale in the detector's units, unit-tested; placebo gaps no longer positive across the board). Residual: the R=1 gate failed on LEGACY 29 and is documented, not resolved (A8.3, A8.4, protocol 5.15); the unexplained f3 excess on LEGACY 25 was not re-measured; the chance term in the metric is unchanged."),
 (2, "Critical", "A7 decided after test curves were seen", "disclosed", "A8 item 2 and protocol 5.14: A7 stays; RAW 3 is on the contamination list and excluded from confirmatory H1."),
 (3, "High", "Evidence sits inside earlier folds' test blocks", "resolved", "A8 item 2: sessions touched by any pilot or diagnostic are listed mechanically; folds whose test segment intersects the list (6 of 34) are excluded from confirmatory H1; all-folds sensitivity reported."),
 (4, "High", "H1(a) crashes on 8 LEGACY folds; 19 usable", "resolved", "`build_specs_safe` skips instead of crashing (A8 item 3, unit-tested). Disclosed remainder: the 5.9 block bootstrap runs over the evaluable folds in order, so gaps between skipped folds are not respected; the protocol does not define this."),
 (5, "High", "Feature pool selected on all of TRAIN (N.3)", "disclosed", "A8 item 4: justification (label-free screening); limits stated; no in-fold recomputation."),
 (6, "Medium", "EM stopping is relative, not the 1e-4 of 5.4", "resolved", "A12 finding 6: absolute tolerance 1e-4 nats on the total training log-likelihood for all three EM models; fits at the 200 cap are recorded (`fit_info.converged`); unit-tested. Machinery rerun: of 239 EM starts on RAW 3, 56 reached the cap (Student-t HMM 39 of 70); of 187 on LEGACY 29, 30 (Student-t HMM 18 of 50, HSMM 12 of 67)."),
 (7, "Medium", "Old state re-based in the refractory period", "resolved", "A12 finding 7: the old state is no longer re-based inside the refractory period (loop detectors and vectorised sweep agree; unit-tested)."),
 (8, "Medium", "Null splices carry natural shifts as large as small breaks", "disclosed", "A8.1: the placebo, not the null splice, is the zero-effect reference; the null construction is unchanged."),
 (9, "Medium", "Break tau capped at 13:55 for all cells", "resolved", "A12 finding 9: `tau_cap`: permanent breaks and nulls to slot 299 (14:30), sandwiches to availability 14:00 and in-session end (slot <= 269 / 264); unit-tested on a synthetic panel. The A8 gate scripts keep the historical G_MAX."),
 (10, "Medium", "Fold-level Lee-Mykland threshold never used", "open", "No change; affects the sensitivity set only."),
 (11, "Medium", "Checkpoint keys omit the code version", "resolved", "`s5_run.py` keys every unit with a code-version hash (A9, A10; unit-tested). The old pilot scripts keep their old keys and are not used for the run."),
 (12, "Medium", "'25 of 25 checks' overstates coverage", "open", "No change made to those checks; the A10 machinery check adds its own (guards, resume, finiteness)."),
 (13, "Medium", "+/-0.05 threshold robustness undefined under A7", "open", "No amendment defines it."),
 (14, "Low", "Hit window counts pre-seam evidence", "resolved", "A12 finding 14: a hit needs T_d strictly after tau and T_c within 60 min (`hit_in_window`, sweeps); unit-tested. Feature look-back windows still contain pre-seam bars."),
 (15, "Low", "Unconfirmed alarms not counted", "resolved", "A12 finding 15: candidates open at the close are returned as dropped by the loop detectors and by the sweeps (`return_dropped`), and the backend reports the share at the calibrated threshold; unit-tested."),
 (16, "Low", "Seeds, versions and shares not recorded", "open", "Partly: run summaries record the code version; seeds, library versions and abstention/skip shares are not recorded in them."),
 (17, "Low", "Input hashes not checked at run time", "open", "The backend records input hashes for the freeze but does not verify the data files against them."),
 (18, "Low", "Student-t states ordered by scale, not variance", "open", "No change made."),
 (19, "Low", "A bad Student-t start can win silently", "open", "No change made."),
 (20, "Low", "Superseded code paths still live", "open", "No change made (`V.events_for`, hard-coded RAW in `s5_d2.py`)."),
 (21, "Low", "Sensitivity pool not limited to RAW in code", "open", "No change made."),
 (22, "Low", "Unamended choices and records", "open", "Resolved part: the protocol no longer says DRAFT (frozen). Open: HSMM 0.5 pseudo-count and the duration cap of 78 were never amended; the s5_fast docstring credit and the LEGACY report's missing writer script and hash table are unchanged."),
]
cnt = {k: sum(1 for r in R if r[3] == k) for k in ("resolved", "disclosed", "open")}
L = ["# Cold audit status", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Source: `section5_cold_audit.md` (sha256 `{sha(ROOT / 'section5_cold_audit.md')}`), 22 findings. Cited by `AMENDMENT_A11.md`; updated by `AMENDMENT_A12.md` (the A11 version is preserved as `COLD_AUDIT_STATUS_v1_A11.md`). Status values: resolved (fixed and tested, or covered by an amendment that removes the problem), disclosed (stated in a dated record, problem remains), open (not addressed). Facts only.", "",
     f"Totals: resolved {cnt['resolved']}, disclosed {cnt['disclosed']}, open {cnt['open']}.", "", "| # | Severity | Finding | Status | Evidence |", "|---|---|---|---|---|"]
L += [f"| {n} | {sv} | {t} | **{st}** | {ev} |" for n, sv, t, st, ev in R]
L += ["", "Findings 6, 7, 9, 14 and 15 were fixed by A12. Still open: 10, 12, 13, 16-21 and the open part of 22; disclosed: 1 (residual), 2, 4 (gap handling), 5, 8."]
OUT.unlink(); OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print(cnt)
