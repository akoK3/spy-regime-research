#!/usr/bin/env python3
"""Writes AMENDMENT_A14_2.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE the code it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A14_2.md"; assert not OUT.exists()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); now = datetime.datetime.now(datetime.timezone.utc)
cited = ["SECTION5_PROTOCOL.md", "AMENDMENT_A14.md", "AMENDMENT_A14_1.md", "OPEN_AUDIT_FINDINGS.md", "section5/s5_models.py", "section5/s5_h1.py", "section5/s5_backend.py", "section5/s5_run.py", "section5/s5_tests_a14.py"]
L = ["# Amendment A14.2 to AMENDMENT_A14.md (Student-t start selection and flagged fits; decides the open choice of finding 19)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar; written before the code it governs. Decided by the user after A14 left the choice open. Facts only.", "",
     "## Evidence cited (hashes before this amendment's changes)", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## Rule", "",
      "- Why: 5.4 restarts a Student-t HMM start whose fit leaves a state under 1% occupancy; A14 recorded when that fails but left open which start to keep. Evidence that it is rare: 1 of 80 inner-train fits on RAW 3 and LEGACY 29 needed any restart and none was kept with a state under 1% (A14, `OPEN_AUDIT_FINDINGS.md` finding 19).",
      "- Among the starts of one fit, the kept fit is the one with the highest final log-likelihood among the starts whose kept attempt satisfies the 1% rule (every state at 1% or more). If no start satisfies the rule after its 10 attempts, the fit with the highest log-likelihood is kept and flagged (`kept_fit_occupancy_ok` = False). Before: the highest log-likelihood regardless of the rule.",
      "- Reporting: every machinery and run report states the number of Student-t fits that are flagged (kept fits failing the rule) and the number of starts that failed it.",
      "- Sensitivity excluding flagged fits (H1, Student-t HMM): the backend marks a fold's Student-t result as flagged if the kept feature model or the kept baseline model of that fold is flagged; `family_result` adds a third analysis, 'excluding_flagged_fits', computed on the confirmatory folds that are not flagged (same tests as the confirmatory analysis). The confirmatory analysis itself is not changed by flags. Other families have no flags.", "",
      "## Governs", "", "The start-selection change in `s5_models.py`, the flag plumbing in `s5_backend.py`, `s5_run.py` and `s5_h1.py`, unit tests, the protocol re-freeze (previous text preserved as `SECTION5_PROTOCOL_v5_FROZEN_A14_1.md`) and ledger rows. Finding 19 is then resolved. No evaluation data, no clean fold."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
