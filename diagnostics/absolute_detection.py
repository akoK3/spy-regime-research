#!/usr/bin/env python3
"""POST HOC descriptive (user order 2026-11-14, Veksler's point: report absolute detection performance, not only feature-minus-baseline
differences). Run after the 5.12 freeze and the evaluation; changes no frozen, MR2 or evaluation result; no new evaluation-period read.

Development part (34 development folds; the saved MR2 A17-style models, sha256-checked against the A17 manifest; no fitting):
  per fold x family (gaussian_hmm, student_t_hmm, hsmm, bocpd) x model (feature, baseline), on the fold's TEST-segment stable-day splices
  (s5_backend.DataBackend._splices, seed 4242, as MR2):
    pauc       absolute pAUC (s5_a6.pauc of the s5_backend._h1a_points curve; the same computation as MR2). Reproduction check per
               fold and family: pAUC(feature) - pAUC(baseline) must equal the MR2 score unit 'a' exactly (s5_a22.same), else exit 4.
    at the fold's stored calibrated threshold (A7, 0.2 alarms per validation session; s5_d7.load_fold_models), per planted cell
    (variance ratio 1.5/2/3/5/10 x direction up/down x duration permanent/30/60/120 min):
      hit60      share of break splices with an alarm whose first update (T_d) is available after the onset tau and whose
                 confirmation (T_c) is available within 60 min of tau (s5_events.hit_in_window; the H1(a) hit definition)
      delay60    minutes from tau to T_c for those hits
      hit_any    share with any confirmed alarm with T_d after tau before the session end; delay_any = minutes tau -> T_c of the first
    null       confirmed alarms per null splice (two stable days spliced without a break) at the same threshold
  realised alarm rates on the real test sessions and FOMC hit rates are taken from the stored MR2 A17-style records (a17_results.json).
Evaluation part (already-written outputs only): FOMC hit rates, reference alarm rates and alarms per session from
section5/results/evaluation_{LEGACY,RAW}.json; confirmation lag T_c - T_d of the real confirmed alarms from the 'breaks' lists there.
Absolute evaluation pAUC is NOT available from written outputs (only the difference was stored) and would need a new evaluation read.

Usage: absolute_detection.py run WORKER NWORKERS   (folds i with i % NWORKERS == WORKER; resumable, one JSON per fold)
       absolute_detection.py combine              (writes section5/results/posthoc_absolute_detection.json and .md once)
Exit codes: 0 done, 1 crash, 3 guard, 4 reproduction mismatch."""
import sys, os, json, time, gc, hashlib, datetime, traceback
from pathlib import Path
import numpy as np
ROOT = Path(__file__).resolve().parent.parent; S5 = ROOT / "section5"; sys.path.insert(0, str(S5))
RES = S5 / "results"; OUT = RES / "posthoc_absolute_detection"; UNITS = OUT / "units"; LOG = OUT / "log.txt"
FINAL = RES / "posthoc_absolute_detection.json"; TABLES = RES / "posthoc_absolute_detection.md"
FAMS = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); CODE_VERSION = "a0323ed24d68e896"; MIN = 60 * 10 ** 9
sha = lambda p: hashlib.sha256(Path(p).read_bytes()).hexdigest()


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"
    OUT.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def guards():
    import s5_guard as G, s5_lib as L
    cv = G.code_version()
    if cv != CODE_VERSION: raise PermissionError(f"code version {cv} != {CODE_VERSION}")
    ph = G.frozen_protocol_hash(); primary, _, _ = L.pools(); need = L.a20_pool(primary) + ["lee_mykland_approx60"]
    for e in ("LEGACY", "RAW"):
        have = set(np.load(L.CACHE / f"{e}_features.npz").files)
        if not set(need) <= have: raise PermissionError(f"{e} feature cache lacks {sorted(set(need) - have)}")
    return ph, {e: sha(L.CACHE / f"{e}_features.npz") for e in ("LEGACY", "RAW")}


def cell_key(c): return "null" if c == "null" else f"R{c[0]}|{c[1]}|{'perm' if c[2] is None else c[2]}"


def splice_results(db, fam, model, subset, thr):
    """Per splice at threshold thr: (cell, tau, events) for break and null splices, plus the H1(a) curve points."""
    import s5_eval as V, s5_a7 as B, s5_events as E, s5_a22 as A22
    sp = db._splices(); to_des = db.c["to_des"]; mk = db.c["mk"]; D = 1 + len(subset)
    rows = [(s, r) for s, r in zip(sp["specs"], sp["rows"])]
    qs = [mk(r, subset) for r in [to_des(r, r["iA"]) for _, r in rows]]; rs = V.run_filter(fam, model, qs, D)
    out = []
    for (s, r), q, x in zip(rows, qs, rs):
        ev = B.events(fam, x, q, thr) if q["n"] else []
        out.append(dict(cell=s["cell"], tau=int(r["tau"]) if s["cell"] != "null" else None, ev=[(int(q["avail"][e["i_d"]]), int(q["avail"][e["i_c"]])) for e in ev]))
    points = A22.h1a_points_shifted(db, fam, model, subset, (0,))[0]
    return out, points


def summarise(spl):
    by = {}
    for s in spl:
        k = cell_key(s["cell"]); b = by.setdefault(k, dict(n=0, hit60=0, delay60=[], hit_any=0, delay_any=[], alarms=0))
        b["n"] += 1
        if s["cell"] == "null": b["alarms"] += len(s["ev"]); continue
        tau = s["tau"]; after = [(d, c) for d, c in s["ev"] if d > tau]
        w = [c for d, c in after if c <= tau + 60 * MIN]
        if w: b["hit60"] += 1; b["delay60"].append((min(w) - tau) / MIN)
        if after: b["hit_any"] += 1; b["delay_any"].append((min(c for _, c in after) - tau) / MIN)
    return by


def run(worker, nw):
    import s5_guard as G, s5_backend as BK, s5_a22 as A22, s5_a6 as A6, s5_h1 as H
    ph, cache0 = guards(); man = A22.a17_manifest(); mr2 = A22.mr2_units(); excluded, _ = G.excluded_folds(); UNITS.mkdir(parents=True, exist_ok=True)
    folds = [f for i, f in enumerate(G.MAIN_FOLDS) if i % nw == worker]
    log(f"worker {worker}/{nw}: start; code version {CODE_VERSION}; {len(folds)} folds")
    ctx = None
    for fold in folds:
        p = UNITS / f"{fold.replace('|', '_')}.json"
        if p.exists(): continue
        era, n = fold.split("|"); t0 = time.time()
        if ctx is None or ctx["era"] != era: ctx = None; gc.collect(); ctx = BK.era_context(era)
        db = BK.DataBackend(era, int(n), allowed=set(G.MAIN_FOLDS), protocol_sha256=ph, shared=ctx)
        models, thr = A22.load_models(fold, man); sp = db._splices(); n_st = sp["n_stable"]; u = dict(fold=fold, confirmatory=fold not in excluded, n_stable_test=n_st, families={})
        for fam in FAMS:
            rec = {}
            if n_st < 8 or not sp["specs"]:
                u["families"][fam] = dict(skipped=f"{n_st} stable test days" if n_st < 8 else (sp["why"] or "no specs")); continue
            pts = {}
            for w in ("feature", "baseline"):
                m, sub = models[fam][w]; spl, pts[w] = splice_results(db, fam, m, sub, thr[fam][w])
                rec[w] = dict(threshold=thr[fam][w], subset=list(sub), pauc=float(A6.pauc(pts[w])), cells=summarise(spl))
            eff = H.h1a_fold_effect(pts["feature"], pts["baseline"], n_st)["effect"]                 # the MR2 fold effect, recomputed
            stored = mr2[("score", fold, fam)]["a"]
            if not A22.same(rec["feature"]["pauc"] - rec["baseline"]["pauc"], stored) or not A22.same(eff, stored):
                log(f"MISMATCH {fold} {fam}: pAUC difference {rec['feature']['pauc'] - rec['baseline']['pauc']!r} / {eff!r} != MR2 {stored!r}"); return 4
            u["families"][fam] = rec
        u["minutes"] = (time.time() - t0) / 60
        tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(u, default=float), encoding="utf-8"); tmp.replace(p)
        log(f"{fold}: {n_st} stable days; pAUC f/b " + ", ".join(f"{f.split('_')[0]} {u['families'][f]['feature']['pauc']:.3f}/{u['families'][f]['baseline']['pauc']:.3f}" for f in FAMS if "feature" in u["families"][f]) + f"; reproduction ok; {u['minutes']:.1f} min")
        del db; gc.collect()
    _, cache1 = guards(); log(f"worker {worker}/{nw}: DONE; feature caches unchanged: {cache1 == cache0}"); return 0


def q(x):
    x = np.asarray(x, float)
    return None if not len(x) else dict(n=int(len(x)), median=float(np.median(x)), q25=float(np.percentile(x, 25)), q75=float(np.percentile(x, 75)))


def combine():
    import s5_guard as G
    if FINAL.exists(): print("exists; written once"); return 3
    files = sorted(UNITS.glob("*.json")); us = [json.loads(p.read_text(encoding="utf-8")) for p in files]
    if len(us) != 34: print(f"{len(us)} units, expected 34"); return 3
    a17 = json.loads((RES / "a17" / "a17_results.json").read_text(encoding="utf-8"))
    dev = {}
    for era in ("LEGACY", "RAW"):
        for scope in ("confirmatory", "all_folds"):
            sel = [u for u in us if u["fold"].startswith(era + "|") and (u["confirmatory"] or scope == "all_folds")]
            for fam in FAMS:
                ok = [u for u in sel if "feature" in u["families"][fam]]; r = dict(n_folds=len(sel), n_folds_scored=len(ok))
                for w in ("feature", "baseline"):
                    pa = [u["families"][fam][w]["pauc"] for u in ok]; cells = {}
                    for u in ok:
                        for k, b in u["families"][fam][w]["cells"].items():
                            c = cells.setdefault(k, dict(n=0, hit60=0, delay60=[], hit_any=0, delay_any=[], alarms=0))
                            for kk in ("n", "hit60", "hit_any", "alarms"): c[kk] += b[kk]
                            c["delay60"] += b["delay60"]; c["delay_any"] += b["delay_any"]
                    cs = {k: (dict(n_null=c["n"], alarms_per_null_splice=c["alarms"] / c["n"]) if k == "null" else
                              dict(n=c["n"], hit60_rate=c["hit60"] / c["n"], delay60_min=q(c["delay60"]), hit_any_rate=c["hit_any"] / c["n"], delay_any_min=q(c["delay_any"]))) for k, c in cells.items()}
                    by_ratio = {}
                    for R in ("1.5", "2", "3", "5", "10"):
                        for dr in ("up", "down"):
                            ks = [k for k in cells if k.startswith(f"R{R}|{dr}|")]; n = sum(cells[k]["n"] for k in ks)
                            if n: by_ratio[f"R{R}|{dr}"] = dict(n=n, hit60_rate=sum(cells[k]["hit60"] for k in ks) / n, delay60_min=q(sum((cells[k]["delay60"] for k in ks), [])),
                                                             hit_any_rate=sum(cells[k]["hit_any"] for k in ks) / n, delay_any_min=q(sum((cells[k]["delay_any"] for k in ks), [])))
                    r[w] = dict(pauc_mean=float(np.mean(pa)) if pa else None, pauc_median=float(np.median(pa)) if pa else None, pauc_per_fold={u["fold"]: u["families"][fam][w]["pauc"] for u in ok},
                                cells=cs, by_ratio_direction=by_ratio)
                dev.setdefault(era, {}).setdefault(scope, {})[fam] = r
    # realised test alarm rates and FOMC hit rates from the stored A17 records (per era, all folds and confirmatory)
    a17ck = {}
    for p in (RES / "a17" / "ckpt").glob("*.json"):
        parts = p.stem.split("_"); a17ck[(f"{parts[0]}|{parts[1]}", "_".join(parts[2:]))] = json.loads(p.read_text(encoding="utf-8"))      # file name: <ERA>_<n>_<family>.json
    rates = {}
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            for w in ("feature", "baseline"):
                per = []
                for f in [x for x in G.MAIN_FOLDS if x.startswith(era + "|")]:
                    c = a17ck.get((f, fam))
                    if c and w in c.get("alarms", {}): al = c["alarms"][w]; per.append((f, sum(len(v) for v in al.values()) / max(len(al), 1)))
                rates.setdefault(era, {}).setdefault(fam, {})[w] = dict(mean_test_alarms_per_session=float(np.mean([r for _, r in per])) if per else None, n_folds=len(per))
    fomc = {}
    for fam in FAMS:
        h = a17["h1c"][fam]; evs = h["events"]
        for era in ("LEGACY", "RAW"):
            e = [x for x in evs if str(x.get("fold", "")).startswith(era)]
            fomc.setdefault(era, {})[fam] = dict(n_events=len(e), feature_hit_rate=(sum(bool(x.get("f3_hit", x.get("feature_hit"))) for x in e) / len(e)) if e else None,
                                                 baseline_hit_rate=(sum(bool(x.get("base_hit", x.get("baseline_hit"))) for x in e) / len(e)) if e else None)
        fomc.setdefault("pooled", {})[fam] = dict(n_events=h["paired"]["n_events"], feature_hit_rate=h["f3"]["hit_rate"], baseline_hit_rate=h["base"]["hit_rate"],
                                                 feature_reference_alarm_rate=h["f3"]["reference_alarm_rate"], baseline_reference_alarm_rate=h["base"]["reference_alarm_rate"])
    ev = {}
    for era in ("LEGACY", "RAW"):
        e = json.loads((RES / f"evaluation_{era}.json").read_text(encoding="utf-8"))
        for fam in FAMS:
            g = e["families"][fam]; c = g.get("H1c", {}); lags = [(b["T0_min"] - b["S_min"]) for b in e["breaks"] if b["family"] == fam and b["kind"] == "confirmed"]
            ev.setdefault(era, {})[fam] = dict(n_sessions=e["n_evaluation_sessions"], alarms_per_session=g["alarms_per_session"],
                                               fomc=dict(n_events=c.get("n_events"), feature_hit_rate=(c.get("feature") or {}).get("hit_rate"), baseline_hit_rate=(c.get("baseline") or {}).get("hit_rate"),
                                                         feature_reference_alarm_rate=(c.get("feature") or {}).get("reference_alarm_rate"), baseline_reference_alarm_rate=(c.get("baseline") or {}).get("reference_alarm_rate")),
                                               confirmation_lag_Tc_minus_Td_min=q(lags), pauc_absolute="not stored (difference only); would need a new evaluation read",
                                               h1a_difference=g.get("H1a", {}).get("effect"))
    res = dict(label="POST HOC descriptive (Veksler's point): absolute detection performance. Development folds with saved models; evaluation from already-written outputs only. Changes no frozen, MR2 or evaluation result.",
               code_version=G.code_version(), script_sha256=sha(__file__), units_sha256={p.name: sha(p) for p in files}, development=dev, development_realised_test_alarm_rates=rates,
               development_fomc=fomc, evaluation=ev, minutes=sum(u.get("minutes", 0) for u in us), generated=datetime.datetime.now(datetime.timezone.utc).isoformat())
    FINAL.write_text(json.dumps(res, indent=1, default=float), encoding="utf-8"); FINAL.with_suffix(".sha256").write_text(f"{sha(FINAL)}  {FINAL.name}\n", encoding="ascii")
    TABLES.write_text(tables(res), encoding="utf-8"); TABLES.with_suffix(".sha256").write_text(f"{sha(TABLES)}  {TABLES.name}\n", encoding="ascii")
    print(TABLES.read_text(encoding="utf-8")); return 0


def f3(x): return "–" if x is None else f"{x:.3f}"
def f2(x): return "–" if x is None else f"{x:.2f}"
def dq(d): return "–" if not d else f"{d['median']:.0f} [{d['q25']:.0f}, {d['q75']:.0f}] (n {d['n']})"


def tables(res):
    L = ["# Absolute detection performance (POST HOC, descriptive)", "", res["label"], "",
         f"Source: `section5/results/posthoc_absolute_detection.json`; script `diagnostics/absolute_detection.py` (sha256 `{res['script_sha256']}`); code version `{res['code_version']}`.", "",
         "## 1. Absolute pAUC, development test splices (mean over folds; confirmatory folds)", "", "| Era | Family | Folds scored | pAUC feature | pAUC baseline | Difference |", "|---|---|---|---|---|---|"]
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            r = res["development"][era]["confirmatory"][fam]; a, b = r["feature"]["pauc_mean"], r["baseline"]["pauc_mean"]
            L.append(f"| {era} | {fam} | {r['n_folds_scored']}/{r['n_folds']} | {f3(a)} | {f3(b)} | {f3(None if a is None or b is None else a - b)} |")
    L += ["", "pAUC = area under the curve of hit rate (share of break splices hit within 60 min) against null alarm rate (confirmed alarms per null "
          "spliced session) for null alarm rates 0-0.5, divided by 0.5 (protocol 5.0). The two axes are in different units, so there is no simple "
          "chance level; the baseline column is the returns-only reference.", "",
          "## 2. Detection at the calibrated threshold, by planted variance ratio and direction (development, confirmatory folds, feature model)", "",
          "Hit = T_d after onset and T_c within 60 min (the H1(a) hit). Delay = minutes from onset to T_c: median [IQR] (n). 'Any' = first confirmation after onset before the session end.", ""]
    for era in ("LEGACY", "RAW"):
        L += [f"### {era}", "", "| Family | Ratio, direction | Splices | Hit within 60 min | Delay of those hits | Detected by close | Delay to first confirmation |", "|---|---|---|---|---|---|---|"]
        for fam in FAMS:
            br = res["development"][era]["confirmatory"][fam]["feature"]["by_ratio_direction"]
            for k, v in br.items(): L.append(f"| {fam} | {k.replace('|', ' ')} | {v['n']} | {f2(v['hit60_rate'])} | {dq(v['delay60_min'])} | {f2(v['hit_any_rate'])} | {dq(v['delay_any_min'])} |")
        L += [""]
    L += ["Per duration (permanent, 30, 60, 120 min) and for the baseline models: `development.<era>.<scope>.<family>.<model>.cells` in the JSON.", "",
          "## 3. Alarm rates", "", "| Era | Family | Null splices: alarms per splice, feature / baseline | Real test sessions: alarms per session, feature / baseline (A17 records) |", "|---|---|---|---|"]
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            r = res["development"][era]["confirmatory"][fam]; nf = r["feature"]["cells"].get("null", {}); nb = r["baseline"]["cells"].get("null", {}); rr = res["development_realised_test_alarm_rates"][era][fam]
            L.append(f"| {era} | {fam} | {f3(nf.get('alarms_per_null_splice'))} / {f3(nb.get('alarms_per_null_splice'))} | {f3(rr['feature']['mean_test_alarms_per_session'])} / {f3(rr['baseline']['mean_test_alarms_per_session'])} |")
    L += ["", "Thresholds were calibrated to 0.2 alarms per validation session (A7).", "", "## 4. FOMC hit rates (release to release + 60 min)", "",
          "| Data | Era | Family | Events | Hit rate feature | Hit rate baseline |", "|---|---|---|---|---|---|"]
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            d = res["development_fomc"][era][fam]; L.append(f"| development (A17) | {era} | {fam} | {d['n_events']} | {f2(d['feature_hit_rate'])} | {f2(d['baseline_hit_rate'])} |")
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            d = res["evaluation"][era][fam]["fomc"]; L.append(f"| evaluation (written) | {era} | {fam} | {d['n_events']} | {f2(d['feature_hit_rate'])} | {f2(d['baseline_hit_rate'])} |")
    L += ["", "## 5. Evaluation periods (already-written outputs; adaptive/exploratory label, previously exposed periods)", "",
          "| Era | Family | Sessions | Alarms per session, feature / baseline | Confirmation lag T_c - T_d, min: median [IQR] (n) | Absolute pAUC |", "|---|---|---|---|---|---|"]
    for era in ("LEGACY", "RAW"):
        for fam in FAMS:
            d = res["evaluation"][era][fam]; a = d["alarms_per_session"]
            L.append(f"| {era} | {fam} | {d['n_sessions']} | {f3(a.get('feature'))} / {f3(a.get('baseline'))} | {dq(d['confirmation_lag_Tc_minus_Td_min'])} | not stored |")
    L += ["", "The evaluation outputs store only the pAUC difference (H1a), and a break-onset delay needs a planted onset, so onset delays exist only for the development splices. "
          "Sources: `section5/results/evaluation_{LEGACY,RAW}.json`, `section5/results/a17/a17_results.json`, `section5/results/a17/ckpt/`.", ""]
    return "\n".join(L)


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
