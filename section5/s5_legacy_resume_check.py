"""Checkpoint-recovery check: re-compute 5 splices of chunk 0 (stored by the KILLED run) in a fresh process and compare with the stored rows."""
import sys, json, numpy as np
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_lib as L, s5_fast as F, s5_a6 as A, s5_a7 as B, s5_d2 as D2, s5_d2_stable as S
import s5_legacy_pilot as P
primary, _, _ = L.pools(); cols = primary
d = L.load_era("LEGACY", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "LEGACY", 29); dv = S.des_variance(d)
D2._W.update(d=d, cols=cols, bases=F.load_bases(d, "LEGACY", cols))
sv, _ = S.stable_days(d, seg["val"], dv); st, _ = S.stable_days(d, seg["test"], dv); rng = np.random.default_rng(4242)
spv = A.build_specs(d, dv, sv, rng, A.N_CAL_NULL, A.CAL_CELLS, A.N_CELL); cells = [(R, dr, du) for R in B.SIZES for dr in B.DIRS for du in B.DURS]
spt = A.build_specs(d, dv, st, rng, A.N_NULL, cells, A.N_CELL); specs = spv + spt
stored = P.CK.run(f"splice_chunk|LEGACY|29|0|{len(specs)}", lambda: None)[0]
ok = []
for k in range(5):
    new = D2._work(specs[k]); old = stored[k]
    ok.append(all(np.array_equal(np.asarray(new[f]), np.asarray(old[f]), equal_nan=True) for f in ("X", "avail") if f in new) and new["tau"] == old["tau"])
print("stored-by-killed-run chunk 0 equals fresh recompute for 5 splices:", ok)
json.dump(dict(equal=ok), open(L.HERE / "results" / "legacy_resume_check.json", "w"))
