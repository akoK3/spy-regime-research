#!/usr/bin/env python3
"""Writes A13_REPORT.md (+ sidecar): gate sanity check and machinery timing under the A13 EM tolerance. Facts only."""
import json, hashlib, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; RES = ROOT / "section5" / "results"; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
g = json.loads((RES / "a13_gate_RAW3_seed777.json").read_text()); g0 = json.loads((RES / "a8_2_gate_RAW3_seed777.json").read_text())
m = {t: json.loads((RES / f"{t}_machinery_RAW3.json").read_text()) for t in ("a10", "a12", "a13")}
L = ["# A13 report: gate sanity check and machinery timing (RAW 3 only, contaminated fold)", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Rule: `AMENDMENT_A13.md` (sha256 `{sha(ROOT / 'AMENDMENT_A13.md')}`). Validation sessions for the gate; no clean fold, no evaluation data. No result enters any protocol decision.", "",
     "## Gate sanity check (A8.2 rule, seed 777, A13 code)", "", f"Detectors inside: **{sum(v['inside'] for v in g['detectors'].values())} of 8** (A8.2 result on the earlier code: {sum(v['inside'] for v in g0['detectors'].values())} of 8). Stable validation days {g['stable_validation_days']}.", "",
     "| Detector | pAUC P1 | pAUC P2 | P2 day-level 95% CI | Inside (A13) | Inside (A8.2 earlier code) |", "|---|---|---|---|---|---|"]
for k, v in g["detectors"].items(): L.append(f"| {k} | {v['pauc_placebo']:.3f} | {v['pauc_placebo2']:.3f} | [{v['placebo2_ci'][0]:.3f}, {v['placebo2_ci'][1]:.3f}] | {v['inside']} | {g0['detectors'][k]['inside']} |")
L += ["", "## Machinery timing on RAW 3", "", "| | A10 code (EM relative 1e-4, cap 200) | A12 code (absolute 1e-4 nats, cap 200) | A13 code (1e-6 per observation, cap 500) |", "|---|---|---|---|"]
row = lambda n, f: L.append(f"| {n} | {f(m['a10'])} | {f(m['a12'])} | {f(m['a13'])} |")
row("Failures", lambda r: len(r["failures"])); row("Total run incl. resume and freeze step (min)", lambda r: r["total_minutes"]); row("Selection objective calls / seconds", lambda r: f"{r['backend_calls']['objective_calls']} / {r['backend_seconds']['objective_calls']}")
row("Scoring incl. splice build (s)", lambda r: r["backend_seconds"]["score"]); row("Threshold bisection (s)", lambda r: r["backend_seconds"]["final_thresholds"]); row("Peak process memory (MB)", lambda r: int(r["peak_memory_mb"]))
row("Resume: second call computed / reused", lambda r: f"{r['resume']['second']['misses']} / {r['resume']['second']['hits']}"); row("Non-finite outputs", lambda r: len(r["non_finite_outputs"]))
e = m["a13"]["em_fits"]; e12 = m["a12"]["em_fits"]
L += ["", "EM cap hits per family (starts at the cap / starts):", "", "| Family | A12 (cap 200) | A13 (cap 500) |", "|---|---|---|"]
for f in sorted(e["by_family"]): L.append(f"| {f} | {e12['by_family'].get(f, {}).get('at_cap', 0)} / {e12['by_family'].get(f, {}).get('starts', 0)} | {e['by_family'][f]['at_cap']} / {e['by_family'][f]['starts']} |")
L += ["", f"Total: A12 {e12['n_starts_reaching_cap']} of {e12['n_starts']} starts at the cap, median {e12['iterations_median']} iterations; A13 {e['n_starts_reaching_cap']} of {e['n_starts']}, median {e['iterations_median']} iterations.", "",
      "Files: `section5/results/a13_gate_RAW3_seed777.json`, `a13_machinery_RAW3.json`, logs."]
OUT = ROOT / "A13_REPORT.md"; OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("\n".join(L[10:30]))
