#!/usr/bin/env python3
"""Guarded readers of the Section 3.10 canonical one-minute panels (SPY, TLT, HYG, GOLD = XAUUSD mid, DOLLAR = DOLLARIDX mid), outside the code-version closure.
The panels hold development AND evaluation sessions. Two entry points:
  load_development(era, columns): rows with session_date_ny inside the era's TRAIN span (step3_all_in_one.CONFIG; checked against that file's text), nothing later.
      Rows after the span are discarded chunk by chunk while streaming and are never returned or summarised.
  load_eval(era, columns, freeze_path, confirm_token): rows inside the era's evaluation period only, and only when ALL of these hold, checked in this order:
      1. the freeze file verifies against its sidecar (s5_freeze.verify_freeze) and confirm_token is its sha256 (deliberate invocation);
      2. the freeze's amendment list equals s5_amendment_manifest.freeze_ready() now (every amendment ADOPTED, unchanged since the freeze; A27 and A23 finished);
      3. the era-calibration lock exists (A16 rule 5: the era calibration precedes the freeze and the evaluation);
      4. the audit-1 finding 17 preflight passes now (s5_preflight_data_hashes.py exit 0; the panel is the file whose hash the frozen 4.3.0 protocol records);
      5. for Section 6 calls (section6=True): the Section 6 fingerprint file exists and verifies (AMENDMENT_A28 rule 6e).
    Every call, allowed or refused, is appended to results/eval_access_log.txt before any row is read.
Evaluation periods: LEGACY 2019-01-02..2022-03-04 (4.3.0-A1), RAW 2025-01-02..2026-10-12 (4.3.0 freeze v2). Nothing here writes a freeze or a lock."""
import sys, re, json, hashlib, datetime, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
PANELS = {"LEGACY": ROOT / "section3_10_alignment_results" / "canonical_panel_LEGACY_1m.csv.gz", "RAW": ROOT / "section3_10_alignment_results" / "canonical_panel_RAW_1m.csv.gz"}
DEV = {"LEGACY": ("2003-01-02", "2018-12-21"), "RAW": ("2022-03-07", "2024-12-23")}
EVAL = {"LEGACY": ("2019-01-02", "2022-03-04"), "RAW": ("2025-01-02", "2026-10-12")}
ACCESS_LOG = HERE / "results" / "eval_access_log.txt"
ASSETS = ("SPY", "TLT", "HYG", "GOLD", "DOLLAR")
KEYS = ["utc_minute_start_assumed", "available_utc_assuming_minute_start", "session_date_ny", "minute_index_in_session"]


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def check_dev_spans():
    """DEV must equal the first/last sessions of step3_all_in_one.CONFIG (read as text, not imported), and EVAL must start after DEV ends."""
    txt = (ROOT / "step3_all_in_one.py").read_text(encoding="utf-8")
    for era, (a, b) in DEV.items():
        m = re.search(rf'"{era}":\("(\d{{4}}-\d\d-\d\d)","(\d{{4}}-\d\d-\d\d)"', txt)
        if not m or (m.group(1), m.group(2)) != (a, b): raise PermissionError(f"{era}: development span {a}..{b} differs from step3_all_in_one.CONFIG")
        if not EVAL[era][0] > b: raise PermissionError(f"{era}: evaluation period does not start after the development span")
    return True


def _read(era, columns, lo, hi, panel=None, chunksize=500_000):
    import pandas as pd
    cols = list(dict.fromkeys(KEYS + list(columns or []))); out = []
    for ch in pd.read_csv(panel or PANELS[era], usecols=cols, chunksize=chunksize, dtype={"session_date_ny": str}):
        keep = (ch["session_date_ny"] >= lo) & (ch["session_date_ny"] <= hi)
        if keep.any(): out.append(ch.loc[keep])
        del ch
    df = pd.concat(out, ignore_index=True) if out else pd.DataFrame(columns=cols)
    if len(df) and not (df["session_date_ny"].min() >= lo and df["session_date_ny"].max() <= hi): raise RuntimeError("date filter failed")
    return df


def load_development(era, columns, panel=None):
    check_dev_spans(); lo, hi = DEV[era]; return _read(era, columns, lo, hi, panel)


def _log(msg):
    ACCESS_LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(ACCESS_LOG, "a", encoding="utf-8") as f: f.write(f"{datetime.datetime.now(datetime.timezone.utc).isoformat()} {msg}\n")


def eval_guard(era, freeze_path, confirm_token, section6=False, preflight=None, lock=None, fingerprint=None):
    import s5_freeze as FZ, s5_amendment_manifest as AM, s5_guard as G
    fz = FZ.verify_freeze(freeze_path)
    if confirm_token != sha(freeze_path): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    now = AM.freeze_ready()
    if fz.get("amendments") != now: raise PermissionError("the amendment list differs from the one in the freeze document")
    if not Path(lock or G.LOCK).exists(): raise PermissionError("era-calibration lock missing: the era calibration must precede the evaluation")
    rc = (preflight or (lambda: subprocess.run([sys.executable, str(HERE / "s5_preflight_data_hashes.py")], capture_output=True, text=True).returncode))()
    if rc != 0: raise PermissionError(f"finding-17 data-hash preflight failed (exit {rc})")
    if section6:
        fp = Path(fingerprint or (ROOT / "section6" / "results" / "s6_fingerprint.json")); side = fp.with_suffix(".sha256")
        if not fp.exists() or not side.exists() or side.read_text().split()[0] != sha(fp): raise PermissionError("Section 6 fingerprint missing or differs from its sidecar (A28 rule 6e)")
    if era not in EVAL: raise PermissionError(f"unknown era {era}")
    return fz


def load_eval(era, columns, freeze_path, confirm_token, section6=False, panel=None, **kw):
    _log(f"REQUEST era={era} columns={list(columns or [])} freeze={Path(freeze_path).name} section6={section6}")
    try: eval_guard(era, freeze_path, confirm_token, section6, **kw)
    except Exception as e: _log(f"REFUSED era={era}: {e}"); raise
    _log(f"ALLOWED era={era}"); lo, hi = EVAL[era]; return _read(era, columns, lo, hi, panel)


if __name__ == "__main__": print(check_dev_spans())
