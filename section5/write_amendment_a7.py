#!/usr/bin/env python3
"""Writes AMENDMENT_A7.md (+ sidecar). Verifies the cited hashes first. Refuses to overwrite."""
import hashlib, datetime
from pathlib import Path
import pandas as pd

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; OUT = ROOT / "AMENDMENT_A7.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = {}
for n in ("AMENDMENT_A6.md", "PILOT_REPORT_A6.md", "SECTION5_PROTOCOL.md"):
    assert (ROOT / n).with_suffix(".sha256").read_text().split()[0] == sha(ROOT / n), n; cited[n] = sha(ROOT / n)
cited["section5/results/a6_pilot_results.json"] = sha(HERE / "results" / "a6_pilot_results.json")
assert cited["section5/results/a6_pilot_results.json"] in (ROOT / "PILOT_REPORT_A6.md").read_text(encoding="utf-8"), "A6 pilot results hash not in the A6 pilot report"
now = datetime.datetime.now(datetime.timezone.utc); ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
L = ["# Amendment A7 to SECTION5_PROTOCOL.md (extends AMENDMENT_A6.md)", "", f"Dated {now.isoformat()} UTC ({ny} New York). Status: ADOPTED when committed with its hash sidecar; written before the machinery pilot it governs. Facts only.", "",
     "## Evidence cited (hashes recomputed and compared to the sidecars before this file was written)", "", "| Document | SHA-256 |", "|---|---|"] + [f"| `{k}` | `{v}` |" for k, v in cited.items()] + [
     "", "Reason: the machinery pilot under A6 (`PILOT_REPORT_A6.md`, findings 1, 2, 5) found that the strictest value of the A6 threshold grids (HMM/HSMM 0.9999; BOCPD drop m = 30) does not reach the fixed target of 0.2 confirmed alarms per session for the 3-feature models and for BOCPD (strictest-threshold rates 0.26-0.60 per session), that the H1(a) curve of those models starts above a null alarm rate of 0.1, and that A6 defines no wider range.", "",
     "## Change", "",
     "1. **Thresholds become continuous.** HMM and HSMM: the threshold theta is a real number on the log-odds scale of the alarm statistic. The alarm statistic is the probability mass that has left the old state, s = sum of P over the states other than the old state; the alarm condition of A6 item 1, P(old state) < 1 - thr for 3 consecutive real updates, is written as log(s) - log(P(old state)) > theta, with thr = 1 / (1 + exp(-theta)); theta = 0 is thr = 0.5, theta = 9.21 is thr = 0.9999. s is summed from the other states, not computed as 1 - P(old state), so that values near 1 keep their precision. BOCPD (run-length-drop alarm of A6 item 4): the drop size m is a real number >= 1 (the alarm needs a drop of at least m updates in the most likely run length; the observable effect is that of ceil(m)).",
     "2. **Section 6 thresholds by bisection.** On the REAL validation sessions of the fold (native sessions, no splices) the threshold is found by bisection so that the detector gives the fixed target of 0.2 confirmed alarms per session (A6 item 3): the alarm rate is evaluated at the bounds theta in [0, 30] (HMM/HSMM) and m in [1, 80] (BOCPD); if the rate at the strictest bound is above 0.2 the strictest bound is used and the fold is flagged; if the rate at the loosest bound is already <= 0.2 the loosest bound is used and the fold is flagged as below target; otherwise the interval is halved, keeping the end whose rate is <= 0.2 as the strict end, until its width is below 0.001 (theta) or 0.5 (m); the strict end is returned, so the validation rate is <= 0.2 and as close to it as the tolerance and the discreteness of the alarm counts allow. The A6 rule (highest rate not above 0.2) is unchanged; bisection replaces its enumeration over a grid. The realized frequency on the fold's test sessions is reported as in A6.",
     "3. **H1(a) curve over the same range.** The hit-rate versus alarm-rate curve of A6 item 2 is evaluated on a uniform sweep of the same continuous ranges: theta from 0 to 30 in steps of 0.25 (121 values), m from 1 to 80 in steps of 1 (80 values). The metric (partial area for null alarm rates 0-0.5 per session, divided by 0.5), the splices, the power by ratio and the statement that this is a sensitivity measure under simulated conditions are unchanged. The D4 run-2 rule (A6 item 6a, for the BOCPD secondary threshold) enumerates the same sweep values.",
     "4. **This widens the threshold range only.** No target (0.2 alarms per session; 10% null-session false-alarm share in the run-2 rule; the 0-0.5 window), no event rule (3 consecutive real updates, skip resets, 30-minute refractory, silent first 2 updates), no model, pool, split or metric changes. Thresholds are still chosen on validation data only and frozen before the test sessions are scored.", "",
     "## Governs", "", "The machinery pilot that follows (same design as the A6 pilot: RAW fold 3, fixed a-priori feature sets, no selection, no evaluation-period data, no protocol change based on the pilot's performance)."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.with_suffix(".sha256").read_text())
