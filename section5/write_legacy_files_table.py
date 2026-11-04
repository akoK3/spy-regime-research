#!/usr/bin/env python3
"""A14 (finding 22): PILOT_REPORT_LEGACY.md has no writer script and no file hash table and is a closed record. This writes PILOT_REPORT_LEGACY_FILES.md (+ sidecar): current sha256 of the files the report
relies on, and for the code modules the pilot imported, whether they differ from the version at the pilot commit 889d6cc. Refuses to overwrite. Facts only."""
import hashlib, datetime, subprocess
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; OUT = ROOT / "PILOT_REPORT_LEGACY_FILES.md"; assert not OUT.exists()
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest(); COMMIT = "889d6cc"
def at_commit(f):
    r = subprocess.run(["git", "show", f"{COMMIT}:{f}"], cwd=ROOT, capture_output=True)
    return hashlib.sha256(r.stdout).hexdigest() if r.returncode == 0 else None
R = "section5/results/"
files = ["PILOT_REPORT_LEGACY.md", "section5/s5_legacy_pilot.py", "section5/s5_legacy_resume_check.py", R + "legacy_build.json", R + "legacy_build_log.txt", R + "legacy_mem.json", R + "legacy_pilot_results_run_1793580880.json", R + "legacy_resume_check.json", R + "legacy_run1_log.txt", R + "legacy_run2_log.txt"]
mods = ["s5_lib", "s5_models", "s5_events", "s5_eval", "s5_sweep", "s5_fast", "s5_a6", "s5_a7", "s5_d2", "s5_d2_stable", "s5_pilot", "s5_legacy_pilot"]
L = ["# Files behind PILOT_REPORT_LEGACY.md", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC under `AMENDMENT_A14.md` (audit finding 22). `PILOT_REPORT_LEGACY.md` is a closed record and is not edited; its writer script is not recoverable and was not recreated. The hashes below are of the files as they are now.", "",
     "| File | SHA-256 now |", "|---|---|"]
for f in files:
    p = ROOT / f; L.append(f"| `{f}` | `{sha(p)}` |" if p.exists() else f"| `{f}` | (file not found) |")
L += ["", f"Code modules the pilot imported, compared with their version at the pilot commit `{COMMIT}`:", "", "| Module | Hash at pilot commit | Hash now | Changed since the pilot |", "|---|---|---|---|"]
for m in mods:
    f = f"section5/{m}.py"; a = at_commit(f); b = sha(ROOT / f); L.append(f"| `{f}` | `{a}` | `{b}` | {'yes' if a != b else 'no'} |")
L += ["", "The pilot results were computed with the pilot-commit versions; modules marked 'yes' were changed later (amendments A8 to A14), so rerunning the pilot script today does not reproduce them."]
OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("ok")
