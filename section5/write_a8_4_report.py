#!/usr/bin/env python3
"""A8.4: multiplicity (permutation + independent binomial) and leave-one-day-out summary; applies the pre-stated decision of AMENDMENT_A8_4.md. Writes A8_4_INVESTIGATION.md (+ sidecar)."""
import json, hashlib, datetime, sys
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; RES = ROOT / "section5" / "results"; sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rd = lambda n: [json.loads(l) for l in (RES / n).read_text().splitlines()]
leg, raw = rd("a8_3_gate_LEGACY29.jsonl"), rd("a8_3_gate_RAW3.jsonl"); dets = list(leg[0]["detectors"])
M = np.array([[r["detectors"][k]["outside"] for k in dets] for r in leg + raw], int); nL = len(leg)
def n_exceed(a, b):                                    # a, b: seeds x detectors flags; LEGACY, RAW
    ra, rb = a.mean(0), b.mean(0); return int((ra > 2 * np.maximum(rb, 0.05) + 1e-12).sum())
obs = n_exceed(M[:nL], M[nL:]); rng = np.random.default_rng(84); NP_ = 10000; cnt = np.zeros(9, int)
for _ in range(NP_):
    p = rng.permutation(len(M)); cnt[n_exceed(M[p[:nL]], M[p[nL:]])] += 1
P1 = float(cnt[2:].sum() / NP_)
pr = M.mean(0); NS = 100000; X = rng.binomial(20, pr, (NS, 8)) / 20; Y = rng.binomial(20, pr, (NS, 8)) / 20; Pb = float(((X > 2 * np.maximum(Y, 0.05) + 1e-12).sum(1) >= 2).mean())
L = ["# A8.4 investigation", "", f"Written {datetime.datetime.now(datetime.timezone.utc).isoformat()} UTC. Rule: `AMENDMENT_A8_4.md` (sha256 `{sha(ROOT / 'AMENDMENT_A8_4.md')}`). Validation sessions only; no test-segment scoring.", "",
     "## 1. Multiplicity", "", f"- Observed detectors above 2x RAW: {obs} of 8.", f"- Permutation (primary, 10,000 re-splits of the 40 seed records, seed 84): P(at least 2 exceed) = **{P1:.3f}**. Distribution of the count: " + ", ".join(f"{i}: {c/NP_:.3f}" for i, c in enumerate(cnt) if c) + ".",
     f"- Independent binomial (information, 100,000 draws): P(at least 2 exceed) = {Pb:.3f}.", ""]
loo_f = RES / "a8_4_loo_LEGACY29.jsonl"; dec_loo = None
if loo_f.exists():
    lo = rd("a8_4_loo_LEGACY29.jsonl"); days = lo[0]["days"]; n = len(lo)
    # validity: full-day outcomes equal A8.3
    base = {r["seed"]: r for r in leg}; mism = sum(r["results"]["None"][k]["outside"] != base[r["seed"]]["detectors"][k]["outside"] for r in lo for k in dets)
    rate_raw = {k: sum(r["detectors"][k]["outside"] for r in raw) / len(raw) for k in dets}; lim = {k: 2 * max(rate_raw[k], .05) for k in dets}
    L += ["## 2. Leave-one-day-out (LEGACY 29, seeds 1001-1020)", "", f"- Seeds completed: {n}. Validity check, full-day outcomes versus A8.3 file: {mism} mismatches over {n*8} (must be 0, else void).", "",
          "| Day removed | " + " | ".join(dets) + " | exceeds | clears all |", "|---" * (len(dets) + 3) + "|"]
    drivers = []
    for dr in ["None"] + [str(x) for x in days]:
        c = [sum(r["results"][dr][k]["outside"] for r in lo) for k in dets]; ex = [k for k, v in zip(dets, c) if v / n > lim[k] + 1e-12]
        L.append(f"| {'(none)' if dr == 'None' else 'session ' + dr} | " + " | ".join(str(v) for v in c) + f" | {len(ex)} | {'yes' if not ex else 'no'} |")
        if dr != "None" and not ex: drivers.append(dr)
    dec_loo = (len(drivers) == 1) and mism == 0
    L += ["", f"- Days whose removal clears all detectors: {len(drivers)} ({', '.join(drivers) if drivers else 'none'}). Single driving day: **{'yes' if len(drivers) == 1 else 'no'}**" + ("" if mism == 0 else " (VOID: validity check failed)") + ".", ""]
dec = (P1 > 0.10) or bool(dec_loo)
L += ["## Decision (pre-stated)", "", f"- P1 = {P1:.3f} ({'above' if P1 > .10 else 'not above'} 10%); single driving day: {dec_loo}.", f"- **{'Document and proceed' if dec else 'Stop and report'}.**"]
OUT = ROOT / "A8_4_INVESTIGATION.md"; OUT.write_text("\n".join(L) + "\n", encoding="utf-8"); OUT.with_suffix(".sha256").write_text(f"{sha(OUT)}  {OUT.name}\n", encoding="ascii"); print("\n".join(L[4:]))
