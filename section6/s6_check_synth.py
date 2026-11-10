#!/usr/bin/env python3
"""AMENDMENT_A31 rule 4b: acceptance of the synthetic checks, criteria fixed before the run. Reads section6/results/synth_validation_TAG.json; prints each criterion
with its value; writes section6/results/synth_check_TAG.json (written once); exit 0 = all pass, 1 = any fails, 3 = file missing.
  null ("indep", "vol"): each of the six primary tests rejects at 0.05 in <= 0.081 of replicates; the rule 3 control flags each asset in <= 0.081 of replicates.
  effect_h4: H4a and H4b |bias| <= 2 SE of the target and rejection >= 0.80.
  effect_h3: TLT, HYG, gold |bias| <= max(2 SE, 0.10 x target); TLT and gold rejection >= 0.80.
Usage: s6_check_synth.py TAG"""
import sys, json
from pathlib import Path
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
LIM = 0.081


def evaluate(summary):
    rows = []
    def add(name, value, ok): rows.append(dict(criterion=name, value=value, passed=bool(ok)))
    for sc in ("indep", "vol"):
        d = summary[sc]
        for k, t in d["tests"].items(): add(f"{sc}: {k} rejection <= {LIM}", t["reject_raw_0_05"], t["reject_raw_0_05"] <= LIM)
        for a, v in d["filter_control_flag_rate"].items(): add(f"{sc}: A31 rule 3 control flag rate {a} <= {LIM}", v, v <= LIM)
    d = summary["effect_h4"]["tests"]
    for k in ("H4a", "H4b"):
        t = d[k]; add(f"effect_h4: {k} |bias| <= 2 SE", [t["bias"], t["bias_se"]], abs(t["bias"]) <= 2 * t["bias_se"]); add(f"effect_h4: {k} rejection >= 0.80", t["reject_raw_0_05"], t["reject_raw_0_05"] >= 0.80)
    d = summary["effect_h3"]["tests"]
    for a in ("TLT", "HYG", "GOLD"):
        t = d[f"H3_{a}"]; add(f"effect_h3: H3_{a} |bias| <= max(2 SE, 0.10 x target)", [t["bias"], t["bias_se"], t["target_mean"]], abs(t["bias"]) <= max(2 * t["bias_se"], 0.10 * abs(t["target_mean"])))
    for a in ("TLT", "GOLD"): add(f"effect_h3: H3_{a} rejection >= 0.80", d[f"H3_{a}"]["reject_raw_0_05"], d[f"H3_{a}"]["reject_raw_0_05"] >= 0.80)
    return rows


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    tag = sys.argv[1]; f = HERE / "results" / f"synth_validation_{tag}.json"
    if not f.exists(): print(f"missing {f}"); return 3
    rows = evaluate(json.loads(f.read_text(encoding="utf-8"))["summary"])
    for r in rows: print(("PASS " if r["passed"] else "FAIL ") + r["criterion"] + f"  value {r['value']}")
    ok = all(r["passed"] for r in rows); print("A31 rule 4 synthetic checks:", "PASS" if ok else f"FAIL ({sum(not r['passed'] for r in rows)} of {len(rows)} criteria)")
    import s6_run as R, hashlib
    R.write_once(HERE / "results" / f"synth_check_{tag}.json", dict(tag=tag, passed=ok, criteria=rows, synth_sha256=hashlib.sha256(f.read_bytes()).hexdigest(), provenance=R.provenance()))
    return 0 if ok else 1


if __name__ == "__main__": sys.exit(main())
