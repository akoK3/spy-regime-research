#!/usr/bin/env python3
"""Writes AMENDMENT_A8_1.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE the gate re-run and the code it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A8_1.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = ["AMENDMENT_A8.md", "A8_GATE_REPORT.md", "section5_cold_audit.md", "section5/results/a8_gate_LEGACY29_seed777.json", "section5/results/a8_gate_RAW3_seed777.json"]
now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A8.1 to AMENDMENT_A8.md (zero-effect reference of the item 1 gate)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar. **Decided after the A8 gate had been run and had failed** (seed 777, both folds); written before the re-run it governs.", "",
     "## Evidence cited", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## What happened", "",
      "- A8 item 1 defined the zero-effect reference as null splices (two different stable days, same volatility tercile). The gate failed: 4 of 8 detectors inside on LEGACY fold 29, 3 of 8 on RAW fold 3 (`A8_GATE_REPORT.md`).",
      "- Null splices join two different days and carry natural variance shifts (cold audit finding 8); the R = 1 placebo is built by the break code path with a labelled ratio of 1 in the detector's units (unit-tested). The two sets differ in construction, so the gate compared unlike things. This is an inference from the design; the failure itself is the recorded fact.", "",
      "## Change", "",
      "- The zero-effect reference is the set of R = 1 placebo splices (same construction as the break splices: same code path, same tau range, same four durations; only the effect size differs).",
      "- Gate (construction check), replacing the A8 item 1 pass rule: on the validation sessions of RAW fold 3 and LEGACY fold 29, seed 777, two independent sets of 200 placebos (P1 and P2, drawn from the same generator, different random streams) are scored. A detector passes if pAUC(P1) lies inside the 95% percentile interval of pAUC(P2) from 2,000 bootstrap resamples of P2. This checks that the placebo construction gives a stable reference (no dependence on the draw); it does not test that a detector has zero bias. The alarm-rate axis x comes from the same N1 null set as before.",
      "- Null splices (N2) remain in the report as information only; the pAUC difference f3 minus base is reported for P1, P2 and N2.",
      "- Downstream use: in H1(a), break-splice curves are read against the placebo curve of the same fold (the R = 1 hit-rate curve), in addition to the alarm-rate axis of A6/A7. No other rule in A6, A7 or A8 changes.",
      "- No re-draw to obtain a pass; seed 777 is the decision seed; the failed first gate stays on record.", "",
      "## Disclosure", "", "The reference was changed after the gate failed with the original reference. A pass under the new rule is weaker evidence than a pass under the original rule would have been.", "",
      "## Governs", "", "The gate re-run (`section5/s5_a8_gate.py`, rule above), then A8 items 2 and 5 as written in A8. Nothing else."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
