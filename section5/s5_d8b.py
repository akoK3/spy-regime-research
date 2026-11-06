#!/usr/bin/env python3
"""D8b (AMENDMENT_A19_1.md): sensitivity of the D8 census, one factor at a time: (S1) stricter 'large' thresholds, (S2) 30- and 120-min windows, (S3) LEGACY completeness >= 90%.
No detector, no model, no outcome. Writes section5/results/d8/d8b_results.json. D8's primary results are not changed."""
import sys, json, time, datetime, math
from pathlib import Path
import numpy as np, pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import s5_d8 as D, s5_lib as L, s5_d2_stable as S
import step11_a4_rerun_4_3_4_7_8 as pstep

HERE = Path(__file__).resolve().parent; OUT = HERE / "results" / "d8"
Z1, Z01 = 2.576, 3.291
PRIMARY = dict(w=60, large=dict(trend=Z1 * math.sqrt(2), momentum=Z1 * math.sqrt(2 / 60), vol_hi=2.0, vol_lo=0.5, jump=1), legacy_complete=0.98)
VARIANTS = {"D8_primary_recomputed": PRIMARY,
            "S1_strict": dict(PRIMARY, large=dict(trend=Z01 * math.sqrt(2), momentum=Z01 * math.sqrt(2 / 60), vol_hi=3.0, vol_lo=1 / 3, jump=2)),
            "S2_w30": dict(PRIMARY, w=30, large=dict(PRIMARY["large"], momentum=Z1 * math.sqrt(2 / 30))),
            "S2_w120": dict(PRIMARY, w=120, large=dict(PRIMARY["large"], momentum=Z1 * math.sqrt(2 / 120))),
            "S3_legacy90": dict(PRIMARY, legacy_complete=0.90)}
TYPES = ("trend", "momentum", "liquidity", "jumps")


def windows(r, dv, dvol, jump, w):
    mf = math.ceil(50 * w / 60); out = []
    for s in range(w, 390 - w + 1, 5):
        W, P = slice(s, s + w), slice(s - w, s)
        if np.isfinite(r[W]).sum() < mf or np.isfinite(r[P]).sum() < mf: continue
        t = lambda x: (lambda y: np.sqrt(w) * y.mean() / y.std(ddof=1) if len(y) >= mf and y.std(ddof=1) > 0 else np.nan)(x[np.isfinite(x)])
        rr = lambda x: (lambda a, b, ok: np.corrcoef(a[ok], b[ok])[0, 1] if ok.sum() >= mf - 1 else np.nan)(x[:-1], x[1:], np.isfinite(x[:-1]) & np.isfinite(x[1:]))
        rat = lambda a, b: (lambda x, y: x / y if x > 0 and y > 0 else np.nan)(np.nanmean(a), np.nanmean(b))
        out.append(dict(VR=rat(dv[W], dv[P]), VOL=rat(dvol[W], dvol[P]), dt=t(r[W]) - t(r[P]), drho=rr(r[W]) - rr(r[P]), dJ=float(np.nansum(jump[W]) - np.nansum(jump[P]))))
    return out


def shares(df, lg):
    st = (df.VR >= D.BAND[0]) & (df.VR <= D.BAND[1])
    fl = dict(trend=df.dt.abs() >= lg["trend"], momentum=df.drho.abs() >= lg["momentum"], liquidity=(df.VOL >= lg["vol_hi"]) | (df.VOL <= lg["vol_lo"]), jumps=df.dJ >= lg["jump"])
    return {k: float(f[st].mean()) for k, f in fl.items()}, int(len(df)), float(st.mean())


def main():
    import s5_contamination as C; C.check_registry(HERE); t0 = time.time(); data = {}
    for era in ("LEGACY", "RAW"):
        d = L.load_era(era, ["lee_mykland_approx60"]); jump = L._step3().construct_deferred(d)["lee_mykland_jump60"]; dv = S.des_variance(d)
        vol = np.where(np.isfinite(d["volume"]) & (d["volume"] >= 0), d["volume"].astype(float), np.nan); dvol = pstep.adjust(vol, d["slot"], d["first"], d["end"])
        nf = int(pd.read_csv(L.R / "a4_development_nested_folds_TRAIN.csv").query("era == @era").fold.max()) + 1; val = set()
        for f in range(nf): val.update(int(i) for i in L.fold_segments(d, era, f)["val"])
        sess = []
        for i in sorted(val):
            a, b = int(d["first"][i]), int(d["end"][i])
            if b - a == 390: sess.append((float(np.isfinite(d["close"][a:b]).mean()), np.where(d["valid"][a:b], d["r"][a:b], np.nan), dv[a:b], dvol[a:b], jump[a:b]))
        data[era] = sess; del d
    res = dict(label="D8b sensitivity (AMENDMENT_A19_1.md); does not change D8", generated=datetime.datetime.now(datetime.timezone.utc).isoformat(), amendment_sha256=L.sha(L.ROOT / "AMENDMENT_A19_1.md"), variants={})
    for name, v in VARIANTS.items():
        out = {}
        for era, sess in data.items():
            need = v["legacy_complete"] if era == "LEGACY" else 0.98; use = [s for s in sess if s[0] >= need]
            df = pd.DataFrame([x for s in use for x in windows(s[1], s[2], s[3], s[4], v["w"])]); sh, n, st = shares(df, v["large"])
            out[era] = dict(sessions=len(use), windows=n, variance_stable_share=st, large_given_variance_stable=sh)
        occ = {k: all(out[e]["large_given_variance_stable"][k] >= D.OCCURS for e in out) for k in TYPES}
        res["variants"][name] = dict(settings=v, eras=out, occurs=occ); print(name, occ, {e: {k: round(x, 4) for k, x in out[e]["large_given_variance_stable"].items()} for e in out}, {e: out[e]["sessions"] for e in out}, flush=True)
    base = json.loads((OUT / "d8_results.json").read_text(encoding="utf-8"))["occurs"]
    res["d8_primary_occurs"] = base; res["primary_reproduced"] = res["variants"]["D8_primary_recomputed"]["occurs"] == base
    res["verdict_changes"] = {n: {k: [base[k], v["occurs"][k]] for k in TYPES if v["occurs"][k] != base[k]} for n, v in res["variants"].items()}; res["seconds"] = round(time.time() - t0, 1)
    (OUT / "d8b_results.json").write_text(json.dumps(res, indent=1), encoding="utf-8"); print("changes", res["verdict_changes"], "reproduced", res["primary_reproduced"])


if __name__ == "__main__":
    main()
