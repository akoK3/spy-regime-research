#!/usr/bin/env python3
"""Writes D4_REPORT.md (+ sidecar hash) from section5/results/d4_results.json (two threshold-selection rules computed from the same fits)."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "D4_REPORT.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
ALL = json.loads((RES / "d4_results.json").read_text())
DT = ["gaussian", "student_t5"]; RS = [2, 3, 5, 10]; FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]
names = sorted({k.split("|", 3)[3] for k in ALL}); fam_of = lambda n: n.split("|")[0]
fm = lambda x: "-" if x is None else f"{x:.0f}"


def section(rule, title, full):
    r = {k.split("|", 1)[1]: v for k, v in ALL.items() if k.startswith(rule + "|")}
    g = lambda d, R, n: r[f"{d}|R{R}|{n}"]
    passes = lambda d, n: g(d, 10, n)["hit_up"] >= 0.8 and g(d, 10, n)["hit_down"] >= 0.8 and g(d, 10, n)["test_fa"] <= 0.10 and g(d, 10, n)["calibration_feasible"]
    score = lambda d, n: min(g(d, 10, n)["hit_up"], g(d, 10, n)["hit_down"]) if g(d, 10, n)["test_fa"] <= 0.10 and g(d, 10, n)["calibration_feasible"] else -1 + min(g(d, 10, n)["hit_up"], g(d, 10, n)["hit_down"]) * 0.01
    L = [f"## {title}", "", "### Verdict per family (pass: R=10 hit >= 0.80 up and down, test FA <= 0.10, feasible calibration)", ""]
    fam_rows = []
    for fam in FAMS:
        nm = [n for n in names if fam_of(n) == fam]; s = []
        for d in DT:
            ps = [n for n in nm if passes(d, n)]; best = max(nm, key=lambda n: score(d, n)); b = g(d, 10, best); fam_rows.append((fam, d, ps, best, b))
            s.append(f"{d}: " + (f"**PASS** ({len(ps)} of {len(nm)} configurations; {', '.join(ps[:3])}{' ...' if len(ps) > 3 else ''})" if ps else f"**FAIL** (best {best}: hit up {b['hit_up']:.2f} / down {b['hit_down']:.2f}, test FA {b['test_fa']:.2f}{'' if b['calibration_feasible'] else ', infeasible calibration'})"))
        L.append(f"- **{fam}**: " + "; ".join(s))
    L += ["", "### R = 10, every configuration: threshold, test FA (share of null sessions), alarms per 20 null sessions, hit up / down, median delay up / down (min)", "",
          "| configuration | thr (G) | FA (G) | per20 (G) | hit up/down (G) | delay (G) | pass (G) | thr (t5) | FA (t5) | per20 (t5) | hit up/down (t5) | delay (t5) | pass (t5) |", "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for n in names:
        row = [n]
        for d in DT:
            b = g(d, 10, n); row += [f"{b['threshold']}{'' if b['calibration_feasible'] else ' (INF)'}", f"{b['test_fa']:.2f}", f"{b['test_alarms_per20']:.1f}", f"{b['hit_up']:.2f} / {b['hit_down']:.2f}", f"{fm(b['delay_up_min'])} / {fm(b['delay_down_min'])}", "PASS" if passes(d, n) else "fail"]
        L.append("| " + " | ".join(row) + " |")
    if full:
        L += ["", "### Power curves 2-10x, best configuration per family (best = highest min(hit up, hit down) at R=10 among configurations with test FA <= 0.10 and a feasible calibration; if none qualifies, the highest min hit overall)", "",
              "Cells: hit up / hit down (test FA). Thresholds were calibrated separately for each R.", "", "| family | data | configuration | R=2 | R=3 | R=5 | R=10 |", "|---|---|---|---|---|---|---|"]
        for fam, d, ps, best, b in fam_rows:
            L.append(f"| {fam} | {d} | {best} | " + " | ".join(f"{g(d,R,best)['hit_up']:.2f} / {g(d,R,best)['hit_down']:.2f} ({g(d,R,best)['test_fa']:.2f})" for R in RS) + " |")
        L += ["", "### Power curves, every configuration (hit up / hit down at the frozen threshold, test FA in brackets)", "", "| data | configuration | R=2 | R=3 | R=5 | R=10 |", "|---|---|---|---|---|---|"]
        for d in DT:
            for n in names:
                L.append(f"| {d} | {n} | " + " | ".join(f"{g(d,R,n)['hit_up']:.2f} / {g(d,R,n)['hit_down']:.2f} ({g(d,R,n)['test_fa']:.2f})" for R in RS) + " |")
    inf = [k for k, v in r.items() if not v["calibration_feasible"]]
    L += ["", f"Cells with no feasible calibration threshold (recorded, not excluded; the strictest grid value was used): {len(inf)} of {len(r)}" + (": " + ", ".join(inf[:10]) + (" ..." if len(inf) > 10 else "") if inf else "."), ""]
    return L


L = ["# Diagnostic D4 report (pure synthetic power study)", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Frozen detector code; D4 event rules; no market data.", "",
     "## Design", "",
     "- Sessions: 78 updates of iid noise (Gaussian, or Student-t df 5 scaled to unit variance); variance ratio R in 2, 3, 5, 10 at a random update j in 20-60; up = sd 1 to sqrt(R), down = sd sqrt(R) to 1. Per cell: 500 null, 500 up and 500 down test sessions. Separate seeds for training (189 sessions at the same R: 40% calm, 20% stressed, 20% up, 20% down), 500 calibration nulls, 500 + 500 calibration breaks and the test sessions.",
     "- One model per (family, K or lambda, data type, R) fitted on the training seeds (1 start, seed 0); inputs z-scored with the pooled training mean/sd. The model therefore knows R (favourable to the detectors; my choice).",
     "- HMM/HSMM rule (new): alarm when P(old state) < 1 - threshold for 3 consecutive real updates; old state = argmax at updates 1-2, then at each alarm; 30-min refractory and silent first 2 updates as in the frozen code.",
     "- BOCPD alarms: (a) P(changepoint within 3 updates) = P(run length <= 2): rising edge >= threshold, held 3 updates with no new alarm (frozen `detect_bocpd`); (b) the most likely run length drops by >= m between consecutive updates (m = the threshold: 1, 2, 3, 5, 8, 12, 20, 30) and holds: at the k-th update after the drop it is <= low + k, for 3 updates; (c) P(run length < 6), same edge/hold logic as (a). lambda = 12, 39, 78; prior (0, 1, 1, 1).",
     "- Threshold grids: HMM/HSMM 0.5-0.9999; BOCPD (a), (c) 0.01-0.999; (b) drop 1-30. Two selection rules were computed from the same fits and are both reported: run 1 'smallest' = smallest grid value with calibration-null session false-alarm share <= 0.10; run 2 'maxhit' = among grid values with calibration false-alarm share <= 0.10, the one with the highest calibration hit rate, ties to the smallest. Run 2 was added after run 1 showed the degenerate BOCPD (a)/(c) calibrations (below). Run 1 as first executed is `d4_run1_as_first_executed.json`; the 'smallest' rule reproduces it exactly.",
     "- Hit = confirmed alarm (T_c) within 12 updates after the break (T_c availability in [tau, tau + 60 min], tau = availability of update j-1); delay = T_c - tau in minutes (median over hits). FA = share of the 500 test null sessions with any confirmed alarm; 'per20' = confirmed alarms per 20 null sessions.",
     "- Pass mark (yours): hit >= 0.80 for R = 10 in both directions at test FA <= 0.10.", "",
     "## Failure recorded in run 1", "",
     "- BOCPD (a) and (c) were calibrated to threshold 0.01 and then produced no alarms at all (FA 0.00, hit 0.00) in every cell: P(run length <= 2) never falls below 0.01 (its prior floor is about 1-(1-1/lambda)^3 = 7-22%), so the rising-edge alarm cannot occur and 'smallest threshold with FA <= 10%' selects this dead zone. The false-alarm constraint is not monotone in the threshold for these alarms. This is a threshold-selection defect, not evidence about BOCPD; run 2 selects on calibration hit rate instead.", ""]
L += section("maxhit", "Run 2 (threshold = highest calibration hit rate subject to calibration FA <= 0.10)", True)
L += section("smallest", "Run 1 (threshold = smallest value with calibration FA <= 0.10)", False)
L += ["## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_d4.py", "s5_events.py", "s5_models.py", "write_d4_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("d4_results.json", "d4_run1_as_first_executed.json"): L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print("\n".join(L[L.index('### Verdict per family (pass: R=10 hit >= 0.80 up and down, test FA <= 0.10, feasible calibration)'):][:9]))
