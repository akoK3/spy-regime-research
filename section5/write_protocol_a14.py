#!/usr/bin/env python3
"""Integrates AMENDMENT_A14 and A14.1 into SECTION5_PROTOCOL.md (consolidation only), updates the audit status files (previous versions preserved) and preserves the A13 protocol as
SECTION5_PROTOCOL_v4_FROZEN_A13.md. Refuses to run twice."""
import hashlib, datetime, shutil, re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V4 = ROOT / "SECTION5_PROTOCOL_v4_FROZEN_A13.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A13" in P.read_text(encoding="utf-8"); assert not V4.exists()
def keep(src, dst): shutil.copyfile(ROOT / src, ROOT / dst); (ROOT / dst).with_suffix(".sha256").write_text(f"{sha(ROOT / dst)}  {dst}\n", encoding="ascii")
keep("SECTION5_PROTOCOL.md", V4.name); keep("COLD_AUDIT_STATUS.md", "COLD_AUDIT_STATUS_v2_A12.md"); keep("OPEN_AUDIT_FINDINGS.md", "OPEN_AUDIT_FINDINGS_v1_A13.md")
now = datetime.datetime.now(datetime.timezone.utc)
# ---- audit status files
def edit(path, pairs):
    t = (ROOT / path).read_text(encoding="utf-8")
    for a, b in pairs: assert t.count(a) == 1, (path, a[:60]); t = t.replace(a, b)
    (ROOT / path).write_text(t, encoding="utf-8"); (ROOT / path).with_suffix(".sha256").write_text(f"{sha(ROOT / path)}  {Path(path).name}\n", encoding="ascii")
cs = (ROOT / "COLD_AUDIT_STATUS.md").read_text(encoding="utf-8").split("\n")
r19 = next(l for l in cs if l.startswith("| 19 |")); r22 = next(l for l in cs if l.startswith("| 22 |"))
edit("COLD_AUDIT_STATUS.md", [
    (r19, "| 19 | Low | A bad Student-t start can win silently | **open** | A14: per-start attempts and the 1% occupancy flag are now recorded and reported (reporting fix). Measured on 80 inner-train fits of the contaminated folds: 1 needed a restart, none used all 10 attempts, none was kept with a state under 1%. The behaviour when all attempts fail (reject, keep flagged, raise the cap) and whether to prefer a valid start over a higher-likelihood violating one is a design choice, not decided. |"),
    (r22, "| 22 | Low | Unamended choices and records | **resolved** | A14, A14.1: HSMM pseudo-count 0.5 (hazard smoothing), hazard clip, probability floors, weight guard and the duration cap 78 (= full-session updates) are documented as named constants with unit tests, results unchanged; the `s5_fast.py` docstring credit is corrected; `PILOT_REPORT_LEGACY_FILES.md` gives the file hashes the LEGACY report lacks (its writer script is not recoverable); the protocol no longer says DRAFT (frozen). |"),
    ("Totals: resolved 8, disclosed 4, open 10.", "Totals: resolved 9, disclosed 4, open 9."),
    ("Findings 6, 7, 9, 14 and 15 were fixed by A12. Still open: 10, 12, 13, 16-21 and the open part of 22; disclosed: 1 (residual), 2, 4 (gap handling), 5, 8.", "Findings 6, 7, 9, 14 and 15 were fixed by A12; 22 by A14/A14.1. Still open: 10, 12, 13, 16-21 (19 has the reporting fix of A14 and waits for a design choice); disclosed: 1 (residual), 2, 4 (gap handling), 5, 8.")])
of = (ROOT / "OPEN_AUDIT_FINDINGS.md").read_text(encoding="utf-8").split("\n")
o19 = next(l for l in of if l.startswith("| 19 |")); o22 = next(l for l in of if l.startswith("| 22 |"))
edit("OPEN_AUDIT_FINDINGS.md", [
    (o22 + "\n", ""),
    (o19, "| 19 | Low | A bad Student-t start can win silently (`s5_models.py`) | Student-t HMM fit quality. A14 records per-start attempts and the 1% occupancy flag (reporting). Measured on 80 inner-train fits of the contaminated folds: 1 restart, none exhausted, none kept with a state under 1%. Open design choice: behaviour when all 10 attempts fail, and whether a valid start is preferred over a higher-likelihood violating start. |"),
    ("Ten findings are open: 3 Medium, 7 Low. None changes the primary H1 detection or QLIKE computation except possibly 19 (Student-t fits) and 22 (HSMM parameters not in the protocol).", "Nine findings are open after A14: 3 Medium, 6 Low (22 was resolved by A14/A14.1). None changes the primary H1 detection or QLIKE computation except possibly 19 (Student-t fits)."),
    ("Open cold-audit findings after A12", "Open cold-audit findings after A14 (the A13 list is preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`)")])
# ---- protocol
t = P.read_text(encoding="utf-8")
def rep(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)
rep("(integrated through Amendment A13)", "(integrated through Amendment A14.1)")
t = re.sub(r"Re-frozen with A13 \S+ UTC \(\S+ New York; ", f"Re-frozen with A14 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
rep("and with A12 earlier on 2026-11-03)", "with A12 earlier on 2026-11-03 and with A13 at 2026-11-04T00:06 UTC)")
rep("Amendments A6 to A13. ", "Amendments A6 to A14.1. "); rep("through A12 as `SECTION5_PROTOCOL_v3_FROZEN_A12.md`", "through A12 as `SECTION5_PROTOCOL_v3_FROZEN_A12.md`, through A13 as `SECTION5_PROTOCOL_v4_FROZEN_A13.md`")
rep("\n\nSupporting records", "\n| A14 | `AMENDMENT_A14.md` | audit finding 22 documented; finding 19 reporting | `%s` |\n| A14.1 | `AMENDMENT_A14_1.md` | M-step weight guard documented | `%s` |\n\nSupporting records" % (sha(ROOT / "AMENDMENT_A14.md"), sha(ROOT / "AMENDMENT_A14_1.md")))
rep("Seeds and versions recorded.", "Seeds and versions recorded. HSMM constants (A14, A14.1; as in the code, unchanged): the duration hazard update is h[k, d] = (leave + 0.5 h0) / (leave + stay + 0.5) with the pooled hazard h0, last bin 1, clipped to [1e-6, 1]; duration cap Dmax = 78 bins of one grid interval (the 78 decision updates of a full session); +1e-12 on initial-state and transition counts; +1e-12 guard on state-weight denominators. Student-t HMM: per start the number of attempts and whether the kept fit has every state at 1% or more are recorded (A14 finding 19); what to do when all 10 attempts fail is not decided.")
a = t.index("- Cold audit findings (`COLD_AUDIT_STATUS.md`"); b = t.index("- The era-level calibration")
t = t[:a] + "- Cold audit findings (`COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md`): 9 open (10, 12, 13, 16-21; 19 has its reporting fix and waits for a design choice), 4 disclosed (1 residual, 2, 4, 5, 8: see the status list), 9 resolved (22 by A14/A14.1). The open ones do not change the primary detection or QLIKE computation except possibly 19 (Student-t fits).\n- Finding 19 design choice, asked of the user: behaviour when all 10 restart attempts of a Student-t start leave a state under 1% (reject the fit, keep it flagged as now, or raise the cap), and whether a start that satisfies the rule is preferred over a higher-likelihood start that violates it.\n" + t[b:]
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
