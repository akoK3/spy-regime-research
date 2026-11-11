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
      5. for Section 6 calls (section6=True): the Section 6 fingerprint file exists, verifies (AMENDMENT_A28 rule 6e) and equals the code on disk (AMENDMENT_A36 rule 7c).
  authorise(era, freeze_path, confirm_token, section6, what): the same guard and log for a read that another audited loader performs (the 5.13 panel of
      s5_eval513, AMENDMENT_A36 rule 7d); returns the evaluation span. Nothing may open an evaluation span without load_eval, authorise or authorise_a38.
  authorise_a38(kind, freeze_path, confirm_token, what): the A38 rule 1 reads (HF Raw / Clean SPY on the RAW evaluation span), after the official 5.13 RAW result.
    Every call, allowed or refused, is appended to results/eval_access_log.txt before any row is read.
Evaluation periods: LEGACY 2019-01-02..2022-03-04 (4.3.0-A1), RAW 2025-01-02..2026-10-12 (4.3.0 freeze v2). Nothing here writes a freeze or a lock."""
import sys, re, json, hashlib, datetime, subprocess
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent
PANELS = {"LEGACY": ROOT / "section3_10_alignment_results" / "canonical_panel_LEGACY_1m.csv.gz", "RAW": ROOT / "section3_10_alignment_results" / "canonical_panel_RAW_1m.csv.gz"}
DEV = {"LEGACY": ("2003-01-02", "2018-12-21"), "RAW": ("2022-03-07", "2024-12-23")}
EVAL = {"LEGACY": ("2019-01-02", "2022-03-04"), "RAW": ("2025-01-02", "2026-10-12")}
ACCESS_LOG = HERE / "results" / "eval_access_log.txt"
EVAL_READS = []                                # (era, section6) of every evaluation-period read allowed in this process (FABLE_REAUDIT M3: s6_run.write_once requires the A26 label once this is non-empty)
sys.path.insert(0, str(HERE)); import s5_guard as _G
LOCK = _G.LOCK                                 # the era-calibration lock path of s5_guard (A16 rule 5)
FINGERPRINT = ROOT / "section6" / "results" / "s6_fingerprint.json"
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


def _read(era, columns, lo, hi, panel=None, chunksize=500_000):      # panel: development reads only (load_development); load_eval never passes one
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


def _preflight():
    """The finding-17 data-hash preflight, run as its own process; exit code."""
    return subprocess.run([sys.executable, str(HERE / "s5_preflight_data_hashes.py")], capture_output=True, text=True).returncode


def eval_guard(era, freeze_path, confirm_token, section6=False):
    """No argument can relax a check (FABLE_AUDIT M1): the lock, the fingerprint, the panel paths and the preflight are module constants / functions; only tests patch them."""
    return _checks(era, freeze_path, confirm_token, section6, need_active=True)


def precheck(era, freeze_path, confirm_token, section6=False):
    """AMENDMENT_A37 rule 2a: every check of eval_guard, run before the one-shot marker, except that the labelled 5.13 entry need not be active yet. Reads nothing; logged as
    PRECHECK (never ALLOWED) and not recorded in EVAL_READS."""
    _log(f"PRECHECK era={era} freeze={Path(freeze_path).name} section6={section6}")
    try: fz = _checks(era, freeze_path, confirm_token, section6, need_active=False)
    except Exception as e: _log(f"PRECHECK FAILED era={era}: {e}"); raise
    _log(f"PRECHECK PASSED era={era}"); return fz


def _checks(era, freeze_path, confirm_token, section6, need_active):
    import s5_freeze as FZ, s5_amendment_manifest as AM, s5_eval_label as EV
    EV.ready()      # AMENDMENT_A34 rule 3b: the A26 label module is in place before any evaluation-period read; FABLE_REAUDIT M3: and no script calls the 5.13 writer directly
    if need_active and not section6 and not EV.ACTIVE: raise PermissionError("a Section 5 evaluation-period read is allowed only inside s5_eval_label.run_confirmatory_labelled (A26 1d, A34 3b)")
    fz = FZ.verify_freeze(freeze_path)
    if confirm_token != sha(freeze_path): raise PermissionError("confirm_token must be the sha256 of the freeze file")
    now = AM.freeze_ready()
    if fz.get("amendments") != now: raise PermissionError("the amendment list differs from the one in the freeze document")
    if not Path(LOCK).exists(): raise PermissionError("era-calibration lock missing: the era calibration must precede the evaluation")
    rc = _preflight()
    if rc != 0: raise PermissionError(f"finding-17 data-hash preflight failed (exit {rc})")
    if section6: fingerprint_check()
    if era not in EVAL: raise PermissionError(f"unknown era {era}")
    return fz


def fingerprint_check():
    """A28 6e and A36 7c: the Section 6 fingerprint exists, equals its sidecar, and every fingerprinted file and the code version equal the code on disk."""
    fp = Path(FINGERPRINT); side = fp.with_suffix(".sha256")
    if not fp.exists() or not side.exists() or side.read_text().split()[0] != sha(fp): raise PermissionError("Section 6 fingerprint missing or differs from its sidecar (A28 rule 6e)")
    sys.path.insert(0, str(ROOT / "section6")); import s6_fingerprint as FPM
    old = json.loads(fp.read_text(encoding="utf-8")); cur = FPM.current(); changed = sorted(k for k in set(old["files"]) | set(cur["files"]) if old["files"].get(k) != cur["files"].get(k))
    if changed or old.get("code_version") != cur["code_version"]: raise PermissionError("code differs from the Section 6 fingerprint (A36 rule 7c): " + (", ".join(changed) or "code version"))
    return True


def authorise(era, freeze_path, confirm_token, section6=False, what=""):
    """Guard and access log for an evaluation-period read performed by another audited loader; returns the evaluation span (first, last session)."""
    _log(f"REQUEST era={era} what={what!r} freeze={Path(freeze_path).name} section6={section6}")
    try: eval_guard(era, freeze_path, confirm_token, section6)
    except Exception as e: _log(f"REFUSED era={era}: {e}"); raise
    _log(f"ALLOWED era={era}"); EVAL_READS.append((era, bool(section6))); return EVAL[era]


A38_RESULTS = HERE / "results"                 # where the official 5.13 RAW result lies (tests patch it)


def authorise_a38(kind, freeze_path, confirm_token, what=""):
    """AMENDMENT_A38 rule 5a (PREFREEZE_AUDIT M4): the guard and access log for the A38 rule 1 reads (SPY from the 2026-11-11 HF Raw / Clean files on the study grid of
    the RAW evaluation span). Every check of the Section 6 guard (freeze, token, amendment list, lock, data-hash preflight, Section 6 fingerprint), plus: A38 ADOPTED
    and equal to its sidecar; the official 5.13 RAW result exists and carries the A26 label. It needs neither the labelled 5.13 entry nor section6=True; it is logged
    as A38. The file hash and the one-shot marker are checked by s5_a38.run_file."""
    _log(f"REQUEST A38 kind={kind} what={what!r} freeze={Path(freeze_path).name}")
    try:
        import s5_amendment_manifest as AM, s5_eval_label as EV, s5_freeze as FZ
        if kind not in ("raw", "clean"): raise PermissionError(f"unknown A38 file kind {kind}")
        _checks("RAW", freeze_path, confirm_token, section6=True, need_active=False)
        e = AM.manifest(("A38",))[0]
        if not (e["present"] and e["status"] == "ADOPTED" and e["sidecar_matches"]): raise PermissionError("AMENDMENT_A38 is not ADOPTED with a matching sidecar")
        off = Path(A38_RESULTS) / f"{FZ.EVAL_PREFIX}RAW.json"
        if not off.exists(): raise PermissionError("A38 5a: the official 5.13 RAW result must exist before the A38 reads")
        EV.verify_labelled(A38_RESULTS)
    except Exception as ex: _log(f"REFUSED A38 kind={kind}: {ex}"); raise
    _log(f"ALLOWED A38 kind={kind}"); EVAL_READS.append(("RAW", f"a38:{kind}")); return EVAL["RAW"]


def load_eval(era, columns, freeze_path, confirm_token, section6=False):
    """Evaluation-period rows; the signature has no override (no panel, lock, fingerprint or preflight argument)."""
    lo, hi = authorise(era, freeze_path, confirm_token, section6, what=f"columns={list(columns or [])}"); return _read(era, columns, lo, hi)


if __name__ == "__main__": print(check_dev_spans())
