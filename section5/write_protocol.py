#!/usr/bin/env python3
"""Writes SECTION5_PROTOCOL.md (verbatim user text 5.0-5.13) with date and input hashes; sidecar SECTION5_PROTOCOL.sha256. Refuses to overwrite."""
import hashlib, re, datetime
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
R = ROOT / "section431_step3_all_in_one_results"
SRC = ROOT / "_s5_raw.txt"
OUT = ROOT / "SECTION5_PROTOCOL.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
text = SRC.read_text(encoding="utf-8")
body = [l for l in text.splitlines() if re.match(r"5\.\d+ ", l)]
assert [l.split()[0] for l in body] == [f"5.{i}" for i in range(14)], "expected sections 5.0-5.13"
now = datetime.datetime.now(datetime.timezone.utc)
ny = pd.Timestamp(now).tz_convert("America/New_York").isoformat()
inputs = ["a4_sec4_3_9_frozen_matrix_v2.csv", "a4_sec4_3_9_matrix_primary_view_v2.csv", "a4_sec4_3_9_matrix_sensitivity_view_v2.csv",
          "a4_development_nested_folds_TRAIN.csv", "a4_folds_check.json", "a4_lm_threshold_calibration.json"]
L = ["# Section 5 protocol", "", "**Status: DRAFT pending pilot**", "",
     f"Written {now.isoformat()} UTC ({ny} New York). Governing document for the Section 5 pipeline and pilot; written before any Section 5 code was run.",
     "Changes: dated, hashed amendments only. Source: text supplied by the user, reproduced unchanged below.", "",
     "## Cited inputs (SHA-256)", "", "| File | SHA-256 |", "|---|---|"]
L += [f"| `section431_step3_all_in_one_results/{f}` | `{sha(R / f)}` |" for f in inputs]
L += ["", "Feature matrix: 4.3.9 matrix v2 = `a4_sec4_3_9_frozen_matrix_v2.csv` (hash above).", "", "## Protocol text (verbatim)", ""]
L += [l + "\n" for l in body]
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8"))
OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.read_text(encoding="utf-8")[:1500]); print(OUT.with_suffix(".sha256").read_text())
