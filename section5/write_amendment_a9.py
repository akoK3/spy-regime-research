#!/usr/bin/env python3
"""Writes AMENDMENT_A9.md (+ sidecar). Facts only. Refuses to overwrite. Written BEFORE the code changes it governs."""
import hashlib, datetime
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "AMENDMENT_A9.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
cited = ["SECTION5_PROTOCOL.md", "AMENDMENT_A6.md", "AMENDMENT_A8.md", "AMENDMENT_A8_4.md", "section5/s5_h1.py", "section5/s5_freeze.py", "section5/s5_select.py", "section5/s5_stats.py", "section5/s5_tests_build.py"]
now = datetime.datetime.now(datetime.timezone.utc)
L = ["# Amendment A9 to SECTION5_PROTOCOL.md (Holm families, H2 simplicity order, confirmed implementation choices)", "",
     f"Dated {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York). Status: ADOPTED when committed with its hash sidecar; written before the code changes it governs. Facts only.", "",
     "## Evidence cited (hashes of the files before this amendment's changes)", "", "| Document | SHA-256 |", "|---|---|"]
for f in cited: L.append(f"| `{f}` | `{sha(ROOT / f)}` |")
L += ["", "## 1. Holm across three H1 families", "",
      "- A6 item 4: BOCPD is secondary, outside H1 and outside its Holm family; Holm in 5.11 runs across three families (Gaussian HMM, Student-t HMM, HSMM). `s5_h1.py` (code written after A8.4) ran Holm over four families, which contradicts A6 item 4.",
      "- Now: `s5_h1.h1_decision` applies Holm to the three H1 families only; BOCPD is scored and reported with its intersection-union p-value, unadjusted, as secondary (A6 item 4). `FAMILIES` is split into `H1_FAMILIES` (three) and `SECONDARY_FAMILIES` (BOCPD). The unit test `test_h1_decision_holm_over_families` is corrected to three families.", "",
      "## 2. H2 simplicity order", "",
      "- 5.12: the H2 primary detector is the family passing H1 with the lowest median validation QLIKE; ties go to the simpler model. Order fixed: Gaussian HMM < Student-t HMM < HSMM (simplest first). BOCPD is not an H1 family and cannot be the H2 primary detector. This replaces the order chosen in `s5_freeze.py` (Gaussian HMM, BOCPD, Student-t HMM, HSMM), which was an unconfirmed implementation choice.", "",
      "## 3. Implementation choices confirmed", "",
      "- The block-bootstrap p-value (blocks of 3 consecutive folds, centred, one-sided, add-one correction) is the primary p-value of each H1 component; Wilcoxon and sign consistency are reported beside it (5.9).",
      "- The final-setup feature count (5.8) is the median across folds, rounded half up.", "",
      "## 4. Code under this amendment", "",
      "- `section5/s5_run.py`: the orchestration of a full run (per-fold selection, H1(a)/(b) scoring, statistics, freeze, guarded refit) against an injected backend, with code-version-keyed checkpoints (audit finding 11) and the confirmatory fold exclusions of A8 item 2.",
      "- `section5/s5_dry_run.py`: a dry run on synthetic data only (synthetic backend with known effects, temporary directories). No market data, no test or evaluation data.",
      "- A data backend that connects the orchestration to the fitted models, splices and QLIKE series is not part of this amendment; it needs its own dated amendment before any run on data.", "",
      "## Governs", "", "The three changes above and the orchestration code with its synthetic dry run. No run on market data, test segments or evaluation periods."]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("written", sha(OUT))
