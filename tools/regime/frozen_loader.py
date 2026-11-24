"""Verification and loading of the vendored frozen detector (RAW Gaussian HMM, research freeze of 2026-11-12).

verify() must pass before anything is unpickled. It checks, against constants pinned in this file (so an edited
VENDOR_LOCK.json cannot make a tampered copy pass):
  * every vendored file against VENDOR_LOCK.json, and the model / manifest / freeze / evaluation hashes against the pins;
  * the manifest and freeze sidecars; the freeze's frozen-model record; the freeze's RAW Gaussian HMM threshold and setup;
  * code_version recomputed from the 25 vendored closure files == the freeze's code_version (a0323ed24d68e896).

Research code is used, not rewritten: s5_models and s5_events are imported from the vendored copies; the few functions
needed from modules that have import-time side effects (s5_lib, s5_fast, step11, step3, s5_break_export) are taken
from the vendored file text by name (ast), so the code that runs is the hashed text.
"""
import ast, sys, json, pickle, hashlib, importlib.util, types
from pathlib import Path

import numpy as np

FROZEN = Path(__file__).resolve().parent / "frozen"
SRC = FROZEN / "src"
LOCK = FROZEN / "VENDOR_LOCK.json"

# ---- pins (from the research freeze; see regime/FORWARD_TEST_PREREGISTRATION.md)
MODEL_REL = "src/section5/results/frozen_models/RAW_gaussian_hmm.pkl"
MODEL_SHA256 = "b0848a4bd67497e9810fe72f45529ef41435aef120c9aa94df8fedfe2779750a"
MANIFEST_SHA256 = "edb78798544a8896c88f5a6b02857591d96f6764ed0d7f498685cbdbc0ac06dd"
FREEZE_SHA256 = "846c1aaafaf1cb02911bc680c0b197f97e17b00386695fc0f6eb0b26b02e3a94"
EVALUATION_RAW_SHA256 = "1159e8aad0ff022fe1e0544ae6dc12bf1720f50960955cab4061698644054051"
CODE_VERSION = "a0323ed24d68e896"
THRESHOLD = 16.98211669921875
FEATURES = ["rv10_partial90__sadj"]
K = 4
VERSION_SCHEME = "A15"


class IntegrityError(RuntimeError):
    pass


def _sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def code_version(root, files):
    """section5/s5_guard.code_version, same algorithm, over the vendored copies."""
    h = hashlib.sha256(); h.update(VERSION_SCHEME.encode())
    for f in sorted(files):
        h.update(f.encode()); h.update(hashlib.sha256((Path(root) / f).read_bytes()).digest())
    return h.hexdigest()[:16]


def verify(frozen=FROZEN):
    """Raise IntegrityError on any mismatch; return a dict of the verified hashes."""
    frozen = Path(frozen); src = frozen / "src"
    if not (frozen / "VENDOR_LOCK.json").exists(): raise IntegrityError("VENDOR_LOCK.json missing")
    lock = json.loads((frozen / "VENDOR_LOCK.json").read_text(encoding="utf-8"))
    bad = [rel for rel, h in lock["files"].items() if not (frozen / rel).exists() or _sha(frozen / rel) != h]
    if bad: raise IntegrityError(f"vendored files differ from VENDOR_LOCK.json: {bad}")
    pins = {MODEL_REL: MODEL_SHA256, "src/section5/results/frozen_models/manifest.json": MANIFEST_SHA256,
            "src/section5/results/section5_freeze.json": FREEZE_SHA256, "src/section5/results/evaluation_RAW.json": EVALUATION_RAW_SHA256}
    for rel, h in pins.items():
        if _sha(frozen / rel) != h: raise IntegrityError(f"{rel} differs from the pinned SHA-256")
    res = src / "section5" / "results"
    for name, side in (("frozen_models/manifest.json", "frozen_models/manifest.sha256"), ("section5_freeze.json", "section5_freeze.sha256"), ("evaluation_RAW.json", "evaluation_RAW.sha256")):
        if (res / side).read_text().split()[0] != _sha(res / name): raise IntegrityError(f"{name} differs from its sidecar")
    man = json.loads((res / "frozen_models/manifest.json").read_text(encoding="utf-8"))
    if man["files"].get("RAW_gaussian_hmm.pkl") != MODEL_SHA256: raise IntegrityError("manifest does not list the pinned model hash")
    fz = json.loads((res / "section5_freeze.json").read_text(encoding="utf-8"))
    rec = fz["input_hashes"]["frozen_models"]
    if rec["manifest_sha256"] != MANIFEST_SHA256 or rec["files"]["RAW_gaussian_hmm.pkl"] != MODEL_SHA256: raise IntegrityError("freeze frozen-model record differs")
    if fz["h2_primary_detector"] != "gaussian_hmm": raise IntegrityError("freeze primary detector is not gaussian_hmm")
    if float(fz["thresholds"]["RAW"]["gaussian_hmm"]["threshold"]) != THRESHOLD: raise IntegrityError("freeze RAW gaussian_hmm threshold differs from the pin")
    s = fz["setups"]["RAW"]["gaussian_hmm"]
    if s["features"] != FEATURES or s["params"] != {"K": K}: raise IntegrityError("freeze RAW gaussian_hmm setup differs from the pin")
    cv = code_version(src, lock["closure"])
    if cv != CODE_VERSION or fz["code_version"] != CODE_VERSION: raise IntegrityError(f"code_version {cv} (freeze {fz['code_version']}) != {CODE_VERSION}")
    return dict(status="verified", model_sha256=MODEL_SHA256, manifest_sha256=MANIFEST_SHA256, freeze_sha256=FREEZE_SHA256,
                code_version=cv, threshold=THRESHOLD, vendor_lock_sha256=_sha(frozen / "VENDOR_LOCK.json"),
                research_commit=lock.get("research_commit"), n_files=len(lock["files"]))


# ---- code from the vendored text
def _import_file(name, path):
    spec = importlib.util.spec_from_file_location(name, path); mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod; spec.loader.exec_module(mod); return mod


def extract(path, names, module_name, env=None):
    """New module holding the top-level definitions `names` (functions, classes, simple assignments) taken verbatim
    from the file text at `path`. Imports are provided through `env`; the module's own import-time code never runs."""
    text = Path(path).read_text(encoding="utf-8"); tree = ast.parse(text)
    mod = types.ModuleType(module_name); mod.__dict__.update(env or {}); mod.__file__ = str(path)
    want = set(names); found = set(); body = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)) and node.name in want: body.append(node); found.add(node.name)
        elif isinstance(node, ast.Assign):
            tg = [t.id for t in node.targets if isinstance(t, ast.Name)] + [e.id for t in node.targets if isinstance(t, ast.Tuple) for e in t.elts if isinstance(e, ast.Name)]
            if want & set(tg): body.append(node); found.update(want & set(tg))
    if want - found: raise IntegrityError(f"{Path(path).name}: definitions not found {sorted(want - found)}")
    exec(compile(ast.Module(body=body, type_ignores=[]), str(path), "exec"), mod.__dict__)
    return mod


_MODS = {}


def modules():
    """The research functions used by the engine, from the verified vendored files (call verify() first)."""
    if _MODS: return _MODS
    import pandas as pd
    s5 = SRC / "section5"
    M = _import_file("s5_models", s5 / "s5_models.py")                     # numpy/scipy only, no side effects
    E = _import_file("s5_events", s5 / "s5_events.py")                     # numpy only
    C = _import_file("section4_3_1_candidates", SRC / "section431_step3_verification/prototype_sources/section4_3_1_candidates.py")
    base = dict(np=np, pd=pd, Path=Path)
    L = extract(s5 / "s5_lib.py", ["GRID", "FIRST_SLOT", "HORIZON", "QLIKE_FLOOR", "RET_NAME", "WINSOR", "Prep", "grid_slots", "session_grid", "build_sequence", "pad"], "s5_lib", base)
    sys.modules["s5_lib"] = L                                                # pickle resolves s5_lib.Prep here
    F = extract(s5 / "s5_fast.py", ["ret5_scale", "deseason"], "s5_fast_vendored", base)
    q = extract(SRC / "step8_sections_4_3_4_to_4_3_9.py", ["SLOTS"], "step8_vendored", base)
    P = extract(SRC / "step11_a4_rerun_4_3_4_7_8.py", ["WINDOW", "MIN_COUNT", "adjust"], "step11_vendored", dict(base, q=q))
    S3 = extract(SRC / "step3_all_in_one.py", ["OHLC_KEYS", "load_ohlc"], "step3_vendored", dict(base, selected_csv=C.selected_csv, ns=C.ns))
    BX = extract(s5 / "s5_break_export.py", ["WARM", "RUN", "REF_MIN", "MIN", "runs_old_state"], "s5_break_export_vendored", base)
    _MODS.update(models=M, events=E, candidates=C, lib=L, fast=F, step11=P, step3=S3, breaks=BX)
    return _MODS


class _RestrictedUnpickler(pickle.Unpickler):
    ALLOWED = {("s5_models", "GaussianHMM"), ("s5_lib", "Prep"), ("numpy._core.multiarray", "_reconstruct"), ("numpy._core.multiarray", "scalar"),
               ("numpy", "ndarray"), ("numpy", "dtype"), ("numpy.core.multiarray", "_reconstruct"), ("numpy.core.multiarray", "scalar"), ("builtins", "set")}

    def find_class(self, module, name):
        if (module, name) not in self.ALLOWED: raise IntegrityError(f"pickle references a non-allowed global {module}.{name}")
        return super().find_class(module, name)


_BUNDLE = {}


def load_bundle(frozen=FROZEN):
    """verify(), then unpickle the frozen bundle with a restricted unpickler. Returns (bundle, verification)."""
    if "b" in _BUNDLE and Path(frozen) == FROZEN: return _BUNDLE["b"], _BUNDLE["v"]
    v = verify(frozen); modules()
    data = (Path(frozen) / MODEL_REL).read_bytes()
    if hashlib.sha256(data).hexdigest() != MODEL_SHA256: raise IntegrityError("model bytes changed after verification")
    import io
    b = _RestrictedUnpickler(io.BytesIO(data)).load()
    if (b["era"], b["family"], list(b["features"]), dict(b["params"])) != ("RAW", "gaussian_hmm", FEATURES, {"K": K}): raise IntegrityError("bundle setup differs from the pins")
    if abs(float(b["thresholds"]["feature_recomputed"]) - THRESHOLD) > 1e-9: raise IntegrityError("bundle threshold differs from the freeze")
    if Path(frozen) == FROZEN: _BUNDLE.update(b=b, v=v)
    return b, v
