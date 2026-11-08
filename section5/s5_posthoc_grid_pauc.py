#!/usr/bin/env python3
"""POST HOC, DESCRIPTIVE (user request after the A22 results; not in A22, no test, no verdict): absolute H1(a) partial areas of the feature and the baseline model separately on the
1-min and 5-min grids, for the A22 rule 3g setups (MR2 era final setups, seed 0, 3 starts, MR2 splice specs; families with both grids: Gaussian HMM, Student-t HMM, BOCPD; no 1-min HSMM).
Every unit refits exactly as s5_a22.phase_grid and must reproduce the stored A22 grid effect (pAUC feature - pAUC baseline) exactly, else stop (exit 4).
Reported per grid and family over the 22 confirmatory folds with an H1(a) effect: mean/median pAUC (xmax 0.5 alarms per session) of feature and baseline, and the hit rate y at null
alarm rates 0.1, 0.2 and 0.5 per session. Contamination POST_MAIN_RUN. Usage: s5_posthoc_grid_pauc.py PROTOCOL_SHA256      writes results/posthoc_grid_pauc/."""
import sys, os, gc, json, time, datetime, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "posthoc_grid_pauc"; CK = OUT / "ckpt"; GRIDS = (1, 5); FAMS = ("gaussian_hmm", "student_t_hmm", "bocpd"); XS = (0.1, 0.2, 0.5)


def unit_points(db, fold, fam, st):
    import s5_a6 as A6, s5_h1 as H
    s = db.score(fold, fam, dict(st, val_qlike=None)); eff = H.h1a_fold_effect(s["points_feat"], s["points_base"], s["n_stable_test"], failed=s.get("h1a_failed"))["effect"]
    if eff is None: return dict(effect=None)
    pf, pb = s["points_feat"], s["points_base"]
    return dict(effect=eff, pauc_feature=float(A6.pauc(pf)), pauc_baseline=float(A6.pauc(pb)), y_feature={str(x): float(A6.y_at(pf, x)) for x in XS}, y_baseline={str(x): float(A6.y_at(pb, x)) for x in XS},
                points_feature=pf, points_baseline=pb)


def summarize(recs, conf):
    out = {}
    for g in GRIDS:
        for fam in FAMS:
            u = [recs[(g, f, fam)] for f in conf if recs[(g, f, fam)]["effect"] is not None]; v = lambda k: np.array([x[k] for x in u], float)
            out.setdefault(str(g), {})[fam] = dict(n_folds=len(u), pauc_feature_mean=float(v("pauc_feature").mean()), pauc_baseline_mean=float(v("pauc_baseline").mean()), effect_mean=float(v("effect").mean()),
                pauc_feature_median=float(np.median(v("pauc_feature"))), pauc_baseline_median=float(np.median(v("pauc_baseline"))),
                y_feature_mean={str(x): float(np.mean([r["y_feature"][str(x)] for r in u])) for x in XS}, y_baseline_mean={str(x): float(np.mean([r["y_baseline"][str(x)] for r in u])) for x in XS})
    for fam in FAMS:
        a, b = out["1"][fam], out["5"][fam]
        out.setdefault("change_1_minus_5", {})[fam] = dict(feature=a["pauc_feature_mean"] - b["pauc_feature_mean"], baseline=a["pauc_baseline_mean"] - b["pauc_baseline_mean"], effect=a["effect_mean"] - b["effect_mean"])
    return out


def main():
    import s5_guard as G
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "posthoc_grid_pauc_log.txt"
    try:
        ph = A.guards(sys.argv[1]); _, SeedMain = A._classes(); _, excluded, conf = A.folds_split(); fs = A.final_setups(); tag = dict(A.tag_of(ph, "posthoc_grid_pauc"), script=A.file_sha(__file__)); recs = {}; t0 = time.time()
        A.log(f"posthoc grid pAUC start: grids {GRIDS}, families {FAMS}, {len(conf)} confirmatory folds; POST HOC, descriptive")
        for g in GRIDS:
            with A.Grid(g):
                b = SeedMain(ph, 0, 4242, ctx_fn=A.era_context_grid, dmax=390 // g)
                for k, fold in enumerate(conf, 1):
                    t1 = time.time(); era = fold.split("|")[0]; done = []
                    for fam in FAMS:
                        p = CK / f"g{g}_{A.fkey(fold)}_{fam}.json"; u = A.ck_get(p, tag)
                        if u is None:
                            G.check_unlocked("posthoc grid pAUC"); st = {x: fs[era][fam][x] for x in ("features", "params", "base_params")}; r = A.roundtrip(unit_points(b._b(fold), fold, fam, st))
                            ref = json.loads((A.OUT / "grids" / "ckpt" / f"g{g}_{A.fkey(fold)}_{fam}.json").read_text(encoding="utf-8"))["score"]["a"]
                            if not A.same(r["effect"], ref): raise A.Mismatch(f"g{g} {fold} {fam}: effect {r['effect']!r} != A22 {ref!r}")
                            u = dict(r, grid=g, fold=fold, family=fam, tag=tag); A.write_json(p, u); done.append(fam)
                        recs[(g, fold, fam)] = u
                    if done: A.log(f"posthoc grid {g} {k}/{len(conf)} {fold}: " + ", ".join(f"{f.split('_')[0]} pAUC f/b " + ("NA" if recs[(g, fold, f)]['effect'] is None else f"{recs[(g, fold, f)]['pauc_feature']:.3f}/{recs[(g, fold, f)]['pauc_baseline']:.3f}") for f in FAMS) + f" (A22 effect reproduced); {(time.time() - t1) / 60:.1f} min")
                del b; gc.collect()
        res = dict(label="POST HOC, DESCRIPTIVE: absolute H1(a) pAUC of feature and baseline, 1-min vs 5-min grid (A22 rule 3g setups); not a test, changes no verdict",
                   generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), tag=tag, summary=summarize(recs, conf),
                   per_fold={f"g{g}|{f}|{fam}": {k: v for k, v in recs[(g, f, fam)].items() if k not in ("tag", "points_feature", "points_baseline")} for g in GRIDS for f in conf for fam in FAMS}, hours=(time.time() - t0) / 3600)
        A.write_json(OUT / "posthoc_grid_pauc.json", res); A.log("posthoc grid pAUC DONE: " + json.dumps(res["summary"]["change_1_minus_5"])); return 0
    except A.Mismatch as e: A.log(f"posthoc grid pAUC MISMATCH (stop): {e}"); return 4
    except PermissionError as e: A.log(f"posthoc grid pAUC REFUSED: {e}"); return 3
    except KeyboardInterrupt: return 2
    except BaseException as e:
        A.log(f"posthoc grid pAUC CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): A.log("  | " + l)
        return 1


if __name__ == "__main__":
    sys.exit(main())
