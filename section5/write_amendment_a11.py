#!/usr/bin/env python3
"""Writes AMENDMENT_A11.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE the code it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A11.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = ["SECTION5_PROTOCOL.md", "AMENDMENT_A7.md", "AMENDMENT_A8.md", "AMENDMENT_A10.md", "section5_cold_audit.md", "section5/s5_backend.py", "section5/s5_h1c.py", "section5/s5_contamination.py", "section5/results/d6_fomc_dates.json", "section5/results/contamination_list.json"]
now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A11 to SECTION5_PROTOCOL.md (era-level threshold, HSMM K, H1(c) release times, audit status)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Facts only.", "",
     "## Evidence cited (hashes before this amendment's changes)", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## 1. Era-level threshold for 5.13", "",
      "- Gap: A7 fixes the threshold rule on a fold's validation sessions; 5.13 refits on full TRAIN, where no validation segment exists.",
      "- Rule: for each era, with n = the number of TRAIN sessions of the era, the frozen final setup of each family (5.8, 5.12) is refitted on sessions 0 to n - 64 (n - 63 sessions); the next 5 sessions are the embargo; the last 58 sessions (58 = the validation length of RAW fold 3 and LEGACY fold 29 after their embargoes) are native calibration sessions. The threshold (theta for HMM/HSMM, m for BOCPD) is calibrated on those 58 sessions by the A7 rule (bisection to 0.2 confirmed alarms per session, same bounds and flags). The threshold is then frozen (5.12) and used unchanged with the full-TRAIN refit of 5.13.",
      "- Stated limit: the threshold is calibrated on a model fitted on a shorter sample than the model it is applied to; that is the rule as specified, and the realized alarm rate of the refit on the calibration sessions is reported when the freeze is built.", "",
      "## 2. HSMM K, and a correction to A10", "",
      "- 5.4 gives HSMM K 2-3; the Gaussian and Student-t HMM range 2-4. A10 item 1 wrote 'K in {2, 3, 4} for the Gaussian HMM, Student-t HMM and HSMM (5.4)': the HSMM range and the citation were wrong, and `s5_backend.py` followed it. Corrected: the HSMM grid is K in {2, 3}; HMM families {2, 3, 4}; BOCPD lambda in {12, 39, 78}. A10 stays on record unchanged; this amendment supersedes that sentence. The machinery check of A10 (RAW 3, LEGACY 29) tuned the HSMM over {2, 3, 4}; its HSMM tuning results are not valid under 5.4 and the check is to be repeated before it is cited for the HSMM.", "",
      "## 3. H1(c) event times", "",
      "- Each meeting's release time is read from its federalreserve.gov statement page (`For release at ...`). Pages are fetched once, cached with their sha256, and the result is stored in `section5/results/h1c_release_times.json` (URL, status, time, hash). Statement pages that say `For immediate release` or carry no parseable time, or cannot be fetched, are recorded as unavailable and those meetings are excluded from H1(c); no time is assumed.",
      "- The hit window is [t, t + 60 min] for the meeting's release time t (a confirmed alarm with availability in the window). The eligible-event list of A8 item 2 is regenerated with this restriction.", "",
      "## 4. Cold audit status", "",
      "- `COLD_AUDIT_STATUS.md` (hashed) lists every one of the 22 findings of `section5_cold_audit.md` with its status (resolved, disclosed, open) and the evidence. No finding is fixed by this amendment other than those named above.", "",
      "## Governs", "", "The four items, their unit tests, the protocol update (a new frozen integration; the previous frozen text is preserved as `SECTION5_PROTOCOL_v1_FROZEN_A10.md`) and the ledger rows. No run of models on market data, no test-segment scoring, no evaluation data."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
