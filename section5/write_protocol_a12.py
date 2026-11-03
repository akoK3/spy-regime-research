#!/usr/bin/env python3
"""Integrates AMENDMENT_A12 into SECTION5_PROTOCOL.md (consolidation only). The previous frozen text (through A11) is preserved byte-identical as SECTION5_PROTOCOL_v2_FROZEN_A11.md. Refuses to run twice."""
import hashlib, datetime, shutil, re, json
from pathlib import Path
from zoneinfo import ZoneInfo
ROOT = Path(__file__).resolve().parent.parent; P = ROOT / "SECTION5_PROTOCOL.md"; V2 = ROOT / "SECTION5_PROTOCOL_v2_FROZEN_A11.md"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
assert "integrated through Amendment A11" in P.read_text(encoding="utf-8"); assert not V2.exists(); shutil.copyfile(P, V2); V2.with_suffix(".sha256").write_text(f"{sha(V2)}  {V2.name}\n", encoding="ascii")
t = P.read_text(encoding="utf-8"); now = datetime.datetime.now(datetime.timezone.utc)
cl = json.loads((ROOT / "section5" / "results" / "contamination_list.json").read_text()); sch = json.loads((ROOT / "section5" / "results" / "h1c_schedule_times.json").read_text())


def rep(a, b):
    global t; assert t.count(a) == 1, a[:70]; t = t.replace(a, b)


rep("(integrated through Amendment A11)", "(integrated through Amendment A12)")
t = re.sub(r"Re-frozen with A11 \S+ UTC \(\S+ New York; first frozen through A10 at 2026-11-03T21:42:23 UTC\)", f"Re-frozen with A12 {now.isoformat()} UTC ({now.astimezone(ZoneInfo('America/New_York')).isoformat()} New York; first frozen through A10 at 2026-11-03T21:42:23 UTC, re-frozen with A11 at 2026-11-03T21:56:11 UTC)", t, count=1)
rep("Amendments A6 to A11. The previous frozen text (through A10) is preserved unchanged as `SECTION5_PROTOCOL_v1_FROZEN_A10.md`", "Amendments A6 to A12. The previous frozen texts are preserved unchanged: through A10 as `SECTION5_PROTOCOL_v1_FROZEN_A10.md`, through A11 as `SECTION5_PROTOCOL_v2_FROZEN_A11.md`")
rep("\n\nSupporting records", "\n| A12 | `AMENDMENT_A12.md` | audit findings 6, 7, 9, 14, 15 fixed; H1(c) schedule times; machinery rerun | `%s` |\n\nSupporting records" % sha(ROOT / "AMENDMENT_A12.md"))
rep("EM 3 starts, 200 iterations, tol 1e-4, variance floor 1e-6.", "EM 3 starts, 200 iterations, tol 1e-4 (absolute change of the total training log-likelihood in nats, the same for every model; fits that reach the 200 cap are reported; A12 finding 6), variance floor 1e-6.")
rep("old state = argmax at updates 1-2 and at each alarm;", "old state = argmax at updates 1-2 and at each alarm (not re-based inside the refractory period; A12 finding 7);")
rep("Unconfirmed by the close: dropped and counted.", "Unconfirmed by the close: dropped and counted (a candidate run still open at the close; A12 finding 15).")
rep("tau on the 11:05-14:30 grid (<= 14:00 for sandwiches);", "tau on the 11:05-14:30 grid (grid slots 94-299) for permanent breaks and null splices, and for sandwiches availability <= 14:00 with the first bar after the sandwich inside the session (slot <= 269 for 30 and 60 minutes, <= 264 for 120 minutes) (A12 finding 9);")
rep("y = share of break splices with a confirmed alarm within 60 min after tau;", "y = share of break splices with a confirmed alarm within 60 min after tau whose first run update (T_d; BOCPD: the drop update) is available strictly after tau (A12 finding 14);")
rep("(read from its federalreserve.gov page; meetings without a stated time are excluded; A11 item 3)", "(stated on its federalreserve.gov statement page or press-conference page, or the documented schedule 14:15 before April 2011 and 14:00 from 2013, Lucca and Moench 2015; meetings with no source are excluded; A11 item 3, A12 item 2)")
a = t.index("28 folds confirmatory. H1(c) events"); b = t.index("H1(c) is secondary and has low power with 16 events.") + len("H1(c) is secondary and has low power with 16 events.")
t = t[:a] + f"28 folds confirmatory. H1(c) events (A12 item 2): of {len(sch['meetings'])} listed meetings, {sch['counts']['time']} have a usable release time ({sch['counts']['by_basis']}) and {sch['counts']['excluded']} (non-press-conference days from April 2011 to December 2012) are excluded as ambiguous; the Fed press-conference page for 2012-01-25 states 12:20, not the 12:30 of the general rule, and is used as stated. Before April 2011 no Fed page states the time; the 14:15 of Lucca and Moench ('at, or a few minutes after, 2:15 pm') is used, so the window start can be a few minutes late. {cl['n_h1c_events']} eligible events remain in uncontaminated test segments (`section5/results/h1c_schedule_times.json`, `contamination_list.json`)." + t[b:]
rep("The A10 machinery check tuned the HSMM over {2, 3, 4}; its HSMM tuning results are not valid under 5.4 and the check is to be repeated before it is cited for the HSMM.", "The A10 machinery check tuned the HSMM over {2, 3, 4}; it was repeated under A12 with K in {2, 3} (`A12_MACHINERY_REPORT.md`).")
a = t.index("## Open items"); t = t[:a] + """## Open items (not decided; each needs an amendment before the step that depends on it)

- Cold audit findings (`COLD_AUDIT_STATUS.md`, updated with A12): findings 6, 7, 9, 14 and 15 are fixed in A12. Still open: 10, 12, 13, 16-21 and the open part of 22; disclosed: 1 (residual), 2, 4, 5, 8.
- The era-level calibration (A11 item 1) is implemented and unit-tested for the split; it has not been run on data.
- Results computed under the earlier detector and splice code (A6/A7 pilots, A8 gates, A8.3, A8.4, the A10 machinery check) are records of that code; the R=1 gate (5.15) has not been rerun under the A12 code.
- H1(c) before April 2011 rests on the documented schedule alone (no Fed page states those times).
"""
P.write_text(t, encoding="utf-8"); P.with_suffix(".sha256").write_text(f"{sha(P)}  {P.name}\n", encoding="ascii"); print("protocol", sha(P))
