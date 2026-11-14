#!/usr/bin/env python3
"""POST HOC sensitivity (user order 2026-11-13; run after the 5.12 freeze and the evaluation; changes no frozen, MR2 or evaluation result): MR2 feature selection (protocol 5.8,
greedy forward from the return-only model at K=3, 1% gain rule, at most 6 features) rerun on all 34 development folds for gaussian_hmm, student_t_hmm and hsmm with 3 k-means++
starts per fit (seed 0, starts 0-2: the seeds of the main fits, s5_backend.DataBackend.fit) instead of 1. If the selected set differs from MR2, K is re-tuned on the same grid with
3 starts (s5_select.tune, as MR2); if it is the same, the MR2 K is kept (same set, same 3-start fits, so tuning would repeat MR2). Baselines are not refitted (MR2 already tunes
them with 3 starts). Era final setups under the 3-start rule: s5_select.final_setup on the 3-start fold setups.
Data: development folds only, through s5_backend.DataBackend / era_context (inner train and validation; the test segment is not read). The objective is s5_backend's
(validation QLIKE of a model fitted on the inner train, delay not computed) built from DataBackend.fit and qlike_on, without the era-calibration lock check that
DataBackend.objective applies (A16 rule 5 protects the confirmatory run; this is a labelled post-hoc analysis that writes only to its own directory; A38 also calls
qlike_on directly). Reproduction check per unit: the 1-start return-only validation QLIKE must equal the first value of the MR2 trace exactly, else exit 4.
Not a result module; imports the result modules unchanged (code version must stay a0323ed24d68e896).
Usage: mr2_starts3_sensitivity.py run WORKER NWORKERS     (folds i with i % NWORKERS == WORKER; resumable, one JSON per fold and family)
       mr2_starts3_sensitivity.py combine                 (writes section5/results/posthoc_mr2_starts3.json once)
Exit codes: 0 done, 1 crash, 3 guard, 4 reproduction mismatch."""
import sys, os, json, time, gc, hashlib, datetime, ctypes, traceback
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; S5 = ROOT / "section5"; sys.path.insert(0, str(S5))
RES = S5 / "results"; OUT = RES / "posthoc_mr2_starts3"; UNITS = OUT / "units"; LOG = OUT / "log.txt"; FINAL = RES / "posthoc_mr2_starts3.json"; MAIN2 = RES / "main_run_2"
FAMS = ("gaussian_hmm", "student_t_hmm", "hsmm"); CODE_VERSION = "a0323ed24d68e896"; STARTS = 3
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()
rt = lambda x: json.loads(json.dumps(x, default=float))


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def mr2_setups():
    """(fold, family) -> MR2 'select' unit, version-checked against the MR2 completion record (as s5_a22.mr2_units)."""
    import s5_guard as G
    rec = G.verify_completion(MAIN2 / G.COMPLETION, require_main=True); u = {}
    for p in (MAIN2 / "ckpt").glob("*.json"):
        c = json.loads(p.read_text(encoding="utf-8")); k = c["key"].split("|")
        if c["version"] != rec["checkpoint_version"]: raise PermissionError(f"MR2 checkpoint {p.name} has another version")
        if k[0] == "select": u[(f"{k[3]}|{k[4]}", k[5])] = c["value"]
    if len(u) != 136: raise PermissionError(f"{len(u)} MR2 select units, expected 136")
    return u


def guards():
    import s5_guard as G, s5_lib as L
    cv = G.code_version()
    if cv != CODE_VERSION: raise PermissionError(f"code version {cv} != {CODE_VERSION}")
    ph = G.frozen_protocol_hash()
    caches = {e: L.CACHE / f"{e}_features.npz" for e in ("LEGACY", "RAW")}
    primary, _, _ = L.pools(); need = L.a20_pool(primary) + ["lee_mykland_approx60"]
    for e, cf in caches.items():
        have = set(np.load(cf).files)
        if not set(need) <= have: raise PermissionError(f"{cf.name} lacks {sorted(set(need) - have)}: load_era would write the cache")
    return ph, {e: sha(cf) for e, cf in caches.items()}


def objective(db, family):
    """s5_backend.DataBackend.objective without the lock check (see module doc)."""
    def f(subset, params, starts):
        m = db.fit(family, subset, params, starts); loss, _ = db.qlike_on(family, m, subset, "val"); loss = loss[np.isfinite(loss)]
        return dict(qlike=float(loss.mean()) if len(loss) else float("inf"), delay=float("nan"))
    return f


def run(worker, nw):
    import s5_guard as G, s5_backend as BK, s5_select as SEL
    ph, cache0 = guards(); mr2 = mr2_setups(); UNITS.mkdir(parents=True, exist_ok=True)
    folds = [f for i, f in enumerate(G.MAIN_FOLDS) if i % nw == worker]
    log(f"worker {worker}/{nw}: start; code version {CODE_VERSION}; protocol {ph[:16]}...; {len(folds)} folds; feature caches {', '.join(f'{e} {h[:12]}' for e, h in cache0.items())}")
    try: ctypes.windll.kernel32.SetThreadExecutionState(0x80000000 | 0x00000001)
    except Exception: pass
    ctx = None
    for fold in folds:
        todo = [fam for fam in FAMS if not (UNITS / f"{fold.replace('|', '_')}_{fam}.json").exists()]
        if not todo: continue
        era, n = fold.split("|")
        if ctx is None or ctx["era"] != era: ctx = None; gc.collect(); ctx = BK.era_context(era)
        db = BK.DataBackend(era, int(n), allowed=set(G.MAIN_FOLDS), protocol_sha256=ph, shared=ctx)
        for fam in todo:
            t0 = time.time(); m = mr2[(fold, fam)]; obj = objective(db, fam)
            r1 = rt(obj((), SEL.BASE_PARAMS, 1)["qlike"])
            if r1 != m["trace"][0]["qlike"]: log(f"MISMATCH {fold} {fam}: 1-start return-only QLIKE {r1!r} != MR2 {m['trace'][0]['qlike']!r}"); return 4
            g = SEL.greedy_forward(db.candidates(fold), lambda s, p, st: obj(s, p, STARTS))
            same = g["selected"] == m["features"]
            if same: params, vq, tuned = m["params"], m["val_qlike"], "not rerun (same set as MR2; MR2 K kept)"
            else: t = SEL.tune(g["selected"], obj, BK.HSMM_GRID if fam == "hsmm" else BK.HMM_GRID); params, vq, tuned = t["params"], t["result"]["qlike"], "rerun (3 starts, MR2 grid)"
            u = rt(dict(fold=fold, family=fam, reproduction=dict(one_start_return_only_qlike=r1, mr2=m["trace"][0]["qlike"], equal=True),
                        mr2=dict(features=m["features"], params=m["params"], base_params=m["base_params"], trace=m["trace"], val_qlike=m["val_qlike"]),
                        starts3=dict(features=g["selected"], params=params, base_params=m["base_params"], trace=g["trace"], exhausted=g["exhausted"], tune=tuned, val_qlike=vq),
                        set_changed=not same, order_only=(not same and sorted(g["selected"]) == sorted(m["features"])), minutes=(time.time() - t0) / 60))
            p = UNITS / f"{fold.replace('|', '_')}_{fam}.json"; tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, indent=1), encoding="utf-8"); tmp.replace(p)
            log(f"{fold} {fam}: 1 start {m['features']} K {m['params']} | 3 starts {g['selected']} K {params}{' CHANGED' if not same else ''}; reproduction ok; {u['minutes']:.1f} min")
        del db; gc.collect()
    _, cache1 = guards()
    if cache1 != cache0: log(f"WARNING feature cache changed during the run: {cache0} -> {cache1}")
    log(f"worker {worker}/{nw}: DONE; feature caches unchanged: {cache1 == cache0}"); return 0


def combine():
    import s5_guard as G, s5_select as SEL
    if FINAL.exists(): print("exists; written once"); return 3
    files = sorted(UNITS.glob("*.json")); us = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    if len(us) != 34 * 3: print(f"{len(us)} units, expected 102"); return 3
    summ = json.loads((MAIN2 / "run_summary.json").read_text(encoding="utf-8")); per = {(u["fold"], u["family"]): u for u in us}
    eras = ("LEGACY", "RAW"); final = {}
    for e in eras:
        for fam in FAMS:
            fl = [f for f in G.MAIN_FOLDS if f.startswith(e + "|")]
            mr2_check = rt(SEL.final_setup([dict(per[(f, fam)]["mr2"]) for f in fl]))
            if mr2_check != rt({k: v for k, v in summ["final_setups"][e][fam].items()}): raise SystemExit(f"final_setup on the MR2 fold setups does not reproduce run_summary {e} {fam}")
            s3 = rt(SEL.final_setup([dict(per[(f, fam)]["starts3"]) for f in fl])); m = summ["final_setups"][e][fam]
            final.setdefault(e, {})[fam] = dict(mr2=m, starts3=s3, features_same=s3["features"] == m["features"], params_same=s3["params"] == m["params"])
    fz = json.loads((RES / "section5_freeze.json").read_text(encoding="utf-8"))
    table = {fam: {f: dict(starts1=per[(f, fam)]["mr2"]["features"], starts3=per[(f, fam)]["starts3"]["features"], changed=per[(f, fam)]["set_changed"], order_only=per[(f, fam)]["order_only"],
                           K1=per[(f, fam)]["mr2"]["params"], K3=per[(f, fam)]["starts3"]["params"], confirmatory=f not in G.excluded_folds()[0]) for f in G.MAIN_FOLDS} for fam in FAMS}
    res = dict(label="POST HOC sensitivity, run after the 5.12 freeze and the evaluation; changes no frozen, MR2 or evaluation result. MR2 5.8 forward selection with 3 starts (seed 0, starts 0-2) instead of 1; development folds only",
               code_version=G.code_version(), script_sha256=sha(__file__), mr2_completion_sha256=sha(MAIN2 / G.COMPLETION), freeze_sha256=sha(RES / "section5_freeze.json"),
               units_sha256={p.name: sha(p) for p in files}, per_fold=table,
               n_changed={fam: sum(v["changed"] for v in table[fam].values()) for fam in FAMS}, n_changed_set_not_order={fam: sum(v["changed"] and not v["order_only"] for v in table[fam].values()) for fam in FAMS},
               final_setups=final, freeze_features={e: {fam: fz.get("setups", fz.get("final_setups", {})).get(e, {}).get(fam, {}).get("features") for fam in FAMS} for e in eras} if isinstance(fz, dict) else None,
               minutes=sum(u["minutes"] for u in us), generated=datetime.datetime.now(datetime.timezone.utc).isoformat())
    FINAL.write_text(json.dumps(res, indent=1), encoding="utf-8"); FINAL.with_suffix(".sha256").write_text(f"{sha(FINAL)}  {FINAL.name}\n", encoding="ascii")
    print(json.dumps(dict(n_changed=res["n_changed"], n_changed_set_not_order=res["n_changed_set_not_order"], final={e: {f: (v["starts3"]["features"], v["starts3"]["params"], v["features_same"], v["params_same"]) for f, v in final[e].items()} for e in final}), indent=1))
    return 0


if __name__ == "__main__":
    try:
        if sys.argv[1:2] == ["run"]: sys.exit(run(int(sys.argv[2]), int(sys.argv[3])))
        if sys.argv[1:2] == ["combine"]: sys.exit(combine())
        print(__doc__); sys.exit(3)
    except PermissionError as e: log(f"REFUSED: {e}"); sys.exit(3)
    except SystemExit: raise
    except BaseException as e:
        log(f"CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        sys.exit(1)
