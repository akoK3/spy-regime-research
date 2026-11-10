#!/usr/bin/env python3
"""Cold audit 2 finding 14 for Section 5, outside the code-version closure (FABLE_AUDIT L6, 2026-11-10). s5_lib / s5_fast load cache/{era}_features.npz and
cache/{era}_bases.npz by column name only, and they are in the closure, so they are not changed. This script stamps each cache file with the finding 14 key:
sha256 of the file, plus key = sha256(feature-code hash | panel hash | ETF-file hash), where the feature-code hash covers the modules that compute the cached columns and
the input hashes are those of the files the loader opens. s5_preflight_data_hashes.py (finding 17, run by every runner and by s5_eval_loader.load_eval) checks the stamp:
  - a cache file whose bytes differ from the stamp: MISMATCH;
  - feature code or panel changed while the cache did not: the key differs: MISMATCH (stale cache: delete the npz, let the loader rebuild it, stamp again).
The stamp is written once (2026-11-10, after MR2, A23, A25, A27). No hash of these caches was recorded before; the stamp records their state from now on, under
code version a0323ed24d68e896 and the panel hashes the frozen 4.3.0 protocol records (preflight group A).
Usage: s5_cache_stamp.py            write results/cache_stamp.json (+ .sha256); refuses if it exists
       s5_cache_stamp.py --check    print the check rows; exit 0 / 1 (differs) / 2 (missing)"""
import sys, re, json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; CACHE = HERE / "cache"; STAMP = HERE / "results" / "cache_stamp.json"
FEATURE_CODE = ("step3_all_in_one.py", "step8_sections_4_3_4_to_4_3_9.py", "step11_a4_rerun_4_3_4_7_8.py", "section431_step3_verification/prototype_sources/section431_additions.py",
                "section431_step3_verification/prototype_sources/section4_3_1_candidates.py", "section5/s5_lib.py", "section5/s5_fast.py", "section5/s5_d2.py", "section5/s5_d2_stable.py")
FILES = {era: (f"{era}_features.npz", f"{era}_bases.npz") for era in ("LEGACY", "RAW")}


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def inputs(era):
    """The files the Section 5 loader opens for `era`: the CONFIG panel and ETF relative paths in step3_all_in_one.py (read as text, as the finding-17 preflight does),
    resolved like step3_all_in_one.file_path (ROOT/rel, else ROOT/<file name>); None if one is missing."""
    t = (ROOT / "step3_all_in_one.py").read_text(encoding="utf-8")
    m = {k: (a, b) for k, a, b in re.findall(r'"(RAW|LEGACY)":\("[^"]*","[^"]*","([^"]+)","([^"]+)"\)', t)}
    out = []
    for rel in m.get(era, ()):
        p = ROOT / rel; p = p if p.exists() else ROOT / Path(rel).name
        if not p.exists(): return None
        out.append(p)
    return out or None


def code_hash(): return hashlib.sha256("|".join(f"{f}:{sha(ROOT / f)}" for f in FEATURE_CODE).encode()).hexdigest()


def key(era):
    """Finding 14 key: sha256(feature-code hash | panel sha256 | ETF file sha256)."""
    ps = inputs(era); return None if ps is None else hashlib.sha256("|".join([code_hash()] + [sha(p) for p in ps]).encode()).hexdigest()


def stamp():
    if STAMP.exists(): raise SystemExit(f"{STAMP} exists (written once)")
    doc = dict(label="Section 5 feature-cache stamp (finding 14, outside the closure)", created_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(), feature_code=list(FEATURE_CODE),
               eras={era: dict(key=key(era), inputs=[str(x) for x in (inputs(era) or [])], files={f: sha(CACHE / f) for f in fs if (CACHE / f).exists()}) for era, fs in FILES.items()})
    STAMP.parent.mkdir(parents=True, exist_ok=True); STAMP.write_text(json.dumps(doc, indent=1), encoding="utf-8"); STAMP.with_suffix(".sha256").write_text(f"{sha(STAMP)}  {STAMP.name}\n", encoding="ascii")
    return doc


def rows():
    """(group, label, recorded, actual_fn, note) rows for the finding-17 preflight; actual_fn() -> current value or None (missing)."""
    if not STAMP.exists(): return [("C feature cache", "cache_stamp.json", "stamp missing", lambda: None, "s5_cache_stamp.py")]
    side = STAMP.with_suffix(".sha256"); doc = json.loads(STAMP.read_text(encoding="utf-8")); out = []
    out.append(("C feature cache", "cache_stamp.json sidecar", side.read_text().split()[0] if side.exists() else "sidecar missing", lambda: sha(STAMP), "s5_cache_stamp.py"))
    for era, e in doc["eras"].items():
        out.append(("C feature cache", f"{era} key = sha(feature code | panel | ETF)", e["key"], (lambda era=era: key(era)), "finding 14 key"))
        for f, h in e["files"].items(): out.append(("C feature cache", f"cache/{f}", h, (lambda f=f: sha(CACHE / f) if (CACHE / f).exists() else None), "cache_stamp.json"))
    return out


if __name__ == "__main__":
    if "--check" in sys.argv:
        worst = 0
        for g, lab, rec, fn, _ in rows():
            act = fn(); st = "MISSING" if act is None else ("OK" if act == rec else "MISMATCH"); worst = max(worst, 2 if act is None else (0 if act == rec else 1)); print(f"{st:8s} {lab}")
        sys.exit(worst)
    print(json.dumps(stamp(), indent=1))
