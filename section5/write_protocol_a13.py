#!/usr/bin/env python3
"""Integrates AMENDMENT_A13 into SECTION5_PROTOCOL.md (consolidation only). The previous frozen text (through A12) is preserved byte-identical as SECTION5_PROTOCOL_v3_FROZEN_A12.md. Refuses to run twice."""
import hashlib, datetime, shutil, re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V3 = ROOT / "SECTION5_PROTOCOL_v3_FROZEN_A12.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A12" in P.read_text(encoding="utf-8"); assert not V3.exists(); shutil.copyfile(P, V3); V3.with_suffix(".sha256").write_text(f"{sha(V3)}  {V3.name}\n", encoding="ascii")
t = P.read_text(encoding="utf-8"); now = datetime.datetime.now(datetime.timezone.utc)


def rep(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)


rep("(integrated through Amendment A12)", "(integrated through Amendment A13)")
t = re.sub(r"Re-frozen with A12 \S+ UTC \(\S+ New York; ", f"Re-frozen with A13 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
t = t.replace("re-frozen with A11 at 2026-11-03T21:56:11 UTC)", "re-frozen with A11 at 2026-11-03T21:56:11 UTC and with A12 earlier on 2026-11-03)", 1)
rep("Amendments A6 to A12. The previous frozen texts are preserved unchanged: through A10 as `SECTION5_PROTOCOL_v1_FROZEN_A10.md`, through A11 as `SECTION5_PROTOCOL_v2_FROZEN_A11.md`", "Amendments A6 to A13. The previous frozen texts are preserved unchanged: through A10 as `SECTION5_PROTOCOL_v1_FROZEN_A10.md`, through A11 as `SECTION5_PROTOCOL_v2_FROZEN_A11.md`, through A12 as `SECTION5_PROTOCOL_v3_FROZEN_A12.md`")
rep("\n\nSupporting records", "\n| A13 | `AMENDMENT_A13.md` | EM tolerance per observation, gate sanity check, open findings list, ledger rule | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A13.md"))
rep("tol 1e-4 (absolute change of the total training log-likelihood in nats, the same for every model; fits that reach the 200 cap are reported; A12 finding 6)", "tol 1e-6 per observation (an EM run converges when the change of the total training log-likelihood divided by the number of real training updates is below 1e-6; cap 500 iterations; the same for every model; cap hits are reported per family; A12 finding 6 as amended by A13 item 1)")
rep("cold audit `section5_cold_audit.md` with its status list `COLD_AUDIT_STATUS.md`,", "cold audit `section5_cold_audit.md` with its status list `COLD_AUDIT_STATUS.md` and the open findings with their effects `OPEN_AUDIT_FINDINGS.md`,")
rep("`A12_MACHINERY_REPORT.md`).", "`A12_MACHINERY_REPORT.md`; EM tolerance and timing under A13: `A13_REPORT.md`). Records: every ledger row from A13 on carries WHY and EVIDENCE.")
a = t.index("## Open items"); b = t.index("- The era-level calibration")
t = t[:a] + """## Open items (not decided; each needs an amendment before the step that depends on it)

- Cold audit findings (`COLD_AUDIT_STATUS.md`, `OPEN_AUDIT_FINDINGS.md`): 10 open (10, 12, 13, 16-22), 4 disclosed (1 residual, 2, 4, 5, 8: see the status list), 8 resolved. The open ones do not change the primary detection or QLIKE computation except possibly 19 (Student-t fits) and 22 (HSMM parameters not in the protocol).
""" + t[b:]
t = t.replace("- Results computed under the earlier detector and splice code (A6/A7 pilots, A8 gates, A8.3, A8.4, the A10 machinery check) are records of that code; the R=1 gate (5.15) has not been rerun under the A12 code.", "- Results computed under the earlier detector and splice code (A6/A7 pilots, A8 gates, A8.3, A8.4, the A10 and A12 machinery checks) are records of that code. A single-seed R=1 gate check on RAW 3 under the A13 code gave the result in `A13_REPORT.md`; the LEGACY 29 gate and the 20-seed characterization were not rerun.")
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
