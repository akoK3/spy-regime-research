#!/usr/bin/env python3
"""Preflight for audit-1 finding 17 (input hashes not verified at run time): hash the data files a run reads and
compare them with the hashes recorded before any Section 5 run. Standalone: standard library only; it imports
nothing from s5_lib, s5_backend or any other module in the result-code closure, and it never calls a loader.

Recorded hashes (all written before Section 5 began; none is recomputed here):
  A. Market data (SPY panel and ETF file per era): frozen Section 4.3.0 protocol v2,
     frozen_documents/protocol_20261029T032641Z.json, development.<era>.panel_sha256 / etf_sha256. The protocol's
     own sidecar is checked first. The panel hashes are also cross-checked against the Section 3 close-out manifest
     (section3_final_closeout_results/input_output_manifest.csv, HASHED_AT_CLOSEOUT).
  B. Cited inputs of SECTION5_PROTOCOL.md (feature matrix v2 and views, folds, fold check, Lee-Mykland calibration):
     the "Cited inputs (SHA-256)" table. The protocol's sidecar is checked first.

The file actually hashed for A is the one the loader opens: the relative path in step3_all_in_one.CONFIG
(read as text, not imported), resolved like step3_all_in_one.file_path (ROOT/rel, else ROOT/<file name>). The
script stops if that path differs from the path the frozen protocol names.

  C. Section 5 feature caches (cache/{era}_features.npz, _bases.npz): results/cache_stamp.json written by
     s5_cache_stamp.py (finding 14 key = sha256(feature code | panel | ETF file); added 2026-11-10, FABLE_AUDIT L6).
     A changed cache, or changed feature code or input with an unchanged cache (stale), is a MISMATCH.

Not covered: pickles, and files whose hashes are already checked by guards (contamination list, completion
records, amendments).

Usage:  python section5/s5_preflight_data_hashes.py [--out FILE.json]
Exit:   0 all match / 1 a hash differs / 2 a file or a record is missing or inconsistent."""
import sys, re, json, csv, hashlib, datetime, argparse
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
FROZEN = ROOT / "frozen_documents" / "protocol_20261029T032641Z.json"
S3_MANIFEST = ROOT / "section3_final_closeout_results" / "input_output_manifest.csv"
PROTOCOL = ROOT / "SECTION5_PROTOCOL.md"
STEP3 = ROOT / "step3_all_in_one.py"


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""): h.update(b)
    return h.hexdigest()


def sidecar_ok(p):
    s = Path(p).with_suffix(".sha256")
    return s.exists() and s.read_bytes().decode("ascii").split()[0] == sha(p)


def resolve(rel):
    """Same resolution as step3_all_in_one.file_path."""
    p = ROOT / rel
    if p.exists(): return p
    alt = ROOT / Path(rel).name
    return alt if alt.exists() else None


def loader_config():
    """CONFIG of step3_all_in_one.py, parsed from its text: era -> (panel rel path, etf rel path)."""
    t = STEP3.read_text(encoding="utf-8")
    return {m.group(1): (m.group(2), m.group(3)) for m in re.finditer(r'"(RAW|LEGACY)":\("[^"]*","[^"]*","([^"]+)","([^"]+)"\)', t)}


def recorded():
    """[(group, label, recorded sha, path to hash, note)] or raise SystemExit(2) on a broken record."""
    probs, out = [], []
    if not sidecar_ok(FROZEN): probs.append(f"{FROZEN.name}: sidecar missing or does not match")
    if not sidecar_ok(PROTOCOL): probs.append(f"{PROTOCOL.name}: sidecar missing or does not match")
    fz = json.loads(FROZEN.read_text(encoding="utf-8"))
    s3 = {}
    if S3_MANIFEST.exists():
        for r in csv.reader(S3_MANIFEST.open(encoding="utf-8")):
            if len(r) >= 3 and re.fullmatch(r"[0-9a-f]{64}", r[2]): s3[Path(r[0].replace("\\", "/")).name] = r[2]
    cfg = loader_config()
    if set(cfg) != {"RAW", "LEGACY"}: probs.append(f"step3_all_in_one.CONFIG not parsed (found {sorted(cfg)})")
    for era in ("LEGACY", "RAW"):
        dev = fz["development"][era]
        for kind, idx in (("panel", 0), ("etf", 1)):
            rec = dev[f"{kind}_sha256"]; frozen_name = Path(dev[f"{kind}_file"].replace("\\", "/")).name
            rel = cfg.get(era, (None, None))[idx]
            if rel is None: continue
            if Path(rel).name != frozen_name: probs.append(f"{era} {kind}: loader reads {rel}, frozen protocol names {frozen_name}")
            if frozen_name in s3 and s3[frozen_name] != rec: probs.append(f"{era} {kind}: frozen protocol {rec[:16]} and Section 3 manifest {s3[frozen_name][:16]} disagree")
            note = "frozen 4.3.0 v2" + (" = Section 3 manifest" if frozen_name in s3 else "")
            out.append(("A market data", f"{era}_{kind}:{frozen_name}", rec, resolve(rel), note))
    t = PROTOCOL.read_text(encoding="utf-8")
    table = t.split("## Cited inputs (SHA-256)", 1)[1].split("\n## ", 1)[0] if "## Cited inputs (SHA-256)" in t else ""
    cited = re.findall(r"\|\s*`([^`]+)`\s*\|\s*`([0-9a-f]{64})`\s*\|", table)
    if not cited: probs.append("SECTION5_PROTOCOL.md: Cited inputs table not found")
    for rel, h in cited:
        p = ROOT / rel; out.append(("B cited inputs", rel, h, p if p.exists() else None, "SECTION5_PROTOCOL.md cited inputs"))
    if probs:
        for x in probs: print("RECORD PROBLEM:", x)
        raise SystemExit(2)
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(); ap.add_argument("--out", help="write the check as JSON to this file"); a = ap.parse_args(argv)
    import s5_cache_stamp as CS      # standard library only; outside the closure
    rows, worst = [], 0
    for group, label, rec, path, note in recorded() + CS.rows():
        actual = path() if callable(path) else (sha(path) if path is not None else None)
        if actual is None: status = "MISSING"; worst = max(worst, 2); path = None
        else:
            status = "OK" if actual == rec else "MISMATCH"
            if status == "MISMATCH": worst = max(worst, 1)
        rows.append(dict(group=group, file=label, path=(str(path) if path is not None and not callable(path) else None), recorded=rec, actual=actual, status=status, record=note))
        print(f"{status:8s} {group:15s} {label}  recorded {rec[:16]}  actual {(actual or '-')[:16]}")
    verdict = {0: "PASS", 1: "FAIL (hash mismatch)", 2: "FAIL (file missing)"}[worst]
    print(f"data hash preflight: {verdict}; {sum(r['status'] == 'OK' for r in rows)}/{len(rows)} files match")
    if a.out:
        doc = dict(label="Data hash preflight (audit-1 finding 17)", checked_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                   script_sha256=sha(__file__), frozen_protocol_sha256=sha(FROZEN), section5_protocol_sha256=sha(PROTOCOL), verdict=verdict, files=rows)
        Path(a.out).parent.mkdir(parents=True, exist_ok=True); Path(a.out).write_text(json.dumps(doc, indent=1), encoding="utf-8")
    return worst


if __name__ == "__main__":
    sys.exit(main())
