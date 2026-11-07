#!/usr/bin/env python3
"""MR2 (AMENDMENT_A20.md): the main run under A20 (__sadj-only scale inputs, deseasonalised QLIKE target), then the A17-style phase on its fits (reproduction with exact-match abort,
saved models and alarms, H1(c), POST HOC R=1-net H1(a), QLIKE percent), then D7 per A19.3 on the MR2 fits. Reuses s5_main_run, s5_a17 and s5_d7 with MR2 directories; their rules are unchanged.
Usage: s5_mr2.py PROTOCOL_SHA256 STAGE [--check]
  STAGE: mr2 | a17 | d7 (the runner calls them in this order); d7a21 = D7 rerun with A21 rule 1 into results/mr2/d7_a21 (AMENDMENT_A21.md rule 2).   --check (any stage): guards plus the full preflight on the contaminated folds RAW 3 and LEGACY 29 (selection and
  scoring of all four families, A17-style reproduction and extras, D7 including its positive control); writes only to results/mr2_preflight/.
Exit codes: 0 done, 1 crash (retryable; resumes from checkpoints), 2 Ctrl+C, 3 guard refusal, 4 A17-style reproduction mismatch (stop)."""
import sys, os, json, time, pickle, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))

HERE = Path(__file__).resolve().parent; RES = HERE / "results"; MAIN2 = RES / "main_run_2"; MR2 = RES / "mr2"; PRE = RES / "mr2_preflight"; LOG = RES / "mr2_log.txt"
CONTAMINATED = ("RAW|3", "LEGACY|29")


def configure():
    """Point the reused modules at the MR2 directories (A20 rule 4)."""
    import s5_main_run as MR, s5_a17 as A, s5_a17_a18_common as CM, s5_d7 as D
    MR.OUT, MR.LOG = MAIN2, LOG
    A.MAIN, A.OUT = MAIN2, MR2 / "a17"; CM.LOG = LOG
    D.MAIN_DIR, D.A17, D.OUT, D.CK, D.LOG = MAIN2, MR2 / "a17", MR2 / "d7", MR2 / "d7" / "ckpt", LOG
    return MR, A, CM, D


def preflight(token):
    import s5_guard as G, s5_contamination as C, s5_backend as BK, s5_run as RUN, s5_lib as L, s5_h1 as H
    MR, A, CM, D = configure(); log = CM.log
    ph = G.verify_frozen_protocol(token); G.canonical_contamination(); excluded, _ = G.excluded_folds(); C.check_registry(HERE)
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    if not set(CONTAMINATED) <= excluded: raise PermissionError("preflight folds must be contaminated")
    log(f"MR2 preflight: protocol {ph[:16]}... FROZEN (through A20), canonical list, {len(excluded)} excluded, no lock, registry ok; code version {G.code_version()}")
    MR.preflight(token)                                                                                        # main-run guards with the MR2 directory (reads no data)
    PRE.mkdir(parents=True, exist_ok=True); (PRE / "models").mkdir(exist_ok=True); units = []; t0 = time.time()
    for fold in CONTAMINATED:
        era, n = fold.split("|"); db = BK.DataBackend(era, int(n)); c = db.c
        assert c["cols"] == L.a20_pool(L.pools()[0]) and len(c["cols"]) == 13, f"pool is not the A20 pool: {c['cols']}"
        tg = np.concatenate([q["tgt"] for q in db.sequences("val", ())]); tg = tg[np.isfinite(tg)]
        assert len(tg) > 1000 and 10 < np.median(tg) < 1000, f"QLIKE target is not deseasonalised (median {np.median(tg)})"                # deseasonalised: about 60; raw: about 1e-4
        log(f"MR2 preflight {fold}: pool 13 (A20), validation QLIKE target median {np.median(tg):.1f} (deseasonalised; raw would be ~1e-4)")
        class One:
            kind = "check"
            def __init__(s, b): s.b = b
            def objective(s, f, fam): return s.b.objective(f, fam)
            def candidates(s, f): return s.b.candidates(f)
            def param_grid(s, fam): return s.b.param_grid(fam)
            def score(s, f, fam, setup): return s.b.score(f, fam, setup)
        db2 = BK.DataBackend(era, int(n)); models, thr = {}, {}
        for fam in H.FAMILIES:
            t1 = time.time(); setup = RUN.select_fold(One(db), fold, fam); stored = CM.roundtrip(RUN.score_fold(One(db), fold, fam, setup))
            rec, mism = A.unit(One(db2), db2, fold, fam, setup, stored, save_dir=PRE / "models")
            if mism: raise SystemExit(f"MR2 preflight: A17-style reproduction mismatch at {fold} {fam}: {mism[:3]}")
            o = pickle.loads((PRE / "models" / f"{fold.replace('|', '_')}_{fam}.pkl").read_bytes())
            models[fam] = dict(feature=(o["feature"], tuple(setup["features"])), baseline=(o["baseline"], ())); thr[fam] = {w: rec["thresholds"][w]["threshold"] for w in ("feature", "baseline")}
            log(f"MR2 preflight {fold} {fam}: features {setup['features']} K/lam {setup['params']} baseline {setup['base_params']}; H1(a) {stored['a']}, H1(b) {stored['b']}; "
                f"reproduced exactly; thresholds {thr[fam]['feature']:.2f}/{thr[fam]['baseline']:.2f}; QLIKE pct {rec['qlike_test']['pct']:.1f}; placebo gap {rec['placebo']['gap']}; {(time.time() - t1) / 60:.1f} min")
        u = D.fold_unit(db2, fold, models, thr); units.append(u); a = D.aggregate([u])
        log(f"MR2 preflight {fold} D7 ({a['n_days']} days): positive control (sweep gain, feature models) " + "; ".join(
            f"{pc}: " + ", ".join(f"{f.split('_')[0]} {a['types'][pc][f + '|feature']['diff']:+.2f}{'*' if a['types'][pc][f + '|feature']['responds'] else ''}" for f in D.H1_FAMILIES) for pc in D.PC)
            + f"; baselines x5.29 " + ", ".join(f"{a['types']['pc_ratio5.29'][f + '|baseline']['diff']:+.2f}" for f in D.H1_FAMILIES) + f"; gates {a['gates']}")
        del db, db2
    a = D.aggregate(units); (PRE / "mr2_preflight.json").write_text(json.dumps(a, indent=1, default=float), encoding="utf-8")
    log(f"MR2 preflight, both contaminated folds pooled ({a['n_days']} days): gates {a['gates']}; D7 verdicts {{{', '.join(f'{k}: missed={v['missed']}' for k, v in a['verdict'].items())}}} "
        f"(preflight only; written to results/mr2_preflight/); {(time.time() - t0) / 60:.1f} min")
    return ph


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in ("mr2", "a17", "d7", "d7a21"): print(__doc__); return 3
    token, stage, check = sys.argv[1], sys.argv[2], "--check" in sys.argv[3:]
    MR, A, CM, D = configure(); LOG.parent.mkdir(parents=True, exist_ok=True); (MR2 / "a17" / "models").mkdir(parents=True, exist_ok=True)
    if check:
        try: preflight(token); CM.log(f"MR2 preflight passed (--check): nothing started"); return 0
        except SystemExit as e: CM.log(str(e)); return 4
        except (PermissionError, RuntimeError, AssertionError) as e: CM.log(f"MR2 preflight REFUSED: {type(e).__name__}: {e}"); return 3
        except BaseException as e:
            CM.log(f"MR2 preflight CRASH: {type(e).__name__}: {e}")
            for l in traceback.format_exc().rstrip().splitlines(): CM.log("  | " + l)
            return 1
    if stage == "d7a21":                                                                                         # A21 rule 2: D7 with the A21 rule-1 exclusion, own directory and log
        if check: print("d7a21 has no --check here; its preflight is s5_step2.py --check (A21 rule 4)"); return 3
        D.OUT, D.CK, D.LOG = MR2 / "d7_a21", MR2 / "d7_a21" / "ckpt", RES / "a21_log.txt"; D.OUT.mkdir(parents=True, exist_ok=True); stage = "d7"
    sys.argv = [sys.argv[0], token]                                                                              # the reused mains read argv[1] = token
    return {"mr2": MR.main, "a17": A.main, "d7": D.main}[stage]()


if __name__ == "__main__":
    sys.exit(main())
