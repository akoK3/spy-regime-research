"""Diagnostic (validation splices only): why no threshold met 1 false alarm per 20 null sessions for the fixed 3-feature models."""
import sys, json, numpy as np
sys.path.insert(0, '.')
import s5_lib as L, s5_eval as V, s5_pilot as P
primary, _, _ = L.pools(); cols = primary
d = L.load_era("RAW", cols + ["lee_mykland_approx60"]); seg = L.fold_segments(d, "RAW", 3)
rows = {k: [L.session_grid(d, i, cols) for i in seg[k]] for k in ("train", "val")}
names = [L.RET_NAME] + cols; prep = L.Prep().fit(np.vstack([r["X"] for r in rows["train"]]), names)
ck = L.Checkpoint(L.HERE / "cache" / "pilot_ckpt"); rng = np.random.default_rng(P.SEED + 100)
vb, vn = V.sample_pairs(d, seg["val"], 24, 24, rng)
out = {}
for var, sub in (("base", []), ("f3", P.FIXED3)):
    idx = [prep.keep.index(L.RET_NAME)] + [prep.keep.index(n) for n in sub]
    mk = lambda r: L.build_sequence(dict(r, X=prep.transform(r["X"])[:, idx]))
    tr = [mk(r) for r in rows["train"]]; m = V.make_model("gaussian_hmm", K=3, starts=1, seed=0); m.fit(L.pad(tr, len(idx)))
    nulls = [mk(ck.run(f"splice_row|RAW|3|{s['iA']}|{s['iB']}|{s['g']}", None)) for s in vn]
    res = V.run_filter("gaussian_hmm", m, nulls, len(idx))
    sc = V.score_splices("gaussian_hmm", res, nulls, None, False, V.STATE_THR)
    seam = []
    for q, r, s in zip(nulls, res, vn):
        ev = V.events_for("gaussian_hmm", r, q, 0.99)[0]
        seam += [int(q["slots"][e["i_d"]] - s["g"]) for e in ev]
    out[var] = dict(fa_by_thr={str(k): v["fa_rate"] for k, v in sc.items()}, T_d_slot_minus_g_at_0_99=seam)
print(json.dumps(out)); open("results/diag_pilot_fa.json", "w").write(json.dumps(out, indent=1))
