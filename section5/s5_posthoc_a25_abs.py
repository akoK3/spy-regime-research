#!/usr/bin/env python3
"""Post hoc (descriptive, requested 2026-11-09; not an amendment, no test, changes no verdict): absolute H1(a) pAUC of the feature and baseline models separately at the A25
LEGACY decision delays 0 / +5 / +10 min (A25 scoring: unshifted data times, hit window 60 - delta). A25 stored only the fold effects (feature - baseline); this recomputes the
two curves with s5_a25_delay.h1a_points_window, unchanged. Also the hit rate at the A7 0.2-per-session null alarm rate is not computed: pAUC only.
Checks: per fold and family, pAUC(feature) - pAUC(baseline) must equal the stored A25 effect at every delay (else exit 4). The 25 confirmatory LEGACY folds; MR2 A17-style models.
Usage: s5_posthoc_a25_abs.py PROTOCOL_SHA256. Output: results/a25/abs_pauc.json (checkpoints results/a25/abs_ckpt/). Exit 0 / 1 crash (resumes) / 3 refused / 4 mismatch."""
import sys, gc, json, time, datetime
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import s5_a22 as A, s5_a25_delay as Z

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "a25"


def unit(db, fold, models, stored):
    import s5_a6 as A6
    sp = db._splices(); n = sp["n_stable"]; out = {}
    for fam in A.FAMILIES:
        if n < 8 or not sp["specs"]: out[fam] = None; continue
        (mf, sf), (mb, sb) = models[fam]["feature"], models[fam]["baseline"]; pf = Z.h1a_points_window(db, fam, mf, sf, Z.DELAYS); pb = Z.h1a_points_window(db, fam, mb, sb, Z.DELAYS); rec = {}
        for dl in Z.DELAYS:
            f, b = float(A6.pauc(pf[dl])), float(A6.pauc(pb[dl]))
            if not A.same(f - b, stored[fam][str(dl)]) and not np.isclose(f - b, stored[fam][str(dl)], rtol=0, atol=1e-12): raise A.Mismatch(f"{fold} {fam} delta {dl}: {f - b!r} != A25 {stored[fam][str(dl)]!r}")
            rec[str(dl)] = dict(feature=f, baseline=b)
        out[fam] = rec
    return out


def run(token):
    import s5_main as MB, s5_guard as G
    ph = Z.guards(token); man = A.a17_manifest(); _, _, conf = A.folds_split(); leg = [f for f in conf if f.startswith("LEGACY|")]; b = MB.MainBackend(ph)
    tag = dict(script=A.file_sha(__file__), a25_script=A.file_sha(HERE / "s5_a25_delay.py"), a25_results=A.file_sha(OUT / "delay_datatime.json"), code_version=G.code_version(), protocol=ph); recs = {}; t00 = time.time()
    for k, fold in enumerate(leg, 1):
        p = OUT / "abs_ckpt" / f"{A.fkey(fold)}.json"; u = A.ck_get(p, tag)
        if u is None:
            G.check_unlocked("A25 absolute pAUC"); t0 = time.time(); models, _ = A.load_models(fold, man); st = json.loads((OUT / "ckpt" / f"{A.fkey(fold)}.json").read_text(encoding="utf-8"))["effects"]
            db = b._b(fold); u = dict(fold=fold, pauc=unit(db, fold, models, st), tag=tag); A.write_json(p, u); del db; gc.collect()
            A.log(f"A25 abs pAUC {k}/{len(leg)} {fold}: f/b 0/5/10 " + ", ".join(f"{f.split('_')[0]} " + "/".join(f"{u['pauc'][f][str(d)]['feature']:.3f}|{u['pauc'][f][str(d)]['baseline']:.3f}" for d in Z.DELAYS) for f in A.H1F if u['pauc'][f]) + f"; {(time.time() - t0) / 60:.1f} min")
        recs[fold] = u
    summ = {}
    for fam in A.FAMILIES:
        ok = [f for f in leg if recs[f]["pauc"][fam]]; summ[fam] = dict(n_folds=len(ok))
        for dl in Z.DELAYS:
            fv = np.array([recs[f]["pauc"][fam][str(dl)]["feature"] for f in ok]); bv = np.array([recs[f]["pauc"][fam][str(dl)]["baseline"] for f in ok])
            summ[fam][str(dl)] = dict(mean_feature=float(fv.mean()), mean_baseline=float(bv.mean()), mean_diff=float((fv - bv).mean()))
    res = dict(label="Post hoc, descriptive: absolute H1(a) pAUC, feature and baseline, A25 delays 0/5/10 (LEGACY confirmatory folds)", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               tag=tag, summary=summ, per_fold={f: recs[f]["pauc"] for f in leg}, hours=(time.time() - t00) / 3600)
    A.write_json(OUT / "abs_pauc.json", res); A.log("A25 abs pAUC DONE: " + "; ".join(f"{f.split('_')[0]} " + "/".join(f"{summ[f][str(d)]['mean_feature']:.3f}|{summ[f][str(d)]['mean_baseline']:.3f}" for d in Z.DELAYS) for f in A.H1F)); return 0


def main():
    if len(sys.argv) < 2: print(__doc__); return 3
    A.LOG = HERE / "results" / "a25_abs_log.txt"
    try: return run(sys.argv[1])
    except A.Mismatch as e: A.log(f"A25 abs MISMATCH (stop): {e}"); return 4
    except (PermissionError, RuntimeError) as e: A.log(f"A25 abs REFUSED: {e}"); return 3
    except KeyboardInterrupt: return 2
    except Exception as e:
        import traceback; A.log(f"A25 abs CRASH: {e!r}\n{traceback.format_exc()}"); return 1


if __name__ == "__main__": sys.exit(main())
