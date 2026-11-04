#!/usr/bin/env python3
"""Integrates AMENDMENT_A14.2 into SECTION5_PROTOCOL.md (consolidation only), updates the audit status files (previous versions preserved), preserves the A14.1 protocol as SECTION5_PROTOCOL_v5_FROZEN_A14_1.md. Refuses to run twice."""
import hashlib, datetime, shutil, re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V5 = ROOT / "SECTION5_PROTOCOL_v5_FROZEN_A14_1.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A14.1" in P.read_text(encoding="utf-8"); assert not V5.exists()
def keep(src, dst): shutil.copyfile(ROOT / src, ROOT / dst); (ROOT / dst).with_suffix(".sha256").write_text(f"{sha(ROOT / dst)}  {dst}\n", encoding="ascii")
keep("SECTION5_PROTOCOL.md", V5.name); keep("COLD_AUDIT_STATUS.md", "COLD_AUDIT_STATUS_v3_A14.md"); keep("OPEN_AUDIT_FINDINGS.md", "OPEN_AUDIT_FINDINGS_v2_A14.md")
now = datetime.datetime.now(datetime.timezone.utc)
def edit(path, pairs):
    t = (ROOT / path).read_text(encoding="utf-8")
    for a, b in pairs: assert t.count(a) == 1, (path, a[:60]); t = t.replace(a, b)
    (ROOT / path).write_text(t, encoding="utf-8"); (ROOT / path).with_suffix(".sha256").write_text(f"{sha(ROOT / path)}  {Path(path).name}\n", encoding="ascii")
cs = (ROOT / "COLD_AUDIT_STATUS.md").read_text(encoding="utf-8").split("\n"); r19 = next(l for l in cs if l.startswith("| 19 |"))
edit("COLD_AUDIT_STATUS.md", [(r19, "| 19 | Low | A bad Student-t start can win silently | **resolved** | A14 (reporting) and A14.2 (rule): the kept fit is the highest-likelihood start among those satisfying the 1% rule; if none does, the best fit is kept and flagged; flagged fits are counted in every report and an H1 sensitivity excludes folds with flagged Student-t fits; unit-tested. Measured before the change: 1 of 80 inner-train fits needed a restart, none was kept with a state under 1%. |"),
    ("Totals: resolved 9, disclosed 4, open 9.", "Totals: resolved 10, disclosed 4, open 8."),
    ("Still open: 10, 12, 13, 16-21 (19 has the reporting fix of A14 and waits for a design choice);", "Fixed by A14.2: 19. Still open: 10, 12, 13, 16-18, 20, 21;")])
of = (ROOT / "OPEN_AUDIT_FINDINGS.md").read_text(encoding="utf-8").split("\n"); o19 = next(l for l in of if l.startswith("| 19 |"))
edit("OPEN_AUDIT_FINDINGS.md", [(o19 + "\n", ""), ("Nine findings are open after A14: 3 Medium, 6 Low (22 was resolved by A14/A14.1). None changes the primary H1 detection or QLIKE computation except possibly 19 (Student-t fits).", "Eight findings are open after A14.2: 3 Medium, 5 Low (22 was resolved by A14/A14.1, 19 by A14.2). None changes the primary H1 detection or QLIKE computation."),
    ("Open cold-audit findings after A14 (the A13 list is preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`)", "Open cold-audit findings after A14.2 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md` and `OPEN_AUDIT_FINDINGS_v2_A14.md`)")])
t = P.read_text(encoding="utf-8")
def rep(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)
rep("(integrated through Amendment A14.1)", "(integrated through Amendment A14.2)")
t = re.sub(r"Re-frozen with A14 \S+ UTC \(\S+ New York; ", f"Re-frozen with A14.2 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
rep("with A13 at 2026-11-04T00:06 UTC)", "with A13 at 2026-11-04T00:06 UTC and with A14 earlier on 2026-11-04)")
rep("Amendments A6 to A14.1. ", "Amendments A6 to A14.2. "); rep("through A13 as `SECTION5_PROTOCOL_v4_FROZEN_A13.md`", "through A13 as `SECTION5_PROTOCOL_v4_FROZEN_A13.md`, through A14.1 as `SECTION5_PROTOCOL_v5_FROZEN_A14_1.md`")
rep("\n\nSupporting records", "\n| A14.2 | `AMENDMENT_A14_2.md` | Student-t start selection under the 1%% rule; flagged-fit reporting and sensitivity | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A14_2.md"))
rep("Student-t HMM: per start the number of attempts and whether the kept fit has every state at 1% or more are recorded (A14 finding 19); what to do when all 10 attempts fail is not decided.", "Student-t HMM (A14, A14.2): per start the number of attempts and whether the kept fit has every state at 1% or more are recorded; the kept fit is the highest-likelihood start among those satisfying the 1% rule, and if none does after 10 attempts the highest-likelihood fit is kept and flagged; flagged fits are counted in every report.")
rep("5.10 Robustness: by era;", "5.10 Robustness: by era; Student-t HMM sensitivity excluding folds whose kept feature or baseline fit is flagged (A14.2);")
a = t.index("- Cold audit findings (`COLD_AUDIT_STATUS.md`"); b = t.index("- The era-level calibration")
t = t[:a] + "- Cold audit findings (`COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md`): 8 open (10, 12, 13, 16-18, 20, 21), 4 disclosed (1 residual, 2, 4, 5, 8: see the status list), 10 resolved (19 by A14/A14.2, 22 by A14/A14.1). None of the open ones changes the primary detection or QLIKE computation.\n" + t[b:]
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
