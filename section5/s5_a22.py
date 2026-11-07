#!/usr/bin/env python3
"""A22 (AMENDMENT_A22.md): 5.11 power, D8c, 5.10 robustness on the MR2 setups (era, flagged Student-t fits, threshold target 0.15/0.25, LEGACY delay +5/+10 min, seeds 1-3, RAW
sensitivity pool, 5/15/1-min grids on the era final setups) and the A18 rerun on A20 inputs. One phase per call; the runner calls them in the A22 rule 5a priority order.
Secondary and descriptive; nothing changes the MR2 verdicts, the 5.8 setups or 5.12; no freeze, no era calibration. Contamination POST_MAIN_RUN (D8c: s5_d8c.py, DESCRIPTIVE).
Usage: s5_a22.py PROTOCOL_SHA256 PHASE [--check]
  PHASE: power | d8c | era_flagged | thresholds | delay | a18 | seeds | raw80 | grids | grid1 | grid1_hsmm | all (with --check only)
  --check: unit tests + the phase's preflight on the contaminated RAW 3 and LEGACY 29 folds only; writes only to results/a22_preflight/.
Exit codes: 0 done, 1 crash (retryable; resumes from checkpoints), 2 Ctrl+C, 3 guard refusal or failed preflight, 4 reproduction mismatch (stop)."""
import sys, os, gc, json, time, pickle, hashlib, datetime, traceback, subprocess
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent)); sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

HERE = Path(__file__).resolve().parent; ROOT = HERE.parent; RES = HERE / "results"; OUT = RES / "a22"; PRE = RES / "a22_preflight"; LOG = RES / "a22_log.txt"
MAIN2 = RES / "main_run_2"; A17D = RES / "mr2" / "a17"; A18OUT = RES / "mr2" / "a18"; D7A21 = RES / "mr2" / "d7_a21" / "d7_results.json"; S2 = RES / "step2_liquidity" / "step2_results.json"
CONTAMINATED = ("RAW|3", "LEGACY|29"); FAMILIES = ("gaussian_hmm", "student_t_hmm", "hsmm", "bocpd"); H1F = FAMILIES[:3]
PHASES = ("power", "d8c", "era_flagged", "thresholds", "delay", "a18", "seeds", "raw80", "grids", "grid1", "grid1_hsmm")      # A22 rule 5a order
TARGETS = (0.15, 0.20, 0.25); DELAYS = (0, 5, 10); SEEDS = (1, 2, 3); GRIDS = (5, 15); HSMM1_MAX_H = 24.0
EXIT_OK, EXIT_CRASH, EXIT_STOP, EXIT_GUARD, EXIT_MISMATCH = 0, 1, 2, 3, 4
MIN_NS = 60 * 10 ** 9


class Mismatch(Exception): pass


def log(msg):
    line = f"{datetime.datetime.now().astimezone().isoformat(timespec='seconds')} [py {os.getpid()}] {msg}"; LOG.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG, "a", encoding="utf-8") as f: f.write(line + "\n")
    print(line, flush=True)


def file_sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def roundtrip(x): return json.loads(json.dumps(x, default=float))
def fkey(fold): return fold.replace("|", "_")


def write_json(p, obj):
    p = Path(p); p.parent.mkdir(parents=True, exist_ok=True); tmp = p.with_suffix(".tmp"); tmp.write_text(json.dumps(obj, indent=1, default=float), encoding="utf-8"); tmp.replace(p)


def ck_get(p, tag):
    p = Path(p)
    if p.exists():
        u = json.loads(p.read_text(encoding="utf-8"))
        if u.get("tag") == tag: return u
    return None


def same(a, b):
    import s5_a17_a18_common as CM
    return CM.same(roundtrip(a), roundtrip(b))


# ---------- MR2 records
def mr2_units():
    """(kind, fold, family) -> stored MR2 unit ('select' setup or 'score' record), version-checked against the MR2 completion record."""
    import s5_guard as G
    rec = G.verify_completion(MAIN2 / G.COMPLETION, require_main=True); u = {}
    for p in (MAIN2 / "ckpt").glob("*.json"):
        c = json.loads(p.read_text(encoding="utf-8")); k = c["key"].split("|")
        if c["version"] != rec["checkpoint_version"]: raise PermissionError(f"MR2 checkpoint {p.name} has another version")
        u[(k[0], f"{k[3]}|{k[4]}", k[5])] = c["value"]
    if len(u) != 272: raise PermissionError(f"{len(u)} MR2 units, expected 272")
    return u


def a17_manifest():
    man = json.loads((A17D / "a17_results.json").read_text(encoding="utf-8"))["models_manifest"]
    if len(man) != 136: raise PermissionError(f"MR2 A17-style manifest has {len(man)} models, expected 136")
    return man


def a17_record(fold, fam): return json.loads((A17D / "ckpt" / f"{fkey(fold)}_{fam}.json").read_text(encoding="utf-8"))


def load_models(fold, man):
    import s5_d7 as D
    D.A17 = A17D; return D.load_fold_models(fold, man)                  # sha256 of every pickle checked against the MR2 A17-style manifest


def guards(token):
    import s5_guard as G, s5_contamination as C
    ph = G.verify_frozen_protocol(token); G.canonical_contamination(); C.check_registry(HERE); G.verify_completion(MAIN2 / G.COMPLETION, require_main=True)
    if G.LOCK.exists(): raise PermissionError("era-calibration lock exists (A16 rule 5)")
    a = ROOT / "AMENDMENT_A22.md"
    if not a.exists() or (ROOT / "AMENDMENT_A22.sha256").read_text().split()[0] != file_sha(a): raise PermissionError("AMENDMENT_A22.md missing or its sidecar differs")
    a17_manifest(); return ph


def tag_of(ph, phase):
    import s5_guard as G
    return dict(a22_script=file_sha(__file__), a22=file_sha(ROOT / "AMENDMENT_A22.md"), code_version=G.code_version(), protocol=ph, phase=phase)


def folds_split():
    import s5_guard as G
    excluded, _ = G.excluded_folds(); folds = list(G.MAIN_FOLDS); return folds, excluded, [f for f in folds if f not in excluded]


# ---------- shared scoring helpers
def h1a_points_shifted(db, family, model, subset, deltas):
    """DataBackend._h1a_points with every alarm availability shifted by delta minutes (A22 rule 3d); delta 0 is the original computation. Returns {delta: points}."""
    import s5_eval as V, s5_a7 as B, s5_sweep as W
    sp = db._splices(); null = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] == "null"]; brk = [r for s, r in zip(sp["specs"], sp["rows"]) if s["cell"] != "null"]
    D = 1 + len(subset); grid = B.MGRID if family == "bocpd" else B.THETA; to_des = db.c["to_des"]; mk = db.c["mk"]
    def run_(rl):
        qs = [mk(r, subset) for r in [to_des(r, r["iA"]) for r in rl]]; rs = V.run_filter(family, model, qs, D)
        R_, real, av = W.stack(rs, qs, "rstar" if family == "bocpd" else "P"); return R_, real, av, np.array([r["tau"] for r in rl], np.int64)
    sw = (lambda a, b, c_, t: W.sweep_map(a, b, c_, grid, t)) if family == "bocpd" else (lambda a, b, c_, t: W.sweep_old_state(a, b, c_, grid, t))
    Rn, ren, avn, _ = run_(null); Rb, reb, avb, tb = run_(brk); out = {}
    for dl in deltas:
        cnt, _ = sw(Rn, ren, shift_avail(avn, dl), None); xs = cnt.mean(0); _, h = sw(Rb, reb, shift_avail(avb, dl), tb); out[dl] = list(zip(xs.tolist(), h.mean(0).tolist()))
    return out


def shift_avail(av, dl):
    """Availability times (ns) shifted by dl minutes; padding (0) stays padding."""
    return np.where(av != 0, av + np.int64(dl) * MIN_NS, 0)


def h1c(alarms, deltas_by_fold=None, fams=FAMILIES):
    """H1(c) exactly as s5_a17.aggregate from alarm records {(fold, family): {'feature': {day: [[T_d, T_c], ...]}, 'baseline': ...}}; T_c shifted by deltas_by_fold[fold] minutes."""
    import s5_h1c as HC, s5_guard as G
    j, _ = G.contamination(); ev = j["h1c_eligible_events_per_fold"]; mins = j["h1c_event_release_minute_after_0930"]; fomc = {x for v in ev.values() for x in v}; out = {}
    for fam in fams:
        hf, hb, rf, rb = [], [], [], []
        for key, dates in ev.items():
            era, n = ("LEGACY", key[6:]) if key.startswith("LEGACY") else ("RAW", key[3:]); fold = f"{era}|{int(n)}"; dl = (deltas_by_fold or {}).get(fold, 0)
            af, ab = alarms[(fold, fam)]["feature"], alarms[(fold, fam)]["baseline"]; nonf = [d for d in af if d not in fomc]
            for x in dates:
                m = mins[x]; hf.append(HC.hit([a[1] + dl for a in af.get(x, [])], m)); hb.append(HC.hit([a[1] + dl for a in ab.get(x, [])], m))
                rf.append(HC.reference_rate([[a[1] + dl for a in af[d]] for d in nonf], m)); rb.append(HC.reference_rate([[a[1] + dl for a in ab[d]] for d in nonf], m))
        out[fam] = HC.summarize(fam, hf, hb, float(np.mean(rf)), float(np.mean(rb)))
    return out


def fam_results(eff_a, eff_b, fold_ids, excluded, flagged=None):
    import s5_h1 as H
    fr = {fam: H.family_result([eff_a[(f, fam)] for f in fold_ids], [eff_b[(f, fam)] for f in fold_ids], fold_ids, excluded, 10000, 0,
                               flagged=[bool(flagged[(f, fam)]) for f in fold_ids] if flagged else None) for fam in FAMILIES}
    return dict(family_results=fr, holm={w: H.h1_decision(fr, which=w) for w in ("confirmatory", "all_folds_sensitivity")})


def brief(res):
    return "; ".join(f"{f.split('_')[0]} a {res['family_results'][f]['confirmatory']['H1a']['mean']:+.4f} (p {res['family_results'][f]['confirmatory']['H1a']['p_block_bootstrap']:.3f}) "
                     f"b {res['family_results'][f]['confirmatory']['H1b']['mean']:+.4f} holm {'R' if res['holm']['confirmatory'][f]['reject'] else '-'}" for f in FAMILIES)


# ---------- phase: 5.11 power (A22 rule 4)
def d7_mde(n_days, p0, draws=2000, seed=1907, respond=0.10, grid=None):
    """Smallest true hit-rate difference with >= 80% power under 'difference >= 0.10 and 95% CI excluding 0' (normal-approximation CI; independent days and hits)."""
    rng = np.random.default_rng(seed); grid = grid if grid is not None else np.round(np.arange(0.01, 0.4001, 0.01), 2); curve = {}
    for dl in grid:
        p1 = min(1.0, p0 + dl); h0 = rng.random((draws, n_days)) < p0; h1 = rng.random((draws, n_days)) < p1; x = h1.astype(float) - h0
        m = x.mean(1); se = x.std(1, ddof=1) / np.sqrt(n_days); pw = float(((m >= respond) & (m - 1.959964 * se > 0)).mean()); curve[float(dl)] = pw
        if pw >= 0.8: return dict(mde=float(dl), power=pw, p0=p0, n_days=n_days, curve=curve)
    return dict(mde=None, power=None, p0=p0, n_days=n_days, curve=curve)


def phase_power(ph, out_dir):
    import s5_stats as ST
    units = mr2_units(); folds, excluded, conf = folds_split(); res = dict(label="5.11 power (AMENDMENT_A22.md rule 4)", h1={}, d7={}, step2_d7={})
    for fam in FAMILIES:
        res["h1"][fam] = {}
        for comp in ("a", "b"):
            x = np.array([units[("score", f, fam)][comp] for f in conf if units[("score", f, fam)][comp] is not None], float); sd = float(x.std(ddof=1))
            r = dict(n_folds_observed=int(len(x)), mean=float(x.mean()), sd=sd)
            for lab, al in (("alpha_holm_first_0.0167", 0.05 / 3), ("alpha_0.05", 0.05)):
                m = ST.mde(sd, 26, alpha=al, power=0.8, nsim=400, nboot=500, seed=0) if sd > 0 else dict(mde_in_sd=None, mde=None, power=None)
                r[lab] = dict(m, observed_over_mde=(r["mean"] / m["mde"]) if m.get("mde") else None)
            res["h1"][fam]["H1" + comp] = r
        log(f"A22 power {fam}: H1(a) mean {res['h1'][fam]['H1a']['mean']:+.4f} MDE(.05/3) {res['h1'][fam]['H1a']['alpha_holm_first_0.0167']['mde']}; "
            f"H1(b) mean {res['h1'][fam]['H1b']['mean']:+.4f} MDE(.05/3) {res['h1'][fam]['H1b']['alpha_holm_first_0.0167']['mde']}")
    d7 = json.loads(D7A21.read_text(encoding="utf-8")); s2 = json.loads(S2.read_text(encoding="utf-8"))["d7"]["aggregate"]
    for fam in FAMILIES:
        res["d7"][fam] = d7_mde(int(d7["n_days"]), float(d7["types"]["pc_ratio3"][f"{fam}|feature"]["rate0"]))
        res["step2_d7"][fam] = d7_mde(int(s2["n_days"]), float(s2["types"]["pc_ratio3"][f"{fam}|feature"]["rate0"]))
    log("A22 power D7 MDE (feature models): " + ", ".join(f"{f.split('_')[0]} {res['d7'][f]['mde']}" for f in FAMILIES) + "; Step 2 D7: " + ", ".join(f"{f.split('_')[0]} {res['step2_d7'][f]['mde']}" for f in FAMILIES))
    res["sources"] = dict(mr2_record=file_sha(MAIN2 / "run_complete.json"), d7_a21=file_sha(D7A21), step2=file_sha(S2)); write_json(out_dir / "power.json", res); return res


# ---------- phase: era split and flagged fits (A22 rules 3a, 3b)
def phase_era_flagged(ph, out_dir):
    units = mr2_units(); folds, excluded, conf = folds_split(); summ = json.loads((MAIN2 / "run_summary.json").read_text(encoding="utf-8"))
    ea = {(f, fam): units[("score", f, fam)]["a"] for f in folds for fam in FAMILIES}; eb = {(f, fam): units[("score", f, fam)]["b"] for f in folds for fam in FAMILIES}
    fl = {(f, fam): units[("score", f, fam)]["flagged_fit"] for f in folds for fam in FAMILIES}
    full = fam_results(ea, eb, folds, excluded, fl)
    if not same(full["family_results"], summ["family_results"]) or not same(full["holm"], summ["holm"]): raise Mismatch("recomputed MR2 family results differ from run_summary.json")
    res = dict(label="5.10 era split and Student-t flagged fits (AMENDMENT_A22.md rules 3a, 3b)", reproduces_mr2_summary=True, eras={},
               flagged=dict(n_flagged={fam: sum(bool(fl[(f, fam)]) for f in folds) for fam in FAMILIES}))
    for era in ("LEGACY", "RAW"):
        ef = [f for f in folds if f.startswith(era + "|")]; r = fam_results(ea, eb, ef, excluded)
        r["per_fold_confirmatory"] = {fam: {f: dict(a=ea[(f, fam)], b=eb[(f, fam)]) for f in ef if f not in excluded} for fam in FAMILIES}; res["eras"][era] = r
        log(f"A22 era {era} ({len([f for f in ef if f not in excluded])} confirmatory folds): {brief(r)}")
    st = res["flagged"]["n_flagged"]["student_t_hmm"]; res["flagged"]["student_t_excluding_flagged"] = "identical to the MR2 confirmatory result (0 flagged fits)" if st == 0 else full["family_results"]["student_t_hmm"].get("excluding_flagged_fits")
    log(f"A22 flagged fits: {res['flagged']['n_flagged']}"); write_json(out_dir / "era_flagged.json", res); return res


# ---------- phase: thresholds 0.15 / 0.20 / 0.25 (A22 rule 3c)
def threshold_unit(db, fold, models, thr_stored):
    import s5_eval as V, s5_a7 as B
    d = db.c["d"]; out = {}
    for fam in FAMILIES:
        out[fam] = {}
        for w in ("feature", "baseline"):
            m, sub = models[fam][w]; D = 1 + len(sub); qs = db.sequences("val", sub); rs = V.run_filter(fam, m, qs, D); lo, hi, tol = B.BOUNDS["bocpd" if fam == "bocpd" else "hmm"]
            rate = lambda th: sum(len(B.events(fam, r, q, th)) for q, r in zip(qs, rs)) / len(qs)
            qt = db.sequences("test", sub); rt = V.run_filter(fam, m, qt, D); rec = {}
            for tg in TARGETS:
                th, info = B.bisect_threshold(rate, lo, hi, tg, tol); al = {}
                for q, r in zip(qt, rt): al[str(d["day"][d["first"][q["sess"]]])] = [[int(q["slots"][e["i_d"]]) + 1, int(q["slots"][e["i_c"]]) + 1] for e in (B.events(fam, r, q, th) if q["n"] else [])]
                rec[f"{tg:.2f}"] = dict(threshold=float(th), info=info, validation_rate=float(rate(th)), test_rate=float(sum(len(v) for v in al.values()) / len(qt)), n_test=len(qt), alarms=al)
            if rec["0.20"]["threshold"] != thr_stored[fam][w]: raise Mismatch(f"{fold} {fam} {w}: threshold at 0.20 {rec['0.20']['threshold']!r} != stored {thr_stored[fam][w]!r}")
            out[fam][w] = rec
    return out


def phase_thresholds(ph, out_dir, folds=None, backend=None, check_alarms=True):
    import s5_main as MB, s5_guard as G
    man = a17_manifest(); _, excluded, conf = folds_split(); folds = folds or conf; tag = tag_of(ph, "thresholds"); b = backend or MB.MainBackend(ph); units = {}
    for k, fold in enumerate(folds, 1):
        p = out_dir / "thresholds" / "ckpt" / f"{fkey(fold)}.json"; u = ck_get(p, tag)
        if u is None:
            G.check_unlocked("A22 thresholds"); t0 = time.time(); models, thr = load_models(fold, man); u = dict(fold=fold, units=threshold_unit(b._b(fold), fold, models, thr), tag=tag)
            if check_alarms:
                for fam in FAMILIES:
                    st = a17_record(fold, fam)["alarms"]
                    for w in ("feature", "baseline"):
                        if not same(u["units"][fam][w]["0.20"]["alarms"], st[w]): raise Mismatch(f"{fold} {fam} {w}: test alarms at 0.20 differ from the MR2 A17-style record")
            write_json(p, u); log(f"A22 thresholds {k}/{len(folds)} {fold}: 0.20 reproduced exactly; " + ", ".join(f"{f.split('_')[0]} " + "/".join(f"{u['units'][f]['feature'][t]['threshold']:.2f}" for t in ('0.15', '0.20', '0.25')) for f in FAMILIES) + f"; {(time.time() - t0) / 60:.1f} min")
        units[fold] = u
    if folds != conf: return units
    res = dict(label="5.10 threshold target 0.15 / 0.20 / 0.25 (AMENDMENT_A22.md rule 3c)", targets={}, reproduces_mr2_thresholds_and_alarms_at_0_20=True)
    for tg in ("0.15", "0.20", "0.25"):
        al = {(f, fam): {w: units[f]["units"][fam][w][tg]["alarms"] for w in ("feature", "baseline")} for f in conf for fam in FAMILIES}
        rates = {fam: {w: dict(median_test_rate=float(np.median([units[f]["units"][fam][w][tg]["test_rate"] for f in conf])), mean_test_rate=float(np.mean([units[f]["units"][fam][w][tg]["test_rate"] for f in conf])),
                           flagged=[f for f in conf if units[f]["units"][fam][w][tg]["info"] != "ok"]) for w in ("feature", "baseline")} for fam in FAMILIES}
        res["targets"][tg] = dict(h1c=h1c(al), realised_test_alarm_rate=rates)
        log(f"A22 thresholds target {tg}: H1(c) hit f/b " + ", ".join(f"{f.split('_')[0]} {res['targets'][tg]['h1c'][f]['f3']['hit_rate']:.2f}/{res['targets'][tg]['h1c'][f]['base']['hit_rate']:.2f} (p {res['targets'][tg]['h1c'][f]['paired']['p_two_sided']:.2f})" for f in FAMILIES)
            + "; median test rate (feature) " + ", ".join(f"{rates[f]['feature']['median_test_rate']:.3f}" for f in FAMILIES))
    a17h = json.loads((A17D / "a17_results.json").read_text(encoding="utf-8"))["h1c"]
    if not all(same({k: v for k, v in a17h[f].items() if k != "events"}, res["targets"]["0.20"]["h1c"][f]) for f in FAMILIES): raise Mismatch("H1(c) at 0.20 differs from the MR2 A17-style result")
    res["reproduces_mr2_h1c_at_0_20"] = True; write_json(out_dir / "thresholds.json", res); return res


# ---------- phase: LEGACY delay (A22 rule 3d)
def delay_unit(db, fold, models, stored):
    import s5_h1 as H
    out = {}; n = db._splices()["n_stable"]; failed = db._splices()["why"] if (n >= 8 and not db._splices()["specs"]) else None
    for fam in FAMILIES:
        if n < 8 or failed: eff = {dl: H.h1a_fold_effect([], [], n, failed=failed)["effect"] for dl in DELAYS}
        else:
            (mf, sf), (mb, sb) = models[fam]["feature"], models[fam]["baseline"]; pf = h1a_points_shifted(db, fam, mf, sf, DELAYS); pb = h1a_points_shifted(db, fam, mb, sb, DELAYS)
            eff = {dl: H.h1a_fold_effect(pf[dl], pb[dl], n)["effect"] for dl in DELAYS}
        if not same(eff[0], stored[fam]): raise Mismatch(f"{fold} {fam}: delay 0 H1(a) {eff[0]!r} != MR2 {stored[fam]!r}")
        out[fam] = {str(dl): eff[dl] for dl in DELAYS}
    return out


def phase_delay(ph, out_dir, folds=None, backend=None):
    import s5_main as MB, s5_guard as G
    man = a17_manifest(); units = mr2_units(); allf, excluded, conf = folds_split(); leg = [f for f in conf if f.startswith("LEGACY|")]; folds = folds or leg; tag = tag_of(ph, "delay"); b = backend or MB.MainBackend(ph); recs = {}
    for k, fold in enumerate(folds, 1):
        p = out_dir / "delay" / "ckpt" / f"{fkey(fold)}.json"; u = ck_get(p, tag)
        if u is None:
            G.check_unlocked("A22 delay"); t0 = time.time(); models, _ = load_models(fold, man); db = b._b(fold)
            u = dict(fold=fold, effects=delay_unit(db, fold, models, {fam: units[("score", fold, fam)]["a"] for fam in FAMILIES}), tag=tag); write_json(p, u)
            log(f"A22 delay {k}/{len(folds)} {fold}: delta 0 reproduced exactly; H1(a) 0/5/10 " + ", ".join(f"{f.split('_')[0]} " + "/".join("NA" if u['effects'][f][str(dl)] is None else f"{u['effects'][f][str(dl)]:+.3f}" for dl in DELAYS) for f in FAMILIES) + f"; {(time.time() - t0) / 60:.1f} min")
        recs[fold] = u
    if folds != leg: return recs
    res = dict(label="5.10 LEGACY decision delay +5/+10 min (AMENDMENT_A22.md rule 3d)", delays={}, reproduces_mr2_at_delta_0=True)
    eb = {(f, fam): units[("score", f, fam)]["b"] for f in conf for fam in FAMILIES}
    alarms = {(f, fam): a17_record(f, fam)["alarms"] for f in conf for fam in FAMILIES}
    for dl in DELAYS:
        ea = {(f, fam): (recs[f]["effects"][fam][str(dl)] if f in recs else units[("score", f, fam)]["a"]) for f in conf for fam in FAMILIES}
        r = fam_results(ea, eb, conf, set()); r["h1c"] = h1c(alarms, {f: dl for f in leg}); res["delays"][str(dl)] = dict(confirmatory=r["family_results"], holm=r["holm"]["confirmatory"], h1c=r["h1c"])
        log(f"A22 delay +{dl} min: {brief(r)}")
    summ = json.loads((MAIN2 / "run_summary.json").read_text(encoding="utf-8"))
    if not all(same(res["delays"]["0"]["confirmatory"][f]["all_folds_sensitivity"], summ["family_results"][f]["confirmatory"]) for f in FAMILIES): raise Mismatch("delay 0 fold tests differ from MR2 confirmatory")
    write_json(out_dir / "delay.json", res); return res


# ---------- phase: A18 rerun on A20 inputs (A22 rule 2)
def a18_analyse(summ):
    import s5_h1 as H, s5_posthoc_main as PH, s5_a17_a18_common as CM
    from collections import Counter
    per = summ["_per_fold"]; folds = summ["folds"]; excluded = set(summ["excluded"]); main = {(f, fam): v["features"] for (k, f, fam), v in mr2_units().items() if k == "select"}
    out = dict(label="A18 rerun on A20 inputs (AMENDMENT_A22.md rule 2): selection by one-step-ahead predictive log-likelihood; compared with MR2", d1={}, nonvol_share={}, h1={})
    for fam in H.FAMILIES:
        sets = {f: per[fam][f]["setup"]["features"] for f in folds}; fams = {f: [PH.family_of(c) for c in s] for f, s in sets.items()}
        nonvol = lambda fs: any(x in CM.NONVOL_FAMILIES for x in fs); mainf = {f: [PH.family_of(c) for c in main[(f, fam)]] for f in folds}
        out["d1"][fam] = dict(mean_features=float(np.mean([len(s) for s in sets.values()])), folds_with_no_feature=sum(1 for s in sets.values() if not s),
                              feature_frequency=dict(Counter(c for s in sets.values() for c in s).most_common()), family_frequency_folds=dict(Counter(x for fs in fams.values() for x in set(fs)).most_common()),
                              same_family_coselection_folds=dict(Counter(x for fs in fams.values() for x, n in Counter(fs).items() if n >= 2).most_common()),
                              same_features_as_mr2_folds=sum(1 for f in folds if sorted(sets[f]) == sorted(main[(f, fam)])), per_fold=sets)
        out["nonvol_share"][fam] = dict(all_folds=sum(nonvol(fams[f]) for f in folds) / len(folds), confirmatory=sum(nonvol(fams[f]) for f in folds if f not in excluded) / sum(1 for f in folds if f not in excluded),
                                        mr2_all_folds=sum(nonvol(mainf[f]) for f in folds) / len(folds))
        out["h1"][fam] = {w: dict(H1a=summ["family_results"][fam][w]["H1a"], H1b=summ["family_results"][fam][w]["H1b"], p_iu=summ["family_results"][fam][w]["p_iu"], holm=summ["holm"][w][fam]) for w in ("confirmatory", "all_folds_sensitivity")}
    return out


def phase_a18(ph, out_dir):
    import s5_a18 as A18, s5_run as RUN, s5_a17_a18_common as CM
    CM.LOG = LOG; t0 = time.time(); log(f"A22 A18 rerun start (kind {A18.KIND}; resumes from {A18OUT / 'run' / 'ckpt'})")
    summ = RUN.run_all(A18.Logged(A18.A18Main(ph)), A18OUT / "run"); res = a18_analyse(summ)
    res.update(kind=A18.KIND, completion_record=summ["completion_record"], a22=file_sha(ROOT / "AMENDMENT_A22.md"), hours=(time.time() - t0) / 3600); write_json(A18OUT / "a18_results.json", res)
    log("A22 A18 rerun DONE: confirmatory Holm " + ", ".join(f"{f.split('_')[0]} p_iu {res['h1'][f]['confirmatory']['p_iu']:.4f} {'R' if res['h1'][f]['confirmatory']['holm']['reject'] else '-'}" for f in FAMILIES)); return res


# ---------- backends for seeds, RAW pool and grids
def _classes():
    import s5_backend as BK, s5_main as MB, s5_lib as L, s5_eval as V, s5_d2 as D2, s5_d2_stable as S, s5_a6 as A, s5_a7 as B, s5_fast as F

    class SeedBackend(BK.DataBackend):
        """A22 rule 3e: model start seed and H1(a) splice seed = self.seed (MR2: 0 and 4242)."""
        kind = "a22_seed"; seed = 0; dmax = 78

        def fit(self, family, subset, params, starts):
            key = (family, tuple(subset), tuple(sorted(params.items())), starts)
            if key not in self._fits:
                m = V.make_model(family, K=params.get("K", 3), lam=params.get("lam", 39), starts=starts, seed=self.seed, Dmax=self.dmax); D = 1 + len(subset); m.fit(L.pad(self.sequences("train", subset), D)); self._fits[key] = m
            return self._fits[key]

        def _splices(self):
            if self._splice is None:
                c = self.c; stable, _ = S.stable_days(c["d"], c["seg"]["test"], c["dv"]); rng = np.random.default_rng(self.splice_seed); cells = [(R, dr, du) for R in B.SIZES for dr in B.DIRS for du in B.DURS]
                specs, why = A.build_specs_safe(c["d"], c["dv"], stable, rng, A.N_NULL, cells, A.N_CELL, min_days=self.min_days); rows = []
                if specs: D2._W.update(d=c["d"], cols=c["cols"], bases=F.load_bases(c["d"], self.era, c["cols"]), dv=c["dv"]); rows = [D2._work(s) for s in specs]
                self._splice = dict(n_stable=len(stable), specs=specs, rows=rows, why=why)
            return self._splice

    class SeedMain(MB.MainBackend):
        kind = "a22_seed"

        def __init__(self, ph, seed, splice_seed, ctx_fn=None, dmax=78, fold_cls=SeedBackend):
            super().__init__(ph); self.seed, self.splice_seed, self.ctx_fn, self.dmax, self.fold_cls = seed, splice_seed, ctx_fn or BK.era_context, dmax, fold_cls

        def _ctx(self, era):
            if self._era is None or self._era["era"] != era:
                self._cur = self._era_b = self._era = None; gc.collect(); self._era = self.ctx_fn(era)
            return self._era

        def _b(self, fold):
            if self._cur is None or self._cur.id != fold:
                era, n = fold.split("|"); self._cur = None; gc.collect()
                self._cur = self.fold_cls(era, int(n), allowed=set(self.ids), protocol_sha256=self.protocol_sha256, shared=self._ctx(era)); self._cur.seed, self._cur.splice_seed, self._cur.dmax = self.seed, self.splice_seed, self.dmax
            return self._cur
    return SeedBackend, SeedMain


def seed_fold(era, n, seed, splice_seed, shared=None, dmax=78):
    SeedBackend, _ = _classes(); db = SeedBackend(era, int(n), shared=shared); db.seed, db.splice_seed, db.dmax = seed, splice_seed, dmax; return db


def phase_seeds(ph, out_dir, folds=None, seeds=SEEDS, mains=None):
    import s5_run as RUN, s5_guard as G
    _, SeedMain = _classes(); units = mr2_units(); allf, excluded, conf = folds_split(); folds = folds or conf; tag = tag_of(ph, "seeds"); recs = {}
    for s in seeds:
        b = (mains or {}).get(s) or SeedMain(ph, s, s)
        for k, fold in enumerate(folds, 1):
            t0 = time.time(); done = []
            for fam in FAMILIES:
                p = out_dir / "seeds" / "ckpt" / f"s{s}_{fkey(fold)}_{fam}.json"; u = ck_get(p, tag)
                if u is None:
                    G.check_unlocked("A22 seeds"); sc = RUN.score_fold(b, fold, fam, units[("select", fold, fam)]); u = dict(seed=s, fold=fold, family=fam, score=roundtrip(sc), tag=tag); write_json(p, u); done.append(fam)
                recs[(s, fold, fam)] = u
            if done: log(f"A22 seed {s} {k}/{len(folds)} {fold}: " + ", ".join(f"{f.split('_')[0]} a {recs[(s, fold, f)]['score']['a']} b {recs[(s, fold, f)]['score']['b']:+.4f}" for f in FAMILIES) + f"; {(time.time() - t0) / 60:.1f} min")
        del b; gc.collect()
    if folds != conf or tuple(seeds) != SEEDS: return recs
    res = dict(label="5.10 seeds 1, 2, 3 for starts and splices (AMENDMENT_A22.md rule 3e); seed 0 = MR2", seeds={})
    ea0 = {(f, fam): units[("score", f, fam)]["a"] for f in conf for fam in FAMILIES}; eb0 = {(f, fam): units[("score", f, fam)]["b"] for f in conf for fam in FAMILIES}
    res["seeds"]["0"] = fam_results(ea0, eb0, conf, set())
    for s in SEEDS:
        ea = {(f, fam): recs[(s, f, fam)]["score"]["a"] for f in conf for fam in FAMILIES}; eb = {(f, fam): recs[(s, f, fam)]["score"]["b"] for f in conf for fam in FAMILIES}
        res["seeds"][str(s)] = fam_results(ea, eb, conf, set()); log(f"A22 seed {s}: {brief(res['seeds'][str(s)])}")
    res["spread"] = {fam: {c: dict(min=min(res["seeds"][s]["family_results"][fam]["all_folds_sensitivity"][c]["mean"] for s in res["seeds"]), max=max(res["seeds"][s]["family_results"][fam]["all_folds_sensitivity"][c]["mean"] for s in res["seeds"]),
                                   holm_rejects=sum(res["seeds"][s]["holm"]["all_folds_sensitivity"][fam]["reject"] for s in res["seeds"]) if fam in H1F else None) for c in ("H1a", "H1b")} for fam in FAMILIES}
    write_json(out_dir / "seeds.json", res); return res


# ---------- phase: RAW sensitivity pool (A22 rule 3f)
def era_context_sens(era):
    import s5_lib as L, s5_d2_stable as S
    _, sens, _ = L.pools(); cols = L.a20_pool(sens); L.assert_pool(cols, "sensitivity")
    if len(cols) != 69: raise RuntimeError(f"sensitivity pool under A20 has {len(cols)} columns, expected 69")
    d = L.load_era(era, cols + ["lee_mykland_approx60"]); dv = S.des_variance(d); d["dv"] = dv
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), 78), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    return dict(era=era, d=d, dv=dv, cols=cols, native=native, Mx=Mx, pool="sensitivity69")


def _sens_classes():
    import s5_backend as BK, s5_main as MB

    class SensBackend(BK.DataBackend):
        kind = "a22_raw80_fold"

        def _build(self):
            if self._shared is None: self._shared = era_context_sens(self.era)
            if self._shared.get("pool") != "sensitivity69": raise RuntimeError("RAW-pool backend without the sensitivity context")
            return super()._build()

    class SensMain(MB.MainBackend):
        kind = "a22_raw80"

        def __init__(self, ph): super().__init__(ph); self.ids_run = [f"RAW|{i}" for i in range(4)]
        def folds(self): return list(self.ids_run)

        def _ctx(self, era):
            if self._era is None or self._era["era"] != era:
                self._cur = self._era_b = self._era = None; gc.collect(); self._era = era_context_sens(era)
            return self._era

        def _b(self, fold):
            if self._cur is None or self._cur.id != fold:
                era, n = fold.split("|"); self._cur = None; gc.collect(); self._cur = SensBackend(era, int(n), allowed=set(self.ids), protocol_sha256=self.protocol_sha256, shared=self._ctx(era))
            return self._cur
    return SensBackend, SensMain


class Logged:
    def __init__(self, b, name): self._b = b; self.name = name; self._t0 = None; self.kind = b.kind
    def __getattr__(self, n): return getattr(self._b, n)
    def objective(self, fold, family): self._t0 = time.time(); return self._b.objective(fold, family)
    def score(self, fold, family, setup):
        sel = f"selection {(time.time() - self._t0) / 60:.1f} min" if self._t0 else "selection from checkpoint"; self._t0 = None; t0 = time.time(); r = self._b.score(fold, family, setup)
        log(f"  {self.name} {fold} {family}: {sel}; features {setup['features']} params {setup['params']} baseline {setup['base_params']}; scoring {(time.time() - t0) / 60:.1f} min"); return r


def phase_raw80(ph, out_dir):
    import s5_run as RUN
    _, SensMain = _sens_classes(); units = mr2_units(); t0 = time.time(); log("A22 RAW sensitivity pool (69 columns) start: RAW 0-3, 5.8 selection and scoring")
    summ = RUN.run_all(Logged(SensMain(ph), "A22 raw80"), out_dir / "raw80" / "run"); per = summ["_per_fold"]
    res = dict(label="5.10 RAW sensitivity pool: 80 columns under the A20 rule = 69 (AMENDMENT_A22.md rule 3f); RAW 0 confirmatory, RAW 1-3 all-folds only", completion_record=summ["completion_record"],
               family_results=summ["family_results"], holm=summ["holm"], per_fold={fam: {f: dict(features=per[fam][f]["setup"]["features"], params=per[fam][f]["setup"]["params"], base_params=per[fam][f]["setup"]["base_params"],
               a=per[fam][f]["score"]["a"], b=per[fam][f]["score"]["b"], mr2_features=units[("select", f, fam)]["features"], mr2_a=units[("score", f, fam)]["a"], mr2_b=units[("score", f, fam)]["b"]) for f in summ["folds"]} for fam in FAMILIES},
               hours=(time.time() - t0) / 3600)
    write_json(out_dir / "raw80.json", res); log("A22 RAW pool DONE: " + "; ".join(f"{fam.split('_')[0]} " + ", ".join(f"{f}: {res['per_fold'][fam][f]['features']} b {res['per_fold'][fam][f]['b']:+.4f} (MR2 {res['per_fold'][fam][f]['mr2_b']:+.4f})" for f in summ["folds"]) for fam in FAMILIES)); return res


# ---------- phase: grids (A22 rule 3g)
class Grid:
    """Sets the s5_lib decision grid to G minutes inside the block (bars stamped G-1, 2G-1, ...); restores 5 minutes after."""
    def __init__(self, g): self.g = g
    def __enter__(self):
        import s5_lib as L
        self.old = (L.GRID, L.FIRST_SLOT); L.GRID, L.FIRST_SLOT = self.g, self.g - 1; return self
    def __exit__(self, *a):
        import s5_lib as L
        L.GRID, L.FIRST_SLOT = self.old


def era_context_grid(era):
    import s5_lib as L, s5_backend as BK
    if L.GRID == 5: return BK.era_context(era)
    primary, _, _ = L.pools(); cols = L.a20_pool(primary); import s5_d2_stable as S
    d = L.load_era(era, cols + ["lee_mykland_approx60"]); dv = S.des_variance(d); d["dv"] = dv; W = len(L.grid_slots(390))
    native = [L.session_grid(d, i, cols) for i in range(len(d["first"]))]; Mx = np.full((len(native), W), np.nan)
    for i, r in enumerate(native): Mx[i, :len(r["X"])] = r["X"][:, 0]
    return dict(era=era, d=d, dv=dv, cols=cols, native=native, Mx=Mx, grid=L.GRID)


def grid_score(db, fold, fam, setup, g):
    import s5_h1 as H
    s = db.score(fold, fam, dict(setup, val_qlike=None)); a = H.h1a_fold_effect(s["points_feat"], s["points_base"], s["n_stable_test"], failed=s.get("h1a_failed"))
    b = H.h1b_fold_effect(s["loss_base"], s["key_base"], s["loss_feat"], s["key_feat"], lag=60 // g)
    return roundtrip(dict(a=a["effect"], a_skipped=a["skipped"], a_failed=a.get("failed"), b=b["effect"], b_skipped=b["skipped"], b_n=b["n"], b_dm_stat=(b["dm"] or {}).get("stat"), flagged_fit=bool(s.get("flagged_fit", False))))


def final_setups():
    return json.loads((MAIN2 / "run_summary.json").read_text(encoding="utf-8"))["final_setups"]


def phase_grid(ph, out_dir, grids, fams, label, folds=None, dbs=None):
    import s5_guard as G
    _, SeedMain = _classes(); allf, excluded, conf = folds_split(); folds = folds or conf; fs = final_setups(); tag = tag_of(ph, "grids"); recs = {}
    for g in grids:
        with Grid(g):
            b = None if dbs else SeedMain(ph, 0, 4242, ctx_fn=era_context_grid, dmax=390 // g)
            for k, fold in enumerate(folds, 1):
                t0 = time.time(); done = []; era = fold.split("|")[0]
                for fam in fams:
                    p = out_dir / "grids" / "ckpt" / f"g{g}_{fkey(fold)}_{fam}.json"; u = ck_get(p, tag)
                    if u is None:
                        G.check_unlocked("A22 grids"); st = {x: fs[era][fam][x] for x in ("features", "params", "base_params")}
                        db = dbs[(g, fold)] if dbs else b._b(fold); u = dict(grid=g, fold=fold, family=fam, setup=st, score=grid_score(db, fold, fam, st, g), tag=tag); write_json(p, u); done.append(fam)
                    recs[(g, fold, fam)] = u
                if done: log(f"A22 grid {g} min {k}/{len(folds)} {fold}: " + ", ".join(f"{f.split('_')[0]} a {recs[(g, fold, f)]['score']['a']} b {recs[(g, fold, f)]['score']['b']}" for f in done) + f"; {(time.time() - t0) / 60:.1f} min")
            del b; gc.collect()
    if folds != conf: return recs
    path = out_dir / "grids.json"; res = json.loads(path.read_text(encoding="utf-8")) if path.exists() else dict(label="5.10 grids on the MR2 era final setups (AMENDMENT_A22.md rule 3g); 5 min = reference", grids={})
    for g in grids:
        ea = {(f, fam): recs[(g, f, fam)]["score"]["a"] for f in conf for fam in fams}; eb = {(f, fam): recs[(g, f, fam)]["score"]["b"] for f in conf for fam in fams}
        import s5_h1 as H
        fr = {fam: H.family_result([ea[(f, fam)] for f in conf], [eb[(f, fam)] for f in conf], conf, set(), 10000, 0) for fam in fams}
        res["grids"].setdefault(str(g), {}).update({fam: fr[fam]["all_folds_sensitivity"] for fam in fams}); res["grids"][str(g)]["final_setups"] = fs
        log(f"A22 grid {g} min ({label}): " + "; ".join(f"{f.split('_')[0]} a {fr[f]['all_folds_sensitivity']['H1a']['mean']:+.4f} (p {fr[f]['all_folds_sensitivity']['H1a']['p_block_bootstrap']:.3f}) b {fr[f]['all_folds_sensitivity']['H1b']['mean']:+.4f} (p {fr[f]['all_folds_sensitivity']['H1b']['p_block_bootstrap']:.3f})" for f in fams))
    for g in res["grids"]:                                                         # A15 rule 6a: a family not (yet) scored enters Holm as p = 1 and counts in m
        res["grids"][g]["holm"] = __import__("s5_stats").holm({f: (res["grids"][g][f]["p_iu"] if f in res["grids"][g] else float("nan")) for f in H1F})
    write_json(path, res); return res


def hsmm1_projection(dbs):
    """A22 rule 3h: seconds per EM iteration of the 1-min HSMM (feature model of the final setup, Dmax 390) on the preflight folds, times the mean iterations per start of the MR2 5-min
    HSMM fits (A17-style pickles), times 3 starts x 2 models x 26 folds."""
    import s5_eval as V, s5_lib as L
    man = a17_manifest(); its = []
    for name in man:
        if name.endswith("_hsmm.pkl"):
            o = pickle.loads((A17D / "models" / name).read_bytes())
            for m in (o["feature"], o["baseline"]): its += list(m.fit_info["iterations"])
    fs = final_setups(); per = []
    for (g, fold), db in dbs.items():
        if g != 1: continue
        st = fs[fold.split("|")[0]]["hsmm"]; sub = tuple(st["features"]); batch = L.pad(db.sequences("train", sub), 1 + len(sub))
        m = V.make_model("hsmm", K=st["params"]["K"], starts=1, seed=0, Dmax=390); m._init(batch, np.random.default_rng(0)); t0 = time.time(); m._em_step(batch); m._em_step(batch); per.append((time.time() - t0) / 2)
    sec = float(np.mean(per)); mean_it = float(np.mean(its)); hours = sec * mean_it * 3 * 2 * 26 / 3600
    return dict(seconds_per_iteration=sec, per_fold_seconds=per, mean_iterations_per_start_5min=mean_it, projected_hours_26_folds=hours, limit_hours=HSMM1_MAX_H, run=bool(hours <= HSMM1_MAX_H))


def phase_grid1_hsmm(ph, out_dir):
    pj = PRE / "hsmm1_projection.json"
    if not pj.exists(): raise PermissionError("no 1-min HSMM projection from the preflight (A22 rule 3h)")
    p = json.loads(pj.read_text(encoding="utf-8")); rec = dict(label="1-min HSMM (AMENDMENT_A22.md rule 3h)", projection=p)
    if not p["run"]:
        rec["status"] = f"NOT RUN: projected {p['projected_hours_26_folds']:.1f} h > {HSMM1_MAX_H} h"; write_json(out_dir / "grid1_hsmm.json", rec); log(f"A22 1-min HSMM {rec['status']} (rule 3h)"); return rec
    r = phase_grid(ph, out_dir, (1,), ("hsmm",), "1-min HSMM"); rec["status"] = "run"; write_json(out_dir / "grid1_hsmm.json", rec); return r


# ---------- preflight (A22 rule 5b)
def preflight(token, which):
    import unittest, s5_guard as G, s5_backend as BK, s5_run as RUN, s5_a18 as A18, s5_a17_a18_common as CM
    ph = guards(token); t0 = time.time(); PRE.mkdir(parents=True, exist_ok=True); excluded, _ = G.excluded_folds()
    if not set(CONTAMINATED) <= excluded: raise PermissionError("preflight folds must be contaminated")
    r = unittest.TextTestRunner(verbosity=0).run(unittest.defaultTestLoader.loadTestsFromName("s5_tests_a22"))
    if not r.wasSuccessful(): raise RuntimeError(f"A22 unit tests failed: {len(r.failures)} failures, {len(r.errors)} errors")
    log(f"A22 preflight [{which}]: protocol {ph[:16]}... FROZEN, MR2 record, canonical list, no lock, registry ok, A22 sidecar ok; {r.testsRun} A22 unit tests pass")
    units = mr2_units(); man = a17_manifest(); rep = {}
    class One:
        kind = "check"
        def __init__(s, db): s.db = db
        def __getattr__(s, n): return getattr(s.db, n)
        def _b(s, fold): return s.db
    if which in ("all", "cheap"):
        rep["power"] = phase_power(ph, PRE)["h1"]; rep["era_flagged"] = phase_era_flagged(ph, PRE)["flagged"]
        rc = subprocess.run([sys.executable, str(HERE / "s5_d8c.py"), "--check"], capture_output=True, text=True)
        if rc.returncode != 0: raise RuntimeError(f"D8c preflight failed: {rc.stderr[-500:]}")
        log(f"A22 preflight D8c (RAW era): {rc.stdout.strip().splitlines()[-1]}")
    if which in ("all", "cheap"):
        for fold in CONTAMINATED:
            era, n = fold.split("|"); db = BK.DataBackend(era, int(n)); t1 = time.time()
            phase_thresholds(ph, PRE, folds=[fold], backend=One(db))
            if era == "LEGACY": phase_delay(ph, PRE, folds=[fold], backend=One(db))
            log(f"A22 preflight thresholds{' + delay' if era == 'LEGACY' else ''} {fold}: reproduced MR2 exactly; {(time.time() - t1) / 60:.1f} min"); del db; gc.collect()
    if which in ("all", "a18"):
        for fold in CONTAMINATED:
            era, n = fold.split("|"); db = A18.A18Fold(era, int(n)); t1 = time.time()
            for fam in FAMILIES:
                st = RUN.select_fold(One(db), fold, fam); sc = RUN.score_fold(One(db), fold, fam, st)
                if sc["b"] is None: raise RuntimeError(f"A18 preflight {fold} {fam}: H1(b) not evaluable")
                log(f"A22 preflight A18 {fold} {fam}: features {st['features']} params {st['params']} baseline {st['base_params']}; H1(a) {sc['a']}, H1(b) {sc['b']:+.4f}")
            log(f"A22 preflight A18 {fold}: {(time.time() - t1) / 60:.1f} min"); del db; gc.collect()
    if which in ("all", "seeds"):
        for fold in CONTAMINATED:
            era, n = fold.split("|"); ctx = BK.era_context(era); db = seed_fold(era, n, 1, 1, shared=ctx); t1 = time.time()
            for fam in FAMILIES:
                sc = RUN.score_fold(One(db), fold, fam, units[("select", fold, fam)])
                if sc["b"] is None: raise RuntimeError(f"seed preflight {fold} {fam}: H1(b) not evaluable")
                log(f"A22 preflight seed 1 {fold} {fam}: H1(a) {sc['a']} (MR2 {units[('score', fold, fam)]['a']}), H1(b) {sc['b']:+.4f} (MR2 {units[('score', fold, fam)]['b']:+.4f})")
            db0 = seed_fold(era, n, 0, 4242, shared=ctx)
            sc0 = RUN.score_fold(One(db0), fold, "gaussian_hmm", units[("select", fold, "gaussian_hmm")])
            if not same(sc0, units[("score", fold, "gaussian_hmm")]): raise Mismatch(f"seed backend with seeds 0/4242 does not reproduce MR2 at {fold}")
            log(f"A22 preflight seeds {fold}: seed backend at 0/4242 reproduces MR2 exactly; {(time.time() - t1) / 60:.1f} min"); del db, db0, ctx; gc.collect()
    if which in ("all", "raw80"):
        SensBackend, _ = _sens_classes(); db = SensBackend("RAW", 3); t1 = time.time()
        if len(db.candidates("RAW|3")) < 60: raise RuntimeError(f"RAW pool has only {len(db.candidates('RAW|3'))} usable candidates")
        for fam in FAMILIES:
            st = RUN.select_fold(Logged(One(db), "preflight raw80"), "RAW|3", fam); sc = RUN.score_fold(One(db), "RAW|3", fam, st)
            log(f"A22 preflight RAW pool RAW|3 {fam}: {len(db.candidates('RAW|3'))} candidates; features {st['features']} params {st['params']}; H1(a) {sc['a']}, H1(b) {sc['b']:+.4f} (MR2 {units[('score', 'RAW|3', fam)]['b']:+.4f})")
        log(f"A22 preflight RAW pool: {(time.time() - t1) / 60:.1f} min"); del db; gc.collect()
    if which in ("all", "grids"):
        fs = final_setups(); dbs = {}
        for g in (5, 15, 1):
            with Grid(g):
                for fold in CONTAMINATED:
                    era, n = fold.split("|"); ctx = era_context_grid(era); db = seed_fold(era, n, 0, 4242, shared=ctx, dmax=390 // g); dbs[(g, fold)] = db; t1 = time.time()
                    for fam in (FAMILIES if g != 1 else ("gaussian_hmm", "student_t_hmm", "bocpd")):
                        st = {x: fs[era][fam][x] for x in ("features", "params", "base_params")}; sc = grid_score(db, fold, fam, st, g)
                        if sc["b"] is None: raise RuntimeError(f"grid {g} preflight {fold} {fam}: H1(b) not evaluable")
                        mr = units[("select", fold, fam)]; same_setup = mr["features"] == st["features"] and mr["params"] == st["params"] and mr["base_params"] == st["base_params"]
                        if g == 5 and same_setup:
                            ref = units[("score", fold, fam)]
                            if not (same(sc["a"], ref["a"]) and same(sc["b"], ref["b"])): raise Mismatch(f"grid 5 with the fold's own setup does not reproduce MR2 at {fold} {fam}")
                        log(f"A22 preflight grid {g} {fold} {fam}: H1(a) {sc['a']}, H1(b) {sc['b']:+.4f}{' (= MR2 exactly)' if g == 5 and same_setup else ''}")
                    log(f"A22 preflight grid {g} {fold}: {(time.time() - t1) / 60:.1f} min")
                    if g != 1: del dbs[(g, fold)]
                    gc.collect()
        with Grid(1): pj = hsmm1_projection(dbs)
        write_json(PRE / "hsmm1_projection.json", pj); log(f"A22 preflight 1-min HSMM: {pj['seconds_per_iteration']:.1f} s per EM iteration x {pj['mean_iterations_per_start_5min']:.0f} iterations x 3 starts x 2 models x 26 folds = {pj['projected_hours_26_folds']:.1f} h -> {'RUN' if pj['run'] else 'NOT RUN'} (limit {HSMM1_MAX_H} h)")
    log(f"A22 preflight [{which}] PASSED in {(time.time() - t0) / 60:.1f} min (written to results/a22_preflight/)"); return ph


# ---------- run
def run(token, phase):
    ph = guards(token); OUT.mkdir(parents=True, exist_ok=True); t0 = time.time(); log(f"A22 phase {phase} start")
    if phase == "d8c":
        rc = subprocess.run([sys.executable, str(HERE / "s5_d8c.py")])
        if rc.returncode != 0: raise RuntimeError(f"D8c exited {rc.returncode}")
    else:
        {"power": lambda: phase_power(ph, OUT), "era_flagged": lambda: phase_era_flagged(ph, OUT), "thresholds": lambda: phase_thresholds(ph, OUT), "delay": lambda: phase_delay(ph, OUT),
         "a18": lambda: phase_a18(ph, OUT), "seeds": lambda: phase_seeds(ph, OUT), "raw80": lambda: phase_raw80(ph, OUT),
         "grids": lambda: phase_grid(ph, OUT, GRIDS, FAMILIES, "5 = reference, 15"), "grid1": lambda: phase_grid(ph, OUT, (1,), ("gaussian_hmm", "student_t_hmm", "bocpd"), "1-min, no HSMM"),
         "grid1_hsmm": lambda: phase_grid1_hsmm(ph, OUT)}[phase]()
    log(f"A22 phase {phase} DONE in {(time.time() - t0) / 3600:.2f} h; no freeze, no era calibration"); return EXIT_OK


DONE_FILES = dict(power="results/a22/power.json", d8c="results/d8/d8c_results.json", era_flagged="results/a22/era_flagged.json", thresholds="results/a22/thresholds.json", delay="results/a22/delay.json",
                  a18="results/mr2/a18/a18_results.json", seeds="results/a22/seeds.json", raw80="results/a22/raw80.json", grids="results/a22/grids.json", grid1="results/a22/grids.json", grid1_hsmm="results/a22/grid1_hsmm.json")


def main():
    if len(sys.argv) < 3 or sys.argv[2] not in PHASES + ("all", "cheap"): print(__doc__); return EXIT_GUARD
    token, phase, check = sys.argv[1], sys.argv[2], "--check" in sys.argv[3:]
    if not check and phase in ("all", "cheap"): print("'all' and 'cheap' are preflight groups (--check)"); return EXIT_GUARD
    import s5_d7 as D
    guard_errors = (PermissionError, RuntimeError, AssertionError) if check else (PermissionError,)
    try:
        D.keep_awake(True)
        if check: preflight(token, phase); return EXIT_OK
        return run(token, phase)
    except Mismatch as e: log(f"A22 {phase} REPRODUCTION MISMATCH (stop): {e}"); return EXIT_MISMATCH
    except guard_errors as e: log(f"A22 {phase} {'preflight ' if check else ''}REFUSED: {type(e).__name__}: {e}"); return EXIT_GUARD
    except KeyboardInterrupt: log(f"A22 {phase} STOPPED by the user (Ctrl+C); finished units are checkpointed"); return EXIT_STOP
    except BaseException as e:
        log(f"A22 {phase} CRASH: {type(e).__name__}: {e}")
        for l in traceback.format_exc().rstrip().splitlines(): log("  | " + l)
        return EXIT_CRASH
    finally: D.keep_awake(False)


if __name__ == "__main__":
    sys.exit(main())
