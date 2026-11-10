#!/usr/bin/env python3
"""AMENDMENT_A28 rule 6e: fingerprint of the Section 6 code before the joint evaluation. sha256 of every section6/*.py, of the Section 5 helpers Section 6 uses
(s5_eval_loader.py, s5_amendment_manifest.py, s5_break_export.py) and the result-module code version (must be a0323ed24d68e896). Written once with a sidecar; never
overwritten (a later change is a deviation, reported with its reason: verify() lists the files that differ).
Usage: s6_fingerprint.py write | verify. Not run before the user says so (it precedes the joint evaluation only)."""
import sys, json, hashlib, datetime
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; sys.path.insert(0, str(ROOT / "section5"))
FP = HERE / "results" / "s6_fingerprint.json"; HELPERS = ("s5_eval_loader.py", "s5_amendment_manifest.py", "s5_break_export.py"); CODE_VERSION = "a0323ed24d68e896"


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def current():
    import s5_guard as G
    files = {f"section6/{p.name}": sha(p) for p in sorted(HERE.glob("*.py"))} | {f"section5/{n}": sha(ROOT / "section5" / n) for n in HELPERS}
    return dict(files=files, code_version=G.code_version())


def write():
    if FP.exists(): raise FileExistsError("fingerprint exists; it is never overwritten (A28 rule 6e)")
    cur = current()
    if cur["code_version"] != CODE_VERSION: raise PermissionError(f"code version {cur['code_version']} != {CODE_VERSION}")
    FP.parent.mkdir(parents=True, exist_ok=True); FP.write_text(json.dumps(dict(cur, created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat()), indent=1), encoding="utf-8")
    FP.with_suffix(".sha256").write_text(f"{sha(FP)}  {FP.name}\n", encoding="ascii"); return FP


def verify():
    if FP.with_suffix(".sha256").read_text().split()[0] != sha(FP): raise RuntimeError("fingerprint differs from its sidecar")
    old = json.loads(FP.read_text(encoding="utf-8")); cur = current()
    return dict(changed=sorted(k for k in set(old["files"]) | set(cur["files"]) if old["files"].get(k) != cur["files"].get(k)), code_version_same=old["code_version"] == cur["code_version"])


if __name__ == "__main__":
    print(write() if sys.argv[1:2] == ["write"] else json.dumps(verify(), indent=1))
