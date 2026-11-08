#!/usr/bin/env python3
"""O9 L1 fix (user request): 5.11 H1(a) MDE with n_folds = the number of confirmatory folds that have an H1(a) effect (22), instead of 26 as A22 rule 4a wrote; H1(b) keeps 26
(every confirmatory fold has an H1(b) effect). Same s5_stats.mde settings as A22 rule 4a (power 0.8, alpha 0.05/3 and 0.05, nsim 400, nboot 500, seed 0). Reads the MR2 records only;
results/a22/power.json stays unchanged as the A22 record. Writes results/a22/power_observed_n.json."""
import sys, json, datetime
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_a22 as A, s5_stats as ST

def main():
    units = A.mr2_units(); _, _, conf = A.folds_split(); old = json.loads((A.OUT / "power.json").read_text(encoding="utf-8")); res = dict(label="5.11 power with observed fold counts (O9 L1); supersedes the H1(a) MDE of power.json for interpretation", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), h1={})
    for fam in A.FAMILIES:
        res["h1"][fam] = {}
        for comp in ("a", "b"):
            x = np.array([units[("score", f, fam)][comp] for f in conf if units[("score", f, fam)][comp] is not None], float); sd = float(x.std(ddof=1)); n = int(len(x)); r = dict(n_folds=n, mean=float(x.mean()), sd=sd)
            for lab, al in (("alpha_holm_first_0.0167", 0.05 / 3), ("alpha_0.05", 0.05)):
                m = ST.mde(sd, n, alpha=al, power=0.8, nsim=400, nboot=500, seed=0) if sd > 0 else dict(mde_in_sd=None, mde=None, power=None)
                r[lab] = dict(m, observed_over_mde=(r["mean"] / m["mde"]) if m.get("mde") else None, a22_mde_n26=old["h1"][fam]["H1" + comp][lab].get("mde"))
            res["h1"][fam]["H1" + comp] = r
    A.write_json(A.OUT / "power_observed_n.json", res)
    for fam in A.H1F: print(fam, {c: (res["h1"][fam][c]["n_folds"], round(res["h1"][fam][c]["alpha_holm_first_0.0167"]["mde"], 4), round(res["h1"][fam][c]["alpha_holm_first_0.0167"]["a22_mde_n26"], 4), round(res["h1"][fam][c]["alpha_holm_first_0.0167"]["observed_over_mde"], 2)) for c in ("H1a", "H1b")})
    return 0

if __name__ == "__main__": sys.exit(main())
