#!/usr/bin/env python3
"""Adopts AMENDMENT_A31 (A31 rule 5b) after the rule 4 synthetic checks pass: user pre-approval of 2026-11-10 ("A31 is pre-approved per the spec below"). Refuses unless
section6/results/synth_check_TAG.json exists with passed = true and A31 is a DRAFT. Changes only the status line, writes the sidecar, adds a ledger row (WHY / EVIDENCE),
runs the ledger tests. Usage: s6_adopt_a31.py TAG"""
import sys, re, json, hashlib, datetime, subprocess
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; A = ROOT / "AMENDMENT_A31.md"; SIDE = ROOT / "AMENDMENT_A31.sha256"


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    tag = sys.argv[1]; chk = HERE / "results" / f"synth_check_{tag}.json"
    if not chk.exists() or not json.loads(chk.read_text(encoding="utf-8")).get("passed"): print(f"refused: {chk.name} missing or not passed"); return 3
    t = A.read_text(encoding="utf-8"); m = re.search(r"Status: DRAFT \(revised [^)]*\), awaiting adoption\.", t)
    if not m or SIDE.exists(): print("refused: A31 is not the expected DRAFT or a sidecar exists"); return 3
    draft_sha = sha(A); now = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    new = (f"Status: ADOPTED {now} (user pre-approval 2026-11-10: \"A31 is pre-approved per the spec below\"; rule 4 synthetic checks passed, "
           f"section6/results/{chk.name} sha256 {sha(chk)[:16]}...; the draft, sha256 {draft_sha[:16]}..., is unchanged apart from this status line).")
    A.write_text(t.replace(m.group(0), new), encoding="utf-8"); SIDE.write_text(f"{sha(A)}  {A.name}\n", encoding="ascii")
    s5 = ROOT / "section5"
    r = subprocess.run([sys.executable, str(s5 / "s5_ledger.py"), "add", "AMENDMENT_A31.md", "Amendment A31 (ADOPTED)",
                        "Placebo exclusion by past alarms only; H4a = every calm-state streak start, label afterward, gap-0 placebos; placebo-filter null control (filtered vs fully unfiltered random times, H3 next-day, two-sided 95% week-block interval)",
                        "User pre-approval 2026-11-10 of the specification; rule 4 synthetic checks passed", f"section6/results/{chk.name} {sha(chk)}; draft sha256 {draft_sha}"], cwd=s5, capture_output=True, text=True)
    print(r.stdout, r.stderr)
    if r.returncode != 0: return 1
    r = subprocess.run([sys.executable, str(s5 / "s5_tests_ledger.py")], cwd=s5, capture_output=True, text=True); print(r.stdout[-300:], r.stderr[-300:]); return r.returncode


if __name__ == "__main__": sys.exit(main())
