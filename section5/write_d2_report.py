#!/usr/bin/env python3
"""Writes D2_REPORT.md (+ sidecar hash) from section5/results/d2_results.json. Facts only. Refuses to overwrite."""
import json, hashlib, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = ROOT / "D2_REPORT.md"
assert not OUT.exists(), "exists; never overwrite"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
r = json.loads((RES / "d2_results.json").read_text()); st = json.loads((RES / "d2_stable_days.json").read_text())
FAMS = ["gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"]; SETS = ["base", "f3", "f6"]; THS = [0.5, 0.7, 0.9, 0.95, 0.99, 0.999, 0.9999]
SIZES = [1.5, 2, 3, 5, 10]; DURS = ["None", "30", "60", "120"]
n_stable = len(r["stable_days"])
L = ["# Diagnostic D2 report", "", "**RAW fold 3, validation sessions only; frozen pilot detectors (K=3, lambda=39, 1 start, seed 0, raw 5-min return) with fixed a-priori feature sets; no selection; no evaluation data; the fold's test segment is not used.**", "",
     f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC.", "",
     "## Design", "",
     f"- Stable days (defined in `s5_d2_stable.py` before any detector ran): deseasonalised 1-min variance (r^2 / median r^2 of the same slot over the previous 20 sessions, >= 10 finite) with first-half / second-half ratio in [0.8, 1.25] and no hourly block mean above 2x the median block mean. {n_stable} of 58 validation sessions qualify: {r['stable_days']}.",
     f"- Null: {r['n_null']} splices of two distinct stable days of the same session-volatility tercile (terciles over the {n_stable} stable days), tau drawn from the 11:05-14:30 grid. Only {n_stable} distinct days exist, so pairs and null sessions repeat; the Wilson 95% intervals below treat the {r['n_null']} null sessions as independent and are therefore too narrow.",
     f"- Breaks: stable day A until tau, then stable day B whose 1-min returns, ranges and price excursions are scaled by f so that the deseasonalised variance after tau equals R x (up) or 1/R x (down) the deseasonalised variance of A before tau (R = 1.5, 2, 3, 5, 10), volume unchanged; permanent (to the close) or a sandwich of 30 / 60 / 120 min after which A's own path continues (price-continuous at both seams); tau <= 14:00 so the 120-min sandwich fits. {r['n_cell']} splices per (size, direction, duration) cell = {r['n_cell']*40} breaks. Features recomputed from the spliced series (fast path, equal to the 21-session recomputation).",
     "- Hit = confirmed (T_c) within 60 min of tau; for sandwiches it counts even if the sandwich has ended before T_c. Delay = T_c - tau, median over hits.",
     "- Construction checks on 8 real panels (price at g unchanged, return across tau = f x B's return, deseasonalised variance ratio = target, sandwich tail continuous): " + ("all PASS" if all(all(v for k, v in c.items() if k != "cell") for c in r["construction_checks"]) else "FAIL: " + json.dumps(r["construction_checks"])) + ".",
     "- Natural scaling needed (f^2 quantiles 10/50/90% by cell, how far B's own variance is from the target): range of medians over cells " + f"{min(v[1] for v in r['f2_quantiles'].values()):.2f}-{max(v[1] for v in r['f2_quantiles'].values()):.2f}.", "",
     "- Realized deseasonalised variance ratio over the FIRST 60 min after tau (median over splices), by size and duration, up direction: " + "; ".join(f"R={R}: " + ", ".join(f"{d_}:{r['realized_first60_ratio_median'][f'{R}|up|{d_}']}" for d_ in DURS) for R in SIZES) + ". Down direction: " + "; ".join(f"R={R}: " + ", ".join(f"{d_}:{r['realized_first60_ratio_median'][f'{R}|down|{d_}']}" for d_ in DURS) for R in SIZES) + ". The target ratio is enforced over the whole post-tau segment (to the close for permanent), so the first-60-min ratio differs by duration.", "",
     "## A. False alarms per 20 stable-day null sessions (95% Wilson CI), by detector and threshold", "",
     "| detector | set | " + " | ".join(str(t) for t in THS) + " |", "|---|---|" + "---|" * len(THS)]
for fam in FAMS:
    for s in SETS:
        cells = []
        for t in THS:
            e = r["fa"][f"{fam}|{s}|{t}"]["stable_null"]; cells.append(f"{e['per20']:.1f} [{e['ci95_per20'][0]:.1f}-{e['ci95_per20'][1]:.1f}]")
        L.append(f"| {fam} | {s} | " + " | ".join(cells) + " |")
L += ["", "Target: <= 1 per 20.", "", "## B. Attribution: old tercile test vs stable-day test, same detectors", "",
      "FA = false alarms per 20 null sessions (old null = the earlier tercile-matched null of any day; stable null = this report). Hit: old = the earlier tercile breaks (100, both directions, permanent); new = pooled over all D2 breaks with permanent duration (sizes 1.5-10, both directions, 240 splices); new>=3x = same restricted to R >= 3 (144 splices).", "",
      "| detector | set | thr | FA old null | FA stable null | hit old tercile | hit D2 permanent (all sizes) | hit D2 permanent (R>=3) |", "|---|---|---|---|---|---|---|---|"]


def pooled(hit, filt):
    num = den = 0
    for k, v in hit.items():
        if k == "old_break": continue
        R, dr, du = k.split("|")
        if filt(float(R), dr, du): num += v["n_hits"]; den += v["n"]
    return num / den if den else float("nan")


for fam in FAMS:
    for s in SETS:
        for t in (0.99, 0.999):
            key = f"{fam}|{s}|{t}"; fa = r["fa"][key]; h = r["hit"][key]
            L.append(f"| {fam} | {s} | {t} | {fa['old_null']['per20']:.1f} | {fa['stable_null']['per20']:.1f} | {h['old_break']['hit']:.2f} | {pooled(h, lambda R, dr, du: du == 'None'):.2f} | {pooled(h, lambda R, dr, du: du == 'None' and R >= 3):.2f} |")
L += ["", "## C. Hit rate (median delay of hits, min) by size, direction and duration", "",
      "Cells: hit rate (median delay); n = " + str(r["n_cell"]) + " per cell. Columns: direction up (calm to stressed) then down, each permanent / 30 / 60 / 120-min sandwich. '-' = no hit.", ""]
for fam, s, t in [(f, "f3", 0.999) for f in FAMS] + [(f, "base", 0.9) for f in FAMS]:
    fa = r["fa"][f"{fam}|{s}|{t}"]["stable_null"]
    L += [f"### {fam} / {s} / threshold {t} (stable-null FA per 20: {fa['per20']:.1f})", "", "| R | " + " | ".join(f"up {d}" for d in ("perm", "30", "60", "120")) + " | " + " | ".join(f"down {d}" for d in ("perm", "30", "60", "120")) + " |", "|---|" + "---|" * 8]
    h = r["hit"][f"{fam}|{s}|{t}"]
    for R in SIZES:
        row = []
        for dr in ("up", "down"):
            for du in DURS:
                e = h[f"{R}|{dr}|{du}"]; row.append(f"{e['hit']:.2f} ({e['median_delay_hits']:.0f})" if e["median_delay_hits"] is not None else f"{e['hit']:.2f} (-)")
        L.append(f"| {R} | " + " | ".join(row) + " |")
    L.append("")
L += ["## Files", "", "| File | SHA-256 |", "|---|---|"]
for f in ("s5_d2_stable.py", "s5_d2.py", "s5_fast.py", "write_d2_report.py"): L.append(f"| section5/{f} | `{sha(HERE / f)}` |")
for f in ("d2_stable_days.json", "d2_results.json"): L.append(f"| section5/results/{f} | `{sha(RES / f)}` |")
OUT.write_bytes(("\n".join(L) + "\n").encode("utf-8")); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii")
print(OUT.read_text(encoding="utf-8")[:2500])
