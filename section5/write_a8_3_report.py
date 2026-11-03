#!/usr/bin/env python3
"""Writes A8_3_GATE_CHARACTERIZATION.md (+ sidecar) from the a8_3 jsonl files, applying the pre-stated rule of AMENDMENT_A8_3.md."""
import json, hashlib, datetime
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent; RES = ROOT / "section5" / "results"
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
import sys; sys.path.insert(0, str(ROOT / "section5")); import s5_h1c as H
rd = lambda n: [json.loads(l) for l in (RES / n).read_text().splitlines()]
leg, raw = rd("a8_3_gate_LEGACY29.jsonl"), rd("a8_3_gate_RAW3.jsonl"); s777 = {"LEGACY": json.loads((RES / "a8_2_gate_LEGACY29_seed777.json").read_text()), "RAW": json.loads((RES / "a8_2_gate_RAW3_seed777.json").read_text())}
dets = list(leg[0]["detectors"]); rate = lambda rs, k: sum(r["detectors"][k]["outside"] for r in rs)
L = ["# A8.3 gate characterization (P1 vs P2, 20 new seeds)", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Rule: `AMENDMENT_A8_3.md` (sha256 `{sha(ROOT / 'AMENDMENT_A8_3.md')}`). Seeds 1001-1020; validation sessions only; no test-segment scoring.", "",
     f"Stable validation days: LEGACY 29 = {leg[0]['stable_days']}, RAW 3 = {raw[0]['stable_days']}. Seeds run: LEGACY {len(leg)}, RAW {len(raw)}.", "",
     "| Detector | LEGACY fails | LEGACY rate [Wilson 95%] | RAW fails | RAW rate [Wilson 95%] | Floor 2x max(RAW, .05) | Within 2x | seed 777 LEGACY / RAW outside |", "|---|---|---|---|---|---|---|---|"]
far = []
for k in dets:
    a, b = rate(leg, k), rate(raw, k); ra, rb = a / len(leg), b / len(raw); lim = 2 * max(rb, 0.05); ok = ra <= lim + 1e-12; far += [] if ok else [k]
    wa, wb = H.wilson(a, len(leg)), H.wilson(b, len(raw))
    L.append(f"| {k} | {a}/{len(leg)} | {ra:.2f} [{wa[0]:.2f}, {wa[1]:.2f}] | {b}/{len(raw)} | {rb:.2f} [{wb[0]:.2f}, {wb[1]:.2f}] | {lim:.2f} | {'yes' if ok else '**NO**'} | {not s777['LEGACY']['detectors'][k]['inside']} / {not s777['RAW']['detectors'][k]['inside']} |")
pa, pb = sum(rate(leg, k) for k in dets) / (8 * len(leg)), sum(rate(raw, k) for k in dets) / (8 * len(raw))
anyfail = lambda rs: sum(any(v["outside"] for v in r["detectors"].values()) for r in rs)
L += ["", f"Pooled over the 8 detectors (information): LEGACY {pa:.3f}, RAW {pb:.3f}. Seeds with at least one detector outside: LEGACY {anyfail(leg)}/{len(leg)}, RAW {anyfail(raw)}/{len(raw)}.", "",
      "## Pre-stated rule result", "", ("All 8 detectors are within 2x: the LEGACY 29 seed-777 failure is documented as chance." if not far else f"Detectors far higher on LEGACY (> 2x max(RAW, .05)): {', '.join(far)}. To be investigated before any main run (separate dated step).")]
OUT = ROOT / "A8_3_GATE_CHARACTERIZATION.md"; OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("\n".join(L[4:]))
