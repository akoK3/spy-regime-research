#!/usr/bin/env python3
"""Integrates AMENDMENT_A11 into SECTION5_PROTOCOL.md (consolidation only). The previous frozen text is preserved byte-identical as SECTION5_PROTOCOL_v1_FROZEN_A10.md. Refuses to run twice."""
import hashlib, datetime, shutil
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V1 = ROOT / "SECTION5_PROTOCOL_v1_FROZEN_A10.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); PREV = "51264c1d8bfb23fd446756308151a7cdaa9cc80b66f50f98a248dd14eb438fad"
assert sha(P) == PREV, "protocol is not the A10 frozen version"; assert not V1.exists(); shutil.copyfile(P, V1); V1.with_suffix(".sha256").write_text(f"{sha(V1)}  {V1.name}\n", encoding="ascii")
t = P.read_text(encoding="utf-8"); now = datetime.datetime.now(datetime.timezone.utc)
def rep(a, b):
    global t; assert t.count(a) == 1, a[:60]; t = t.replace(a, b)
rep("**Status: FROZEN** (integrated through Amendment A10).", "**Status: FROZEN** (integrated through Amendment A11).")
rep("Frozen ", "Re-frozen with A11 ")
rep("This file consolidates the original draft and Amendments A6 to A10.", "This file consolidates the original draft and Amendments A6 to A11. The previous frozen text (through A10) is preserved unchanged as `SECTION5_PROTOCOL_v1_FROZEN_A10.md` (sha256 `%s`)." % sha(V1))
rep("\n\nSupporting records", "\n| A11 | `AMENDMENT_A11.md` | era-level threshold for 5.13, HSMM K 2-3 (A10 citation corrected), H1(c) release times, cold audit status | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A11.md"))
rep("Supporting records (not part of the rules): cold audit `section5_cold_audit.md`,", "Supporting records (not part of the rules): cold audit `section5_cold_audit.md` with its status list `COLD_AUDIT_STATUS.md`,")
rep("detection within 60 min of FOMC 14:00 announcements in uncontaminated test segments", "detection within 60 min of each FOMC statement's actual release time (read from its federalreserve.gov page; meetings without a stated time are excluded; A11 item 3) in uncontaminated test segments")
rep("5.12 Freeze final setups, thresholds and hashes", "5.12 Freeze final setups, thresholds (era-level, 5.13) and hashes")
rep("5.13 Refit the frozen setup on full TRAIN per era; run once", "5.13 Era-level threshold (A11 item 1): for each era with n TRAIN sessions, each family's frozen final setup is refitted on sessions 0 to n - 64, the next 5 sessions are the embargo, and the last 58 sessions are native calibration sessions on which the A7 rule (bisection to 0.2 alarms per session, same bounds and flags) sets the threshold; the threshold is frozen in 5.12 and used unchanged with the refit below (it comes from a model fitted on a shorter sample than the model it is applied to; the realized rate on the calibration sessions is reported). Refit the frozen setup on full TRAIN per era; run once")
rep("28 folds confirmatory; 112 eligible FOMC events for H1(c) (`section5/results/contamination_list.json`).", "28 folds confirmatory. H1(c) events (A11 item 3): of 152 listed meetings, 48 statement pages state a release time (all 14:00 ET: 2016-2018 and 2022-2024), 104 are unavailable (103 'For immediate release', 1 page not found as the FOMC statement) and are excluded without assuming a time (`section5/results/h1c_release_times.json`); 16 eligible events remain in uncontaminated test segments (LEGACY folds 24-26, RAW fold 0) (`section5/results/contamination_list.json`). H1(c) is secondary and has low power with 16 events.")
rep("data backend `s5_backend.py`.", "data backend `s5_backend.py`; era-level calibration `s5_era_threshold.py`; release-time reader `s5_h1c_times.py`. HSMM K grid {2, 3}, Gaussian and Student-t HMM {2, 3, 4}, BOCPD lambda {12, 39, 78} (A11 item 2; the A10 sentence with K in {2, 3, 4} for the HSMM and its 5.4 citation was wrong). The A10 machinery check tuned the HSMM over {2, 3, 4}; its HSMM tuning results are not valid under 5.4 and the check is to be repeated before it is cited for the HSMM.")
a = t.index("## Open items at freeze"); t = t[:a] + """## Open items (not decided; each needs an amendment before the step that depends on it)

- Cold audit findings: 3 resolved, 4 disclosed, 15 open (`COLD_AUDIT_STATUS.md`). Open findings that change alarm behaviour (EM tolerance 6, old state in the refractory period 7, tau cap 9, pre-seam hits 14, unconfirmed alarms 15) are not fixed.
- The era-level calibration (A11 item 1) is implemented (`s5_era_threshold.py`) and unit-tested for the split; it has not been run on data.
- The HSMM tuning of the A10 machinery check must be repeated with K in {2, 3}.
- H1(c) has 16 eligible events, because release times are stated only on 2016-2018 and 2022-2024 statement pages.
"""
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
