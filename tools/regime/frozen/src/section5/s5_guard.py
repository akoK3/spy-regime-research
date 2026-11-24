#!/usr/bin/env python3
"""A15/A16 guards of the main run. No market data. Frozen protocol (A15 rule 5b), canonical contamination list (A16 rule 2), result-module code version (A15 rule 4, A16 rule 4),
completion record (A16 rule 1), era-calibration lock (A16 rule 5). Paths are fixed module constants; tests patch them, callers cannot pass others."""
import ast, re, json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
PROTOCOL = ROOT / "SECTION5_PROTOCOL.md"
CONTAMINATION = HERE / "results" / "contamination_list.json"
LOCK = HERE / "results" / "ERA_CALIBRATION.lock"
VERSION_SCHEME = "A15"
RESULT_ROOTS = ["s5_run.py", "s5_backend.py", "s5_era_threshold.py", "s5_main.py"]
COMPLETION = "run_complete.json"
MAIN_FOLDS = [f"LEGACY|{i}" for i in range(30)] + [f"RAW|{i}" for i in range(4)]
STATED = re.compile(r"contamination list sha256 `([0-9a-f]{64})`")


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def _side(p):
    s = Path(p).with_suffix(".sha256"); return s.read_text().split()[0] if s.exists() else None


def write_side(p): Path(p).with_suffix(".sha256").write_text(f"{sha(p)}  {Path(p).name}\n", encoding="ascii")


# ---------- protocol (A15 rule 5b)
def frozen_protocol_hash():
    """sha256 of SECTION5_PROTOCOL.md if its sidecar matches and the text says FROZEN; else PermissionError."""
    h = sha(PROTOCOL)
    if _side(PROTOCOL) != h or "**Status: FROZEN**" not in PROTOCOL.read_text(encoding="utf-8"): raise PermissionError("SECTION5_PROTOCOL.md is not FROZEN with a matching sidecar")
    return h


def verify_frozen_protocol(token):
    h = frozen_protocol_hash()
    if token != h: raise PermissionError("the token is not the sha256 of the FROZEN SECTION5_PROTOCOL.md (A15 rule 5b)")
    return h


# ---------- contamination list (A16 rule 2)
def canonical_contamination():
    """(path, sha256) of the canonical list after checking it against its sidecar and against the hash stated in protocol 5.14; else RuntimeError."""
    h = sha(CONTAMINATION); m = STATED.search(PROTOCOL.read_text(encoding="utf-8"))
    if _side(CONTAMINATION) != h: raise RuntimeError("contamination list does not match its sidecar (A16 rule 2)")
    if not m or m.group(1) != h: raise RuntimeError("contamination list hash differs from the one stated in protocol 5.14 (A16 rule 2)")
    return CONTAMINATION, h


def contamination():
    p, h = canonical_contamination(); return json.loads(p.read_text(encoding="utf-8")), h


def excluded_folds():
    j, h = contamination(); return {f"{x['era']}|{x['fold']}" for x in j["folds"] if x["excluded"]}, h


# ---------- code version (A15 rule 4; no override, A16 rule 4)
def _local(name, dirs):
    for dd in dirs:
        p = dd / (name.replace(".", "/") + ".py")
        if p.exists(): return p
    return None


def result_modules(roots=RESULT_ROOTS, base=HERE):
    """Transitive closure of local imports (section5/, repository root, Section 4 source folder) from `roots`; paths relative to the repository root, sorted."""
    dirs = [base, base.parent, base.parent / "section431_step3_verification" / "prototype_sources"]; seen = set(); todo = [base / r for r in roots if (base / r).exists()]
    while todo:
        p = todo.pop()
        if p in seen: continue
        seen.add(p)
        for node in ast.walk(ast.parse(p.read_text(encoding="utf-8"))):
            names = [a.name for a in node.names] if isinstance(node, ast.Import) else ([node.module] if isinstance(node, ast.ImportFrom) and node.module and not node.level else [])
            for n in names:
                q = _local(n, dirs)
                if q is not None and q not in seen: todo.append(q)
    return sorted(str(p.relative_to(base.parent)).replace("\\", "/") for p in seen)


def code_version(base=HERE):
    h = hashlib.sha256(); h.update(VERSION_SCHEME.encode())
    for f in result_modules(base=base):
        p = base.parent / f; h.update(f.encode()); h.update(hashlib.sha256(p.read_bytes()).digest())
    return h.hexdigest()[:16]


def checkpoint_version(code_v, protocol_h):
    """A16 rule 6: checkpoints depend on the code and on the verified protocol."""
    return hashlib.sha256(f"{code_v}|{protocol_h}".encode()).hexdigest()[:16]


# ---------- completion record (A16 rule 1)
def write_completion(run_dir, **rec):
    p = Path(run_dir) / COMPLETION; rec = dict(kind="section5_run_complete", created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **rec)
    p.write_text(json.dumps(rec, indent=1, default=float), encoding="utf-8"); write_side(p); return p


def verify_completion(path, require_main=True):
    """The record's sidecar matches; its protocol, contamination and code hashes equal the current verified ones; with require_main, backend 'main' and all 34 folds."""
    p = Path(path)
    if not p.exists() or _side(p) != sha(p): raise PermissionError(f"no valid completion record at {p} (A16 rule 1)")
    r = json.loads(p.read_text(encoding="utf-8")); _, ch = canonical_contamination()
    if r.get("protocol_sha256") != frozen_protocol_hash(): raise PermissionError("completion record: protocol hash differs from the FROZEN protocol")
    if r.get("contamination_sha256") != ch: raise PermissionError("completion record: contamination list hash differs from the canonical list")
    if r.get("code_version") != code_version(): raise PermissionError("completion record: code version differs from the current code")
    if require_main and (r.get("backend") != "main" or r.get("folds") != MAIN_FOLDS): raise PermissionError("completion record is not a main run over all 34 folds")
    return r


# ---------- era-calibration lock (A16 rule 5)
def write_lock(**info):
    LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LOCK, "a", encoding="utf-8") as f: f.write(json.dumps(dict(time_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), **info)) + "\n")


def check_unlocked(what="selection or scoring"):
    if LOCK.exists(): raise PermissionError(f"{what} refused: era calibration has run ({LOCK.name} exists; A16 rule 5)")
