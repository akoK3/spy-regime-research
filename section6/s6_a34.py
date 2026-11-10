#!/usr/bin/env python3
"""AMENDMENT_A34 (post-diagnosis): per-asset placebo pools (A31 rule 1 matching plus the asset available in the placebo session) for
  2a the A32 deseasonalised |return| statistic (exploratory, uncorrected): +5 / +15 / +30 / +60 tested, (T - 30, T] descriptive;
  2b E1 footprint taxonomy (descriptive): per-asset cutoffs; chance reference from a joint TLT-and-HYG pool;
  2c H3 next-day sensitivity, all 4 assets (secondary, BH of 4, outside Holm; the H3 primary is unchanged).
Only these parts are recomputed; every other development result and file is unchanged. Development data only.
Usage: s6_a34.py development DETECTOR [--nboot 9999]     Output (written once): section6/results/a34_development_DETECTOR.json"""
import sys, json, csv, time, hashlib, datetime, collections
from pathlib import Path
import numpy as np
HERE = Path(__file__).resolve().parent; sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE.parent / "section5"))
import s6_lib as L, s6_run as R, s6_h2 as H

ASSETS = R.ASSETS; AMENDMENTS = ("A28", "A29", "A30", "A31", "A32", "A33", "A33_1", "A34"); POST = "post-diagnosis (AMENDMENT_A34; specified after the label-free HYG diagnosis)"


def _seed(u, tag, seed=2034): return int(hashlib.sha256(f"{seed}|{u['era']}|{u['day']}|{u['S']}|{u['kind']}|{u.get('role')}|{tag}".encode()).hexdigest()[:8], 16)


def per_asset_placebos(E_by, cand_by, alarms_by, units):
    """A34 rule 1: u['pl_by_asset'][a] (asset a available in the placebo session) and u['pl_joint'] (TLT and HYG both available; E1 chance reference only)."""
    for u in units:
        E = E_by[u["era"]]; c = cand_by[u["era"]]; al = alarms_by[u["era"]]; mk = lambda ix: [dict(day_idx=int(c["day_idx"][i]), S=int(c["S"][i]), gap=u["gap"], T=int(c["S"][i]) + u["gap"]) for i in ix]
        u["pl_by_asset"] = {a: mk(L.draw_placebos(u, c, al, seed=_seed(u, a), eligible=E.avail[a][c["day_idx"]])) for a in ASSETS}
        u["pl_joint"] = mk(L.draw_placebos(u, c, al, seed=_seed(u, "joint"), eligible=E.avail["TLT"][c["day_idx"]] & E.avail["HYG"][c["day_idx"]]))
    return units


def units_a34(E_by, rows, sess):
    units, cand_by, alarms_by = [], {}, {}
    for era, E in E_by.items():
        u, c, al = R.build(E, [x for x in rows if x["era"] == era], sess); units += u; cand_by[era], alarms_by[era] = c, al
    units = [u for u in units if u.get("role", "break") == "break" and u["kind"] == "confirmed" and u["direction"] == "calm_to_stressed" and u["burn_in_ok"]]
    return per_asset_placebos(E_by, cand_by, alarms_by, units)


def as_asset(units, a): return [dict(u, placebos=u["pl_by_asset"][a]) for u in units]


def e1_a34(E_by, br, h=30):
    """A34 2b: each asset's cutoff from its own per-asset placebo windows; chance reference = joint-pool placebos, each asset's cutoff from its per-asset
    placebos excluding the classified time. Categories and order as A32 4c (s6_h2.classify)."""
    cb, cp = collections.Counter(), collections.Counter(); skipped = dict(window_past_close=0, tlt_or_hyg_not_evaluable=0)
    for u in br:
        E = E_by[u["era"]]; T = u["T"]
        if T + h > L.N_MIN: skipped["window_past_close"] += 1; continue
        ref = {a: [(p["day_idx"], p["T"], p["T"] + h) for p in u["pl_by_asset"][a]] for a in ASSETS}
        m = {a: H.move(E, a, u["day_idx"], T, T + h, ref[a]) for a in ASSETS}
        if m["TLT"] is None or m["HYG"] is None: skipped["tlt_or_hyg_not_evaluable"] += 1; continue
        cb[H.classify(m)] += 1
        for p in u["pl_joint"]:
            d, s, b = p["day_idx"], p["T"], p["T"] + h
            if b > L.N_MIN: continue
            mp = {a: H.move(E, a, d, s, b, [w for w in ref[a] if (w[0], w[1]) != (d, s)]) for a in ASSETS}
            if mp["TLT"] is None or mp["HYG"] is None: continue
            cp[H.classify(mp)] += 1
    nb, npl = sum(cb.values()), sum(cp.values())
    return dict(label="A34 2b E1 footprint taxonomy with per-asset placebo pools (descriptive; " + POST + ")", window=[0, h], n_breaks=nb, n_placebos=npl, skipped=skipped,
                breaks={k: dict(n=cb[k], share=(cb[k] / nb if nb else None)) for k in H.CATS}, placebos={k: dict(n=cp[k], share=(cp[k] / npl if npl else None)) for k in H.CATS})


def analyse(E_by, rows, sess, nboot, detector):
    br = units_a34(E_by, rows, sess); res = dict(detector=detector, label="AMENDMENT_A34 recomputed parts (" + POST + "; development data)", n_breaks=len(br))
    res["placebos_per_break"] = {a: dict(zip(("p10", "p50", "p90"), map(float, np.percentile([len(u["pl_by_asset"][a]) for u in br], [10, 50, 90])))) for a in ASSETS}
    res["exploratory_a32"] = dict(label="EXPLORATORY (A33 rule 4), uncorrected; per-asset placebo pools; " + POST,
                                  tests={f"X_{a}_{w}": H.h2_test(E_by, as_asset(br, a), a, *H.WINDOWS[w], (0 if w == "pre30" else nboot)) for w in ("h30", "h5", "h15", "h60", "pre30") for a in ASSETS})
    h3 = {f"H3_{a}": R.h3_test(E_by, as_asset(br, a), a, "next_day", nboot) for a in ASSETS}
    ps = [(k, v["p"]) for k, v in h3.items() if v.get("p") is not None]; adj = dict(zip([k for k, _ in ps], L.bh([p for _, p in ps]))) if ps else {}
    for k, v in h3.items(): v.update(p_bh=(float(adj[k]) if k in adj else None))
    res["h3_sensitivity"] = dict(label="A34 2c H3 next-day with per-asset placebo pools: SECONDARY sensitivity, BH of 4, outside Holm; the H3 primary is unchanged; " + POST, tests=h3)
    res["E1"] = e1_a34(E_by, br)
    return res


def development(det, nboot):
    if det not in R.FAMILIES[:3]: print("DETECTOR must be gaussian_hmm, student_t_hmm or hsmm"); return 3
    R.a29_guard(AMENDMENTS)
    out = R.OUT / f"a34_development_{det}.json"
    if out.exists(): print("result exists; written once"); return 3
    rows = [x for x in csv.DictReader(open(R.BREAKS / "breaks.csv", encoding="utf-8")) if x["family"] == det]
    for x in rows:
        for k in ("S_min", "T0_min", "end_min"): x[k] = int(x[k]) if x[k] not in ("", "None") else None
    sess = json.loads((R.BREAKS / "sessions.json").read_text(encoding="utf-8")); E_by = {era: R.load_era(era, "development") for era in ("LEGACY", "RAW")}; t0 = time.time()
    res = analyse(E_by, rows, sess, nboot, det)
    import s6_fingerprint as FP, s5_amendment_manifest as AM
    res.update(period="development", nboot=nboot, seconds=round(time.time() - t0, 1), generated=datetime.datetime.now(datetime.timezone.utc).isoformat(),
               provenance=dict(code=FP.current(), amendments=AM.manifest(AMENDMENTS)))
    print(f"written {R.write_once(out, res)}"); return 0


def main():
    a = sys.argv[1:]
    if len(a) < 2 or a[0] != "development": print(__doc__); return 3
    return development(a[1], int(a[a.index("--nboot") + 1]) if "--nboot" in a else L.NBOOT)


if __name__ == "__main__": sys.exit(main())
