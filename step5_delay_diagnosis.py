#!/usr/bin/env python3
"""Where do the strict one-bar delay test mismatches fall? Reads the failed outputs from the
saved verification report, recomputes only those, and records slot, session and value pattern
of every mismatching row. Changes nothing."""
import sys, json, hashlib, datetime
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import step5_policy as p  # noqa: E402

OUT = p.OUT
report_file = sorted(OUT.glob("policy_4_3_1_P1_verification_2*.json"))[-1]  # the original (v1) report
report = json.loads(report_file.read_text(encoding="utf-8"))
failed = {r["detail"]["dataset"]: r["detail"]["failed"] for r in report["table"] if "detail" in r}


def diagnose(d, label):
    names = failed[label]
    orig, late = p.compute(d), p.compute(p.delayed(d))
    spans = list(zip(d["first"], d["end"]))
    lens = [int(b - a) for a, b in spans]
    src = np.concatenate([np.arange(a, b - 1) for a, b in spans]); dst = src + 1
    session = np.repeat(np.arange(len(spans)), [n - 1 for n in lens])
    early = [k for k, n in enumerate(lens) if n < 390]
    res = {}
    for name in names:
        x, y = orig[name][src], late[name][dst]
        bad = ~np.isclose(x, y, rtol=1e-9, atol=0, equal_nan=True)
        w = int("".join(ch for ch in name.split("_")[0] if ch.isdigit())) if "partial90" in name else None
        res[name] = dict(
            mismatching_rows=int(bad.sum()), rows_compared=int(len(src)),
            original_nan_delayed_finite=int((np.isnan(x[bad]) & np.isfinite(y[bad])).sum()),
            original_finite_delayed_nan=int((np.isfinite(x[bad]) & np.isnan(y[bad])).sum()),
            both_finite_but_different=int((np.isfinite(x[bad]) & np.isfinite(y[bad])).sum()),
            delayed_slots_with_mismatch=sorted(set(int(v) for v in d["slot"][dst[bad]])),
            sessions_with_mismatch=int(len(set(session[bad]))),
            expected_edge=("delayed slot == W (first computable row; original needs slot >= W)" if w else "slot right after an early-close session's last bar, in the 20 sessions after it"),
            W=w,
        )
        if w:
            res[name]["all_mismatches_at_slot_W_only"] = res[name]["delayed_slots_with_mismatch"] == [w] and res[name]["both_finite_but_different"] == 0
        else:
            bad_sessions = sorted(set(int(k) for k in session[bad]))
            near_early = all(any(0 < k - e <= 20 for e in early) for k in bad_sessions)
            res[name]["early_close_session_indexes"] = early
            res[name]["all_mismatches_after_early_close"] = bool(near_early and bad.sum() > 0)
    return res


out = {"generated_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(), "verification_report": report_file.name,
       "verification_report_sha256": p.sha(report_file), "datasets": {}}
for label, builder in (("synthetic panel", lambda: p.s.synthetic_panel()), ("RAW 40-session slice", lambda: p.real_slice("RAW")), ("LEGACY 40-session slice", lambda: p.real_slice("LEGACY"))):
    out["datasets"][label] = diagnose(builder(), label)
    for name, r in out["datasets"][label].items():
        print(f"{label} | {name}: {r['mismatching_rows']}/{r['rows_compared']} rows differ; "
              f"orig NaN->delayed finite {r['original_nan_delayed_finite']}, orig finite->delayed NaN {r['original_finite_delayed_nan']}, "
              f"both finite but different {r['both_finite_but_different']}; delayed slots {r['delayed_slots_with_mismatch'][:6]}", flush=True)
data = (json.dumps(out, indent=2) + "\n").encode("utf-8")
path = OUT / "step5_delay_failure_diagnosis.json"
print("SHA-256:", p.write_hashed(path, data), path.name)
