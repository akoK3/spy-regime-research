#!/usr/bin/env python3
"""Writes AMENDMENT_A8_2.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE the gate re-run and the code it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A8_2.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = ["AMENDMENT_A8.md", "AMENDMENT_A8_1.md", "A8_1_GATE_REPORT.md", "D6_REPORT.md", "section5/results/a8_1_gate_LEGACY29_seed777.json", "section5/results/a8_1_gate_RAW3_seed777.json"]
now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A8.2 to AMENDMENT_A8.md and AMENDMENT_A8_1.md (gate bootstrap unit; status of D6)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar. Both changes were decided after the A8.1 gate result (RAW 3 passed 8 of 8, LEGACY 29 passed 3 of 8); written before the re-run they govern.", "",
     "## Evidence cited", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## 1. Gate bootstrap resamples stable days", "",
      "- A8.1 resampled the 200 placebo splices of P2. The splices are drawn from few stable validation days (7 on LEGACY 29, 16 on RAW 3), so they are not independent; the interval was too narrow (inference). Decided after the LEGACY 29 failure.",
      "- Now: each bootstrap replicate draws n stable validation days with replacement (n = number of stable days of the fold) and weights each P2 splice by the number of times its session A was drawn; pAUC is computed from the weighted hit curve. 2,000 replicates, 95% percentile interval. Pass rule, placebo sets, seed (777) and folds unchanged from A8.1. The splice-level result is reported for information.",
      "- If the gate fails on either fold: stop and report; nothing else changes.", "",
      "## 2. D6 is descriptive, not contamination", "",
      "- D6 ran no detector, no model and no performance measure; it computed SPY variance ratios around dates. Item 2 of A8 is amended: D6 dates (FOMC statements and the three listed shocks) are not entered in the contamination list. The registry marks D6 scripts as DESCRIPTIVE. All other registry entries (pilots, diagnostics D2-D5, audit runs, gate) stay.",
      "- Disclosure: the H1(c) events (FOMC announcements) were chosen knowing from D6 that SPY variance around FOMC statements is large (median ratio 8.6 against 0.91 at random 14:00 moments). H1(c) is secondary; the choice of event type is not independent of that observation.", "",
      "## Governs", "", "The gate re-run on both folds. If it passes: A8 item 2 (contamination list, fold exclusions) and, for item 5, only the list of eligible FOMC events per fold (uncontaminated test segment, post-embargo, 390 bars). No detector is scored on test-segment data. If it fails: nothing further."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
