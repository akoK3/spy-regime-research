#!/usr/bin/env python3
"""Integrates AMENDMENT_A16 into SECTION5_PROTOCOL.md (consolidation only; 5.14 now states the canonical contamination list hash), adds audit 2 findings 16-21 to the status files
(previous versions preserved), preserves the A15 protocol as SECTION5_PROTOCOL_v7_FROZEN_A15.md. Refuses to run twice."""
import hashlib, datetime, shutil, re
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V7 = ROOT / "SECTION5_PROTOCOL_v7_FROZEN_A15.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A15)" in P.read_text(encoding="utf-8"); assert not V7.exists()
CL = ROOT / "section5/results/contamination_list.json"; ch = sha(CL); assert (CL.with_suffix(".sha256")).read_text().split()[0] == ch


def keep(src, dst): shutil.copyfile(ROOT / src, ROOT / dst); (ROOT / dst).with_suffix(".sha256").write_text(f"{sha(ROOT / dst)}  {dst}\n", encoding="ascii")
def side(path): (ROOT / path).with_suffix(".sha256").write_text(f"{sha(ROOT / path)}  {Path(path).name}\n", encoding="ascii")


keep("SECTION5_PROTOCOL.md", V7.name); keep("COLD_AUDIT_STATUS.md", "COLD_AUDIT_STATUS_v5_A15.md"); keep("OPEN_AUDIT_FINDINGS.md", "OPEN_AUDIT_FINDINGS_v4_A15.md")
now = datetime.datetime.now(datetime.timezone.utc); OLD = "700a09fc527f00d532021deafdcd725641b9eea900caf03065bcdc11f011d942"; NEW = sha(ROOT / "section5_cold_audit_2.md")
NEWROWS = [("16", "Medium", "Era calibration guard was a public flag; EraBackend callable directly", "A16 rule 1: EraBackend needs the hash-checked completion record of a main run over 34 folds"),
           ("17", "Medium", "Contamination list supplied by the caller; freeze did not compare lists", "A16 rule 2: one canonical list, checked against its sidecar and protocol 5.14 everywhere"),
           ("18", "Medium", "Registry pattern missed era_context(, splice_batch(, pool initialisers", "A16 rule 3: pattern extended; unit-tested"),
           ("19", "Low", "run_all(files=...) could narrow the checkpoint version", "A16 rule 4: argument removed"),
           ("20", "Low", "Nothing blocked re-scoring after the era calibration", "A16 rule 5: ERA_CALIBRATION.lock written before the first era fit blocks selection and scoring"),
           ("21", "Low", "Protocol hash checked once; freeze stored any string; checkpoints ignored it", "A16 rule 6: run_all verifies it, checkpoint version includes it, freeze re-verifies against the completion record")]

# ---------- COLD_AUDIT_STATUS.md
t = (ROOT / "COLD_AUDIT_STATUS.md").read_text(encoding="utf-8")
def ed(a, b, n=1):
    global t; assert t.count(a) == n, a[:60]; t = t.replace(a, b)
ed(f"## Cold audit 2 (`section5_cold_audit_2.md` (sha256 `{OLD}`), 15 findings; A15)\n\nTotals: resolved 9, open 6.",
   f"## Cold audit 2 (`section5_cold_audit_2.md`, sha256 `{NEW}` with the re-audit after A15 appended (the first part, sha256 `{OLD}`, is byte-identical to the version A15 cites); 21 findings: 15 in the audit, 16-21 = the re-audit's new problems 1-6; A15, A16)\n\nTotals: resolved 15, open 6. The re-audit confirmed findings 1-9 as fixed (3, 4 and 5 with the residuals 16-21).")
t = t.rstrip("\n") + "\n" + "".join(f"| {n} | {s} | {f} | **resolved** | {e}; unit-tested (`s5_tests_a16.py`). |\n" for n, s, f, e in NEWROWS)
ed("last by `AMENDMENT_A15.md` (the A14.2 version is preserved as `COLD_AUDIT_STATUS_v4_A14_2.md`; earlier ones as v1-v3)", "last by `AMENDMENT_A16.md` (the A15 version is preserved as `COLD_AUDIT_STATUS_v5_A15.md`; earlier ones as v1-v4)")
(ROOT / "COLD_AUDIT_STATUS.md").write_text(t, encoding="utf-8"); side("COLD_AUDIT_STATUS.md")

# ---------- OPEN_AUDIT_FINDINGS.md
t = (ROOT / "OPEN_AUDIT_FINDINGS.md").read_text(encoding="utf-8")
ed("# Open cold-audit findings after A15 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`, `_v2_A14.md`, `_v3_A14_2.md`)", "# Open cold-audit findings after A16 (earlier lists preserved as `OPEN_AUDIT_FINDINGS_v1_A13.md`, `_v2_A14.md`, `_v3_A14_2.md`, `_v4_A15.md`)")
ed(f"`section5_cold_audit_2.md` (sha256 `{OLD}`) (audit 2)", f"`section5_cold_audit_2.md` (sha256 `{NEW}`, with the re-audit after A15; the A15 version `{OLD}` is its first part) (audit 2)")
ed("Six findings are open, all Low.", "Six findings are open, all Low (10-15). The re-audit's new problems (findings 16-21) are resolved by A16.")
(ROOT / "OPEN_AUDIT_FINDINGS.md").write_text(t, encoding="utf-8"); side("OPEN_AUDIT_FINDINGS.md")

# ---------- protocol
t = P.read_text(encoding="utf-8")
ed("(integrated through Amendment A15)", "(integrated through Amendment A16)")
t = re.sub(r"Re-frozen with A15 \S+ UTC \(\S+ New York; ", f"Re-frozen with A16 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; ", t, count=1)
ed("and with A14.2 at 2026-11-04T00:29 UTC)", "and with A14.2 at 2026-11-04T00:29 UTC and with A15 at 2026-11-04T01:25 UTC)")
ed("Amendments A6 to A15. ", "Amendments A6 to A16. ")
ed("through A14.2 as `SECTION5_PROTOCOL_v6_FROZEN_A14_2.md` (sha256 `313fd3db59908e88cdcd6d64d24949a0fbd0a912a15dea498c4c93e0c16bd453`)", f"through A14.2 as `SECTION5_PROTOCOL_v6_FROZEN_A14_2.md` (sha256 `313fd3db59908e88cdcd6d64d24949a0fbd0a912a15dea498c4c93e0c16bd453`), through A15 as `SECTION5_PROTOCOL_v7_FROZEN_A15.md` (sha256 `{sha(V7)}`)")
ed("\n\nSupporting records", "\n| A16 | `AMENDMENT_A16.md` | re-audit after A15: completion record for era calibration, canonical hash-checked contamination list, registry pattern, no version override, lock after era calibration, protocol hash bound to checkpoints and freeze | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A16.md"))
ed("cold audits `section5_cold_audit.md` and `section5_cold_audit_2.md`", f"cold audits `section5_cold_audit.md` and `section5_cold_audit_2.md` (with the re-audit after A15; sha256 `{NEW}`)")
ed("26 folds confirmatory. `run_all` loads this list itself (A15 rule 5d).", f"26 folds confirmatory. The list is canonical (A16 rule 2): contamination list sha256 `{ch}`; every use checks the file against its sidecar and this hash and raises otherwise; no function takes another list.")
ed("5.12 Freeze final setups (with the baseline parameters), thresholds (era-level, 5.13, computed only after every fold has been selected and scored; A15 rule 5c)",
   "5.12 Freeze final setups (with the baseline parameters), thresholds (era-level, 5.13, computed only by an `EraBackend` holding the hash-checked completion record that `run_all` writes after every fold has been selected and scored, A16 rule 1; the first era fit writes a lock after which no selection or scoring is computed, A16 rule 5; A15 rule 5c)")
ed("before any evaluation output exists (hashed freeze document", "before any evaluation output exists; the freeze records the FROZEN protocol hash, verified again and equal to the completion record's (A16 rule 6) (hashed freeze document")
ed("the backend serves a clean fold only with the sha256 of the FROZEN protocol matching its sidecar (A15 rule 5b)", "the backend serves a clean fold only with the sha256 of the FROZEN protocol matching its sidecar (A15 rule 5b); checkpoints are keyed by the code closure (no override, A16 rule 4) and the verified protocol hash (A16 rule 6); the registry pattern also covers `era_context(`, `splice_batch(` and the pool initialisers (A16 rule 3)")
ed("Audit 2: 9 resolved by A15, 6 open (10-15, Low).", "Audit 2: 21 findings (16-21 from the re-audit after A15): 9 resolved by A15, 6 by A16, 6 open (10-15, Low).")
ed("it is reached only through `s5_main.MainBackend` after a complete run (A15). The main run (A15 rule 5) has not been run.", "it is reached only through `s5_main.MainBackend` with the completion record of a complete run (A15, A16). The main run (A15 rule 5) has not been run.")
P.write_text(t, encoding="utf-8"); side("SECTION5_PROTOCOL.md"); print("protocol", sha(P))
