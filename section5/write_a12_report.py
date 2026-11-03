#!/usr/bin/env python3
"""Writes A12_MACHINERY_REPORT.md (+ sidecar) from the a12 machinery results (RAW 3, LEGACY 29) and compares with the A10 run. Facts only."""
import json, hashlib, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; RES = ROOT / "section5" / "results"; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
R = {k: json.loads((RES / f"a12_machinery_{k}.json").read_text()) for k in ("RAW3", "LEGACY29")}; O = {k: json.loads((RES / f"a10_machinery_{k}.json").read_text()) for k in R}
L = ["# A12 machinery check (contaminated folds only; rerun under the A12 code)", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Rule: `AMENDMENT_A12.md` (sha256 `{sha(ROOT / 'AMENDMENT_A12.md')}`). Folds RAW 3 and LEGACY 29 only (both on the contamination list); one fold per call; no clean fold, no evaluation data. Statistics are not evaluable with one fold; no result enters any protocol decision. A10 figures are the earlier run (old EM tolerance, old event and hit rules, old tau range, HSMM K 2-4).", "",
     "| | RAW 3 (A12) | RAW 3 (A10) | LEGACY 29 (A12) | LEGACY 29 (A10) |", "|---|---|---|---|---|"]
def row(n, f): L.append(f"| {n} | {f(R['RAW3'])} | {f(O['RAW3'])} | {f(R['LEGACY29'])} | {f(O['LEGACY29'])} |")
row("Failures", lambda r: len(r["failures"])); row("Total run incl. resume and freeze step (min)", lambda r: r["total_minutes"]); row("Peak process memory (MB)", lambda r: int(r["peak_memory_mb"]))
row("Min free system memory (MB)", lambda r: int(r["min_free_system_mb"])); row("Selection objective calls / seconds", lambda r: f"{r['backend_calls']['objective_calls']} / {r['backend_seconds']['objective_calls']}")
row("Scoring incl. splice build (s)", lambda r: r["backend_seconds"]["score"]); row("Threshold bisection (s)", lambda r: r["backend_seconds"]["final_thresholds"])
row("Resume: second call computed / reused", lambda r: f"{r['resume']['second']['misses']} / {r['resume']['second']['hits']}"); row("Non-finite outputs", lambda r: len(r["non_finite_outputs"])); row("H1(a) skipped folds", lambda r: sum(len(v) for v in r["skipped_h1a"].values()))
L += ["", "EM fits (A12 finding 6; absolute tolerance 1e-4 nats, cap 200 iterations):", "", "| Fold | Models fitted | Starts | Starts at the cap | Median iterations | By family (starts / at cap) |", "|---|---|---|---|---|---|"]
for k, r in R.items():
    e = r["em_fits"]; L.append(f"| {k} | {e['n_models']} | {e['n_starts']} | {e['n_starts_reaching_cap']} | {e['iterations_median']} | " + "; ".join(f"{f} {v['starts']} / {v['at_cap']}" for f, v in e["by_family"].items()) + " |")
L += ["", "Selected setups (descriptive; validation QLIKE of the tuned model against the return-only model):", "", "| Fold | Family | Features | Params | val QLIKE | return-only QLIKE |", "|---|---|---|---|---|---|"]
for k, r in R.items():
    for f, s in r["setups"].items(): L.append(f"| {k} | {f} | {', '.join(s['features']) or '-'} | {s['params']} | {s['val_qlike']:.4f} | {s['base_qlike']:.4f} |")
L += ["", "Open candidate share at the close (finding 15), at the bisected threshold on the validation sessions (final-setup models): see `final_thresholds` records in the run summaries; the HSMM grid is K in {2, 3} (A11).", "Files: `section5/results/a12_machinery_RAW3.json`, `a12_machinery_LEGACY29.json`, logs."]
OUT = ROOT / "A12_MACHINERY_REPORT.md"; OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("\n".join(L[4:22]))
