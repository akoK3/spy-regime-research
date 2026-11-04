#!/usr/bin/env python3
"""Writes AMENDMENT_A14_1.md (+ sidecar). Facts only. Refuses to overwrite."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A14_1.md"; assert not OUT.exists()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A14.1 to AMENDMENT_A14.md (one more undocumented guard)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar. Facts only.", "",
     "| Document | SHA-256 |", "|---|---|", f"| `AMENDMENT_A14.md` | `{sha(ROOT / 'AMENDMENT_A14.md')}` |", f"| `section5/s5_models.py` (before this change) | `{sha(ROOT / 'section5/s5_models.py')}` |", "",
     "- Found while testing A14: the three EM M-steps divide by state weights with a numerical guard (`weight + 1e-12`: Gaussian HMM and Student-t HMM state weights, Student-t scale weights, HSMM state weights) and the Student-t occupancy is computed with `max(total weight, 1e-12)`. A14 listed the 1e-12 added to initial-state and transition counts but not these denominator guards.",
     "- Documented now as `WEIGHT_GUARD = 1e-12` in `s5_models.py`, used at all five places; values and results unchanged; a unit test fixes the value and that no bare 1e-12 remains outside the named constants.", "",
     "## Governs", "", "The constant and its test only."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
