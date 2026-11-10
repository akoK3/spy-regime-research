#!/usr/bin/env python3
"""A26 rule 2b/2c: the amendment list of the 5.12 freeze document, produced outside the code-version closure.
Checked (A26 2c): the existing freeze path receives it without any closure change. s5_run.freeze_step(backend, summ, results_dir, amendments) passes `amendments` unchanged to
s5_freeze.build_freeze, which stores it as doc["amendments"] (JSON); the list below is passed as that argument. No module of s5_guard.result_modules changes.
Each entry: file name, status at freeze time (ADOPTED / DRAFT, from the "Status:" line), sha256 of the file on disk, sha256 in its sidecar, equal (bool).
freeze_ready() refuses (PermissionError) when: any listed amendment is missing, has no sidecar, differs from its sidecar or is a DRAFT (A26 2b: the freeze and the 5.13 run
depend on all of them); the A27 result does not exist (A27 rule 3d: the freeze is not written while A27 is unfinished); or the A23 result does not exist.
Usage: s5_amendment_manifest.py [--check]  prints the manifest; --check also runs freeze_ready() (exit 0 ready / 3 not ready). Writes nothing; never writes a freeze or a lock."""
import sys, re, json, hashlib
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
AMENDMENTS = ("A21", "A22", "A23", "A24", "A25", "A26", "A27", "A28")
REQUIRED_RESULTS = {"A27": HERE / "results" / "a27" / "confirm_count.json", "A23": HERE / "results" / "a23" / "a23_results.json"}
STATUS = re.compile(r"^.*?Status:\s*(ADOPTED|DRAFT)\b", re.M)


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def entry(name, root=ROOT):
    p = root / f"AMENDMENT_{name}.md"; s = root / f"AMENDMENT_{name}.sha256"
    if not p.exists(): return dict(amendment=name, file=p.name, present=False)
    m = STATUS.search(p.read_text(encoding="utf-8")); disk = sha(p); side = s.read_text(encoding="ascii").split()[0] if s.exists() else None
    return dict(amendment=name, file=p.name, present=True, status=m.group(1) if m else "UNKNOWN", sha256=disk, sidecar_sha256=side, sidecar_matches=(side == disk))


def manifest(names=AMENDMENTS, root=ROOT): return [entry(n, root) for n in names]


def freeze_ready(names=AMENDMENTS, root=ROOT, required=None):
    """The manifest to pass to s5_run.freeze_step as `amendments`; PermissionError listing every reason if the freeze may not be written."""
    man = manifest(names, root); bad = []
    for e in man:
        if not e["present"]: bad.append(f"{e['file']} missing")
        elif e["sidecar_sha256"] is None: bad.append(f"{e['file']} has no sidecar")
        elif not e["sidecar_matches"]: bad.append(f"{e['file']} differs from its sidecar")
        elif e["status"] != "ADOPTED": bad.append(f"{e['file']} is {e['status']}")
    for k, p in (REQUIRED_RESULTS if required is None else required).items():
        if not Path(p).exists(): bad.append(f"{k} result {Path(p).name} does not exist")
    if bad: raise PermissionError("freeze not ready: " + "; ".join(bad))
    return man


def main():
    print(json.dumps(manifest(), indent=1))
    if "--check" in sys.argv[1:]:
        try: freeze_ready(); print("freeze_ready: yes"); return 0
        except PermissionError as e: print(e); return 3
    return 0


if __name__ == "__main__": sys.exit(main())
