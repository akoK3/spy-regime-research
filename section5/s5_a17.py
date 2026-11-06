#!/usr/bin/env python3
"""A17: deterministic reproduction of the main-run fits (abort on any mismatch), saved models and test alarm times, then H1(c) (pre-registered), the POST HOC R=1-net H1(a) and the
test-segment QLIKE percent. Reads the main run's fold segments through MainBackend (frozen-protocol token); no era calibration, no lock, no freeze, no evaluation data.
Usage: s5_a17.py PROTOCOL_SHA256 [--check]      --check: guards + a full smoke test of the per-unit code on the contaminated RAW 3 fold against the rehearsal checkpoint.
Exit codes: 0 done, 1 crash (retryable; resumes from results/a17/ckpt), 2 Ctrl+C, 3 guard refusal, 4 reproduction mismatch (stop everything)."""
import sys, json, time, pickle, traceback
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_a17_a18_common as CM
from s5_a17_a18_common import log

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "a17"; MAIN = HERE / "results" / "main_run"; REH = HERE / "results" / "rehearsal_a16"


def stored_units(run_dir, version):
    import s5_guard as G
    u = {}
    for p in (run_dir / "ckpt").glob("*.json"):
        c = json.loads(p.read_text(encoding="utf-8")); k = c["key"].split("|"); assert c["version"] == version, p; u[(k[0], f"{k[3]}|{k[4]}", k[5])] = c["value"]
    return u


def guards(token):
    import s5_guard as G, s5_contamination as C
    ph = G.verify_frozen_protocol(token); rec = G.verify_completion(MAIN / G.COMPLETION, require_main=True)
    if rec["code_version"] != G.code_version(): raise PermissionError("code version differs from the main run's: reproduction would not be exact")
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    C.check_registry(HERE); units = stored_units(MAIN, rec["checkpoint_version"])
    if len(units) != 272: raise PermissionError(f"{len(units)} stored units, expected 272")
    j, ch = G.contamination(); ev = j["h1c_eligible_events_per_fold"]; mins = j["h1c_event_release_minute_after_0930"]
    if sum(len(v) for v in ev.values()) != 98 or any(x not in mins for v in ev.values() for x in v): raise PermissionError("H1(c) event list is not the 98 events with release minutes")
    log(f"A17 guards: protocol {ph[:16]}..., main record verified (results {rec['results_sha256'][:16]}...), code {rec['code_version']}, 272 units, 98 H1(c) events, no lock, registry ok")
    return ph, rec, units, ev, mins


def unit(b, db, fold, fam, setup, stored, save_dir=None):
    """Reproduce one (fold, family) unit exactly, then the A17 extras. Returns (record, mismatch list)."""
    import s5_run as RUN, s5_h1 as H, s5_eval as V
    cap = CM.Capture(b); sc = CM.roundtrip(RUN.score_fold(cap, fold, fam, setup)); mism = CM.diffs(sc, stored)
    if mism: return dict(reproduced=sc), mism
    s = cap.s; feats = tuple(setup["features"]); mf = db.fit(fam, feats, dict(setup["params"]), 3); mb = db.fit(fam, (), dict(setup["base_params"]), 3)
    rec = dict(reproduced=sc, exact_match=True)
    if save_dir is not None:
        p = save_dir / f"{fold.replace('|', '_')}_{fam}.pkl"; p.write_bytes(pickle.dumps(dict(feature=mf, baseline=mb, setup=setup), protocol=4)); rec["model_pickle_sha256"] = CM.file_sha(p)
    tf, tb = CM.a7_threshold(db, fam, feats, setup["params"]), CM.a7_threshold(db, fam, (), setup["base_params"])
    rec["thresholds"] = dict(feature=tf, baseline=tb)
    rec["alarms"] = dict(feature=CM.test_alarms(db, fam, feats, setup["params"], tf["threshold"]), baseline=CM.test_alarms(db, fam, (), setup["base_params"], tb["threshold"]))
    lb, lf, _ = V.align(np.asarray(s["loss_base"], float), np.asarray(s["key_base"]), np.asarray(s["loss_feat"], float), np.asarray(s["key_feat"])); ok = np.isfinite(lb) & np.isfinite(lf)
    rec["qlike_test"] = dict(mean_base=float(lb[ok].mean()), mean_feat=float(lf[ok].mean()), n=int(ok.sum()), pct=float(100 * (lb[ok].mean() - lf[ok].mean()) / lb[ok].mean()))
    if sc["a"] is not None:
        import s5_a6 as A, s5_d2 as D2
        if not hasattr(db, "_placebo_rows"): db._placebo_rows = [D2._work(sp) for sp in CM.placebo_specs(db)]
        gp = A.pauc(CM.placebo_points(db, fam, mf, feats, db._placebo_rows)) - A.pauc(CM.placebo_points(db, fam, mb, (), db._placebo_rows))
        rec["placebo"] = dict(gap=float(gp), net_a=float(sc["a"] - gp), n_placebo=len(db._placebo_rows))
    else: rec["placebo"] = dict(gap=None, net_a=None, skipped=sc["a_skipped"])
    return rec, []


def preflight(token):
    import s5_backend as BK, s5_guard as G
    ph, rec, units, ev, mins = guards(token); OUT.mkdir(parents=True, exist_ok=True); (OUT / "models").mkdir(exist_ok=True)
    rrec = G.verify_completion(REH / G.COMPLETION, require_main=False)
    if rrec["code_version"] != rec["code_version"] or rrec["checkpoint_version"] != rec["checkpoint_version"]: raise PermissionError("rehearsal checkpoints are not at the main run's version")
    ru = stored_units(REH, rrec["checkpoint_version"]); db = BK.DataBackend("RAW", 3); t0 = time.time()
    class One:                                                                                       # minimal backend over the contaminated fold (no token needed)
        kind = "check"
        def score(self, fold, family, setup): return db.score(fold, family, setup)
    r, mism = unit(One(), db, "RAW|3", "gaussian_hmm", ru[("select", "RAW|3", "gaussian_hmm")], ru[("score", "RAW|3", "gaussian_hmm")])
    if mism: raise SystemExit(f"MISMATCH in the determinism probe: {mism}")
    log(f"A17 preflight: RAW 3 Gaussian HMM reproduced the rehearsal checkpoint exactly; extras ran (thresholds {r['thresholds']['feature']['threshold']:.3f}/{r['thresholds']['baseline']['threshold']:.3f}, "
        f"QLIKE test pct {r['qlike_test']['pct']:.1f}, placebo gap {r['placebo']['gap']}) in {(time.time() - t0) / 60:.1f} min; nothing written to results/a17/ckpt")
    done = len(list((OUT / "ckpt").glob("*.json"))) if (OUT / "ckpt").exists() else 0; log(f"A17 preflight: {done} of 136 A17 units already checkpointed")
    return ph


def aggregate(units, ev, mins, folds, excluded):
    import s5_h1 as H, s5_h1c as HC, s5_guard as G
    recs = {(f, fam): json.loads((OUT / "ckpt" / f"{f.replace('|', '_')}_{fam}.json").read_text(encoding="utf-8")) for f in folds for fam in H.FAMILIES}
    fomc = {x for v in ev.values() for x in v}; out = dict(h1c={}, posthoc_r1_net_h1a={}, qlike_test_pct={})
    for fam in H.FAMILIES:
        hf, hb, rf, rb, per = [], [], [], [], []
        for key, dates in ev.items():
            era, n = ("LEGACY", key[6:]) if key.startswith("LEGACY") else ("RAW", key[3:])          # contamination-list keys: 'LEGACY12', 'RAW0'
            r = recs[(f"{era}|{int(n)}", fam)]; af, ab = r["alarms"]["feature"], r["alarms"]["baseline"]; nonf = [d for d in af if d not in fomc]
            for x in dates:
                m = mins[x]; h_f = HC.hit([a[1] for a in af.get(x, [])], m); h_b = HC.hit([a[1] for a in ab.get(x, [])], m); hf.append(h_f); hb.append(h_b)
                rf.append(HC.reference_rate([[a[1] for a in af[d]] for d in nonf], m)); rb.append(HC.reference_rate([[a[1] for a in ab[d]] for d in nonf], m)); per.append(dict(date=x, fold=f"{era}|{int(n)}", release_minute=m, feature_hit=h_f, baseline_hit=h_b))
        out["h1c"][fam] = dict(HC.summarize(fam, hf, hb, float(np.mean(rf)), float(np.mean(rb))), events=per)
        a = [recs[(f, fam)]["reproduced"]["a"] for f in folds]; net = [recs[(f, fam)]["placebo"]["net_a"] for f in folds]; gap = [recs[(f, fam)]["placebo"]["gap"] for f in folds]
        fr = H.family_result(net, [0.0] * len(folds), folds, excluded, 10000, 0)
        out["posthoc_r1_net_h1a"][fam] = dict(label="POST HOC", per_fold={f: dict(a=x, gap=g, net=y) for f, x, g, y in zip(folds, a, gap, net)},
                                              confirmatory=fr["confirmatory"]["H1a"], all_folds=fr["all_folds_sensitivity"]["H1a"],
                                              mean_gap_confirmatory=float(np.mean([g for f, g in zip(folds, gap) if f not in excluded and g is not None])))
        pc = {f: recs[(f, fam)]["qlike_test"] for f in folds}; c = [pc[f]["pct"] for f in folds if f not in excluded]
        out["qlike_test_pct"][fam] = dict(confirmatory_median=float(np.median(c)), confirmatory_q25_q75=[float(q) for q in np.percentile(c, [25, 75])], confirmatory_min_max=[float(min(c)), float(max(c))],
                                          confirmatory_pooled=float(100 * (np.mean([pc[f]["mean_base"] for f in folds if f not in excluded]) - np.mean([pc[f]["mean_feat"] for f in folds if f not in excluded])) / np.mean([pc[f]["mean_base"] for f in folds if f not in excluded])),
                                          all_folds_median=float(np.median([pc[f]["pct"] for f in folds])), per_fold={f: pc[f]["pct"] for f in folds})
    out["thresholds_flagged"] = {fam: [f"{f}:{w}" for f in folds for w in ("feature", "baseline") if recs[(f, fam)]["thresholds"][w]["info"] != "ok"] for fam in H.FAMILIES}
    return out


def main():
    if len(sys.argv) < 2: print("usage: s5_a17.py PROTOCOL_SHA256 [--check]"); return CM.EXIT_GUARD
    token, check = sys.argv[1], "--check" in sys.argv[2:]
    try:
        if check: preflight(token); log("A17 preflight passed (--check): A17 NOT started"); return CM.EXIT_OK
        ph, rec, units, ev, mins = guards(token)
    except SystemExit as e: log(f"A17 STOP: {e}"); return CM.EXIT_MISMATCH
    except (PermissionError, RuntimeError, AssertionError) as e: log(f"A17 REFUSED (not retryable): {type(e).__name__}: {e}"); return CM.EXIT_GUARD
    import s5_main as MB, s5_guard as G, s5_h1 as H
    tag = dict(a17_script=CM.file_sha(__file__), common=CM.file_sha(CM.__file__), main_results=rec["results_sha256"]); ck = OUT / "ckpt"; ck.mkdir(parents=True, exist_ok=True); models = OUT / "models"; models.mkdir(exist_ok=True)
    CM.keep_awake(True); t0 = time.time(); b = MB.MainBackend(ph); folds = b.folds(); excluded, _ = G.excluded_folds()
    try:
        for i, fold in enumerate(folds, 1):
            for fam in H.FAMILIES:
                p = ck / f"{fold.replace('|', '_')}_{fam}.json"
                if p.exists() and json.loads(p.read_text(encoding="utf-8")).get("tag") == tag: continue
                G.check_unlocked("A17"); t1 = time.time(); db = b._b(fold)
                r, mism = unit(b, db, fold, fam, units[("select", fold, fam)], units[("score", fold, fam)], save_dir=models)
                if mism:
                    (OUT / "MISMATCH.json").write_text(json.dumps(dict(fold=fold, family=fam, differences=mism, reproduced=r["reproduced"], stored=units[("score", fold, fam)]), indent=1, default=float), encoding="utf-8")
                    log(f"A17 MISMATCH at {fold} {fam}: {mism[:3]} -> stop (exit 4); details in results/a17/MISMATCH.json"); return CM.EXIT_MISMATCH
                r["tag"] = tag; tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(r, default=float), encoding="utf-8"); tmp.replace(p)
                log(f"A17 fold {i}/34 {fold} {fam}: exact match; H1(b) test pct {r['qlike_test']['pct']:.1f}; placebo gap {r['placebo']['gap']}; {(time.time() - t1) / 60:.1f} min")
        res = aggregate(units, ev, mins, folds, excluded); res.update(tag=tag, n_units=136, all_exact=True, models_manifest={p.name: CM.file_sha(p) for p in sorted(models.glob("*.pkl"))})
        (OUT / "a17_results.json").write_text(json.dumps(res, indent=1, default=float), encoding="utf-8")
        log(f"A17 DONE in {(time.time() - t0) / 3600:.2f} h: 136/136 units reproduced exactly; results/a17/a17_results.json written"); return CM.EXIT_OK
    except PermissionError as e: log(f"A17 REFUSED (not retryable): {e}"); return CM.EXIT_GUARD
    except KeyboardInterrupt: log("A17 STOPPED by the user (Ctrl+C); finished units are checkpointed"); return CM.EXIT_STOP
    except BaseException as e:
        log(f"A17 CRASH after {(time.time() - t0) / 60:.1f} min: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return CM.EXIT_CRASH
    finally: CM.keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
